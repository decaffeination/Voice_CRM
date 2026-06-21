import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createSession, deleteSession as deleteSessionApi, listSessions } from '@/api/session'
import type { SessionInfo } from '@/types'

const CURRENT_SESSION_KEY = 'voice_crm_current_session'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<SessionInfo[]>([])
  const currentSessionId = ref<string | null>(localStorage.getItem(CURRENT_SESSION_KEY))
  const loading = ref(false)

  function persistCurrentSession(sessionId: string | null) {
    if (sessionId) {
      localStorage.setItem(CURRENT_SESSION_KEY, sessionId)
    } else {
      localStorage.removeItem(CURRENT_SESSION_KEY)
    }
  }

  async function fetchSessions() {
    loading.value = true
    try {
      sessions.value = await listSessions()
      const saved = currentSessionId.value
      if (saved && sessions.value.some((s) => s.session_id === saved)) {
        return
      }
      if (sessions.value.length) {
        selectSession(sessions.value[0].session_id)
      } else {
        currentSessionId.value = null
        persistCurrentSession(null)
      }
    } finally {
      loading.value = false
    }
  }

  async function newSession(title = '新会话') {
    const session = await createSession(title)
    sessions.value.unshift(session)
    selectSession(session.session_id)
    return session
  }

  function selectSession(sessionId: string) {
    currentSessionId.value = sessionId
    persistCurrentSession(sessionId)
  }

  function updateSessionTitle(sessionId: string, title: string) {
    const index = sessions.value.findIndex((s) => s.session_id === sessionId)
    if (index < 0) return
    sessions.value[index] = { ...sessions.value[index], title }
  }

  async function removeSession(sessionId: string) {
    await deleteSessionApi(sessionId)
    sessions.value = sessions.value.filter((s) => s.session_id !== sessionId)
    if (currentSessionId.value === sessionId) {
      const next = sessions.value[0]?.session_id ?? null
      currentSessionId.value = next
      persistCurrentSession(next)
    }
  }

  function clear() {
    sessions.value = []
    currentSessionId.value = null
    persistCurrentSession(null)
  }

  return {
    sessions,
    currentSessionId,
    loading,
    fetchSessions,
    newSession,
    selectSession,
    updateSessionTitle,
    removeSession,
    clear,
  }
})
