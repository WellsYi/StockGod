<script setup>
import { ref, onMounted, h } from 'vue'
import { listLimitUp } from '../api/index.js'

const rows = ref([])
const tradeDate = ref(undefined)
const loading = ref(false)

const columns = [
  { title: '日期', dataIndex: 'trade_date', width: 100 },
  { title: '代码', dataIndex: 'stock_code', width: 90 },
  { title: '名称', dataIndex: 'stock_name', width: 100 },
  { title: '涨停价', dataIndex: 'price', width: 90, customRender: ({ text }) => text?.toFixed(2) },
  { title: '涨幅', dataIndex: 'change_pct', width: 80, customRender: ({ text }) => `+${text?.toFixed(2)}%` },
  {
    title: '连板', dataIndex: 'limit_times', width: 80,
    customRender: ({ text }) => h('span', { class: `ant-tag ant-tag-${text >= 3 ? 'red' : 'orange'}` }, `${text}连板`),
  },
  { title: '封单(亿)', dataIndex: 'fd_amount', width: 100, customRender: ({ text }) => text?.toFixed(2) },
  { title: '换手率', dataIndex: 'turnover_rate', width: 80, customRender: ({ text }) => `${text?.toFixed(2)}%` },
  { title: '板型', dataIndex: 'board_type', width: 70 },
  { title: '概念标签', dataIndex: 'concept_tags', ellipsis: true, customRender: ({ text }) => text?.join(', ') || '—' },
]

async function load() {
  loading.value = true
  try {
    const params = { limit: 100 }
    if (tradeDate.value) params.trade_date = tradeDate.value.format('YYYY-MM-DD')
    rows.value = await listLimitUp(params)
  } catch {} finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <a-date-picker :value="tradeDate" @update:value="v => tradeDate = v" placeholder="选择日期" allow-clear @change="load" />
      <a-button type="primary" :loading="loading" @click="load">查询</a-button>
      <span v-if="rows.length" style="color:rgba(255,255,255,.45);font-size:13px">共 {{ rows.length }} 条</span>
    </div>

    <a-card title="涨停板">
      <a-table :dataSource="rows" :columns="columns" :loading="loading" :pagination="{ pageSize: 50 }" size="small" rowKey="id" />
    </a-card>
  </div>
</template>
