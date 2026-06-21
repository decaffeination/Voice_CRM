import http from './http'
import type { UserInfo } from '@/types'

export async function login(username: string, password: string) {
  const { data } = await http.post<{ access_token: string }>('/auth/login', {
    username,
    password,
  })
  return data
}

export async function fetchMe() {
  const { data } = await http.get<UserInfo>('/me')
  return data
}
