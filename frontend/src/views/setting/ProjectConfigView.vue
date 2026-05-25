<template>
  <n-card title="项目配置">
    <n-tabs v-model:value="tab" type="line" class="project-config__tabs">
      <n-tab-pane name="members" tab="项目成员">
        <ProjectMembersView embedded />
      </n-tab-pane>
      <n-tab-pane name="templates" tab="项目设置">
        <TemplateSettingsView embedded />
      </n-tab-pane>
    </n-tabs>
  </n-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { NCard, NTabPane, NTabs } from 'naive-ui';
import ProjectMembersView from '@/views/setting/ProjectMembersView.vue';
import TemplateSettingsView from '@/views/setting/TemplateSettingsView.vue';

const route = useRoute();
const router = useRouter();

const tab = ref('members');

watch(
  () => route.query.tab,
  (t) => {
    if (t === 'members' || t === 'templates') {
      tab.value = t;
    } else if (t === 'projects') {
      tab.value = 'members';
    }
  },
  { immediate: true }
);

watch(tab, (t) => {
  if (route.query.tab !== t) {
    router.replace({ query: { ...route.query, tab: t } });
  }
});
</script>

<style scoped>
.project-config__tabs :deep(.n-tab-pane) {
  padding-top: 16px;
}
</style>
