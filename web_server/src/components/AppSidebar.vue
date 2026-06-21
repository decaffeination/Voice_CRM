<template>
  <aside class="sidebar">
    <div class="brand">Sales Intelligence</div>

    <n-button block type="primary" class="new-btn" @click="emit('new-chat')">
      <template #icon><n-icon><AddOutline /></n-icon></template>
      新建会话
    </n-button>

    <n-input
      v-model:value="searchKeyword"
      size="small"
      placeholder="搜索会话..."
      clearable
      class="search-input"
    >
      <template #prefix>
        <n-icon><SearchOutline /></n-icon>
      </template>
    </n-input>

    <div class="section-title">会话 <span class="count">{{ filteredSessions.length }}</span></div>
    <n-scrollbar style="flex: 1">
      <div
        v-for="item in filteredSessions"
        :key="item.session_id"
        class="session-item"
        :class="{ active: item.session_id === currentSessionId }"
        @click="emit('select', item.session_id)"
      >
        <div class="session-main">
          <div class="title" :title="item.title">{{ item.title }}</div>
          <div class="time">{{ formatTime(item.last_active) }}</div>
        </div>
        <n-button
          class="delete-btn"
          text
          size="tiny"
          @click.stop="emit('delete', item.session_id)"
        >
          <template #icon>
            <n-icon size="16"><TrashOutline /></n-icon>
          </template>
        </n-button>
      </div>
      <n-empty v-if="!filteredSessions.length" description="暂无会话" size="small" />
    </n-scrollbar>

    <div class="user-box">
      <div class="user-info">
        <n-icon size="18" class="user-icon"><PersonOutline /></n-icon>
        <span class="role-label">{{ roleLabel }}</span>
      </div>
      <n-button text size="small" @click="emit('logout')">退出</n-button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NIcon, NInput, NScrollbar, NEmpty } from 'naive-ui'
import { AddOutline, PersonOutline, SearchOutline, TrashOutline } from '@vicons/ionicons5'
import type { SessionInfo, UserInfo } from '@/types'
import { getPrimaryRoleLabel } from '@/utils/role'

const props = defineProps<{
  sessions: SessionInfo[]
  currentSessionId: string | null
  user: UserInfo | null
}>()

const emit = defineEmits<{
  'new-chat': []
  select: [sessionId: string]
  delete: [sessionId: string]
  logout: []
}>()

const searchKeyword = ref('')

const roleLabel = computed(() => getPrimaryRoleLabel(props.user?.roles ?? []))

const filteredSessions = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) return props.sessions
  return props.sessions.filter((s) => s.title.toLowerCase().includes(kw))
})

function formatTime(value: string | null) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.sidebar {
  width: 260px;
  border-right: 1px solid #ececec;
  background: #fafafa;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}
.brand {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 22px;
  font-weight: 600;
  color: #111;
  padding: 6px 4px 2px;
  letter-spacing: 0.02em;
}
.new-btn {
  background: #111 !important;
  border: none !important;
}
.search-input {
  margin-top: 2px;
}
.section-title {
  font-size: 11px;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 4px 4px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}
.count {
  color: #bbb;
  font-weight: 400;
}
.session-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 9px 8px 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  border: 1px solid transparent;
  border-left: 3px solid transparent;
  transition: background 0.12s, border-color 0.12s;
}
.session-item:hover {
  background: #fff;
  border-color: #ececec;
  border-left-color: #ececec;
}
.session-item.active {
  background: #fff;
  border-color: #e0e0e0;
  border-left-color: #111;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.session-main {
  flex: 1;
  min-width: 0;
}
.delete-btn {
  opacity: 0;
  flex-shrink: 0;
  color: #999;
}
.session-item:hover .delete-btn {
  opacity: 1;
}
.delete-btn:hover {
  color: #d03050 !important;
}
.title {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #222;
}
.time {
  font-size: 11px;
  color: #aaa;
  margin-top: 3px;
}
.user-box {
  border-top: 1px solid #ececec;
  padding-top: 12px;
  margin-top: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
}
.user-icon {
  color: #666;
}
.role-label {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}
</style>
