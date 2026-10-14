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

## 微信公众号草稿同步

在 `.env` 中配置 `WECHAT_OFFICIAL_ACCOUNT_APPID` 和
`WECHAT_OFFICIAL_ACCOUNT_SECRET` 后，启动独立轮询进程以每五分钟从允许访问的草稿箱接口同步最新草稿摘要。服务会自动获取微信公众号
`access_token`，并使用 Redis 缓存至其到期前五分钟：

```powershell
$env:FLASK_APP = "run.py"
flask sync-wechat-drafts
```

部署时该命令应以单实例常驻运行，避免多个 Web worker 重复请求微信接口。管理端的“立即拉取最新草稿”同样会同步并持久化草稿；首次预览某草稿时才会获取并保存正文。

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

已有数据库升级新闻草稿分类结构时，先备份数据库，再执行 `flask upgrade-news-draft-schema`。该命令会新增 `category_id` 外键，并按原分类名称回填草稿关联；旧的 `category` 文本列会保留，不再用于读写。

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
| 小程序收藏、咨询和留言 | `/api/miniapp/favorites`、`/api/miniapp/consultations`、`/api/miniapp/my-comments`、`/api/miniapp/news/{mediaId}/comments` |
| 产品分类、产品、溯源 | `/api/products/categories`、`/api/products/list`、`/api/products/traceability` |
| 拉取设置、推文分类、推文、互动 | `/api/news/pull-settings`、`/api/news/categories`、`/api/news/articles`、`/api/news/interactions` |

CRUD 列表支持 `page`、`pageSize`、`keyword`，以及前端页面对应的 `status`、`method`、`type`、`category` 筛选参数。

管理后台与小程序使用不同类型的 JWT，令牌不能跨端调用。`WECHAT_MINIAPP_SECRET` 只允许保存在服务端环境变量中。

部署升级小程序收藏、咨询和文章留言的用户关联字段时，先备份数据库，再在后端目录执行 `flask upgrade-miniapp-engagement-schema`。新产生的收藏、咨询和留言均通过登录用户 ID 关联；无法可靠识别所属用户的历史收藏/互动会保留为未关联记录。

## 测试

```powershell
pytest
```

## 宝塔服务器部署

本节部署管理端和 Flask 服务到同一个域名，例如 `admin.example.com`。Nginx
在 `/jgjy/` 提供管理端静态文件，并将 `/jgjy/api` 转发给本机 Gunicorn 的
`/api` 路由；前端保持默认的同域 API 地址，因此不需要在构建时设置
`VITE_API_BASE_URL`。

### 1. 前置条件

- 宝塔已安装并启动 Nginx、MySQL 8+、Redis 6+。
- 域名的 A 记录已指向服务器公网 IP；以下用 `admin.example.com` 代替实际域名。
- 服务器已安装 Git、Python 3.10+ 和 Node.js 20 LTS。Node.js 可通过宝塔的
  Node 项目管理器或 nvm 安装。
- 以下命令以有权限访问 `/www/wwwroot` 的用户执行。示例目录可按实际项目路径修改。

不要将 `.env`、虚拟环境、`node_modules` 或 `uploads` 提交到 Git 仓库。

### 2. 准备 MySQL 和 Redis

在宝塔的数据库管理页面创建数据库和专用账户，也可以通过 MySQL 控制台执行：

```sql
CREATE DATABASE jgjy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'jgjy'@'127.0.0.1' IDENTIFIED BY '替换为高强度数据库密码';
GRANT ALL PRIVILEGES ON jgjy.* TO 'jgjy'@'127.0.0.1';
FLUSH PRIVILEGES;
```

确认宝塔 Redis 服务已启动。若 Redis 启用了密码，在 `REDIS_URL` 中设置为
`redis://:密码@127.0.0.1:6379/0`。

### 3. 上传代码并安装后端依赖

将两个项目分别克隆或上传到服务器。以下示例假设前端和后端目录并列：

```bash
cd /www/wwwroot
git clone <后端仓库地址> jgjy-admin-backend
git clone <前端仓库地址> jgjy-admin-front

cd /www/wwwroot/jgjy-admin-backend
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt
```

创建 `/www/wwwroot/jgjy-admin-backend/.env`，不要直接使用示例中的密码：

```dotenv
ENV=production
SECRET_KEY=替换为openssl-rand-hex-32生成的随机值
JWT_SECRET_KEY=替换为另一份openssl-rand-hex-32生成的随机值
DATABASE_URL=mysql+pymysql://jgjy:数据库密码@127.0.0.1:3306/jgjy?charset=utf8mb4
REDIS_URL=redis://127.0.0.1:6379/0
FRONTEND_ORIGINS=https://admin.example.com
INITIAL_ADMIN_PASSWORD=替换为初始管理员高强度密码
WECHAT_MINIAPP_APPID=
WECHAT_MINIAPP_SECRET=
WECHAT_OFFICIAL_ACCOUNT_APPID=
WECHAT_OFFICIAL_ACCOUNT_SECRET=
```

