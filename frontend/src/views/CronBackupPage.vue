<template>
  <div class="cron-backup-page">
    <Md3PageHeader title="计划任务与备份">
      <template #subtitle>
        <span>Cron 任务调度、自动化备份与日志保留策略</span>
      </template>
      <template #actions>
        <Md3Select
          v-model="selectedAlias"
          :options="sshOptions"
          placeholder="选择服务器"
          style="width: 260px"
          @update:model-value="onAccountChange"
        />
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <template v-if="selectedAlias">
      <Md3Tabs v-model="activeTab" :tabs="tabItems" class="page-tabs" />

      <div class="tab-content">
        <!-- 计划任务 -->
        <template v-if="activeTab === 'cron'">
          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="schedule" class="header-icon" /> 计划任务列表</span>
              <div class="card-header-right">
                <Md3Input
                  v-model="cronSearch"
                  placeholder="搜索任务名称"
                  class="search-input"
                  type="search"
                >
                  <template #prefix>
                    <Md3Icon name="search" size="16" />
                  </template>
                </Md3Input>
                <Md3Button size="sm" variant="primary" @click="openCronDialog()">
                  <Md3Icon name="plus" size="1em" />新建任务
                </Md3Button>
              </div>
            </template>

            <Md3Table
              :columns="cronColumns"
              :data="filteredCronJobs"
              stripe
              max-height="480"
              empty-text="暂无计划任务"
            >
              <template #status="{ row }">
                <Md3Switch
                  :model-value="(row as any).status === 'enabled'"
                  @update:model-value="toggleCronStatus((row as any), $event)"
                />
              </template>
              <template #task_type="{ row }">
                <Md3Tag :type="(row as any).task_type === 'shell' ? 'primary' : 'info'" size="sm">
                  {{ (row as any).task_type === 'shell' ? 'Shell' : 'URL' }}
                </Md3Tag>
              </template>
              <template #last_run="{ row }">
                <span :class="{ 'text-danger': (row as any).last_run_status === 'failed' }">
                  {{ (row as any).last_run_at || '-' }}
                </span>
              </template>
              <template #action="{ row }">
                <div class="action-buttons">
                  <Md3Button size="sm" variant="text" @click="openCronDialog((row as any))">编辑</Md3Button>
                  <Md3Button size="sm" variant="text" @click="showCronLogs((row as any))">日志</Md3Button>
                  <Md3Button size="sm" variant="danger" @click="deleteCron((row as any))">删除</Md3Button>
                </div>
              </template>
            </Md3Table>
          </Md3Card>
        </template>

        <!-- 备份策略 -->
        <template v-if="activeTab === 'backup'">
          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="backup" class="header-icon" /> 备份策略列表</span>
              <div class="card-header-right">
                <Md3Input
                  v-model="backupSearch"
                  placeholder="搜索策略名称"
                  class="search-input"
                  type="search"
                >
                  <template #prefix>
                    <Md3Icon name="search" size="16" />
                  </template>
                </Md3Input>
                <Md3Button size="sm" variant="primary" @click="openBackupDialog()">
                  <Md3Icon name="plus" size="1em" />新建策略
                </Md3Button>
              </div>
            </template>

            <Md3Table
              :columns="backupColumns"
              :data="filteredBackupPolicies"
              stripe
              max-height="480"
              empty-text="暂无备份策略"
            >
              <template #backup_type="{ row }">
                <Md3Tag :type="backupTypeColor((row as any).backup_type)" size="sm">
                  {{ backupTypeLabel((row as any).backup_type) }}
                </Md3Tag>
              </template>
              <template #status="{ row }">
                <Md3Switch
                  :model-value="(row as any).status === 'enabled'"
                  @update:model-value="toggleBackupStatus((row as any), $event)"
                />
              </template>
              <template #action="{ row }">
                <div class="action-buttons">
                  <Md3Button
                    size="sm"
                    variant="primary"
                    :loading="store.runningBackup === (row as any).id"
                    @click="runBackup((row as any))"
                  >
                    立即备份
                  </Md3Button>
                  <Md3Button size="sm" variant="text" @click="openBackupDialog((row as any))">编辑</Md3Button>
                  <Md3Button size="sm" variant="text" @click="showBackupHistory((row as any))">历史</Md3Button>
                  <Md3Button size="sm" variant="danger" @click="deleteBackup((row as any))">删除</Md3Button>
                </div>
              </template>
            </Md3Table>
          </Md3Card>
        </template>

        <!-- 日志保留 -->
        <template v-if="activeTab === 'log'">
          <Md3Alert
            v-if="store.diskAlert?.has_alert"
            type="warning"
            title="磁盘空间告警"
            class="disk-alert-banner"
          >
            <template #message>
              <div class="disk-alert-content">
                <p>以下分区使用率超过 85%，建议配置日志保留策略：</p>
                <div class="disk-alert-list">
                  <Md3Tag
                    v-for="alert in store.diskAlert.alerts"
                    :key="alert.mount_point"
                    type="danger"
                    size="sm"
                  >
                    {{ alert.mount_point }}: {{ alert.use_percent }}%
                  </Md3Tag>
                </div>
              </div>
            </template>
          </Md3Alert>

          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="folder-open" class="header-icon" /> 日志保留策略</span>
              <div class="card-header-right">
                <Md3Input
                  v-model="logSearch"
                  placeholder="搜索规则名称"
                  class="search-input"
                  type="search"
                >
                  <template #prefix>
                    <Md3Icon name="search" size="16" />
                  </template>
                </Md3Input>
                <Md3Button size="sm" variant="primary" @click="openLogDialog()">
                  <Md3Icon name="plus" size="1em" />新建规则
                </Md3Button>
              </div>
            </template>

            <Md3Table
              :columns="logColumns"
              :data="filteredLogPolicies"
              stripe
              max-height="480"
              empty-text="暂无日志保留策略"
            >
              <template #cleanup_action="{ row }">
                <Md3Tag :type="cleanupActionColor((row as any).cleanup_action)" size="sm">
                  {{ cleanupActionLabel((row as any).cleanup_action) }}
                </Md3Tag>
              </template>
              <template #status="{ row }">
                <Md3Switch
                  :model-value="(row as any).status === 'enabled'"
                  @update:model-value="toggleLogStatus((row as any), $event)"
                />
              </template>
              <template #action="{ row }">
                <div class="action-buttons">
                  <Md3Button size="sm" variant="text" @click="previewLogCleanup((row as any))">预览影响</Md3Button>
                  <Md3Button
                    size="sm"
                    variant="primary"
                    :loading="store.runningLogCleanup === (row as any).id"
                    @click="runLogCleanup((row as any))"
                  >
                    立即清理
                  </Md3Button>
                  <Md3Button size="sm" variant="text" @click="openLogDialog((row as any))">编辑</Md3Button>
                  <Md3Button size="sm" variant="danger" @click="deleteLog((row as any))">删除</Md3Button>
                </div>
              </template>
            </Md3Table>
          </Md3Card>
        </template>
      </div>
    </template>

    <Md3Empty v-else description="请先选择一个 SSH 服务器" :image-size="80" />

    <!-- Cron Job Dialog -->
    <Md3Dialog v-model:visible="cronDialogVisible" :title="cronDialogTitle" width="560px">
      <div class="dialog-form">
        <Md3Input v-model="cronForm.name" label="任务名称" placeholder="如：每日数据备份" />
        <div class="form-row">
          <Md3Select
            v-model="cronPreset"
            :options="cronPresetOptions"
            label="预设周期"
            style="width: 140px"
            @update:model-value="onCronPresetChange"
          />
          <Md3Input v-model="cronForm.cron_expression" label="Cron 表达式" placeholder="如：0 2 * * *" />
        </div>
        <Md3Select
          v-model="cronForm.task_type"
          :options="taskTypeOptions"
          label="任务类型"
        />
        <Md3Input
          v-if="cronForm.task_type === 'url'"
          v-model="cronForm.http_method"
          label="HTTP 方法"
          placeholder="GET 或 POST"
        />
        <Md3Input
          v-model="cronForm.command"
          :label="cronForm.task_type === 'shell' ? '命令 / 脚本路径' : 'URL 地址'"
          :placeholder="cronForm.task_type === 'shell' ? '如：/opt/scripts/backup.sh' : '如：https://api.example.com/task'"
        />
        <div class="form-field-inline">
          <span class="field-label">启用任务</span>
          <Md3Switch v-model="cronFormEnabled" />
        </div>
      </div>
      <template #footer>
        <Md3Button @click="cronDialogVisible = false">取消</Md3Button>
        <Md3Button variant="primary" @click="saveCronJob">保存</Md3Button>
      </template>
    </Md3Dialog>

    <!-- Backup Policy Dialog -->
    <Md3Dialog v-model:visible="backupDialogVisible" :title="backupDialogTitle" width="600px">
      <div class="dialog-form">
        <Md3Input v-model="backupForm.name" label="策略名称" placeholder="如：网站每日备份" />
        <Md3Select
          v-model="backupForm.backup_type"
          :options="backupTypeOptions"
          label="备份类型"
        />
        <Md3Input
          v-if="backupForm.backup_type === 'website' || backupForm.backup_type === 'custom'"
          v-model="backupForm.source_path"
          label="源路径"
          placeholder="如：/var/www/html 或 /data/app"
        />
        <template v-if="backupForm.backup_type === 'mysql' || backupForm.backup_type === 'postgresql'">
          <Md3Input v-model="backupForm.db_name" label="数据库名" placeholder="如：mydb" />
          <Md3Input v-model="backupForm.db_host" label="数据库主机" placeholder="默认 localhost" />
          <Md3Input v-model.number="backupForm.db_port" label="端口" type="number" placeholder="默认 3306 / 5432" />
          <Md3Input v-model="backupForm.db_username" label="用户名" placeholder="默认 root" />
        </template>
        <Md3Select
          v-model="backupForm.storage_type"
          :options="storageTypeOptions"
          label="存储类型"
        />
        <div v-if="backupForm.storage_type === 'local'" class="storage-config">
          <Md3Input v-model="backupStorageConfig.local_path" label="本地备份目录" placeholder="如：/backup" />
        </div>
        <div v-if="backupForm.storage_type === 'aliyun_oss'" class="storage-config">
          <Md3Input v-model="backupStorageConfig.bucket" label="Bucket 名称" />
          <Md3Input v-model="backupStorageConfig.access_key_id" label="AccessKey ID" />
          <Md3Input v-model="backupStorageConfig.access_key_secret" label="AccessKey Secret" type="password" />
          <Md3Input v-model="backupStorageConfig.endpoint" label="Endpoint" placeholder="如：oss-cn-hangzhou.aliyuncs.com" />
          <Md3Input v-model="backupStorageConfig.prefix" label="存储路径前缀" placeholder="如：backups/" />
        </div>
        <div v-if="backupForm.storage_type === 'tencent_cos'" class="storage-config">
          <Md3Input v-model="backupStorageConfig.bucket" label="Bucket 名称" />
          <Md3Input v-model="backupStorageConfig.secret_id" label="SecretId" />
          <Md3Input v-model="backupStorageConfig.secret_key" label="SecretKey" type="password" />
          <Md3Input v-model="backupStorageConfig.region" label="Region" placeholder="如：ap-guangzhou" />
          <Md3Input v-model="backupStorageConfig.prefix" label="存储路径前缀" placeholder="如：backups/" />
        </div>
        <div v-if="backupForm.storage_type === 'aws_s3'" class="storage-config">
          <Md3Input v-model="backupStorageConfig.bucket" label="Bucket 名称" />
          <Md3Input v-model="backupStorageConfig.access_key_id" label="Access Key ID" />
          <Md3Input v-model="backupStorageConfig.secret_access_key" label="Secret Access Key" type="password" />
          <Md3Input v-model="backupStorageConfig.region" label="Region" placeholder="如：us-east-1" />
          <Md3Input v-model="backupStorageConfig.endpoint" label="Endpoint（可选）" placeholder="如：s3.amazonaws.com" />
        </div>
        <div v-if="backupForm.storage_type === 'ftp' || backupForm.storage_type === 'sftp'" class="storage-config">
          <Md3Input v-model="backupStorageConfig.host" label="主机地址" />
          <Md3Input v-model.number="backupStorageConfig.port" label="端口" type="number" placeholder="21 / 22" />
          <Md3Input v-model="backupStorageConfig.username" label="用户名" />
          <Md3Input v-model="backupStorageConfig.password" label="密码" type="password" />
          <Md3Input v-model="backupStorageConfig.remote_path" label="远程目录" placeholder="如：/backup" />
        </div>
        <div class="form-row">
          <Md3Select
            v-model="cronPreset"
            :options="cronPresetOptions"
            label="预设周期"
            style="width: 140px"
            @update:model-value="onBackupPresetChange"
          />
          <Md3Input v-model="backupForm.cron_expression" label="Cron 表达式" placeholder="如：0 3 * * *" />
        </div>
        <Md3Input v-model.number="backupForm.retention_count" label="保留份数" type="number" placeholder="默认 7" />
        <Md3Select v-model="backupForm.compression" :options="compressionOptions" label="压缩格式" />
        <div class="form-field-inline">
          <span class="field-label">启用策略</span>
          <Md3Switch v-model="backupFormEnabled" />
        </div>
      </div>
      <template #footer>
        <Md3Button @click="backupDialogVisible = false">取消</Md3Button>
        <Md3Button variant="primary" @click="saveBackupPolicy">保存</Md3Button>
      </template>
    </Md3Dialog>

    <!-- Log Policy Dialog -->
    <Md3Dialog v-model:visible="logDialogVisible" :title="logDialogTitle" width="560px">
      <div class="dialog-form">
        <Md3Input v-model="logForm.name" label="规则名称" placeholder="如：Nginx 日志清理" />
        <Md3Input v-model="logForm.log_path_pattern" label="日志路径/模式" placeholder="如：/var/log/nginx/*.log" />
        <Md3Input v-model.number="logForm.retention_days" label="保留天数" type="number" placeholder="默认 30" />
        <Md3Select
          v-model="logForm.cleanup_action"
          :options="cleanupActionOptions"
          label="清理动作"
        />
        <Md3Input
          v-if="logForm.cleanup_action === 'compress' || logForm.cleanup_action === 'move'"
          v-model="logForm.archive_path"
          label="归档目录"
          placeholder="如：/var/log/archive"
        />
        <div class="form-row">
          <Md3Select
            v-model="cronPreset"
            :options="cronPresetOptions"
            label="预设周期"
            style="width: 140px"
            @update:model-value="onLogPresetChange"
          />
          <Md3Input v-model="logForm.cron_expression" label="Cron 表达式" placeholder="如：0 4 * * 0" />
        </div>
        <div class="form-field-inline">
          <span class="field-label">启用规则</span>
          <Md3Switch v-model="logFormEnabled" />
        </div>
      </div>
      <template #footer>
        <Md3Button @click="logDialogVisible = false">取消</Md3Button>
        <Md3Button variant="primary" @click="saveLogPolicy">保存</Md3Button>
      </template>
    </Md3Dialog>

    <!-- Execution Logs Dialog -->
    <Md3Dialog v-model:visible="logsDialogVisible" title="执行日志" width="720px">
      <Md3Table
        :columns="executionLogColumns"
        :data="store.executionLogs"
        stripe
        max-height="400"
        empty-text="暂无执行日志"
      >
        <template #status="{ row }">
          <Md3Tag :type="row.status === 'success' ? 'success' : 'danger'" size="sm">
            {{ row.status === 'success' ? '成功' : '失败' }}
          </Md3Tag>
        </template>
        <template #duration="{ row }">
          {{ row.duration_seconds ? row.duration_seconds + 's' : '-' }}
        </template>
      </Md3Table>
      <template #footer>
        <Md3Button @click="logsDialogVisible = false">关闭</Md3Button>
      </template>
    </Md3Dialog>

    <!-- Backup History Dialog -->
    <Md3Dialog v-model:visible="historyDialogVisible" title="备份历史" width="720px">
      <Md3Table
        :columns="historyColumns"
        :data="store.backupHistory"
        stripe
        max-height="400"
        empty-text="暂无备份历史"
      >
        <template #status="{ row }">
          <Md3Tag
            :type="row.status === 'success' ? 'success' : row.status === 'running' ? 'primary' : 'danger'"
            size="sm"
          >
            {{ row.status === 'success' ? '成功' : row.status === 'running' ? '执行中' : '失败' }}
          </Md3Tag>
        </template>
        <template #file_size="{ row }">
          {{ (row as any).file_size ? formatFileSize((row as any).file_size) : '-' }}
        </template>
      </Md3Table>
      <template #footer>
        <Md3Button @click="historyDialogVisible = false">关闭</Md3Button>
      </template>
    </Md3Dialog>

    <!-- Preview Dialog -->
    <Md3Dialog v-model:visible="previewDialogVisible" title="预览影响" width="600px">
      <div v-if="previewData" class="preview-content">
        <p class="preview-summary">
          即将处理 <strong>{{ previewData.files?.length || 0 }}</strong> 个文件
          <span v-if="previewData.total_size">，总计 {{ formatFileSize(previewData.total_size) }}</span>
        </p>
        <Md3Table
          :columns="previewColumns"
          :data="previewData.files || []"
          stripe
          max-height="320"
          empty-text="没有即将被处理的文件"
        />
      </div>
      <template #footer>
        <Md3Button @click="previewDialogVisible = false">关闭</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw } from 'vue'
