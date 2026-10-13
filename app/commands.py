"""应用管理命令。"""

import os
import secrets
import time
from datetime import date, datetime

import click
from flask import Flask
from sqlalchemy import inspect, text

from app.blueprints.auth.models import AdminUser
from app.blueprints.company.models import CompanyInfo, Honor
from app.blueprints.customers.models import Customer, CustomerNeed, Favorite, NeedCategory
from app.blueprints.news.models import (
    Article,
    Interaction,
    NewsCategory,
    PullSetting,
    WechatDraft,
)
from app.blueprints.products.models import Product, ProductCategory, TraceabilityBatch
from app.common.extensions import db


def register_commands(app: Flask) -> None:
    """在 Flask 应用上注册数据库管理命令。"""

    @app.cli.command("init-db")
    @click.option("--seed/--no-seed", default=True, help="Load initial demo data.")
    def init_db(seed: bool) -> None:
        """创建本地数据表，并按需载入初始数据。"""
        db.create_all()
        if seed:
            seed_database()
        click.echo("Database initialized.")

    @app.cli.command("upgrade-news-draft-schema")
    # 为已有草稿表补齐后台编辑需要的字段
    def upgrade_news_draft_schema() -> None:
        columns = {
            column["name"] for column in inspect(db.engine).get_columns(WechatDraft.__tablename__)
        }
        additions = {
            "category": "VARCHAR(64)",
            "status": "VARCHAR(16) NOT NULL DEFAULT '草稿'",
        }
        missing_columns = [name for name in additions if name not in columns]
        if not missing_columns:
            click.echo("Wechat draft schema is already up to date.")
            return
        for name in missing_columns:
            db.session.execute(
                text(
                    f"ALTER TABLE {WechatDraft.__tablename__} "
                    f"ADD COLUMN {name} {additions[name]}"
                )
            )
        db.session.commit()
        click.echo(f"Wechat draft columns added: {', '.join(missing_columns)}.")

    @app.cli.command("upgrade-company-info-schema")
    def upgrade_company_info_schema() -> None:
        """将企业规模字段升级为长文本类型。"""
        columns = {
            column["name"]: column
            for column in inspect(db.engine).get_columns(CompanyInfo.__tablename__)
        }
        scale_column = columns.get("scale")
        if scale_column is None:
            click.echo("Company info table does not contain a scale column.", err=True)
            return
        if "TEXT" in str(scale_column["type"]).upper():
            click.echo("Company info schema is already up to date.")
            return
        if db.engine.dialect.name != "mysql":
            click.echo("The company info schema upgrade is supported for MySQL only.", err=True)
            return
        db.session.execute(
            text(f"ALTER TABLE {CompanyInfo.__tablename__} MODIFY COLUMN scale TEXT NOT NULL")
        )
        db.session.commit()
        click.echo("Company info scale column upgraded to TEXT.")

    @app.cli.command("sync-wechat-drafts")
    @click.option("--once", is_flag=True, help="Sync once and exit.")
    def sync_wechat_drafts(once: bool) -> None:
        """每五分钟同步一次微信公众号草稿箱。"""
        from app.blueprints.news.services import (
            get_pull_setting,
            sync_wechat_drafts as sync,
        )

        interval = app.config["WECHAT_DRAFT_SYNC_INTERVAL_SECONDS"]
        while True:
            try:
                if get_pull_setting().enabled:
                    result = sync()
                    click.echo(f"Synced {result['synced']} drafts.")
                else:
                    click.echo("Draft sync is disabled.")
            except Exception as exc:
                app.logger.exception("微信公众号草稿定时同步失败")
                click.echo(f"Draft sync failed: {exc}", err=True)
            if once:
                return
            time.sleep(interval)


def seed_database() -> None:
    """数据表为空时载入与前端兼容的初始记录。

    异常：
        RuntimeError：未配置初始管理员密码。
    """
    admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")
    if not admin_password:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD is required for database seeding")

    if db.session.scalar(db.select(db.func.count(AdminUser.id))) == 0:
        admin = AdminUser(
            name="林经理",
            account="admin",
            role="超级管理员",
            is_active=True,
            last_login=datetime(2026, 9, 12, 9, 12),
        )
        admin.set_password(admin_password)
        users = [admin]
        for name, account, role, active in [
            ("周运营", "operator", "运营专员", True),
            ("陈编辑", "editor", "内容编辑", False),
        ]:
            user = AdminUser(name=name, account=account, role=role, is_active=active)
            user.set_password(secrets.token_urlsafe(32))
            users.append(user)
        db.session.add_all(users)

    _add_if_empty(
        Honor,
        [
            Honor(name="中国酒业协会会员单位", issuer="中国酒业协会", year=2025, status="展示中"),
            Honor(name="品质诚信企业", issuer="浙江省食品协会", year=2024, status="展示中"),
            Honor(name="年度创新品牌", issuer="行业品牌联盟", year=2023, status="已下架"),
        ],
    )
    _add_if_empty(
        CompanyInfo,
        [
            CompanyInfo(
                name="江南谷语酒业有限公司",
                scale="专注于传统酿造工艺与现代品牌运营",
                description="江南谷语，传承江南酿造文化，致力于为客户提供高品质白酒产品。",
                homepage=True,
                address="浙江省杭州市余杭区良渚文化村",
                phone="0571-8888 6688",
                service_phone="400-888-6688",
                email="service@jgjy.com",
            )
        ],
    )
    _seed_customers()
    _seed_products()
    _seed_news()
    db.session.commit()


