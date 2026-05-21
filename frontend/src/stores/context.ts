import { defineStore } from 'pinia';
import { ref } from 'vue';
import { switchContext } from '@/api/auth';
import type { MeResponse } from '@/types';

export const useContextStore = defineStore('context', () => {
  const projectId = ref<string | null>(null);

  function applyFromMe(data: MeResponse) {
    projectId.value =
      data.user.last_project_id ??
      data.projects[0]?.id ??
      null;
  }

  async function switchProject(id: string | null) {
    const { data } = await switchContext(id);
    applyFromMe(data);
  }

  function reset() {
    projectId.value = null;
  }

  return { projectId, applyFromMe, switchProject, reset };
});
