"""微信小程序认证与用户服务。"""

from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
from flask import current_app
from flask_jwt_extended import create_access_token
from PIL import Image, UnidentifiedImageError
from redis.exceptions import RedisError
from sqlalchemy import or_
from werkzeug.datastructures import FileStorage

from app.common.exception import BusinessError
from app.common.extensions import db
from app.common.redis_client import get_redis, prefixed_key

from .models import MiniAppUser
from .schemas import MiniAppAdminUserSchema, MiniAppProfileSchema

WECHAT_SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
WECHAT_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_PHONE_URL = "https://api.weixin.qq.com/wxa/business/getuserphonenumber"
WECHAT_TIMEOUT = 8
MAX_AVATAR_BYTES = 5 * 1024 * 1024
AVATAR_SIZE = (1024, 1024)
AVATAR_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def phone_login(phone_code: str, login_code: str) -> dict[str, Any]:
    """使用微信登录凭证和手机号授权凭证登录小程序。"""
    session = _exchange_login_code(login_code)
    phone_info = _exchange_phone_code(phone_code)
    openid = session.get("openid")
    phone_number = phone_info.get("purePhoneNumber") or phone_info.get("phoneNumber")
    if not openid or not phone_number:
        raise BusinessError("微信未返回完整用户信息", 502)

    # 根据 openid 判断唯一性，而非手机号
    user = db.session.scalar(db.select(MiniAppUser).where(MiniAppUser.openid == openid))
    if user is None:
        user = MiniAppUser(openid=openid, phone_number=phone_number)
        db.session.add(user)
    elif not user.is_active:
        raise BusinessError("账号已停用", 403)

    user.is_deleted = False
    user.unionid = session.get("unionid") or user.unionid
    user.phone_number = phone_number
    user.country_code = phone_info.get("countryCode") or "86"
    user.last_login = datetime.now()
    user.login_count = (user.login_count or 0) + 1
    db.session.commit()

    profile = MiniAppProfileSchema().dump(user)
    profile["token"] = create_access_token(
        identity=str(user.id),
        additional_claims={"user_type": "miniapp"},
        expires_delta=timedelta(days=30),
    )
    return profile


def get_miniapp_user(user_id: int) -> MiniAppUser:
    """返回当前可登录的小程序用户。"""
    user = db.session.get(MiniAppUser, user_id)
    if user is None or user.is_deleted or not user.is_active:
        raise BusinessError("小程序用户不存在或已停用", 401)
    return user


def update_profile(user_id: int, nickname: str) -> MiniAppUser:
    """保存小程序用户主动填写的昵称。"""
    nickname = nickname.strip()
    if not nickname:
        raise BusinessError("昵称不能为空", 422)
    user = get_miniapp_user(user_id)
    user.nickname = nickname
    db.session.commit()
    return user


def save_avatar(user_id: int, avatar: FileStorage) -> MiniAppUser:
    """校验、压缩并保存小程序用户头像文件。"""
    content = avatar.read(MAX_AVATAR_BYTES + 1)
    if not content:
        raise BusinessError("请选择头像文件", 422)
    if len(content) > MAX_AVATAR_BYTES:
        raise BusinessError("头像不能超过 5 MB", 422)

    try:
        image = Image.open(BytesIO(content))
        image_format = (image.format or "").upper()
        if image_format not in AVATAR_FORMATS:
            raise BusinessError("头像仅支持 JPG、PNG 或 WebP", 422)
        image.load()
    except BusinessError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise BusinessError("头像文件无效", 422) from exc

    if image_format in ("JPEG", "WEBP") and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.thumbnail(AVATAR_SIZE)

    folder = get_avatar_folder()
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{AVATAR_FORMATS[image_format]}"
    target = folder / filename
    save_options = {"optimize": True}
    if image_format in ("JPEG", "WEBP"):
        save_options["quality"] = 88
    image.save(target, format=image_format, **save_options)

    user = get_miniapp_user(user_id)
    previous_avatar = user.avatar_url
    user.avatar_url = f"/api/miniapp/avatars/{filename}"
    db.session.commit()
    _remove_previous_avatar(previous_avatar, filename)
    return user


