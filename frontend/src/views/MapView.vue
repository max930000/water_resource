<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import {
  PhArrowClockwise,
  PhCaretRight,
  PhCrosshair,
  PhDrop,
  PhWarningCircle,
} from '@phosphor-icons/vue'
import { api, type DistrictGroup, type Station } from '../api'
import { markerColors } from '../tokens'

// 台北車站。桌機瀏覽器定位常不準或被拒絕，所以給一個合理的預設中心。
const DEFAULT_CENTER = { lat: 25.0478, lon: 121.517 }

const router = useRouter()
const mapEl = ref<HTMLDivElement | null>(null)
const mode = ref<'nearby' | 'district'>('nearby')
const radius = ref(1000)
const districtGroups = ref<DistrictGroup[]>([])
const selected = ref('') // 格式："臺北市|大安區"
const stations = ref<Station[]>([])
const loading = ref(false)
const error = ref('')
const notice = ref('')
const center = ref({ ...DEFAULT_CENTER })

let map: L.Map | null = null
let markerLayer: L.LayerGroup | null = null
let meMarker: L.CircleMarker | null = null

const problemCount = computed(() => stations.value.filter((s) => s.open_report_count > 0).length)

// 給螢幕閱讀器的即時播報：結果變動時念出來，但不搶走焦點
const summary = computed(() => {
  if (loading.value) return '載入中'
  if (!stations.value.length) return '這個範圍沒有直飲臺'
  return problemCount.value
    ? `共 ${stations.value.length} 座，其中 ${problemCount.value} 座有待處理回報`
    : `共 ${stations.value.length} 座`
})

function initMap() {
  if (!mapEl.value) return
  map = L.map(mapEl.value, { zoomControl: false }).setView(
    [center.value.lat, center.value.lon],
    15,
  )
  L.control.zoom({ position: 'bottomright' }).addTo(map)

  // OpenStreetMap：開源、可商用。競賽規則禁止 Google Maps 這類商用地圖套件。
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)

  markerLayer = L.layerGroup().addTo(map)
}

// 氣泡內容用 DOM 建立而不是拼 HTML 字串：
// 1. 站名來自外部資料，拼字串有 XSS 風險
// 2. 裡面放真正的 <button>，鍵盤也能操作
function buildPopup(s: Station): HTMLElement {
  const box = document.createElement('div')
  box.className = 'min-w-44'

  const title = document.createElement('p')
  title.className = 'text-base font-semibold text-ink'
  title.textContent = s.name
  box.append(title)

  if (s.address) {
    const addr = document.createElement('p')
    addr.className = 'mt-0.5 text-sm text-ink-muted'
    addr.textContent = s.address
    box.append(addr)
  }

  if (s.open_report_count > 0) {
    const warn = document.createElement('p')
    warn.className = 'mt-1 text-sm font-medium text-danger'
    warn.textContent = `${s.open_report_count} 筆待處理回報`
    box.append(warn)
  }

  const btn = document.createElement('button')
  btn.type = 'button'
  btn.className =
    'mt-2 min-h-11 w-full rounded-lg bg-action px-3 text-sm font-medium text-white hover:bg-action-hover'
  btn.textContent = '查看詳情與回報'
  btn.addEventListener('click', () => open(s))
  box.append(btn)

  return box
}

function draw() {
  if (!map || !markerLayer) return
  markerLayer.clearLayers()
  const c = markerColors()

  for (const s of stations.value) {
    const bad = s.open_report_count > 0
    // 無障礙規則「顏色不能是唯一線索」：
    // 有問題的站點除了變紅，標記也更大、外框更粗，色弱使用者也分得出來。
    L.circleMarker([s.lat, s.lon], {
      radius: bad ? 11 : 7,
      weight: bad ? 3 : 2,
      color: bad ? c.badStroke : c.okStroke,
      fillColor: bad ? c.badFill : c.okFill,
      fillOpacity: 0.9,
    })
      .bindPopup(buildPopup(s))
      .addTo(markerLayer)
  }

  meMarker?.remove()
  if (mode.value === 'nearby') {
    meMarker = L.circleMarker([center.value.lat, center.value.lon], {
      radius: 8,
      weight: 3,
      color: c.meStroke,
      fillColor: c.meFill,
      fillOpacity: 1,
    })
      .addTo(map)
      .bindTooltip('我的位置')
    map.setView([center.value.lat, center.value.lon], 15)
  } else if (stations.value.length) {
    map.fitBounds(L.latLngBounds(stations.value.map((s) => [s.lat, s.lon] as [number, number])), {
      padding: [24, 24],
    })
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    if (mode.value === 'nearby') {
      stations.value = await api.nearby(center.value.lat, center.value.lon, radius.value)
    } else if (selected.value) {
      const [city, district] = selected.value.split('|')
      stations.value = (await api.byDistrict(city, district)).items
    } else {
      stations.value = []
    }
    draw()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '載入失敗'
  } finally {
    loading.value = false
  }
}

