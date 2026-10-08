"""微信小程序认证与用户数据模式。"""

from marshmallow import Schema, fields, validate


class PhoneLoginSchema(Schema):
    """校验手机号授权登录所需的两个临时凭证。"""

    phone_code = fields.String(
        data_key="phoneCode",
        required=True,
        validate=validate.Length(min=1, max=256),
    )
    login_code = fields.String(
        data_key="loginCode",
        required=True,
        validate=validate.Length(min=1, max=256),
    )


class MiniAppProfileSchema(Schema):
    """序列化返回给小程序的当前用户资料。"""

    id = fields.Integer(dump_only=True)
    nickname = fields.String()
    avatar_url = fields.String(data_key="avatarUrl")
    phone_number = fields.String(data_key="phoneNumber")
    logged_in = fields.Constant(True, data_key="loggedIn")


class MiniAppProfileUpdateSchema(Schema):
    """校验小程序用户主动填写的资料。"""

    nickname = fields.String(
        required=True,
        validate=validate.Length(min=1, max=64),
    )


class MiniAppAdminUserSchema(Schema):
    """序列化后台管理端的小程序用户记录。"""

    id = fields.Integer(dump_only=True)
    key = fields.Integer(attribute="id", dump_only=True)
    openid = fields.String()
    unionid = fields.String(allow_none=True)
    nickname = fields.String()
    avatar_url = fields.String(data_key="avatarUrl")
    phone_number = fields.String(data_key="phoneNumber")
    country_code = fields.String(data_key="countryCode")
    login_count = fields.Integer(data_key="loginCount")
    last_login = fields.DateTime(
        data_key="lastLogin",
        format="%Y-%m-%d %H:%M",
        allow_none=True,
    )
    create_time = fields.DateTime(data_key="createTime", format="%Y-%m-%d %H:%M")
    status = fields.Method(serialize="get_status")

    def get_status(self, user) -> str:
        """将启用状态转换为后台展示文本。"""
        return "启用" if user.is_active else "停用"