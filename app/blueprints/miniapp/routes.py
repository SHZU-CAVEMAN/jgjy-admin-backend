"""微信小程序认证 HTTP 路由。"""

from flask import Blueprint, request, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.customers.schemas import ConsultationSchema
from app.blueprints.customers.services import (
    create_consultation,
    list_public_need_categories,
    list_user_favorites,
    list_user_consultations,
    toggle_user_favorite,
)
from app.blueprints.company.schemas import CompanyContactSchema, CompanyProfileSchema
from app.blueprints.company.services import get_company_info
from app.blueprints.products.services import (
    get_public_home_summary,
    get_public_product,
    list_public_products,
)
from app.blueprints.news.services import (
    create_article_comment,
    get_article_interaction_summary,
    get_public_news,
    list_article_comments,
    list_public_news,
    list_user_comments,
    record_article_share,
    toggle_article_like,
)
from app.common.exception import BusinessError
from app.common.response import success

from .schemas import MiniAppProfileSchema, MiniAppProfileUpdateSchema, PhoneLoginSchema
from .services import (
    get_avatar_folder,
    get_miniapp_user,
    phone_login,
    save_avatar,
    update_profile,
)

miniapp_bp = Blueprint("miniapp", __name__, url_prefix="/api/miniapp")


@miniapp_bp.post("/auth/phone-login")
def phone_login_route():
    """使用微信手机号授权完成小程序登录。"""
    payload = PhoneLoginSchema().load(request.get_json(silent=True) or {})
    return success(phone_login(payload["phone_code"], payload["login_code"]))


@miniapp_bp.get("/auth/me")
@jwt_required()
def current_miniapp_user():
    """返回当前小程序登录用户。"""
    user = get_miniapp_user(int(get_jwt_identity()))
    return success(MiniAppProfileSchema().dump(user))


@miniapp_bp.route("/profile", methods=["PUT", "PATCH"])
@jwt_required()
def update_miniapp_profile():
    """保存当前小程序用户主动填写的昵称。"""
    payload = MiniAppProfileUpdateSchema().load(request.get_json(silent=True) or {})
    user = update_profile(int(get_jwt_identity()), payload["nickname"])
    return success(MiniAppProfileSchema().dump(user), "资料保存成功")


@miniapp_bp.post("/profile/avatar")
@jwt_required()
def upload_miniapp_avatar():
    """上传并保存当前小程序用户头像。"""
    avatar = request.files.get("avatar")
    if avatar is None:
        raise BusinessError("请选择头像文件", 422)
    user = save_avatar(int(get_jwt_identity()), avatar)
    return success(MiniAppProfileSchema().dump(user), "头像保存成功")


@miniapp_bp.get("/avatars/<path:filename>")
def miniapp_avatar(filename: str):
    """返回已保存的小程序用户头像。"""
    return send_from_directory(get_avatar_folder(), filename, max_age=86400)


@miniapp_bp.get("/products")
def miniapp_products():
    """返回小程序产品分页列表。"""
    return success(list_public_products(request.args.to_dict()))


@miniapp_bp.get("/products/<int:product_id>")
def miniapp_product_detail(product_id: int):
    """返回小程序产品详情。"""
    return success(get_public_product(product_id))


@miniapp_bp.get("/home")
def miniapp_home():
    """返回小程序首页可展示的实时产品汇总。"""
    return success(get_public_home_summary())


@miniapp_bp.get("/company")
def miniapp_company():
    """返回小程序可公开展示的企业资料和联系方式。"""
    info = get_company_info()
    return success(
        {
            **CompanyProfileSchema().dump(info),
            **CompanyContactSchema().dump(info),
        }
    )


@miniapp_bp.get("/news")
def miniapp_news():
    """返回小程序可见的已发布推文列表。"""
    return success(list_public_news(request.args.to_dict()))


@miniapp_bp.get("/news/<string:media_id>")
def miniapp_news_detail(media_id: str):
    """返回小程序可见的已发布推文详情。"""
    return success(get_public_news(media_id))


@miniapp_bp.get("/news/<string:media_id>/interactions")
@jwt_required(optional=True)
def miniapp_news_interactions(media_id: str):
    """返回文章互动计数及可选的当前用户状态。"""
    identity = get_jwt_identity()
    user_id = int(identity) if identity is not None else None
    return success(get_article_interaction_summary(media_id, user_id))


@miniapp_bp.post("/news/<string:media_id>/likes/toggle")
@jwt_required()
def miniapp_news_like_toggle(media_id: str):
    """切换当前小程序用户对文章的点赞。"""
    return success(toggle_article_like(int(get_jwt_identity()), media_id))


@miniapp_bp.post("/news/<string:media_id>/shares")
@jwt_required()
def miniapp_news_share(media_id: str):
    """记录当前小程序用户的一次文章转发。"""
    return success(record_article_share(int(get_jwt_identity()), media_id))


@miniapp_bp.get("/news/<string:media_id>/comments")
def miniapp_news_comments(media_id: str):
    """返回已发布文章的用户留言。"""
    return success(list_article_comments(media_id))


@miniapp_bp.post("/news/<string:media_id>/comments")
@jwt_required()
def miniapp_news_comment_create(media_id: str):
    """保存当前小程序用户对文章的留言。"""
    comment = create_article_comment(
        int(get_jwt_identity()), media_id, request.get_json(silent=True) or {}
    )
    return success(comment, "留言成功", 201)


@miniapp_bp.get("/need-categories")
def miniapp_need_categories():
    """返回小程序启用的需求分类。"""
    return success(list_public_need_categories())


@miniapp_bp.get("/favorites")
@jwt_required()
def miniapp_favorites():
    """返回当前小程序用户的收藏。"""
    return success(list_user_favorites(int(get_jwt_identity())))


@miniapp_bp.post("/favorites/toggle")
@jwt_required()
def miniapp_favorite_toggle():
    """切换当前小程序用户的收藏状态。"""
    result = toggle_user_favorite(
        int(get_jwt_identity()), request.get_json(silent=True) or {}
    )
    return success(result)


@miniapp_bp.get("/my-comments")
@jwt_required()
def miniapp_my_comments():
    """返回当前小程序用户发表的留言。"""
    return success(list_user_comments(int(get_jwt_identity())))


@miniapp_bp.post("/consultations")
@jwt_required()
def create_miniapp_consultation():
    """提交当前小程序用户的咨询需求。"""
    need = create_consultation(
        int(get_jwt_identity()),
        request.get_json(silent=True) or {},
    )
    return success(ConsultationSchema().dump(need), "咨询提交成功", 201)


@miniapp_bp.get("/consultations")
@jwt_required()
def miniapp_consultations():
    """返回当前小程序用户自己的咨询记录。"""
    return success(list_user_consultations(int(get_jwt_identity())))