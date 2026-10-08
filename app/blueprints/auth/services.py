"""认证业务逻辑。"""

from datetime import datetime

from flask_jwt_extended import create_access_token, create_refresh_token

from app.common.exception import BusinessError
from app.common.extensions import db

from .models import AdminUser
from .schemas import UserSchema

user_schema = UserSchema()


def authenticate(account: str, password: str) -> dict:
    """认证用户凭据并签发 JWT 令牌。

    参数：
        account：登录账号。
        password：客户端提交的明文密码。

    返回：
        JWT 令牌和序列化后的用户信息。

    异常：
        BusinessError：凭据无效或账号已停用。
    """
    user = db.session.scalar(
        db.select(AdminUser).where(
            AdminUser.account == account,
            AdminUser.is_deleted.is_(False),
        )
    )
    if user is None or not user.check_password(password):
        raise BusinessError("账号或密码错误", 401)
    if not user.is_active:
        raise BusinessError("账号已停用", 403)

    user.last_login = datetime.now()
    db.session.commit()
    identity = str(user.id)
    claims = {"user_type": "admin"}
    return {
        "accessToken": create_access_token(identity=identity, additional_claims=claims),
        "refreshToken": create_refresh_token(identity=identity, additional_claims=claims),
        "user": user_schema.dump(user),
    }


def get_user(user_id: int) -> AdminUser:
    """根据标识符加载启用状态的用户。

    异常：
        BusinessError：用户不存在或不可用。
    """
    user = db.session.get(AdminUser, user_id)
    if user is None or user.is_deleted or not user.is_active:
        raise BusinessError("用户不存在或已停用", 401)
    return user
