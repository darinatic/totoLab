import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/toto/explore' },

  // Toto
  { path: '/toto/explore', name: 'toto-explore', component: () => import('../views/Explore.vue') },
  { path: '/toto/predict', name: 'toto-predict', component: () => import('../views/Predictions.vue') },
  { path: '/toto/reality-check', name: 'toto-backtest', component: () => import('../views/Backtest.vue') },
  { path: '/toto/data', name: 'toto-data', component: () => import('../views/DataTable.vue') },

  // 4D
  { path: '/4d/explore', name: '4d-explore', component: () => import('../views/fourd/Explore.vue') },
  { path: '/4d/predict', name: '4d-predict', component: () => import('../views/fourd/Predictions.vue') },
  { path: '/4d/reality-check', name: '4d-backtest', component: () => import('../views/fourd/Backtest.vue') },
  { path: '/4d/data', name: '4d-data', component: () => import('../views/fourd/DataTable.vue') },

  // legacy redirects (old Toto URLs)
  { path: '/predict', redirect: '/toto/predict' },
  { path: '/reality-check', redirect: '/toto/reality-check' },
  { path: '/data', redirect: '/toto/data' },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
