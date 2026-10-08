"""企业信息 HTTP 路由。"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.common.crud import register_crud_routes
from app.common.response import success

from .services import (
    contact_schema,
    get_company_info,
    honor_service,
    profile_schema,
    update_company_info,
)

company_bp = Blueprint("company", __name__, url_prefix="/api/company")

register_crud_routes(company_bp, "/honors", "honors", honor_service)


@company_bp.get("/profile")
@jwt_required()
def get_profile():
    """返回企业资料设置。"""
    return success(profile_schema().dump(get_company_info()))


@company_bp.put("/profile")
@jwt_required()
def put_profile():
    """替换企业资料设置。"""
    schema = profile_schema()
    info = update_company_info(request.get_json(silent=True) or {}, schema)
    return success(schema.dump(info), "保存成功")


@company_bp.get("/contact")
@jwt_required()
def get_contact():
    """返回企业联系方式设置。"""
    return success(contact_schema().dump(get_company_info()))


@company_bp.put("/contact")
@jwt_required()
def put_contact():
    """替换企业联系方式设置。"""
    schema = contact_schema()
    info = update_company_info(request.get_json(silent=True) or {}, schema)
    return success(schema.dump(info), "保存成功")
