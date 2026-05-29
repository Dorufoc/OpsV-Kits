<template>
  <div class="permission-editor">
    <div class="perm-section perm-preview-section">
      <div class="perm-section-header">
        <span class="perm-section-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 5v4l3 3M12 11l-2.5"/></svg>
        </span>
        <span>权限预览</span>
        <span class="perm-mode">{{ modeStr }}</span>
      </div>
      <div class="perm-rwx-display">
        <div class="perm-rwx-group" v-for="group in rwxGroups" :key="group.label">
          <span class="perm-rwx-label">{{ group.label }}</span>
          <span class="perm-rwx-chars">
            <template v-for="(ch, idx) in group.chars" :key="idx">
              <span :class="['perm-char', ch !== '-' ? 'perm-char-on' : 'perm-char-off']">{{ ch }}</span>
            </template>
          </span>
        </div>
      </div>
    </div>

    <Md3Divider />

    <div class="perm-section">
      <div class="perm-matrix">
        <div class="perm-matrix-header">
          <span class="perm-col-label"></span>
          <span class="perm-col-header perm-col-r">读取</span>
          <span class="perm-col-header perm-col-w">写入</span>
          <span class="perm-col-header perm-col-x">执行</span>
        </div>
        <div class="perm-matrix-row" v-for="group in userGroups" :key="group.key">
          <span class="perm-row-label">
            <span class="perm-row-icon">{{ group.icon }}</span>
            {{ group.label }}
          </span>
          <Md3Checkbox
            :model-value="permissions[group.key].r"
            @update:model-value="(v) => toggle(group.key, 'r', v as boolean)"
          />
          <Md3Checkbox
            :model-value="permissions[group.key].w"
            @update:model-value="(v) => toggle(group.key, 'w', v as boolean)"
          />
          <Md3Checkbox
            :model-value="permissions[group.key].x"
            @update:model-value="(v) => toggle(group.key, 'x', v as boolean)"
          />
        </div>
      </div>
    </div>

    <Md3Divider />

    <div class="perm-section perm-presets-section">
      <div class="perm-section-header">
        <span class="perm-section-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/></svg>
        </span>
        <span>快速预设</span>
      </div>
      <div class="perm-presets">
        <button
          v-for="preset in presets"
          :key="preset.label"
          :class="['perm-preset-btn', { active: isPresetActive(preset) }]"
          @click="applyPreset(preset)"
        >
          <span class="perm-preset-mode">{{ preset.mode }}</span>
          <span class="perm-preset-label">{{ preset.label }}</span>
        </button>
      </div>
    </div>

    <div v-if="showRecursive" class="perm-section perm-recursive-section">
      <Md3Checkbox
        :model-value="recursive"
        @update:model-value="$emit('update:recursive', $event as boolean)"
        label="应用到子目录和文件（递归）"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, reactive } from 'vue'
import { Md3Divider } from '@/components/md3'
import Md3Checkbox from '@/components/md3/Md3Checkbox.vue'

interface PermissionMode {
  owner: { r: boolean; w: boolean; x: boolean }
  group: { r: boolean; w: boolean; x: boolean }
  other: { r: boolean; w: boolean; x: boolean }
}

interface Preset {
  label: string
  mode: string
  owner: { r: boolean; w: boolean; x: boolean }
  group: { r: boolean; w: boolean; x: boolean }
  other: { r: boolean; w: boolean; x: boolean }
}

const props = withDefaults(defineProps<{
  modelValue?: number
  showRecursive?: boolean
  recursive?: boolean
}>(), {
  modelValue: 0o644,
  showRecursive: false,
  recursive: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: number]
  'update:recursive': [value: boolean]
}>()

const permissions = reactive<PermissionMode>({
  owner: { r: false, w: false, x: false },
  group: { r: false, w: false, x: false },
  other: { r: false, w: false, x: false },
})

function modeToPermissions(mode: number): PermissionMode {
  return {
    owner: { r: !!(mode & 0o400), w: !!(mode & 0o200), x: !!(mode & 0o100) },
    group: { r: !!(mode & 0o040), w: !!(mode & 0o020), x: !!(mode & 0o010) },
    other: { r: !!(mode & 0o004), w: !!(mode & 0o002), x: !!(mode & 0o001) },
  }
}

function permissionsToMode(p: PermissionMode): number {
  let mode = 0
  if (p.owner.r) mode |= 0o400
  if (p.owner.w) mode |= 0o200
  if (p.owner.x) mode |= 0o100
  if (p.group.r) mode |= 0o040
  if (p.group.w) mode |= 0o020
  if (p.group.x) mode |= 0o010
  if (p.other.r) mode |= 0o004
  if (p.other.w) mode |= 0o002
  if (p.other.x) mode |= 0o001
  return mode
}

watch(() => props.modelValue, (val) => {
  const p = modeToPermissions(val)
  permissions.owner = { ...p.owner }
  permissions.group = { ...p.group }
  permissions.other = { ...p.other }
}, { immediate: true })

function toggle(group: 'owner' | 'group' | 'other', perm: 'r' | 'w' | 'x', value: boolean) {
  permissions[group][perm] = value
  const mode = permissionsToMode(permissions)
  emit('update:modelValue', mode)
}

const modeStr = computed(() => {
  return '0' + permissionsToMode(permissions).toString(8).padStart(3, '0')
})

