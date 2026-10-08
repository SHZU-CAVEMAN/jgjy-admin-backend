"""应用公共配置。"""

import os
from datetime import timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class BaseConfig:
    """定义所有运行环境共享的配置。"""

    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173")
    WECHAT_MINIAPP_APPID = os.getenv("WECHAT_MINIAPP_APPID")
    WECHAT_MINIAPP_SECRET = os.getenv("WECHAT_MINIAPP_SECRET")
    MINIAPP_AVATAR_FOLDER = os.getenv(
        "MINIAPP_AVATAR_FOLDER",
        str(PROJECT_ROOT / "uploads" / "miniapp" / "avatars"),
    )
    PRODUCT_IMAGE_FOLDER = os.getenv(
        "PRODUCT_IMAGE_FOLDER",
        str(PROJECT_ROOT / "uploads" / "products"),
    )
    JSON_AS_ASCII = False
