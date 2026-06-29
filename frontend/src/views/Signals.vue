<script setup>
import { ref, onMounted, h } from 'vue'
import { listSignals, getSignal, analyzeSignal, listAccuracy } from '../api/index.js'

const rows = ref([])
const stockCode = ref('')
const signalType = ref(undefined)
const loading = ref(false)

// 详情抽屉
const drawerVisible = ref(false)
const detail = ref(null)
const accuracy = ref(null)
const analyzing = ref(false)

const signalTypeOptions = [
  { value: '异常放量', label: '异常放量' },
  { value: '急涨', label: '急涨' },
  { value: 'VWAP突破', label: 'VWAP突破' },
  { value: '逼近涨停', label: '逼近涨停' },
  { value: '连续拉升', label: '连续拉升' },
  { value: '连续砸盘', label: '连续砸盘' },
]

const verdictColor = { pending: 'default', hit: 'green', miss: 'red', uncertain: 'orange' }
const verdictLabel = { pending: '待定', hit: '命中', miss: '错过', uncertain: '待确认' }

const columns = [
  { title: '时间', dataIndex: 'trigger_time', width: 170, customRender: ({ text }) => text?.replace('T', ' ') },
  { title: '代码', dataIndex: 'stock_code', width: 90 },
  { title: '名称', dataIndex: 'stock_name', width: 100 },
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
      if (text == null) return '—'
      const color = text > 0 ? '#f5222d' : text < 0 ? '#52c41a' : ''
      return h('span', { style: { color } }, `${text > 0 ? '+' : ''}${text?.toFixed(2)}%`)
    },
  },
  {
    title: 'LLM 解读', dataIndex: 'llm_analysis', ellipsis: true,
    customRender: ({ text }) => text || '—',
  },
]

async function load() {
  loading.value = true
  try {
    const params = { limit: 100 }
    if (stockCode.value) params.stock_code = stockCode.value
    if (signalType.value) params.signal_type = signalType.value
    rows.value = await listSignals(params)
  } catch {} finally { loading.value = false }
}

async function openDetail(row) {
  try {
    detail.value = null
    accuracy.value = null
    const [sig, accList] = await Promise.all([
      getSignal(row.id),
      listAccuracy({ limit: 200 }),
    ])
    detail.value = sig
    accuracy.value = accList.find(a => a.signal_id === row.id) || null
    drawerVisible.value = true
  } catch (e) {
    console.error('openDetail error:', e)
  }
}

async function handleAnalyze() {
  if (!detail.value || analyzing.value) return
  analyzing.value = true
  try {
    detail.value = await analyzeSignal(detail.value.id)
  } catch (e) {
    console.error('analyze error:', e)
  } finally {
    analyzing.value = false
  }
}

function formatSignalDetail(d) {
  if (!d) return null
  if (typeof d === 'string') { try { d = JSON.parse(d) } catch {} }
  if (typeof d !== 'object') return null
  const items = []
  // stock_monitor 产生的字段
  if (d.ratio != null) items.push({ label: '量比', value: d.ratio.toFixed(2) })
  if (d.amount != null) items.push({ label: '成交额', value: (d.amount / 1e8).toFixed(2) + '亿' })
  if (d.turnover != null) items.push({ label: '换手率', value: d.turnover.toFixed(2) + '%' })
  if (d.volume != null) items.push({ label: '成交量', value: (d.volume / 10000).toFixed(0) + '万手' })
  // 模拟测试或手动推送的字段
  if (d.volume_ratio != null) items.push({ label: '量比', value: d.volume_ratio.toFixed(2) })
  if (d.reason) items.push({ label: '原因', value: d.reason })
  return items.length ? items : [{ label: '原始数据', value: JSON.stringify(d) }]
}

onMounted(load)
</script>

