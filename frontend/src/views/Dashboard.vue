<script setup>
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { listSignals, getSignal, countSignalsToday, getMonitorStatus, startMonitor, stopMonitor } from '../api/index.js'

const router = useRouter()

// ── 状态 ──
const todayCount = ref(0)
const signals = ref([])
const taskStatus = ref({})
const loading = ref(false)
const msg = ref('')

// 详情抽屉
const drawerVisible = ref(false)
const detail = ref(null)

// ── 实时流 ──
const liveFeed = ref([])
const meaningfulFeed = computed(() =>
  liveFeed.value.filter(item =>
    item.type === 'signal' ||
    (item.type === 'bili_dynamic' && item.data?.author)
  )
)

// 信号类型配色
const TYPE_COLORS = {
  '异常放量': '#00D4FF',
  '急涨': '#FF4444',
  'VWAP突破': '#7C3AED',
  '逼近涨停': '#FF9800',
  '连续拉升': '#FF4444',
  '连续砸盘': '#00E676',
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
  { title: '时间', dataIndex: 'trigger_time', width: 100,
    customRender: ({ text }) => text?.replace('T', ' ')?.slice(11, 19) },
  { title: '代码', dataIndex: 'stock_code', width: 80 },
  { title: '名称', dataIndex: 'stock_name', width: 90 },
  {
    title: '信号', dataIndex: 'signal_type', width: 120,
    customRender: ({ text }) => renderSignalBadge(text),
  },
  { title: '价格', dataIndex: 'price', width: 80,
    customRender: ({ text }) => text != null ? text.toFixed(2) : '—' },
  {
    title: '涨幅', dataIndex: 'change_pct', width: 90,
    customRender: ({ text }) => renderChangePct(text),
  },
  { title: 'LLM', dataIndex: 'llm_analysis', ellipsis: true,
    customRender: ({ text }) => {
      if (!text) return h('span', { style: 'color:var(--text-muted)' }, '—')
      return h('span', { class: 'td-llm has-content', title: text }, text)
    }},
]

function renderSignalBadge(type) {
  const cls = type === '异常放量' ? 'sig-vol' :
    type === '站上分时均线' || type === 'VWAP突破' ? 'sig-ma' :
    type === '异常放量拉升' || type === '连续拉升' ? 'sig-surge' :
    type === '连续砸盘' ? 'sig-dump' : 'sig-default'
  return h('span', { class: `signal-badge ${cls}` }, type)
}

function renderChangePct(text) {
  if (text == null) return '—'
  const dir = text > 0 ? '▲' : text < 0 ? '▼' : ''
  const cls = text > 0 ? 'up' : text < 0 ? 'down' : ''
  return h('span', { class: `td-change ${cls}` }, `${dir} ${text > 0 ? '+' : ''}${text.toFixed(2)}%`)
}

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

// ── 信号详情抽屉 ──
async function openDetail(row) {
  try {
    detail.value = null
    detail.value = await getSignal(row.id)
    drawerVisible.value = true
  } catch (e) {
    console.error('openDetail error:', e)
  }
}

function handleRowClick(record) {
  openDetail(record)
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
    const msgObj = JSON.parse(raw)
    const id = msgObj.timestamp + (msgObj.data?.stock_code || msgObj.data?.dynamic_id || Math.random())
    liveFeed.value.unshift({ ...msgObj, _id: id })
    if (liveFeed.value.length > 100) liveFeed.value.length = 100
  } catch {}
}
function handleWsEvent(e) { onWsMessage(e.detail) }

// ── 生命周期 ──
let statsInterval = null
onMounted(async () => {
  window.addEventListener('ws:message', handleWsEvent)
  await loadStats()
  statsInterval = setInterval(loadStats, 30000)
})
onUnmounted(() => {
  window.removeEventListener('ws:message', handleWsEvent)
  clearInterval(statsInterval)
})

function getDistClass(pct) {
  if (pct >= 70) return 'fill-blue'
  if (pct >= 40) return 'fill-green'
  return 'fill-orange'
}

function getTaskRunningCount() {
  return Object.values(taskStatus.value).filter(v => v === 'running').length
}
</script>

