<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import { api, type DistrictGroup, type Station } from '../api'

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
const center = ref({ ...DEFAULT_CENTER })

let map: L.Map | null = null
let markerLayer: L.LayerGroup | null = null
let meMarker: L.CircleMarker | null = null

const problemCount = computed(
  () => stations.value.filter((s) => s.open_report_count > 0).length,
)

function initMap() {
  if (!mapEl.value) return
  map = L.map(mapEl.value, { zoomControl: false }).setView(
    [center.value.lat, center.value.lon],
    15,
  )
  L.control.zoom({ position: 'bottomright' }).addTo(map)

  // 圖磚來源：OpenStreetMap（開源、可商用）。
  // 競賽規則禁止 Google Maps 這類商用地圖套件，這是安全的選擇。
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)

  markerLayer = L.layerGroup().addTo(map)
}

function escapeHtml(t: string) {
  const d = document.createElement('div')
  d.textContent = t
  return d.innerHTML
}

function draw() {
  if (!map || !markerLayer) return
  markerLayer.clearLayers()

  for (const s of stations.value) {
    const bad = s.open_report_count > 0
    // 用 circleMarker 而不是預設的 pin 圖示：不用載圖檔，打包時不會有路徑問題
    const marker = L.circleMarker([s.lat, s.lon], {
      radius: 8,
      weight: 2,
      color: bad ? '#e11d48' : '#0f766e',
      fillColor: bad ? '#fecdd3' : '#5eead4',
      fillOpacity: 0.9,
    }).bindPopup(
      `<strong>${escapeHtml(s.name)}</strong><br>` +
        `<span style="color:#64748b;font-size:12px">${escapeHtml(s.address ?? '')}</span>` +
        (bad
          ? `<br><span style="color:#e11d48;font-size:12px">${s.open_report_count} 筆待處理回報</span>`
          : '') +
        `<br><span style="color:#0f766e;font-size:12px;text-decoration:underline">看詳情與回報 →</span>`,
    )
    // 點氣泡就跳到詳情頁
    marker.on('popupopen', () => {
      marker.getPopup()?.getElement()?.addEventListener('click', () => open(s))
    })
    marker.addTo(markerLayer)
  }

  meMarker?.remove()
  if (mode.value === 'nearby') {
    meMarker = L.circleMarker([center.value.lat, center.value.lon], {
      radius: 7,
      color: '#1d4ed8',
      fillColor: '#3b82f6',
      fillOpacity: 1,
    })
      .addTo(map)
      .bindTooltip('我的位置')
    map.setView([center.value.lat, center.value.lon], 15)
  } else if (stations.value.length) {
    map.fitBounds(
      L.latLngBounds(stations.value.map((s) => [s.lat, s.lon] as [number, number])),
    )
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
  if (!navigator.geolocation) return load()
  navigator.geolocation.getCurrentPosition(
    (p) => {
      center.value = { lat: p.coords.latitude, lon: p.coords.longitude }
      load()
    },
    () => load(),
    { enableHighAccuracy: true, timeout: 6000 },
  )
}

function open(s: Station) {
  router.push(`/stations/${s.id}`)
}

onMounted(async () => {
  initMap()
  districtGroups.value = await api.districts()
  await load()
})

watch([mode, radius, selected], load)
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex items-center gap-2 overflow-x-auto bg-white px-3 py-2 text-xs shadow-sm">
      <div class="flex shrink-0 rounded-full bg-slate-100 p-0.5">
        <button
          class="rounded-full px-3 py-1"
          :class="mode === 'nearby' ? 'bg-teal-700 text-white' : 'text-slate-600'"
          @click="mode = 'nearby'"
        >
          附近
        </button>
        <button
          class="rounded-full px-3 py-1"
          :class="mode === 'district' ? 'bg-teal-700 text-white' : 'text-slate-600'"
          @click="mode = 'district'"
        >
          行政區
        </button>
      </div>

      <label v-if="mode === 'nearby'" class="flex shrink-0 items-center gap-1 text-slate-600">
        半徑
        <select v-model.number="radius" class="rounded border border-slate-300 px-2 py-1">
          <option :value="500">500 公尺</option>
          <option :value="1000">1 公里</option>
          <option :value="3000">3 公里</option>
        </select>
      </label>

      <!-- optgroup 是 HTML 原生的分組功能，不用寫任何 JS。
           後端已經把行政區按縣市分好組，這裡直接用。 -->
      <select
        v-else
        v-model="selected"
        class="shrink-0 rounded border border-slate-300 px-2 py-1"
      >
        <option value="">選擇行政區</option>
        <optgroup v-for="g in districtGroups" :key="g.city" :label="g.city">
          <option v-for="d in g.districts" :key="d" :value="`${g.city}|${d}`">{{ d }}</option>
        </optgroup>
      </select>

      <button
        v-if="mode === 'nearby'"
        class="ml-auto shrink-0 text-teal-700 underline"
        @click="locate"
      >
        重新定位
      </button>
    </div>

    <!-- 地圖：一定要有明確高度，不然 Leaflet 算出 0 就什麼都不顯示 -->
    <div class="relative min-h-0 flex-1">
      <div ref="mapEl" class="h-full w-full"></div>
      <div
        v-if="loading"
        class="absolute left-1/2 top-3 z-[1000] -translate-x-1/2 rounded-full bg-white/90 px-3 py-1 text-xs shadow"
      >
        載入中…
      </div>
      <p
        v-if="error"
        class="absolute inset-x-3 bottom-3 z-[1000] rounded bg-rose-50 px-3 py-2 text-xs text-rose-700 shadow"
      >
        {{ error }}
      </p>
    </div>

    <div class="h-[36%] overflow-y-auto border-t border-slate-200 bg-white">
      <p class="sticky top-0 bg-white px-3 py-2 text-[11px] text-slate-500">
        共 {{ stations.length }} 座<span v-if="problemCount"
          >，其中
          <span class="font-semibold text-rose-600">{{ problemCount }} 座有待處理回報</span></span
        >
      </p>
      <ul>
        <li
          v-for="s in stations"
          :key="s.id"
          class="flex items-center gap-2 border-b border-slate-100 px-3 py-2 active:bg-slate-50"
          @click="open(s)"
        >
          <span
            class="h-2.5 w-2.5 shrink-0 rounded-full"
            :class="s.open_report_count > 0 ? 'bg-rose-500' : 'bg-teal-500'"
          ></span>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium">{{ s.name }}</p>
            <p class="truncate text-[11px] text-slate-500">{{ s.address }}</p>
            <p v-if="s.open_report_count" class="text-[11px] text-rose-600">
              {{ s.open_report_count }} 筆待處理回報
            </p>
          </div>
          <span v-if="s.distance_meters != null" class="shrink-0 text-[11px] text-slate-500">
            {{ Math.round(s.distance_meters) }} m
          </span>
          <span class="shrink-0 text-slate-300">›</span>
        </li>
      </ul>
      <p v-if="!loading && !stations.length" class="px-3 py-6 text-center text-xs text-slate-400">
        這個範圍沒有直飲臺，試試放大半徑或換一區
      </p>
    </div>
  </div>
</template>
