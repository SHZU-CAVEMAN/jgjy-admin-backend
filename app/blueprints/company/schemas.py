"""企业信息数据模式。"""

from marshmallow import Schema, fields, validate


class HonorSchema(Schema):
    """校验并序列化企业荣誉。"""

    id = fields.Integer(dump_only=True)
    key = fields.Integer(attribute="id", dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=128))
    issuer = fields.String(required=True, validate=validate.Length(min=1, max=128))
    year = fields.Integer(required=True, validate=validate.Range(min=1900, max=2200))
    status = fields.String(
        load_default="展示中",
        validate=validate.OneOf(["展示中", "已下架"]),
    )


class CompanyProfileSchema(Schema):
    """校验并序列化企业资料设置。"""

    name = fields.String(required=True, validate=validate.Length(min=1, max=128))
    scale = fields.String(required=True, validate=validate.Length(min=1))
    description = fields.String(required=True, validate=validate.Length(min=1))
    homepage = fields.Boolean(required=True)


class CompanyContactSchema(Schema):
    """校验并序列化企业联系方式设置。"""

    address = fields.String(required=True, validate=validate.Length(min=1, max=255))
    phone = fields.String(required=True, validate=validate.Length(min=1, max=32))
    service_phone = fields.String(
        data_key="servicePhone",
        required=True,
        validate=validate.Length(min=1, max=32),
    )
    email = fields.Email(required=True)


class CompanyInfoSchema(CompanyProfileSchema, CompanyContactSchema):
    """校验并序列化完整企业信息。"""
