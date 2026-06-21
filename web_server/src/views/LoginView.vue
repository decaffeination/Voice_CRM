<template>
  <div class="login-page">
    <div class="card">
      <h1>Sales Intelligence</h1>
      <p class="sub">智能语音 CRM 助手</p>
      <n-form @submit.prevent="handleLogin">
        <n-form-item label="用户名">
          <n-input v-model:value="username" placeholder="admin" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="password" type="password" placeholder="admin123" />
        </n-form-item>
        <n-button block type="primary" :loading="loading" attr-type="submit">
          登录
        </n-button>
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()
const username = ref('admin')
const password = ref('admin123')
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  try {
    await authStore.login(username.value, password.value)
    router.push('/chat')
  } catch {
    message.error('登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f7f7f8;
}
.card {
  width: 380px;
  background: #fff;
  border: 1px solid #ececec;
  border-radius: 16px;
  padding: 32px;
}
h1 {
  margin: 0;
  font-size: 28px;
}
.sub {
  color: #888;
  margin: 8px 0 24px;
}
</style>
