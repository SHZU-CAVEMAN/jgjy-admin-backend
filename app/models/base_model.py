"""SQLAlchemy 模型公共字段。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.common.extensions import db


class BaseModel(db.Model):
    """提供主键、时间戳和软删除字段。"""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    def soft_delete(self) -> None:
        """将记录标记为已删除，但不从数据库中移除。"""
        self.is_deleted = True