可用以下命令生成密钥：

```bash
openssl rand -hex 32
```

首次部署时初始化数据表和初始管理员：

```bash
cd /www/wwwroot/jgjy-admin-backend
./.venv/bin/flask --app run:app init-db
```

已有生产数据库升级到包含推文草稿分类的版本时，执行一次幂等升级命令，而不是删除数据库：

```bash
./.venv/bin/flask --app run:app upgrade-news-draft-schema
```

### 4. 构建管理端

前端默认将 `/jgjy` 加到请求前缀，业务调用会形成 `/jgjy/api/...`，适配下方
Nginx 配置。构建前不要设置 `VITE_API_BASE_URL`；若服务器上存在该环境变量，
请先清除它。

```bash
cd /www/wwwroot/jgjy-admin-front
npm ci
npm run build
```

构建产物为 `/www/wwwroot/jgjy-admin-front/dist`。每次发布前端代码后，重新执行
`git pull`、`npm ci` 和 `npm run build`。

### 5. 配置 systemd 运行 Gunicorn

创建 `/etc/systemd/system/jgjy-admin-backend.service`：

```ini
[Unit]
Description=JGJY Admin Flask API
After=network.target

[Service]
Type=simple
User=www
Group=www
WorkingDirectory=/www/wwwroot/jgjy-admin-backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/www/wwwroot/jgjy-admin-backend/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 --timeout 60 run:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`www` 是宝塔 Nginx 常用运行用户；如果服务器实际用户不同，替换 `User` 和
`Group`。确保该用户对后端目录及其 `uploads` 子目录有读写权限：

```bash
chown -R www:www /www/wwwroot/jgjy-admin-backend
systemctl daemon-reload
systemctl enable --now jgjy-admin-backend
systemctl status jgjy-admin-backend --no-pager
curl http://127.0.0.1:5000/api/health
```

健康检查返回 HTTP 200 且 `database` 为 `ok` 后，再配置站点反向代理。

### 6. 配置宝塔 Nginx 站点

在宝塔“网站”中新建 `admin.example.com` 站点。在站点“配置文件”的对应 `server`
块中保留宝塔生成的 TLS 配置，并加入以下内容：

```nginx
client_max_body_size 20m;

location = /jgjy {
  return 301 /jgjy/;
}

location ^~ /jgjy/api/ {
  proxy_pass http://127.0.0.1:5000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 60s;
}

location ^~ /jgjy/ {
  alias /www/wwwroot/jgjy-admin-front/dist/;
  try_files $uri $uri/ /jgjy/index.html;
}
```

不要在同一站点同时添加“反向代理全部路径”规则，否则会覆盖前端静态文件。前端静态
资源路径为 `/jgjy/assets/...`，不会走接口代理。后端已经通过
`/api/products/images/...` 和 `/api/miniapp/avatars/...` 路由提供上传资源，无需额外
为 `uploads` 添加 Nginx `alias`。

在宝塔“SSL”页面申请并部署 Let's Encrypt 证书，开启“强制 HTTPS”，然后重载 Nginx：

```bash
nginx -t && systemctl reload nginx
```

### 7. 微信草稿同步进程

只有配置了公众号 AppID 和 AppSecret 时才需要运行同步进程。它必须保持单实例，避免
多个 Gunicorn worker 重复拉取微信草稿。创建
`/etc/systemd/system/jgjy-wechat-drafts.service`：

```ini
[Unit]
Description=JGJY WeChat Draft Synchronizer
After=network.target jgjy-admin-backend.service

[Service]
Type=simple
User=www
Group=www
WorkingDirectory=/www/wwwroot/jgjy-admin-backend
ExecStart=/www/wwwroot/jgjy-admin-backend/.venv/bin/flask --app run:app sync-wechat-drafts
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用命令：

```bash
systemctl daemon-reload
systemctl enable --now jgjy-wechat-drafts
```

### 8. 发布、验证与排错

后端发布顺序：拉取代码、安装依赖、执行必要的数据库升级，再重启服务：

```bash
cd /www/wwwroot/jgjy-admin-backend
git pull
./.venv/bin/pip install -r requirements.txt
./.venv/bin/flask --app run:app upgrade-news-draft-schema
systemctl restart jgjy-admin-backend
```

常用检查命令：

```bash
systemctl status jgjy-admin-backend --no-pager
journalctl -u jgjy-admin-backend -n 100 --no-pager
curl -i http://127.0.0.1:5000/api/health
nginx -t
```

若登录后接口返回跨域错误，检查 `.env` 的 `FRONTEND_ORIGINS` 是否与浏览器地址完全
一致（包含 `https://`，不包含末尾 `/`），修改后重启 `jgjy-admin-backend`。若页面刷新
后出现 404，确认 Nginx 的 `location ^~ /jgjy/` 中保留了
`try_files ... /jgjy/index.html`。