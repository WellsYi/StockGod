<script setup>
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { listSignals, countSignalsToday, getMonitorStatus, startMonitor, stopMonitor } from '../api/index.js'

// ── 状态 ──
const todayCount = ref(0)
const signals = ref([])
const taskStatus = ref({})
const loading = ref(false)
const msg = ref('')

// ── 实时流 ──
const liveFeed = ref([])
const meaningfulFeed = computed(() =>
  liveFeed.value.filter(item =>
    item.type === 'signal' ||
    (item.type === 'bili_dynamic' && item.data?.author)
  )
)
const newItemIds = ref(new Set())

// 信号类型配色
const TYPE_COLORS = {
  '异常放量': '#1677ff',
  '急涨': '#f5222d',
  'VWAP突破': '#722ed1',
  '逼近涨停': '#fa8c16',
  '连续拉升': '#eb2f96',
  '连续砸盘': '#52c41a',
}

// 信号类型分布
const typeDistribution = computed(() => {
  const counts = {}
  for (const s of signals.value) {
    const t = s.signal_type || '其他'
    counts[t] = (counts[t] || 0) + 1
  }
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1
  return Object.entries(counts)
    .map(([type, count]) => ({
      type, count, pct: Math.round(count / total * 100),
      color: TYPE_COLORS[type] || '#666',
    }))
    .sort((a, b) => b.count - a.count)
})

// 最新信号时间
const latestSignalTime = computed(() => {
  if (!signals.value.length) return '—'
  return signals.value[0]?.trigger_time?.replace('T', ' ')?.slice(11, 19) || '—'
})

// 信号表格列
const signalColumns = [
  { title: '时间', dataIndex: 'trigger_time', width: 160, customRender: ({ text }) => text?.replace('T', ' ')?.slice(11, 19) },
  { title: '代码', dataIndex: 'stock_code', width: 90 },
  { title: '名称', dataIndex: 'stock_name', width: 90 },
  {
    title: '信号', dataIndex: 'signal_type', width: 120,
    customRender: ({ text, record }) => {
      const color = record.change_pct > 0 ? 'red' : 'green'
      return h('span', { class: `ant-tag ant-tag-${color}` }, text)
    },
  },
  { title: '价格', dataIndex: 'price', width: 80, customRender: ({ text }) => text?.toFixed(2) },
  {
    title: '涨幅', dataIndex: 'change_pct', width: 80,
    customRender: ({ text }) => {
      const color = text > 0 ? '#f5222d' : text < 0 ? '#52c41a' : ''
      return h('span', { style: { color } }, `${text > 0 ? '+' : ''}${text?.toFixed(2)}%`)
    },
  },
  { title: 'LLM', dataIndex: 'llm_analysis', ellipsis: true, customRender: ({ text }) => text || '—' },
]

// ── 数据加载 ──
async function loadStats() {
  try {
    const [cnt, sigs, status] = await Promise.all([
      countSignalsToday(),
      listSignals({ limit: 50 }),
      getMonitorStatus(),
    ])
    todayCount.value = cnt.count
    signals.value = sigs
    taskStatus.value = status.tasks || {}
  } catch {}
}

// ── 任务控制 ──
async function handleStart(name) {
  loading.value = true
  try { msg.value = (await startMonitor(name)).message } catch { msg.value = '操作失败' }
  loading.value = false
  await loadStats()
}
async function handleStop(name) {
  loading.value = true
  try { msg.value = (await stopMonitor(name)).message } catch { msg.value = '操作失败' }
  loading.value = false
  await loadStats()
}

// ── WS 实时推送 ──
function onWsMessage(raw) {
  try {
    const msg = JSON.parse(raw)
    const id = msg.timestamp + (msg.data?.stock_code || msg.data?.dynamic_id || Math.random())
    liveFeed.value.unshift({ ...msg, _id: id, _new: true })
    if (liveFeed.value.length > 100) liveFeed.value.length = 100
  } catch {}
}

function handleWsEvent(e) { onWsMessage(e.detail) }

// ── 生命周期 ──
let statsInterval = null
let newItemTimer = null

onMounted(async () => {
  window.addEventListener('ws:message', handleWsEvent)
  await loadStats()
  statsInterval = setInterval(loadStats, 30000)
  newItemTimer = setInterval(() => { newItemIds.value.clear() }, 5000)
})

