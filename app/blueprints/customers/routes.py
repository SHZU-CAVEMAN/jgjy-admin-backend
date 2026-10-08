"""客户业务域 HTTP 路由。"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.blueprints.miniapp.services import list_miniapp_users
from app.common.crud import register_crud_routes
from app.common.response import success

from .services import (
	customer_service,
	favorite_service,
	need_category_service,
	need_service,
)

customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")

register_crud_routes(customers_bp, "/needs", "needs", need_service)
register_crud_routes(
	customers_bp,
	"/need-categories",
	"need_categories",
	need_category_service,
)
register_crud_routes(customers_bp, "/favorites", "favorites", favorite_service)
register_crud_routes(customers_bp, "/info", "customer_info", customer_service)


@customers_bp.get("/miniapp-users")
@jwt_required()
def miniapp_users_index():
	"""返回小程序登录用户统计列表。"""
	return success(list_miniapp_users(request.args.to_dict()))
