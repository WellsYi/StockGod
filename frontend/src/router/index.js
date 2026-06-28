import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/stocks', name: 'StockManager', component: () => import('../views/StockManager.vue') },
  { path: '/signals', name: 'Signals', component: () => import('../views/Signals.vue') },
  { path: '/limit-up', name: 'LimitUp', component: () => import('../views/LimitUp.vue') },
  { path: '/bili', name: 'BiliDynamics', component: () => import('../views/BiliDynamics.vue') },
  { path: '/monitor', name: 'MonitorStatus', component: () => import('../views/MonitorStatus.vue') },
  { path: '/rag', name: 'RAGChat', component: () => import('../views/RAGChat.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
