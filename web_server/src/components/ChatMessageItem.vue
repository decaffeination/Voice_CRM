<template>
  <div class="message" :class="message.role">
    <div class="avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
    <div class="bubble">
      <div v-if="message.transcript" class="transcript">🎤 {{ message.transcript }}</div>
      <div class="markdown-body" v-html="html" />
      <div v-if="message.intent" class="meta">意图: {{ message.intent }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import type { ChatMessage } from '@/types'

const props = defineProps<{ message: ChatMessage }>()
const html = computed(() => renderMarkdown(props.message.content))
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.message.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #ececec;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}
.bubble {
  max-width: 75%;
  background: #fff;
  border: 1px solid #ececec;
  border-radius: 14px;
  padding: 12px 14px;
}
.message.user .bubble {
  background: #111;
  color: #fff;
  border-color: #111;
}
.message.user .bubble :deep(code) {
  background: rgba(255, 255, 255, 0.15);
}
.transcript {
  font-size: 12px;
  opacity: 0.75;
  margin-bottom: 6px;
}
.meta {
  margin-top: 8px;
  font-size: 12px;
  color: #888;
}
</style>
