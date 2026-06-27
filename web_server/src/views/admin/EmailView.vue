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
              <n-input v-model:value="smtpForm.from" placeholder="noreply@example.com" />
            </n-form-item>
            <n-form-item label="用户名">
              <n-input v-model:value="smtpForm.username" placeholder="可选" />
            </n-form-item>
            <n-form-item label="密码">
              <n-input
                v-model:value="smtpForm.password"
                type="password"
                :placeholder="emailSettings?.smtp_password_set ? '已配置，留空则不修改' : '可选'"
              />
            </n-form-item>
            <n-form-item label="TLS">
              <n-switch v-model:value="smtpForm.use_tls" />
            </n-form-item>
          </n-form>
          <n-space>
            <n-button type="primary" :loading="smtpSaving" @click="saveSmtpSettings">保存 SMTP</n-button>
            <n-button :loading="testing" @click="testSend">测试发送</n-button>
          </n-space>
          <n-alert type="info" style="margin-top: 16px" :show-icon="false">
            SMTP：{{ emailSettings?.smtp_configured ? '已配置' : '未配置' }}；
            密码：{{ emailSettings?.smtp_password_set ? '已设置' : '未设置' }}；
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
  testEmailSend,
  updateEmailSettings,
  updateSmtpSettings,
  type EmailSettings,
} from '@/api/admin'

const message = useMessage()

const emailSettings = ref<EmailSettings | null>(null)
const emailForm = reactive({ enabled: true, dry_run: true })
const smtpForm = reactive({
  host: '',
  port: 587,
  from: '',
  username: '',
  password: '',
  use_tls: true,
})
const emailSaving = ref(false)
const smtpSaving = ref(false)
const testing = ref(false)

async function loadEmailSettings() {
  try {
    emailSettings.value = await fetchEmailSettings()
    emailForm.enabled = emailSettings.value.enabled
    emailForm.dry_run = emailSettings.value.dry_run
    smtpForm.host = emailSettings.value.smtp_host || ''
    smtpForm.port = emailSettings.value.smtp_port || 587
    smtpForm.from = emailSettings.value.from_address || ''
    smtpForm.username = emailSettings.value.smtp_user || ''
    smtpForm.use_tls = emailSettings.value.use_tls
    smtpForm.password = ''
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

async function saveSmtpSettings() {
  smtpSaving.value = true
  try {
    const payload: Parameters<typeof updateSmtpSettings>[0] = {
      smtp_host: smtpForm.host,
      smtp_port: smtpForm.port,
      smtp_user: smtpForm.username,
      from_address: smtpForm.from,
      use_tls: smtpForm.use_tls,
    }
    if (smtpForm.password) {
      payload.smtp_password = smtpForm.password
    }
    emailSettings.value = await updateSmtpSettings(payload)
    smtpForm.password = ''
    message.success('SMTP 配置已保存')
  } catch {
    message.error('保存 SMTP 配置失败')
  } finally {
    smtpSaving.value = false
  }
}

async function testSend() {
  const to = smtpForm.from || emailSettings.value?.from_address
  if (!to || !to.includes('@')) {
    message.warning('请先填写有效的发件/测试邮箱')
    return
  }
  testing.value = true
  try {
    const result = await testEmailSend(to)
    if (result.sent) {
      message.success(result.dry_run ? '测试模式：邮件已模拟发送' : '测试邮件发送成功')
    } else {
      message.error(result.error || '测试发送失败')
    }
  } catch {
    message.error('测试发送失败')
  } finally {
    testing.value = false
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