import { Md3Message, Md3Icon } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import {
  Md3PageHeader,
  Md3Divider,
  Md3Card,
  Md3Tag,
  Md3Input,
  Md3Table,
  Md3Tabs,
  Md3Select,
  Md3Switch,
  Md3Empty,
  Md3Dialog,
  Md3Alert,
} from '@/components/md3'
import { Md3Confirm } from '@/components/md3/Md3Confirm'
import { useCronBackupStore } from '@/stores/cronBackupStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import type { CronJob, BackupPolicy, LogRetentionPolicy } from '@/stores/cronBackupStore'

const store = useCronBackupStore()
const sshStore = useSshAccountStore()

const selectedAlias = ref('')
const activeTab = ref('cron')

// Search
const cronSearch = ref('')
const backupSearch = ref('')
const logSearch = ref('')

// Dialog visibility
const cronDialogVisible = ref(false)
const backupDialogVisible = ref(false)
const logDialogVisible = ref(false)
const logsDialogVisible = ref(false)
const historyDialogVisible = ref(false)
const previewDialogVisible = ref(false)

// Editing state
const editingCronId = ref('')
const editingBackupId = ref('')
const editingLogId = ref('')
const cronPreset = ref('')

// Preview data
const previewData = ref<any>(null)

// Forms
const cronForm = ref({
  name: '',
  cron_expression: '',
  task_type: 'shell' as 'shell' | 'url',
  command: '',
  http_method: 'GET',
  status: 'enabled' as 'enabled' | 'disabled',
})
const cronFormEnabled = ref(true)

