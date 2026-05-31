# OpsV-Kits 测试指南

## 测试架构

本项目采用分层测试策略：

```
tests/
├── backend/                    # 后端单元测试
│   ├── test_health.py         # 健康检查
│   ├── test_docker.py         # Docker管理
│   ├── test_docker_store.py   # Docker应用商店
│   ├── test_ssh_account.py    # SSH账户管理
│   ├── test_process.py        # 进程管理
│   ├── test_monitor_*.py      # 资源监控
│   ├── test_project.py        # 项目部署
│   ├── test_build.py          # 构建服务
│   ├── test_sync.py           # 文件同步
│   ├── test_file_manager.py   # 文件管理
│   ├── test_settings.py       # 系统设置
│   ├── test_webssh.py         # WebSSH终端
│   ├── test_db_toolkit.py     # 数据库工具
│   ├── test_cron_backup.py    # 定时备份
│   ├── test_security.py       # 安全配置
│   ├── test_vite_deploy.py    # Vite部署
│   ├── test_remote_drive.py   # 远程磁盘
│   ├── test_port.py           # 端口管理
│   └── test_system.py         # 系统信息
├── frontend/                   # 前端测试
│   ├── tests/                 # Vitest单元测试
│   │   ├── api.test.ts        # API客户端
│   │   ├── stores/            # Pinia状态管理
│   │   │   ├── dockerStore.test.ts
│   │   │   ├── sshAccountStore.test.ts
│   │   │   ├── monitorStore.test.ts
│   │   │   ├── processStore.test.ts
│   │   │   ├── projectStore.test.ts
│   │   │   ├── buildStore.test.ts
│   │   │   ├── viteDeployStore.test.ts
│   │   │   ├── syncStore.test.ts
│   │   │   └── settingsStore.test.ts
│   │   └── router.test.ts     # 路由配置
│   ├── screenshots/           # 视觉测试截图
│   ├── test_pages.py          # Playwright页面测试
│   ├── comprehensive_test.py  # 综合E2E测试
│   └── run_frontend_tests.py  # E2E测试运行脚本
└── conftest.py                # 共享测试配置
```

## 快速开始

### 运行所有测试

```bash
# 运行全部测试
python run_all_tests.py --all

# 仅运行后端测试
python run_all_tests.py --backend

# 仅运行前端单元测试
python run_all_tests.py --frontend

# 生成覆盖率报告
python run_all_tests.py --all --coverage
```

### 后端测试

```bash
# 运行所有后端测试
python -m pytest tests/backend/ -v

# 运行特定模块测试
python -m pytest tests/backend/test_docker.py -v
python -m pytest tests/backend/test_process.py -v

# 生成覆盖率报告
python -m pytest tests/backend/ --cov=backend/app --cov-report=html
```

### 前端测试

```bash
# 安装测试依赖
cd frontend
npm install --save-dev vitest @vue/test-utils jsdom @vitejs/plugin-vue

# 运行单元测试
npx vitest run

# 监听模式运行测试
npx vitest

# 生成覆盖率报告
npx vitest run --coverage
```

## 测试覆盖统计

### 后端API覆盖

| 模块 | 端点数量 | 测试数量 | 覆盖率 |
|------|----------|----------|--------|
| health | 1 | 2 | 100% |
| docker | 25+ | 40+ | 95%+ |
| docker_store | 7 | 30 | 100% |
| ssh_account | 15+ | 35+ | 95%+ |
| process | 10 | 35+ | 100% |
| monitor | 15+ | 20+ | 90%+ |
| project | 10+ | 25+ | 95%+ |
| build | 8+ | 15+ | 90%+ |
| sync | 5 | 15+ | 100% |
| file_manager | 10+ | 20+ | 90%+ |
| settings | 5 | 15+ | 100% |
| webssh | 8 | 15+ | 95%+ |
| db_toolkit | 10+ | 15+ | 90%+ |
| cron_backup | 18+ | 70 | 95%+ |
| security | 20+ | 60+ | 95%+ |
| vite_deploy | 10 | 47 | 100% |
| remote_drive | 1 | 7 | 100% |
| port | 4 | 30 | 100% |
| system | 10+ | 15+ | 90%+ |

**总计：600+ 测试用例，覆盖所有后端API端点**

### 前端测试覆盖

| 模块 | 测试类型 | 测试数量 |
|------|----------|----------|
| API客户端 | 单元测试 | 15+ |
| dockerStore | Store测试 | 10+ |
| sshAccountStore | Store测试 | 15+ |
| monitorStore | Store测试 | 10+ |
| processStore | Store测试 | 12+ |
| projectStore | Store测试 | 10+ |
| buildStore | Store测试 | 8+ |
| viteDeployStore | Store测试 | 10+ |
| syncStore | Store测试 | 8+ |
| settingsStore | Store测试 | 8+ |
| router | 路由测试 | 10+ |
| 组件 | 组件测试 | 10+ |

**总计：150+ 前端测试用例**

## 测试约定

### 后端测试

- 使用 `pytest` + `httpx` + `TestClient`
- 所有外部服务调用使用 `unittest.mock.patch` 模拟
- 测试文件命名：`test_<module>.py`
- 测试类命名：`Test<ModuleName>`
- 测试函数命名：`test_<action>_<scenario>`
- 使用 `@pytest.fixture` 提供共享测试数据

### 前端测试

- 使用 `vitest` + `@vue/test-utils`
- 所有API调用使用 `vi.mock` 模拟
- 测试文件命名：`<module>.test.ts`
- 使用 `beforeEach` 重置Pinia状态
- 使用 `createPinia` + `setActivePinia` 模式

## CI/CD集成

在CI环境中运行测试：

```bash
# 安装依赖
pip install -r tests/requirements.txt
cd frontend && npm ci && cd ..

# 运行测试
python run_all_tests.py --all --coverage

# 检查退出码
echo $?  # 0表示所有测试通过
```
