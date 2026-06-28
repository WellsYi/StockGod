<script setup>
import { ref, onMounted } from 'vue'
import { getMonitorStatus, startMonitor, stopMonitor } from '../api/index.js'

const tasks = ref({})
const loading = ref(false)
const msg = ref('')

async function load() {
  try {
    const data = await getMonitorStatus()
    tasks.value = data.tasks || {}
  } catch {}
}

async function handleStart(name) {
  loading.value = true
  try { msg.value = (await startMonitor(name)).message } catch { msg.value = '操作失败' }
  loading.value = false
  await load()
}

async function handleStop(name) {
  loading.value = true
  try { msg.value = (await stopMonitor(name)).message } catch { msg.value = '操作失败' }
  loading.value = false
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <a-alert v-if="msg" :message="msg" type="info" closable style="margin-bottom:16px" @close="msg=''" />

    <a-card title="后台任务控制">
      <a-list v-if="Object.keys(tasks).length" :dataSource="Object.entries(tasks)">
        <template #renderItem="{ item }">
          <a-list-item>
            <div style="display:flex;justify-content:space-between;align-items:center;width:100%">
              <span><strong>{{ item[0] }}</strong> <a-tag :color="item[1] === 'running' ? 'green' : 'orange'">{{ item[1] }}</a-tag></span>
              <span>
                <a-button v-if="item[1] === 'stopped'" type="primary" size="small" :loading="loading" @click="handleStart(item[0])">启动</a-button>
                <a-button v-if="item[1] === 'running'" danger size="small" :loading="loading" @click="handleStop(item[0])">停止</a-button>
              </span>
            </div>
          </a-list-item>
        </template>
      </a-list>
      <div v-else style="text-align:center;padding:48px 0;color:rgba(255,255,255,.45)">加载中…</div>
    </a-card>
  </div>
</template>