function locate() {
  notice.value = ''
  if (!navigator.geolocation) {
    notice.value = '這個裝置不支援定位，改以台北車站為中心'
    return load()
  }
  navigator.geolocation.getCurrentPosition(
    (p) => {
      center.value = { lat: p.coords.latitude, lon: p.coords.longitude }
      load()
    },
    () => {
      // 失敗不能沉默 —— 要讓使用者知道現在的中心點不是他的位置
      notice.value = '無法取得定位，改以台北車站為中心'
      load()
    },
    { enableHighAccuracy: true, timeout: 6000 },
  )
}

function open(s: Station) {
  router.push(`/stations/${s.id}`)
}

function formatDistance(m: number) {
  return m < 1000 ? `${Math.round(m)} 公尺` : `${(m / 1000).toFixed(1)} 公里`
}

onMounted(async () => {
  initMap()
  try {
    districtGroups.value = await api.districts()
  } catch {
    /* 行政區清單失敗不影響「附近」模式，load() 會顯示錯誤 */
  }
  await load()
})

// 離開頁面時釋放地圖，避免在台北通 WebView 裡累積記憶體
onBeforeUnmount(() => {
  map?.remove()
  map = null
})

watch([mode, radius, selected], load)
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- 篩選列 -->
    <div class="flex flex-wrap items-center gap-2 border-b border-line bg-surface px-3 py-2">
      <div role="group" aria-label="查詢方式" class="flex rounded-full bg-line p-1">
        <button
          type="button"
          :aria-pressed="mode === 'nearby'"
          class="min-h-11 rounded-full px-4 text-sm font-medium transition-colors"
          :class="mode === 'nearby' ? 'bg-action text-white' : 'text-ink-strong'"
          @click="mode = 'nearby'"
        >
          附近
        </button>
        <button
          type="button"
          :aria-pressed="mode === 'district'"
          class="min-h-11 rounded-full px-4 text-sm font-medium transition-colors"
          :class="mode === 'district' ? 'bg-action text-white' : 'text-ink-strong'"
          @click="mode = 'district'"
        >
          行政區
        </button>
      </div>

      <label v-if="mode === 'nearby'" class="flex items-center gap-2 text-sm text-ink-muted">
        半徑
        <!-- 下拉選單字級 16px：低於 16px iOS 會在點擊時自動放大整個畫面 -->
        <select
          v-model.number="radius"
          class="min-h-11 rounded-lg border border-line-strong bg-surface px-2 text-base text-ink"
        >
          <option :value="500">500 公尺</option>
          <option :value="1000">1 公里</option>
          <option :value="3000">3 公里</option>
        </select>
      </label>

      <label v-else class="flex min-w-0 flex-1 items-center">
        <span class="sr-only">選擇行政區</span>
        <select
          v-model="selected"
          class="min-h-11 w-full rounded-lg border border-line-strong bg-surface px-2 text-base text-ink"
        >
          <option value="">選擇行政區</option>
          <!-- optgroup：HTML 原生分組。後端已按縣市分好組，直接用。 -->
          <optgroup v-for="g in districtGroups" :key="g.city" :label="g.city">
            <option v-for="d in g.districts" :key="d" :value="`${g.city}|${d}`">{{ d }}</option>
          </optgroup>
        </select>
      </label>

    </div>

    <p v-if="notice" role="status" class="bg-warning-soft px-3 py-2 text-sm text-warning-ink">
      {{ notice }}
    </p>

    <!-- 地圖：容器一定要有明確高度，Leaflet 才算得出尺寸 -->
    <div class="relative min-h-0 flex-1">
      <div
        ref="mapEl"
        role="region"
        aria-label="直飲臺地圖。也可以使用下方清單瀏覽相同內容。"
        class="h-full w-full"
      ></div>

      <!-- 定位按鈕浮在地圖上（地圖 App 的慣例），不佔篩選列的空間。
           只有圖示沒有文字，所以一定要給 aria-label，螢幕閱讀器才念得出用途。 -->
      <button
        v-if="mode === 'nearby'"
        type="button"
        aria-label="重新定位到我的位置"
        title="重新定位"
        class="absolute right-3 top-3 z-[1000] flex h-11 w-11 items-center justify-center rounded-full bg-surface text-action shadow-md transition-colors hover:bg-action-soft"
        @click="locate"
      >
        <PhCrosshair :size="22" weight="bold" aria-hidden="true" />
      </button>
    </div>

    <!-- 清單：地圖的無障礙替代方案，也是單手操作的主要入口 -->
    <section aria-labelledby="list-heading" class="flex h-[42%] flex-col border-t border-line bg-surface">
      <div class="flex items-center justify-between px-4 py-2">
        <h2 id="list-heading" class="text-sm font-semibold text-ink">
          {{ mode === 'nearby' ? '附近的直飲臺' : '行政區內的直飲臺' }}
        </h2>
        <p aria-live="polite" class="text-sm text-ink-muted">
          {{ summary }}
        </p>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto" :aria-busy="loading">
        <!-- 錯誤：說明原因並提供重試，而不是只顯示「失敗」 -->
        <div v-if="error" role="alert" class="m-4 rounded-xl bg-danger-soft p-4">
          <p class="flex items-center gap-2 text-base font-medium text-danger">
            <PhWarningCircle :size="20" weight="bold" aria-hidden="true" />
            載入失敗
          </p>
          <p class="mt-1 text-sm text-danger">{{ error }}</p>
          <button
            type="button"
            class="mt-3 inline-flex min-h-11 items-center gap-1.5 rounded-lg bg-surface px-4 text-sm font-medium text-danger"
            @click="load"
          >
            <PhArrowClockwise :size="18" aria-hidden="true" />
            重試
          </button>
        </div>

        <!-- 載入中：骨架畫面，讓版面不會跳動 -->
        <ul v-else-if="loading" aria-hidden="true">
          <li v-for="n in 4" :key="n" class="flex items-center gap-3 border-b border-line px-4 py-3">
            <span class="h-3 w-3 shrink-0 animate-pulse rounded-full bg-line"></span>
            <span class="flex-1 space-y-2">
              <span class="block h-4 w-2/3 animate-pulse rounded bg-line"></span>
              <span class="block h-3 w-1/2 animate-pulse rounded bg-line"></span>
            </span>
          </li>
        </ul>

        <!-- 空狀態：告訴使用者下一步能做什麼 -->
        <div v-else-if="!stations.length" class="flex flex-col items-center px-6 py-8 text-center">
          <PhDrop :size="36" class="text-brand" aria-hidden="true" />
          <p class="mt-2 text-base text-ink">
            {{ mode === 'district' && !selected ? '請先選擇一個行政區' : '這個範圍沒有直飲臺' }}
          </p>
          <button
            v-if="mode === 'nearby' && radius < 3000"
            type="button"
            class="mt-3 min-h-11 rounded-lg px-4 text-sm font-medium text-action hover:bg-action-soft"
            @click="radius = 3000"
          >
            擴大到 3 公里
          </button>
        </div>

        <ul v-else>
          <li v-for="s in stations" :key="s.id" class="border-b border-line">
            <!-- 用真正的 <button>，不要在 <li> 上掛 @click：鍵盤和螢幕閱讀器才操作得到 -->
            <button
              type="button"
              class="flex min-h-16 w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-canvas active:bg-action-soft"
              @click="open(s)"
            >
              <span
                class="shrink-0 rounded-full"
                :class="s.open_report_count > 0 ? 'h-3.5 w-3.5 bg-danger-icon' : 'h-3 w-3 bg-brand'"
                aria-hidden="true"
              ></span>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-base font-medium text-ink">{{ s.name }}</span>
                <span class="block truncate text-sm text-ink-muted">{{ s.address }}</span>
                <span
                  v-if="s.open_report_count"
                  class="mt-1 inline-flex items-center gap-1 text-sm font-medium text-danger"
                >
                  <PhWarningCircle :size="16" weight="bold" aria-hidden="true" />
                  {{ s.open_report_count }} 筆待處理回報
                </span>
              </span>
              <span
                v-if="s.distance_meters != null"
                class="shrink-0 text-sm tabular-nums text-ink-muted"
              >
                {{ formatDistance(s.distance_meters) }}
              </span>
              <PhCaretRight :size="18" class="shrink-0 text-ink-muted" aria-hidden="true" />
            </button>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>