onUnmounted(() => {
  window.removeEventListener('ws:message', handleWsEvent)
  clearInterval(statsInterval)
  clearInterval(newItemTimer)
})
</script>

<template>
  <div class="dashboard">
    <a-alert v-if="msg" :message="msg" type="info" closable style="margin-bottom:12px" @close="msg=''" />

    <!-- KPI 卡片行 -->
    <a-row :gutter="12" class="kpi-row">
      <a-col :span="6">
        <a-card class="kpi-card" :bordered="false">
          <div class="kpi-inner">
            <span class="kpi-label">今日信号</span>
            <span class="kpi-value" style="color:#f5222d">{{ todayCount }}</span>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="kpi-card" :bordered="false">
          <div class="kpi-inner">
            <span class="kpi-label">运行中任务</span>
            <span class="kpi-value" style="color:#52c41a">{{ Object.values(taskStatus).filter(v => v === 'running').length }}</span>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="kpi-card" :bordered="false">
          <div class="kpi-inner">
            <span class="kpi-label">最新信号</span>
            <span class="kpi-value" style="color:#1677ff;font-size:20px">{{ latestSignalTime }}</span>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="kpi-card" :bordered="false">
          <div class="kpi-inner">
            <span class="kpi-label">信号类型</span>
            <span class="kpi-value" style="color:#722ed1">{{ typeDistribution.length }}种</span>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 实时流 + 信号类型分布 -->
    <a-row :gutter="12" class="mid-row">
      <a-col :span="16">
        <a-card title="实时异动流" class="feed-card" :bordered="false">
          <div class="feed-list" v-if="meaningfulFeed.length">
            <div
              v-for="item in meaningfulFeed"
              :key="item._id"
              class="feed-item"
              :class="{ 'feed-item-new': item._new }"
            >
              <span class="feed-time">{{ item.timestamp?.slice(11, 19) || item._time }}</span>
              <a-tag :color="item.type === 'signal' ? 'red' : 'blue'" size="small" style="margin:0 6px 0 0;line-height:20px;font-size:11px">
                {{ item.type === 'signal' ? '股票' : 'B站' }}
              </a-tag>
              <span class="feed-name">{{ item.data?.stock_name || item.data?.author || '—' }}</span>
              <span class="feed-detail" v-if="item.data?.signal_type">{{ item.data.signal_type }}</span>
              <span class="feed-code" v-if="item.data?.stock_code" style="color:rgba(255,255,255,.35);font-size:11px;margin-left:4px">{{ item.data.stock_code }}</span>
              <span class="feed-pct" v-if="item.data?.change_pct != null" :style="{ color: item.data.change_pct > 0 ? '#f5222d' : '#52c41a' }">
                {{ item.data.change_pct > 0 ? '+' : '' }}{{ item.data.change_pct.toFixed(2) }}%
              </span>
              <span class="feed-summary" v-if="item.data?.llm_summary" :title="item.data.llm_summary">💬</span>
            </div>
          </div>
          <div v-else class="feed-empty">
            <div class="feed-empty-icon">◉</div>
            <div style="margin-top:8px;font-size:14px;color:rgba(255,255,255,.65)">等待实时异动推送…</div>
            <div style="margin-top:4px;font-size:12px;color:rgba(255,255,255,.25)">股票信号和 B站动态会在这里实时展示</div>
          </div>
        </a-card>
      </a-col>

      <a-col :span="8">
        <a-card title="信号类型分布" class="dist-card" :bordered="false">
          <div v-if="typeDistribution.length" class="dist-list">
            <div v-for="d in typeDistribution" :key="d.type" class="dist-item">
              <div class="dist-header">
                <span class="dist-label">{{ d.type }}</span>
                <span class="dist-count">{{ d.count }}次</span>
              </div>
              <div class="dist-bar-track">
                <div class="dist-bar-fill" :style="{ width: d.pct + '%', background: d.color }" />
              </div>
            </div>
          </div>
          <div v-else style="text-align:center;padding:32px 0;color:rgba(255,255,255,.25);font-size:13px">暂无信号数据</div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 最近信号 + 后台任务 -->
    <a-row :gutter="12" class="bottom-row">
      <a-col :span="16">
        <a-card title="最近信号" :bordered="false">
          <a-table
            :dataSource="signals"
            :columns="signalColumns"
            :pagination="{ pageSize: 10, size: 'small' }"
            size="small"
            rowKey="id"
          />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="后台任务" :bordered="false">
          <a-list v-if="Object.keys(taskStatus).length" :dataSource="Object.entries(taskStatus)" size="small">
            <template #renderItem="{ item }">
              <a-list-item>
                <div class="task-item">
                  <div class="task-info">
                    <span class="task-name">{{ item[0] }}</span>
                    <a-tag :color="item[1] === 'running' ? 'green' : 'orange'" style="margin-left:8px;font-size:11px;line-height:20px">{{ item[1] }}</a-tag>
                  </div>
                  <div>
                    <a-button v-if="item[1] === 'stopped'" type="primary" size="small" :loading="loading" @click="handleStart(item[0])">启动</a-button>
                    <a-button v-if="item[1] === 'running'" danger size="small" :loading="loading" @click="handleStop(item[0])">停止</a-button>
                  </div>
                </div>
              </a-list-item>
            </template>
          </a-list>
          <div v-else style="text-align:center;padding:24px 0;color:rgba(255,255,255,.45);font-size:13px">加载中…</div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1400px;
}

