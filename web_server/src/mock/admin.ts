export interface SystemService {
  name: string
  key: string
  status: string
}

export const MOCK_SERVICES: SystemService[] = [
  { name: 'PostgreSQL', key: 'database', status: '正常' },
  { name: 'Redis', key: 'redis', status: '未启用' },
  { name: 'Vector DB', key: 'vector_db', status: '正常' },
  { name: 'LLM Provider', key: 'llm', status: '正常' },
  { name: 'WebSocket', key: 'websocket', status: '正常' },
  { name: 'SMTP', key: 'smtp', status: '未配置' },
]

export const AUDIT_ACTION_OPTIONS = [
  { label: '全部', value: '' },
  { label: '知识库', value: 'knowledge' },
  { label: 'CRM', value: 'crm' },
  { label: '系统配置', value: 'settings' },
  { label: '用户操作', value: 'auth' },
]
