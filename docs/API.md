# OpsV-Kits API 接口文档

> **Base URL**: `/api`
> **版本**: 0.1.0
> **协议**: RESTful + WebSocket
> **认证**: 请求头携带 `Authorization: Bearer <token>`（如已配置）

---

## 目录

- [1. 健康检查](#1-健康检查)
- [2. SSH 账户管理](#2-ssh-账户管理)
- [3. 项目管理](#3-项目管理)
- [4. 文件同步](#4-文件同步)
- [5. 编译运行](#5-编译运行)
- [6. 环境管理](#6-环境管理)
- [7. 文件管理](#7-文件管理)
- [8. Docker 管理](#8-docker-管理)
- [9. 系统管理](#9-系统管理)
- [10. WebSSH 终端](#10-webssh-终端)
- [11. 远程驱动器](#11-远程驱动器)
- [12. 应用设置](#12-应用设置)

---

## 通用说明

### 响应格式

所有 REST 接口返回 JSON 格式数据。成功响应状态码为 `200` 或 `201`，删除成功返回 `204 No Content`。

### 错误响应

```json
{
  "detail": "错误描述信息"
}
```

常见状态码：

| 状态码 | 含义 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### WebSocket 通用说明

WebSocket 端点使用 JSON 消息格式通信。客户端发送和接收的消息均为 JSON 对象，包含 `type` 字段标识消息类型。

---

## 1. 健康检查

### GET `/api/health`

服务健康检查。

**请求参数**: 无

**响应示例**:

```json
{
  "status": "ok",
  "service": "OpsV-Kits API",
  "version": "0.1.0"
}
```

---

## 2. SSH 账户管理

### 2.1 账户 CRUD

#### GET `/api/accounts`

获取所有 SSH 账户列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| group | string | 否 | 按分组筛选 |

**响应**: `SSHAccount[]`

```json
[
  {
    "alias": "prod-server",
    "host": "192.168.1.100",
    "port": 22,
    "username": "root",
    "auth_type": "key",
    "is_default": true,
    "group": "production",
    "workplace_path": "~/projects"
  }
]
```

#### POST `/api/accounts`

创建 SSH 账户。

**请求体** (`SSHAccountCreate`):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | 账户唯一标识 |
| host | string | 是 | 主机地址 |
| port | integer | 否 | 端口，默认 22 |
| username | string | 是 | 用户名 |
| auth_type | string | 是 | 认证方式: `password` / `key` / `agent` |
| password | string | 条件 | auth_type=password 时必填 |
| private_key | string | 条件 | auth_type=key 时必填，PEM 格式 |
| key_passphrase | string | 否 | 私钥密码 |
| totp_secret | string | 否 | TOTP 密钥 |
| is_default | boolean | 否 | 是否为默认账户 |
| group | string | 否 | 所属分组 |
| workplace_path | string | 否 | 工作目录，默认 ~/projects |

**响应**: `SSHAccount` (201)

#### GET `/api/accounts/{alias}`

获取指定账户详情。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alias | string | 账户标识 |

**响应**: `SSHAccount`

#### PUT `/api/accounts/{alias}`

更新账户信息（部分更新）。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alias | string | 账户标识 |

**请求体** (`SSHAccountUpdate`): 所有字段均为可选，同 `SSHAccountCreate`。

**响应**: `SSHAccount`

#### DELETE `/api/accounts/{alias}`

删除账户。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alias | string | 账户标识 |

**响应**: 204 No Content

#### GET `/api/accounts/exists`

检查是否已有账户。

**响应**:

```json
{
  "exists": true,
  "count": 3
}
```

#### GET `/api/accounts/default/info`

获取默认账户信息。

**响应**: `SSHAccount | null`

#### POST `/api/accounts/{alias}/test`

测试指定账户的连接。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alias | string | 账户标识 |

**响应**:

```json
{
  "alias": "prod-server",
  "success": true,
  "message": "连接成功"
}
```

#### POST `/api/accounts/test-connection`

测试连接（不保存账户）。

**请求体**: `SSHAccountCreate`

**响应**:

```json
{
  "success": true,
  "message": "连接成功"
}
```

#### POST `/api/accounts/{alias}/default`

设置指定账户为默认账户。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alias | string | 账户标识 |

**响应**: `SSHAccount`

#### POST `/api/accounts/workplace/init`

初始化远程工作目录。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | 账户标识 |

**响应**:

```json
{
  "message": "工作目录已创建"
}
```

#### DELETE `/api/accounts/clear-all`

清除所有账户。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| confirm | string | 是 | 必须为 `"yes"` |

**响应**: 204 No Content

#### GET `/api/accounts/storage/info`

获取存储信息。

**响应**:

```json
{
  "home_directory": "/home/user/.opsv",
  "persist_directory": "/home/user/.opsv/accounts",
  "accounts_file_path": "/home/user/.opsv/accounts/accounts.json",
  "persist_dir_exists": true,
  "accounts_file_exists": true,
  "accounts_count": 3
}
```

### 2.2 账户分组

#### GET `/api/accounts/groups` 或 GET `/api/accounts/groups/list`

获取所有分组。

**响应**: `AccountGroup[]`

```json
[
  {
    "name": "production",
    "accounts": ["prod-server", "prod-backup"]
  }
]
```

#### POST `/api/accounts/groups`

创建分组。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 分组名称 |
| accounts | string[] | 否 | 账户标识列表 |

**响应**: `AccountGroup` (201)

#### DELETE `/api/accounts/groups/{name}`

删除分组。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| name | string | 分组名称 |

**响应**: 204 No Content

### 2.3 审计日志

#### GET `/api/accounts/audit/logs`

获取操作审计日志。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 否 | 按账户筛选 |
| limit | integer | 否 | 返回条数，默认 100 |

**响应**: `AuditLog[]`

```json
[
  {
    "timestamp": "2026-01-15T10:30:00",
    "account_alias": "prod-server",
    "action": "connect",
    "status": "success",
    "detail": "SSH 连接成功"
  }
]
```

---

## 3. 项目管理

### GET `/api/projects`

获取所有项目配置。

**响应**: `ProjectConfig[]`

```json
[
  {
    "alias": "my-service",
    "local_path": "/home/dev/projects/my-service",
    "remote_path": "/opt/apps/my-service",
    "ssh_alias": "prod-server",
    "created_at": "2026-01-15T10:00:00",
    "updated_at": "2026-01-15T10:00:00"
  }
]
```

### POST `/api/projects`

创建项目。

**请求体** (`ProjectConfigCreate`):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | 项目标识 |
| local_path | string | 否 | 本地路径 |
| remote_path | string | 否 | 远程路径 |
| ssh_alias | string | 否 | 关联的 SSH 账户 |

**响应**: `ProjectConfig` (201)

### GET `/api/projects/{alias}`

获取项目详情。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alias | string | 项目标识 |

**响应**: `ProjectConfig`

### PUT `/api/projects/{alias}`

更新项目配置。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alias | string | 项目标识 |

**请求体** (`ProjectConfigUpdate`): 所有字段可选，同 `ProjectConfigCreate`。

**响应**: `ProjectConfig`

### DELETE `/api/projects/{alias}`

删除项目。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alias | string | 项目标识 |

**响应**: 204 No Content

---

## 4. 文件同步

### POST `/api/sync/start`

启动文件同步任务。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| local_path | string | 是 | 本地目录路径 |
| remote_path | string | 是 | 远程目录路径 |
| account_alias | string | 是 | SSH 账户标识 |
| force | boolean | 否 | 是否强制全量同步 |

**响应**:

```json
{
  "sync_id": "sync_abc123",
  "message": "同步任务已启动"
}
```

### GET `/api/sync/status/{sync_id}`

查询同步状态。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| sync_id | string | 同步任务 ID |

**响应**: 同步状态对象

### GET `/api/sync/status`

查询同步状态（替代方式）。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sync_id | string | 否 | 同步任务 ID |

**响应**: 同步状态对象

### POST `/api/sync/stop`

停止同步任务。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sync_id | string | 是 | 同步任务 ID |

**响应**:

```json
{
  "success": true,
  "message": "同步任务已停止"
}
```

### WebSocket `/api/sync/ws/status`

实时同步状态推送。

**客户端发送**:

```json
{ "sync_id": "sync_abc123" }
```

**服务端推送**:

```json
{
  "type": "connected",
  "sync_id": "sync_abc123",
  "status": "syncing"
}
```

---

## 5. 编译运行

### POST `/api/build/compile`

启动编译任务。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| project_path | string | 是 | 远程项目路径 |
| local_path | string | 否 | 本地项目路径 |
| command | string | 否 | 自定义编译命令 |
| jdk_version | string | 否 | JDK 版本 |

**响应**: `BuildTaskResponse`

```json
{
  "task_id": "build_xyz789",
  "account_alias": "prod-server",
  "project_path": "/opt/apps/my-service",
  "action": "compile",
  "status": "running",
  "log": "",
  "started_at": "2026-01-15T10:30:00"
}
```

### POST `/api/build/test`

启动测试任务。

**请求体**: 同 compile，action 为 `test`。

**响应**: `BuildTaskResponse`

### POST `/api/build/package`

打包项目。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| project_path | string | 是 | 远程项目路径 |
| command | string | 否 | 自定义打包命令 |

**响应**: `BuildTaskResponse`

### POST `/api/build/run/jar`

运行 JAR 包。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| project_path | string | 是 | 远程项目路径 |
| jar_path | string | 是 | JAR 文件路径 |
| jvm_args | string | 否 | JVM 参数 |
| app_args | string | 否 | 应用参数 |
| local_path | string | 否 | 本地项目路径 |
| jdk_version | string | 否 | JDK 版本 |
| server_port | integer | 否 | 服务端口 |

**响应**: `BuildTaskResponse`

### POST `/api/build/run/spring-boot`

运行 Spring Boot 项目。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| project_path | string | 是 | 远程项目路径 |
| main_class | string | 否 | 主类全限定名 |
| local_path | string | 否 | 本地项目路径 |
| jdk_version | string | 否 | JDK 版本 |
| server_port | integer | 否 | 服务端口 |

**响应**: `BuildTaskResponse`

### POST `/api/build/run/exec`

直接运行 Java 类。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| project_path | string | 是 | 远程项目路径 |
| main_class | string | 是 | 主类全限定名 |

**响应**: `BuildTaskResponse`

### POST `/api/build/run`

通用运行接口。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| project_path | string | 是 | 远程项目路径 |
| local_path | string | 否 | 本地项目路径 |
| run_mode | string | 否 | `spring-boot` / `jar` / `exec` |
| jar_path | string | 否 | JAR 路径（run_mode=jar 时必填） |
| main_class | string | 否 | 主类（run_mode=spring-boot/exec 时必填） |
| jvm_args | string | 否 | JVM 参数 |
| app_args | string | 否 | 应用参数 |
| jdk_version | string | 否 | JDK 版本 |
| server_port | integer | 否 | 服务端口 |

**响应**: `BuildTaskResponse`

### POST `/api/build/stop/{task_id}`

停止构建/运行任务。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务 ID |

**响应**:

```json
{
  "task_id": "build_xyz789",
  "status": "stopped",
  "message": "任务已停止"
}
```

### POST `/api/build/stop`

停止任务（Body 方式）。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务 ID |

**响应**: 同上

### GET `/api/build/status/{task_id}`

查询任务状态。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务 ID |

**响应**: `BuildTaskResponse`

### GET `/api/build/history`

获取构建历史。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 否 | 按账户筛选 |
| limit | integer | 否 | 返回条数，默认 50 |

**响应**:

```json
{
  "tasks": [
    {
      "task_id": "build_xyz789",
      "account_alias": "prod-server",
      "project_path": "/opt/apps/my-service",
      "action": "compile",
      "status": "completed",
      "exit_code": 0,
      "log": "...",
      "started_at": "2026-01-15T10:30:00",
      "completed_at": "2026-01-15T10:32:00"
    }
  ]
}
```

### GET `/api/build/log/{task_id}`

获取任务日志。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务 ID |

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| max_lines | integer | 否 | 最大行数，默认 500 |

**响应**:

```json
{
  "task_id": "build_xyz789",
  "log": "[INFO] Building...\n[INFO] BUILD SUCCESS"
}
```

### WebSocket `/api/build/ws/logs/{task_id}`

实时构建日志流。

**客户端发送**:

```json
{ "type": "ping" }
```

**服务端推送**:

```json
{
  "type": "log_update",
  "data": "[INFO] Compiling...\n"
}
```

---

## 6. 环境管理

### GET `/api/environment/check`

检查远程环境（JDK/Maven）。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| project_path | string | 是 | 远程项目路径 |
| jdk_version | string | 否 | 期望的 JDK 版本 |

**响应**:

```json
{
  "account_alias": "prod-server",
  "project_path": "/opt/apps/my-service",
  "java": {
    "installed": true,
    "version": "17.0.2",
    "path": "/usr/lib/jvm/java-17/bin/java"
  },
  "maven": {
    "installed": true,
    "version": "3.9.5",
    "path": "/usr/bin/mvn"
  },
  "all_ready": true
}
```

### POST `/api/environment/install`

安装环境组件。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| java_version | string | 否 | JDK 版本 |
| project_path | string | 否 | 远程项目路径 |
| dnf_mirror | string | 否 | DNF 镜像源 |
| proxy | string | 否 | 代理地址 |

**响应**: `TaskStatusResponse`

```json
{
  "task_id": "env_install_abc",
  "account_alias": "prod-server",
  "components": ["java-17", "maven"],
  "status": "running",
  "progress": 0.0,
  "message": "开始安装..."
}
```

### GET `/api/environment/status`

查询安装任务状态。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务 ID |

**响应**: `TaskStatusResponse`

### WebSocket `/api/environment/ws/status`

实时安装状态推送。

**客户端发送**:

```json
{ "type": "subscribe", "task_id": "env_install_abc" }
```

**服务端推送**:

```json
{
  "type": "status_update",
  "task_id": "env_install_abc",
  "data": {
    "status": "running",
    "progress": 0.5,
    "message": "正在安装 Maven..."
  }
}
```

---

## 7. 文件管理

### 7.1 文件操作

#### GET `/api/files/list`

列出远程目录内容。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 目录路径 |

**响应**:

```json
{
  "path": "/opt/apps",
  "entries": [
    {
      "name": "my-service",
      "path": "/opt/apps/my-service",
      "is_dir": true,
      "size": 4096,
      "permission": "drwxr-xr-x",
      "owner": "root",
      "group": "root",
      "modified": "2026-01-15T10:00:00"
    }
  ]
}
```

#### GET `/api/files/stat`

获取文件/目录详细信息。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 文件路径 |

**响应**:

```json
{
  "path": "/opt/apps/config.yml",
  "is_dir": false,
  "is_file": true,
  "is_link": false,
  "size": 1024,
  "permissions": "-rw-r--r--",
  "permission_mode": "0644",
  "modify_time": "2026-01-15T10:00:00",
  "owner": "root",
  "group": "root"
}
```

#### GET `/api/files/content`

读取文件内容。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 文件路径 |

**响应**:

```json
{
  "path": "/opt/apps/config.yml",
  "content": "server:\n  port: 8080"
}
```

#### POST `/api/files/content`

保存文件内容。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 文件路径 |
| content | string | 是 | 文件内容 |

**响应**:

```json
{
  "path": "/opt/apps/config.yml",
  "status": "saved"
}
```

#### POST `/api/files/mkdir`

创建目录。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 目录路径 |

**响应**:

```json
{
  "path": "/opt/apps/new-dir",
  "status": "created"
}
```

#### POST `/api/files/delete`

删除文件/目录。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 文件路径 |

**响应**:

```json
{
  "path": "/opt/apps/old-file",
  "status": "deleted"
}
```

#### POST `/api/files/rename`

重命名/移动文件。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| src | string | 是 | 源路径 |
| dst | string | 是 | 目标路径 |

**响应**:

```json
{
  "src": "/opt/apps/old-name",
  "dst": "/opt/apps/new-name",
  "status": "renamed"
}
```

#### POST `/api/files/copy`

复制文件。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| src | string | 是 | 源路径 |
| dst | string | 是 | 目标路径 |

**响应**:

```json
{
  "src": "/opt/apps/file.txt",
  "dst": "/opt/apps/file-copy.txt",
  "status": "copied"
}
```

#### POST `/api/files/chmod`

修改文件权限。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 文件路径 |
| mode | string | 是 | 权限模式，如 `0755` |

**响应**:

```json
{
  "path": "/opt/apps/script.sh",
  "mode": "0755",
  "status": "changed"
}
```

#### POST `/api/files/chown`

修改文件所有者。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 文件路径 |
| user | string | 否 | 用户名 |
| group | string | 否 | 组名 |

**响应**:

```json
{
  "path": "/opt/apps/file.txt",
  "user": "appuser",
  "group": "appgroup",
  "status": "changed"
}
```

#### POST `/api/files/upload`

上传文件。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| remote_path | string | 是 | 远程目标路径 |
| local_path | string | 是 | 本地源路径 |

**响应**:

```json
{
  "local_path": "/home/dev/file.txt",
  "remote_path": "/opt/apps/file.txt",
  "status": "uploaded"
}
```

#### GET `/api/files/download`

下载文件。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| remote_path | string | 是 | 远程源路径 |
| local_path | string | 是 | 本地目标路径 |

**响应**:

```json
{
  "remote_path": "/opt/apps/file.txt",
  "local_path": "/home/dev/file.txt",
  "status": "downloaded"
}
```

#### GET `/api/files/search`

搜索文件。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 搜索起始路径 |
| pattern | string | 是 | 搜索模式（通配符） |
| max_depth | integer | 否 | 最大搜索深度 |
| file_type | string | 否 | 文件类型筛选 |

**响应**:

```json
{
  "path": "/opt/apps",
  "pattern": "*.yml",
  "results": [
    {
      "path": "/opt/apps/config.yml",
      "name": "config.yml",
      "is_dir": false,
      "size": 1024,
      "permissions": "0644",
      "modify_time": "2026-01-15T10:00:00"
    }
  ]
}
```

### 7.2 批量操作

#### POST `/api/files/batch/delete`

批量删除文件。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| paths | string[] | 是 | 文件路径列表 |

**响应**: 操作结果列表

#### POST `/api/files/batch/chmod`

批量修改权限。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| paths | string[] | 是 | 文件路径列表 |
| mode | string | 是 | 权限模式 |

**响应**: 操作结果列表

### 7.3 命令执行

#### POST `/api/command/exec`

执行远程命令。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| command | string | 是 | 命令内容 |
| timeout | number | 否 | 超时时间（秒），默认 30 |

**响应**:

```json
{
  "stdout": "output text",
  "stderr": "",
  "exit_code": 0
}
```

#### POST `/api/command/exec/batch`

批量执行命令。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| commands | string[] | 是 | 命令列表 |
| timeout | number | 否 | 超时时间（秒），默认 60 |

**响应**:

```json
{
  "results": [
    { "stdout": "result1", "stderr": "", "exit_code": 0 },
    { "stdout": "result2", "stderr": "", "exit_code": 0 }
  ]
}
```

#### GET `/api/command/history`

获取命令执行历史。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 否 | 按账户筛选 |
| limit | integer | 否 | 返回条数，默认 100 |

**响应**:

```json
{
  "records": [
    {
      "timestamp": "2026-01-15T10:30:00",
      "account_alias": "prod-server",
      "command": "ls -la",
      "exit_code": 0,
      "stdout": "...",
      "stderr": ""
    }
  ]
}
```

### 7.4 权限检查

#### GET `/api/permission/check`

检查文件权限。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 文件路径 |

**响应**:

```json
{
  "path": "/opt/apps/file.txt",
  "exists": true,
  "readable": true,
  "writable": true,
  "executable": false,
  "permissions": "0644",
  "owner": "root",
  "group": "root",
  "current_user": "appuser"
}
```

#### GET `/api/permission/user`

获取远程用户信息。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{
  "username": "appuser",
  "uid": 1000,
  "gid": 1000,
  "groups": ["appuser", "docker"],
  "home": "/home/appuser",
  "shell": "/bin/bash",
  "is_root": false
}
```

#### GET `/api/permission/sudo`

检查 sudo 权限。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{
  "alias": "prod-server",
  "has_sudo": true
}
```

### 7.5 书签管理

#### GET `/api/bookmarks`

获取书签列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 否 | 按账户筛选 |

**响应**:

```json
{
  "bookmarks": [
    {
      "alias": "prod-server",
      "path": "/opt/apps",
      "label": "应用目录",
      "created_at": "2026-01-15T10:00:00"
    }
  ]
}
```

#### POST `/api/bookmarks`

添加书签。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 目录路径 |
| label | string | 是 | 书签名称 |

**响应**: 书签对象 (201)

#### DELETE `/api/bookmarks`

删除书签。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| path | string | 是 | 目录路径 |

**响应**:

```json
{
  "alias": "prod-server",
  "path": "/opt/apps",
  "status": "removed"
}
```

### 7.6 操作历史

#### GET `/api/operations/history`

获取文件操作历史。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 否 | 按账户筛选 |
| limit | integer | 否 | 返回条数，默认 100 |

**响应**:

```json
{
  "records": [
    {
      "timestamp": "2026-01-15T10:30:00",
      "account_alias": "prod-server",
      "action": "delete",
      "path": "/opt/apps/old-file",
      "status": "success",
      "detail": "文件已删除"
    }
  ]
}
```

---

## 8. Docker 管理

### 8.1 Docker 环境

#### GET `/api/docker/info`

获取 Docker 环境信息。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{
  "installed": true,
  "version": "24.0.7",
  "running": true,
  "permissions": {
    "can_run": true,
    "needs_sudo": false
  }
}
```

#### POST `/api/docker/install`

一键安装 Docker。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{
  "message": "Docker 安装任务已启动"
}
```

### 8.2 容器管理

#### GET `/api/docker/containers`

获取容器列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| all | boolean | 否 | 是否包含已停止容器 |

**响应**: 容器列表

#### GET `/api/docker/containers/{container_id}`

获取容器详情。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| container_id | string | 容器 ID |

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**: 容器详情对象

#### POST `/api/docker/containers/{container_id}/start`

启动容器。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "容器已启动" }
```

#### POST `/api/docker/containers/{container_id}/stop`

停止容器。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| timeout | integer | 否 | 超时时间（秒） |

**响应**:

```json
{ "message": "容器已停止" }
```

#### POST `/api/docker/containers/{container_id}/restart`

重启容器。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "容器已重启" }
```

#### POST `/api/docker/containers/{container_id}/kill`

强制停止容器。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "容器已强制停止" }
```

#### DELETE `/api/docker/containers/{container_id}`

删除容器。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| force | boolean | 否 | 是否强制删除 |

**响应**:

```json
{ "message": "容器已删除" }
```

#### POST `/api/docker/containers/{container_id}/pause`

暂停容器。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "容器已暂停" }
```

#### POST `/api/docker/containers/{container_id}/unpause`

恢复容器。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "容器已恢复" }
```

#### GET `/api/docker/containers/{container_id}/logs`

获取容器日志。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| tail | integer | 否 | 返回行数，默认 100 |
| timestamps | boolean | 否 | 是否包含时间戳 |

**响应**:

```json
{
  "logs": "2026-01-15T10:00:00 Starting application...\n2026-01-15T10:00:01 Started successfully"
}
```

#### GET `/api/docker/containers/{container_id}/stats`

获取容器资源统计。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**: 容器统计对象（CPU、内存、网络等）

#### POST `/api/docker/containers/{container_id}/exec`

在容器中执行命令。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| command | string | 是 | 命令内容 |

**响应**:

```json
{
  "exit_code": 0,
  "stdout": "output",
  "stderr": ""
}
```

#### WebSocket `/api/docker/ws/containers/{container_id}/logs`

实时容器日志流。

**客户端发送**:

```json
{ "account_alias": "prod-server" }
```

**服务端推送**:

```json
{
  "type": "log",
  "data": "2026-01-15T10:00:00 Log line\n"
}
```

### 8.3 镜像管理

#### GET `/api/docker/images`

获取镜像列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**: 镜像列表

#### DELETE `/api/docker/images/{image_id}`

删除镜像。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "镜像已删除" }
```

#### POST `/api/docker/images/pull`

拉取镜像。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| image_name | string | 是 | 镜像名称 |

**响应**:

```json
{ "message": "镜像拉取任务已启动" }
```

#### POST `/api/docker/images/build`

构建镜像。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| tag | string | 是 | 镜像标签 |
| dockerfile_path | string | 是 | Dockerfile 路径 |
| context_path | string | 是 | 构建上下文路径 |

**响应**:

```json
{ "message": "镜像构建任务已启动" }
```

#### POST `/api/docker/images/prune`

清理未使用镜像。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**: 清理结果

#### GET `/api/docker/images/search`

搜索镜像。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| term | string | 是 | 搜索关键词 |

**响应**: 搜索结果列表

### 8.4 网络管理

#### GET `/api/docker/networks`

获取网络列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**: 网络列表

#### POST `/api/docker/networks`

创建网络。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| name | string | 是 | 网络名称 |
| driver | string | 否 | 驱动类型，默认 `bridge` |

**响应** (201):

```json
{
  "network_id": "net_abc123",
  "name": "my-network",
  "driver": "bridge"
}
```

#### GET `/api/docker/networks/{network_id}`

获取网络详情。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**: 网络详情对象

#### DELETE `/api/docker/networks/{network_id}`

删除网络。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "网络已删除" }
```

### 8.5 卷管理

#### GET `/api/docker/volumes`

获取卷列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**: 卷列表

#### POST `/api/docker/volumes`

创建卷。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| name | string | 是 | 卷名称 |

**响应** (201):

```json
{ "volume_name": "my-volume" }
```

#### GET `/api/docker/volumes/{volume_name}`

获取卷详情。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**: 卷详情对象

#### DELETE `/api/docker/volumes/{volume_name}`

删除卷。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "卷已删除" }
```

### 8.6 Compose 管理

#### GET `/api/docker/compose/projects`

获取 Compose 项目列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| search_path | string | 否 | 搜索路径，默认 `/` |

**响应**: Compose 项目列表

#### POST `/api/docker/compose/up`

启动 Compose 项目。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| project_path | string | 是 | Compose 文件路径 |
| detach | boolean | 否 | 是否后台运行 |

**响应**:

```json
{ "message": "Compose 项目已启动" }
```

#### POST `/api/docker/compose/down`

停止 Compose 项目。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 是 | SSH 账户标识 |
| project_path | string | 是 | Compose 文件路径 |

**响应**:

```json
{ "message": "Compose 项目已停止" }
```

---

## 9. 系统管理

### GET `/api/system/info`

获取系统信息。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{
  "hostname": "prod-server",
  "os": "CentOS Linux 7",
  "kernel": "3.10.0-1160.el7.x86_64",
  "uptime": "30 days, 5 hours"
}
```

### GET `/api/system/performance`

获取系统性能数据。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{
  "cpu": {
    "cores": 4,
    "model": "Intel Xeon E5-2680",
    "load_avg": [0.5, 0.3, 0.2]
  },
  "memory": {
    "total": 8589934592,
    "used": 4294967296,
    "percent": 50.0
  }
}
```

### GET `/api/system/disks`

获取磁盘信息。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{
  "disks": [
    {
      "mount": "/",
      "total": 53687091200,
      "used": 26843545600,
      "percent": 50.0
    }
  ]
}
```

### POST `/api/system/reboot`

重启服务器。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "服务器正在重启" }
```

### POST `/api/system/shutdown`

关闭服务器。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "服务器正在关闭" }
```

### POST `/api/system/reload/network`

重载网络配置。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "网络配置已重载" }
```

### POST `/api/system/reload/ssh`

重载 SSH 配置。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "SSH 配置已重载" }
```

### POST `/api/system/cache/clear`

清理系统缓存。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{ "message": "系统缓存已清理" }
```

### GET `/api/system/selinux`

获取 SELinux 状态。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**: SELinux 状态对象

### POST `/api/system/selinux`

设置 SELinux 模式。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| mode | string | 是 | `enforcing` / `permissive` |

**响应**:

```json
{ "message": "SELinux 模式已设置为 permissive" }
```

### GET `/api/system/firewall/status`

获取防火墙状态。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**: 防火墙状态对象

### POST `/api/system/firewall/set`

启用/禁用防火墙。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| enable | boolean | 是 | 是否启用 |

**响应**:

```json
{ "message": "防火墙已启用" }
```

### GET `/api/system/firewall/rules`

获取防火墙规则。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{
  "rules": [
    { "port": 8080, "protocol": "tcp", "zone": "public" }
  ]
}
```

### GET `/api/system/firewall/zones`

获取防火墙区域。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |

**响应**:

```json
{
  "zones": ["public", "internal", "trusted"]
}
```

### POST `/api/system/firewall/port`

开放/关闭端口。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| port | integer | 是 | 端口号 |
| protocol | string | 否 | 协议，默认 `tcp` |
| zone | string | 否 | 区域，默认 `public` |

**响应**:

```json
{ "message": "端口 8080/tcp 已开放" }
```

### DELETE `/api/system/firewall/port`

关闭端口。

**查询参数**: 同 POST

**响应**:

```json
{ "message": "端口 8080/tcp 已关闭" }
```

### POST `/api/system/firewall/service`

开放/关闭服务。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | SSH 账户标识 |
| service | string | 是 | 服务名称 |
| zone | string | 否 | 区域，默认 `public` |

**响应**:

```json
{ "message": "服务 http 已开放" }
```

### DELETE `/api/system/firewall/service`

关闭服务。

**查询参数**: 同 POST

**响应**:

```json
{ "message": "服务 http 已关闭" }
```

---

## 10. WebSSH 终端

### GET `/api/webssh/sessions`

获取会话列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| group | string | 否 | 按分组筛选 |

**响应**:

```json
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "account_alias": "prod-server",
      "host": "192.168.1.100",
      "port": 22,
      "username": "root",
      "status": "connected",
      "created_at": "2026-01-15T10:00:00",
      "last_active": "2026-01-15T10:30:00"
    }
  ],
  "count": 1,
  "groups": ["production"],
  "stats": {
    "total": 1,
    "connected": 1,
    "disconnected": 0
  }
}
```

### POST `/api/webssh/test`

测试 SSH 连接（不创建会话）。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account_alias | string | 否 | 使用已保存账户 |
| host | string | 条件 | 主机地址（无 account_alias 时必填） |
| port | integer | 否 | 端口，默认 22 |
| username | string | 条件 | 用户名（无 account_alias 时必填） |
| auth_type | string | 是 | `password` / `key` / `agent` |
| password | string | 条件 | 密码 |
| private_key | string | 条件 | 私钥 |
| key_passphrase | string | 否 | 私钥密码 |
| totp_secret | string | 否 | TOTP 密钥 |
| group | string | 否 | 分组 |

**响应**:

```json
{ "success": true, "message": "连接成功" }
```

### POST `/api/webssh/connect`

创建 SSH 会话。

**请求体**: 同 `/api/webssh/test`

**响应**:

```json
{
  "success": true,
  "session": {
    "session_id": "sess_abc123",
    "account_alias": "prod-server",
    "host": "192.168.1.100",
    "port": 22,
    "username": "root",
    "status": "connected",
    "created_at": "2026-01-15T10:00:00",
    "last_active": "2026-01-15T10:00:00"
  }
}
```

### POST `/api/webssh/disconnect`

断开 SSH 会话。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话 ID |

**响应**:

```json
{
  "success": true,
  "session_id": "sess_abc123"
}
```

### POST `/api/webssh/resize`

调整终端大小。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话 ID |
| width | integer | 是 | 宽度 (10-500) |
| height | integer | 是 | 高度 (5-200) |

**响应**:

```json
{ "success": true }
```

### POST `/api/webssh/command`

向终端发送命令。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话 ID |
| command | string | 是 | 命令内容 |

**响应**:

```json
{ "success": true }
```

### GET `/api/webssh/sessions/history`

获取会话历史。

**响应**:

```json
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "host": "192.168.1.100",
      "username": "root",
      "status": "disconnected",
      "created_at": "2026-01-15T10:00:00"
    }
  ],
  "count": 1
}
```

### DELETE `/api/webssh/sessions/history/{session_id}`

删除会话历史记录。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话 ID |

**响应**:

```json
{ "success": true }
```

### GET `/api/webssh/history`

获取命令历史。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 否 | 按会话筛选 |
| limit | integer | 否 | 返回条数，默认 50 |

**响应**:

```json
{
  "history": [
    {
      "timestamp": "2026-01-15T10:30:00",
      "command": "ls -la"
    }
  ],
  "count": 1
}
```

### WebSocket `/api/webssh/ws/{session_id}`

交互式终端 WebSocket。

**客户端发送**:

```json
// 输入命令
{ "type": "input", "data": "ls -la\n" }

