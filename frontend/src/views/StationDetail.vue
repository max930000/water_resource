<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  api,
  STATUS_LABEL,
  TYPE_LABEL,
  type Report,
  type StationDetail,
} from '../api'

const route = useRoute()
const router = useRouter()
const stationId = Number(route.params.id)

const station = ref<StationDetail | null>(null)
const reports = ref<Report[]>([])
const loading = ref(true)
const message = ref('')
const isError = ref(false)

// 回報表單
const type = ref('NO_WATER')
const description = ref('')
const submitting = ref(false)

async function load() {
  loading.value = true
  try {
    station.value = await api.station(stationId)
    reports.value = await api.stationReports(stationId)
  } catch (e) {
    isError.value = true
    message.value = e instanceof Error ? e.message : '載入失敗'
  } finally {
    loading.value = false
  }
}

async function submit() {
  submitting.value = true
  message.value = ''
  isError.value = false
  try {
    await api.createReport(stationId, {
      type: type.value,
      description: description.value || undefined,
    })
    description.value = ''
    message.value = '回報已送出，感謝你讓城市更好'
    await load()
  } catch (e) {
    isError.value = true
    message.value = e instanceof Error ? e.message : '送出失敗'
  } finally {
    submitting.value = false
  }
}

// 後端回的時間沒有時區資訊，直接當本地時間顯示就好
function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}

onMounted(load)
</script>

<template>
  <div class="h-full overflow-y-auto bg-slate-50 pb-6">
    <button class="px-3 py-2 text-xs text-teal-700" @click="router.back()">← 返回地圖</button>

    <p v-if="loading" class="px-4 py-10 text-center text-sm text-slate-400">載入中…</p>

    <template v-else-if="station">
      <!-- 基本資料 -->
      <section class="bg-white px-4 py-4">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <h2 class="text-lg font-bold">{{ station.name }}</h2>
            <p class="mt-0.5 text-xs text-slate-500">{{ station.address }}</p>
          </div>
          <span
            class="shrink-0 rounded px-2 py-0.5 text-[11px]"
            :class="station.status === '正常' ? 'bg-teal-100 text-teal-800' : 'bg-amber-100 text-amber-800'"
          >
            {{ station.status ?? '狀態不明' }}
          </span>
        </div>

        <img
          v-if="station.photo_url"
          :src="station.photo_url"
          alt="直飲臺照片"
          class="mt-3 h-40 w-full rounded object-cover"
          loading="lazy"
          @error="($event.target as HTMLImageElement).style.display = 'none'"
        />

        <dl class="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
          <div><dt class="text-slate-400">行政區</dt><dd>{{ station.district ?? '—' }}</dd></div>
          <div><dt class="text-slate-400">開放時間</dt><dd>{{ station.open_hours ?? '—' }}</dd></div>
          <div><dt class="text-slate-400">場所類型</dt><dd>{{ station.place_type ?? '—' }}</dd></div>
          <div><dt class="text-slate-400">設置地點</dt><dd>{{ station.install_spot ?? '—' }}</dd></div>
        </dl>
      </section>

      <!-- 水質資訊：這是這個服務真正的差異化，市民原本根本看不到 -->
      <section class="mt-2 bg-white px-4 py-4">
        <h3 class="text-sm font-semibold">水質資訊</h3>
        <dl class="mt-2 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
          <div>
            <dt class="text-slate-400">大腸桿菌數</dt>
            <dd class="font-mono font-semibold text-teal-700">{{ station.coliform ?? '—' }}</dd>
          </div>
          <div>
            <dt class="text-slate-400">最近採樣</dt>
            <dd>{{ fmt(station.last_sampled_at) }}</dd>
          </div>
          <div><dt class="text-slate-400">維護單位</dt><dd>{{ station.maintainer ?? '—' }}</dd></div>
          <div><dt class="text-slate-400">聯絡電話</dt><dd>{{ station.phone ?? '—' }}</dd></div>
        </dl>
        <a
          v-if="station.quality_url"
          :href="station.quality_url"
          target="_blank"
          rel="noopener"
          class="mt-3 inline-block text-xs text-teal-700 underline"
        >
          查看北水處官方水質公開資訊 →
        </a>
        <p class="mt-2 text-[10px] text-slate-400">
          資料同步時間：{{ fmt(station.synced_at) }}
        </p>
      </section>

      <!-- 回報表單 -->
      <section class="mt-2 bg-white px-4 py-4">
        <h3 class="text-sm font-semibold">回報這座直飲臺的狀況</h3>
        <form class="mt-2 space-y-2" @submit.prevent="submit">
          <select v-model="type" class="w-full rounded border border-slate-300 px-2 py-2 text-sm">
            <option v-for="(label, value) in TYPE_LABEL" :key="value" :value="value">
              {{ label }}
            </option>
          </select>
          <textarea
            v-model="description"
            rows="2"
            maxlength="500"
            placeholder="補充說明（選填，最多 500 字）"
            class="w-full rounded border border-slate-300 px-2 py-2 text-sm"
          ></textarea>
          <button
            type="submit"
            :disabled="submitting"
            class="w-full rounded bg-teal-700 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {{ submitting ? '送出中…' : '送出回報' }}
          </button>
        </form>

        <p
          v-if="message"
          class="mt-2 rounded px-2 py-1.5 text-xs"
          :class="isError ? 'bg-rose-50 text-rose-700' : 'bg-teal-50 text-teal-800'"
        >
          {{ message }}
        </p>
      </section>

      <!-- 回報紀錄 -->
      <section class="mt-2 bg-white px-4 py-4">
        <h3 class="text-sm font-semibold">回報紀錄（{{ reports.length }}）</h3>
        <ul class="mt-2 divide-y divide-slate-100">
          <li v-for="r in reports" :key="r.id" class="py-2.5">
            <div class="flex flex-wrap items-center gap-2 text-[11px]">
              <span class="rounded bg-slate-100 px-1.5 py-0.5">{{ TYPE_LABEL[r.type] }}</span>
              <span
                class="rounded px-1.5 py-0.5"
                :class="{
                  'bg-rose-100 text-rose-700': r.status === 'OPEN',
                  'bg-amber-100 text-amber-800': r.status === 'IN_PROGRESS',
                  'bg-teal-100 text-teal-800': r.status === 'RESOLVED',
                  'bg-slate-200 text-slate-600': r.status === 'REJECTED',
                }"
              >
                {{ STATUS_LABEL[r.status] }}
              </span>
              <span class="ml-auto text-slate-400">{{ fmt(r.created_at) }}</span>
            </div>
            <p v-if="r.description" class="mt-1 text-xs text-slate-700">{{ r.description }}</p>
            <p v-if="r.admin_note" class="mt-1 rounded bg-slate-50 px-2 py-1 text-xs text-slate-600">
              維護單位回覆：{{ r.admin_note }}
            </p>
          </li>
        </ul>
        <p v-if="!reports.length" class="py-4 text-center text-xs text-slate-400">
          還沒有人回報過這座直飲臺
        </p>
      </section>
    </template>
  </div>
</template>
