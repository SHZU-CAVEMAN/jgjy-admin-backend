"""新闻业务域数据模式。"""

from marshmallow import Schema, fields, validate


class KeyedSchema(Schema):
    """以后台和前端所需形式公开数据库标识符。"""

    id = fields.Integer(dump_only=True)
    key = fields.Integer(attribute="id", dump_only=True)


class PullSettingSchema(Schema):
    """校验公众号同步设置。"""

    account = fields.String(required=True, validate=validate.Length(min=1, max=128))
    count = fields.Integer(required=True, validate=validate.Range(min=1, max=100))
    time = fields.String(
        required=True,
        validate=validate.Regexp(r"^(?:[01]\d|2[0-3]):[0-5]\d$"),
    )
    enabled = fields.Boolean(required=True)


class NewsCategorySchema(KeyedSchema):
    """校验并序列化推文分类。"""

    name = fields.String(required=True, validate=validate.Length(min=1, max=64))
    count = fields.Integer(dump_only=True)
    updated = fields.Date(dump_only=True)
    status = fields.String(
        load_default="启用",
        validate=validate.OneOf(["启用", "停用"]),
    )


class ArticleSchema(KeyedSchema):
    """校验并序列化推文。"""

    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    category = fields.String(required=True, validate=validate.Length(min=1, max=64))
    author = fields.String(required=True, validate=validate.Length(min=1, max=64))
    published_at = fields.DateTime(
        data_key="time",
        format="%Y-%m-%d %H:%M",
        allow_none=True,
        load_default=None,
    )
    status = fields.String(
        load_default="草稿",
        validate=validate.OneOf(["草稿", "已发布"]),
    )


class WechatDraftSchema(KeyedSchema):
    """序列化微信公众号草稿摘要和正文。"""

    media_id = fields.String(data_key="mediaId")
    title = fields.String()
    author = fields.String()
    category_id = fields.Integer(data_key="categoryId", allow_none=True)
    category = fields.Method("get_category_name", dump_only=True)
    status = fields.String(validate=validate.OneOf(["草稿", "已发布"]))
    digest = fields.String()
    thumbnail_url = fields.String(data_key="thumbnailUrl")
    draft_created_at = fields.DateTime(
        data_key="createdAt", format="%Y-%m-%d %H:%M", allow_none=True
    )
    draft_updated_at = fields.DateTime(
        data_key="updatedAt", format="%Y-%m-%d %H:%M", allow_none=True
    )
    content_synced_at = fields.DateTime(
        data_key="contentSyncedAt", format="%Y-%m-%d %H:%M", allow_none=True
    )

    @staticmethod
    def get_category_name(draft):
        """返回关联分类的当前名称。"""
        return draft.news_category.name if draft.news_category else None


class WechatDraftUpdateSchema(Schema):
    """校验本地微信公众号草稿可编辑信息。"""

    title = fields.String(validate=validate.Length(min=1, max=255))
    author = fields.String(validate=validate.Length(max=128))
    category_id = fields.Integer(data_key="categoryId", allow_none=True)
    status = fields.String(validate=validate.OneOf(["草稿", "已发布"]))
    digest = fields.String(validate=validate.Length(max=65535))


class InteractionSchema(KeyedSchema):
    """校验并序列化推文互动。"""

    user = fields.String(required=True, validate=validate.Length(min=1, max=128))
    article = fields.String(required=True, validate=validate.Length(min=1, max=255))
    type = fields.String(
        required=True,
        validate=validate.OneOf(["点赞", "收藏", "转发", "留言"]),
    )
    interacted_at = fields.DateTime(
        data_key="time",
        format="%Y-%m-%d %H:%M",
        required=True,
    )
    comment = fields.String(load_default="-")
