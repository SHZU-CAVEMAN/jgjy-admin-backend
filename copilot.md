## 项目目录结构
project-root/
├── app/                      # 核心应用包
│   ├── __init__.py           # Flask应用工厂（create_app）
│   ├── config/               # 配置管理
│   │   ├── __init__.py
│   │   ├── base_config.py    # 公共配置（基类）
│   │   ├── dev_config.py     # 开发环境配置
│   │   └── prod_config.py    # 生产环境配置
│   ├── common/               # 公共工具/组件
│   │   ├── __init__.py
│   │   ├── extensions.py     # 所有Flask扩展实例化（db、jwt、redis）
│   │   ├── redis_client.py   # Redis连接池封装
│   │   ├── response.py       # 统一响应格式工具
│   │   ├── exception.py      # 全局异常/自定义业务异常
│   │   └── log.py            # 日志配置
│   ├── models/               # 全局SQLAlchemy模型（可选，也可放模块内）
│   │   ├── __init__.py
│   │   └── base_model.py     # 模型基类（公共字段：id、create_time、update_time、is_deleted）
│   └── blueprints/           # 业务模块（每个模块一个Blueprint）
│       ├── __init__.py
│       └── {module_name}/    # 示例：auth（认证模块）
│           ├── routes.py     # 定义Blueprint和路由，业务逻辑放service
│           ├── models.py     # 当前模块的SQLAlchemy模型
│           ├── schemas.py    # 请求/响应校验（marshmallow）
│           ├── services.py   # 业务逻辑层（核心逻辑放这里）
│           └── utils.py     # 模块专属工具
├── .env                      # 环境变量（敏感信息不硬编码）
├── requirements.txt          # 依赖列表（锁版本）
├── run.py                    # 启动入口（生产用gunicorn）
└── README.md                 # 项目说明

## 编码硬约束
Flask应用初始化：必须用「应用工厂模式」（create_app函数），根据ENV环境变量加载不同配置，所有扩展在extensions.py实例化、在工厂函数中绑定app。
Blueprint规范：
每个业务域独立Blueprint，命名格式{module}_bp（如auth_bp）
注册时强制加url_prefix（如/auth）
避免循环依赖：路由中只写逻辑分发，业务逻辑统一放services.py
SQLAlchemy规范：
所有模型继承BaseModel（提供公共字段：自增主键id、创建/更新时间、软删除标记）
表名必须显式声明__tablename__ = "t_{module}_{table}"（如t_auth_user）
禁止原生SQL直接拼串，用ORM原生方法（避免SQL注入）

Redis规范：
用redis.ConnectionPool实现连接复用，禁止每次新建连接
Key统一前缀格式：{project_name}:{module}:{key}（如jgjy:auth:token_xxx）
缓存必须设置过期时间，禁止无过期缓存
接口规范：
统一返回格式（强制用response.py的工具方法）：
json
{ "code": 200, "message": "success", "data": {...}, "timestamp": 1696000000 }
参数校验必须用marshmallow，禁止手动if判断
认证接口用Flask-JWT-Extended，装饰器@jwt_required()控制权限
全局异常拦截（覆盖HTTP异常、自定义业务异常、未知异常）

## 代码风格：
严格遵循PEP8规范，Python 3.10+用简洁类型注解（如list[str]）
每个函数必须写docstring（作用、参数、返回值、异常）
敏感信息（数据库密码、Redis密码、JWT密钥）必须从.env读取，禁止硬编