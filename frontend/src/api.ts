// 所有跟後端說話的程式碼都集中在這裡。
// 之後換網址、加驗證 header，只要改這一個檔案。

// 後端位址。優先讀建置時的環境變數，沒設定就用本機開發的預設值。
// Docker 打包時會透過 VITE_API_BASE 指定，不用改程式碼。
const BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

async function request(path: string, init?: RequestInit, params: Record<string, string | number> = {}) {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== '' && v !== undefined && v !== null)
      .map(([k, v]) => [k, String(v)]),
  ).toString()
  const res = await fetch(BASE + path + (qs ? `?${qs}` : ''), init)
  if (!res.ok) {
    let msg = `後端回了 ${res.status}`
    try {
      msg = (await res.json()).detail ?? msg
    } catch { /* 後端沒回 JSON 就用狀態碼 */ }
    throw new Error(typeof msg === 'string' ? msg : `後端回了 ${res.status}`)
  }
  return res.status === 204 ? null : res.json()
}

const get = (path: string, params = {}) => request(path, undefined, params)

const send = (path: string, method: string, body: unknown) =>
  request(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

// ── 顯示用的中文對照 ──────────────────────────────────
export const TYPE_LABEL: Record<string, string> = {
  BROKEN: '設備故障',
  NO_WATER: '沒有出水',
  DIRTY: '環境髒污',
  GOOD: '狀況良好',
  OTHER: '其他',
}

export const STATUS_LABEL: Record<string, string> = {
  OPEN: '待處理',
  IN_PROGRESS: '處理中',
  RESOLVED: '已完成',
  REJECTED: '不受理',
}

export interface Station {
  id: number
  name: string
  city: string | null
  district: string | null
  address: string | null
  lat: number
  lon: number
  status: string | null
  open_report_count: number
  distance_meters?: number
}

export interface StationDetail extends Station {
  place_type: string | null
  owner_unit: string | null
  install_spot: string | null
  open_hours: string | null
  maintainer: string | null
  phone: string | null
  status_changed_at: string | null
  last_sampled_at: string | null
  coliform: string | null
  quality_url: string | null
  photo_url: string | null
  synced_at: string
}

export interface Report {
  id: number
  station_id: number
  station_name: string
  type: string
  description: string | null
  status: string
  admin_note: string | null
  created_at: string
  resolved_at: string | null
}

export interface DistrictGroup {
  city: string
  districts: string[]
}

export const api = {
  health: () => get('/health'),
  districts: (): Promise<DistrictGroup[]> => get('/api/v1/stations/districts'),
  nearby: (lat: number, lon: number, radius: number): Promise<Station[]> =>
    get('/api/v1/stations/nearby', { lat, lon, radius, limit: 100 }),
  byDistrict: (city: string, district: string): Promise<{ items: Station[] }> =>
    get('/api/v1/stations', { city, district, size: 200 }),

  station: (id: number): Promise<StationDetail> => get(`/api/v1/stations/${id}`),
  stationReports: (id: number): Promise<Report[]> => get(`/api/v1/stations/${id}/reports`),
  createReport: (stationId: number, body: { type: string; description?: string }): Promise<Report> =>
    send(`/api/v1/stations/${stationId}/reports`, 'POST', body),

  reports: (params: Record<string, string | number>): Promise<{ items: Report[]; total: number }> =>
    get('/api/v1/reports', params),
  updateReport: (id: number, body: { status?: string; admin_note?: string | null }): Promise<Report> =>
    send(`/api/v1/reports/${id}`, 'PATCH', body),
}