<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">
      <a-input :value="stockCode" @update:value="v => stockCode = v" placeholder="股票代码" style="width:140px" allow-clear @pressEnter="load" />
      <a-select :value="signalType" @update:value="v => signalType = v" placeholder="全部信号" style="width:140px" :options="signalTypeOptions" allow-clear @change="load" />
      <a-button type="primary" :loading="loading" @click="load">查询</a-button>
      <span v-if="rows.length" style="color:rgba(255,255,255,.45);font-size:13px">共 {{ rows.length }} 条</span>
    </div>

    <a-card title="信号列表" :bordered="false">
      <a-table
        :dataSource="rows"
        :columns="columns"
        :loading="loading"
        :pagination="{ pageSize: 50 }"
        size="small"
        rowKey="id"
        :customRow="(record) => ({ onClick: () => openDetail(record) })"
      />
    </a-card>

    <!-- 详情抽屉 -->
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
          <div class="detail-row"><span class="dl">涨幅</span><span class="dd" :style="{ color: detail.change_pct > 0 ? '#f5222d' : '#52c41a' }">{{ detail.change_pct > 0 ? '+' : '' }}{{ detail.change_pct?.toFixed(2) }}%</span></div>
        </div>

        <!-- signal_detail 技术参数 -->
        <div class="detail-section" v-if="formatSignalDetail(detail.signal_detail)">
          <h4 class="detail-title">技术参数</h4>
          <div v-for="item in formatSignalDetail(detail.signal_detail)" :key="item.label" class="detail-row">
            <span class="dl">{{ item.label }}</span><span class="dd">{{ item.value }}</span>
          </div>
        </div>

        <!-- 准确率 -->
        <div class="detail-section" v-if="accuracy">
          <h4 class="detail-title">准确率追踪</h4>
          <div class="detail-row">
            <span class="dl">判定</span>
            <span class="dd"><a-tag :color="verdictColor[accuracy.verdict]">{{ verdictLabel[accuracy.verdict] }}</a-tag></span>
          </div>
          <div class="detail-row" v-if="accuracy.price_5min"><span class="dl">5分钟价</span><span class="dd">{{ accuracy.price_5min?.toFixed(2) }}</span></div>
          <div class="detail-row" v-if="accuracy.price_15min"><span class="dl">15分钟价</span><span class="dd">{{ accuracy.price_15min?.toFixed(2) }}</span></div>
          <div class="detail-row" v-if="accuracy.price_30min"><span class="dl">30分钟价</span><span class="dd">{{ accuracy.price_30min?.toFixed(2) }}</span></div>
          <div class="detail-row" v-if="accuracy.price_close"><span class="dl">收盘价</span><span class="dd">{{ accuracy.price_close?.toFixed(2) }}</span></div>
          <div class="detail-row" v-if="accuracy.close_change"><span class="dl">收盘涨跌</span><span class="dd" :style="{ color: accuracy.close_change > 0 ? '#f5222d' : '#52c41a' }">{{ accuracy.close_change > 0 ? '+' : '' }}{{ accuracy.close_change?.toFixed(2) }}%</span></div>
        </div>

        <!-- LLM 分析 -->
        <div class="detail-section">
          <h4 class="detail-title" style="display:flex;align-items:center;justify-content:space-between">
            <span>LLM 解读</span>
            <a-button v-if="!detail.llm_analysis" size="small" type="primary" ghost :loading="analyzing" @click="handleAnalyze">生成解读</a-button>
          </h4>
          <p v-if="detail.llm_analysis" style="white-space:pre-wrap;color:rgba(255,255,255,.75);font-size:13px;line-height:1.6;margin:0">{{ detail.llm_analysis }}</p>
          <p v-else style="color:rgba(255,255,255,.25);font-size:12px;margin:0">暂无 LLM 解读，点击上方按钮生成</p>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<style scoped>
.detail-section {
  margin-bottom: 20px; padding-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,.06);
}
.detail-section:last-child { border-bottom: none; }
.detail-title { font-size:13px; color:rgba(255,255,255,.45); margin:0 0 10px 0; }
.detail-row { display:flex; padding:4px 0; font-size:13px; }
.dl { width:80px; color:rgba(255,255,255,.45); flex-shrink:0; }
.dd { color:rgba(255,255,255,.85); }
</style>
