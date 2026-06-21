<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>用户管理</h2>
        <p class="subtitle">管理系统用户账号与访问权限</p>
      </div>
      <n-button type="primary" @click="openCreate">新建用户</n-button>
    </div>

    <n-card size="small" class="table-card">
      <div class="filter-bar">
        <n-input
          v-model:value="filters.keyword"
          placeholder="搜索用户名或姓名"
          clearable
          style="width: 220px"
          @keyup.enter="applyFilters"
          @clear="applyFilters"
        />
        <n-select
          v-model:value="filters.role"
          :options="roleFilterOptions"
          placeholder="角色"
          clearable
          style="width: 140px"
          @update:value="applyFilters"
        />
        <n-select
          v-model:value="filters.status"
          :options="statusFilterOptions"
          placeholder="状态"
          clearable
          style="width: 120px"
          @update:value="applyFilters"
        />
        <n-button @click="applyFilters">查询</n-button>
        <n-button quaternary @click="resetFilters">重置</n-button>
      </div>

      <n-data-table
        :columns="columns"
        :data="users"
        :loading="loading"
        :bordered="false"
        size="small"
        :pagination="{ pageSize: 10 }"
        :scroll-x="960"
      />
    </n-card>

    <n-modal v-model:show="showCreate" preset="card" title="新建用户" style="width: 440px">
      <n-form label-placement="left" label-width="80">
        <n-form-item label="用户名"><n-input v-model:value="createForm.username" /></n-form-item>
        <n-form-item label="姓名"><n-input v-model:value="createForm.display_name" /></n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="createForm.role" :options="roleOptions" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="createForm.password" type="password" placeholder="至少 6 位" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCreate = false">取消</n-button>
          <n-button type="primary" :loading="creating" @click="handleCreate">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showEdit" preset="card" title="编辑用户" style="width: 440px">
      <n-form v-if="editing" label-placement="left" label-width="80">
        <n-form-item label="用户名"><n-input :value="editing.username" disabled /></n-form-item>
        <n-form-item label="姓名"><n-input v-model:value="editing.display_name" /></n-form-item>
        <n-form-item label="角色">
          <n-select
            v-model:value="editingRole"
            :options="editRoleOptions"
            :disabled="isLastAdminSelf"
          />
        </n-form-item>
        <n-alert v-if="isLastAdminSelf" type="warning" :show-icon="false" style="margin-top: 4px">
          当前为唯一管理员，不可变更角色
        </n-alert>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showEdit = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSaveEdit">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal
      v-model:show="showResetPassword"
      preset="card"
      title="重置密码"
      style="width: 440px"
    >
      <n-form label-placement="left" label-width="80">
        <n-form-item label="用户">
          <n-input :value="resetTarget?.display_name || resetTarget?.username" disabled />
        </n-form-item>
        <n-form-item label="新密码">
          <n-input
            v-model:value="resetPassword"
            type="password"
            placeholder="至少 6 位"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showResetPassword = false">取消</n-button>
          <n-button type="primary" :loading="resetting" @click="handleResetPassword">确认重置</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSpace,
  NSelect,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
  type SelectOption,
} from 'naive-ui'
import {
  createUser,
  deleteUser,
  listRoles,
  listUsers,
  resetUserPassword,
  updateUser,
  updateUserRoles,
  type RoleInfo,
} from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import type { UserInfo } from '@/types'
import { getPrimaryRoleLabel, isAdmin } from '@/utils/role'

const message = useMessage()
const dialog = useDialog()
const authStore = useAuthStore()

const users = ref<UserInfo[]>([])
const roles = ref<RoleInfo[]>([])
const loading = ref(false)
const creating = ref(false)
const saving = ref(false)
const resetting = ref(false)
const showCreate = ref(false)
const showEdit = ref(false)
const showResetPassword = ref(false)
const editing = ref<UserInfo | null>(null)
const editingRole = ref('')
const resetTarget = ref<UserInfo | null>(null)
const resetPassword = ref('')

const createForm = reactive({
  username: '',
  display_name: '',
  role: '',
  password: '',
})

const filters = reactive({
  keyword: '',
  role: null as string | null,
  status: null as boolean | null,
})

const statusFilterOptions: SelectOption[] = [
  { label: '正常', value: true },
  { label: '已禁用', value: false },
]

const roleOptions = computed<SelectOption[]>(() =>
  roles.value.map((r) => ({ label: r.name, value: r.code })),
)

const roleFilterOptions = computed<SelectOption[]>(() => roleOptions.value)

const adminCount = computed(
  () => users.value.filter((u) => isAdmin(u.roles)).length,
)

const isLastAdminSelf = computed(() => {
  if (!editing.value || !authStore.user) return false
  return (
    editing.value.user_id === authStore.user.user_id &&
    isAdmin(editing.value.roles) &&
    adminCount.value <= 1
  )
})

const editRoleOptions = computed<SelectOption[]>(() => {
  if (!editing.value || !authStore.user) return roleOptions.value
  const isSelf = editing.value.user_id === authStore.user.user_id
  const wasAdmin = isAdmin(editing.value.roles)
  if (isSelf && wasAdmin && adminCount.value <= 1) {
    return roleOptions.value.filter((o) => o.value === 'Admin')
  }
  return roleOptions.value
})

function isSelf(row: UserInfo): boolean {
  return authStore.user?.user_id === row.user_id
}

function canDelete(row: UserInfo): boolean {
  if (isSelf(row)) return false
  if (isAdmin(row.roles) && adminCount.value <= 1) return false
  return true
}

