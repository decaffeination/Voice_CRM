<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>邮件配置</h2>
        <p class="subtitle">SMTP 发信服务与邮件工具开关</p>
      </div>
      <n-tag :type="emailSettings?.production_mode ? 'success' : 'warning'" size="small" round>
        {{ emailSettings?.production_mode ? '生产模式' : '测试模式' }}
      </n-tag>
    </div>

    <n-grid :cols="2" :x-gap="16" responsive="screen" item-responsive>
      <n-gi span="2 l:1">
        <n-card size="small" title="发信开关" class="content-card">
          <div class="settings-row">
            <div>
              <div class="row-title">启用邮件功能</div>
              <div class="row-desc">开启后 AI 可通过邮件工具发送通知</div>
            </div>
            <n-switch v-model:value="emailForm.enabled" :disabled="emailSaving" />
          </div>
          <div class="settings-row">
            <div>
              <div class="row-title">测试模式（dry_run）</div>
              <div class="row-desc">开启后不实际发信，仅记录日志</div>
            </div>
            <n-switch v-model:value="emailForm.dry_run" :disabled="emailSaving" />
          </div>
          <n-button type="primary" :loading="emailSaving" style="margin-top: 16px" @click="saveEmailSettings">
            保存邮件设置
          </n-button>
        </n-card>
      </n-gi>

      <n-gi span="2 l:1">
        <n-card size="small" title="SMTP 配置" class="content-card">
          <n-form label-placement="left" label-width="100">
            <n-form-item label="SMTP 服务器">
              <n-input v-model:value="smtpForm.host" placeholder="smtp.example.com" />
            </n-form-item>
            <n-form-item label="端口">
              <n-input-number v-model:value="smtpForm.port" :min="1" :max="65535" style="width: 100%" />
            </n-form-item>
            <n-form-item label="发件邮箱">
              <n-input v-model:value="smtpForm.from" :placeholder="emailSettings?.from_address || 'noreply@example.com'" />
            </n-form-item>
            <n-form-item label="用户名">
              <n-input v-model:value="smtpForm.username" placeholder="可选" />
            </n-form-item>
            <n-form-item label="密码">
              <n-input v-model:value="smtpForm.password" type="password" placeholder="可选" />
            </n-form-item>
          </n-form>
          <n-space>
            <n-button type="primary" @click="saveSmtpMock">保存 SMTP（Mock）</n-button>
            <n-button :loading="testing" @click="testSend">测试发送</n-button>
          </n-space>
          <n-alert type="info" style="margin-top: 16px" :show-icon="false">
            当前后端 SMTP 字段：{{ emailSettings?.smtp_configured ? '已配置' : '未配置' }}；
            发件地址：{{ emailSettings?.from_address || '-' }}
          </n-alert>
        </n-card>
      </n-gi>
    </n-grid>
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
  NGi,
  NGrid,
  NInput,
  NInputNumber,
  NSpace,
  NSwitch,
  NTag,
  useMessage,
} from 'naive-ui'
import {
  fetchEmailSettings,
  updateEmailSettings,
  type EmailSettings,
} from '@/api/admin'

const message = useMessage()

const emailSettings = ref<EmailSettings | null>(null)
const emailForm = reactive({ enabled: true, dry_run: true })
const smtpForm = reactive({
  host: 'smtp.localhost',
  port: 587,
  from: '',
  username: '',
  password: '',
})
const emailSaving = ref(false)
const testing = ref(false)

async function loadEmailSettings() {
  try {
    emailSettings.value = await fetchEmailSettings()
    emailForm.enabled = emailSettings.value.enabled
    emailForm.dry_run = emailSettings.value.dry_run
    smtpForm.from = emailSettings.value.from_address || ''
  } catch {
    message.error('加载邮件设置失败')
  }
}

async function saveEmailSettings() {
  emailSaving.value = true
  try {
    emailSettings.value = await updateEmailSettings({
      enabled: emailForm.enabled,
      dry_run: emailForm.dry_run,
    })
    message.success('邮件设置已更新')
  } catch {
    message.error('保存邮件设置失败')
  } finally {
    emailSaving.value = false
  }
}

function saveSmtpMock() {
  message.success('SMTP 配置已保存（Mock，待后端接口对接）')
}

async function testSend() {
  testing.value = true
  await new Promise((r) => setTimeout(r, 800))
  testing.value = false
  if (emailForm.dry_run) {
    message.info('测试模式：邮件已模拟发送（Mock）')
  } else {
    message.success('测试邮件发送成功（Mock）')
  }
}

onMounted(loadEmailSettings)
</script>

<style scoped>
@import './admin-page.css';
.settings-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f0;
  gap: 16px;
}
.row-title {
  font-size: 14px;
  font-weight: 500;
}
.row-desc {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}
</style>
