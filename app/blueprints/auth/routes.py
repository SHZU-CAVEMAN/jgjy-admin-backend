"""认证 HTTP 路由。"""

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

from app.common.response import success

from .schemas import LoginSchema, UserSchema
from .services import authenticate, get_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    """认证后台用户。"""
    payload = LoginSchema().load(request.get_json(silent=True) or {})
    return success(authenticate(payload["account"], payload["password"]))


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """使用刷新令牌签发新的访问令牌。"""
    identity = get_jwt_identity()
    get_user(int(identity))
    return success(
        {
            "accessToken": create_access_token(
                identity=identity,
                additional_claims={"user_type": "admin"},
            )
        }
    )


@auth_bp.get("/me")
@jwt_required()
def me():
    """返回当前已认证用户。"""
    user = get_user(int(get_jwt_identity()))
    return success(UserSchema().dump(user))
