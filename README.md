<div align="center">

# react-fastapi-admin

<p>
  <strong>一个基于 FastAPI + React + Ant Design 的现代化后台管理系统</strong>
</p>

<p>
  默认使用 SQLite 启动，内置启动引导、JWT 认证、RBAC 权限控制、审计日志与文件上传能力。
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
      <strong>自动引导启动</strong><br>
      开发环境默认支持数据库初始化、迁移升级、基础数据种子与 API 元数据刷新。
    </td>
    <td width="33%">
      <strong>权限模型完整</strong><br>
      基于角色聚合菜单权限与 API 权限，覆盖登录、鉴权、授权与页面访问控制。
    </td>
    <td width="33%">
      <strong>前后端分离</strong><br>
      后端基于 FastAPI，前端基于 React 19 + Vite 8，接口与页面职责清晰。
    </td>
  </tr>
  <tr>
    <td width="33%">
      <strong>审计日志可追踪</strong><br>
      支持筛选、游标分页、详情查看与导出，便于定位后台操作记录。
    </td>
    <td width="33%">
      <strong>上传能力可切换</strong><br>
      支持本地存储与对象存储，超级管理员可在系统设置页面直接切换与维护。
    </td>
    <td width="33%">
      <strong>开箱即看文档</strong><br>
      启动后根路径自动跳转到 <code>/docs</code>，可直接查看 OpenAPI 文档。
    </td>
  </tr>
</table>

## 功能状态

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 认证与会话 | 已完成 | JWT 登录、刷新令牌、退出登录、密码修改、个人资料更新 |
| 权限控制 | 已完成 | RBAC 菜单权限、API 权限、前端页面守卫 |
| 工作台 | 已完成 | 概览统计、系统状态、近期活动 |
| 用户管理 | 已完成 | 用户查询、创建、编辑、启停等管理能力 |
| 角色管理 | 已完成 | 角色维护、权限分配 |
| API 管理 | 已完成 | API 元数据维护与权限关联 |
| 审计日志 | 已完成 | 条件检索、游标分页、详情、导出 |
| 文件上传 | 已完成 | 本地存储与对象存储上传 |

## 技术栈

| 层级 | 技术 |
| --- | --- |
| Backend | FastAPI, Granian, Tortoise ORM, Aerich, Pydantic Settings, Loguru, PyJWT |
| Frontend | React 19, Vite 8, Ant Design 6, Tailwind CSS 4, React Router 7, Axios |
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
uv run python main.py
```

如果你已经激活虚拟环境，也可以直接运行：

```bash
python main.py
```

开发环境首次启动默认会自动执行：

- 初始化数据库结构
- 应用已有迁移
- 创建默认角色
- 创建超级管理员
- 刷新 API 元数据

### 4. 启动前端

```bash
cd web
pnpm install
pnpm dev
```

前端开发服务器默认运行在 `http://127.0.0.1:5173`，并会将 `/api` 请求代理到 `http://127.0.0.1:9999/api/v1`。

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

## 常用命令

### 后端

```bash
uv sync
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
aerich migrate
aerich upgrade
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
| `AUTO_BOOTSTRAP` | 是否启用启动引导 | `true` |
| `RUN_MIGRATIONS_ON_STARTUP` | 启动时是否自动迁移 | 开发环境默认开启 |
| `SEED_BASE_DATA_ON_STARTUP` | 启动时是否初始化基础数据 | 默认开启 |
| `REFRESH_API_METADATA_ON_STARTUP` | 启动时是否刷新 API 元数据 | 开发环境默认开启 |
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

### 启动行为

- 根路径 `/` 会重定向到 `/docs`
- 开发环境会根据配置自动决定是否启用热重载、自动迁移和 API 元数据刷新
- 本地文件上传默认挂载到 `/static`

## Docker 说明

当前仓库中的 `Dockerfile` 仍引用 `deploy/entrypoint.sh` 与 `deploy/web.conf`，但仓库内未包含 `deploy/` 目录，因此暂不建议直接按旧文档进行容器构建。

如果后续补齐 `deploy/` 目录，再补充完整的 Docker 构建与运行说明会更合理。

## License

本项目基于 [MIT](./LICENSE) 协议开源。
