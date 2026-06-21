import http from './http'
import type { SessionInfo } from '@/types'

export async function createSession(title = '新会话') {
  const { data } = await http.post<{ session: SessionInfo }>('/session', { title })
  return data.session
}

export async function listSessions() {
  const { data } = await http.get<{ sessions: SessionInfo[]; total: number }>('/sessions')
  return data.sessions
}

export async function deleteSession(sessionId: string) {
  const { data } = await http.delete<{ session_id: string }>(`/session/${sessionId}`)
  return data
}
