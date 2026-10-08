"""用户管理 HTTP 路由。"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.auth.schemas import UserSchema
from app.common.response import success

from .services import create_user, delete_user, list_users, update_user

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.get("", strict_slashes=False)
@jwt_required()
def users_index():
    """列出后台用户。"""
    return success(
        list_users(
            request.args.get("keyword", "").strip(),
            request.args.get("page", 1, type=int),
            request.args.get("pageSize", 20, type=int),
        )
    )


@users_bp.post("", strict_slashes=False)
@jwt_required()
def users_create():
    """创建后台用户。"""
    user = create_user(request.get_json(silent=True) or {})
    return success(UserSchema().dump(user), "创建成功", 201)


@users_bp.route("/<int:user_id>", methods=["PUT", "PATCH"])
@jwt_required()
def users_update(user_id: int):
    """更新后台用户。"""
    user = update_user(user_id, request.get_json(silent=True) or {})
    return success(UserSchema().dump(user), "更新成功")


@users_bp.delete("/<int:user_id>")
@jwt_required()
def users_delete(user_id: int):
    """软删除后台用户。"""
    delete_user(user_id, int(get_jwt_identity()))
    return success(message="删除成功")