const backupForm = ref({
  name: '',
  backup_type: 'website' as 'website' | 'mysql' | 'postgresql' | 'custom',
  source_path: '',
  db_name: '',
  db_host: 'localhost',
  db_port: undefined as number | undefined,
  db_username: '',
  storage_type: 'local' as 'local' | 'aliyun_oss' | 'tencent_cos' | 'aws_s3' | 'ftp' | 'sftp',
  cron_expression: '',
  retention_count: 7,
  compression: 'tar.gz' as 'tar.gz' | 'zip' | 'none',
  status: 'enabled' as 'enabled' | 'disabled',
})
const backupFormEnabled = ref(true)
const backupStorageConfig = ref<Record<string, any>>({})

const logForm = ref({
  name: '',
  log_path_pattern: '',
  retention_days: 30,
  cleanup_action: 'delete' as 'delete' | 'compress' | 'move',
  archive_path: '',
  cron_expression: '',
  status: 'enabled' as 'enabled' | 'disabled',
})
const logFormEnabled = ref(true)

const tabItems = computed(() => [
  { label: '计划任务', value: 'cron', icon: markRaw({ template: '<Md3Icon name="schedule" size="1em" />', components: { Md3Icon } }) },
  { label: '备份策略', value: 'backup', icon: markRaw({ template: '<Md3Icon name="backup" size="1em" />', components: { Md3Icon } }) },
  { label: '日志保留', value: 'log', icon: markRaw({ template: '<Md3Icon name="folder-open" size="1em" />', components: { Md3Icon } }) },
])

