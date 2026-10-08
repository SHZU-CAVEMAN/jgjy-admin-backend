"""环境配置注册表。"""

from .dev_config import DevelopmentConfig
from .prod_config import ProductionConfig

CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
