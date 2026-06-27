export interface UserInfo {
  user_id: number
  username: string
  display_name: string | null
  roles: string[]
  is_active?: boolean
}

export interface SessionInfo {
  session_id: string
  user_id: number
  title: string
  created_at: string | null
  last_active: string | null
}

export interface KnowledgeCitation {
  index: number
  ref: string
  source: string
  doc_id?: string | null
  page?: number | null
  snippet?: string
  score?: number | null
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  channel?: 'text' | 'voice'
  intent?: string | null
  transcript?: string
  citations?: KnowledgeCitation[]
}

export interface HistoryMessageRecord {
  id: number
  role: 'user' | 'assistant'
  content: string
  channel?: 'text' | 'voice'
  created_at: string | null
}

export interface WsMessage {
  type: string
  text?: string
  delta?: string
  data?: string
  session_id?: string
  intent?: string
  message?: string
  title?: string
  index?: number
  sentence?: string
  total_chunks?: number
  with_tts?: boolean
  citations?: KnowledgeCitation[]
}
