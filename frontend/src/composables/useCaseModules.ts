import { computed, ref } from 'vue';
import { listModules } from '@/api/cases';
import { useContextStore } from '@/stores/context';
import type { CaseModule } from '@/types/business';
import { buildModuleTree, moduleSelectOptions } from '@/utils/moduleTree';

/** 用例列表等页面的模块数据（筛选下拉） */
export function useCaseModules() {
  const ctx = useContextStore();
  const modules = ref<CaseModule[]>([]);

  const treeData = computed(() => buildModuleTree(modules.value));
  const moduleOptions = computed(() => moduleSelectOptions(modules.value));

  async function loadModules() {
    if (!ctx.projectId) {
      modules.value = [];
      return;
    }
    const { data } = await listModules();
    modules.value = data;
  }

  return {
    modules,
    treeData,
    moduleOptions,
    loadModules,
  };
}
