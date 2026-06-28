<script setup>
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  DashboardOutlined, StockOutlined, RocketOutlined,
  VideoCameraOutlined, SettingOutlined, RobotOutlined,
  FundOutlined,
} from '@ant-design/icons-vue'
import { Badge } from 'ant-design-vue'

const router = useRouter()
const route = useRoute()
const wsConnected = ref(false)
let ws = null
let pingTimer = null

const menuItems = [
  { key: '/', icon: h(DashboardOutlined), label: '异动' },
  { key: '/stocks', icon: h(FundOutlined), label: '股票池' },
  { key: '/signals', icon: h(StockOutlined), label: '信号' },
  { key: '/limit-up', icon: h(RocketOutlined), label: '涨停' },
  { key: '/bili', icon: h(VideoCameraOutlined), label: 'B站' },
  { key: '/monitor', icon: h(SettingOutlined), label: '监控' },
  { key: '/rag', icon: h(RobotOutlined), label: 'RAG' },
]

const selectedKeys = computed(() => [route.path])

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
  <a-layout style="min-height:100vh">
    <a-layout-sider collapsible theme="dark" width="220">
      <div class="sidebar-logo">
        <div>
          StockGod
          <small>复盘系统</small>
        </div>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        theme="dark"
        mode="inline"
        @click="({ key }) => router.push(key)"
        :items="menuItems"
      />
    </a-layout-sider>

    <a-layout>
      <a-layout-header style="background:#141414;padding:0 24px;display:flex;align-items:center;justify-content:flex-end;border-bottom:1px solid #303030;height:48px;line-height:48px;">
        <Badge :status="wsConnected ? 'success' : 'error'" :text="wsConnected ? '已连接' : '未连接'" />
      </a-layout-header>
      <a-layout-content class="site-content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>
