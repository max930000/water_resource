<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  PhArrowClockwise,
  PhArrowSquareOut,
  PhCaretLeft,
  PhChatText,
  PhCheckCircle,
  PhDrop,
  PhPhone,
  PhSpinnerGap,
  PhWarningCircle,
} from '@phosphor-icons/vue'
import { api, TYPE_LABEL, type Report, type StationDetail } from '../api'
import StatusBadge from '../components/StatusBadge.vue'

const MAX_LEN = 500

const route = useRoute()
const router = useRouter()
const stationId = Number(route.params.id)

const station = ref<StationDetail | null>(null)
const reports = ref<Report[]>([])
const loading = ref(true)
const loadError = ref('')
const photoFailed = ref(false)

// 回報表單
const type = ref('NO_WATER')
const description = ref('')
const submitting = ref(false)
const submitResult = ref<{ ok: boolean; text: string } | null>(null)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    // 兩個請求互不相依，同時發出，而不是一個等一個
    ;[station.value, reports.value] = await Promise.all([
      api.station(stationId),
      api.stationReports(stationId),
    ])
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : '載入失敗'
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (submitting.value) return // 防止連點送出兩筆
  submitting.value = true
  submitResult.value = null
  try {
    await api.createReport(stationId, {
      type: type.value,
      description: description.value.trim() || undefined,
    })
    description.value = ''
    submitResult.value = { ok: true, text: '回報已送出，維護單位處理後會在下方回覆' }
    reports.value = await api.stationReports(stationId)
  } catch (e) {
    // 錯誤訊息要說原因，並保留使用者剛打的內容，讓他能直接重送
    submitResult.value = {
      ok: false,
      text: `送出失敗：${e instanceof Error ? e.message : '請稍後再試'}`,
    }
  } finally {
    submitting.value = false
  }
}

function goBack() {
  // 從外部連結直接進來時沒有上一頁，退回地圖而不是關掉 WebView
  if (window.history.state?.back) router.back()
  else router.push('/')
}

function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}

onMounted(load)
</script>

