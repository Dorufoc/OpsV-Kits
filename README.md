# OpsV-Kits

远程开发一站式工具箱 - 文件同步 · 环境部署 · 编译运行 · Docker 管理 · WebSSH 终端

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.3+-orange.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 项目简介

OpsV-Kits 是一个面向 Java 开发者的远程开发自动化平台，通过 Web 界面和 CLI 工具，实现从本地到远程 Linux 主机的文件同步、环境自动检查安装、项目编译运行，同时内置远程文件管理、SSH 多账户管理、Docker 容器管理、WebSSH 终端等完整运维能力。

核心特性：

| 模块 | 功能 | 说明 |
|------|------|------|
| 文件同步 | 增量同步 / .gitignore 过滤 / 双向策略 | 自动识别变更文件，仅传输差异内容，支持断点续传 |
| 环境安装 | JDK / Maven 自动检测与安装 | 远程自动检查 Java/Maven 版本，不满足则通过 DNF 自动安装 |
| 编译运行 | Maven 全生命周期 / 实时日志回传 | 支持 `mvn clean compile/package`，WebSocket 实时推送彩色日志 |
| 文件管理 | 浏览 / 编辑 / 上传下载 / 权限管理 | 完整的远程 Linux 文件管理器，支持拖拽上传和权限修改 |
| SSH 账户 | 多账户 / 多认证 / AES 加密存储 | 密码/密钥/Agent/TOTP 多种认证，敏感信息本地 AES 加密 |
| WebSSH | xterm.js 原生终端 / 多标签会话 | VS Code 同款终端体验，支持多会话、全屏、SFTP 文件传输 |
| Docker 管理 | 容器/镜像/网络/卷/Compose | 完整的 Docker 生命周期管理，支持实时日志和资源监控 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+ (前端开发服务器)

### 安装与运行

```bash
# 1. 克隆项目
git clone https://github.com/yourname/OpsV-Kits.git
cd OpsV-Kits

# 2. 创建并激活虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 3. 一键启动（自动安装依赖并启动前后端）
python main.py
```

启动后浏览器自动打开 `http://localhost:5173`。首次使用进入 Web 界面配置 SSH 账户即可开始使用，无需修改任何配置文件。

### 常用启动参数

```bash
python main.py --backend-only        # 仅启动后端
python main.py --frontend-only       # 仅启动前端
python main.py --prod                # 生产模式（后端 serving 已构建的前端）
python main.py --no-browser          # 不自动打开浏览器
python main.py --port 8080           # 自定义后端端口
python main.py --skip-deps           # 跳过依赖检查
```

