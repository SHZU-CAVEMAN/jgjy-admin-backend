"""客户业务域数据库模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class NeedCategory(BaseModel):
    """表示小程序和后台共用的需求分类。"""

    __tablename__ = "t_customer_need_category"

    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sort: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="启用")


class CustomerNeed(BaseModel):
    """表示客户提交的需求。"""

    __tablename__ = "t_customer_need"

    miniapp_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("t_miniapp_user.id"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("t_customer_need_category.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str] = mapped_column(String(32), default="")
    category: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(String(32))
    region: Mapped[str] = mapped_column(String(128), default="")
    budget: Mapped[str] = mapped_column(String(64), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="待处理")

    miniapp_user = relationship("MiniAppUser", lazy="joined")
    need_category = relationship("NeedCategory", lazy="joined")


class Favorite(BaseModel):
    """表示客户收藏的内容。"""

    __tablename__ = "t_customer_favorite"

    miniapp_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("t_miniapp_user.id"), nullable=True, index=True
    )
    customer: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    favorited_at: Mapped[datetime] = mapped_column(DateTime)
    miniapp_user = relationship("MiniAppUser", lazy="joined")


class Customer(BaseModel):
    """表示客户联系记录。"""

    __tablename__ = "t_customer_info"

    company: Mapped[str] = mapped_column(String(128))
    contact: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(32))
    needs: Mapped[int] = mapped_column(Integer, default=0)
    last_contact: Mapped[date] = mapped_column(Date)
