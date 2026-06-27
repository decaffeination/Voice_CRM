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
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password_set: boolean
  from_address: string
  use_tls: boolean
  production_mode: boolean
}

export interface SystemParams {
  system_name: string
  system_logo: string
  default_language: string
  token_limit: number
  session_retention_days: number
}

export interface ModelConfig {
  id: string
  name: string
  provider: string
  model: string
  temperature: number
  max_tokens: number
  enabled: boolean
  is_default: boolean
  base_url?: string
  api_key_configured?: boolean
}

export interface EmailTestResult {
  sent: boolean
  dry_run?: boolean
  message_id?: string | null
  error?: string | null
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

export async function updateSmtpSettings(body: {
  smtp_host?: string
  smtp_port?: number
  smtp_user?: string
  smtp_password?: string
  from_address?: string
  use_tls?: boolean
}) {
  const { data } = await http.patch<EmailSettings>('/admin/settings/email/smtp', body)
  return data
}

export async function testEmailSend(to: string) {
  const { data } = await http.post<EmailTestResult>('/admin/settings/email/test', { to })
  return data
}

export async function fetchSystemParams() {
  const { data } = await http.get<SystemParams>('/admin/settings/system')
  return data
}

export async function updateSystemParams(body: Partial<SystemParams>) {
  const { data } = await http.patch<SystemParams>('/admin/settings/system', body)
  return data
}

export async function fetchModelConfigs() {
  const { data } = await http.get<{ items: ModelConfig[] }>('/admin/settings/models')
  return data.items
}

export async function updateModelConfig(body: {
  provider?: string
  model?: string
  base_url?: string
  temperature?: number
  max_tokens?: number
  enabled?: boolean
}) {
  const { data } = await http.patch<{ items: ModelConfig[] }>('/admin/settings/models', body)
  return data.items
}