const sshOptions = computed(() =>
  sshStore.accounts.map(acc => ({
    label: `${acc.alias} (${acc.host})`,
    value: acc.alias,
  }))
)

const cronPresetOptions = [
  { label: '手动输入', value: '' },
  { label: '每分钟', value: '* * * * *' },
  { label: '每小时', value: '0 * * * *' },
  { label: '每天', value: '0 2 * * *' },
  { label: '每周', value: '0 3 * * 0' },
  { label: '每月', value: '0 4 1 * *' },
]

const taskTypeOptions = [
  { label: 'Shell 脚本', value: 'shell' },
  { label: 'URL 访问', value: 'url' },
]

const backupTypeOptions = [
  { label: '网站目录', value: 'website' },
  { label: 'MySQL 数据库', value: 'mysql' },
  { label: 'PostgreSQL 数据库', value: 'postgresql' },
  { label: '自定义目录', value: 'custom' },
]

const storageTypeOptions = [
  { label: '本地磁盘', value: 'local' },
  { label: '阿里云 OSS', value: 'aliyun_oss' },
  { label: '腾讯云 COS', value: 'tencent_cos' },
  { label: 'AWS S3', value: 'aws_s3' },
  { label: 'FTP', value: 'ftp' },
  { label: 'SFTP', value: 'sftp' },
]

