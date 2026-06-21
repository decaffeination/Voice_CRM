<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>系统参数</h2>
        <p class="subtitle">平台全局配置与运行参数</p>
      </div>
      <n-button type="primary" @click="handleSave">保存配置</n-button>
    </div>

    <n-card size="small" class="content-card" style="max-width: 720px">
      <n-form label-placement="left" label-width="140">
        <n-form-item label="系统名称">
          <n-input v-model:value="form.system_name" placeholder="Sales Intelligence" />
        </n-form-item>
        <n-form-item label="系统 Logo">
          <n-input v-model:value="form.system_logo" placeholder="Logo URL 或上传路径（Mock）" />
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
      <n-alert type="info" :show-icon="false">
        当前为 Mock 配置页，保存后仅在本地会话生效，待后端系统参数 API 对接后持久化。
      </n-alert>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  useMessage,
} from 'naive-ui'
import { MOCK_SYSTEM_PARAMS } from '@/mock/admin'

const message = useMessage()

const form = reactive({ ...MOCK_SYSTEM_PARAMS })

const langOptions = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' },
  { label: '日本語', value: 'ja-JP' },
]

function handleSave() {
  message.success('系统参数已保存（Mock）')
}
</script>

<style scoped>
@import './admin-page.css';
</style>
