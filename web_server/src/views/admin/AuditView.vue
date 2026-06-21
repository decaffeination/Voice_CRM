<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>操作审计</h2>
        <p class="subtitle">记录系统关键操作，支持追溯与合规审计</p>
      </div>
    </div>

    <n-card size="small" class="table-card">
      <div class="filters">
        <n-input
          v-model:value="filters.userId"
          size="small"
          placeholder="用户 ID"
          style="width: 120px"
          clearable
        />
        <n-select
          v-model:value="filters.actionType"
          size="small"
          :options="actionOptions"
          style="width: 140px"
        />
        <n-date-picker
          v-model:value="filters.dateRange"
          type="daterange"
          size="small"
          clearable
          style="width: 260px"
        />
        <n-input
          v-model:value="filters.action"
          size="small"
          placeholder="操作关键词"
          style="width: 180px"
          clearable
          @keyup.enter="handleSearch"
        />
        <n-button size="small" type="primary" @click="handleSearch">查询</n-button>
        <n-button size="small" @click="resetFilters">重置</n-button>
      </div>

      <n-data-table
        :columns="auditColumns"
        :data="filteredItems"
        :loading="auditLoading"
        :pagination="auditPagination"
        remote
        size="small"
        :bordered="false"
        :scroll-x="1000"
        style="margin-top: 16px"
        @update:page="onAuditPageChange"
        @update:page-size="onPageSizeChange"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NDatePicker,
  NInput,
  NSelect,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { fetchAuditLogs, type AuditLogItem } from '@/api/admin'
import { AUDIT_ACTION_OPTIONS } from '@/mock/admin'

const message = useMessage()

const auditItems = ref<AuditLogItem[]>([])
const auditLoading = ref(false)
const actionOptions = AUDIT_ACTION_OPTIONS

const filters = reactive({
  userId: '',
  actionType: '',
  action: '',
  dateRange: null as [number, number] | null,
})

const auditPagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
})

const filteredItems = computed(() => {
  let items = auditItems.value
  if (filters.userId) {
    const uid = Number(filters.userId)
    if (!Number.isNaN(uid)) items = items.filter((i) => i.user_id === uid)
  }
  if (filters.actionType) {
    items = items.filter((i) => i.action.includes(filters.actionType))
  }
  if (filters.dateRange) {
    const [start, end] = filters.dateRange
    items = items.filter((i) => {
      if (!i.created_at) return false
      const t = new Date(i.created_at).getTime()
      return t >= start && t <= end + 86400000
    })
  }
  return items
})

const auditColumns: DataTableColumns<AuditLogItem> = [
  {
    title: '时间',
    key: 'created_at',
    width: 170,
    render: (row) => row.created_at?.replace('T', ' ').slice(0, 19) ?? '-',
  },
  { title: '操作', key: 'action', width: 160 },
  { title: '资源', key: 'resource', width: 180, ellipsis: { tooltip: true } },
  {
    title: '详情',
    key: 'detail',
    ellipsis: { tooltip: true },
    render: (row) => h('span', row.detail || '-'),
  },
  { title: '用户 ID', key: 'user_id', width: 80 },
]

async function loadAuditLogs() {
  auditLoading.value = true
  try {
    const offset = (auditPagination.page - 1) * auditPagination.pageSize
    const result = await fetchAuditLogs({
      action: filters.action || undefined,
      limit: auditPagination.pageSize,
      offset,
    })
    auditItems.value = result.items
    auditPagination.itemCount = result.total
  } catch {
    message.error('加载审计日志失败')
  } finally {
    auditLoading.value = false
  }
}

function handleSearch() {
  auditPagination.page = 1
  loadAuditLogs()
}

function resetFilters() {
  filters.userId = ''
  filters.actionType = ''
  filters.action = ''
  filters.dateRange = null
  auditPagination.page = 1
  loadAuditLogs()
}

function onAuditPageChange(page: number) {
  auditPagination.page = page
  loadAuditLogs()
}

function onPageSizeChange(pageSize: number) {
  auditPagination.pageSize = pageSize
  auditPagination.page = 1
  loadAuditLogs()
}

onMounted(loadAuditLogs)
</script>

<style scoped>
@import './admin-page.css';
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
</style>