const compressionOptions = [
  { label: 'tar.gz', value: 'tar.gz' },
  { label: 'zip', value: 'zip' },
  { label: '不压缩', value: 'none' },
]

const cleanupActionOptions = [
  { label: '删除', value: 'delete' },
  { label: '压缩归档', value: 'compress' },
  { label: '移动归档', value: 'move' },
]

const cronColumns = [
  { prop: 'name', label: '名称', width: '160px' },
  { prop: 'cron_expression', label: 'Cron 表达式', width: '120px' },
  { prop: 'task_type', label: '类型', width: '80px' },
  { prop: 'command', label: '命令/URL' },
  { prop: 'status', label: '状态', width: '70px' },
  { prop: 'last_run', label: '最后执行', width: '140px' },
  { prop: 'action', label: '操作', width: '180px' },
]

const backupColumns = [
  { prop: 'name', label: '策略名称', width: '160px' },
  { prop: 'backup_type', label: '备份类型', width: '100px' },
  { prop: 'storage_type', label: '存储位置', width: '100px' },
  { prop: 'cron_expression', label: '周期', width: '120px' },
  { prop: 'retention_count', label: '保留份数', width: '90px' },
  { prop: 'last_backup_at', label: '最后备份', width: '140px' },
  { prop: 'status', label: '状态', width: '70px' },
  { prop: 'action', label: '操作', width: '260px' },
]

const logColumns = [
  { prop: 'name', label: '规则名称', width: '160px' },
  { prop: 'log_path_pattern', label: '日志路径', width: '180px' },
  { prop: 'retention_days', label: '保留天数', width: '90px' },
  { prop: 'cleanup_action', label: '清理动作', width: '90px' },
  { prop: 'cron_expression', label: '周期', width: '120px' },
  { prop: 'status', label: '状态', width: '70px' },
  { prop: 'action', label: '操作', width: '300px' },
]

