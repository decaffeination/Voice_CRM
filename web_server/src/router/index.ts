import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        { path: '', redirect: '/chat' },
        { path: 'chat', name: 'chat', component: () => import('@/views/ChatView.vue') },
        {
          path: 'knowledge',
          name: 'knowledge',
          component: () => import('@/views/KnowledgeView.vue'),
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'admin',
          component: () => import('@/views/admin/AdminLayout.vue'),
          meta: { requiresAdmin: true },
          children: [
            { path: '', redirect: '/admin/users' },
            {
              path: 'users',
              name: 'admin-users',
              component: () => import('@/views/admin/UsersView.vue'),
            },
            {
              path: 'roles',
              name: 'admin-roles',
              component: () => import('@/views/admin/RolesView.vue'),
            },
            {
              path: 'models',
              name: 'admin-models',
              component: () => import('@/views/admin/ModelsView.vue'),
            },
            {
              path: 'monitor',
              name: 'admin-monitor',
              component: () => import('@/views/admin/MonitorView.vue'),
            },
            {
              path: 'email',
              name: 'admin-email',
              component: () => import('@/views/admin/EmailView.vue'),
            },
            {
              path: 'audit',
              name: 'admin-audit',
              component: () => import('@/views/admin/AuditView.vue'),
            },
            {
              path: 'params',
              name: 'admin-params',
              component: () => import('@/views/admin/ParamsView.vue'),
            },
            { path: 'settings', redirect: '/admin/email' },
          ],
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.token) return '/login'
  if (!auth.user) {
    try {
      await auth.loadUser()
    } catch {
      auth.logout()
      return '/login'
    }
  }
  if (to.matched.some((r) => r.meta.requiresAdmin)) {
    if (!auth.user?.roles?.includes('Admin')) return '/dashboard'
  }
  return true
})

export default router