<template>
  <div class="dashboard">
    <a-alert v-if="msg" :message="msg" type="info" closable style="margin-bottom:0" @close="msg=''" />

    <!-- STATS CARDS -->
    <div class="stats-grid">
      <div class="stat-card blue">
        <div class="stat-card-header">
          <span class="stat-label">今日信号</span>
          <div class="stat-icon blue">🔔</div>
        </div>
        <div class="stat-value blue">{{ todayCount }}</div>
        <div class="stat-trend">实时更新</div>
      </div>
      <div class="stat-card green">
        <div class="stat-card-header">
          <span class="stat-label">运行中任务</span>
          <div class="stat-icon green">▶</div>
        </div>
        <div class="stat-value green">{{ getTaskRunningCount() }}</div>
        <div class="stat-trend">{{ getTaskRunningCount() > 0 ? '● 全部正常运行' : '无运行任务' }}</div>
      </div>
      <div class="stat-card orange">
        <div class="stat-card-header">
          <span class="stat-label">最新信号</span>
          <div class="stat-icon orange">⏱</div>
        </div>
        <div class="stat-value orange" style="font-size:22px; padding-top:5px;">{{ latestSignalTime }}</div>
        <div class="stat-trend">实时监控中</div>
      </div>
      <div class="stat-card purple">
        <div class="stat-card-header">
          <span class="stat-label">信号类型</span>
          <div class="stat-icon purple">≡</div>
        </div>
        <div class="stat-value purple">{{ typeDistribution.length }}<span style="font-size:14px;font-family:Inter;margin-left:4px;">种</span></div>
        <div class="stat-trend">{{ typeDistribution.map(d => d.type).join(' / ') }}</div>
      </div>
    </div>

    <!-- MIDDLE: live stream + signal distribution -->
    <div class="middle-grid">
      <!-- Live Stream -->
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">实时异动流</div>
          <span class="panel-badge">LIVE</span>
        </div>
        <div class="live-stream-body" v-if="!meaningfulFeed.length">
          <div class="radar-ring"><div class="radar-center"></div></div>
          <div class="waiting-text">
            等待实时异动推送<span class="cursor-blink">_</span><br>
            <span style="opacity:0.5;">股票信号和 B 站动态将在此实时显示</span>
          </div>
        </div>
        <div class="feed-list" v-else>
          <div v-for="item in meaningfulFeed" :key="item._id" class="feed-item">
            <span class="feed-time">{{ item.timestamp?.slice(11, 19) || item._time }}</span>
            <span class="feed-tag" :class="item.type === 'signal' ? 'tag-stock' : 'tag-bili'">{{ item.type === 'signal' ? '股票' : 'B站' }}</span>
            <span class="feed-name">{{ item.data?.stock_name || item.data?.author || '—' }}</span>
            <span class="feed-detail" v-if="item.data?.signal_type">{{ item.data.signal_type }}</span>
            <span class="feed-pct" :class="item.data?.change_pct > 0 ? 'up' : 'down'" v-if="item.data?.change_pct != null">
              {{ item.data.change_pct > 0 ? '+' : '' }}{{ item.data.change_pct.toFixed(2) }}%
            </span>
            <span class="feed-llm" v-if="item.data?.llm_summary" :title="item.data.llm_summary">💬</span>
          </div>
        </div>
      </div>

      <!-- Signal Distribution -->
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">信号类型分布</div>
        </div>
        <div class="signal-dist-body">
          <div v-if="typeDistribution.length" class="dist-list">
            <div v-for="d in typeDistribution" :key="d.type" class="dist-item">
              <div class="dist-label-row">
                <div class="dist-label">
                  <div class="dist-dot" :style="{ background: d.color }"></div>
                  {{ d.type }}
                </div>
                <div class="dist-count">{{ d.count }} 次</div>
              </div>
              <div class="dist-bar-track">
                <div class="dist-bar-fill" :class="getDistClass(d.pct)" :style="{ width: d.pct + '%' }"></div>
              </div>
            </div>
          </div>
          <div v-else style="text-align:center;padding:32px 0;color:var(--text-muted);font-size:13px">暂无信号数据</div>
        </div>
      </div>
    </div>

    <!-- SIGNALS TABLE -->
    <div class="panel table-panel">
      <div class="panel-header">
        <div class="panel-title">最近信号</div>
        <span class="panel-badge">{{ signals.length }} 条记录</span>
      </div>
      <a-table
        :dataSource="signals"
        :columns="signalColumns"
        :pagination="{ pageSize: 10, size: 'small', showSizeChanger: false }"
        size="small"
        rowKey="id"
        :customRow="(record) => ({ onClick: () => handleRowClick(record) })"
      />
    </div>

    <!-- 信号详情抽屉 -->
    <a-drawer
      :open="drawerVisible"
      @close="drawerVisible = false"
      title="信号详情"
      placement="right"
      width="480"
    >
      <template v-if="detail">
        <div class="detail-section">
          <div class="detail-row"><span class="dl">股票</span><span class="dd">{{ detail.stock_name }}（{{ detail.stock_code }}）</span></div>
          <div class="detail-row"><span class="dl">时间</span><span class="dd">{{ detail.trigger_time?.replace('T', ' ') }}</span></div>
          <div class="detail-row"><span class="dl">信号</span><span class="dd"><a-tag :color="detail.change_pct > 0 ? 'red' : 'green'">{{ detail.signal_type }}</a-tag></span></div>
          <div class="detail-row"><span class="dl">价格</span><span class="dd">{{ detail.price?.toFixed(2) }}</span></div>
          <div class="detail-row"><span class="dl">涨幅</span><span class="dd" :style="{ color: detail.change_pct > 0 ? '#FF4444' : '#00E676' }">{{ detail.change_pct > 0 ? '+' : '' }}{{ detail.change_pct?.toFixed(2) }}%</span></div>
        </div>

        <div class="detail-section" v-if="detail.signal_detail && typeof detail.signal_detail === 'object'">
          <h4 class="detail-title">技术参数</h4>
          <div v-for="(v, k) in detail.signal_detail" :key="k" class="detail-row">
            <span class="dl">{{ k }}</span><span class="dd">{{ v }}</span>
          </div>
        </div>

        <div class="detail-section" v-if="detail.llm_analysis">
          <h4 class="detail-title">LLM 解读</h4>
          <p style="white-space:pre-wrap;color:rgba(255,255,255,.75);font-size:13px;line-height:1.6;margin:0">{{ detail.llm_analysis }}</p>
        </div>
      </template>
    </a-drawer>

    <!-- TASKS -->
    <div class="panel" v-if="Object.keys(taskStatus).length">
      <div class="panel-header" style="padding:12px 20px">
        <div class="panel-title">后台任务</div>
        <span class="panel-badge">{{ getTaskRunningCount() }} 运行中</span>
      </div>
      <div class="tasks-body">
        <div v-for="(status, name) in taskStatus" :key="name" class="task-row" :class="{ stopped: status !== 'running' }">
          <div class="task-left">
            <span class="task-name">{{ name }}</span>
            <div class="running-badge" v-if="status === 'running'">
              <div class="running-dot"></div>
              RUNNING
            </div>
            <span class="stopped-badge" v-else>STOPPED</span>
          </div>
          <div class="task-right">
            <button v-if="status === 'running'" class="stop-btn" :loading="loading" @click="handleStop(name)">停止</button>
            <button v-else class="start-btn" :loading="loading" @click="handleStart(name)">启动</button>
          </div>
          <div class="task-progress" v-if="status === 'running'">
            <div class="task-progress-bar"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== STATS CARDS ===== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 18px 20px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}
