"""认证请求与响应数据模式。"""

from marshmallow import Schema, fields, validate


class LoginSchema(Schema):
    """校验后台登录凭据。"""

    account = fields.String(required=True, validate=validate.Length(min=1, max=64))
    password = fields.String(required=True, validate=validate.Length(min=6, max=128))


class UserSchema(Schema):
    """序列化已认证的后台用户。"""

    id = fields.Integer(dump_only=True)
    name = fields.String()
    account = fields.String()
    role = fields.String()
    status = fields.Method(serialize="get_status")
    lastLogin = fields.DateTime(attribute="last_login", format="%Y-%m-%d %H:%M")

    def get_status(self, user) -> str:
        """将启用标记映射为前端状态标签。"""
        return "启用" if user.is_active else "停用"
