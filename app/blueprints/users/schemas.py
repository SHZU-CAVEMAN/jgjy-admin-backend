"""系统用户数据模式。"""

from marshmallow import Schema, fields, validate


class AdminUserWriteSchema(Schema):
    """校验后台用户的创建和更新数据。"""

    name = fields.String(required=True, validate=validate.Length(min=1, max=64))
    account = fields.String(required=True, validate=validate.Length(min=3, max=64))
    password = fields.String(load_only=True, validate=validate.Length(min=6, max=128))
    role = fields.String(required=True, validate=validate.Length(min=1, max=32))
    status = fields.String(validate=validate.OneOf(["启用", "停用"]))
