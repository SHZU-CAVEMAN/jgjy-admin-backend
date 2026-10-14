"""客户业务域服务。"""

from datetime import datetime
from typing import Any

from app.blueprints.miniapp.models import MiniAppUser
from app.blueprints.news.models import WechatDraft
from app.blueprints.news.services import _serialize_public_news
from app.blueprints.products.models import Product
from app.blueprints.products.services import _serialize_public_product
from app.common.crud import CrudService
from app.common.exception import BusinessError
from app.common.extensions import db

from .models import Customer, CustomerNeed, Favorite, NeedCategory
from .schemas import (
    ConsultationCreateSchema,
    ConsultationSchema,
    CustomerNeedSchema,
    CustomerSchema,
    FavoriteSchema,
    FavoriteToggleSchema,
    NeedCategorySchema,
)

need_category_service = CrudService(
    NeedCategory,
    NeedCategorySchema(),
    ("name",),
    ("status",),
)

need_service = CrudService(
    CustomerNeed,
    CustomerNeedSchema(),
    ("name", "phone", "category", "content", "region"),
    ("status", "method", "category"),
)
favorite_service = CrudService(
    Favorite,
    FavoriteSchema(),
    ("customer", "content"),
    ("type",),
)
customer_service = CrudService(
    Customer,
    CustomerSchema(),
    ("company", "contact", "phone"),
)


def list_public_need_categories() -> list[dict[str, Any]]:
    """返回小程序可选的启用需求分类。"""
    categories = db.session.scalars(
        db.select(NeedCategory)
        .where(
            NeedCategory.is_deleted.is_(False),
            NeedCategory.status == "启用",
        )
        .order_by(NeedCategory.sort.asc(), NeedCategory.id.asc())
    ).all()
    return NeedCategorySchema(many=True).dump(categories)


def create_consultation(user_id: int, payload: dict[str, Any]) -> CustomerNeed:
    """创建并关联当前小程序用户的咨询需求。"""
    data = ConsultationCreateSchema().load(payload)
    user = db.session.get(MiniAppUser, user_id)
    if user is None or user.is_deleted or not user.is_active:
        raise BusinessError("小程序用户不存在或已停用", 401)
    category = db.session.get(NeedCategory, data["category_id"])
    if category is None or category.is_deleted or category.status != "启用":
        raise BusinessError("需求分类不存在或已停用", 422)

    need = CustomerNeed(
        miniapp_user_id=user.id,
        category_id=category.id,
        name=data["name"],
        phone=data["phone"],
        category=category.name,
        method="微信小程序",
        region=data["region"],
        budget=data["budget"],
        content=data["remark"],
        submitted_at=datetime.now(),
        status="待处理",
    )
    db.session.add(need)
    db.session.commit()
    return need


def list_user_consultations(user_id: int) -> list[dict[str, Any]]:
    """返回当前小程序用户的咨询记录。"""
    records = db.session.scalars(
        db.select(CustomerNeed)
        .where(
            CustomerNeed.miniapp_user_id == user_id,
            CustomerNeed.is_deleted.is_(False),
        )
        .order_by(CustomerNeed.submitted_at.desc(), CustomerNeed.id.desc())
    ).all()
    return ConsultationSchema(many=True).dump(records)


def list_user_favorites(user_id: int) -> list[dict[str, Any]]:
    """返回当前小程序用户的收藏记录。"""
    records = db.session.scalars(
        db.select(Favorite)
        .where(
            Favorite.miniapp_user_id == user_id,
            Favorite.is_deleted.is_(False),
        )
        .order_by(Favorite.favorited_at.desc(), Favorite.id.desc())
    ).all()
    product_ids = set()
    article_ids = set()
    for favorite in records:
        if not favorite.target_id:
            continue
        if favorite.type == "产品" and favorite.target_id.isdigit():
            product_ids.add(int(favorite.target_id))
        elif favorite.type == "推文":
            article_ids.add(favorite.target_id)
    products = db.session.scalars(
        db.select(Product).where(
            Product.id.in_(product_ids),
            Product.status == "上架",
            Product.is_deleted.is_(False),
        )
    ).all() if product_ids else []
    articles = db.session.scalars(
        db.select(WechatDraft).where(
            WechatDraft.media_id.in_(article_ids),
            WechatDraft.status == "已发布",
            WechatDraft.is_deleted.is_(False),
        )
    ).all() if article_ids else []
    products_by_id = {product.id: product for product in products}
    articles_by_id = {article.media_id: article for article in articles}

    items = []
    for favorite in records:
        item = FavoriteSchema().dump(favorite)
        if favorite.type == "产品" and favorite.target_id:
            product = products_by_id.get(int(favorite.target_id)) if favorite.target_id.isdigit() else None
            if product is None:
                continue
            item["item"] = _serialize_public_product(product)
        elif favorite.type == "推文" and favorite.target_id:
            article = articles_by_id.get(favorite.target_id)
            if article is None:
                continue
            item["item"] = _serialize_public_news(article)
        else:
            continue
        items.append(item)
    return items


def toggle_user_favorite(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """切换当前用户对有效产品或已发布推文的收藏状态。"""
    data = FavoriteToggleSchema().load(payload)
    user = db.session.get(MiniAppUser, user_id)
    if user is None or user.is_deleted or not user.is_active:
        raise BusinessError("小程序用户不存在或已停用", 401)

    target_id = data["target_id"]
    if data["type"] == "产品":
        try:
            target = db.session.scalar(
                db.select(Product).where(
                    Product.id == int(target_id),
                    Product.status == "上架",
                    Product.is_deleted.is_(False),
                )
            )
        except ValueError as exc:
            raise BusinessError("产品 ID 无效", 422) from exc
        content = target.name if target else None
    else:
        target = db.session.scalar(
            db.select(WechatDraft).where(
                WechatDraft.media_id == target_id,
                WechatDraft.status == "已发布",
                WechatDraft.is_deleted.is_(False),
            )
        )
        content = target.title if target else None
    if target is None:
        raise BusinessError("收藏内容不存在或不可用", 404)

    favorite = db.session.scalar(
        db.select(Favorite).where(
            Favorite.miniapp_user_id == user_id,
            Favorite.type == data["type"],
            Favorite.target_id == target_id,
            Favorite.is_deleted.is_(False),
        )
    )
    if favorite is not None:
        favorite.soft_delete()
        db.session.commit()
        return {"collected": False}

    favorite = Favorite(
        miniapp_user_id=user.id,
        customer=user.nickname or user.phone_number,
        content=content,
        type=data["type"],
        target_id=target_id,
        favorited_at=datetime.now(),
    )
    db.session.add(favorite)
    db.session.commit()
    return {
        "collected": True,
        "favorite": FavoriteSchema().dump(favorite),
    }
