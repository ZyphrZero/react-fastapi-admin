<div align="center">

# react-fastapi-admin

<p>
  <strong>一个基于 FastAPI + React + shadcn/ui 的现代化后台管理系统</strong>
</p>

<p>
  默认使用 SQLite 启动，采用显式运维命令管理数据库与种子数据，内置 JWT 认证、RBAC 权限控制、审计日志、文件/图像上传能力。
</p>

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.135+-009688?logo=fastapi&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React-19-149ECA?logo=react&logoColor=white">
  <img alt="Vite" src="https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-blue">
</p>

<p>
  <a href="#项目亮点">项目亮点</a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="#访问入口">访问入口</a> ·
  <a href="#配置说明">配置说明</a> ·
  <a href="#开发说明">开发说明</a>
</p>

</div>

## 项目亮点

<table>
  <tr>
    <td width="33%">
      <strong>显式运维命令</strong><br>
      数据库初始化、迁移升级、基础数据种子与 API 元数据刷新统一由 <code>python -m app</code> 显式执行。
    </td>
    <td width="33%">
      <strong>权限模型完整</strong><br>
      基于角色聚合菜单权限与 API 权限，覆盖登录、鉴权、授权与页面访问控制。
    </td>
    <td width="33%">
      <strong>前后端分离</strong><br>
      后端基于 FastAPI，前端基于 React 19 + Vite 8，页面、权限与接口职责清晰。
    </td>
  </tr>
  <tr>
    <td width="33%">
      <strong>审计日志可追踪</strong><br>
      支持筛选、游标分页、详情查看与导出，便于定位后台操作记录。
    </td>
    <td width="33%">
      <strong>上传能力可切换</strong><br>
      支持本地存储与对象存储，头像上传支持裁剪并统一转换为 WebP。
    </td>
    <td width="33%">
      <strong>界面与文档一体化交付</strong><br>
      生产镜像会同时提供管理界面与 <code>/docs</code> 文档入口，部署路径更简单。
    </td>
  </tr>
</table>

