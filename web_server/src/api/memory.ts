import http from './http'
import type { HistoryMessageRecord } from '@/types'

export interface SessionMessagesResponse {
  session_id: string
  messages: HistoryMessageRecord[]
  total: number
  summary: string | null
}

export async function getSessionMessages(sessionId: string) {
  const { data } = await http.get<SessionMessagesResponse>(
    `/session/${sessionId}/messages`,
  )
  return data
}
