# 江南谷语管理后台服务

基于 Flask 的管理后台 API，与 `jgjy-admin` 前端页面业务域对应。项目采用应用工厂、Blueprint、SQLAlchemy ORM、JWT、Marshmallow 和 Redis 连接池。

## 项目目录

```text
jgjy-admin-backend/
|-- app/
|   |-- __init__.py              # Flask 应用工厂及扩展、蓝图注册
|   |-- commands.py              # 数据库初始化和演示数据命令
|   |-- config/                  # 开发、生产环境配置
|   |-- common/                  # 扩展、响应、异常、CRUD、Redis、日志等公共能力
|   |-- models/
|   |   `-- base_model.py        # 模型公共基类和通用字段
|   `-- blueprints/              # 按业务域划分的 Blueprint
|       |-- auth/                # 登录、令牌和管理员认证
|       |-- users/               # 后台用户管理
|       |-- company/             # 企业资料和荣誉管理
|       |-- customers/           # 客户、需求和收藏管理
|       |-- miniapp/             # 微信小程序登录和用户
|       |-- products/            # 产品、分类和溯源管理
|       |-- news/                # 推文、分类、互动和拉取设置
|       `-- dashboard/           # 数据看板聚合接口
|-- scripts/
|   `-- image_processor.py       # 本地图片批量加提示、压缩及格式转换
|-- tests/                       # pytest 接口与业务测试
|-- instance/                    # 本地 SQLite 数据库等运行时文件
|-- .env                         # 本地环境变量，不提交版本库
|-- .env.example                 # 环境变量示例
|-- pytest.ini                   # pytest 配置
|-- requirements.txt             # Python 依赖及版本
|-- run.py                       # 应用启动入口
`-- README.md                    # 项目说明
```

业务 Blueprint 通常包含 `models.py`、`schemas.py`、`services.py` 和 `routes.py`。公共模型字段集中在 `app/models/base_model.py`，具体业务模型保留在所属业务域内，避免不同模块之间产生不必要的耦合。

## 环境要求

- Python 3.10+
- MySQL 8+
- Redis 6+（可选；微信 access_token 无法缓存时自动直连微信）

## 本地启动

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，至少替换 `SECRET_KEY`、`JWT_SECRET_KEY`、`INITIAL_ADMIN_PASSWORD` 和 `WECHAT_MINIAPP_SECRET`，然后初始化并启动：

```powershell
$env:FLASK_APP = "run.py"
flask init-db
flask run --host 0.0.0.0 --port 5000
```

默认账号为 `admin`，密码取自 `.env` 的 `INITIAL_ADMIN_PASSWORD`。

## 图片批处理

脚本会递归扫描本地输入目录，为每张图片的右下角添加“该图片有侵权风险”，并生成三种文件：

1. `original/`：保留源文件名、格式和分辨率的加提示图片。
2. `compressed/`：使用稳定的 32 位十六进制名称，保持源图片格式并压缩到 600 KB 以下。
3. `webp/`：与压缩图使用相同的 32 位名称，转换为 600 KB 以下的 WebP 图片。

基本用法：

```powershell
python scripts/image_processor.py "D:\待处理图片" "D:\处理结果"
```

输出结构示例：

```text
处理结果/
|-- original/
|   `-- 原文件名.png
|-- compressed/
|   `-- 6fc364b4e8082cdaea511d1d0fec14e0.png
`-- webp/
    `-- 6fc364b4e8082cdaea511d1d0fec14e0.webp
```

可选参数：

```powershell
python scripts/image_processor.py INPUT OUTPUT `
  --max-kb 600 `
  --text "该图片有侵权风险" `
  --font "C:\Windows\Fonts\msyh.ttc"
```

- 支持静态 JPG、JPEG、PNG、WebP、BMP、TIFF 图片。
- 默认自动查找 Windows 微软雅黑、黑体或宋体；其他系统找不到中文字体时需使用 `--font` 指定。
- “原图”指保留文件名、格式和分辨率，因写入了提示文字，文件内容不会与源文件完全相同。
- 压缩图若仅降低编码质量仍超过上限，会逐步缩小分辨率，直到不超过指定大小。
- 输出目录可以位于输入目录内，脚本会自动排除已生成文件，避免重复处理。

## 数据库

当前开发阶段使用 `flask init-db` 创建表并载入演示数据。模型结构变化时可删除本地 `instance/jgjy.db` 后重新初始化。生产环境通过 `DATABASE_URL` 配置 MySQL，例如：

```text
mysql+pymysql://user:password@127.0.0.1:3306/jgjy?charset=utf8mb4
```

## API 约定

所有响应格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": 1696000000
}
```

除登录和健康检查外，请求需携带 `Authorization: Bearer <accessToken>`。

| 业务 | 接口前缀或路径 |
| --- | --- |
| 登录、刷新、当前用户 | `/api/auth/login`、`/api/auth/refresh`、`/api/auth/me` |
| 数据看板 | `/api/dashboard/summary` |
| 后台用户 | `/api/users` |
| 荣誉、企业介绍、联系方式 | `/api/company/honors`、`/api/company/profile`、`/api/company/contact` |
| 需求、收藏、客户信息 | `/api/customers/needs`、`/api/customers/favorites`、`/api/customers/info` |
| 小程序用户统计 | `/api/customers/miniapp-users` |
| 小程序手机号登录、当前用户 | `/api/miniapp/auth/phone-login`、`/api/miniapp/auth/me` |
| 产品分类、产品、溯源 | `/api/products/categories`、`/api/products/list`、`/api/products/traceability` |
| 拉取设置、推文分类、推文、互动 | `/api/news/pull-settings`、`/api/news/categories`、`/api/news/articles`、`/api/news/interactions` |

CRUD 列表支持 `page`、`pageSize`、`keyword`，以及前端页面对应的 `status`、`method`、`type`、`category` 筛选参数。

管理后台与小程序使用不同类型的 JWT，令牌不能跨端调用。`WECHAT_MINIAPP_SECRET` 只允许保存在服务端环境变量中。

## 测试

```powershell
pytest
```