const executionLogColumns = [
  { prop: 'started_at', label: '开始时间', width: '160px' },
  { prop: 'status', label: '状态', width: '80px' },
  { prop: 'exit_code', label: '退出码', width: '80px' },
  { prop: 'duration', label: '耗时', width: '80px' },
  { prop: 'output', label: '输出摘要' },
]

const historyColumns = [
  { prop: 'started_at', label: '备份时间', width: '160px' },
  { prop: 'status', label: '状态', width: '80px' },
  { prop: 'file_size', label: '文件大小', width: '100px' },
  { prop: 'storage_type', label: '存储类型', width: '100px' },
  { prop: 'storage_path', label: '存储路径' },
]

const previewColumns = [
  { prop: 'path', label: '文件路径' },
  { prop: 'size', label: '大小', width: '100px' },
  { prop: 'modified_at', label: '修改时间', width: '160px' },
]

const filteredCronJobs = computed(() => {
  let items = store.cronJobs
  if (cronSearch.value) {
    const q = cronSearch.value.toLowerCase()
    items = items.filter(j => j.name.toLowerCase().includes(q))
  }
  return items.map(j => ({ ...j, last_run: j.last_run_at || '-' }))
})

const filteredBackupPolicies = computed(() => {
  let items = store.backupPolicies
  if (backupSearch.value) {
    const q = backupSearch.value.toLowerCase()
    items = items.filter(p => p.name.toLowerCase().includes(q))
  }
  return items
})

const filteredLogPolicies = computed(() => {
  let items = store.logPolicies
  if (logSearch.value) {
    const q = logSearch.value.toLowerCase()
    items = items.filter(p => p.name.toLowerCase().includes(q))
  }
  return items
})

const cronDialogTitle = computed(() => editingCronId.value ? '编辑计划任务' : '新建计划任务')
const backupDialogTitle = computed(() => editingBackupId.value ? '编辑备份策略' : '新建备份策略')
const logDialogTitle = computed(() => editingLogId.value ? '编辑日志保留规则' : '新建日志保留规则')

function backupTypeLabel(type: string): string {
  const map: Record<string, string> = {
    website: '网站', mysql: 'MySQL', postgresql: 'PostgreSQL', custom: '自定义',
  }
  return map[type] || type
}

function backupTypeColor(type: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  switch (type) {
    case 'website': return 'primary'
    case 'mysql': return 'success'
    case 'postgresql': return 'info'
    case 'custom': return 'warning'
    default: return 'info'
  }
}

function cleanupActionLabel(action: string): string {
  const map: Record<string, string> = { delete: '删除', compress: '压缩', move: '移动' }
  return map[action] || action
}

function cleanupActionColor(action: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  switch (action) {
    case 'delete': return 'danger'
    case 'compress': return 'warning'
    case 'move': return 'primary'
    default: return 'info'
  }
}

