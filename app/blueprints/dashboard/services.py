"""数据看板聚合服务。"""

import json
from datetime import date, datetime, time, timedelta

from sqlalchemy import func

from app.blueprints.customers.models import CustomerNeed, Favorite
from app.blueprints.customers.schemas import CustomerNeedSchema
from app.blueprints.news.models import Interaction
from app.common.extensions import db
from app.common.redis_client import get_redis, prefixed_key

CACHE_TTL_SECONDS = 60


def get_dashboard_summary() -> dict:
    """返回数据看板指标、趋势、分类和最新需求。"""
    cache_key = prefixed_key("dashboard", "summary")
    try:
        cached = get_redis().get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        cached = None

    summary = _build_summary()
    try:
        get_redis().setex(
            cache_key,
            CACHE_TTL_SECONDS,
            json.dumps(summary, ensure_ascii=False),
        )
    except Exception:
        pass
    return summary


def _build_summary() -> dict:
    """根据当前数据库记录聚合数据看板信息。"""
    total_needs = _count(CustomerNeed)
    pending_needs = _count(CustomerNeed, CustomerNeed.status == "待处理")
    total_favorites = _count(Favorite)
    total_interactions = _count(Interaction)
    today = date.today()

    trend = []
    for days_ago in range(6, -1, -1):
        current_date = today - timedelta(days=days_ago)
        start = datetime.combine(current_date, time.min)
        end = start + timedelta(days=1)
        count = _count(
            CustomerNeed,
            CustomerNeed.submitted_at >= start,
            CustomerNeed.submitted_at < end,
        )
        trend.append({"date": current_date.strftime("%m.%d"), "value": count})

    category_rows = db.session.execute(
        db.select(CustomerNeed.category, func.count(CustomerNeed.id))
        .where(CustomerNeed.is_deleted.is_(False))
        .group_by(CustomerNeed.category)
        .order_by(func.count(CustomerNeed.id).desc())
    ).all()
    categories = [
        {
            "name": category,
            "value": count,
            "percentage": round(count * 100 / total_needs, 1) if total_needs else 0,
        }
        for category, count in category_rows
    ]
    recent = db.session.scalars(
        db.select(CustomerNeed)
        .where(CustomerNeed.is_deleted.is_(False))
        .order_by(CustomerNeed.submitted_at.desc())
        .limit(5)
    ).all()
    return {
        "totalNeeds": total_needs,
        "stats": [
            _stat("客户需求总量", total_needs, "#2474f5"),
            _stat("待处理需求", pending_needs, "#f59e0b"),
            _stat("内容收藏总量", total_favorites, "#16a085"),
            _stat("推文互动总量", total_interactions, "#e65b81"),
        ],
        "trend": trend,
        "categories": categories,
        "latestNeeds": CustomerNeedSchema(many=True).dump(recent),
    }


def _count(model, *conditions) -> int:
    """统计符合可选条件且未删除的记录数。"""
    statement = db.select(func.count(model.id)).where(model.is_deleted.is_(False))
    if conditions:
        statement = statement.where(*conditions)
    return db.session.scalar(statement) or 0


def _stat(label: str, value: int, color: str) -> dict:
    """构建一项实时统计指标。"""
    return {
        "label": label,
        "value": f"{value:,}",
        "color": color,
    }