def _seed_customers() -> None:
    """载入客户业务域的初始记录。"""
    _add_if_empty(
        NeedCategory,
        [
            NeedCategory(name="基酒采购", sort=1, status="启用"),
            NeedCategory(name="定制酒", sort=2, status="启用"),
            NeedCategory(name="储酒服务", sort=3, status="启用"),
            NeedCategory(name="封坛酒", sort=4, status="启用"),
            NeedCategory(name="贴牌代工", sort=5, status="启用"),
        ],
    )
    _add_if_empty(
        CustomerNeed,
        [
            CustomerNeed(name="杭州远景科技", category="产品咨询", method="官网表单", submitted_at=datetime(2026, 9, 12, 10, 24), status="待处理"),
            CustomerNeed(name="上海青禾食品", category="渠道合作", method="微信公众号", submitted_at=datetime(2026, 9, 12, 9, 48), status="已处理"),
            CustomerNeed(name="苏州新锐制造", category="定制需求", method="官网表单", submitted_at=datetime(2026, 9, 11, 16, 32), status="待处理"),
        ],
    )
    _add_if_empty(
        Favorite,
        [
            Favorite(customer="杭州远景科技", content="53度酱香型白酒", type="产品", favorited_at=datetime(2026, 9, 12, 8, 41)),
            Favorite(customer="上海青禾食品", content="江南酒文化的传承", type="推文", favorited_at=datetime(2026, 9, 11, 21, 3)),
            Favorite(customer="宁波丰禾商贸", content="商务定制系列", type="产品", favorited_at=datetime(2026, 9, 11, 16, 20)),
        ],
    )
    _add_if_empty(
        Customer,
        [
            Customer(company="杭州远景科技", contact="张伟", phone="138****2851", needs=4, last_contact=date(2026, 9, 12)),
            Customer(company="上海青禾食品", contact="李娜", phone="139****6218", needs=2, last_contact=date(2026, 9, 11)),
            Customer(company="苏州新锐制造", contact="王强", phone="137****9042", needs=1, last_contact=date(2026, 9, 9)),
        ],
    )


def _seed_products() -> None:
    """载入产品业务域的初始记录。"""
    _add_if_empty(
        ProductCategory,
        [
            ProductCategory(name="酱香白酒", sort=1, status="启用"),
            ProductCategory(name="浓香白酒", sort=2, status="启用"),
            ProductCategory(name="定制系列", sort=3, status="启用"),
        ],
    )
    _add_if_empty(
        Product,
        [
            Product(name="江南谷语·典藏", category="酱香白酒", spec="500ml / 瓶", price="¥ 699", status="上架"),
            Product(name="江南谷语·臻品", category="浓香白酒", spec="500ml / 瓶", price="¥ 399", status="上架"),
            Product(name="商务定制礼盒", category="定制系列", spec="6瓶 / 盒", price="¥ 1,299", status="下架"),
        ],
    )
    _add_if_empty(
        TraceabilityBatch,
        [
            TraceabilityBatch(batch="JGY-202609-001", product="江南谷语·典藏", production_date=date(2026, 9, 5), codes=1200, status="已生成"),
            TraceabilityBatch(batch="JGY-202608-004", product="江南谷语·臻品", production_date=date(2026, 8, 22), codes=800, status="已生成"),
            TraceabilityBatch(batch="JGY-202608-003", product="商务定制礼盒", production_date=date(2026, 8, 18), codes=600, status="待生成"),
        ],
    )


def _seed_news() -> None:
    """载入新闻业务域的初始记录。"""
    _add_if_empty(
        PullSetting,
        [PullSetting(account="江南谷语酒业", count=20, time="02:00", enabled=True)],
    )
    _add_if_empty(
        NewsCategory,
        [
            NewsCategory(name="品牌故事", count=18, updated=date(2026, 9, 12), status="启用"),
            NewsCategory(name="行业资讯", count=26, updated=date(2026, 9, 11), status="启用"),
            NewsCategory(name="品鉴知识", count=12, updated=date(2026, 9, 8), status="启用"),
        ],
    )
    _add_if_empty(
        Article,
        [
            Article(title="江南酒文化的传承与新生", category="品牌故事", author="陈编辑", published_at=datetime(2026, 9, 12, 8), status="已发布"),
            Article(title="如何品鉴一杯好酱酒", category="品鉴知识", author="陈编辑", published_at=datetime(2026, 9, 10, 8), status="已发布"),
            Article(title="秋季饮酒的温度与礼仪", category="行业资讯", author="周运营", published_at=None, status="草稿"),
        ],
    )
    _add_if_empty(
        Interaction,
        [
            Interaction(user="杭州远景科技", article="江南酒文化的传承与新生", type="收藏", interacted_at=datetime(2026, 9, 12, 9, 30), comment="-"),
            Interaction(user="上海青禾食品", article="如何品鉴一杯好酱酒", type="留言", interacted_at=datetime(2026, 9, 12, 8, 48), comment="内容很有帮助"),
            Interaction(user="宁波丰禾商贸", article="江南酒文化的传承与新生", type="点赞", interacted_at=datetime(2026, 9, 11, 19, 12), comment="-"),
        ],
    )


def _add_if_empty(model, records: list) -> None:
    """仅在模型数据表为空时添加记录。"""
    if db.session.scalar(db.select(db.func.count(model.id))) == 0:
        db.session.add_all(records)