"""共享的 Flask 扩展实例。"""

from flask import request
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class ModelBase(DeclarativeBase):
    """提供 SQLAlchemy 声明式基类。"""


db = SQLAlchemy(model_class=ModelBase)
jwt = JWTManager()


def configure_jwt_handlers() -> None:
    """配置 JWT 错误，使其使用统一响应结构。"""
    from app.common.response import error

    @jwt.unauthorized_loader
    def unauthorized(reason: str):
        """处理缺少有效认证请求头的请求。"""
        return error(reason, 401)

    @jwt.invalid_token_loader
    def invalid_token(reason: str):
        """处理格式错误或签名无效的令牌。"""
        return error(reason, 401)

    @jwt.expired_token_loader
    def expired_token(_header: dict, _payload: dict):
        """处理已过期的 JWT 令牌。"""
        return error("登录凭证已过期", 401)

    @jwt.revoked_token_loader
    def revoked_token(_header: dict, _payload: dict):
        """处理已撤销的 JWT 令牌。"""
        return error("登录凭证已失效", 401)

    @jwt.token_verification_loader
    def verify_user_type(_header: dict, payload: dict) -> bool:
        """隔离管理后台与小程序的登录凭证。"""
        expected = "miniapp" if request.path.startswith("/api/miniapp/") else "admin"
        return payload.get("user_type") == expected

    @jwt.token_verification_failed_loader
    def invalid_user_type(_header: dict, _payload: dict):
        """拒绝在错误客户端使用的登录凭证。"""
        return error("登录凭证类型不匹配", 401)
