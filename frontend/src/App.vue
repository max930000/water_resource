<script setup lang="ts">
// App.vue 現在只是「外框」：標題列 + 內容區 + 底部導覽。
// 實際的頁面由 router 決定要把哪一個放進 RouterView。
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
const current = computed(() => route.name)

const tabs = [
  { name: 'map', to: '/', label: '地圖', icon: '💧' },
  { name: 'admin', to: '/admin', label: '維護後台', icon: '🛠' },
] as const
</script>

<template>
  <div class="flex h-full flex-col">
    <header class="flex items-center justify-between bg-teal-700 px-4 py-3 text-white">
      <div>
        <h1 class="text-base font-bold leading-tight">城市水路</h1>
        <p class="text-[11px] opacity-80">臺北直飲臺地圖｜資料來源：臺北市資料大平臺</p>
      </div>
    </header>

    <main class="min-h-0 flex-1 overflow-hidden">
      <!-- 目前路由對應的頁面會畫在這裡 -->
      <RouterView />
    </main>

    <nav class="grid grid-cols-2 border-t border-slate-200 bg-white">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.name"
        :to="tab.to"
        class="flex flex-col items-center gap-0.5 py-2 text-[11px]"
        :class="current === tab.name ? 'font-semibold text-teal-700' : 'text-slate-500'"
      >
        <span class="text-lg leading-none">{{ tab.icon }}</span>
        {{ tab.label }}
      </RouterLink>
    </nav>
  </div>
</template>
