"""可复用的 CRUD 服务与路由注册。"""

from typing import Any

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import Schema
from sqlalchemy import or_

from app.common.exception import BusinessError
from app.common.extensions import db
from app.common.response import success
from app.models.base_model import BaseModel


class CrudService:
    """为单个模型类型提供带校验的 CRUD 操作。"""

    def __init__(
        self,
        model: type[BaseModel],
        schema: Schema,
        search_fields: tuple[str, ...] = (),
        filter_fields: tuple[str, ...] = (),
    ) -> None:
        """配置模型、数据模式以及允许查询的字段。"""
        self.model = model
        self.schema = schema
        self.search_fields = search_fields
        self.filter_fields = filter_fields

    def list(self, args: dict[str, Any]) -> dict:
        """返回经过筛选和分页的记录集合。"""
        page = max(int(args.get("page", 1)), 1)
        per_page = min(max(int(args.get("pageSize", 20)), 1), 100)
        statement = db.select(self.model).where(self.model.is_deleted.is_(False))
        keyword = str(args.get("keyword", "")).strip()
        if keyword and self.search_fields:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(
                    *[
                        getattr(self.model, field).ilike(pattern)
                        for field in self.search_fields
                    ]
                )
            )
        for field in self.filter_fields:
            value = args.get(field)
            if value:
                statement = statement.where(getattr(self.model, field) == value)
        pagination = db.paginate(
            statement.order_by(self.model.id.desc()),
            page=page,
            per_page=per_page,
            error_out=False,
        )
        return {
            "items": self.schema.dump(pagination.items, many=True),
            "total": pagination.total,
            "page": pagination.page,
            "pageSize": pagination.per_page,
            "pages": pagination.pages,
        }

    def get(self, record_id: int) -> BaseModel:
        """根据标识符返回未删除的记录。"""
        record = db.session.get(self.model, record_id)
        if record is None or record.is_deleted:
            raise BusinessError("记录不存在", 404)
        return record

    def create(self, payload: dict[str, Any]) -> BaseModel:
        """校验数据并创建记录。"""
        data = self.schema.load(payload)
        record = self.model(**data)
        db.session.add(record)
        db.session.commit()
        return record

    def update(self, record_id: int, payload: dict[str, Any]) -> BaseModel:
        """校验数据并更新记录。"""
        record = self.get(record_id)
        data = self.schema.load(payload, partial=True)
        for key, value in data.items():
            setattr(record, key, value)
        db.session.commit()
        return record

    def delete(self, record_id: int) -> None:
        """软删除一条记录。"""
        record = self.get(record_id)
        record.soft_delete()
        db.session.commit()


def register_crud_routes(
    blueprint: Blueprint,
    path: str,
    endpoint: str,
    service: CrudService,
) -> None:
    """在蓝图上注册受 JWT 保护的标准 CRUD 路由。"""

    @jwt_required()
    def index():
        """列出记录。"""
        return success(service.list(request.args.to_dict()))

    @jwt_required()
    def detail(record_id: int):
        """返回单条记录。"""
        return success(service.schema.dump(service.get(record_id)))

    @jwt_required()
    def create():
        """创建一条记录。"""
        record = service.create(request.get_json(silent=True) or {})
        return success(service.schema.dump(record), "创建成功", 201)

    @jwt_required()
    def update(record_id: int):
        """更新一条记录。"""
        record = service.update(record_id, request.get_json(silent=True) or {})
        return success(service.schema.dump(record), "更新成功")

    @jwt_required()
    def delete(record_id: int):
        """软删除一条记录。"""
        service.delete(record_id)
        return success(message="删除成功")

    blueprint.add_url_rule(path, f"{endpoint}_index", index, methods=["GET"])
    blueprint.add_url_rule(
        f"{path}/<int:record_id>",
        f"{endpoint}_detail",
        detail,
        methods=["GET"],
    )
    blueprint.add_url_rule(path, f"{endpoint}_create", create, methods=["POST"])
    blueprint.add_url_rule(
        f"{path}/<int:record_id>",
        f"{endpoint}_update",
        update,
        methods=["PUT", "PATCH"],
    )
    blueprint.add_url_rule(
        f"{path}/<int:record_id>",
        f"{endpoint}_delete",
        delete,
        methods=["DELETE"],
    )
