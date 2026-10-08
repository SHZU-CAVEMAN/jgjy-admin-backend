"""系统用户业务逻辑。"""

from sqlalchemy import or_

from app.blueprints.auth.models import AdminUser
from app.blueprints.auth.schemas import UserSchema
from app.common.exception import BusinessError
from app.common.extensions import db

from .schemas import AdminUserWriteSchema


def list_users(keyword: str, page: int, per_page: int) -> dict:
    """返回经过筛选的后台用户分页数据。"""
    statement = db.select(AdminUser).where(AdminUser.is_deleted.is_(False))
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(
            or_(AdminUser.name.ilike(pattern), AdminUser.account.ilike(pattern))
        )
    pagination = db.paginate(statement.order_by(AdminUser.id.desc()), page=page, per_page=per_page)
    return {
        "items": UserSchema(many=True).dump(pagination.items),
        "total": pagination.total,
        "page": pagination.page,
        "pageSize": pagination.per_page,
        "pages": pagination.pages,
    }


def create_user(payload: dict) -> AdminUser:
    """创建新的后台用户。

    异常：
        BusinessError：账号已存在。
    """
    data = AdminUserWriteSchema().load(payload)
    if "password" not in data:
        raise BusinessError("新增用户必须设置密码", 422)
    existing = db.session.scalar(
        db.select(AdminUser).where(AdminUser.account == data["account"])
    )
    if existing is not None:
        raise BusinessError("登录账号已存在", 409)
    password = data.pop("password")
    status = data.pop("status", "启用")
    user = AdminUser(**data, is_active=status == "启用")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def update_user(user_id: int, payload: dict) -> AdminUser:
    """更新现有后台用户。"""
    user = _get_user(user_id)
    data = AdminUserWriteSchema(partial=True).load(payload)
    duplicate = db.session.scalar(
        db.select(AdminUser).where(
            AdminUser.account == data.get("account"),
            AdminUser.id != user_id,
        )
    ) if data.get("account") else None
    if duplicate is not None:
        raise BusinessError("登录账号已存在", 409)
    password = data.pop("password", None)
    status = data.pop("status", None)
    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.set_password(password)
    if status:
        user.is_active = status == "启用"
    db.session.commit()
    return user


def delete_user(user_id: int, current_user_id: int) -> None:
    """软删除后台用户。

    异常：
        BusinessError：用户尝试删除自己的账号。
    """
    if user_id == current_user_id:
        raise BusinessError("不能删除当前登录账号")
    user = _get_user(user_id)
    user.soft_delete()
    db.session.commit()


def _get_user(user_id: int) -> AdminUser:
    """返回可用用户，不存在时抛出错误。"""
    user = db.session.get(AdminUser, user_id)
    if user is None or user.is_deleted:
        raise BusinessError("用户不存在", 404)
    return user
