"""客户业务域数据模式。"""

from marshmallow import Schema, fields, validate


class KeyedSchema(Schema):
    """以后台和前端所需形式公开数据库标识符。"""

    id = fields.Integer(dump_only=True)
    key = fields.Integer(attribute="id", dump_only=True)


class NeedCategorySchema(KeyedSchema):
    """校验并序列化需求分类。"""

    name = fields.String(required=True, validate=validate.Length(min=1, max=64))
    sort = fields.Integer(load_default=1, validate=validate.Range(min=1))
    status = fields.String(
        load_default="启用",
        validate=validate.OneOf(["启用", "停用"]),
    )


class CustomerNeedSchema(KeyedSchema):
    """校验并序列化客户需求。"""

    miniapp_user_id = fields.Integer(data_key="miniappUserId", dump_only=True)
    openid = fields.Method(serialize="get_openid", dump_only=True)
    category_id = fields.Integer(data_key="categoryId", allow_none=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=128))
    phone = fields.String(load_default="", validate=validate.Length(max=32))
    category = fields.String(required=True, validate=validate.Length(min=1, max=64))
    method = fields.String(required=True, validate=validate.Length(min=1, max=32))
    region = fields.String(load_default="", validate=validate.Length(max=128))
    budget = fields.String(load_default="", validate=validate.Length(max=64))
    content = fields.String(data_key="remark", load_default="")
    submitted_at = fields.DateTime(
        data_key="time",
        format="%Y-%m-%d %H:%M",
        required=True,
    )
    status = fields.String(
        load_default="待处理",
        validate=validate.OneOf(["待处理", "跟进中", "已处理"]),
    )

    def get_openid(self, need) -> str:
        """返回关联小程序用户的 openid。"""
        return need.miniapp_user.openid if need.miniapp_user else ""


class ConsultationCreateSchema(Schema):
    """校验小程序提交的咨询需求。"""

    name = fields.String(required=True, validate=validate.Length(min=1, max=128))
    phone = fields.String(required=True, validate=validate.Regexp(r"^1\d{10}$"))
    category_id = fields.Integer(data_key="categoryId", required=True)
    region = fields.String(load_default="", validate=validate.Length(max=128))
    budget = fields.String(load_default="", validate=validate.Length(max=64))
    remark = fields.String(load_default="", validate=validate.Length(max=1000))


class ConsultationSchema(Schema):
    """序列化小程序用户自己的咨询记录。"""

    id = fields.Integer(dump_only=True)
    miniapp_user_id = fields.Integer(data_key="miniappUserId", dump_only=True)
    name = fields.String()
    phone = fields.String()
    category = fields.String(data_key="type")
    region = fields.String()
    budget = fields.String()
    content = fields.String(data_key="remark")
    submitted_at = fields.DateTime(data_key="date", format="%Y-%m-%d %H:%M")
    status = fields.String()


class FavoriteSchema(KeyedSchema):
    """校验并序列化客户收藏。"""

    miniapp_user_id = fields.Integer(data_key="miniappUserId", dump_only=True)
    target_id = fields.String(data_key="targetId", dump_only=True, allow_none=True)
    openid = fields.Method(serialize="get_openid", dump_only=True)
    phone_number = fields.Method(data_key="phoneNumber", serialize="get_phone_number", dump_only=True)
    customer = fields.String(required=True, validate=validate.Length(min=1, max=128))
    content = fields.String(required=True, validate=validate.Length(min=1, max=255))
    type = fields.String(required=True, validate=validate.OneOf(["产品", "推文"]))
    favorited_at = fields.DateTime(
        data_key="time",
        format="%Y-%m-%d %H:%M",
        required=True,
    )

    def get_openid(self, favorite) -> str:
        """返回关联小程序用户的 OpenID。"""
        return favorite.miniapp_user.openid if favorite.miniapp_user else ""

    def get_phone_number(self, favorite) -> str:
        """返回关联小程序用户手机号。"""
        return favorite.miniapp_user.phone_number if favorite.miniapp_user else ""


class FavoriteToggleSchema(Schema):
    """校验收藏目标。"""

    type = fields.String(required=True, validate=validate.OneOf(["产品", "推文"]))
    target_id = fields.String(
        data_key="targetId", required=True, validate=validate.Length(min=1, max=128)
    )


class CustomerSchema(KeyedSchema):
    """校验并序列化客户联系方式。"""

    company = fields.String(required=True, validate=validate.Length(min=1, max=128))
    contact = fields.String(required=True, validate=validate.Length(min=1, max=64))
    phone = fields.String(required=True, validate=validate.Length(min=1, max=32))
    needs = fields.Integer(load_default=0, validate=validate.Range(min=0))
    last_contact = fields.Date(data_key="lastContact", required=True)
