"""产品业务域数据模式。"""

from marshmallow import Schema, fields, validate


class KeyedSchema(Schema):
    """以后台和前端所需形式公开数据库标识符。"""

    id = fields.Integer(dump_only=True)
    key = fields.Integer(attribute="id", dump_only=True)


class ProductCategorySchema(KeyedSchema):
    """校验并序列化产品分类。"""

    name = fields.String(required=True, validate=validate.Length(min=1, max=64))
    sort = fields.Integer(load_default=1, validate=validate.Range(min=1))
    status = fields.String(
        load_default="启用",
        validate=validate.OneOf(["启用", "停用"]),
    )


class StockSchema(KeyedSchema):
    """校验并序列化库存记录。"""

    category = fields.String(allow_none=True, load_default=None, validate=validate.Length(max=64))
    name = fields.String(allow_none=True, load_default=None, validate=validate.Length(max=64))
    code = fields.String(allow_none=True, load_default=None, validate=validate.Length(max=64))
    zone = fields.String(allow_none=True, load_default=None, validate=validate.Length(max=64))
    tons = fields.Float(allow_none=True, load_default=None)
    alcohol = fields.String(allow_none=True, load_default=None, validate=validate.Length(max=16))
    year = fields.String(allow_none=True, load_default=None, validate=validate.Length(max=32))
    stocked_at = fields.Date(data_key="stockedAt", allow_none=True, load_default=None)
    status = fields.String(allow_none=True, load_default=None, validate=validate.Length(max=16))
    remark = fields.String(allow_none=True, load_default=None, validate=validate.Length(max=255))


class ProductSchema(KeyedSchema):
    """校验并序列化产品。"""

    name = fields.String(required=True, validate=validate.Length(min=1, max=128))
    category = fields.String(required=True, validate=validate.Length(min=1, max=64))
    spec = fields.String(required=True, validate=validate.Length(min=1, max=64))
    price = fields.String(required=True, validate=validate.Length(min=1, max=32))
    year = fields.String(load_default="", validate=validate.Length(max=32))
    description = fields.String(load_default="", validate=validate.Length(max=512))
    stock_id = fields.Integer(data_key="stockId", allow_none=True, load_default=None)
    stock_name = fields.Method(data_key="stockName", serialize="get_stock_name", dump_only=True)
    image_original_url = fields.String(data_key="imageOriginalUrl", required=True, validate=validate.Length(max=512))
    thumbnail_url = fields.String(data_key="thumbnailUrl", required=True, validate=validate.Length(max=512))
    detail_image_url = fields.String(data_key="detailImageUrl", required=True, validate=validate.Length(max=512))
    status = fields.String(
        load_default="上架",
        validate=validate.OneOf(["上架", "下架"]),
    )

    def get_stock_name(self, product) -> str:
        """返回关联库存的罐体名称。"""
        return product.stock.name if product.stock and product.stock.name else ""


class TraceabilitySchema(KeyedSchema):
    """校验并序列化溯源批次。"""

    batch = fields.String(required=True, validate=validate.Length(min=1, max=64))
    product = fields.String(required=True, validate=validate.Length(min=1, max=128))
    production_date = fields.Date(data_key="date", required=True)
    codes = fields.Integer(load_default=0, validate=validate.Range(min=0))
    status = fields.String(
        load_default="待生成",
        validate=validate.OneOf(["待生成", "已生成"]),
    )
