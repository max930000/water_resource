<script setup lang="ts">
// 回報狀態徽章。
// 無障礙規則「顏色不能是唯一線索」：每個狀態都有圖示 + 文字，色弱也分得出來。
import { computed } from 'vue'
import { PhCheckCircle, PhClock, PhProhibit, PhWarningCircle } from '@phosphor-icons/vue'
import { STATUS_LABEL } from '../api'

const props = defineProps<{ status: string }>()

const style = computed(() => {
  switch (props.status) {
    case 'OPEN':
      return { cls: 'bg-danger-soft text-danger', icon: PhWarningCircle }
    case 'IN_PROGRESS':
      return { cls: 'bg-warning-soft text-warning-ink', icon: PhClock }
    case 'RESOLVED':
      return { cls: 'bg-action-soft text-action', icon: PhCheckCircle }
    default:
      return { cls: 'bg-canvas text-ink-muted', icon: PhProhibit }
  }
})
</script>

<template>
  <span
    class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium"
    :class="style.cls"
  >
    <component :is="style.icon" :size="14" weight="bold" aria-hidden="true" />
    {{ STATUS_LABEL[status] ?? status }}
  </span>
</template>
