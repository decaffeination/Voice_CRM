import http from './http'
import type { UserInfo } from '@/types'

export interface RoleInfo {
  code: string
  name: string
  description: string | null
}

export interface CreateUserPayload {
  username: string
  password: string
  display_name?: string
  roles: string[]
}

export interface UpdateUserPayload {
  display_name?: string
  is_active?: boolean
}

export interface UserListResponse {
  items: UserInfo[]
  total: number
  limit: number
  offset: number
}

export interface ListUsersParams {
  keyword?: string
  role?: string
  is_active?: boolean
  limit?: number
  offset?: number
}

export async function listRoles() {
  const { data } = await http.get<RoleInfo[]>('/roles')
  return data
}

export async function listUsers(params?: ListUsersParams) {
  const { data } = await http.get<UserListResponse>('/users', { params })
  return data
}

export async function createUser(payload: CreateUserPayload) {
  const { data } = await http.post<UserInfo>('/users', payload)
  return data
}

export async function updateUser(userId: number, payload: UpdateUserPayload) {
  const { data } = await http.patch<UserInfo>(`/users/${userId}`, payload)
  return data
}

export async function updateUserRoles(userId: number, roles: string[]) {
  const { data } = await http.patch<UserInfo>(`/users/${userId}/roles`, { roles })
  return data
}

export async function resetUserPassword(userId: number, newPassword: string) {
  const { data } = await http.patch<{ message: string }>(`/users/${userId}/password`, {
    new_password: newPassword,
  })
  return data
}

export async function deleteUser(userId: number) {
  const { data } = await http.delete<{ message: string }>(`/users/${userId}`)
  return data
}
