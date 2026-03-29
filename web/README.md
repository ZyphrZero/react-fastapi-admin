# React Go Admin - React 前端

一个基于 **React 18 + Ant Design 5 + Tailwind CSS 4 + Vite 8** 构建的现代化管理系统前端。

## 🚀 技术栈

- **React 18.3.1** - 最新的 React 框架
- **Ant Design 5.26.5** - 企业级 UI 组件库
- **Tailwind CSS 4.1.11** - 原子化 CSS 框架
- **Vite 8** - 新一代前端构建工具
- **React Router Dom** - 路由管理
- **Axios** - HTTP 请求库

## 📁 项目结构

```
src/
├── api/                  # API接口定义
│   └── index.js         # 统一API接口
├── components/          # 公共组件
│   ├── Layout/          # 主布局组件
│   ├── ProtectedRoute.jsx   # 路由守卫
│   └── LoginRedirect.jsx    # 登录重定向
├── pages/              # 页面组件
│   ├── Login/          # 登录页面
│   └── Dashboard/      # 工作台页面
├── router/             # 路由配置
│   └── index.jsx       # 路由定义
├── utils/              # 工具函数
│   └── request.js      # HTTP请求封装
├── App.jsx             # 根组件
├── main.jsx           # 应用入口
└── index.css          # 全局样式
```

## 🎯 功能特性

### ✅ 已完成功能

1. **登录系统**

   - 现代化的登录界面设计
   - 表单验证和错误处理
   - Token 认证和自动跳转

2. **主布局系统**

   - 响应式侧边栏导航
   - 头部导航栏
   - 面包屑导航
   - 用户信息展示

3. **工作台页面**

   - 系统统计数据展示
   - 系统状态监控
   - 快速操作入口
   - 最近活动列表

4. **路由系统**
   - 路由守卫机制
   - 嵌套路由配置
   - 404 错误页面

### 🚧 待开发功能

- 用户管理页面
- 角色管理页面
- 菜单管理页面
- API 管理页面
- 审计日志页面
- 文件管理页面
- 个人中心页面

## 🛠️ 安装和运行

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 🔧 配置说明

### Vite 配置 (vite.config.js)

- **路径别名**: `@` 指向 `src` 目录
- **代理配置**: `/api/v1` 代理到 `http://localhost:9999`
- **插件**: React + Tailwind CSS

### 样式配置

- **全局样式**: 使用 Tailwind CSS 进行样式管理
- **组件样式**: Ant Design 组件样式
- **主题配置**: 可在 `App.jsx` 中自定义主题
- **响应式设计**: 支持移动端适配

## 🎨 界面展示

### 登录页面

- 现代化渐变背景
- 玻璃质感卡片设计
- 表单验证和加载状态

### 主界面

- 侧边栏可折叠导航
- 顶部导航栏和面包屑
- 卡片式内容布局

### 工作台

- 统计数据卡片
- 系统状态图表
- 快速操作按钮
- 活动记录表格

## 🔐 认证流程

1. 用户输入用户名密码登录
2. 调用 `/base/access_token` 接口获取 token
3. 将 token 存储到 localStorage
4. 获取用户信息并存储
5. 跳转到工作台页面
6. 后续请求自动携带 token

## 📱 响应式设计

- **桌面端**: 完整的侧边栏和多列布局
- **平板端**: 适中的组件尺寸
- **移动端**: 折叠菜单和单列布局

## 🔗 与后端集成

确保 Go 后端服务运行在 `http://localhost:9999`，前端将通过代理访问后端 API。

## 🤝 开发规范

- 使用 ES6+语法
- 组件采用函数式组件 + Hooks
- 使用 Tailwind CSS 进行样式开发
- 遵循 Ant Design 设计规范
- 保持代码简洁和可维护性
