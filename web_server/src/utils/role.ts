const ROLE_LABELS: Record<string, string> = {
  Admin: '管理员',
  SalesManager: '销售经理',
  Sales: '销售',
  CustomerService: '客服',
}

export function getPrimaryRoleLabel(roles: string[]): string {
  const priority = ['Admin', 'SalesManager', 'Sales', 'CustomerService']
  for (const code of priority) {
    if (roles.includes(code)) return ROLE_LABELS[code] || code
  }
  return roles[0] ? ROLE_LABELS[roles[0]] || roles[0] : '用户'
}

export function isAdmin(roles: string[]): boolean {
  return roles.includes('Admin')
}
