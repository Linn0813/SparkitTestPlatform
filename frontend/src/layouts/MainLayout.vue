<template>
  <n-layout has-sider style="height: 100vh">
    <n-layout-sider bordered :width="220" collapse-mode="width" class="app-sidebar">
      <div class="logo">SparkitTestPlatform</div>
      <n-menu
        class="app-menu"
        :value="activeKey || undefined"
        :options="menuOptions"
        :root-indent="18"
        :indent="14"
        @update:value="onMenu"
      />
    </n-layout-sider>
    <n-layout>
      <n-layout-header bordered class="app-header">
        <template v-if="showContextSwitcher">
          <n-select
            v-model:value="ctx.projectId"
            :options="projectOptions"
            placeholder="选择项目"
            style="width: 220px"
            @update:value="onProjectChange"
          />
        </template>
        <n-text v-else depth="3" class="header-hint">{{ headerHint }}</n-text>
        <div style="flex: 1" />
        <n-text depth="3" class="build-time" :title="`前端构建时间 ${appBuildTimeLabel}`">
          构建 {{ appBuildTimeLabel }}
        </n-text>
        <n-dropdown :options="userMenuOptions" @select="onUserMenu">
          <n-button quaternary>{{ auth.user?.name }}</n-button>
        </n-dropdown>
      </n-layout-header>
      <n-layout-content content-style="padding: 16px">
        <router-view />
      </n-layout-content>
    </n-layout>
    <UserProfileModal v-model:show="showProfile" />
  </n-layout>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NDropdown,
  NLayout,
  NLayoutContent,
  NLayoutHeader,
  NLayoutSider,
  NMenu,
  NSelect,
  NText,
} from 'naive-ui';
import UserProfileModal from '@/components/UserProfileModal.vue';
import { useSidebarMenu } from '@/composables/useSidebarMenu';
import { useUserAdminMenu } from '@/composables/useUserAdminMenu';
import { findMenuLabel } from '@/config/sidebarMenu';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';
import { appBuildTimeLabel } from '@/utils/buildInfo';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const ctx = useContextStore();

const { menuOptions, activeKey, activeLabel, onMenu } = useSidebarMenu();
const { buildUserMenuOptions } = useUserAdminMenu();

const showContextSwitcher = computed(() => !route.meta.hideContextSwitcher);

const headerHint = computed(() => {
  if (showContextSwitcher.value) return '';
  return findMenuLabel(route.name as string) ?? activeLabel.value ?? '';
});

const projectOptions = computed(() =>
  (auth.me?.projects ?? []).map((p) => ({ label: p.name, value: p.id }))
);

const showProfile = ref(false);
const userMenuOptions = computed(() => buildUserMenuOptions());

async function onProjectChange(id: string) {
  await ctx.switchProject(id);
  await auth.loadMe();
}

function onUserMenu(key: string) {
  if (key === 'profile') {
    showProfile.value = true;
    return;
  }
  if (key === 'logout') {
    auth.logoutAndRedirect();
    return;
  }
  router.push({ name: key });
}
</script>

<style scoped>
.logo {
  padding: 16px 18px 12px;
  font-weight: 700;
  font-size: 18px;
  color: #18a058;
  border-bottom: 1px solid var(--n-border-color);
  margin-bottom: 4px;
}

.app-menu {
  padding: 4px 8px 12px;
}

.app-header {
  height: 56px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-hint {
  font-size: 13px;
}

.build-time {
  font-size: 12px;
  white-space: nowrap;
  user-select: text;
}
</style>
