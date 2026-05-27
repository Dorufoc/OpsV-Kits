<template>
  <div class="vscode-page">
    <el-page-header title="OpsV-Kits" @back="goBack">
      <template #content>
        <span>Web VSCode</span>
        <el-tag v-if="status.running" type="success" size="small" style="margin-left: 8px;">运行中</el-tag>
        <el-tag v-else type="info" size="small" style="margin-left: 8px;">已停止</el-tag>
      </template>
      <template #extra>
        <div class="header-actions">
          <el-button
            v-if="!status.running"
            type="primary"
            size="small"
            @click="startVSCode"
            :loading="loading"
          >
            <el-icon><VideoPlay /></el-icon> 启动服务
          </el-button>
          <el-button
            v-else
            type="danger"
            size="small"
            @click="stopVSCode"
            :loading="loading"
          >
            <el-icon><VideoPause /></el-icon> 停止服务
          </el-button>
          <el-button
            v-if="status.running"
            type="primary"
            size="small"
            @click="openVSCode"
          >
            <el-icon><FullScreen /></el-icon> 新窗口打开
          </el-button>
        </div>
      </template>
    </el-page-header>

    <el-divider />

    <!-- 服务控制面板 -->
    <el-card shadow="never" class="control-card" v-if="!status.running">
      <template #header>
        <span><el-icon :size="16"><Setting /></el-icon> 服务配置</span>
      </template>

      <el-form :model="config" label-width="120px" size="small">
        <el-form-item label="服务端口">
          <el-input-number v-model="config.port" :min="1024" :max="65535" style="width: 150px" />
          <span class="form-tip">code-server 监听端口（默认 8082）</span>
        </el-form-item>

        <el-form-item label="工作目录">
          <el-input v-model="config.workDir" placeholder="默认为项目根目录" style="width: 400px">
            <template #append>
              <el-button @click="selectWorkDir">选择目录</el-button>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="认证方式">
          <el-switch
            v-model="config.enableAuth"
            active-text="密码认证"
            inactive-text="无认证（仅本地）"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="startVSCode" :loading="loading">
            <el-icon><VideoPlay /></el-icon> 启动 Web VSCode
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="status.error"
        :title="status.error"
        type="error"
        :closable="false"
        style="margin-top: 16px"
      />
    </el-card>

    <!-- 运行状态面板 -->
    <el-card shadow="never" class="status-card" v-else>
      <template #header>
        <span><el-icon :size="16"><Monitor /></el-icon> 服务状态</span>
      </template>

      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">访问地址：</span>
          <el-link type="primary" :href="status.url" target="_blank">{{ status.url }}</el-link>
          <el-button size="small" text @click="copyUrl" style="margin-left: 8px;">
            <el-icon><DocumentCopy /></el-icon>
          </el-button>
        </div>
        <div class="status-item">
          <span class="status-label">服务端口：</span>
          <el-tag size="small">{{ status.port }}</el-tag>
        </div>
        <div class="status-item">
          <span class="status-label">进程 ID：</span>
          <el-tag size="small" type="info">{{ status.pid }}</el-tag>
        </div>
        <div class="status-item" v-if="authToken">
          <span class="status-label">认证密码：</span>
          <el-input
            v-model="authToken"
            readonly
            size="small"
            style="width: 300px"
            type="password"
            show-password
          >
            <template #append>
              <el-button @click="copyToken">
                <el-icon><DocumentCopy /></el-icon>
              </el-button>
            </template>
          </el-input>
        </div>
      </div>

      <el-divider />

      <div class="iframe-container">
        <iframe
          v-if="status.url"
          :src="status.url"
          class="vscode-iframe"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads"
          allow="clipboard-read; clipboard-write"
        ></iframe>
      </div>
    </el-card>

    <!-- 使用说明 -->
    <el-card shadow="never" class="help-card">
      <template #header>
        <span><el-icon :size="16"><InfoFilled /></el-icon> 使用说明</span>
      </template>

      <el-collapse accordion>
        <el-collapse-item title="📖 什么是 Web VSCode？" name="intro">
          <div class="help-content">
            <p>Web VSCode 基于 <a href="https://github.com/coder/code-server" target="_blank">code-server</a>，
            让您可以在浏览器中直接使用完整的 Visual Studio Code 功能，包括：</p>
            <ul>
              <li>代码编辑与语法高亮</li>
              <li>智能提示与代码补全</li>
              <li>终端与调试功能</li>
              <li>Git 版本控制</li>
              <li>插件扩展支持</li>
            </ul>
          </div>
        </el-collapse-item>

        <el-collapse-item title="⚠️ 安装 code-server" name="install">
          <div class="help-content">
            <p>首次使用前需要安装 code-server：</p>
            <h4>Windows（使用 npm）：</h4>
            <pre><code>npm install -g code-server</code></pre>

            <h4>Linux / macOS（使用官方脚本）：</h4>
            <pre><code>curl -fsSL https://code-server.dev/install.sh | sh</code></pre>

            <p>安装完成后，刷新本页面即可启动服务。</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="🔒 安全说明" name="security">
          <div class="help-content">
            <ul>
              <li>code-server 默认只监听 <code>127.0.0.1</code>（本机），其他设备无法直接访问</li>
              <li>建议启用密码认证，防止未授权访问</li>
              <li>工作目录默认设置为项目根目录，您可以修改为其他目录</li>
              <li>停止服务时会自动清理临时配置文件</li>
            </ul>
          </div>
        </el-collapse-item>

        <el-collapse-item title="📝 快捷键" name="shortcuts">
          <div class="help-content">
            <p>Web VSCode 支持大部分 VS Code 快捷键：</p>
            <ul>
              <li><kbd>Ctrl+P</kbd> / <kbd>Cmd+P</kbd> - 快速打开文件</li>
              <li><kbd>Ctrl+Shift+P</kbd> / <kbd>Cmd+Shift+P</kbd> - 命令面板</li>
              <li><kbd>Ctrl+`</kbd> - 打开/关闭终端</li>
              <li><kbd>Ctrl+S</kbd> / <kbd>Cmd+S</kbd> - 保存文件</li>
              <li><kbd>F1</kbd> - 显示所有命令</li>
            </ul>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  VideoPlay,
  VideoPause,
  FullScreen,
  Setting,
  Monitor,
  DocumentCopy,
  InfoFilled,
} from '@element-plus/icons-vue'
import { request } from '@/api'

const router = useRouter()

// 状态
const loading = ref(false)
const status = ref({
  running: false,
  port: 8082,
  pid: null as number | null,
  url: '',
  error: '',
})
const authToken = ref('')

// 配置
const config = ref({
  port: 8082,
  workDir: '',
  enableAuth: true,
})

// 定时器
let statusTimer: number | null = null

function goBack() {
  router.push('/')
}

async function fetchStatus() {
  try {
    const res = await request.get('/vscode/status')
    status.value = res
    if (!res.running) {
      authToken.value = ''
    }
  } catch (error) {
    console.error('Failed to fetch status:', error)
  }
}

async function startVSCode() {
  loading.value = true
  try {
    const res = await request.post('/vscode/start', {
      port: config.value.port,
      work_dir: config.value.workDir || undefined,
      enable_auth: config.value.enableAuth,
    })

    if (res.success) {
      status.value = res.status
      authToken.value = res.auth_token || ''
      ElMessage.success('Web VSCode 启动成功')
    } else {
      status.value = res.status
      ElMessage.error(res.status.error || '启动失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '启动失败')
  } finally {
    loading.value = false
  }
}

async function stopVSCode() {
  try {
    await ElMessageBox.confirm(
      '确定要停止 Web VSCode 服务吗？未保存的文件可能会丢失。',
      '确认停止',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
  } catch {
    return
  }

  loading.value = true
  try {
    const res = await request.post('/vscode/stop')
    status.value = res
    authToken.value = ''
    ElMessage.success('Web VSCode 已停止')
  } catch (error: any) {
    ElMessage.error(error.message || '停止失败')
  } finally {
    loading.value = false
  }
}

function openVSCode() {
  if (status.value.url) {
    window.open(status.value.url, '_blank')
  }
}

function selectWorkDir() {
  // 由于浏览器安全限制，无法直接选择本地目录
  // 这里使用 input 提示用户输入路径
  ElMessageBox.prompt(
    '请输入工作目录的绝对路径（留空使用项目根目录）：',
    '选择工作目录',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: config.value.workDir,
    }
  )
    .then(({ value }) => {
      config.value.workDir = value
    })
    .catch(() => {})
}

async function copyUrl() {
  if (!status.value.url) return
  try {
    await navigator.clipboard.writeText(status.value.url)
    ElMessage.success('地址已复制')
  } catch {
    ElMessage.warning('复制失败')
  }
}

async function copyToken() {
  if (!authToken.value) return
  try {
    await navigator.clipboard.writeText(authToken.value)
    ElMessage.success('密码已复制')
  } catch {
    ElMessage.warning('复制失败')
  }
}

onMounted(() => {
  fetchStatus()
  // 每 5 秒刷新一次状态
  statusTimer = window.setInterval(fetchStatus, 5000)
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
  }
})
</script>

<style scoped>
.vscode-page { padding: 0; }

.header-actions {
  display: flex;
  gap: 8px;
}

.control-card,
.status-card,
.help-card {
  margin-bottom: 16px;
}

.control-card :deep(.el-card__header),
.status-card :deep(.el-card__header),
.help-card :deep(.el-card__header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  font-weight: 600;
  font-size: 14px;
}

.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.status-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  font-size: 13px;
}

.status-label {
  color: #606266;
  min-width: 100px;
}

.iframe-container {
  width: 100%;
  height: calc(100vh - 400px);
  min-height: 500px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.vscode-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.help-content {
  font-size: 13px;
  line-height: 1.8;
  color: #303133;
}

.help-content h4 {
  font-size: 14px;
  margin: 12px 0 6px;
  color: #303133;
}

.help-content p {
  margin: 4px 0;
  color: #606266;
}

.help-content ul {
  margin: 4px 0;
  padding-left: 20px;
}

.help-content li {
  margin: 3px 0;
}

.help-content code {
  background: #f5f7fa;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 12px;
  color: #e6a23c;
  font-family: Consolas, monospace;
}

.help-content pre {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
}

.help-content pre code {
  background: none;
  padding: 0;
}

.help-content kbd {
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 3px;
  padding: 2px 6px;
  font-size: 12px;
  font-family: Consolas, monospace;
}

.help-content a {
  color: #409eff;
  text-decoration: none;
}

.help-content a:hover {
  text-decoration: underline;
}
</style>