### 手动启动

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端（新终端）
cd frontend
npm install
npm run dev
```

---

## 项目结构

```
OpsV-Kits/
├── backend/                          # Python 后端
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/               # API 路由
│   │   │       ├── sync.py           # 文件同步接口
│   │   │       ├── build.py          # 编译运行接口
│   │   │       ├── file_manager.py   # 文件管理接口
│   │   │       ├── ssh_account.py    # SSH 账户管理接口
│   │   │       ├── docker.py         # Docker 管理接口
│   │   │       ├── webssh.py         # WebSSH 终端接口
│   │   │       ├── system.py         # 系统信息接口
│   │   │       ├── settings.py       # 配置管理接口
│   │   │       └── health.py         # 健康检查接口
│   │   ├── core/                     # 核心引擎
│   │   │   ├── ssh_client.py         # SSH 连接客户端
│   │   │   ├── ssh_pool.py           # SSH 连接池
│   │   │   ├── file_sync.py          # 文件同步引擎
│   │   │   ├── gitignore_parser.py   # .gitignore 解析器
│   │   │   ├── remote_executor.py    # 远程命令执行器
│   │   │   ├── remote_file_manager.py# 远程文件管理器
│   │   │   ├── permission_checker.py # 权限检查器
│   │   │   ├── webssh_adapter.py     # WebSSH 适配器
│   │   │   └── encryption.py         # AES 加密模块
│   │   ├── services/                 # 业务服务层
│   │   │   ├── sync_service.py       # 同步服务
│   │   │   ├── build_service.py      # 构建服务
│   │   │   ├── file_manager_service.py
│   │   │   ├── ssh_account_service.py# SSH 账户服务
│   │   │   ├── docker_service.py     # Docker 服务
│   │   │   └── webssh_service.py     # WebSSH 服务
│   │   ├── models/                   # Pydantic 数据模型
│   │   └── main.py                   # FastAPI 应用入口
│   └── requirements.txt
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── components/               # UI 组件
│   │   ├── views/                    # 页面视图
│   │   ├── stores/                   # Pinia 状态管理
│   │   └── api/                      # API 封装
│   └── package.json
├── config/
│   └── settings.yaml                 # 用户配置文件（可选）
├── third_party/
│   └── webssh/                       # WebSSH 核心库（fork）
├── main.py                           # 项目启动器
└── README.md
```

---

## 使用的开源项目

### 后端依赖（直接依赖）

| # | 项目名称 | 用途 | 最低版本 | 许可证 | 原始项目链接 |
|---|----------|------|----------|---------|-------------|
| 1 | FastAPI | Web 框架 | 0.104.0 | MIT | https://github.com/tiangolo/fastapi |
| 2 | Uvicorn | ASGI 服务器 | 0.24.0 | BSD-3-Clause | https://github.com/encode/uvicorn |
| 3 | Paramiko | SSH 连接库 | 3.3.0 | LGPL-2.1 | https://github.com/paramiko/paramiko |
| 4 | Pydantic | 数据验证与类型检查 | 2.5.0 | MIT | https://github.com/pydantic/pydantic |
| 5 | Pydantic-Settings | 配置管理 | 2.1.0 | MIT | https://github.com/pydantic/pydantic-settings |
| 6 | PyYAML | YAML 配置文件解析 | 6.0.1 | MIT | https://github.com/yaml/pyyaml |
| 7 | WebSockets | WebSocket 通信 | 12.0 | BSD-3-Clause | https://github.com/aaugustin/websockets |
| 8 | Watchdog | 文件系统监控（文件变更检测） | 3.0.0 | Apache-2.0 | https://github.com/gorakhargosh/watchdog |
| 9 | Pathspec | .gitignore 规则解析 | 0.11.0 | MPL-2.0 | https://github.com/cpburnz/pathspec |
| 10 | python-multipart | 表单数据解析（multipart/form-data） | 0.0.6 | MIT | https://github.com/Kludex/python-multipart |

### 后端依赖（间接依赖 / 传递依赖）

| # | 项目名称 | 用途 | 许可证 | 原始项目链接 | 由以下直接依赖引入 |
|---|----------|------|---------|-------------|-------------------|
| 11 | Tornado | 异步 Web 框架（webssh 使用） | Apache-2.0 | https://github.com/tornadoweb/tornado | webssh |
| 12 | cryptography | 加密原语（paramiko 使用） | Apache-2.0 / BSD | https://github.com/pyca/cryptography | paramiko |
| 13 | bcrypt | 密码哈希（paramiko 使用） | Apache-2.0 / BSD | https://github.com/pyca/bcrypt | paramiko |
| 14 | h11 | HTTP/1.1 协议实现（uvicorn 使用） | MIT | https://github.com/encode/h11 | uvicorn |
| 15 | httptools | HTTP 解析器加速（uvicorn 使用） | MIT | https://github.com/MagicStack/httptools | uvicorn |
| 16 | click | 命令行接口（uvicorn 使用） | BSD-3-Clause | https://github.com/pallets/click | uvicorn |
| 17 | watchfiles | 文件变更检测（uvicorn reload 使用） | MIT | https://github.com/samuelcolvin/watchfiles | uvicorn |

### 第三方集成项目

| # | 项目名称 | 用途 | 许可证 | 原始项目链接 | 集成方式 |
|---|----------|------|---------|-------------|---------|
| 18 | webssh | WebSSH 终端核心引擎 | MIT | https://github.com/huashengdun/webssh | 本地 fork（third_party/webssh），基于其架构实现 WebSSH 服务 |

### 前端依赖（直接依赖）

| # | 项目名称 | 用途 | 版本范围 | 许可证 | 原始项目链接 |
|---|----------|------|----------|---------|-------------|
| 1 | Vue | 前端框架 | ^3.3.8 | MIT | https://github.com/vuejs/core |
| 2 | Vue Router | 路由管理 | ^4.2.5 | MIT | https://github.com/vuejs/router |
| 3 | Pinia | 状态管理 | ^2.1.7 | MIT | https://github.com/vuejs/pinia |
| 4 | Element Plus | UI 组件库 | ^2.4.4 | MIT | https://github.com/element-plus/element-plus |
| 5 | Axios | HTTP 客户端 | ^1.6.2 | MIT | https://github.com/axios/axios |
| 6 | xterm | 终端模拟器（VS Code 同款） | ^5.3.0 | MIT | https://github.com/xtermjs/xterm.js |
| 7 | xterm-addon-fit | 终端自适应插件 | ^0.8.0 | MIT | https://github.com/xtermjs/xterm.js |
| 8 | xterm-addon-web-links | 终端 URL 链接识别插件 | ^0.9.0 | MIT | https://github.com/xtermjs/xterm.js |

### 前端依赖（开发依赖）

| # | 项目名称 | 用途 | 版本范围 | 许可证 | 原始项目链接 |
|---|----------|------|----------|---------|-------------|
| 9 | Vite | 前端构建工具 | ^5.0.0 | MIT | https://github.com/vitejs/vite |
| 10 | @vitejs/plugin-vue | Vite Vue 插件 | ^4.5.0 | MIT | https://github.com/vitejs/vite-plugin-vue |
| 11 | TypeScript | 类型系统 | ^5.3.0 | Apache-2.0 | https://github.com/microsoft/TypeScript |
| 12 | vue-tsc | Vue TypeScript 类型检查 | ^2.0.0 | MIT | https://github.com/vuejs/language-tools |
| 13 | @types/node | Node.js 类型定义 | ^20.10.0 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped |

### 许可证汇总

| 许可证 | 适用项目 |
|--------|---------|
| MIT | FastAPI, Pydantic, Pydantic-Settings, PyYAML, python-multipart, Vue, Vue Router, Pinia, Element Plus, Axios, xterm.js, xterm-addon-fit, xterm-addon-web-links, Vite, @vitejs/plugin-vue, vue-tsc, @types/node, webssh, h11, httptools, watchfiles |
| BSD-3-Clause | Uvicorn, WebSockets, click |
| Apache-2.0 | Watchdog, Tornado, cryptography, bcrypt, TypeScript |
| LGPL-2.1 | Paramiko |
| MPL-2.0 | Pathspec |

> 本项目所有依赖均采用商业友好型开源协议，未使用 GPL / AGPL 等强 copyleft 协议组件。
>
> webssh 项目为本项目本地 fork，基于其架构和代码实现 WebSSH 终端功能。原始项目作者为 Shengdun Hua（https://github.com/huashengdun/webssh），采用 MIT 许可证。

---

## API 概览

所有 API 均以 `/api` 为前缀，支持 RESTful 风格和 WebSocket 实时通信。

| 模块 | 端点 | 方法 | 描述 |
|------|------|------|------|
| Health | `/api/health` | GET | 服务健康检查 |
| SSH 账户 | `/api/accounts` | GET/POST | 账户 CRUD |
| | `/api/accounts/{alias}/test` | POST | 测试连接 |
| 文件同步 | `/api/sync/start` | POST | 启动同步任务 |
| | `/api/sync/status/{sync_id}` | GET | 查询同步状态 |
| | `/api/sync/stop/{sync_id}` | POST | 停止同步任务 |
| | `/ws/sync/{sync_id}` | WebSocket | 实时进度推送 |
| 编译运行 | `/api/build/start` | POST | 启动构建任务 |
| | `/api/build/logs/{task_id}` | GET | 获取构建日志 |
| | `/ws/build/{task_id}` | WebSocket | 实时日志流 |
| 文件管理 | `/api/files/list` | GET | 列出远程目录 |
| | `/api/files/content` | GET/POST | 读写文件内容 |
| | `/api/files/upload` | POST | 上传文件 |
| | `/api/files/download` | GET | 下载文件 |
| Docker | `/api/docker/containers` | GET | 容器列表 |
| | `/api/docker/images` | GET | 镜像列表 |
| | `/api/docker/{id}/start|stop|restart` | POST | 容器操作 |
| | `/api/docker/install` | POST | 一键安装 Docker |
| WebSSH | `/api/webssh/connect` | POST | 创建 SSH 会话 |
| | `/api/webssh/sessions` | GET | 会话列表 |
| | `/ws/webssh/{session_id}` | WebSocket | 终端数据流 |

---

## 使用场景

### 日常开发 - 一键部署

1. 进入 Web 界面配置 SSH 账户（主机、用户名、密钥/密码）
2. 设置本地项目路径和远程部署路径
3. 点击 "一键部署" 按钮
4. 系统自动完成：文件同步 -> 环境检查 -> Maven 编译 -> 启动运行
5. 在 Web 终端实时查看彩色日志输出

### 远程文件管理

1. 进入 "文件管理" 页面
2. 浏览远程服务器目录树
3. 支持上传/下载/编辑/删除/重命名/权限修改
4. 拖拽文件即可上传，支持批量操作

### Docker 容器运维

1. 进入 "Docker" 页面
2. 查看容器列表（运行中/已停止）和资源监控
3. 启动/停止/重启/删除容器
4. 实时查看容器日志，支持 WebSocket 流式推送
5. 一键进入容器交互式终端

### WebSSH 终端

1. 进入 "终端" 页面
2. 从已保存的 SSH 账户列表中一键连接
3. 多标签页管理多个 SSH 会话
4. 支持 SFTP 文件拖拽传输
5. 全屏模式、终端主题定制、命令历史

---

## CLI 命令行

除了 Web 界面，OpsV-Kits 还提供完整的 CLI 工具：

```bash
# 完整流程：同步 -> 环境检查 -> 编译 -> 运行
python -m app.cli run

