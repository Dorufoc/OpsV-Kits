<template>
  <div class="git-commit-panel">
    <Md3Card class="filter-card">
      <div class="filter-form">
        <Md3Input v-model="filterForm.author" label="提交人" placeholder="作者名称" style="width: 160px" />
        <Md3Input v-model="filterForm.since" label="起始日期" placeholder="2024-01-01" style="width: 140px" />
        <Md3Input v-model="filterForm.until" label="结束日期" placeholder="2024-12-31" style="width: 140px" />
        <Md3Input v-model="filterForm.keyword" label="关键词" placeholder="搜索提交信息" style="flex: 1" />
        <Md3Button size="sm" variant="primary" @click="handleSearch">搜索</Md3Button>
      </div>
    </Md3Card>

    <div class="commit-timeline">
      <div
        v-for="commit in gitStore.commits"
        :key="commit.hash"
        class="commit-item"
        :class="{ 'commit-item--expanded': expandedHash === commit.hash }"
      >
        <div class="commit-header" @click="toggleExpand(commit.hash)">
          <div class="commit-dot" />
          <span class="commit-hash">{{ commit.short_hash }}</span>
          <span class="commit-message">{{ commit.message }}</span>
          <span class="commit-author">{{ commit.author }}</span>
          <span class="commit-date">{{ commit.date }}</span>
        </div>
        <div v-if="expandedHash === commit.hash" class="commit-detail">
          <div v-if="commitDetailLoading" class="detail-loading">加载中...</div>
          <template v-else>
            <div v-if="commitDiffFiles.length > 0" class="detail-files">
              <span class="detail-label">变更文件:</span>
              <Md3Tag v-for="f in commitDiffFiles" :key="f" size="sm" class="file-tag">{{ f }}</Md3Tag>
            </div>
            <pre v-if="commitDiffContent" class="detail-diff">{{ commitDiffContent }}</pre>
          </template>
        </div>
      </div>
    </div>

    <div v-if="gitStore.commitTotal > pageSize" class="pagination">
      <Md3Button size="sm" :disabled="currentPage <= 1" @click="currentPage--">上一页</Md3Button>
      <span class="pagination-info">{{ currentPage }} / {{ totalPages }}</span>
      <Md3Button size="sm" :disabled="currentPage >= totalPages" @click="currentPage++">下一页</Md3Button>
    </div>

    <Md3Empty v-if="gitStore.commits.length === 0 && !gitStore.loading" description="暂无提交记录" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useGitIntegrationStore } from '@/stores/gitIntegrationStore'
import {
  Md3Card,
  Md3Input,
  Md3Tag,
  Md3Empty,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

const gitStore = useGitIntegrationStore()

const currentPage = ref(1)
const pageSize = 20
const expandedHash = ref('')
const commitDiffFiles = ref<string[]>([])
const commitDiffContent = ref('')
const commitDetailLoading = ref(false)

const filterForm = ref({
  author: '',
  since: '',
  until: '',
  keyword: '',
})

const totalPages = computed(() => Math.ceil(gitStore.commitTotal / pageSize))

async function handleSearch() {
  currentPage.value = 1
  await fetchCommits()
}

async function fetchCommits() {
  await gitStore.fetchCommits({
    author: filterForm.value.author || undefined,
    since: filterForm.value.since || undefined,
    until: filterForm.value.until || undefined,
    keyword: filterForm.value.keyword || undefined,
    page: currentPage.value,
    page_size: pageSize,
  })
}

async function toggleExpand(hash: string) {
  if (expandedHash.value === hash) {
    expandedHash.value = ''
    return
  }
  expandedHash.value = hash
  commitDetailLoading.value = true
  commitDiffFiles.value = []
  commitDiffContent.value = ''
  try {
    const res = await gitStore.fetchCommitDiff(hash)
    commitDiffFiles.value = res.files
    commitDiffContent.value = res.diff
  } catch {
    // ignore
  } finally {
    commitDetailLoading.value = false
  }
}

watch(currentPage, () => {
  fetchCommits()
})

onMounted(() => {
  fetchCommits()
})
</script>

<style scoped>
.filter-card {
  margin-bottom: var(--md3-space-md);
}

.filter-form {
  display: flex;
  align-items: flex-end;
  gap: var(--md3-space-md);
  flex-wrap: wrap;
}

.commit-timeline {
  position: relative;
  padding-left: 20px;
}

.commit-item {
  position: relative;
  padding: var(--md3-space-sm) 0;
  border-left: 2px solid var(--md3-outline-variant);
  margin-left: 8px;
}

.commit-header {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-md);
  cursor: pointer;
  border-radius: var(--md3-shape-sm);
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.commit-header:hover {
  background: var(--md3-surface-container-low);
}

.commit-dot {
  position: absolute;
  left: -7px;
  top: 16px;
  width: 12px;
  height: 12px;
  border-radius: var(--md3-shape-full);
  background: var(--md3-primary);
  border: 2px solid var(--md3-surface);
}

.commit-hash {
  font-family: var(--md3-font-mono);
  font: var(--md3-type-label-small);
  color: var(--md3-primary);
  flex-shrink: 0;
}

.commit-message {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.commit-author {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  flex-shrink: 0;
}

.commit-date {
  font: var(--md3-type-body-small);
  color: var(--md3-outline);
  flex-shrink: 0;
}

.commit-detail {
  margin: var(--md3-space-sm) var(--md3-space-md);
  padding: var(--md3-space-md);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-sm);
  border: 1px solid var(--md3-outline-variant);
}

.detail-loading {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  text-align: center;
  padding: var(--md3-space-md);
}

.detail-files {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--md3-space-xs);
  margin-bottom: var(--md3-space-sm);
}

.detail-label {
  font: var(--md3-type-body-small);
  color: var(--md3-outline);
  margin-right: var(--md3-space-xs);
}

.file-tag {
  margin-bottom: 2px;
}

.detail-diff {
  font-family: var(--md3-font-mono);
  font-size: 12px;
  background: var(--md3-inverse-surface);
  color: var(--md3-inverse-on-surface);
  padding: var(--md3-space-md);
  border-radius: var(--md3-shape-xs);
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--md3-space-md);
  margin-top: var(--md3-space-lg);
}

.pagination-info {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
}
</style>
