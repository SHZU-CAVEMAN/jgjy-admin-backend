"""新闻业务域 HTTP 路由。"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.common.crud import register_crud_routes
from app.common.response import success

from .schemas import PullSettingSchema
from .services import (
    article_service,
    category_service,
    get_wechat_draft_content,
    get_pull_setting,
    interaction_service,
    list_wechat_drafts,
    sync_wechat_drafts,
    update_pull_setting,
    update_wechat_draft,
    wechat_draft_schema,
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


@news_bp.get("/drafts")
@jwt_required()
def drafts_list():
    """返回已持久化的微信公众号草稿列表。"""
    return success(list_wechat_drafts(request.args.to_dict()))


@news_bp.patch("/drafts/<string:media_id>")
@jwt_required()
# 更新本地保存的微信公众号草稿信息
def draft_update(media_id: str):
    draft = update_wechat_draft(media_id, request.get_json(silent=True) or {})
    return success(wechat_draft_schema.dump(draft), "更新成功")


@news_bp.post("/drafts/sync")
@jwt_required()
def drafts_sync():
    """手动同步微信公众号草稿箱。"""
    result = sync_wechat_drafts()
    return success(result, "草稿同步成功")


@news_bp.get("/drafts/<string:media_id>/content")
@jwt_required()
def draft_content(media_id: str):
    """返回草稿正文，并在首次读取时持久化。"""
    return success(get_wechat_draft_content(media_id))
