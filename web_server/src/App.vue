<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <router-view />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
const themeOverrides = {
  common: {
    primaryColor: '#111111',
    borderRadius: '10px',
  },
}
</script>