## 预览图
![login_light_dark_diagonal_preview.png](https://cdn.pixelpunk.cc/f/01c51f0211f647ef/login_light_dark_diagonal_preview.png)  
![dashboard_light_dark_diagonal_preview.png](https://cdn.pixelpunk.cc/f/4735f2fde4244262/dashboard_light_dark_diagonal_preview.png)

## 技术栈

| 层级 | 技术 |
| --- | --- |
| Backend | FastAPI, Granian, Tortoise ORM, Aerich, Pydantic Settings, Loguru, PyJWT, Pillow |
| Frontend | React 19, Vite 8, shadcn/ui, Tailwind CSS 4, React Router 7, Axios, Recharts |
| Database | SQLite 默认，可切换 MySQL / PostgreSQL |

## 项目结构

```text
.
├── app/                  # FastAPI 后端代码
│   ├── api/v1/           # HTTP 路由
│   ├── controllers/      # 业务控制层
│   ├── core/             # 框架能力、依赖与启动流程
│   ├── models/           # ORM 模型
│   ├── schemas/          # 请求/响应模型
│   ├── settings/         # 配置与环境变量
│   └── tests/            # 后端测试
├── migrations/           # Aerich 迁移文件
├── web/                  # React 前端代码
│   ├── src/api/          # API 客户端
│   ├── src/components/   # 公共组件
│   ├── src/pages/        # 页面
│   ├── src/router/       # 路由
│   ├── src/hooks/        # Hooks
│   └── src/utils/        # 工具方法
├── app/cli.py            # 统一 CLI 入口（服务、迁移、种子、刷新 API）
├── app/asgi.py           # ASGI 应用入口
├── pyproject.toml        # Python 依赖与工具配置
└── .env.example          # 环境变量示例
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18.8.0+
- pnpm

### 1. 克隆项目

```bash
git clone https://github.com/mizhexiaoxiao/react-fastapi-admin.git
cd react-fastapi-admin
```

### 2. 准备环境变量

Linux / macOS:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

推荐先确认以下配置：

```env
APP_ENV=dev
PORT=9999
DB_CONNECTION=sqlite
DB_FILE=db.sqlite3
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=
```

> `INITIAL_ADMIN_PASSWORD` 为空时，系统会在首次引导时自动生成管理员密码，并只在启动控制台输出一次。  
> 生产环境必须显式配置安全的 `SECRET_KEY`。

### 3. 启动后端

推荐使用 `uv`：

```bash
uv sync
uv run python -m app bootstrap
uv run python -m app serve
```

如果你已经激活虚拟环境，也可以直接运行：

```bash
python -m app bootstrap
python -m app serve
```

首次初始化或数据库变更后，请显式执行运维命令：

- `python -m app db upgrade`：应用已提交的数据库迁移
- `python -m app db seed`：写入默认角色、超级管理员和默认权限
- `python -m app db sync`：同步 API 元数据目录
- `python -m app bootstrap`：一次性执行以上完整流程

### 4. 启动前端

```bash
cd web
pnpm install
pnpm dev
```

前端开发服务器默认运行在 `http://127.0.0.1:5173`，并会将以下路径代理到后端：

- `/api` -> `http://127.0.0.1:9999/api/v1`
- `/static` -> `http://127.0.0.1:9999/static`

## 访问入口

| 入口 | 地址 |
| --- | --- |
| 后端服务 | `http://127.0.0.1:9999` |
| API 文档 | `http://127.0.0.1:9999/docs` |
| OpenAPI | `http://127.0.0.1:9999/openapi.json` |
| 健康检查 | `http://127.0.0.1:9999/health` |
| 前端开发地址 | `http://127.0.0.1:5173` |

默认管理员说明：

- 用户名默认为 `admin`
- 密码由 `INITIAL_ADMIN_PASSWORD` 决定
- 如果未配置初始密码，请从首次启动控制台复制系统生成的一次性密码

## 界面说明

- 工作台提供近 7 天趋势、模块热度和状态分布等核心概览信息。
- 登录页支持浅色、深色和跟随系统主题切换。
- 个人中心支持头像上传与裁剪。
- 系统支持本地静态资源访问。

## 常用命令

### 后端

```bash
uv sync
uv run python -m app bootstrap
uv run python -m app serve
uv run pytest app/tests
uv run pytest app/tests/test_log_system.py
```

### 前端

```bash
cd web
pnpm install
pnpm dev
pnpm lint
pnpm build
```

### 数据库迁移

```bash
uv run python -m app db upgrade
uv run python -m app db seed
uv run python -m app db sync
uv run python -m app bootstrap
```

## 配置说明

`.env.example` 已提供完整示例，下面是最常用的配置项：

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `APP_ENV` | 运行环境，支持 `dev` / `prod` | `dev` |
| `HOST` | 服务监听地址 | `0.0.0.0` |
| `PORT` | 服务端口 | `9999` |
| `DB_CONNECTION` | 数据库类型，支持 `sqlite` / `mysql` / `postgres` | `sqlite` |
| `DB_FILE` | SQLite 文件名 | `db.sqlite3` |
| `INITIAL_ADMIN_USERNAME` | 初始管理员用户名 | `admin` |
| `INITIAL_ADMIN_PASSWORD` | 初始管理员密码，留空则自动生成 | 空 |
| `SECRET_KEY` | 应用密钥，生产环境必须修改 | 开发环境自动生成 |

## 开发说明

### 默认数据库

- 项目默认使用 SQLite，数据库文件位于项目根目录下的 `db.sqlite3`
- 如需切换到 MySQL 或 PostgreSQL，请在 `.env` 中修改 `DB_CONNECTION` 及对应连接参数

### 权限模型

- 基于角色统一管理菜单权限与接口权限。
- 支持用户、角色、API、审计日志、上传等后台模块的访问控制。
- 通用能力与业务模块按功能划分，便于扩展与维护。

### 启动行为

- 应用启动时只负责加载配置、连接数据库并提供服务。
- 数据库初始化、基础数据写入和元数据同步通过 `python -m app ...` 显式执行。
- 本地文件上传默认挂载到 `/static`。

## Docker 说明

- `deploy/.env.example`：Docker 环境变量示例
- `deploy/docker-compose.yml`：应用 + PostgreSQL 的 Docker Compose 配置
- `deploy/install.sh`：一键安装脚本

### 部署定位

- 单个应用容器同时提供前端页面与后端 API
- PostgreSQL 通过 Compose 一起部署
- 访问根路径即可打开管理界面，base_url + `/docs` 仍可查看 OpenAPI 文档

### 一键安装

```bash
cd deploy
chmod +x install.sh
./install.sh
```

安装脚本会自动完成以下操作：

- 生成 `deploy/.env`
- 自动填充 `SECRET_KEY`、数据库密码和初始管理员密码
- 构建并启动容器
- 执行 `python -m app bootstrap`
- 输出访问地址与管理员账号

### 手动部署

```bash
cd deploy
cp .env.example .env
docker compose --env-file .env up -d
```

首次初始化数据库、默认角色、管理员账号和 API 元数据：

```bash
docker compose --env-file .env exec api python -m app bootstrap
```

后续升级数据库迁移：

```bash
docker compose --env-file .env exec api python -m app db upgrade
```

查看服务状态与日志：

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs -f api
```

## License

本项目基于 [MIT](./LICENSE) 协议开源。
