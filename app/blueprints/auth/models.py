"""认证数据库模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.base_model import BaseModel


class AdminUser(BaseModel):
    """表示允许访问管理后台的用户。"""

    __tablename__ = "t_auth_user"

    name: Mapped[str] = mapped_column(String(64))
    account: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="内容编辑")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def set_password(self, password: str) -> None:
        """对明文密码进行哈希处理并保存。"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """校验明文密码是否与已保存的哈希匹配。"""
        return check_password_hash(self.password_hash, password)
