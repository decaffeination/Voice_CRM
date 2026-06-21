<template>
  <div class="admin-shell">
    <aside class="admin-sider">
      <div class="sider-title">系统管理</div>
      <n-menu
        :value="activeMenu"
        :options="menuOptions"
        @update:value="onMenuSelect"
      />
    </aside>
    <main class="admin-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon, NMenu, type MenuOption } from 'naive-ui'
import {
  PeopleOutline,
  ShieldCheckmarkOutline,
  HardwareChipOutline,
  PulseOutline,
  MailOutline,
  DocumentTextOutline,
  SettingsOutline,
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => {
  const name = route.name
  if (typeof name === 'string' && name.startsWith('admin-')) {
    return name.replace('admin-', '')
  }
  return 'users'
})

function renderIcon(icon: typeof PeopleOutline) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  { label: '用户管理', key: 'users', icon: renderIcon(PeopleOutline) },
  { label: '角色权限', key: 'roles', icon: renderIcon(ShieldCheckmarkOutline) },
  { label: '模型配置', key: 'models', icon: renderIcon(HardwareChipOutline) },
  { label: '系统监控', key: 'monitor', icon: renderIcon(PulseOutline) },
  { label: '邮件配置', key: 'email', icon: renderIcon(MailOutline) },
  { label: '操作审计', key: 'audit', icon: renderIcon(DocumentTextOutline) },
  { label: '系统参数', key: 'params', icon: renderIcon(SettingsOutline) },
]

function onMenuSelect(key: string) {
  router.push(`/admin/${key}`)
}
</script>

<style scoped>
.admin-shell {
  display: flex;
  min-height: calc(100vh - 57px);
  background: #f7f7f8;
}
.admin-sider {
  width: 220px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #ececec;
  padding: 20px 12px;
}
.sider-title {
  font-size: 15px;
  font-weight: 600;
  color: #111;
  padding: 0 12px 16px;
}
.admin-main {
  flex: 1;
  min-width: 0;
  padding: 24px;
  box-sizing: border-box;
}
</style>
