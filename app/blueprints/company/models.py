"""企业信息数据库模型。"""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel


class Honor(BaseModel):
    """表示企业荣誉墙中展示的荣誉。"""

    __tablename__ = "t_company_honor"

    name: Mapped[str] = mapped_column(String(128))
    issuer: Mapped[str] = mapped_column(String(128))
    year: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="展示中")


class CompanyInfo(BaseModel):
    """存储单例企业资料与联系方式设置。"""

    __tablename__ = "t_company_info"

    name: Mapped[str] = mapped_column(String(128), default="")
    scale: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    homepage: Mapped[bool] = mapped_column(Boolean, default=True)
    address: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    service_phone: Mapped[str] = mapped_column(String(32), default="")
    email: Mapped[str] = mapped_column(String(128), default="")
