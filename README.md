<div align="center">

# react-fastapi-admin

<p>
  <strong>一个基于 FastAPI + React + shadcn/ui 的现代化后台管理系统</strong>
</p>

<p>
  默认使用 SQLite 启动，采用显式运维命令管理数据库与种子数据，内置 JWT 认证、RBAC 权限控制、审计日志、文件上传与个人中心头像裁剪上传能力。
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
      数据库初始化、迁移升级、基础数据种子与 API 元数据刷新统一由 <code>manage.py</code> 显式执行。
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
      <strong>开箱即看文档</strong><br>
      启动后根路径自动跳转到 <code>/docs</code>，可直接查看 OpenAPI 文档。
    </td>
  </tr>
</table>

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
├── manage.py             # 运维命令入口（迁移、种子、刷新 API）
├── main.py               # 后端启动入口
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
APP_ENV=development
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
uv run python manage.py bootstrap
uv run python main.py
```

如果你已经激活虚拟环境，也可以直接运行：

```bash
python manage.py bootstrap
python main.py
```

首次初始化或数据库变更后，请显式执行运维命令：

- `python manage.py migrate`：初始化数据库并应用迁移
- `python manage.py seed`：写入默认角色、超级管理员和默认权限
- `python manage.py refresh-api`：同步 API 元数据目录
- `python manage.py bootstrap`：一次性执行以上完整流程

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

- 工作台使用 `Recharts` + `shadcn/ui chart` 组件展示近 7 天趋势、模块热度和状态分布。
- 登录页支持浅色、深色和跟随系统主题切换，并使用点阵 + 渐变风格背景。
- 个人中心支持头像裁剪上传，前端导出 WebP，后端再次统一转换为 WebP 后保存。
- 本地静态资源通过 `/static` 暴露，头像与上传文件在开发环境也可直接通过 Vite 代理访问。

## 常用命令

### 后端

```bash
uv sync
uv run python manage.py bootstrap
uv run python main.py
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
uv run python manage.py migrate
uv run python manage.py seed
uv run python manage.py refresh-api
uv run python manage.py bootstrap
```

## 配置说明

`.env.example` 已提供完整示例，下面是最常用的配置项：

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `APP_ENV` | 运行环境，支持 `development` / `production` | `development` |
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

- 接口统一挂载在 `/api/v1`
- 登录、刷新令牌等基础接口位于 `/api/v1/base`
- 受保护模块包括用户、角色、API、审计日志、上传等资源
- 前端菜单权限与接口权限均基于角色聚合结果控制
- 个人中心头像上传接口位于 `/api/v1/base/upload_avatar`，仅要求已登录，不依赖额外页面权限

### 启动行为

- 根路径 `/` 会重定向到 `/docs`
- 应用进程启动时只负责加载配置、连接数据库并提供服务，不再隐式执行迁移或种子写入
- 数据库初始化、基础数据和 API 元数据同步统一通过 `python manage.py ...` 显式执行
- 本地文件上传默认挂载到 `/static`
- `.webp` 静态资源已注册为 `image/webp` MIME 类型，适用于头像与图片资源直接访问

## Docker 说明

当前仓库中的 `Dockerfile` 仍引用 `deploy/entrypoint.sh` 与 `deploy/web.conf`，但仓库内未包含 `deploy/` 目录，因此暂不建议直接按旧文档进行容器构建。

如果后续补齐 `deploy/` 目录，再补充完整的 Docker 构建与运行说明会更合理。

## License

本项目基于 [MIT](./LICENSE) 协议开源。
