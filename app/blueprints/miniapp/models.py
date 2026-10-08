"""微信小程序用户模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel


class MiniAppUser(BaseModel):
    """表示通过微信小程序登录的客户用户。"""

    __tablename__ = "t_miniapp_user"

    openid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    unionid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(32), index=True)
    country_code: Mapped[str] = mapped_column(String(8), default="86")
    nickname: Mapped[str] = mapped_column(String(64), default="微信用户")
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    login_count: Mapped[int] = mapped_column(Integer, default=0)