function formatFileSize(bytes: number): string {
  if (!bytes && bytes !== 0) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function onCronPresetChange(val: string | number | (string | number)[]) {
  const v = String(val)
  if (v) {
    cronForm.value.cron_expression = v
  }
}

function onBackupPresetChange(val: string | number | (string | number)[]) {
  const v = String(val)
  if (v) {
    backupForm.value.cron_expression = v
  }
}

function onLogPresetChange(val: string | number | (string | number)[]) {
  const v = String(val)
  if (v) {
    logForm.value.cron_expression = v
  }
}

function resetCronForm() {
  cronForm.value = {
    name: '', cron_expression: '', task_type: 'shell', command: '', http_method: 'GET', status: 'enabled',
  }
  cronFormEnabled.value = true
  cronPreset.value = ''
  editingCronId.value = ''
}

function resetBackupForm() {
  backupForm.value = {
    name: '', backup_type: 'website', source_path: '', db_name: '', db_host: 'localhost',
    db_port: undefined, db_username: '', storage_type: 'local', cron_expression: '',
    retention_count: 7, compression: 'tar.gz', status: 'enabled',
  }
  backupFormEnabled.value = true
  backupStorageConfig.value = {}
  cronPreset.value = ''
  editingBackupId.value = ''
}

function resetLogForm() {
  logForm.value = {
    name: '', log_path_pattern: '', retention_days: 30, cleanup_action: 'delete',
    archive_path: '', cron_expression: '', status: 'enabled',
  }
  logFormEnabled.value = true
  cronPreset.value = ''
  editingLogId.value = ''
}

function openCronDialog(job?: CronJob) {
  resetCronForm()
  if (job) {
    editingCronId.value = job.id
    cronForm.value = {
      name: job.name,
      cron_expression: job.cron_expression,
      task_type: job.task_type,
      command: job.command,
      http_method: job.http_method || 'GET',
      status: job.status,
    }
    cronFormEnabled.value = job.status === 'enabled'
  }
  cronDialogVisible.value = true
}

function openBackupDialog(policy?: BackupPolicy) {
  resetBackupForm()
  if (policy) {
    editingBackupId.value = policy.id
    backupForm.value = {
      name: policy.name,
      backup_type: policy.backup_type,
      source_path: policy.source_path || '',
      db_name: policy.db_name || '',
      db_host: policy.db_host || 'localhost',
      db_port: policy.db_port,
      db_username: policy.db_username || '',
      storage_type: policy.storage_type,
      cron_expression: policy.cron_expression,
      retention_count: policy.retention_count,
      compression: policy.compression,
      status: policy.status,
    }
    backupFormEnabled.value = policy.status === 'enabled'
    backupStorageConfig.value = { ...policy.storage_config }
  }
  backupDialogVisible.value = true
}

function openLogDialog(policy?: LogRetentionPolicy) {
  resetLogForm()
  if (policy) {
    editingLogId.value = policy.id
    logForm.value = {
      name: policy.name,
      log_path_pattern: policy.log_path_pattern,
      retention_days: policy.retention_days,
      cleanup_action: policy.cleanup_action,
      archive_path: policy.archive_path || '',
      cron_expression: policy.cron_expression,
      status: policy.status,
    }
    logFormEnabled.value = policy.status === 'enabled'
  }
  logDialogVisible.value = true
}

async function saveCronJob() {
  if (!cronForm.value.name || !cronForm.value.cron_expression || !cronForm.value.command) {
    Md3Message.warning('请填写完整信息')
    return
  }
  const data = {
    ...cronForm.value,
    status: cronFormEnabled.value ? 'enabled' : 'disabled',
  }
  try {
    if (editingCronId.value) {
      await store.updateCronJob(editingCronId.value, data)
      Md3Message.success('任务已更新')
    } else {
      await store.createCronJob(data)
      Md3Message.success('任务已创建')
    }
    cronDialogVisible.value = false
  } catch {
    Md3Message.error('保存失败')
  }
}

async function saveBackupPolicy() {
  if (!backupForm.value.name || !backupForm.value.cron_expression) {
    Md3Message.warning('请填写完整信息')
    return
  }
  const data = {
    ...backupForm.value,
    status: backupFormEnabled.value ? 'enabled' : 'disabled',
    storage_config: backupStorageConfig.value,
  }
  try {
    if (editingBackupId.value) {
      await store.updateBackupPolicy(editingBackupId.value, data)
      Md3Message.success('策略已更新')
    } else {
      await store.createBackupPolicy(data)
      Md3Message.success('策略已创建')
    }
    backupDialogVisible.value = false
  } catch {
    Md3Message.error('保存失败')
  }
}

async function saveLogPolicy() {
  if (!logForm.value.name || !logForm.value.log_path_pattern || !logForm.value.cron_expression) {
    Md3Message.warning('请填写完整信息')
    return
  }
  const data = {
    ...logForm.value,
    status: logFormEnabled.value ? 'enabled' : 'disabled',
  }
  try {
    if (editingLogId.value) {
      await store.updateLogPolicy(editingLogId.value, data)
      Md3Message.success('规则已更新')
    } else {
      await store.createLogPolicy(data)
      Md3Message.success('规则已创建')
    }
    logDialogVisible.value = false
  } catch {
    Md3Message.error('保存失败')
  }
}

async function toggleCronStatus(row: CronJob, enabled: boolean) {
  try {
    await store.updateCronJob(row.id, { status: enabled ? 'enabled' : 'disabled' })
    Md3Message.success(enabled ? '任务已启用' : '任务已禁用')
  } catch {
    Md3Message.error('操作失败')
  }
}

async function toggleBackupStatus(row: BackupPolicy, enabled: boolean) {
  try {
    await store.updateBackupPolicy(row.id, { status: enabled ? 'enabled' : 'disabled' })
    Md3Message.success(enabled ? '策略已启用' : '策略已禁用')
  } catch {
    Md3Message.error('操作失败')
  }
}

async function toggleLogStatus(row: LogRetentionPolicy, enabled: boolean) {
  try {
    await store.updateLogPolicy(row.id, { status: enabled ? 'enabled' : 'disabled' })
    Md3Message.success(enabled ? '规则已启用' : '规则已禁用')
  } catch {
    Md3Message.error('操作失败')
  }
}

async function deleteCron(row: CronJob) {
  try {
    const confirmed = await Md3Confirm.show({
      title: '确认删除',
      message: `确定删除计划任务 "${row.name}" 吗？`,
      type: 'danger',
    })
    if (!confirmed) return
    await store.deleteCronJob(row.id)
    Md3Message.success('任务已删除')
  } catch {
    Md3Message.error('删除失败')
  }
}

async function deleteBackup(row: BackupPolicy) {
  try {
    const confirmed = await Md3Confirm.show({
      title: '确认删除',
      message: `确定删除备份策略 "${row.name}" 吗？`,
      type: 'danger',
    })
    if (!confirmed) return
    await store.deleteBackupPolicy(row.id)
    Md3Message.success('策略已删除')
  } catch {
    Md3Message.error('删除失败')
  }
}

async function deleteLog(row: LogRetentionPolicy) {
  try {
    const confirmed = await Md3Confirm.show({
      title: '确认删除',
      message: `确定删除日志保留规则 "${row.name}" 吗？`,
      type: 'danger',
    })
    if (!confirmed) return
    await store.deleteLogPolicy(row.id)
    Md3Message.success('规则已删除')
  } catch {
    Md3Message.error('删除失败')
  }
}

async function showCronLogs(row: CronJob) {
  try {
    await store.fetchExecutionLogs(row.id)
    logsDialogVisible.value = true
  } catch {
    Md3Message.error('获取日志失败')
  }
}

async function showBackupHistory(row: BackupPolicy) {
  try {
    await store.fetchBackupHistory(row.id)
    historyDialogVisible.value = true
  } catch {
    Md3Message.error('获取历史记录失败')
  }
}

async function runBackup(row: BackupPolicy) {
  try {
    await store.runBackupNow(row.id)
    Md3Message.success('备份任务已触发')
  } catch {
    Md3Message.error('触发备份失败')
  }
}

async function previewLogCleanup(row: LogRetentionPolicy) {
  try {
    const res = await store.previewLogCleanup(row.id)
    previewData.value = res
    previewDialogVisible.value = true
  } catch {
    Md3Message.error('预览失败')
  }
}

async function runLogCleanup(row: LogRetentionPolicy) {
  try {
    const confirmed = await Md3Confirm.show({
      title: '确认清理',
      message: `确定立即执行日志清理规则 "${row.name}" 吗？`,
    })
    if (!confirmed) return
    await store.runLogCleanupNow(row.id)
    Md3Message.success('清理任务已执行')
  } catch {
    Md3Message.error('清理失败')
  }
}

async function onAccountChange(value: string | number | (string | number)[]) {
  const alias = String(value)
  selectedAlias.value = alias
  store.setAccountAlias(alias)
  await loadTabData()
}

async function loadTabData() {
  if (!selectedAlias.value) return
  if (activeTab.value === 'cron') {
    await store.fetchCronJobs()
  } else if (activeTab.value === 'backup') {
    await store.fetchBackupPolicies()
  } else if (activeTab.value === 'log') {
    await store.fetchLogPolicies()
    await store.fetchDiskAlert()
  }
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  const defaultAcc = sshStore.accounts.find(a => (a as any).default)
  const firstAcc = sshStore.accounts[0]
  const alias = defaultAcc?.alias || firstAcc?.alias || ''
  if (alias) {
    selectedAlias.value = alias
    store.setAccountAlias(alias)
    await loadTabData()
  }
})
</script>

