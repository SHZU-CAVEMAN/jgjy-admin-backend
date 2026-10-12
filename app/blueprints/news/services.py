# 新闻业务域服务

import json
from datetime import datetime

import requests
from flask import current_app
from redis.exceptions import RedisError
from sqlalchemy import or_

from app.common.crud import CrudService
from app.common.exception import BusinessError
from app.common.extensions import db
from app.common.redis_client import get_redis, prefixed_key

from .models import Article, Interaction, NewsCategory, PullSetting, WechatDraft
from .schemas import (
    ArticleSchema,
    InteractionSchema,
    NewsCategorySchema,
    PullSettingSchema,
    WechatDraftSchema,
    WechatDraftUpdateSchema,
)

category_service = CrudService(
    NewsCategory,
    NewsCategorySchema(),
    ("name",),
    ("status",),
)
article_service = CrudService(
    Article,
    ArticleSchema(),
    ("title", "category", "author"),
    ("status", "category"),
)
interaction_service = CrudService(
    Interaction,
    InteractionSchema(),
    ("user", "article", "comment"),
    ("type",),
)
wechat_draft_schema = WechatDraftSchema()
WECHAT_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"

# 返回单例拉取设置；不存在时自动创建
def get_pull_setting() -> PullSetting:
    setting = db.session.scalar(
        db.select(PullSetting).where(PullSetting.is_deleted.is_(False))
    )
    if setting is None:
        setting = PullSetting()
        db.session.add(setting)
        db.session.commit()
    return setting

# 校验并替换公众号拉取设置
def update_pull_setting(payload: dict) -> PullSetting:
    setting = get_pull_setting()
    data = PullSettingSchema().load(payload)
    for key, value in data.items():
        setattr(setting, key, value)
    db.session.commit()
    return setting

# 分页查询本地缓存的微信公众号草稿
def list_wechat_drafts(args: dict) -> dict:
    page = max(int(args.get("page", 1)), 1)
    page_size = min(max(int(args.get("pageSize", 20)), 1), 100)
    statement = db.select(WechatDraft).where(WechatDraft.is_deleted.is_(False))
    keyword = str(args.get("keyword", "")).strip()
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(
            or_(WechatDraft.title.ilike(pattern), WechatDraft.author.ilike(pattern))
        )
    pagination = db.paginate(
        statement.order_by(WechatDraft.draft_updated_at.desc(), WechatDraft.id.desc()),
        page=page,
        per_page=page_size,
        error_out=False,
    )
    return {
        "items": wechat_draft_schema.dump(pagination.items, many=True),
        "total": pagination.total,
        "page": pagination.page,
        "pageSize": pagination.per_page,
        "pages": pagination.pages,
    }

# 从公众号草稿箱拉取最新摘要并执行幂等入库
def sync_wechat_drafts() -> dict:
    setting = get_pull_setting()
    payload = _wechat_post(
        "/cgi-bin/draft/batchget",
        {"offset": 0, "count": setting.count, "no_content": 1},
    )
    records = payload.get("item", [])
    if not isinstance(records, list):
        raise BusinessError("微信公众号草稿箱返回格式无效", 502)

    synced_count = 0
    for item in records:
        media_id = item.get("media_id")
        news_items = item.get("content", {}).get("news_item", [])
        if not media_id or not isinstance(news_items, list):
            continue
        first_article = news_items[0] if news_items else {}
        draft = db.session.scalar(
            db.select(WechatDraft).where(WechatDraft.media_id == media_id)
        )
        if draft is None:
            draft = WechatDraft(media_id=media_id)
            db.session.add(draft)
        draft.title = str(first_article.get("title", ""))
        draft.author = str(first_article.get("author", ""))
        draft.digest = str(first_article.get("digest", ""))
        draft.thumbnail_url = str(first_article.get("thumb_url", ""))
        draft.draft_created_at = _timestamp_to_datetime(
            item.get("content", {}).get("create_time")
        )
        draft.draft_updated_at = _timestamp_to_datetime(
            item.get("update_time") or item.get("content", {}).get("update_time")
        )
        draft.articles_json = json.dumps(news_items, ensure_ascii=False)
        draft.content_json = None
        draft.content_synced_at = None
        synced_count += 1
    db.session.commit()
    return {
        "synced": synced_count,
        "total": payload.get("total_count", synced_count),
        "itemCount": payload.get("item_count", synced_count),
    }

