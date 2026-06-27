import http from './http'

export interface PermissionTreeNode {
  key: string
  label: string
  children?: PermissionTreeNode[]
}

export interface RolePermissions {
  role_code: string
  permission_codes: string[]
}

export async function fetchPermissionTree() {
  const { data } = await http.get<{ items: PermissionTreeNode[] }>('/admin/permissions/tree')
  return data.items
}

export async function fetchRolePermissions(roleCode: string) {
  const { data } = await http.get<RolePermissions>(`/admin/roles/${roleCode}/permissions`)
  return data
}

export async function updateRolePermissions(roleCode: string, permissionCodes: string[]) {
  const { data } = await http.patch<RolePermissions>(`/admin/roles/${roleCode}/permissions`, {
    permission_codes: permissionCodes,
  })
  return data
}