.stat-card:hover {
  background: var(--bg-card-hover);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
}
.stat-card.blue::before { background: linear-gradient(90deg, transparent, #00D4FF, transparent); }
.stat-card.green::before { background: linear-gradient(90deg, transparent, #00E676, transparent); }
.stat-card.orange::before { background: linear-gradient(90deg, transparent, #FF9800, transparent); }
.stat-card.purple::before { background: linear-gradient(90deg, transparent, #7C3AED, transparent); }

.stat-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.stat-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 500;
}
.stat-icon {
  width: 28px; height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}
.stat-icon.blue { background: rgba(0,212,255,0.12); color: #00D4FF; }
.stat-icon.green { background: rgba(0,230,118,0.12); color: #00E676; }
.stat-icon.orange { background: rgba(255,152,0,0.12); color: #FF9800; }
.stat-icon.purple { background: rgba(124,58,237,0.12); color: #A78BFA; }

.stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 8px;
}
.stat-value.blue { color: #00D4FF; text-shadow: 0 0 20px rgba(0,212,255,0.4); }
.stat-value.green { color: #00E676; text-shadow: 0 0 20px rgba(0,230,118,0.4); }
.stat-value.orange { color: #FF9800; text-shadow: 0 0 20px rgba(255,152,0,0.4); }
.stat-value.purple { color: #A78BFA; text-shadow: 0 0 20px rgba(167,139,250,0.4); }
.stat-trend {
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ===== MIDDLE SECTION ===== */
.middle-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 16px;
}
.panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  backdrop-filter: blur(10px);
}
.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.panel-title::before {
  content: '';
  width: 3px; height: 14px;
  background: linear-gradient(180deg, var(--accent-blue), var(--accent-purple));
  border-radius: 2px;
}
.panel-badge {
  font-size: 10px;
  padding: 2px 8px;
  background: rgba(0,212,255,0.1);
  border: 1px solid rgba(0,212,255,0.2);
  border-radius: 20px;
  color: var(--accent-blue);
  font-family: 'JetBrains Mono', monospace;
}

/* ── Live Stream ── */
.live-stream-body {
  height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  position: relative;
  overflow: hidden;
}
.live-stream-body::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 50%, rgba(0,212,255,0.03) 0%, transparent 60%),
    repeating-linear-gradient(0deg, transparent, transparent 24px, rgba(255,255,255,0.02) 25px),
    repeating-linear-gradient(90deg, transparent, transparent 24px, rgba(255,255,255,0.02) 25px);
}
.radar-ring {
  position: relative;
  width: 60px; height: 60px;
}
.radar-ring::before, .radar-ring::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(0,212,255,0.3);
  animation: radar-expand 2.5s ease-out infinite;
}
.radar-ring::before { width: 60px; height: 60px; top: 0; left: 0; }
.radar-ring::after { width: 60px; height: 60px; top: 0; left: 0; animation-delay: 1.25s; }
.radar-center {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 8px; height: 8px;
  background: var(--accent-blue);
  border-radius: 50%;
  box-shadow: 0 0 12px var(--accent-blue);
}
@keyframes radar-expand {
  0% { transform: scale(0.5); opacity: 1; }
  100% { transform: scale(2.5); opacity: 0; }
}
.waiting-text {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  text-align: center;
  line-height: 1.8;
}
.cursor-blink {
  display: inline-block;
  animation: blink 1.2s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* feed list when has data */
.feed-list {
  padding: 8px 0;
  max-height: 320px;
  overflow-y: auto;
}
.feed-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  font-size: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  transition: background 0.2s;
}
.feed-item:last-child { border-bottom: none; }
.feed-item:hover { background: rgba(0,212,255,0.04); }
.feed-time { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted); min-width: 52px; }
.feed-tag {
  font-size: 10px; padding: 1px 6px; border-radius: 3px;
  font-weight: 500; line-height: 18px;
}
.tag-stock { background: rgba(0,212,255,0.1); color: #00D4FF; border: 1px solid rgba(0,212,255,0.2); }
.tag-bili { background: rgba(124,58,237,0.1); color: #A78BFA; border: 1px solid rgba(124,58,237,0.2); }
.feed-name { color: var(--text-primary); font-weight: 500; }
.feed-detail { color: var(--text-secondary); }
.feed-pct { font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 12px; margin-left: auto; }
.feed-pct.up { color: var(--accent-red); }
.feed-pct.down { color: var(--accent-green); }
.feed-llm { cursor: help; font-size: 13px; }

/* ── Signal Distribution ── */
.signal-dist-body { padding: 16px 20px; }
.dist-list { display: flex; flex-direction: column; gap: 14px; }
.dist-item { display: flex; flex-direction: column; gap: 6px; }
.dist-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.dist-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}
.dist-dot { width: 6px; height: 6px; border-radius: 50%; }
.dist-count {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-muted);
}
.dist-bar-track {
  height: 6px;
  background: rgba(255,255,255,0.06);
  border-radius: 999px;
  overflow: hidden;
}
.dist-bar-fill {
  height: 100%;
  border-radius: 999px;
  position: relative;
}
.dist-bar-fill::after {
  content: '';
  position: absolute;
  right: 0; top: 0; bottom: 0;
  width: 20px;
  background: inherit;
  filter: blur(6px);
  border-radius: 999px;
}
.fill-blue { background: linear-gradient(90deg, #0066FF, #00D4FF); box-shadow: 0 0 8px rgba(0,212,255,0.4); }
.fill-green { background: linear-gradient(90deg, #00A854, #00E676); box-shadow: 0 0 8px rgba(0,230,118,0.4); }
.fill-orange { background: linear-gradient(90deg, #E65100, #FF9800); box-shadow: 0 0 8px rgba(255,152,0,0.4); }

/* ── Signal Table Overrides ── */
.table-panel :deep(.ant-table) { background: transparent !important; }
.table-panel :deep(.ant-table-thead > tr > th) {
  background: rgba(255,255,255,0.02) !important;
  border-bottom: 1px solid var(--border-color) !important;
  color: var(--text-muted) !important;
  font-size: 10px !important;
  text-transform: uppercase;
  letter-spacing: 1.5px !important;
  font-weight: 600 !important;
}
.table-panel :deep(.ant-table-tbody > tr > td) {
  border-bottom: 1px solid rgba(255,255,255,0.03) !important;
  font-size: 12px !important;
  padding: 11px 16px !important;
  color: var(--text-secondary) !important;
}
.table-panel :deep(.ant-table-tbody > tr:hover > td) {
  background: rgba(0,212,255,0.04) !important;
}

/* signal badges (used via v-html) */
:deep(.signal-badge) {
  display: inline-flex; align-items: center; padding: 2px 8px;
  border-radius: 4px; font-size: 10px; font-weight: 500; white-space: nowrap;
}
:deep(.sig-vol) { background: rgba(0,212,255,0.1); color: #00D4FF; border: 1px solid rgba(0,212,255,0.2); }
:deep(.sig-ma) { background: rgba(0,230,118,0.1); color: #00E676; border: 1px solid rgba(0,230,118,0.2); }
:deep(.sig-surge) { background: rgba(255,152,0,0.1); color: #FF9800; border: 1px solid rgba(255,152,0,0.2); }
:deep(.sig-dump) { background: rgba(255,68,68,0.1); color: #FF4444; border: 1px solid rgba(255,68,68,0.2); }
:deep(.sig-default) { background: rgba(255,255,255,0.06); color: var(--text-secondary); border: 1px solid rgba(255,255,255,0.1); }

:deep(.td-change) { font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 12px; }
:deep(.td-change.up) { color: var(--accent-red); }
:deep(.td-change.down) { color: var(--accent-green); }

:deep(.td-llm) { font-size: 11px; color: var(--text-muted); max-width: 180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
:deep(.td-llm.has-content) { color: #A78BFA; cursor:pointer; }

/* ── Detail Drawer ── */
.detail-section {
  margin-bottom: 20px; padding-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,.06);
}
.detail-section:last-child { border-bottom: none; }
.detail-title { font-size:13px; color:rgba(255,255,255,.45); margin:0 0 10px 0; }
.detail-row { display:flex; padding:4px 0; font-size:13px; }
.dl { width:80px; color:rgba(255,255,255,.45); flex-shrink:0; }
.dd { color:rgba(255,255,255,.85); }

/* ── Tasks ── */
.tasks-body {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.task-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}
.task-row:hover { background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.1); }
.task-left { display: flex; align-items: center; gap: 12px; }
.task-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-secondary);
  background: rgba(255,255,255,0.06);
  padding: 3px 8px;
  border-radius: 4px;
}
.running-badge {
  display: flex; align-items: center; gap: 5px;
  padding: 3px 8px;
  background: rgba(0,230,118,0.08);
  border: 1px solid rgba(0,230,118,0.2);
  border-radius: 20px;
  font-size: 10px;
  color: var(--accent-green);
  font-weight: 600;
  letter-spacing: 0.5px;
}
.running-dot {
  width: 5px; height: 5px;
  background: var(--accent-green);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--accent-green);
  animation: pulse-dot 1.5s infinite;
}
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 6px var(--accent-green); }
  50% { box-shadow: 0 0 12px var(--accent-green), 0 0 18px rgba(0,230,118,0.4); }
}
.stopped-badge {
  font-size: 10px; font-weight: 600; letter-spacing: 0.5px;
  color: var(--text-muted); padding: 3px 8px;
  background: rgba(255,255,255,0.04);
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.08);
}
.task-right { display: flex; align-items: center; gap: 8px; }
.stop-btn {
  padding: 4px 12px;
  border: 1px solid rgba(255,68,68,0.4);
  background: transparent;
  color: #FF6B6B;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.stop-btn:hover {
  background: rgba(255,68,68,0.12);
  border-color: #FF4444;
  color: #FF4444;
  box-shadow: 0 0 12px rgba(255,68,68,0.2);
}
.start-btn {
  padding: 4px 12px;
  border: 1px solid rgba(0,212,255,0.4);
  background: transparent;
  color: var(--accent-blue);
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.start-btn:hover {
  background: rgba(0,212,255,0.12);
  border-color: var(--accent-blue);
  box-shadow: 0 0 12px rgba(0,212,255,0.2);
}
.task-progress {
  position: absolute; bottom: 0; left: 0; right: 0;
  height: 2px;
  background: rgba(0,230,118,0.1);
  overflow: hidden;
}
.task-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-green), rgba(0,230,118,0.4));
  animation: progress-scan 3s ease-in-out infinite;
}
@keyframes progress-scan {
  0% { width: 20%; margin-left: 0; }
  50% { width: 40%; margin-left: 40%; }
  100% { width: 20%; margin-left: 80%; }
}
</style>
