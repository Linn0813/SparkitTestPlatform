<template>
  <n-alert v-if="projectName" type="info" style="margin-bottom: 12px" :show-icon="false">
    <template v-if="variant === 'settings'">
      当前配置项目：<strong>{{ projectName }}</strong>。此处仅管理<strong>自定义字段</strong>；保存后会同步为顶栏当前项目。
      <template v-if="scene === 'case'"> 用例编辑页另有固定项：标题、优先级、前置条件、步骤。</template>
      <template v-else-if="scene === 'bug'"> 缺陷编辑页另有固定项：标题、描述、状态。</template>
    </template>
    <template v-else>
      当前项目：<strong>{{ projectName }}</strong>。下方「自定义字段」与「项目设置 →
      {{ scene === 'case' ? '用例字段' : '缺陷字段' }}」一致；若不一致请检查顶栏项目是否与设置页所选相同。
    </template>
  </n-alert>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NAlert } from 'naive-ui';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';

const props = withDefaults(
  defineProps<{
    projectId?: string | null;
    scene?: 'case' | 'bug';
    variant?: 'settings' | 'edit';
  }>(),
  {
    scene: 'case',
    variant: 'edit',
  }
);

const auth = useAuthStore();
const ctx = useContextStore();

const projectName = computed(() => {
  const id = props.projectId ?? ctx.projectId;
  if (!id) return null;
  return auth.me?.projects.find((p) => p.id === id)?.name ?? id;
});
</script>
