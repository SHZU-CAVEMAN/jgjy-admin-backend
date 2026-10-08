"""开发环境配置。"""

from .base_config import BaseConfig


class DevelopmentConfig(BaseConfig):
    """配置本地开发环境行为。"""

    DEBUG = True
    SQLALCHEMY_ECHO = False
