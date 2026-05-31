<template>
  <div
    class="md3-progress"
    :class="[
      `md3-progress--${type}`,
      { 'md3-progress--striped': striped },
    ]"
  >
    <template v-if="type === 'line'">
      <div class="md3-progress__track">
        <div
          class="md3-progress__bar"
          :class="{ 'md3-progress__bar--animated': animated }"
          :style="barStyle"
          role="progressbar"
          :aria-valuenow="percentage"
          aria-valuemin="0"
          aria-valuemax="100"
        />
      </div>
      <span v-if="showPercentage" class="md3-progress__label">{{ percentage }}%</span>
    </template>
    <template v-else-if="type === 'circle'">
      <svg class="md3-progress__circle" :viewBox="`0 0 ${size} ${size}`" :width="size" :height="size">
        <circle
          class="md3-progress__circle-track"
          :cx="radius"
          :cy="radius"
          :r="radius"
          :stroke-width="strokeWidth"
        />
        <circle
          class="md3-progress__circle-bar"
          :class="{ 'md3-progress__circle-bar--animated': animated }"
          :cx="radius"
          :cy="radius"
          :r="radius"
          :stroke-width="strokeWidth"
          :style="circleBarStyle"
        />
      </svg>
      <div class="md3-progress__circle-label">
        <slot v-if="$slots.circleLabel" name="circleLabel">{{ percentage }}%</slot>
        <span v-else>{{ percentage }}%</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type ProgressType = 'line' | 'circle'

const props = withDefaults(defineProps<{
  type?: ProgressType
  percentage?: number
  color?: string
  showPercentage?: boolean
  striped?: boolean
  animated?: boolean
  size?: number
  strokeWidth?: number
}>(), {
  type: 'line',
  percentage: 0,
  color: '',
  showPercentage: false,
  striped: false,
  animated: false,
  size: 100,
  strokeWidth: 6,
})

const barStyle = computed(() => ({
  width: `${Math.max(0, Math.min(100, props.percentage))}%`,
  ...(props.color ? { backgroundColor: props.color } : {}),
}))

const radius = computed(() => (props.size - props.strokeWidth) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)

const circleBarStyle = computed(() => ({
  strokeDasharray: `${circumference.value}`,
  strokeDashoffset: `${circumference.value * (1 - Math.max(0, Math.min(100, props.percentage)) / 100)}`,
  ...(props.color ? { stroke: props.color } : {}),
}))
</script>

<style scoped>
.md3-progress {
  display: inline-flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.md3-progress--line {
  flex-direction: row;
}

/* ===== Line Progress ===== */
.md3-progress__track {
  flex: 1;
  height: 4px;
  border-radius: var(--md3-shape-full);
  background: var(--md3-surface-container-highest);
  overflow: hidden;
}

.md3-progress__bar {
  height: 100%;
  border-radius: var(--md3-shape-full);
  background: var(--md3-primary);
  transition: width var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized-decelerate);
}

.md3-progress__bar--animated {
  background: linear-gradient(
    90deg,
    var(--md3-primary) 0%,
    var(--md3-primary-container) 50%,
    var(--md3-primary) 100%
  );
  background-size: 200% 100%;
  animation: md3-progress-stripe 1.5s linear infinite;
}

.md3-progress--striped .md3-progress__bar {
  background-image: repeating-linear-gradient(
    -45deg,
    transparent,
    transparent 4px,
    rgba(255, 255, 255, 0.15) 4px,
    rgba(255, 255, 255, 0.15) 8px
  );
}

.md3-progress__label {
  font: var(--md3-type-label-medium);
  color: var(--md3-on-surface-variant);
  min-width: 3em;
  text-align: right;
}

/* ===== Circle Progress ===== */
.md3-progress--circle {
  flex-direction: column;
  position: relative;
}

.md3-progress__circle {
  transform: rotate(-90deg);
}

.md3-progress__circle-track {
  fill: none;
  stroke: var(--md3-surface-container-highest);
}

.md3-progress__circle-bar {
  fill: none;
  stroke: var(--md3-primary);
  transition: stroke-dashoffset var(--md3-motion-duration-long) var(--md3-motion-easing-emphasized-decelerate);
}

.md3-progress__circle-bar--animated {
  stroke: var(--md3-primary);
  animation: md3-progress-spin 2s linear infinite;
}

.md3-progress__circle-label {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  inset: 0;
  font: var(--md3-type-headline-small);
  color: var(--md3-on-surface);
}

@keyframes md3-progress-stripe {
  0% { background-position: 0% 0%; }
  100% { background-position: 200% 0%; }
}

@keyframes md3-progress-spin {
  0% { stroke-dashoffset: 100%; }
  50% { stroke-dashoffset: 25%; }
  100% { stroke-dashoffset: 100%; }
}

/* ===== Dark Mode ===== */
[data-theme="dark"] .md3-progress--striped .md3-progress__bar {
  background-image: repeating-linear-gradient(
    -45deg,
    transparent,
    transparent 4px,
    rgba(0, 0, 0, 0.2) 4px,
    rgba(0, 0, 0, 0.2) 8px
  );
}
</style>
