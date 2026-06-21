<template>
  <div class="layout">
    <AppSidebar
      :sessions="sessionStore.sessions"
      :current-session-id="sessionStore.currentSessionId"
      :user="authStore.user"
      @new-chat="handleNewChat"
      @select="handleSelect"
      @delete="handleDelete"
      @logout="handleLogout"
    />

    <div class="main">
      <header class="topbar">
        <n-tabs v-model:value="activeTab" type="line" @update:value="onTabChange">
          <n-tab name="chat">对话</n-tab>
          <n-tab name="knowledge">知识库</n-tab>
          <n-tab name="dashboard">概览</n-tab>
          <n-tab v-if="isAdmin" name="admin">系统管理</n-tab>
        </n-tabs>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NTabs, NTab, useDialog, useMessage } from 'naive-ui'
import AppSidebar from '@/components/AppSidebar.vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const authStore = useAuthStore()
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const activeTab = ref('chat')

const isAdmin = computed(() => authStore.user?.roles?.includes('Admin') ?? false)

watch(
  () => route.name,
  (name) => {
    if (typeof name === 'string') {
      if (name.startsWith('admin')) activeTab.value = 'admin'
      else activeTab.value = name
    }
  },
  { immediate: true },
)

onMounted(async () => {
  await sessionStore.fetchSessions()
})

function onTabChange(name: string) {
  if (name === 'admin') {
    router.push('/admin/users')
    return
  }
  router.push(`/${name}`)
}

async function handleNewChat() {
  try {
    await sessionStore.newSession()
    router.push('/chat')
    message.success('已创建新会话')
  } catch {
    message.error('创建会话失败')
  }
}

function handleSelect(sessionId: string) {
  sessionStore.selectSession(sessionId)
  router.push('/chat')
}

function handleDelete(sessionId: string) {
  const session = sessionStore.sessions.find((s) => s.session_id === sessionId)
  dialog.warning({
    title: '删除会话',
    content: `确定删除「${session?.title || '该会话'}」？删除后无法恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await sessionStore.removeSession(sessionId)
        chatStore.clearSession(sessionId)
        message.success('会话已删除')
      } catch {
        message.error('删除失败')
      }
    },
  })
}

function handleLogout() {
  authStore.logout()
  sessionStore.clear()
  chatStore.clearAll()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  background: #fff;
}
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  border-bottom: 1px solid #ececec;
  padding: 8px 24px 0;
}
.content {
  flex: 1;
  overflow: auto;
  background: #f7f7f8;
}
</style>
