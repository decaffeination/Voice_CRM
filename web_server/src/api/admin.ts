import http from './http'

export interface AuditLogItem {
  id: number
  action: string
  resource: string
  detail: string
  user_id: number | null
  session_id: string | null
  request_id: string | null
  created_at: string | null
}

export interface AuditLogListResponse {
  items: AuditLogItem[]
  total: number
  limit: number
  offset: number
}

export interface EmailSettings {
  enabled: boolean
  dry_run: boolean
  smtp_configured: boolean
  from_address: string
  production_mode: boolean
}

export async function fetchAuditLogs(params?: {
  user_id?: number
  action?: string
  limit?: number
  offset?: number
}) {
  const { data } = await http.get<AuditLogListResponse>('/admin/audit', { params })
  return data
}

export async function fetchEmailSettings() {
  const { data } = await http.get<EmailSettings>('/admin/settings/email')
  return data
}

export async function updateEmailSettings(body: {
  enabled?: boolean
  dry_run?: boolean
}) {
  const { data } = await http.patch<EmailSettings>('/admin/settings/email', body)
  return data
}
