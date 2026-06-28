<script setup>
import { ref, onMounted, h } from 'vue'
import { listStocks, addStock, removeStock } from '../api/index.js'
import { Modal } from 'ant-design-vue'

const stocks = ref([])
const codeInput = ref('')
const adding = ref(false)
const msg = ref('')

async function load() {
  try { stocks.value = await listStocks() } catch {}
}

async function handleAdd() {
  const code = codeInput.value.trim()
  if (!code) return
  adding.value = true
  msg.value = ''
  try {
    const res = await addStock(code)
    msg.value = res.message || '添加成功'
    codeInput.value = ''
    await load()
  } catch (e) {
    msg.value = e.response?.data?.detail || '添加失败'
  } finally { adding.value = false }
}

function confirmRemove(code, name) {
  Modal.confirm({
    title: '确认删除',
    content: `确定要从股票池中移除 ${name}（${code}）吗？`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        const res = await removeStock(code)
        msg.value = res.message || '删除成功'
        await load()
      } catch (e) {
        msg.value = e.response?.data?.detail || '删除失败'
      }
    },
  })
}

const columns = [
  { title: '代码', dataIndex: 'code', width: 100 },
  { title: '名称', dataIndex: 'name', width: 140 },
  {
    title: '市场', dataIndex: 'market', width: 80,
    customRender: ({ text }) => text === 1 ? '上证' : '深证',
  },
  {
    title: '操作', key: 'action', width: 100,
    customRender: ({ record }) => h('a-button', {
      danger: true, size: 'small',
      onClick: () => confirmRemove(record.code, record.name),
    }, '删除'),
  },
]

onMounted(load)
</script>

<template>
  <div>
    <a-alert v-if="msg" :message="msg" type="info" closable style="margin-bottom:12px" @close="msg=''" />

    <a-card title="股票池管理" :bordered="false">
      <template #extra>
        <div style="display:flex;gap:8px">
          <a-input
            :value="codeInput"
            @update:value="v => codeInput = v"
            placeholder="输入股票代码"
            style="width:160px"
            @pressEnter="handleAdd"
          />
          <a-button type="primary" :loading="adding" @click="handleAdd">添加</a-button>
        </div>
      </template>

      <a-table
        :dataSource="stocks"
        :columns="columns"
        :pagination="{ pageSize: 20, size: 'small' }"
        size="small"
        rowKey="code"
      >
        <template #emptyText>
          <div style="text-align:center;padding:32px 0;color:rgba(255,255,255,.25)">股票池为空，输入股票代码添加</div>
        </template>
      </a-table>
    </a-card>
  </div>
</template>
