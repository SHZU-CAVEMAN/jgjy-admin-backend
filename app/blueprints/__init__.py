"""业务蓝图注册。"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """注册所有业务蓝图。"""
    from .auth.routes import auth_bp
    from .company.routes import company_bp
    from .customers.routes import customers_bp
    from .dashboard.routes import dashboard_bp
    from .miniapp.routes import miniapp_bp
    from .news.routes import news_bp
    from .products.routes import products_bp
    from .users.routes import users_bp

    blueprints = (
        auth_bp,
        company_bp,
        customers_bp,
        dashboard_bp,
        miniapp_bp,
        products_bp,
        news_bp,
        users_bp,
    )
    for blueprint in blueprints:
        app.register_blueprint(blueprint)
