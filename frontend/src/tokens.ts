// Leaflet 在 JavaScript 裡畫圖，吃不到 Tailwind class，
// 所以從 CSS 變數讀出實際色值 —— 這樣色碼仍然只定義在 tokens.css 一個地方。

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export function markerColors() {
  return {
    okStroke: cssVar('--marker-ok-stroke'),
    okFill: cssVar('--marker-ok-fill'),
    badStroke: cssVar('--marker-bad-stroke'),
    badFill: cssVar('--marker-bad-fill'),
    meStroke: cssVar('--marker-me-stroke'),
    meFill: cssVar('--marker-me-fill'),
  }
}
