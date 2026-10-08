"""产品业务域服务。"""

from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import or_
from werkzeug.datastructures import FileStorage

from app.common.crud import CrudService
from app.common.exception import BusinessError
from app.common.extensions import db

from .models import Product, ProductCategory, TraceabilityBatch
from .schemas import ProductCategorySchema, ProductSchema, TraceabilitySchema

MAX_PRODUCT_IMAGE_BYTES = 15 * 1024 * 1024
THUMBNAIL_SIZE = (480, 360)
DETAIL_IMAGE_SIZE = (1280, 720)
THUMBNAIL_MAX_BYTES = 80 * 1024
DETAIL_IMAGE_MAX_BYTES = 164 * 1024
ORIGINAL_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
CATEGORY_TYPES = {"浓香型": "nong", "酱香型": "jiang", "清香型": "qing"}
TYPE_CATEGORIES = {value: key for key, value in CATEGORY_TYPES.items()}


class ProductCrudService(CrudService):
    """在标准产品 CRUD 之外维护产品图片文件生命周期。"""

    def update(self, record_id: int, payload: dict[str, Any]) -> Product:
        """更新产品，并在换图成功后删除旧图片。"""
        record = self.get(record_id)
        previous_urls = _product_image_urls(record)
        updated = super().update(record_id, payload)
        current_urls = set(_product_image_urls(updated))
        _remove_product_images(url for url in previous_urls if url not in current_urls)
        return updated

    def delete(self, record_id: int) -> None:
        """软删除产品并删除其图片文件。"""
        record = self.get(record_id)
        image_urls = _product_image_urls(record)
        super().delete(record_id)
        _remove_product_images(image_urls)

category_service = CrudService(
    ProductCategory,
    ProductCategorySchema(),
    ("name",),
    ("status",),
)
product_service = ProductCrudService(
    Product,
    ProductSchema(),
    ("name", "category"),
    ("status", "category"),
)
traceability_service = CrudService(
    TraceabilityBatch,
    TraceabilitySchema(),
    ("batch", "product"),
    ("status",),
)


def save_product_image(image_file: FileStorage) -> dict[str, str]:
    """保存产品原图并生成列表缩略图和详情压缩图。"""
    content = image_file.read(MAX_PRODUCT_IMAGE_BYTES + 1)
    if not content:
        raise BusinessError("请选择产品图片", 422)
    if len(content) > MAX_PRODUCT_IMAGE_BYTES:
        raise BusinessError("产品图片不能超过 15 MB", 422)

    try:
        source = Image.open(BytesIO(content))
        image_format = (source.format or "").upper()
        if image_format not in ORIGINAL_FORMATS:
            raise BusinessError("产品图片仅支持 JPG、PNG 或 WebP", 422)
        source = ImageOps.exif_transpose(source)
        source.load()
    except BusinessError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise BusinessError("产品图片文件无效", 422) from exc

    image_id = uuid4().hex
    root = get_product_image_folder()
    original_dir = root / "original"
    thumbnail_dir = root / "thumbnail"
    detail_dir = root / "detail"
    for folder in (original_dir, thumbnail_dir, detail_dir):
        folder.mkdir(parents=True, exist_ok=True)

    original_name = f"{image_id}.{ORIGINAL_FORMATS[image_format]}"
    thumbnail_name = f"{image_id}.jpg"
    detail_name = f"{image_id}.jpg"
    (original_dir / original_name).write_bytes(content)

    rgb_source = source.convert("RGB")
    thumbnail = ImageOps.fit(rgb_source, THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    detail = ImageOps.fit(rgb_source, DETAIL_IMAGE_SIZE, Image.Resampling.LANCZOS)
    _save_jpeg_under_limit(
        thumbnail,
        thumbnail_dir / thumbnail_name,
        THUMBNAIL_MAX_BYTES,
    )
    _save_jpeg_under_limit(
        detail,
        detail_dir / detail_name,
        DETAIL_IMAGE_MAX_BYTES,
    )

    return {
        "imageOriginalUrl": f"/api/products/media/original/{original_name}",
        "thumbnailUrl": f"/api/products/media/thumbnail/{thumbnail_name}",
        "detailImageUrl": f"/api/products/media/detail/{detail_name}",
    }


def get_product_image_folder() -> Path:
    """返回产品图片根目录。"""
    return Path(current_app.config["PRODUCT_IMAGE_FOLDER"])


def list_public_products(args: dict[str, Any]) -> dict[str, Any]:
    """返回小程序可见的上架产品分页列表。"""
    page = max(int(args.get("page", 1)), 1)
    per_page = min(max(int(args.get("pageSize", 20)), 1), 100)
    statement = db.select(Product).where(
        Product.is_deleted.is_(False),
        Product.status == "上架",
    )
    keyword = str(args.get("keyword", "")).strip()
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(
            or_(
                Product.name.ilike(pattern),
                Product.category.ilike(pattern),
                Product.year.ilike(pattern),
            )
        )
    product_type = args.get("type")
    if product_type in TYPE_CATEGORIES:
        statement = statement.where(Product.category == TYPE_CATEGORIES[product_type])
    pagination = db.paginate(
        statement.order_by(Product.id.desc()),
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return {
        "items": [_serialize_public_product(product) for product in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pageSize": pagination.per_page,
        "pages": pagination.pages,
    }


def get_public_product(product_id: int) -> dict[str, Any]:
    """返回一条小程序可见产品详情。"""
    product = db.session.get(Product, product_id)
    if product is None or product.is_deleted or product.status != "上架":
        raise BusinessError("产品不存在或已下架", 404)
    return _serialize_public_product(product)


def _serialize_public_product(product: Product) -> dict[str, Any]:
    """将产品转换为小程序展示结构。"""
    data = ProductSchema().dump(product)
    data["type"] = CATEGORY_TYPES.get(product.category, product.category)
    data["image"] = data.get("thumbnailUrl", "")
    return data


def _product_image_urls(product: Product) -> tuple[str, str, str]:
    """返回产品关联的三种图片路径。"""
    return (
        product.image_original_url,
        product.thumbnail_url,
        product.detail_image_url,
    )


def _remove_product_images(urls) -> None:
    """删除不再被产品记录引用的本地图片文件。"""
    root = get_product_image_folder()
    prefix = "/api/products/media/"
    for url in urls:
        if not url or not url.startswith(prefix):
            continue
        path = root / url.removeprefix(prefix)
        if path.is_file():
            path.unlink()


def _save_jpeg_under_limit(image: Image.Image, target: Path, max_bytes: int) -> None:
    """在保持目标尺寸的前提下压缩 JPEG 到指定上限。"""
    working = image.copy()
    while True:
        smallest = b""
        for quality in range(88, 43, -4):
            output = BytesIO()
            working.save(
                output,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
            )
            smallest = output.getvalue()
            if len(smallest) <= max_bytes:
                target.write_bytes(smallest)
                return
        if working.width <= 320:
            target.write_bytes(smallest)
            return
        working = working.resize(
            (int(working.width * 0.85), int(working.height * 0.85)),
            Image.Resampling.LANCZOS,
        )
