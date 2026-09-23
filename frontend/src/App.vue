<script setup lang="ts">
// 外框：標題列 + 內容區 + 底部導覽。實際頁面由 router 放進 RouterView。
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { PhMapTrifold, PhWrench } from '@phosphor-icons/vue'

const route = useRoute()

// 詳情頁屬於「地圖」這個分頁底下，導覽列要亮在地圖
const activeTab = computed(() => (route.name === 'admin' ? 'admin' : 'map'))

// 規則：導覽圖示用 SVG，不用 emoji（emoji 跨平台長得不一樣，也無法套主題色）
const tabs = [
  { name: 'map', to: '/', label: '地圖', icon: PhMapTrifold },
  { name: 'admin', to: '/admin', label: '維護後台', icon: PhWrench },
] as const
</script>

<template>
  <div class="flex h-dvh flex-col bg-canvas">
    <!-- 鍵盤使用者可以跳過標題直接到內容 -->
    <a
      href="#main"
      class="sr-only rounded bg-action px-4 py-2 text-white focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[2000]"
    >
      跳到主要內容
    </a>

    <header class="bg-action px-4 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] text-white">
      <h1 class="text-lg font-semibold leading-tight">城市水路</h1>
      <p class="mt-0.5 text-xs text-white/90">臺北直飲臺地圖｜資料來源：臺北市資料大平臺</p>
    </header>

    <main id="main" class="min-h-0 flex-1 overflow-hidden">
      <RouterView />
    </main>

    <nav
      aria-label="主要導覽"
      class="grid grid-cols-2 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)]"
    >
      <RouterLink
        v-for="tab in tabs"
        :key="tab.name"
        :to="tab.to"
        :aria-current="activeTab === tab.name ? 'page' : undefined"
        class="flex min-h-14 flex-col items-center justify-center gap-0.5 text-xs transition-colors"
        :class="activeTab === tab.name ? 'font-semibold text-action' : 'text-ink-muted'"
      >
        <component
          :is="tab.icon"
          :size="24"
          :weight="activeTab === tab.name ? 'fill' : 'regular'"
          aria-hidden="true"
        />
        {{ tab.label }}
      </RouterLink>
    </nav>
  </div>
</template>
