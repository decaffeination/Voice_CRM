export interface AdminUser {
  user_id: number
  username: string
  display_name: string
  roles: string[]
  status: 'active' | 'disabled'
  last_login_at: string | null
  created_at: string
}

export interface AdminRole {
  code: string
  name: string
  description: string
  user_count: number
}

export interface PermissionNode {
  key: string
  label: string
  children?: PermissionNode[]
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
}

export interface SystemService {
  name: string
  key: string
  status: string
}

export interface SystemParams {
  system_name: string
  system_logo: string
  default_language: string
  token_limit: number
  session_retention_days: number
}

export const MOCK_USERS: AdminUser[] = [
  {
    user_id: 1,
    username: 'admin',
    display_name: '管理员',
    roles: ['超级管理员'],
    status: 'active',
    last_login_at: '2026-06-18 09:30:00',
    created_at: '2026-01-10 10:00:00',
  },
  {
    user_id: 2,
    username: 'sales01',
    display_name: '张销售',
    roles: ['销售'],
    status: 'active',
    last_login_at: '2026-06-18 08:15:00',
    created_at: '2026-03-02 14:20:00',
  },
  {
    user_id: 3,
    username: 'sales02',
    display_name: '李销售',
    roles: ['销售'],
    status: 'active',
    last_login_at: '2026-06-17 17:40:00',
    created_at: '2026-03-15 09:00:00',
  },
  {
    user_id: 4,
    username: 'cs01',
    display_name: '王客服',
    roles: ['客服'],
    status: 'active',
    last_login_at: '2026-06-18 07:50:00',
    created_at: '2026-04-01 11:30:00',
  },
  {
    user_id: 5,
    username: 'staff01',
    display_name: '赵员工',
    roles: ['普通员工'],
    status: 'disabled',
    last_login_at: '2026-05-20 16:00:00',
    created_at: '2026-05-01 08:00:00',
  },
]

export const MOCK_ROLES: AdminRole[] = [
  { code: 'super_admin', name: '超级管理员', description: '拥有全部系统权限', user_count: 1 },
  { code: 'admin', name: '管理员', description: '系统管理与配置', user_count: 0 },
  { code: 'sales', name: '销售', description: 'CRM 与客户管理', user_count: 2 },
  { code: 'cs', name: '客服', description: '客户服务与咨询', user_count: 1 },
  { code: 'staff', name: '普通员工', description: '基础 AI 助手使用', user_count: 1 },
]

export const PERMISSION_TREE: PermissionNode[] = [
  {
    key: 'ai',
    label: 'AI 助手',
    children: [
      { key: 'ai.chat', label: '对话访问' },
      { key: 'ai.voice', label: '语音交互' },
      { key: 'ai.history', label: '历史记录' },
    ],
  },
  {
    key: 'knowledge',
    label: '知识库',
    children: [
      { key: 'knowledge.read', label: '文档查看' },
      { key: 'knowledge.upload', label: '文档上传' },
      { key: 'knowledge.delete', label: '文档删除' },
      { key: 'knowledge.search', label: '检索测试' },
    ],
  },
  {
    key: 'crm',
    label: 'CRM',
    children: [
      { key: 'crm.read', label: '客户查看' },
      { key: 'crm.write', label: '客户编辑' },
      { key: 'crm.followup', label: '跟进记录' },
    ],
  },
  {
    key: 'admin',
    label: '系统管理',
    children: [
      { key: 'admin.users', label: '用户管理' },
      { key: 'admin.roles', label: '角色权限' },
      { key: 'admin.audit', label: '操作审计' },
      { key: 'admin.settings', label: '系统配置' },
    ],
  },
]

export const ROLE_PERMISSIONS: Record<string, string[]> = {
  super_admin: PERMISSION_TREE.flatMap((m) => [
    m.key,
    ...(m.children?.map((c) => c.key) ?? []),
  ]),
  admin: [
    'ai.chat', 'ai.voice', 'ai.history',
    'knowledge.read', 'knowledge.upload', 'knowledge.search',
    'crm.read', 'crm.write', 'crm.followup',
    'admin.users', 'admin.audit', 'admin.settings',
  ],
  sales: ['ai.chat', 'ai.voice', 'ai.history', 'knowledge.read', 'crm.read', 'crm.write', 'crm.followup'],
  cs: ['ai.chat', 'ai.voice', 'knowledge.read', 'knowledge.search', 'crm.read', 'crm.followup'],
  staff: ['ai.chat', 'ai.history', 'knowledge.read'],
}

export const MOCK_MODELS: ModelConfig[] = [
  {
    id: '1',
    name: '默认对话模型',
    provider: 'DeepSeek',
    model: 'deepseek-chat',
    temperature: 0.7,
    max_tokens: 4096,
    enabled: true,
    is_default: true,
  },
  {
    id: '2',
    name: 'OpenAI GPT-4o',
    provider: 'OpenAI',
    model: 'gpt-4o',
    temperature: 0.5,
    max_tokens: 8192,
    enabled: false,
    is_default: false,
  },
  {
    id: '3',
    name: 'Anthropic Claude',
    provider: 'Anthropic',
    model: 'claude-3-5-sonnet',
    temperature: 0.6,
    max_tokens: 8192,
    enabled: false,
    is_default: false,
  },
  {
    id: '4',
    name: '通义千问',
    provider: 'Qwen',
    model: 'qwen-max',
    temperature: 0.7,
    max_tokens: 6000,
    enabled: false,
    is_default: false,
  },
]

export const MOCK_SERVICES: SystemService[] = [
  { name: 'PostgreSQL', key: 'database', status: '正常' },
  { name: 'Redis', key: 'redis', status: '未启用' },
  { name: 'Vector DB', key: 'vector_db', status: '正常' },
  { name: 'LLM Provider', key: 'llm', status: '正常' },
  { name: 'WebSocket', key: 'websocket', status: '正常' },
  { name: 'SMTP', key: 'smtp', status: '未配置' },
]

export const MOCK_SYSTEM_PARAMS: SystemParams = {
  system_name: 'Sales Intelligence',
  system_logo: '',
  default_language: 'zh-CN',
  token_limit: 8192,
  session_retention_days: 90,
}

export const AUDIT_ACTION_OPTIONS = [
  { label: '全部', value: '' },
  { label: '知识库', value: 'knowledge' },
  { label: 'CRM', value: 'crm' },
  { label: '系统配置', value: 'settings' },
  { label: '用户操作', value: 'auth' },
]
