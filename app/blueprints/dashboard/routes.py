"""数据看板 HTTP 路由。"""

from flask import Blueprint
from flask_jwt_extended import jwt_required

from app.common.response import success

from .services import get_dashboard_summary

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/summary")
@jwt_required()
def summary():
    """返回完整的数据看板摘要。"""
    return success(get_dashboard_summary())
