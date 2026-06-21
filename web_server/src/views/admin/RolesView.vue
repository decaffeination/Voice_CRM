<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h2>角色权限</h2>
        <p class="subtitle">基于 RBAC 的角色与权限管理，预留扩展能力</p>
      </div>
    </div>

    <n-grid :cols="2" :x-gap="16" responsive="screen" item-responsive>
      <n-gi span="2 m:1">
        <n-card size="small" title="角色列表" class="content-card">
          <n-list hoverable clickable>
            <n-list-item
              v-for="role in roles"
              :key="role.code"
              :class="{ active: selectedRole === role.code }"
              @click="selectedRole = role.code"
            >
              <div class="role-item">
                <div>
                  <div class="role-name">{{ role.name }}</div>
                  <div class="role-desc">{{ role.description }}</div>
                </div>
                <n-tag size="small" round>{{ role.user_count }} 人</n-tag>
              </div>
            </n-list-item>
          </n-list>
        </n-card>
      </n-gi>

      <n-gi span="2 m:1">
        <n-card size="small" :title="`${currentRole?.name ?? ''} - 权限配置`" class="content-card">
          <n-alert type="info" style="margin-bottom: 16px" :show-icon="false">
            权限树展示当前角色可访问的模块与操作，后续可对接后端 RBAC 接口。
          </n-alert>
          <n-tree
            block-line
            checkable
            cascade
            :data="treeData"
            :checked-keys="checkedKeys"
            default-expand-all
            @update:checked-keys="onCheck"
          />
          <div style="margin-top: 16px">
            <n-button type="primary" size="small" @click="savePermissions">保存权限（Mock）</n-button>
          </div>
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NGi,
  NGrid,
  NList,
  NListItem,
  NTag,
  NTree,
  useMessage,
  type TreeOption,
} from 'naive-ui'
import {
  MOCK_ROLES,
  PERMISSION_TREE,
  ROLE_PERMISSIONS,
} from '@/mock/admin'

const message = useMessage()

const roles = ref([...MOCK_ROLES])
const selectedRole = ref('super_admin')
const permissionMap = ref<Record<string, string[]>>({ ...ROLE_PERMISSIONS })

const currentRole = computed(() => roles.value.find((r) => r.code === selectedRole.value))

const treeData = computed<TreeOption[]>(() =>
  PERMISSION_TREE.map((node) => ({
    key: node.key,
    label: node.label,
    children: node.children?.map((c) => ({ key: c.key, label: c.label })),
  })),
)

const checkedKeys = computed(() => permissionMap.value[selectedRole.value] ?? [])

function onCheck(keys: Array<string | number>) {
  permissionMap.value[selectedRole.value] = keys.map(String)
}

function savePermissions() {
  message.success('权限已保存（Mock）')
}
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
