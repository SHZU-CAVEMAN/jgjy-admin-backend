"""新闻业务域数据库模型。"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class PullSetting(BaseModel):
    """存储公众号同步设置。"""

    __tablename__ = "t_news_pull_setting"

    account: Mapped[str] = mapped_column(String(128), default="")
    count: Mapped[int] = mapped_column(Integer, default=20)
    time: Mapped[str] = mapped_column(String(5), default="02:00")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class NewsCategory(BaseModel):
    """表示推文分类。"""

    __tablename__ = "t_news_category"

    name: Mapped[str] = mapped_column(String(64))
    count: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String(16), default="启用")


class Article(BaseModel):
    """表示公众号推文。"""

    __tablename__ = "t_news_article"

    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    author: Mapped[str] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="草稿")


class WechatDraft(BaseModel):
    """缓存从微信公众号草稿箱同步的草稿。"""

    __tablename__ = "t_wechat_draft"

    media_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    author: Mapped[str] = mapped_column(String(128), default="")
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("t_news_category.id"), nullable=True
    )
    news_category: Mapped[NewsCategory | None] = relationship()
    status: Mapped[str] = mapped_column(String(16), default="草稿")
    digest: Mapped[str] = mapped_column(Text, default="")
    thumbnail_url: Mapped[str] = mapped_column(String(1024), default="")
    draft_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    draft_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    articles_json: Mapped[str] = mapped_column(Text, default="[]")
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Interaction(BaseModel):
    """表示客户与推文之间的互动。"""

    __tablename__ = "t_news_interaction"

    miniapp_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("t_miniapp_user.id"), nullable=True, index=True
    )
    user: Mapped[str] = mapped_column(String(128))
    article: Mapped[str] = mapped_column(String(255))
    article_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    type: Mapped[str] = mapped_column(String(16))
    interacted_at: Mapped[datetime] = mapped_column(DateTime)
    comment: Mapped[str] = mapped_column(Text, default="-")
    miniapp_user = relationship("MiniAppUser", lazy="joined")