// 调整终端大小
{ "type": "resize", "width": 120, "height": 40 }

// 心跳
{ "type": "ping" }

// 断开连接
{ "type": "disconnect" }
```

**服务端推送**:

```json
// 连接信息
{ "type": "info", "encoding": "utf-8", "session_id": "sess_abc123" }

// 终端输出
{ "type": "data", "content": "total 48\ndrwxr-xr-x  3 root root 4096 ..." }

// 断开通知
{ "type": "disconnected" }

// 心跳响应
{ "type": "pong" }
```

---

## 11. 远程驱动器

### GET `/api/remote-drive/status`

获取远程驱动器状态。

**响应**:

```json
{
  "enabled": true,
  "running": true,
  "port": 8081,
  "hostname": "localhost",
  "webdav_url": "http://localhost:8081/webdav",
  "windows_url": "\\\\localhost@8081\\webdav",
  "mounts": [
    {
      "alias": "prod-server",
      "hostname": "localhost",
      "port": 8081,
      "url": "http://localhost:8081/webdav/prod-server",
      "windows_url": "\\\\localhost@8081\\webdav\\prod-server"
    }
  ],
  "account_count": 1
}
```

---

## 12. 应用设置

### GET `/api/settings`

获取所有应用设置。

**响应**:

```json
{
  "session_ttl_hours": 72,
  "remote_drive_enabled": false,
  "remote_drive_port": 8081
}
```

### PUT `/api/settings`

更新应用设置。

**请求体** (所有字段可选):

| 字段 | 类型 | 说明 |
|------|------|------|
| session_ttl_hours | integer | 会话 TTL（小时），默认 72 |
| remote_drive_enabled | boolean | 是否启用远程驱动器 |
| remote_drive_port | integer | 远程驱动器端口 |

**响应**: 更新后的完整设置对象

---

## 附录

### A. 数据模型速查

#### SSHAccount

| 字段 | 类型 | 说明 |
|------|------|------|
| alias | string | 唯一标识 |
| host | string | 主机地址 |
| port | integer | 端口，默认 22 |
| username | string | 用户名 |
| auth_type | string | `password` / `key` / `agent` |
| password | string | 密码（加密存储） |
| private_key | string | 私钥（加密存储） |
| key_passphrase | string | 私钥密码 |
| totp_secret | string | TOTP 密钥 |
| is_default | boolean | 是否为默认 |
| group | string | 分组 |
| workplace_path | string | 工作目录 |

#### ProjectConfig

| 字段 | 类型 | 说明 |
|------|------|------|
| alias | string | 项目标识 |
| local_path | string | 本地路径 |
| remote_path | string | 远程路径 |
| ssh_alias | string | 关联 SSH 账户 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

#### BuildTaskResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务 ID |
| account_alias | string | SSH 账户 |
| project_path | string | 项目路径 |
| action | string | 操作类型 |
| status | string | 任务状态 |
| log | string | 日志内容 |
| exit_code | integer | 退出码 |
| pid | integer | 进程 ID |
| started_at | datetime | 开始时间 |
| completed_at | datetime | 完成时间 |

#### WebSSHSession

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话 ID |
| account_alias | string | 关联账户 |
| host | string | 主机地址 |
| port | integer | 端口 |
| username | string | 用户名 |
| status | string | `connecting` / `connected` / `disconnected` / `error` |
| created_at | datetime | 创建时间 |
| last_active | datetime | 最后活跃时间 |
| group | string | 分组 |

### B. WebSocket 端点汇总

| 端点 | 用途 |
|------|------|
| `/api/environment/ws/status` | 环境安装状态推送 |
| `/api/build/ws/logs/{task_id}` | 构建日志实时流 |
| `/api/sync/ws/status` | 同步状态实时推送 |
| `/api/docker/ws/containers/{container_id}/logs` | 容器日志实时流 |
| `/api/webssh/ws/{session_id}` | 交互式终端 I/O |

### C. 统计

| 类别 | REST 端点 | WebSocket 端点 |
|------|:-:|:-:|
| 健康检查 | 1 | 0 |
| SSH 账户 | 17 | 0 |
| 编译/环境 | 6 | 2 |
| 文件同步 | 4 | 1 |
| 文件管理 | 21 | 0 |
| 应用设置 | 2 | 0 |
| Docker | 22 | 1 |
| 系统管理 | 15 | 0 |
| 项目管理 | 5 | 0 |
| WebSSH | 9 | 1 |
| 远程驱动器 | 1 | 0 |
| **合计** | **103** | **5** |
