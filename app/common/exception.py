"""应用异常与全局错误处理器。"""

import logging

from flask import Flask
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from .response import error


class BusinessError(Exception):
    """表示预期内的业务规则错误。"""

    def __init__(self, message: str, status_code: int = 400) -> None:
        """初始化业务错误。"""
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_error_handlers(app: Flask) -> None:
    """为所有应用错误注册统一处理器。"""

    @app.errorhandler(BusinessError)
    def handle_business_error(exc: BusinessError):
        """将业务异常转换为 JSON 响应。"""
        return error(exc.message, exc.status_code)

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        """将 Marshmallow 校验错误转换为 JSON 响应。"""
        return error("请求参数校验失败", 422, exc.messages)

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        """将 Werkzeug HTTP 异常转换为 JSON 响应。"""
        return error(exc.description, exc.code or 500)

    @app.errorhandler(Exception)
    def handle_unknown_error(exc: Exception):
        """记录并隐藏未预期的服务器错误。"""
        app.logger.exception("Unhandled application error", exc_info=exc)
        return error("服务器内部错误", 500)

    from flask_jwt_extended.exceptions import JWTExtendedException

    @app.errorhandler(JWTExtendedException)
    def handle_jwt_error(exc: JWTExtendedException):
        """将 JWT 错误转换为 JSON 响应。"""
        return error(str(exc), 401)

    logging.getLogger("werkzeug").setLevel(logging.INFO)
