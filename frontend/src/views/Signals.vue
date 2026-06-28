<script setup>
import { ref, onMounted, h } from 'vue'
import { listSignals } from '../api/index.js'

const rows = ref([])
const stockCode = ref('')
const signalType = ref(undefined)
const loading = ref(false)

const columns = [
  { title: '时间', dataIndex: 'trigger_time', width: 170, customRender: ({ text }) => text?.replace('T', ' ') },
  { title: '代码', dataIndex: 'stock_code', width: 90 },
  { title: '名称', dataIndex: 'stock_name', width: 100 },
  {
    title: '信号类型', dataIndex: 'signal_type', width: 120,
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
  {
    title: 'LLM 解读', dataIndex: 'llm_analysis', ellipsis: true,
    customRender: ({ text }) => text || '—',
  },
]

const signalTypeOptions = [
  { value: '异常放量', label: '异常放量' },
  { value: '急涨', label: '急涨' },
  { value: 'VWAP突破', label: 'VWAP突破' },
  { value: '逼近涨停', label: '逼近涨停' },
  { value: '连续拉升', label: '连续拉升' },
  { value: '连续砸盘', label: '连续砸盘' },
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

onMounted(load)
</script>

<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">
      <a-input :value="stockCode" @update:value="v => stockCode = v" placeholder="股票代码" style="width:140px" allow-clear @pressEnter="load" />
      <a-select :value="signalType" @update:value="v => signalType = v" placeholder="全部信号" style="width:140px" :options="signalTypeOptions" allow-clear @change="load" />
      <a-button type="primary" :loading="loading" @click="load">查询</a-button>
    </div>

    <a-card title="信号列表">
      <a-table :dataSource="rows" :columns="columns" :loading="loading" :pagination="{ pageSize: 50 }" size="small" rowKey="id" />
    </a-card>
  </div>
</template>
