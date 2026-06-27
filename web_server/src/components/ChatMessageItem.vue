<template>
  <div class="message" :class="message.role">
    <div class="avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
    <div class="bubble">
      <div v-if="message.transcript" class="transcript">🎤 {{ message.transcript }}</div>
      <div class="markdown-body" v-html="html" />
      <div v-if="message.citations?.length" class="citations">
        <div class="citations-title">参考来源</div>
        <div
          v-for="item in message.citations"
          :key="item.index"
          class="citation-item"
        >
          <span class="citation-ref">{{ item.ref }}</span>
          <span class="citation-source">{{ item.source }}</span>
          <span v-if="item.page" class="citation-page">第 {{ item.page }} 页</span>
          <div v-if="item.snippet" class="citation-snippet">{{ item.snippet }}</div>
        </div>
      </div>
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
.citations {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e8e8e8;
}
.citations-title {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
  font-weight: 500;
}
.citation-item {
  font-size: 12px;
  color: #555;
  margin-bottom: 8px;
  line-height: 1.5;
}
.citation-ref {
  color: #2080f0;
  font-weight: 600;
  margin-right: 6px;
}
.citation-source {
  font-weight: 500;
}
.citation-page {
  margin-left: 6px;
  color: #888;
}
.citation-snippet {
  margin-top: 4px;
  color: #777;
}
.meta {
  margin-top: 8px;
  font-size: 12px;
  color: #888;
}
</style>
