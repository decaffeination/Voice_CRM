import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchMe, login as loginApi } from '@/api/auth'
import type { UserInfo } from '@/types'

const TOKEN_KEY = 'voice_crm_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<UserInfo | null>(null)

  async function login(username: string, password: string) {
    const data = await loginApi(username, password)
    token.value = data.access_token
    localStorage.setItem(TOKEN_KEY, data.access_token)
    user.value = await fetchMe()
  }

  async function loadUser() {
    if (!token.value) return
    user.value = await fetchMe()
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  return { token, user, login, loadUser, logout }
})
