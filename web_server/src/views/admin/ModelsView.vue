<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>模型配置</h2>
        <p class="subtitle">管理 AI 大模型 Provider 与默认参数</p>
      </div>
      <n-button type="primary" disabled>添加模型（预留）</n-button>
    </div>

    <n-card size="small" class="table-card">
      <n-data-table
        :columns="columns"
        :data="models"
        :bordered="false"
        size="small"
        :pagination="false"
        :scroll-x="900"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { h, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { MOCK_MODELS, type ModelConfig } from '@/mock/admin'

const message = useMessage()
const models = ref([...MOCK_MODELS])

const columns: DataTableColumns<ModelConfig> = [
  { title: '名称', key: 'name', minWidth: 140 },
  { title: 'Provider', key: 'provider', width: 110 },
  { title: '模型', key: 'model', width: 160 },
  { title: 'Temperature', key: 'temperature', width: 110 },
  { title: 'Max Tokens', key: 'max_tokens', width: 110 },
  {
    title: '默认',
    key: 'is_default',
    width: 80,
    render: (row) =>
      row.is_default
        ? h(NTag, { size: 'small', type: 'info', round: true }, () => '默认')
        : '-',
  },
  {
    title: '状态',
    key: 'enabled',
    width: 90,
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: row.enabled ? 'success' : 'default', round: true },
        () => (row.enabled ? '已启用' : '已禁用'),
      ),
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: (row) =>
      h('div', { class: 'action-btns' }, [
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            type: 'primary',
            onClick: () => message.info(`编辑 ${row.name}（Mock）`),
          },
          () => '编辑',
        ),
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            onClick: () => {
              row.enabled = !row.enabled
              message.success(row.enabled ? '已启用' : '已禁用')
            },
          },
          () => (row.enabled ? '禁用' : '启用'),
        ),
      ]),
  },
]
</script>

<style scoped>
@import './admin-page.css';
</style>
