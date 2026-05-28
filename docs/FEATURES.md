# OpsV-Kits 功能模块文档

> 本文档描述 OpsV-Kits 的前端功能模块与对应后端 API 映射关系，供开发者快速了解和集成。

---

## 目录

- [1. 首页仪表盘](#1-首页仪表盘)
- [2. SSH 账户管理](#2-ssh-账户管理)
- [3. 项目管理与一键部署](#3-项目管理与一键部署)
- [4. 文件同步](#4-文件同步)
- [5. 编译运行](#5-编译运行)
- [6. 远程文件管理](#6-远程文件管理)
- [7. Docker 管理](#7-docker-管理)
- [8. WebSSH 终端](#8-webssh-终端)
- [9. 工具箱](#9-工具箱)
- [10. 设置](#10-设置)

---

## 1. 首页仪表盘

**路由**: `/`
**组件**: `Home.vue`

### 功能描述

首页是系统入口，承担两个角色：

1. **首次使用引导**: 当系统中没有任何 SSH 账户时，展示欢迎界面，引导用户添加第一个 SSH 服务器。
2. **监控仪表盘**: 已有账户后，展示系统概览和实时服务器监控。

### 功能点

| 功能 | 说明 | 前端组件 |
|------|------|---------|
| 首次使用检测 | 检查是否已有 SSH 账户 | `accounts/exists` |
| 快速添加 SSH | 表单填写主机/端口/认证信息，支持连接测试 | `accounts` + `accounts/{alias}/test` |
| 统计卡片 | 展示 SSH 账户数、Docker 容器数、部署次数、活跃终端数 | 聚合多个接口 |
| 服务器信息 | 选择账户后查看主机名、OS、内核、运行时间 | `system/info` |
| CPU 监控 | 核心数、型号、负载 | `system/performance` |
| 内存监控 | 总量、使用量、使用率进度条 | `system/performance` |
| 磁盘监控 | 挂载点、容量、使用率详情表格 | `system/disks` |
| 测试连接 | 添加账户前验证 SSH 连通性 | `accounts/{alias}/test` |

### 调用 API

| API | 方法 | 用途 |
|-----|------|------|
| `/api/accounts/exists` | GET | 检测是否有账户 |
| `/api/accounts` | POST | 创建临时账户（测试用） |
| `/api/accounts/{alias}/test` | POST | 测试连接 |
| `/api/accounts/{alias}` | DELETE | 删除测试账户 |
| `/api/system/info` | GET | 获取系统信息 |
| `/api/system/performance` | GET | 获取 CPU/内存数据 |
| `/api/system/disks` | GET | 获取磁盘数据 |

---

## 2. SSH 账户管理

**路由**: `/ssh-accounts`
**组件**: `SshAccountPage.vue`
**Store**: `sshAccountStore.ts`

### 功能描述

管理所有远程服务器的 SSH 连接凭证，支持多种认证方式和分组管理。

### 功能点

| 功能 | 说明 |
|------|------|
| 账户列表 | 展示所有已保存的 SSH 账户，按分组筛选 |
| 创建账户 | 支持密码/密钥/Agent 三种认证方式 |
| 编辑账户 | 修改账户任意字段 |
| 删除账户 | 删除不需要的账户 |
| 测试连接 | 验证 SSH 连接是否正常 |
| 设置默认 | 将某个账户设为默认 |
| 初始化工作目录 | 在远程服务器创建工作目录 |
| 分组管理 | 创建/删除分组，按组管理账户 |
| 审计日志 | 查看账户操作记录 |
| 全部清除 | 一键清除所有账户 |

### 调用 API

| API | 方法 | 用途 |
|-----|------|------|
| `/api/accounts` | GET | 获取账户列表 |
| `/api/accounts` | POST | 创建账户 |
| `/api/accounts/{alias}` | GET | 获取账户详情 |
| `/api/accounts/{alias}` | PUT | 更新账户 |
| `/api/accounts/{alias}` | DELETE | 删除账户 |
| `/api/accounts/{alias}/test` | POST | 测试连接 |
| `/api/accounts/{alias}/default` | POST | 设为默认 |
| `/api/accounts/workplace/init` | POST | 初始化工作目录 |
| `/api/accounts/groups` | GET | 获取分组列表 |
| `/api/accounts/groups` | POST | 创建分组 |
| `/api/accounts/groups/{name}` | DELETE | 删除分组 |
| `/api/accounts/audit/logs` | GET | 获取审计日志 |
| `/api/accounts/clear-all` | DELETE | 清除所有账户 |
| `/api/accounts/storage/info` | GET | 获取存储信息 |

---

## 3. 项目管理与一键部署

**路由**: `/project`
**组件**: `ProjectPage.vue`
**Store**: `projectStore.ts`, `buildStore.ts`, `syncStore.ts`

### 功能描述

管理项目配置，提供从本地到远程服务器的一站式部署流水线：文件同步 → 环境检查 → 编译 → 测试 → 运行。

### 功能点

| 功能 | 说明 |
|------|------|
| 项目列表 | 侧边栏展示所有项目，支持创建/选择/删除 |
| 项目配置 | 本地路径、远程路径、关联 SSH 账户、JDK 版本 |
| 一键部署 | 自动执行: 同步→环境检查→编译→测试→运行 |
| 文件同步 | 增量同步本地代码到远程服务器 |
| 环境检查 | 远程检测 JDK/Maven 是否安装 |
| 环境安装 | 自动通过 DNF 安装缺失组件 |
| Maven 编译 | 执行 `mvn clean compile` |
| 项目测试 | 执行 `mvn test` |
| 打包 | 执行 `mvn package` |
| 运行项目 | 支持 JAR/Spring Boot/直接运行 |
| 停止运行 | 终止远程进程 |
| 实时日志 | WebSocket 推送编译/运行日志 |
| 同步状态 | 显示文件同步进度和变更列表 |
| 构建状态 | 显示构建/运行状态信息 |

### 调用 API

**项目管理**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/projects` | GET | 获取项目列表 |
| `/api/projects` | POST | 创建项目 |
| `/api/projects/{alias}` | PUT | 更新项目 |
| `/api/projects/{alias}` | DELETE | 删除项目 |

**文件同步**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/sync/start` | POST | 启动同步 |
| `/api/sync/status/{sync_id}` | GET | 查询同步状态 |
| `/api/sync/stop` | POST | 停止同步 |
| `/api/sync/ws/status` | WS | 实时同步状态 |

**环境管理**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/environment/check` | GET | 检查环境 |
| `/api/environment/install` | POST | 安装环境 |
| `/api/environment/status` | GET | 查询安装状态 |
| `/api/environment/ws/status` | WS | 实时安装状态 |

**编译运行**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/build/compile` | POST | 编译 |
| `/api/build/test` | POST | 测试 |
| `/api/build/package` | POST | 打包 |
| `/api/build/run/jar` | POST | 运行 JAR |
| `/api/build/run/spring-boot` | POST | 运行 Spring Boot |
| `/api/build/run/exec` | POST | 直接运行 |
| `/api/build/run` | POST | 通用运行 |
| `/api/build/stop/{task_id}` | POST | 停止任务 |
| `/api/build/status/{task_id}` | GET | 查询状态 |
| `/api/build/history` | GET | 构建历史 |
| `/api/build/log/{task_id}` | GET | 获取日志 |
| `/api/build/ws/logs/{task_id}` | WS | 实时日志流 |

### 一键部署流程

```
1. POST /api/sync/start          → 启动文件同步
2. WS  /api/sync/ws/status       → 等待同步完成
3. GET  /api/environment/check   → 检查 JDK/Maven
4. POST /api/environment/install → 如需要，安装环境
5. WS  /api/environment/ws/status→ 等待安装完成
6. POST /api/build/compile       → Maven 编译
7. WS  /api/build/ws/logs/{id}   → 实时查看编译日志
8. POST /api/build/test          → 运行测试
9. WS  /api/build/ws/logs/{id}   → 实时查看测试日志
10. POST /api/build/run          → 启动项目
11. WS  /api/build/ws/logs/{id}   → 实时查看运行日志
```

---

## 4. 文件同步

**路由**: 集成在项目部署页面
**Store**: `syncStore.ts`

### 功能描述

将本地项目文件增量同步到远程服务器，支持 `.gitignore` 规则过滤，通过文件变更监控实现增量传输。

### 功能点

| 功能 | 说明 |
|------|------|
| 增量同步 | 仅传输变更文件 |
| gitignore 过滤 | 自动忽略匹配规则的文件 |
| 变更列表 | 显示新增/修改/删除的文件 |
| 同步进度 | 实时显示同步百分比 |
| 强制同步 | 忽略缓存，全量重新同步 |
| 断点续传 | 中断后可继续同步 |

### 调用 API

| API | 方法 | 用途 |
|-----|------|------|
| `/api/sync/start` | POST | 启动同步任务 |
| `/api/sync/status/{sync_id}` | GET | 轮询同步状态 |
| `/api/sync/stop` | POST | 停止同步 |
| `/api/sync/ws/status` | WebSocket | 实时同步进度 |

### 同步请求参数

```json
{
  "local_path": "/home/dev/projects/my-service",
  "remote_path": "/opt/apps/my-service",
  "account_alias": "prod-server",
  "force": false
}
```

---

## 5. 编译运行

**路由**: 集成在项目部署页面
**组件**: `BuildPanel.vue`
**Store**: `buildStore.ts`

### 功能描述

管理远程服务器上的项目编译、测试和运行，支持通过 WebSocket 实时推送日志输出。

### 功能点

| 功能 | 说明 |
|------|------|
| Maven 编译 | 执行 `mvn clean compile` |
| 运行测试 | 执行 `mvn test` |
| 打包 | 执行 `mvn package` |
| 运行 JAR | 直接运行已打包的 JAR |
| Spring Boot | 通过主类启动 Spring Boot 应用 |
| 直接运行 | 指定主类直接运行 |
| 停止运行 | 终止远程 Java 进程 |
| 实时日志 | WebSocket 彩色日志输出 |
| 历史记录 | 查看历史构建记录 |
| 任务状态 | 运行中/已完成/失败 |

### 调用 API

| API | 方法 | 用途 |
|-----|------|------|
| `/api/build/compile` | POST | 启动编译 |
| `/api/build/test` | POST | 启动测试 |
| `/api/build/package` | POST | 打包项目 |
| `/api/build/run/jar` | POST | 运行 JAR |
| `/api/build/run/spring-boot` | POST | 运行 Spring Boot |
| `/api/build/run/exec` | POST | 直接运行 |
| `/api/build/run` | POST | 通用运行接口 |
| `/api/build/stop/{task_id}` | POST | 停止任务 |
| `/api/build/stop` | POST | 停止任务 (Body 方式) |
| `/api/build/status/{task_id}` | GET | 查询任务状态 |
| `/api/build/history` | GET | 构建历史 |
| `/api/build/log/{task_id}` | GET | 获取日志 |
| `/api/build/ws/logs/{task_id}` | WebSocket | 实时日志流 |

---

## 6. 远程文件管理

**路由**: `/file-manager`
**组件**: `FileManagerPage.vue`, `FileBrowser.vue`

### 功能描述

通过 Web 界面远程浏览和操作 Linux 服务器上的文件系统，类似一个 Web 版的 FTP/SFTP 客户端。

### 功能点

| 功能 | 说明 |
|------|------|
| 账户选择 | 选择已保存的 SSH 账户 |
| 目录浏览 | 树形目录导航，面包屑导航 |
| 文件列表 | 显示文件名、大小、权限、修改时间 |
| 查看详情 | 文件/目录详细信息（inode、链接等） |
| 读取文件 | 在线查看文本文件内容 |
| 编辑文件 | 在线编辑并保存 |
| 新建目录 | 创建文件夹 |
| 删除 | 删除文件/目录 |
| 重命名 | 重命名/移动文件 |
| 复制 | 复制文件 |
| 修改权限 | chmod 修改文件权限 |
| 修改所有者 | chown 修改文件所有者 |
| 上传文件 | 上传本地文件到远程 |
| 下载文件 | 下载远程文件到本地 |
| 搜索文件 | 按名称模式搜索 |
| 书签 | 常用目录快捷方式 |
| 命令执行 | 在远程执行 shell 命令 |
| 权限检查 | 查看当前用户权限 |
| 操作历史 | 查看文件操作记录 |
| 批量操作 | 批量删除、批量修改权限 |

### 调用 API

**文件操作**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/files/list` | GET | 列出目录 |
| `/api/files/stat` | GET | 获取详细信息 |
| `/api/files/content` | GET | 读取文件 |
| `/api/files/content` | POST | 保存文件 |
| `/api/files/mkdir` | POST | 创建目录 |
| `/api/files/delete` | POST | 删除 |
| `/api/files/rename` | POST | 重命名/移动 |
| `/api/files/copy` | POST | 复制 |
| `/api/files/chmod` | POST | 修改权限 |
| `/api/files/chown` | POST | 修改所有者 |
| `/api/files/upload` | POST | 上传文件 |
| `/api/files/download` | GET | 下载文件 |
| `/api/files/search` | GET | 搜索文件 |

**批量操作**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/files/batch/delete` | POST | 批量删除 |
| `/api/files/batch/chmod` | POST | 批量修改权限 |

**命令执行**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/command/exec` | POST | 执行命令 |
| `/api/command/exec/batch` | POST | 批量执行 |
| `/api/command/history` | GET | 命令历史 |

**权限**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/permission/check` | GET | 检查文件权限 |
| `/api/permission/user` | GET | 获取用户信息 |
| `/api/permission/sudo` | GET | 检查 sudo 权限 |

**书签**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/bookmarks` | GET | 获取书签列表 |
| `/api/bookmarks` | POST | 添加书签 |
| `/api/bookmarks` | DELETE | 删除书签 |

**操作历史**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/operations/history` | GET | 获取操作历史 |

---

## 7. Docker 管理

**路由**: `/docker`, `/docker/container/:id`
**组件**: `DockerPage.vue`, `DockerContainerDetail.vue`, `ContainerList.vue`, `ImageList.vue`
**Store**: `dockerStore.ts`

### 功能描述

通过 Web 界面管理远程服务器上的 Docker 容器、镜像、网络、卷和 Compose 项目。

### 功能点

| 功能 | 说明 |
|------|------|
| Docker 信息 | 查看 Docker 版本、运行状态 |
| 一键安装 | 远程安装 Docker |
| 容器列表 | 查看所有容器（运行中/已停止） |
| 容器操作 | 启动/停止/重启/暂停/恢复/强制停止/删除 |
| 容器详情 | 查看容器配置、网络、挂载等信息 |
| 容器日志 | 实时查看容器日志（WebSocket 流） |
| 容器统计 | CPU/内存/网络资源使用 |
| 容器_exec | 在容器内执行命令 |
| 镜像列表 | 查看所有镜像 |
| 镜像操作 | 拉取/构建/删除/搜索镜像 |
| 网络管理 | 创建/删除/查看网络 |
| 卷管理 | 创建/删除/查看卷 |
| Compose | 查看/启动/停止 Compose 项目 |
| 镜像清理 | 清理未使用的镜像 |

### 调用 API

**Docker 环境**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/docker/info` | GET | Docker 环境信息 |
| `/api/docker/install` | POST | 安装 Docker |

**容器**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/docker/containers` | GET | 容器列表 |
| `/api/docker/containers/{id}` | GET | 容器详情 |
| `/api/docker/containers/{id}/start` | POST | 启动 |
| `/api/docker/containers/{id}/stop` | POST | 停止 |
| `/api/docker/containers/{id}/restart` | POST | 重启 |
| `/api/docker/containers/{id}/kill` | POST | 强制停止 |
| `/api/docker/containers/{id}/pause` | POST | 暂停 |
| `/api/docker/containers/{id}/unpause` | POST | 恢复 |
| `/api/docker/containers/{id}` | DELETE | 删除 |
| `/api/docker/containers/{id}/logs` | GET | 查看日志 |
| `/api/docker/containers/{id}/stats` | GET | 资源统计 |
| `/api/docker/containers/{id}/exec` | POST | 执行命令 |
| `/api/docker/ws/containers/{id}/logs` | WS | 实时日志流 |

**镜像**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/docker/images` | GET | 镜像列表 |
| `/api/docker/images/{id}` | DELETE | 删除镜像 |
| `/api/docker/images/pull` | POST | 拉取镜像 |
| `/api/docker/images/build` | POST | 构建镜像 |
| `/api/docker/images/prune` | POST | 清理镜像 |
| `/api/docker/images/search` | GET | 搜索镜像 |

**网络**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/docker/networks` | GET | 网络列表 |
| `/api/docker/networks` | POST | 创建网络 |
| `/api/docker/networks/{id}` | GET | 网络详情 |
| `/api/docker/networks/{id}` | DELETE | 删除网络 |

**卷**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/docker/volumes` | GET | 卷列表 |
| `/api/docker/volumes` | POST | 创建卷 |
| `/api/docker/volumes/{name}` | GET | 卷详情 |
| `/api/docker/volumes/{name}` | DELETE | 删除卷 |

**Compose**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/docker/compose/projects` | GET | Compose 项目列表 |
| `/api/docker/compose/up` | POST | 启动项目 |
| `/api/docker/compose/down` | POST | 停止项目 |

---

## 8. WebSSH 终端

**路由**: `/webssh`
**组件**: `WebSSHPage.vue`, `WebSSHConnectDialog.vue`, `Terminal.vue`, `SessionManager.vue`
**Store**: `websshStore.ts`

### 功能描述

基于 xterm.js 的 Web 终端，提供类似 VS Code 的终端体验，支持多标签会话管理。

### 功能点

| 功能 | 说明 |
|------|------|
| 快速连接 | 从已保存账户一键连接 |
| 新建连接 | 自定义主机/端口/认证连接 |
| 多标签页 | 同时管理多个 SSH 会话 |
| 终端交互 | 完整的交互式终端 |
| 调整大小 | 动态调整终端行列数 |
| 会话列表 | 查看所有活跃/历史会话 |
| 会话历史 | 查看已断开的会话记录 |
| 命令历史 | 查看执行过的命令 |
| 全屏模式 | 终端全屏显示 |
| SFTP 传输 | 支持文件拖拽上传 |

### 调用 API

| API | 方法 | 用途 |
|-----|------|------|
| `/api/webssh/sessions` | GET | 获取会话列表 |
| `/api/webssh/test` | POST | 测试连接 |
| `/api/webssh/connect` | POST | 创建会话 |
| `/api/webssh/disconnect` | POST | 断开会话 |
| `/api/webssh/resize` | POST | 调整终端大小 |
| `/api/webssh/command` | POST | 发送命令 |
| `/api/webssh/sessions/history` | GET | 会话历史 |
| `/api/webssh/sessions/history/{id}` | DELETE | 删除历史记录 |
| `/api/webssh/history` | GET | 命令历史 |
| `/api/webssh/ws/{session_id}` | WebSocket | 交互式终端 I/O |

### WebSocket 通信流程

```
客户端 (xterm.js)                服务端
    |                                |
    |--- {type: "input", data: "ls"} -->|
    |                                | (执行命令)
    |<- {type: "data", content: "..."} --|
    |                                |
    |--- {type: "resize", w:120,h:40} ->|
    |                                |
    |--- {type: "ping"} ------------>|
    |<- {type: "pong"} ---------------|
    |                                |
    |--- {type: "disconnect"} ------>|
    |<- {type: "disconnected"} --------|
```

---

## 9. 工具箱

**路由**: `/tools`
**组件**: `Tools.vue`

### 功能描述

提供常用系统运维工具，包括远程驱动器管理、防火墙配置、SELinux 管理和系统操作。

### 功能点

| 功能 | 说明 |
|------|------|
| 远程驱动器 | 查看 WebDAV 驱动器状态 |
| 防火墙管理 | 查看/启用/禁用防火墙，管理端口和服务规则 |
| SELinux | 查看/设置 SELinux 模式 |
| 系统操作 | 重启/关闭/重载网络/重载 SSH/清理缓存 |

### 调用 API

**远程驱动器**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/remote-drive/status` | GET | 驱动器状态 |

**防火墙**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/system/firewall/status` | GET | 防火墙状态 |
| `/api/system/firewall/set` | POST | 启用/禁用防火墙 |
| `/api/system/firewall/rules` | GET | 查看规则 |
| `/api/system/firewall/zones` | GET | 查看区域 |
| `/api/system/firewall/port` | POST | 开放端口 |
| `/api/system/firewall/port` | DELETE | 关闭端口 |
| `/api/system/firewall/service` | POST | 开放服务 |
| `/api/system/firewall/service` | DELETE | 关闭服务 |

**SELinux**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/system/selinux` | GET | 查看状态 |
| `/api/system/selinux` | POST | 设置模式 |

**系统操作**:

| API | 方法 | 用途 |
|-----|------|------|
| `/api/system/reboot` | POST | 重启服务器 |
| `/api/system/shutdown` | POST | 关闭服务器 |
| `/api/system/reload/network` | POST | 重载网络 |
| `/api/system/reload/ssh` | POST | 重载 SSH |
| `/api/system/cache/clear` | POST | 清理缓存 |

---

## 10. 设置

**路由**: `/settings`
**组件**: `Settings.vue`
**Store**: 直接调用 API 无独立 Store

### 功能描述

管理应用级别的配置项。

### 功能点

| 功能 | 说明 |
|------|------|
| 会话 TTL | 设置空闲会话自动断开时间（小时） |
| 远程驱动器 | 启用/禁用 WebDAV 驱动器 |
| 驱动器端口 | 设置 WebDAV 服务端口 |
| 历史记录 | 管理会话历史记录 |

### 调用 API

| API | 方法 | 用途 |
|-----|------|------|
| `/api/settings` | GET | 获取设置 |
| `/api/settings` | PUT | 更新设置 |
| `/api/webssh/sessions/history` | GET | 会话历史 |
| `/api/webssh/sessions/history/{id}` | DELETE | 删除历史记录 |

### 设置参数

```json
{
  "session_ttl_hours": 72,
  "remote_drive_enabled": false,
  "remote_drive_port": 8081
}
```

---

## 附录

### A. 前端架构概览

```
frontend/
├── src/
│   ├── api/
│   │   └── index.ts              # Axios 实例（拦截器、认证、错误处理）
│   ├── router/
│   │   └── index.ts              # Vue Router（9 条路由）
│   ├── views/                    # 页面组件
│   │   ├── Home.vue              # 首页仪表盘
│   │   ├── ProjectPage.vue       # 项目管理/部署
│   │   ├── FileManagerPage.vue   # 文件管理
│   │   ├── SshAccountPage.vue    # SSH 账户管理
│   │   ├── DockerPage.vue        # Docker 管理
│   │   ├── DockerContainerDetail.vue  # 容器详情
│   │   ├── WebSSHPage.vue        # WebSSH 终端
│   │   ├── Tools.vue             # 工具箱
│   │   └── Settings.vue          # 设置
│   ├── stores/                   # Pinia 状态管理
│   │   ├── sshAccountStore.ts    # SSH 账户状态
│   │   ├── projectStore.ts       # 项目状态
│   │   ├── syncStore.ts          # 同步状态
│   │   ├── buildStore.ts         # 构建状态
│   │   ├── dockerStore.ts        # Docker 状态
│   │   └── websshStore.ts        # WebSSH 状态
│   └── components/               # 通用组件
│       ├── Terminal.vue          # xterm.js 终端
│       ├── BuildPanel.vue        # 构建日志面板
│       ├── SyncPanel.vue         # 同步状态面板
│       ├── SessionManager.vue    # 会话管理
│       ├── ImageList.vue         # Docker 镜像列表
│       ├── ContainerList.vue     # Docker 容器列表
│       ├── FileBrowser.vue       # 文件浏览器
│       └── WebSSHConnectDialog.vue  # SSH 连接对话框
```

### B. 路由表

| 路径 | 页面 | 功能 |
|------|------|------|
| `/` | Home.vue | 首页仪表盘 |
| `/project` | ProjectPage.vue | 项目管理/一键部署 |
| `/file-manager` | FileManagerPage.vue | 远程文件管理 |
| `/ssh-accounts` | SshAccountPage.vue | SSH 账户管理 |
| `/docker` | DockerPage.vue | Docker 管理 |
| `/docker/container/:id` | DockerContainerDetail.vue | 容器详情 |
| `/webssh` | WebSSHPage.vue | WebSSH 终端 |
| `/tools` | Tools.vue | 工具箱 |
| `/settings` | Settings.vue | 设置 |

### C. HTTP 客户端配置

- **Base URL**: `/api`（开发环境通过 Vite 代理转发到后端 8000 端口）
- **认证**: 请求头 `Authorization: Bearer <token>`
- **WebSocket 代理**: `/ws` → 后端 WebSocket
- **超时**: 默认超时
- **错误处理**: 统一拦截器处理错误响应

### D. 认证方式说明

SSH 支持三种认证方式：

| auth_type | 说明 | 必填字段 |
|-----------|------|---------|
| `password` | 密码认证 | password |
| `key` | 密钥认证 | private_key, key_passphrase(可选) |
| `agent` | SSH Agent | 无 |

### E. WebSocket 使用模式

系统中有 5 个 WebSocket 端点，分两种使用模式：

**1. 实时数据流（监听模式）:**
- 环境安装状态: 客户端 subscribe → 服务端推送进度
- 构建日志: 服务端持续推送日志输出
- 容器日志: 服务端持续推送日志输出
- 同步状态: 客户端发送 sync_id → 服务端推送状态

**2. 交互式 I/O（双向模式）:**
- WebSSH: 客户端发送输入 ↔ 服务端返回终端输出
