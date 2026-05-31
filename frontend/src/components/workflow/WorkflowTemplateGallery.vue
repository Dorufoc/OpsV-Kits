<script setup lang="ts">
import { Md3Dialog, Md3Card, Md3Tag, Md3Icon } from '@/components/md3'

interface WorkflowTemplate {
  id: string
  name: string
  description?: string
  category: string
  icon?: string
}

const props = defineProps<{
  templates: WorkflowTemplate[]
}>()

const emit = defineEmits<{
  select: [templateId: string]
  close: []
}>()

const categoryColors: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'> = {
  devops: 'primary',
  monitor: 'success',
  deploy: 'warning',
  security: 'danger',
  general: 'info',
}
</script>

<template>
  <Md3Dialog
    :visible="true"
    title="工作流模板"
    fullscreen
    @close="emit('close')"
  >
    <div class="template-gallery">
      <div class="template-grid">
        <Md3Card
          v-for="tpl in templates"
          :key="tpl.id"
          hoverable
          class="template-card"
          @click="emit('select', tpl.id)"
        >
          <template #header>
            <div class="template-card-header">
              <Md3Icon v-if="tpl.icon" :name="tpl.icon" :size="28" color="var(--md3-primary)" />
              <Md3Tag :type="categoryColors[tpl.category] || 'info'" size="sm">
                {{ tpl.category }}
              </Md3Tag>
            </div>
          </template>
          <div class="template-card-body">
            <h4 class="template-card-name">{{ tpl.name }}</h4>
            <p class="template-card-desc">{{ tpl.description || '' }}</p>
          </div>
        </Md3Card>
      </div>
    </div>
  </Md3Dialog>
</template>

<style scoped>
.template-gallery {
  min-height: 300px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--md3-space-lg);
}

.template-card {
  cursor: pointer;
}

.template-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.template-card-body {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.template-card-name {
  margin: 0;
  font: var(--md3-type-title-small);
  color: var(--md3-on-surface);
}

.template-card-desc {
  margin: 0;
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 900px) {
  .template-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .template-grid {
    grid-template-columns: 1fr;
  }
}
</style>
