"""Flask 应用工厂。"""

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from sqlalchemy import text

load_dotenv()

from app.blueprints import register_blueprints
from app.common.exception import register_error_handlers
from app.common.extensions import configure_jwt_handlers, db, jwt
from app.common.log import configure_logging
from app.common.redis_client import init_redis
from app.config import CONFIGS


def create_app(
    environment: str = "development",
    test_config: dict | None = None,
) -> Flask:
    """创建并配置 Flask 应用实例。

    参数：
        environment：配置环境名称。
        test_config：用于覆盖环境配置的可选设置。

    返回：
        配置完成的 Flask 应用。

    异常：
        ValueError：环境名称未知。
    """
    if environment not in CONFIGS:
        raise ValueError(f"Unknown environment: {environment}")

    app = Flask(__name__)
    app.config.from_object(CONFIGS[environment])
    if test_config:
        app.config.update(test_config)
    _validate_config(app)

    db.init_app(app)
    jwt.init_app(app)
    configure_jwt_handlers()
    CORS(
        app,
        origins=app.config["FRONTEND_ORIGINS"].split(","),
        supports_credentials=True,
    )

    with app.app_context():
        init_redis()

    configure_logging()
    register_error_handlers(app)
    register_blueprints(app)
    from app.commands import register_commands

    register_commands(app)

    @app.get("/api/health")
    def health():
        """返回应用和数据库的健康状态。"""
        from app.common.response import success

        db.session.execute(text("SELECT 1"))
        return success({"status": "ok", "database": "ok"})

    return app


def _validate_config(app: Flask) -> None:
    """缺少必要环境配置时立即终止启动。"""
    required = ("SECRET_KEY", "JWT_SECRET_KEY", "SQLALCHEMY_DATABASE_URI")
    missing = [key for key in required if not app.config.get(key)]
    if missing:
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")