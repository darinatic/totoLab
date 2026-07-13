import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'explore', component: () => import('../views/Explore.vue') },
  { path: '/predict', name: 'predict', component: () => import('../views/Predictions.vue') },
  { path: '/reality-check', name: 'backtest', component: () => import('../views/Backtest.vue') },
  { path: '/data', name: 'data', component: () => import('../views/DataTable.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
