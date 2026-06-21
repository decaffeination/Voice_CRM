import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSessionMessages } from '@/api/memory'
import type { ChatMessage, HistoryMessageRecord } from '@/types'

export type SendingStage = 'idle' | 'thinking' | 'asr' | 'tts' | 'upload'

function toChatMessage(msg: HistoryMessageRecord): ChatMessage {
  const channel = msg.channel === 'voice' ? 'voice' : 'text'
  return {
    id: `db-${msg.id}`,
    role: msg.role,
    content: msg.content,
    channel,
    transcript: channel === 'voice' && msg.role === 'user' ? msg.content : undefined,
  }
}

export const useChatStore = defineStore('chat', () => {
  const messagesBySession = ref<Record<string, ChatMessage[]>>({})
  const loadingBySession = ref<Record<string, boolean>>({})
  const sending = ref(false)
  const sendingStage = ref<SendingStage>('idle')
  const loadedSessions = new Set<string>()

  function getMessages(sessionId: string) {
    return messagesBySession.value[sessionId] || []
  }

  function isLoading(sessionId: string) {
    return !!loadingBySession.value[sessionId]
  }

  async function loadSessionMessages(sessionId: string, force = false) {
    if (!force && loadedSessions.has(sessionId)) return
    loadingBySession.value = { ...loadingBySession.value, [sessionId]: true }
    try {
      const data = await getSessionMessages(sessionId)
      messagesBySession.value[sessionId] = data.messages.map(toChatMessage)
      loadedSessions.add(sessionId)
    } finally {
      const next = { ...loadingBySession.value }
      delete next[sessionId]
      loadingBySession.value = next
    }
  }

  function addMessage(sessionId: string, message: ChatMessage) {
    if (!messagesBySession.value[sessionId]) {
      messagesBySession.value[sessionId] = []
    }
    messagesBySession.value[sessionId].push(message)
    loadedSessions.add(sessionId)
  }

  function updateMessage(
    sessionId: string,
    messageId: string,
    patch: Partial<ChatMessage>,
  ) {
    const list = messagesBySession.value[sessionId]
    if (!list) return
    const index = list.findIndex((item) => item.id === messageId)
    if (index < 0) return
    list[index] = { ...list[index], ...patch }
  }

  function clearSession(sessionId: string) {
    messagesBySession.value[sessionId] = []
    loadedSessions.delete(sessionId)
  }

  function clearAll() {
    messagesBySession.value = {}
    loadedSessions.clear()
  }

  function setSendingStage(stage: SendingStage) {
    sendingStage.value = stage
    sending.value = stage !== 'idle'
  }

  function clearSending() {
    setSendingStage('idle')
  }

  return {
    messagesBySession,
    loadingBySession,
    sending,
    sendingStage,
    setSendingStage,
    clearSending,
    getMessages,
    isLoading,
    loadSessionMessages,
    addMessage,
    updateMessage,
    clearSession,
    clearAll,
  }
})
