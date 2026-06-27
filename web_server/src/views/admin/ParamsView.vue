<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>系统参数</h2>
        <p class="subtitle">平台全局配置与运行参数</p>
      </div>
      <n-button type="primary" :loading="saving" @click="handleSave">保存配置</n-button>
    </div>

    <n-card size="small" class="content-card" style="max-width: 720px">
      <n-spin :show="loading">
        <n-form label-placement="left" label-width="140">
          <n-form-item label="系统名称">
            <n-input v-model:value="form.system_name" placeholder="Voice-CRM" />
          </n-form-item>
          <n-form-item label="系统 Logo">
            <n-input v-model:value="form.system_logo" placeholder="Logo URL" />
          </n-form-item>
          <n-form-item label="默认语言">
            <n-select v-model:value="form.default_language" :options="langOptions" />
          </n-form-item>
          <n-form-item label="Token 限制">
            <n-input-number v-model:value="form.token_limit" :min="1024" :max="128000" style="width: 100%" />
          </n-form-item>
          <n-form-item label="会话保留天数">
            <n-input-number v-model:value="form.session_retention_days" :min="1" :max="365" style="width: 100%" />
          </n-form-item>
        </n-form>
      </n-spin>
      <n-alert type="info" style="margin-top: 16px" :show-icon="false">
        配置保存在服务端运行时内存中，重启后恢复为 config.yaml 默认值。
      </n-alert>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  NSpin,
  useMessage,
} from 'naive-ui'
import { fetchSystemParams, updateSystemParams } from '@/api/admin'

const message = useMessage()

const loading = ref(false)
const saving = ref(false)
const form = reactive({
  system_name: '',
  system_logo: '',
  default_language: 'zh-CN',
  token_limit: 8192,
  session_retention_days: 90,
})

const langOptions = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' },
  { label: '日本語', value: 'ja-JP' },
]

async function loadParams() {
  loading.value = true
  try {
    const data = await fetchSystemParams()
    Object.assign(form, data)
  } catch {
    message.error('加载系统参数失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const data = await updateSystemParams({ ...form })
    Object.assign(form, data)
    message.success('系统参数已保存')
  } catch {
    message.error('保存系统参数失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadParams)
</script>

<style scoped>
@import './admin-page.css';
</style>
