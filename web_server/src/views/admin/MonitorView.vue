<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>系统监控</h2>
        <p class="subtitle">核心服务运行状态与健康检查</p>
      </div>
      <n-button :loading="loading" @click="loadStatus">刷新状态</n-button>
    </div>

    <n-grid :cols="3" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
      <n-gi v-for="svc in services" :key="svc.key" span="3 m:1">
        <n-card size="small" class="service-card">
          <div class="service-head">
            <span class="service-name">{{ svc.name }}</span>
            <n-tag :type="statusType(svc.status)" size="small" round>{{ svc.status }}</n-tag>
          </div>
          <div class="service-key">{{ svc.key }}</div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-card size="small" title="运行概览" class="content-card" style="margin-top: 16px">
      <n-descriptions :column="3" label-placement="left" size="small">
        <n-descriptions-item label="整体状态">
          <n-tag :type="overallType" size="small" round>{{ overallStatus }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="检测时间">{{ checkedAt }}</n-descriptions-item>
        <n-descriptions-item label="数据来源">
          {{ fromApi ? '实时 API' : 'Mock 数据' }}
        </n-descriptions-item>
      </n-descriptions>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NGi,
  NGrid,
  NTag,
} from 'naive-ui'
import { fetchDashboardOverview } from '@/api/dashboard'
import { MOCK_SERVICES, type SystemService } from '@/mock/admin'

const loading = ref(false)
const services = ref<SystemService[]>([...MOCK_SERVICES])
const fromApi = ref(false)
const checkedAt = ref('-')
const overallStatus = ref('正常')

const overallType = computed(() => {
  if (overallStatus.value === '正常') return 'success'
  if (overallStatus.value === '降级') return 'warning'
  return 'error'
})

function statusType(status: string) {
  if (status === '正常') return 'success'
  if (status === '未启用' || status === '未配置') return 'default'
  if (status === '降级') return 'warning'
  return 'error'
}

async function loadStatus() {
  loading.value = true
  checkedAt.value = new Date().toLocaleString('zh-CN')
  try {
    const data = await fetchDashboardOverview()
    fromApi.value = true
    services.value = data.system_status.map((s) => ({
      name: s.name === 'PostgreSQL' ? '数据库 (SQLite)' : s.name,
      key: s.key,
      status: s.status,
    }))
    overallStatus.value = data.overview.system_status
  } catch {
    fromApi.value = false
    services.value = [...MOCK_SERVICES]
    overallStatus.value = '正常'
  } finally {
    loading.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
@import './admin-page.css';
.service-card {
  border-radius: 14px;
}
.service-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.service-name {
  font-size: 15px;
  font-weight: 600;
}
.service-key {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}
</style>