<style scoped>
.cron-backup-page {
  padding: 0;
}

.header-icon {
  width: 16px;
  height: 16px;
  vertical-align: -3px;
}

.page-tabs {
  margin-top: var(--md3-space-sm);
  margin-bottom: var(--md3-space-lg);
}

.tab-content {
  margin-top: var(--md3-space-md);
}

.section-card {
  margin-bottom: var(--md3-space-lg);
}

.section-card :deep(.md3-card-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-md) var(--md3-space-lg);
  font-weight: 600;
  font-size: 14px;
}

.card-header-right {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.search-input {
  width: 200px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  flex-wrap: wrap;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.form-row {
  display: flex;
  align-items: flex-end;
  gap: var(--md3-space-sm);
}

.form-field-inline {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.field-label {
  font-size: 14px;
  color: var(--md3-on-surface-variant);
}

.storage-config {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  padding: var(--md3-space-md);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-sm);
}

.disk-alert-banner {
  margin-bottom: var(--md3-space-md);
}

.disk-alert-content p {
  margin: 0 0 var(--md3-space-sm);
}

.disk-alert-list {
  display: flex;
  gap: var(--md3-space-sm);
  flex-wrap: wrap;
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.preview-summary {
  margin: 0;
  font-size: 14px;
  color: var(--md3-on-surface-variant);
}

.text-danger {
  color: var(--md3-error);
}

/* Responsive */
@media (max-width: 768px) {
  .card-header-right {
    flex-direction: column;
    align-items: stretch;
    gap: var(--md3-space-xs);
  }

  .search-input {
    width: 100%;
  }

  .form-row {
    flex-direction: column;
    align-items: stretch;
  }

  .action-buttons {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
