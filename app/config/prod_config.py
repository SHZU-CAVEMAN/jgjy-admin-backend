"""生产环境配置。"""

from .base_config import BaseConfig


class ProductionConfig(BaseConfig):
    """配置生产环境行为。"""

    DEBUG = False
