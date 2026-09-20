import { createRouter, createWebHistory } from 'vue-router'

// 用 () => import(...) 的寫法，Vite 會自動把每一頁拆成獨立檔案，
// 首次開啟只下載第一頁，在手機網路上快很多。
export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'map', component: () => import('./views/MapView.vue') },
    { path: '/stations/:id', name: 'station', component: () => import('./views/StationDetail.vue') },
    { path: '/admin', name: 'admin', component: () => import('./views/AdminView.vue') },
    { path: '/:rest(.*)', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
