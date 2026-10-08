"""产品业务域 HTTP 路由。"""

from flask import Blueprint, request, send_from_directory
from flask_jwt_extended import jwt_required

from app.common.crud import register_crud_routes
from app.common.exception import BusinessError
from app.common.response import success

from .services import (
    category_service,
    get_product_image_folder,
    product_service,
    save_product_image,
    traceability_service,
)

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

register_crud_routes(products_bp, "/categories", "categories", category_service)
register_crud_routes(products_bp, "/list", "products", product_service)
register_crud_routes(
    products_bp,
    "/traceability",
    "traceability",
    traceability_service,
)


@products_bp.post("/images")
@jwt_required()
def upload_product_image():
    """上传产品原图并返回三种图片地址。"""
    image_file = request.files.get("image")
    if image_file is None:
        raise BusinessError("请选择产品图片", 422)
    return success(save_product_image(image_file), "图片上传成功", 201)


@products_bp.get("/media/<path:filename>")
def product_image(filename: str):
    """返回产品原图或压缩图片。"""
    return send_from_directory(get_product_image_folder(), filename, max_age=2592000)