<template>
  <div class="h-full overflow-y-auto pb-6">
    <div class="sticky top-0 z-10 border-b border-line bg-surface/95 backdrop-blur">
      <button
        type="button"
        class="inline-flex min-h-12 items-center gap-1 px-3 text-base font-medium text-action"
        @click="goBack"
      >
        <PhCaretLeft :size="20" weight="bold" aria-hidden="true" />
        返回地圖
      </button>
    </div>

    <!-- 載入中：骨架 -->
    <div v-if="loading" aria-busy="true" aria-label="載入中" class="space-y-3 p-4">
      <div class="h-7 w-2/3 animate-pulse rounded bg-line"></div>
      <div class="h-4 w-1/2 animate-pulse rounded bg-line"></div>
      <div class="aspect-video w-full animate-pulse rounded-xl bg-line"></div>
    </div>

    <div v-else-if="loadError" role="alert" class="m-4 rounded-xl bg-danger-soft p-4">
      <p class="flex items-center gap-2 text-base font-medium text-danger">
        <PhWarningCircle :size="20" weight="bold" aria-hidden="true" />
        無法載入這座直飲臺
      </p>
      <p class="mt-1 text-sm text-danger">{{ loadError }}</p>
      <button
        type="button"
        class="mt-3 inline-flex min-h-11 items-center gap-1.5 rounded-lg bg-surface px-4 text-sm font-medium text-danger"
        @click="load"
      >
        <PhArrowClockwise :size="18" aria-hidden="true" />
        重試
      </button>
    </div>

    <template v-else-if="station">
      <!-- 基本資料 -->
      <section class="bg-surface px-4 pb-4 pt-3">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h2 class="text-2xl font-semibold leading-8 text-ink">{{ station.name }}</h2>
            <p class="mt-1 text-sm text-ink-muted">{{ station.address }}</p>
          </div>
          <span
            class="shrink-0 rounded-full px-2.5 py-1 text-xs font-medium"
            :class="station.status === '正常' ? 'bg-action-soft text-action' : 'bg-warning-soft text-warning-ink'"
          >
            {{ station.status ?? '狀態不明' }}
          </span>
        </div>

        <!-- 圖片先用 aspect-video 保留空間，載入時版面才不會往下跳（CLS） -->
        <div v-if="station.photo_url && !photoFailed" class="mt-3 aspect-video overflow-hidden rounded-xl bg-line">
          <img
            :src="station.photo_url"
            :alt="`${station.name}的直飲臺外觀照片`"
            width="640"
            height="360"
            loading="lazy"
            class="h-full w-full object-cover"
            @error="photoFailed = true"
          />
        </div>

        <dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
          <div>
            <dt class="text-sm text-ink-muted">行政區</dt>
            <dd class="text-base text-ink">{{ station.district ?? '—' }}</dd>
          </div>
          <div>
            <dt class="text-sm text-ink-muted">開放時間</dt>
            <dd class="text-base tabular-nums text-ink">{{ station.open_hours ?? '—' }}</dd>
          </div>
          <div>
            <dt class="text-sm text-ink-muted">場所類型</dt>
            <dd class="text-base text-ink">{{ station.place_type ?? '—' }}</dd>
          </div>
          <div>
            <dt class="text-sm text-ink-muted">設置地點</dt>
            <dd class="text-base text-ink">{{ station.install_spot ?? '—' }}</dd>
          </div>
        </dl>
      </section>

      <!-- 水質資訊：這個服務真正的差異化 —— 資料本來就公開，但市民從沒看過 -->
      <section aria-labelledby="quality-heading" class="mt-2 bg-surface px-4 py-4">
        <h3 id="quality-heading" class="flex items-center gap-2 text-base font-semibold text-ink">
          <PhDrop :size="20" weight="fill" class="text-brand" aria-hidden="true" />
          水質資訊
        </h3>

        <div class="mt-3 grid grid-cols-2 gap-3">
          <div class="rounded-xl bg-action-soft p-3">
            <p class="text-sm text-action">大腸桿菌數</p>
            <p class="mt-1 text-2xl font-semibold tabular-nums text-action">
              {{ station.coliform ?? '—' }}
            </p>
          </div>
          <div class="rounded-xl bg-canvas p-3">
            <p class="text-sm text-ink-muted">最近採樣</p>
            <p class="mt-1 text-base font-medium tabular-nums text-ink">
              {{ fmt(station.last_sampled_at) }}
            </p>
          </div>
        </div>

        <dl class="mt-3 space-y-2">
          <div class="flex justify-between gap-4">
            <dt class="text-sm text-ink-muted">維護單位</dt>
            <dd class="text-right text-base text-ink">{{ station.maintainer ?? '—' }}</dd>
          </div>
        </dl>

        <div class="mt-3 flex flex-wrap gap-2">
          <a
            v-if="station.phone"
            :href="`tel:${station.phone}`"
            class="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-line-strong px-3 text-sm font-medium text-action"
          >
            <PhPhone :size="18" aria-hidden="true" />
            {{ station.phone }}
          </a>
          <a
            v-if="station.quality_url"
            :href="station.quality_url"
            target="_blank"
            rel="noopener"
            class="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-line-strong px-3 text-sm font-medium text-action"
          >
            北水處官方水質資訊
            <PhArrowSquareOut :size="16" aria-hidden="true" />
            <span class="sr-only">（開啟新視窗）</span>
          </a>
        </div>

        <p class="mt-3 text-xs text-ink-muted">資料同步時間：{{ fmt(station.synced_at) }}</p>
      </section>

      <!-- 回報表單 -->
      <section aria-labelledby="report-heading" class="mt-2 bg-surface px-4 py-4">
        <h3 id="report-heading" class="text-base font-semibold text-ink">回報這座直飲臺的狀況</h3>

        <form class="mt-3 space-y-4" novalidate @submit.prevent="submit">
          <div>
            <!-- 每個欄位都要有看得見的 label，不能只靠 placeholder -->
            <label for="report-type" class="block text-sm font-medium text-ink">
              狀況類型 <span class="text-danger" aria-hidden="true">*</span>
            </label>
            <select
              id="report-type"
              v-model="type"
              required
              class="mt-1 min-h-12 w-full rounded-lg border border-line-strong bg-surface px-3 text-base text-ink"
            >
              <option v-for="(label, value) in TYPE_LABEL" :key="value" :value="value">
                {{ label }}
              </option>
            </select>
          </div>

          <div>
            <label for="report-desc" class="block text-sm font-medium text-ink">
              補充說明（選填）
            </label>
            <textarea
              id="report-desc"
              v-model="description"
              rows="3"
              :maxlength="MAX_LEN"
              aria-describedby="report-desc-help"
              placeholder="例如：按了沒有出水，地上有積水"
              class="mt-1 w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-base text-ink placeholder:text-ink-muted"
            ></textarea>
            <p id="report-desc-help" class="mt-1 text-right text-xs tabular-nums text-ink-muted">
              {{ description.length }} / {{ MAX_LEN }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="submitting"
            :aria-busy="submitting"
            class="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-action text-base font-semibold text-white transition-colors hover:bg-action-hover disabled:opacity-50"
          >
            <PhSpinnerGap v-if="submitting" :size="20" class="animate-spin" aria-hidden="true" />
            {{ submitting ? '送出中…' : '送出回報' }}
          </button>

          <!-- 結果訊息放在按鈕旁邊，而不是頁面頂端 -->
          <p
            v-if="submitResult"
            :role="submitResult.ok ? 'status' : 'alert'"
            class="flex items-start gap-2 rounded-lg px-3 py-2 text-sm"
            :class="submitResult.ok ? 'bg-action-soft text-action' : 'bg-danger-soft text-danger'"
          >
            <component
              :is="submitResult.ok ? PhCheckCircle : PhWarningCircle"
              :size="18"
              weight="bold"
              class="mt-0.5 shrink-0"
              aria-hidden="true"
            />
            {{ submitResult.text }}
          </p>
        </form>
      </section>

      <!-- 回報紀錄 -->
      <section aria-labelledby="history-heading" class="mt-2 bg-surface px-4 py-4">
        <h3 id="history-heading" class="text-base font-semibold text-ink">
          回報紀錄
          <span class="ml-1 text-sm font-normal text-ink-muted">（{{ reports.length }} 筆）</span>
        </h3>

        <ul v-if="reports.length" class="mt-2 divide-y divide-line">
          <li v-for="r in reports" :key="r.id" class="py-3">
            <div class="flex flex-wrap items-center gap-2">
              <StatusBadge :status="r.status" />
              <span class="text-sm font-medium text-ink">{{ TYPE_LABEL[r.type] }}</span>
              <time :datetime="r.created_at" class="ml-auto text-xs tabular-nums text-ink-muted">
                {{ fmt(r.created_at) }}
              </time>
            </div>
            <p v-if="r.description" class="mt-1.5 text-base text-ink">{{ r.description }}</p>
            <div
              v-if="r.admin_note"
              class="mt-2 flex items-start gap-2 rounded-lg bg-canvas px-3 py-2 text-sm text-ink"
            >
              <PhChatText :size="18" class="mt-0.5 shrink-0 text-action" aria-hidden="true" />
              <span><span class="font-medium">維護單位回覆：</span>{{ r.admin_note }}</span>
            </div>
          </li>
        </ul>
        <p v-else class="py-6 text-center text-base text-ink-muted">還沒有人回報過這座直飲臺</p>
      </section>
    </template>
  </div>
</template>