const rwxGroups = computed(() => [
  {
    label: '所有者',
    chars: [
      permissions.owner.r ? 'r' : '-',
      permissions.owner.w ? 'w' : '-',
      permissions.owner.x ? 'x' : '-',
    ],
  },
  {
    label: '用户组',
    chars: [
      permissions.group.r ? 'r' : '-',
      permissions.group.w ? 'w' : '-',
      permissions.group.x ? 'x' : '-',
    ],
  },
  {
    label: '其他用户',
    chars: [
      permissions.other.r ? 'r' : '-',
      permissions.other.w ? 'w' : '-',
      permissions.other.x ? 'x' : '-',
    ],
  },
])

const userGroups = [
  { key: 'owner' as const, icon: '👤', label: '所有者' },
  { key: 'group' as const, icon: '👥', label: '用户组' },
  { key: 'other' as const, icon: '🌐', label: '其他用户' },
]

const presets: Preset[] = [
  { label: '可执行', mode: '0755', owner: { r: true, w: true, x: true }, group: { r: true, w: false, x: true }, other: { r: true, w: false, x: true } },
  { label: '私有文件', mode: '0644', owner: { r: true, w: true, x: false }, group: { r: true, w: false, x: false }, other: { r: true, w: false, x: false } },
  { label: '只读', mode: '0444', owner: { r: true, w: false, x: false }, group: { r: true, w: false, x: false }, other: { r: true, w: false, x: false } },
  { label: '完全开放', mode: '0777', owner: { r: true, w: true, x: true }, group: { r: true, w: true, x: true }, other: { r: true, w: true, x: true } },
  { label: '仅所有者读写', mode: '0600', owner: { r: true, w: true, x: false }, group: { r: false, w: false, x: false }, other: { r: false, w: false, x: false } },
  { label: '仅所有者执行', mode: '0700', owner: { r: true, w: true, x: true }, group: { r: false, w: false, x: false }, other: { r: false, w: false, x: false } },
]

function applyPreset(preset: Preset) {
  permissions.owner = { ...preset.owner }
  permissions.group = { ...preset.group }
  permissions.other = { ...preset.other }
  emit('update:modelValue', permissionsToMode(permissions))
}

function isPresetActive(preset: Preset): boolean {
  const key = `${preset.owner.r}${preset.owner.w}${preset.owner.x}${preset.group.r}${preset.group.w}${preset.group.x}${preset.other.r}${preset.other.w}${preset.other.x}`
  const currentKey = `${permissions.owner.r}${permissions.owner.w}${permissions.owner.x}${permissions.group.r}${permissions.group.w}${permissions.group.x}${permissions.other.r}${permissions.other.w}${permissions.other.x}`
  return key === currentKey
}
</script>

<style scoped>
.permission-editor {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  min-width: 360px;
}

.perm-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.perm-section-header {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  font: var(--md3-type-title-small);
  color: var(--md3-on-surface);
}

.perm-section-icon {
  display: flex;
  align-items: center;
  color: var(--md3-primary);
}

.perm-mode {
  margin-left: auto;
  font: var(--md3-type-body-small);
  font-family: var(--md3-font-mono);
  color: var(--md3-primary);
  background: var(--md3-primary-container);
  padding: 2px 8px;
  border-radius: var(--md3-shape-xs);
}

.perm-preview-section {
  padding: var(--md3-space-sm);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-md);
}

.perm-rwx-display {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: var(--md3-space-xs);
}

.perm-rwx-group {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.perm-rwx-label {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  width: 56px;
  flex-shrink: 0;
}

.perm-rwx-chars {
  display: flex;
  gap: 2px;
  font-family: var(--md3-font-mono);
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 1px;
}

.perm-char {
  width: 20px;
  text-align: center;
}

.perm-char-on {
  color: var(--md3-primary);
}

.perm-char-off {
  color: var(--md3-outline-variant);
}

.perm-matrix {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.perm-matrix-header {
  display: grid;
  grid-template-columns: 140px 48px 48px 48px;
  gap: var(--md3-space-sm);
  padding: 0 calc(4px + 18px);
}

.perm-col-header {
  text-align: center;
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.perm-col-label {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
}

.perm-matrix-row {
  display: grid;
  grid-template-columns: 140px 48px 48px 48px;
  gap: var(--md3-space-sm);
  align-items: center;
  padding: var(--md3-space-xs) 0;
  border-radius: var(--md3-shape-sm);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.perm-matrix-row:hover {
  background: var(--md3-surface-container-low);
}

.perm-row-label {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface);
  padding-left: var(--md3-space-xs);
}

.perm-row-icon {
  font-size: 1rem;
}

.perm-presets {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--md3-space-sm);
}

.perm-preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--md3-space-sm) var(--md3-space-xs);
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-md);
  background: var(--md3-surface-container-low);
  cursor: pointer;
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.perm-preset-btn:hover {
  background: var(--md3-primary-container);
  border-color: var(--md3-primary);
}

.perm-preset-btn.active {
  background: var(--md3-primary-container);
  border-color: var(--md3-primary);
  box-shadow: var(--md3-elevation-level1);
}

.perm-preset-mode {
  font-family: var(--md3-font-mono);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--md3-primary);
}

.perm-preset-label {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
}

.perm-recursive-section {
  padding: var(--md3-space-sm) 0;
}
</style>