def get_avatar_folder() -> Path:
    """返回小程序头像文件存储目录。"""
    return Path(current_app.config["MINIAPP_AVATAR_FOLDER"])


def list_miniapp_users(args: dict[str, Any]) -> dict[str, Any]:
    """返回后台管理端使用的小程序用户分页列表。"""
    page = max(int(args.get("page", 1)), 1)
    per_page = min(max(int(args.get("pageSize", 20)), 1), 100)
    statement = db.select(MiniAppUser).where(MiniAppUser.is_deleted.is_(False))
    keyword = str(args.get("keyword", "")).strip()
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(
            or_(
                MiniAppUser.nickname.ilike(pattern),
                MiniAppUser.phone_number.ilike(pattern),
                MiniAppUser.openid.ilike(pattern),
            )
        )
    status = args.get("status")
    if status in ("启用", "停用"):
        statement = statement.where(MiniAppUser.is_active.is_(status == "启用"))
    pagination = db.paginate(
        statement.order_by(MiniAppUser.last_login.desc(), MiniAppUser.id.desc()),
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return {
        "items": MiniAppAdminUserSchema(many=True).dump(pagination.items),
        "total": pagination.total,
        "page": pagination.page,
        "pageSize": pagination.per_page,
        "pages": pagination.pages,
    }


def _remove_previous_avatar(previous_avatar: str, current_filename: str) -> None:
    """删除用户已被替换的旧头像文件。"""
    if not previous_avatar.startswith("/api/miniapp/avatars/"):
        return
    previous_filename = previous_avatar.rsplit("/", 1)[-1]
    if previous_filename == current_filename:
        return
    previous_path = get_avatar_folder() / previous_filename
    if previous_path.is_file():
        previous_path.unlink()


def _exchange_login_code(login_code: str) -> dict[str, Any]:
    """调用微信 jscode2session 换取用户标识。"""
    appid, secret = _wechat_credentials()
    return _wechat_request(
        "GET",
        WECHAT_SESSION_URL,
        params={
            "appid": appid,
            "secret": secret,
            "js_code": login_code,
            "grant_type": "authorization_code",
        },
    )


def _exchange_phone_code(phone_code: str) -> dict[str, Any]:
    """调用微信接口换取授权手机号。"""
    data = _wechat_request(
        "POST",
        WECHAT_PHONE_URL,
        params={"access_token": _get_access_token()},
        json={"code": phone_code},
    )
    return data.get("phone_info") or {}


def _get_access_token() -> str:
    """获取并缓存微信接口调用凭证。"""
    cache_key = prefixed_key("miniapp", "access_token")
    try:
        cached = get_redis().get(cache_key)
        if cached:
            return cached
    except RedisError:
        current_app.logger.warning("Redis unavailable; requesting WeChat access token")

    appid, secret = _wechat_credentials()
    data = _wechat_request(
        "GET",
        WECHAT_ACCESS_TOKEN_URL,
        params={"grant_type": "client_credential", "appid": appid, "secret": secret},
    )
    token = data.get("access_token")
    if not token:
        raise BusinessError("微信未返回接口调用凭证", 502)
    try:
        expires_in = max(int(data.get("expires_in", 7200)) - 300, 60)
        get_redis().setex(cache_key, expires_in, token)
    except RedisError:
        pass
    return token


def _wechat_credentials() -> tuple[str, str]:
    """返回服务端配置的微信小程序凭据。"""
    appid = current_app.config.get("WECHAT_MINIAPP_APPID")
    secret = current_app.config.get("WECHAT_MINIAPP_SECRET")
    if not appid or not secret:
        raise BusinessError("微信小程序服务尚未配置", 503)
    return appid, secret


def _wechat_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    """请求微信接口并转换统一错误。"""
    try:
        response = requests.request(method, url, timeout=WECHAT_TIMEOUT, **kwargs)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        current_app.logger.warning("WeChat request failed: %s", exc)
        raise BusinessError("微信服务请求失败，请稍后重试", 502) from exc
    if data.get("errcode", 0) != 0:
        current_app.logger.warning(
            "WeChat API error: errcode=%s errmsg=%s",
            data.get("errcode"),
            data.get("errmsg"),
        )
        raise BusinessError("微信授权失败，请重新操作", 400)
    return data