# 返回草稿正文；本地未缓存时从微信获取并持久化
def get_wechat_draft_content(media_id: str) -> dict:
    draft = db.session.scalar(
        db.select(WechatDraft).where(
            WechatDraft.media_id == media_id, WechatDraft.is_deleted.is_(False)
        )
    )
    if draft is None:
        raise BusinessError("草稿不存在，请先同步草稿列表", 404)
    if draft.content_json is None:
        payload = _wechat_post("/cgi-bin/draft/get", {"media_id": media_id})
        news_items = payload.get("news_item")
        if not isinstance(news_items, list):
            raise BusinessError("微信公众号草稿详情返回格式无效", 502)
        draft.content_json = json.dumps(news_items, ensure_ascii=False)
        draft.content_synced_at = datetime.now()
        db.session.commit()
    return {
        "draft": wechat_draft_schema.dump(draft),
        "articles": json.loads(draft.content_json),
    }


# 更新本地草稿信息并校验所选分类
def update_wechat_draft(media_id: str, payload: dict) -> WechatDraft:
    draft = db.session.scalar(
        db.select(WechatDraft).where(
            WechatDraft.media_id == media_id, WechatDraft.is_deleted.is_(False)
        )
    )
    if draft is None:
        raise BusinessError("草稿不存在，请先同步草稿列表", 404)
    data = WechatDraftUpdateSchema().load(payload, partial=True)
    category = data.get("category")
    if category is not None:
        active_category = db.session.scalar(
            db.select(NewsCategory).where(
                NewsCategory.name == category,
                NewsCategory.status == "启用",
                NewsCategory.is_deleted.is_(False),
            )
        )
        if active_category is None:
            raise BusinessError("所选推文分类不存在或已停用", 422)
    for key, value in data.items():
        setattr(draft, key, value)
    db.session.commit()
    return draft

# 发送微信公众号接口请求并标准化上游失败
def _wechat_post(path: str, payload: dict) -> dict:
    access_token = _get_access_token()
    try:
        response = requests.post(
            f"https://api.weixin.qq.com{path}",
            params={"access_token": access_token},
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        data = response.json()
    except requests.RequestException as exc:
        current_app.logger.exception("微信公众号草稿接口请求失败")
        raise BusinessError("微信公众号草稿接口请求失败", 502) from exc
    except ValueError as exc:
        current_app.logger.exception("微信公众号草稿接口返回了无效 JSON")
        raise BusinessError("微信公众号草稿接口返回格式无效", 502) from exc
    if data.get("errcode", 0) != 0:
        current_app.logger.warning(
            "微信公众号草稿接口返回错误：errcode=%s, errmsg=%s",
            data.get("errcode"),
            data.get("errmsg"),
        )
        raise BusinessError(
            f"微信公众号草稿接口错误：{data.get('errmsg', data['errcode'])}", 502
        )
    return data

# 获取公众号 access token，并在到期前五分钟自动刷新
def _get_access_token() -> str:
    cache_key = prefixed_key("official-account", "access_token")
    try:
        cached = get_redis().get(cache_key)
        if cached:
            return cached
    except RedisError:
        current_app.logger.warning("Redis unavailable; requesting official account token")

    appid = current_app.config.get("WECHAT_OFFICIAL_ACCOUNT_APPID")
    secret = current_app.config.get("WECHAT_OFFICIAL_ACCOUNT_SECRET")
    if not appid or not secret:
        raise BusinessError("未配置微信公众号 AppID 或 AppSecret", 503)
    try:
        response = requests.get(
            WECHAT_ACCESS_TOKEN_URL,
            params={
                "grant_type": "client_credential",
                "appid": appid,
                "secret": secret,
            },
            timeout=15,
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        data = response.json()
    except requests.RequestException as exc:
        current_app.logger.exception("微信公众号 access token 请求失败")
        raise BusinessError("微信公众号 access token 请求失败", 502) from exc
    except ValueError as exc:
        current_app.logger.exception("微信公众号 access token 返回了无效 JSON")
        raise BusinessError("微信公众号 access token 返回格式无效", 502) from exc
    if data.get("errcode", 0) != 0:
        current_app.logger.warning(
            "微信公众号 access token 接口返回错误：errcode=%s, errmsg=%s",
            data.get("errcode"),
            data.get("errmsg"),
        )
        raise BusinessError(
            f"微信公众号 access token 接口错误：{data.get('errmsg', data['errcode'])}",
            502,
        )
    token = data.get("access_token")
    if not token:
        raise BusinessError("微信公众号未返回 access token", 502)
    try:
        expires_in = max(int(data.get("expires_in", 7200)) - 300, 60)
        get_redis().setex(cache_key, expires_in, token)
    except RedisError:
        current_app.logger.warning("Redis unavailable; official account token is not cached")
    return token

# 转换微信公众号 Unix 秒级时间戳
def _timestamp_to_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value))
    except (TypeError, ValueError, OSError) as exc:
        raise BusinessError("微信公众号草稿时间戳无效", 502) from exc
