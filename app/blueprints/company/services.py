"""企业信息业务逻辑。"""

from marshmallow import Schema

from app.common.crud import CrudService
from app.common.extensions import db

from .models import CompanyInfo, Honor
from .schemas import (
    CompanyContactSchema,
    CompanyInfoSchema,
    CompanyProfileSchema,
    HonorSchema,
)

honor_service = CrudService(Honor, HonorSchema(), ("name", "issuer"), ("status",))


def get_company_info() -> CompanyInfo:
    """返回单例企业设置记录，不存在时自动创建。"""
    info = db.session.scalar(
        db.select(CompanyInfo).where(CompanyInfo.is_deleted.is_(False))
    )
    if info is None:
        info = CompanyInfo()
        db.session.add(info)
        db.session.commit()
    return info


def update_company_info(payload: dict, schema: Schema) -> CompanyInfo:
    """校验并更新企业设置中的指定部分。"""
    info = get_company_info()
    data = schema.load(payload)
    for key, value in data.items():
        setattr(info, key, value)
    db.session.commit()
    return info


def profile_schema() -> CompanyProfileSchema:
    """返回企业资料数据模式。"""
    return CompanyProfileSchema()


def contact_schema() -> CompanyContactSchema:
    """返回企业联系方式数据模式。"""
    return CompanyContactSchema()


def info_schema() -> CompanyInfoSchema:
    """返回完整企业信息数据模式。"""
    return CompanyInfoSchema()
