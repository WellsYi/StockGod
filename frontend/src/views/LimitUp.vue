<script setup>
import { ref, onMounted, h } from 'vue'
import { listLimitUp, getLimitUp } from '../api/index.js'

const rows = ref([])
const tradeDate = ref(undefined)
const loading = ref(false)

// 详情抽屉
const drawerVisible = ref(false)
const detail = ref(null)

const columns = [
  { title: '日期', dataIndex: 'trade_date', width: 100 },
  { title: '代码', dataIndex: 'stock_code', width: 90 },
  { title: '名称', dataIndex: 'stock_name', width: 100 },
  { title: '涨停价', dataIndex: 'price', width: 90, customRender: ({ text }) => text?.toFixed(2) },
  { title: '涨幅', dataIndex: 'change_pct', width: 80, customRender: ({ text }) => `+${text?.toFixed(2)}%` },
  {
    title: '连板', dataIndex: 'limit_times', width: 70,
    customRender: ({ text }) => h('span', { class: `ant-tag ant-tag-${text >= 3 ? 'red' : 'orange'}` }, `${text}连板`),
  },
  { title: '封单(亿)', dataIndex: 'fd_amount', width: 90, customRender: ({ text }) => text?.toFixed(2) },
  { title: '换手率', dataIndex: 'turnover_rate', width: 70, customRender: ({ text }) => `${text?.toFixed(2)}%` },
  { title: '板型', dataIndex: 'board_type', width: 60 },
  {
    title: '原因', dataIndex: 'reason_tags', ellipsis: true, width: 160,
    customRender: ({ text }) => {
      if (!text?.length) return '—'
      return h('span', text.map(t => h('span', { class: 'ant-tag', style: 'font-size:11px;line-height:18px;margin:1px 2px' }, t)))
    },
  },
  { title: '概念', dataIndex: 'concept_tags', ellipsis: true, width: 140, customRender: ({ text }) => text?.join(', ') || '—' },
]

async function load() {
  loading.value = true
  try {
    const params = { limit: 100 }
    if (tradeDate.value) params.trade_date = tradeDate.value.format('YYYY-MM-DD')
    rows.value = await listLimitUp(params)
  } catch {} finally { loading.value = false }
}

async function openDetail(row) {
  try {
    detail.value = null
    detail.value = await getLimitUp(row.id)
    drawerVisible.value = true
  } catch (e) {
    console.error('openDetail error:', e)
  }
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

    <a-card title="涨停板" :bordered="false">
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
      title="涨停详情"
      placement="right"
      width="480"
    >
      <template v-if="detail">
        <div class="detail-section">
          <div class="detail-row"><span class="dl">股票</span><span class="dd">{{ detail.stock_name }}（{{ detail.stock_code }}）</span></div>
          <div class="detail-row"><span class="dl">日期</span><span class="dd">{{ detail.trade_date }}</span></div>
          <div class="detail-row"><span class="dl">涨停价</span><span class="dd">{{ detail.price?.toFixed(2) }}</span></div>
          <div class="detail-row"><span class="dl">涨幅</span><span class="dd" style="color:#f5222d">+{{ detail.change_pct?.toFixed(2) }}%</span></div>
          <div class="detail-row"><span class="dl">连板</span><span class="dd"><a-tag :color="detail.limit_times >= 3 ? 'red' : 'orange'">{{ detail.limit_times }}连板</a-tag></span></div>
          <div class="detail-row" v-if="detail.board_type"><span class="dl">板型</span><span class="dd">{{ detail.board_type }}</span></div>
          <div class="detail-row" v-if="detail.fd_amount"><span class="dl">封单</span><span class="dd">{{ detail.fd_amount?.toFixed(2) }}亿</span></div>
          <div class="detail-row" v-if="detail.turnover_rate"><span class="dl">换手率</span><span class="dd">{{ detail.turnover_rate?.toFixed(2) }}%</span></div>
        </div>

        <!-- 概念标签 -->
        <div class="detail-section" v-if="detail.concept_tags?.length">
          <h4 class="detail-title">概念板块</h4>
          <span v-for="t in detail.concept_tags" :key="t" class="ant-tag ant-tag-blue" style="margin:2px 4px 2px 0;font-size:12px">{{ t }}</span>
        </div>

        <!-- 原因标签 -->
        <div class="detail-section" v-if="detail.reason_tags?.length">
          <h4 class="detail-title">原因标签</h4>
          <span v-for="t in detail.reason_tags" :key="t" class="ant-tag" style="margin:2px 4px 2px 0;font-size:12px">{{ t }}</span>
        </div>

        <!-- LLM 原因分析 -->
        <div class="detail-section" v-if="detail.reason_llm">
          <h4 class="detail-title">LLM 涨停原因</h4>
          <p style="white-space:pre-wrap;color:rgba(255,255,255,.65);font-size:13px;line-height:1.6;margin:0">{{ detail.reason_llm }}</p>
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
.dl { width:70px; color:rgba(255,255,255,.45); flex-shrink:0; }
.dd { color:rgba(255,255,255,.85); }
</style>
