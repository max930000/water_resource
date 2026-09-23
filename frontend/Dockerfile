# 前端容器：兩階段建置（multi-stage build）
#
# 階段 1 用 Node 把 Vue 編譯成靜態檔案
# 階段 2 只把編譯結果複製到 nginx，Node 和 node_modules 全部丟掉
#
# 為什麼要分兩階段：
#   node_modules 有幾百 MB，但「跑起來」完全不需要它 ——
#   瀏覽器只要 HTML/CSS/JS。最終映像從 1.5GB 變成 50MB。
#   規則要求「可移轉、可上架」，映像小就是實際的優勢。

# ── 階段 1：編譯 ──────────────────────────────────────
FROM node:24-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# ARG 是「build 時」的變數，可以從 docker compose 傳進來。
# Vue 是靜態網站，API 位址在編譯當下就被寫死進 JS 檔案裡，
# 所以必須在這裡決定，不能等到執行時才給。
ARG VITE_API_BASE=http://127.0.0.1:8000
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

# ── 階段 2：只留下編譯結果 ────────────────────────────
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
