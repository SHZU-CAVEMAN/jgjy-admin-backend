"""新闻业务域 HTTP 路由。"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.common.crud import register_crud_routes
from app.common.response import success

from .schemas import PullSettingSchema
from .services import (
    article_service,
    category_service,
    get_pull_setting,
    interaction_service,
    update_pull_setting,
)

news_bp = Blueprint("news", __name__, url_prefix="/api/news")

register_crud_routes(news_bp, "/categories", "categories", category_service)
register_crud_routes(news_bp, "/articles", "articles", article_service)
register_crud_routes(news_bp, "/interactions", "interactions", interaction_service)


@news_bp.get("/pull-settings")
@jwt_required()
def pull_settings_get():
    """返回公众号拉取设置。"""
    return success(PullSettingSchema().dump(get_pull_setting()))


@news_bp.put("/pull-settings")
@jwt_required()
def pull_settings_put():
    """替换公众号拉取设置。"""
    setting = update_pull_setting(request.get_json(silent=True) or {})
    return success(PullSettingSchema().dump(setting), "保存成功")
