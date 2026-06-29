<script setup>
import { ref, onMounted } from 'vue'
import { listBili } from '../api/index.js'

const rows = ref([])
const author = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const params = { limit: 50 }
    if (author.value) params.author = author.value
    rows.value = await listBili(params)
  } catch {} finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <a-input :value="author" @update:value="v => author = v" placeholder="UP主" style="width:160px" allow-clear @pressEnter="load" />
      <a-button type="primary" :loading="loading" @click="load">查询</a-button>
    </div>

    <a-row :gutter="16">
      <a-col :span="12" v-for="r in rows" :key="r.id" style="margin-bottom:16px">
        <a-card>
          <a-card-meta>
            <template #title>
              <span>{{ r.author }}</span>
              <span style="font-size:12px;color:rgba(255,255,255,.45);margin-left:12px">{{ r.pushed_at?.replace('T', ' ') }}</span>
            </template>
            <template #description>
              <div style="margin:8px 0;line-height:1.6;font-size:13px">{{ r.content?.slice(0, 200) }}</div>
              <a-tag v-if="r.llm_summary" color="blue" style="white-space:normal;height:auto;padding:4px 8px;line-height:1.5">{{ r.llm_summary }}</a-tag>
              <div v-if="r.link_url" style="margin-top:8px">
                <a :href="r.link_url" target="_blank">查看原文 →</a>
              </div>
            </template>
          </a-card-meta>
        </a-card>
      </a-col>
    </a-row>

    <div v-if="!rows.length && !loading" style="text-align:center;padding:48px 0;color:rgba(255,255,255,.45)">暂无动态</div>
  </div>
</template>

<style scoped>
:deep(.ant-card-meta-title) {
  color: var(--text-primary) !important;
}
:deep(.ant-card-meta-description) {
  color: var(--text-secondary) !important;
}
</style>
