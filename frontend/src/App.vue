<script setup>
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Badge } from 'ant-design-vue'

const router = useRouter()
const route = useRoute()
const wsConnected = ref(false)
let ws = null
let pingTimer = null

const menuItems = [
  { key: '/', icon: '⚡', label: '异动' },
  { key: '/stocks', icon: '📊', label: '股票池' },
  { key: '/signals', icon: '📡', label: '信号' },
  { key: '/limit-up', icon: '🔔', label: '涨停' },
  { key: '/bili', icon: '🅱', label: 'B站' },
  { key: '/monitor', icon: '🛡', label: '监控' },
  { key: '/rag', icon: '🤖', label: 'RAG' },
]

const selectedKeys = computed(() => [route.path])
const isActive = (key) => route.path === key

function connectWs() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${location.host}/ws`)
  ws.onopen = () => { wsConnected.value = true }
  ws.onclose = () => {
    wsConnected.value = false
    ws = null
    setTimeout(connectWs, 3000)
  }
  ws.onmessage = (e) => {
    window.dispatchEvent(new CustomEvent('ws:message', { detail: e.data }))
  }
  ws.onerror = () => { wsConnected.value = false }
}

onMounted(() => {
  connectWs()
  pingTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping')
  }, 30000)
})

onUnmounted(() => {
  clearInterval(pingTimer)
  if (ws) ws.close()
})
</script>

<template>
  <div class="app-layout">
    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="logo-area">
        <div class="logo-title">StockGod</div>
        <div class="logo-subtitle">量化系统 v2.0</div>
      </div>
      <nav class="nav-menu">
        <div
          v-for="item in menuItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: isActive(item.key) }"
          @click="router.push(item.key)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          {{ item.label }}
        </div>
      </nav>
      <div class="sidebar-footer">
        <div class="sidebar-version">v2.0</div>
      </div>
    </aside>

    <!-- MAIN -->
    <main class="main">
      <header class="topbar">
        <div class="connection-status">
          <div class="status-dot" :class="{ connected: wsConnected }"></div>
          {{ wsConnected ? '已连接' : '未连接' }}
        </div>
      </header>
      <div class="site-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<style>
/* ===== LAYOUT ===== */
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-primary);
}

/* ===== SIDEBAR ===== */
.sidebar {
  width: var(--sidebar-width);
  background: linear-gradient(180deg, #0A0E1A 0%, #0D1220 100%);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: relative;
}
.sidebar::after {
  content: '';
  position: absolute;
  top: 0; right: 0;
  width: 1px; height: 100%;
  background: linear-gradient(180deg, transparent, rgba(0,212,255,0.3), transparent);
}

.logo-area {
  padding: 20px 16px 24px;
  border-bottom: 1px solid var(--border-color);
}
.logo-title {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #00D4FF, #7C3AED);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 1px;
}
.logo-subtitle {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.nav-menu {
  flex: 1;
  padding: 16px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 13px;
  color: var(--text-secondary);
  position: relative;
  user-select: none;
}
.nav-item:hover {
  background: rgba(255,255,255,0.05);
  color: var(--text-primary);
}
.nav-item.active {
  background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(124,58,237,0.15));
  color: var(--accent-blue);
  border: 1px solid rgba(0,212,255,0.2);
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0; top: 50%;
  transform: translateY(-50%);
  width: 3px; height: 60%;
  background: linear-gradient(180deg, var(--accent-blue), var(--accent-purple));
  border-radius: 0 2px 2px 0;
}
.nav-icon { width: 16px; text-align: center; font-size: 14px; }

.sidebar-footer {
  padding: 12px 8px;
  border-top: 1px solid var(--border-color);
}
.sidebar-version {
  text-align: center;
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1px;
}

/* ===== TOP BAR ===== */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-secondary);
}
.topbar {
  height: 52px;
  background: rgba(13,17,23,0.9);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 24px;
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}
.connection-status {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--accent-green);
}
.status-dot {
  width: 7px; height: 7px;
  background: rgba(0,230,118,0.3);
  border-radius: 50%;
  transition: all 0.3s;
}
.status-dot.connected {
  background: var(--accent-green);
  box-shadow: 0 0 8px var(--accent-green);
  animation: pulse-green 2s infinite;
}
@keyframes pulse-green {
  0%, 100% { box-shadow: 0 0 8px var(--accent-green); }
  50% { box-shadow: 0 0 16px var(--accent-green), 0 0 24px rgba(0,230,118,0.4); }
}

/* Ant Design 暗色覆盖 */
.ant-layout { background: transparent !important; }
.ant-layout-content { background: transparent !important; }
.ant-layout-sider { background: transparent !important; min-width: var(--sidebar-width) !important; max-width: var(--sidebar-width) !important; flex: 0 0 var(--sidebar-width) !important; }

/* ant-card dark override */
.ant-card {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
  backdrop-filter: blur(10px) !important;
}
.ant-card-head {
  background: transparent !important;
  border-bottom: 1px solid var(--border-color) !important;
  color: var(--text-primary) !important;
  min-height: 44px;
}
.ant-card-head-title { padding: 12px 0; font-size: 13px; font-weight: 600; }
.ant-card-body { padding: 16px 20px; }

/* ant-table dark override */
.ant-table { background: transparent !important; color: var(--text-secondary) !important; }
.ant-table-thead > tr > th {
  background: rgba(255,255,255,0.02) !important;
  border-bottom: 1px solid var(--border-color) !important;
  color: var(--text-muted) !important;
  font-size: 10px !important;
  text-transform: uppercase;
  letter-spacing: 1.5px !important;
  font-weight: 600 !important;
}
.ant-table-tbody > tr > td {
  border-bottom: 1px solid rgba(255,255,255,0.03) !important;
  font-size: 12px !important;
  padding: 11px 16px !important;
}
.ant-table-tbody > tr:hover > td {
  background: rgba(0,212,255,0.04) !important;
}
.ant-table-tbody > tr.ant-table-row:hover > td:first-child {
  border-left: 2px solid var(--accent-blue) !important;
}
.ant-pagination-item { background: transparent !important; border-color: var(--border-color) !important; }
.ant-pagination-item a { color: var(--text-secondary) !important; }
.ant-pagination-item-active { border-color: rgba(0,212,255,0.4) !important; }
.ant-pagination-item-active a { color: var(--accent-blue) !important; }

/* ant-tag override */
.ant-tag { border-radius: 4px !important; font-size: 10px !important; font-weight: 500 !important; padding: 2px 8px !important; line-height: 18px !important; }

/* ant-btn override */
.ant-btn { border-radius: 6px !important; font-size: 12px !important; }

/* ant-drawer override */
.ant-drawer-content { background: #0D1117 !important; }
.ant-drawer-header { background: transparent !important; border-bottom: 1px solid var(--border-color) !important; }
.ant-drawer-title { color: var(--text-primary) !important; }

/* ant-picker (date) */
.ant-picker { background: rgba(255,255,255,0.06) !important; border-color: var(--border-color) !important; }
.ant-picker input { color: var(--text-primary) !important; }

/* ant-select */
.ant-select-selector { background: rgba(255,255,255,0.06) !important; border-color: var(--border-color) !important; }
.ant-select-selection-placeholder,
.ant-select-selection-item { color: var(--text-primary) !important; }
.ant-select-dropdown { background: #0D1117 !important; border: 1px solid var(--border-color) !important; }
.ant-select-item { color: var(--text-secondary) !important; }
.ant-select-item-option-selected { background: rgba(0,212,255,0.1) !important; color: var(--accent-blue) !important; }

/* ant-input */
.ant-input { background: rgba(255,255,255,0.06) !important; border-color: var(--border-color) !important; color: var(--text-primary) !important; }
.ant-input::placeholder { color: var(--text-muted) !important; }

/* ant-alert */
.ant-alert-info { background: rgba(0,212,255,0.1) !important; border: 1px solid rgba(0,212,255,0.2) !important; }
.ant-alert-message { color: var(--accent-blue) !important; }

/* ant-list */
.ant-list-item { border-bottom: 1px solid rgba(255,255,255,0.03) !important; }

/* ant-empty */
.ant-empty-description { color: var(--text-muted) !important; }
</style>