/* ── KPI ── */
.kpi-row { margin-bottom: 12px; }
.kpi-card { background:#1a1a2e !important; border-radius:8px; }
.kpi-inner { display:flex; flex-direction:column; gap:4px; padding:4px 0; }
.kpi-label { font-size:12px; color:rgba(255,255,255,.45); }
.kpi-value { font-size:28px; font-weight:700; line-height:1.1; }

/* ── 实时流 ── */
.mid-row { margin-bottom: 12px; }
.feed-card :deep(.ant-card-head) { border-bottom:1px solid rgba(255,255,255,.06); min-height:44px; }
.feed-card :deep(.ant-card-head-title) { padding:12px 0; }
.feed-card :deep(.ant-card-body) { padding:8px 16px; }
.feed-list { margin:-8px -16px; max-height:250px; overflow-y:auto; }
.feed-item {
  display:flex; align-items:center; gap:6px;
  padding:8px 12px; font-size:13px;
  border-bottom:1px solid rgba(255,255,255,.04);
  transition:background .3s;
}
.feed-item:last-child { border-bottom:none; }
.feed-item-new {
  animation:feed-flash 3s ease-out;
}
@keyframes feed-flash {
  0%   { background:rgba(245,34,45,.12); }
  100% { background:transparent; }
}
.feed-time { color:rgba(255,255,255,.25); font-size:11px; min-width:52px; font-variant-numeric:tabular-nums; }
.feed-name { color:rgba(255,255,255,.85); font-weight:500; }
.feed-detail { color:rgba(255,255,255,.55); font-size:12px; }
.feed-pct { font-weight:600; font-size:12px; margin-left:auto; font-variant-numeric:tabular-nums; }
.feed-summary { cursor:help; font-size:13px; }
.feed-empty { text-align:center; padding:40px 0; }
.feed-empty-icon { font-size:28px; color:rgba(255,255,255,.08); }

/* ── 信号类型分布 ── */
.dist-card :deep(.ant-card-head) { border-bottom:1px solid rgba(255,255,255,.06); min-height:44px; }
.dist-card :deep(.ant-card-head-title) { padding:12px 0; }
.dist-card :deep(.ant-card-body) { padding:16px; }
.dist-list { display:flex; flex-direction:column; gap:12px; }
.dist-header { display:flex; justify-content:space-between; margin-bottom:4px; }
.dist-label { font-size:13px; color:rgba(255,255,255,.75); }
.dist-count { font-size:12px; color:rgba(255,255,255,.35); }
.dist-bar-track { height:6px; background:rgba(255,255,255,.06); border-radius:3px; overflow:hidden; }
.dist-bar-fill { height:100%; border-radius:3px; transition:width .6s ease; }

/* ── 任务 ── */
.bottom-row { margin-bottom:0; }
.task-item { display:flex; justify-content:space-between; align-items:center; width:100%; }
.task-info { display:flex; align-items:center; }
.task-name { font-size:13px; }

/* 暗色卡片统一 */
.dashboard :deep(.ant-card) { background:#1a1a2e; border-color:rgba(255,255,255,.06); }
.dashboard :deep(.ant-card-head) { background:transparent; border-bottom:1px solid rgba(255,255,255,.06); color:rgba(255,255,255,.85); }
</style>