const columns: DataTableColumns<UserInfo> = [
  { title: '用户 ID', key: 'user_id', width: 80 },
  { title: '用户名', key: 'username', width: 120 },
  {
    title: '姓名',
    key: 'display_name',
    width: 120,
    render: (row) => row.display_name || row.username,
  },
  {
    title: '角色',
    key: 'roles',
    width: 120,
    render: (row) =>
      h(NTag, { size: 'small', round: true }, () => getPrimaryRoleLabel(row.roles)),
  },
  {
    title: '状态',
    key: 'is_active',
    width: 90,
    render: (row) =>
      h(
        NTag,
        {
          size: 'small',
          type: row.is_active !== false ? 'success' : 'default',
          round: true,
        },
        () => (row.is_active !== false ? '正常' : '已禁用'),
      ),
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right',
    render: (row) =>
      h('div', { class: 'action-btns' }, [
        h(
          NButton,
          { size: 'small', quaternary: true, type: 'primary', onClick: () => openEdit(row) },
          () => '编辑',
        ),
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            type: 'info',
            onClick: () => openResetPassword(row),
          },
          () => '重置密码',
        ),
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            type: 'error',
            disabled: !canDelete(row),
            onClick: () => handleDelete(row),
          },
          () => '删除',
        ),
      ]),
  },
]

function apiErrorMessage(error: unknown, fallback: string): string {
  const data = (error as { response?: { data?: { message?: string; detail?: string } } })
    ?.response?.data
  if (typeof data?.message === 'string' && data.message) return data.message
  if (typeof data?.detail === 'string' && data.detail) return data.detail
  return fallback
}

function buildListParams() {
  return {
    keyword: filters.keyword.trim() || undefined,
    role: filters.role || undefined,
    is_active: filters.status ?? undefined,
  }
}

async function loadUsers() {
  loading.value = true
  try {
    const data = await listUsers(buildListParams())
    users.value = data.items
  } catch {
    message.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

async function loadRoleOptions() {
  try {
    roles.value = await listRoles()
    if (!createForm.role && roles.value.length > 0) {
      createForm.role = roles.value.find((r) => r.code === 'Sales')?.code ?? roles.value[0].code
    }
  } catch {
    message.error('加载角色列表失败')
  }
}

function applyFilters() {
  loadUsers()
}

function resetFilters() {
  filters.keyword = ''
  filters.role = null
  filters.status = null
  loadUsers()
}

function openCreate() {
  createForm.username = ''
  createForm.display_name = ''
  createForm.password = ''
  if (roles.value.length > 0) {
    createForm.role = roles.value.find((r) => r.code === 'Sales')?.code ?? roles.value[0].code
  }
  showCreate.value = true
}

function openEdit(row: UserInfo) {
  editing.value = {
    ...row,
    display_name: row.display_name ?? row.username,
    roles: [...row.roles],
  }
  editingRole.value = row.roles[0] ?? ''
  showEdit.value = true
}

function openResetPassword(row: UserInfo) {
  resetTarget.value = row
  resetPassword.value = ''
  showResetPassword.value = true
}

async function handleCreate() {
  const username = createForm.username.trim()
  if (!username) {
    message.warning('请输入用户名')
    return
  }
  if (createForm.password.length < 6) {
    message.warning('密码长度不能少于 6 位')
    return
  }
  if (!createForm.role) {
    message.warning('请选择角色')
    return
  }

  creating.value = true
  try {
    await createUser({
      username,
      password: createForm.password,
      display_name: createForm.display_name.trim() || undefined,
      roles: [createForm.role],
    })
    message.success('用户创建成功')
    showCreate.value = false
    await loadUsers()
  } catch (error) {
    message.error(apiErrorMessage(error, '创建用户失败'))
  } finally {
    creating.value = false
  }
}

async function handleSaveEdit() {
  if (!editing.value) return

  if (
    isAdmin(editing.value.roles) &&
    editingRole.value !== 'Admin' &&
    adminCount.value <= 1
  ) {
    message.warning('不能移除最后一个管理员的角色')
    return
  }

  saving.value = true
  try {
    const displayName = (editing.value.display_name ?? '').trim()
    await updateUser(editing.value.user_id, {
      display_name: displayName || editing.value.username,
    })
    if (editingRole.value && editingRole.value !== editing.value.roles[0]) {
      await updateUserRoles(editing.value.user_id, [editingRole.value])
    }
    message.success('保存成功')
    showEdit.value = false
    await loadUsers()
  } catch (error) {
    message.error(apiErrorMessage(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function handleResetPassword() {
  if (!resetTarget.value) return
  if (resetPassword.value.length < 6) {
    message.warning('密码长度不能少于 6 位')
    return
  }

  resetting.value = true
  try {
    await resetUserPassword(resetTarget.value.user_id, resetPassword.value)
    message.success('密码已重置')
    showResetPassword.value = false
  } catch (error) {
    message.error(apiErrorMessage(error, '重置密码失败'))
  } finally {
    resetting.value = false
  }
}

function handleDelete(row: UserInfo) {
  if (!canDelete(row)) {
    if (isSelf(row)) {
      message.warning('不能删除当前登录账号')
    } else {
      message.warning('不能删除最后一个管理员')
    }
    return
  }

  dialog.warning({
    title: '删除用户',
    content: `确定删除用户「${row.display_name || row.username}」？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteUser(row.user_id)
        message.success('用户已删除')
        await loadUsers()
      } catch (error) {
        message.error(apiErrorMessage(error, '删除失败'))
      }
    },
  })
}

onMounted(async () => {
  if (!authStore.user) {
    try {
      await authStore.loadUser()
    } catch {
      /* router guard handles redirect */
    }
  }
  await Promise.all([loadRoleOptions(), loadUsers()])
})
</script>

<style scoped>
@import './admin-page.css';

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
</style>