# 子命令
python -m app.cli sync          # 仅同步文件
python -m app.cli build         # 仅编译
python -m app.cli start         # 仅运行
python -m app.cli setup         # 仅环境检查安装

# SSH 账户管理
python -m app.cli account list
python -m app.cli account test <alias>
python -m app.cli account default <alias>

# 远程文件管理
python -m app.cli remote ls [path]
python -m app.cli remote upload <local> <remote>
python -m app.cli remote download <remote> [local]

# Docker 管理
python -m app.cli docker ps
python -m app.cli docker logs <container>
python -m app.cli docker exec <container> <command>
```

---

## 安全特性

- 凭证加密：所有 SSH 密码、私钥密码、TOTP 密钥使用 AES-256 加密存储
- 连接池隔离：每个 SSH 账户独立连接池，会话间完全隔离
- 主机密钥验证：支持 known_hosts 策略，防止中间人攻击
- 操作审计：记录所有账户操作日志，支持按账户筛选查询
- 会话超时：空闲会话自动断开，支持自定义超时时间
- 权限校验：文件操作前校验当前用户权限，防止越权操作

---

## 贡献指南

欢迎提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

### 开发环境

```bash
# 后端开发
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端开发
cd frontend
npm install
npm run dev
```

---

## 开源协议

本项目采用 MIT License - 允许商业使用、修改、分发，仅需保留版权声明。

详见 LICENSE 文件。

---

## 联系方式

- 项目仓库: https://github.com/yourname/OpsV-Kits
- Issue 反馈: https://github.com/yourname/OpsV-Kits/issues
- 文档: 详见项目内的 `OpsV-Kits-需求文档.md`

---

OpsV-Kits - 让远程开发像本地一样简单。
