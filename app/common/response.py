"""统一 JSON 响应辅助函数。"""

import time
from typing import Any

from flask import Response, jsonify


def success(
    data: Any = None,
    message: str = "success",
    status_code: int = 200,
) -> tuple[Response, int]:
    """返回成功的 API 响应。"""
    return jsonify(
        {
            "code": status_code,
            "message": message,
            "data": data,
            "timestamp": int(time.time()),
        }
    ), status_code


def error(
    message: str,
    status_code: int = 400,
    data: Any = None,
) -> tuple[Response, int]:
    """返回失败的 API 响应。"""
    return jsonify(
        {
            "code": status_code,
            "message": message,
            "data": data,
            "timestamp": int(time.time()),
        }
    ), status_code
