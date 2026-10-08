"""产品业务域数据库模型。"""

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel


class ProductCategory(BaseModel):
    """表示产品分类。"""

    __tablename__ = "t_product_category"

    name: Mapped[str] = mapped_column(String(64))
    sort: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="启用")


class Product(BaseModel):
    """表示向客户展示的产品。"""

    __tablename__ = "t_product_item"

    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    spec: Mapped[str] = mapped_column(String(64))
    price: Mapped[str] = mapped_column(String(32))
    year: Mapped[str] = mapped_column(String(32), default="")
    description: Mapped[str] = mapped_column(String(512), default="")
    tank: Mapped[str] = mapped_column(String(64), default="")
    tank_code: Mapped[str] = mapped_column(String(64), default="")
    tons: Mapped[int] = mapped_column(Integer, default=0)
    fill: Mapped[int] = mapped_column(Integer, default=0)
    zone: Mapped[str] = mapped_column(String(64), default="")
    image_original_url: Mapped[str] = mapped_column(String(512), default="")
    thumbnail_url: Mapped[str] = mapped_column(String(512), default="")
    detail_image_url: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(16), default="上架")


class TraceabilityBatch(BaseModel):
    """表示一个产品溯源批次。"""

    __tablename__ = "t_product_traceability"

    batch: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    product: Mapped[str] = mapped_column(String(128))
    production_date: Mapped[date] = mapped_column(Date)
    codes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="待生成")
