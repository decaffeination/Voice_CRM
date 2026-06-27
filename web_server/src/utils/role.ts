const ROLE_LABELS: Record<string, string> = {
  Admin: '管理员',
  SalesManager: '销售经理',
  Sales: '销售',
  CustomerService: '客服',
}

/** 与后端 Role.ALL 一致的角色优先级（用于展示主角色） */
export const ROLE_PRIORITY = [
  'Admin',
  'SalesManager',
  'Sales',
  'CustomerService',
] as const

export { ROLE_LABELS }

export function getPrimaryRoleLabel(roles: string[]): string {
  for (const code of ROLE_PRIORITY) {
    if (roles.includes(code)) return ROLE_LABELS[code] || code
  }
  return roles[0] ? ROLE_LABELS[roles[0]] || roles[0] : '用户'
}

export function isAdmin(roles: string[]): boolean {
  return roles.includes('Admin')
}
