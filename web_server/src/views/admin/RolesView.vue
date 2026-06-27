<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>角色权限</h2>
        <p class="subtitle">系统角色与权限管理（与后端 Role 枚举一致）</p>
      </div>
    </div>

    <n-grid :cols="2" :x-gap="16" responsive="screen" item-responsive>
      <n-gi span="2 m:1">
        <n-card size="small" title="角色列表" class="content-card">
          <n-spin :show="loading">
            <n-list hoverable clickable>
              <n-list-item
                v-for="role in roles"
                :key="role.code"
                :class="{ active: selectedRole === role.code }"
                @click="selectRole(role.code)"
              >
                <div class="role-item">
                  <div>
                    <div class="role-name">{{ role.name }}</div>
                    <div class="role-desc">{{ role.description || role.code }}</div>
                  </div>
                  <n-tag size="small" round>{{ role.user_count ?? 0 }} 人</n-tag>
                </div>
              </n-list-item>
            </n-list>
          </n-spin>
        </n-card>
      </n-gi>

      <n-gi span="2 m:1">
        <n-card size="small" :title="`${currentRole?.name ?? ''} - 权限配置`" class="content-card">
          <n-alert type="info" style="margin-bottom: 16px" :show-icon="false">
            权限配置已持久化至数据库；管理员角色需保留用户管理与系统配置权限。
          </n-alert>
          <n-spin :show="permLoading">
            <n-tree
              block-line
              checkable
              cascade
              :data="treeData"
              :checked-keys="checkedKeys"
              default-expand-all
              @update:checked-keys="onCheck"
            />
          </n-spin>
          <div style="margin-top: 16px">
            <n-button type="primary" size="small" :loading="saving" @click="savePermissions">
              保存权限
            </n-button>
          </div>
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NGi,
  NGrid,
  NList,
  NListItem,
  NSpin,
  NTag,
  NTree,
  useMessage,
  type TreeOption,
} from 'naive-ui'
import { listRoles, type RoleInfo } from '@/api/user'
import {
  fetchPermissionTree,
  fetchRolePermissions,
  updateRolePermissions,
  type PermissionTreeNode,
} from '@/api/rbac'
import { ROLE_CODES, type RoleCode } from '@/constants/rbac'

const message = useMessage()

const roles = ref<RoleInfo[]>([])
const permissionTree = ref<PermissionTreeNode[]>([])
const loading = ref(false)
const permLoading = ref(false)
const saving = ref(false)
const selectedRole = ref<RoleCode>(ROLE_CODES.Admin)
const checkedKeys = ref<Array<string | number>>([])

const currentRole = computed(() => roles.value.find((r) => r.code === selectedRole.value))

const treeData = computed<TreeOption[]>(() =>
  permissionTree.value.map((node) => ({
    key: node.key,
    label: node.label,
    children: node.children?.map((c) => ({ key: c.key, label: c.label })),
  })),
)

function onCheck(keys: Array<string | number>) {
  checkedKeys.value = keys
}

async function loadRolePermissions(roleCode: string) {
  permLoading.value = true
  try {
    const data = await fetchRolePermissions(roleCode)
    checkedKeys.value = data.permission_codes
  } catch {
    message.error('加载角色权限失败')
  } finally {
    permLoading.value = false
  }
}

async function selectRole(roleCode: string) {
  selectedRole.value = roleCode as RoleCode
  await loadRolePermissions(roleCode)
}

async function savePermissions() {
  saving.value = true
  try {
    const codes = checkedKeys.value.map(String)
    await updateRolePermissions(selectedRole.value, codes)
    message.success('权限已保存')
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { message?: string } } })?.response?.data
      ?.message
    message.error(detail || '保存权限失败')
  } finally {
    saving.value = false
  }
}

async function loadRoles() {
  loading.value = true
  try {
    roles.value = await listRoles()
    if (roles.value.length > 0 && !roles.value.some((r) => r.code === selectedRole.value)) {
      selectedRole.value = roles.value[0].code as RoleCode
    }
  } catch {
    message.error('加载角色列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    permissionTree.value = await fetchPermissionTree()
  } catch {
    message.error('加载权限树失败')
  }
  await loadRoles()
  await loadRolePermissions(selectedRole.value)
})
</script>

<style scoped>
@import './admin-page.css';
.role-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 12px;
}
.role-name {
  font-size: 14px;
  font-weight: 500;
}
.role-desc {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}
:deep(.n-list-item.active) {
  background: #f5f5f5;
}
</style>
