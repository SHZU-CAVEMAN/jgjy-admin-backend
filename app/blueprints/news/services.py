"""新闻业务域服务。"""

from app.common.crud import CrudService
from app.common.extensions import db

from .models import Article, Interaction, NewsCategory, PullSetting
from .schemas import (
    ArticleSchema,
    InteractionSchema,
    NewsCategorySchema,
    PullSettingSchema,
)

category_service = CrudService(
    NewsCategory,
    NewsCategorySchema(),
    ("name",),
    ("status",),
)
article_service = CrudService(
    Article,
    ArticleSchema(),
    ("title", "category", "author"),
    ("status", "category"),
)
interaction_service = CrudService(
    Interaction,
    InteractionSchema(),
    ("user", "article", "comment"),
    ("type",),
)


def get_pull_setting() -> PullSetting:
    """返回单例拉取设置，不存在时自动创建。"""
    setting = db.session.scalar(
        db.select(PullSetting).where(PullSetting.is_deleted.is_(False))
    )
    if setting is None:
        setting = PullSetting()
        db.session.add(setting)
        db.session.commit()
    return setting


def update_pull_setting(payload: dict) -> PullSetting:
    """校验并替换公众号拉取设置。"""
    setting = get_pull_setting()
    data = PullSettingSchema().load(payload)
    for key, value in data.items():
        setattr(setting, key, value)
    db.session.commit()
    return setting
