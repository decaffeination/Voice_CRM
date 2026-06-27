/** 与后端 rbac_catalog.py 对齐；权限持久化由 /api/admin/roles/{code}/permissions 管理。 */

export interface PermissionNode {
  key: string
  label: string
  children?: PermissionNode[]
}

export const ROLE_CODES = {
  Admin: 'Admin',
  SalesManager: 'SalesManager',
  Sales: 'Sales',
  CustomerService: 'CustomerService',
} as const

export type RoleCode = (typeof ROLE_CODES)[keyof typeof ROLE_CODES]

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

const ALL_PERMISSION_KEYS = PERMISSION_TREE.flatMap((m) => [
  m.key,
  ...(m.children?.map((c) => c.key) ?? []),
])

/** 各角色默认权限预览（与后端 require_* 能力大致对应） */
export const ROLE_PERMISSIONS: Record<RoleCode, string[]> = {
  [ROLE_CODES.Admin]: ALL_PERMISSION_KEYS,
  [ROLE_CODES.SalesManager]: [
    'ai.chat',
    'ai.voice',
    'ai.history',
    'knowledge.read',
    'knowledge.upload',
    'knowledge.search',
    'crm.read',
    'crm.write',
    'crm.followup',
  ],
  [ROLE_CODES.Sales]: [
    'ai.chat',
    'ai.voice',
    'ai.history',
    'knowledge.read',
    'crm.read',
    'crm.write',
    'crm.followup',
  ],
  [ROLE_CODES.CustomerService]: [
    'ai.chat',
    'ai.voice',
    'knowledge.read',
    'knowledge.search',
    'crm.read',
    'crm.followup',
  ],
}
