<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>模型配置</h2>
        <p class="subtitle">管理 AI 大模型 Provider 与默认参数</p>
      </div>
    </div>

    <n-card size="small" class="table-card">
      <n-spin :show="loading">
        <n-data-table
          :columns="columns"
          :data="models"
          :bordered="false"
          size="small"
          :pagination="false"
          :scroll-x="900"
        />
      </n-spin>
    </n-card>

    <n-modal v-model:show="showEdit" preset="card" title="编辑模型" style="width: 480px">
      <n-form v-if="editing" label-placement="left" label-width="100">
        <n-form-item label="Provider">
          <n-input :value="editing.provider" disabled />
        </n-form-item>
        <n-form-item label="模型">
          <n-input v-model:value="editForm.model" />
        </n-form-item>
        <n-form-item label="Base URL">
          <n-input v-model:value="editForm.base_url" />
        </n-form-item>
        <n-form-item label="Temperature">
          <n-input-number v-model:value="editForm.temperature" :min="0" :max="2" :step="0.1" style="width: 100%" />
        </n-form-item>
        <n-form-item label="Max Tokens">
          <n-input-number v-model:value="editForm.max_tokens" :min="256" :max="128000" style="width: 100%" />
        </n-form-item>
        <n-alert type="info" :show-icon="false">
          API Key 通过环境变量 LLM_API_KEY 注入，不在此页面展示。
        </n-alert>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showEdit = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSaveEdit">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSpace,
  NSpin,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { fetchModelConfigs, updateModelConfig, type ModelConfig } from '@/api/admin'

const message = useMessage()
const models = ref<ModelConfig[]>([])
const loading = ref(false)
const saving = ref(false)
const showEdit = ref(false)
const editing = ref<ModelConfig | null>(null)
const editForm = reactive({
  model: '',
  base_url: '',
  temperature: 0.7,
  max_tokens: 4096,
})

const columns: DataTableColumns<ModelConfig> = [
  { title: '名称', key: 'name', minWidth: 140 },
  { title: 'Provider', key: 'provider', width: 110 },
  { title: '模型', key: 'model', width: 160 },
  { title: 'Temperature', key: 'temperature', width: 110 },
  { title: 'Max Tokens', key: 'max_tokens', width: 110 },
  {
    title: 'API Key',
    key: 'api_key_configured',
    width: 90,
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: row.api_key_configured ? 'success' : 'warning', round: true },
        () => (row.api_key_configured ? '已配置' : '未配置'),
      ),
  },
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
            onClick: () => openEdit(row),
          },
          () => '编辑',
        ),
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            onClick: () => toggleEnabled(row),
          },
          () => (row.enabled ? '禁用' : '启用'),
        ),
      ]),
  },
]

async function loadModels() {
  loading.value = true
  try {
    models.value = await fetchModelConfigs()
  } catch {
    message.error('加载模型配置失败')
  } finally {
    loading.value = false
  }
}

function openEdit(row: ModelConfig) {
  editing.value = row
  editForm.model = row.model
  editForm.base_url = row.base_url || ''
  editForm.temperature = row.temperature
  editForm.max_tokens = row.max_tokens
  showEdit.value = true
}

async function handleSaveEdit() {
  if (!editing.value) return
  saving.value = true
  try {
    models.value = await updateModelConfig({
      model: editForm.model,
      base_url: editForm.base_url,
      temperature: editForm.temperature,
      max_tokens: editForm.max_tokens,
    })
    message.success('模型配置已更新')
    showEdit.value = false
  } catch {
    message.error('保存模型配置失败')
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(row: ModelConfig) {
  try {
    models.value = await updateModelConfig({ enabled: !row.enabled })
    message.success(row.enabled ? '已禁用' : '已启用')
  } catch {
    message.error('更新状态失败')
  }
}

onMounted(loadModels)
</script>

<style scoped>
@import './admin-page.css';
</style>
