import { computed, ref, watch, type Ref } from 'vue';
import { listProjectMembers } from '@/api/projects';
import type { ProjectMember } from '@/types';

function memberNameOnly(m: ProjectMember): string {
  const name = m.user?.name?.trim();
  if (name) return name;
  return m.user_id;
}

export function useProjectMemberOptions(projectId: Ref<string | null | undefined>) {
  const loading = ref(false);
  const options = ref<{ label: string; value: string }[]>([]);
  const nameOptions = ref<{ label: string; value: string }[]>([]);

  async function load() {
    const id = projectId.value;
    if (!id) {
      options.value = [];
      nameOptions.value = [];
      return;
    }
    loading.value = true;
    try {
      const { data } = await listProjectMembers(id);
      options.value = data.map((m) => ({
        label: memberNameOnly(m),
        value: m.user_id,
      }));
      nameOptions.value = data.map((m) => ({
        label: memberNameOnly(m),
        value: m.user_id,
      }));
    } catch {
      options.value = [];
      nameOptions.value = [];
    } finally {
      loading.value = false;
    }
  }

  watch(projectId, () => void load(), { immediate: true });

  const labelByUserId = computed(() => {
    const map = new Map<string, string>();
    for (const o of options.value) {
      map.set(o.value, o.label);
    }
    return map;
  });

  const nameByUserId = computed(() => {
    const map = new Map<string, string>();
    for (const o of nameOptions.value) {
      map.set(o.value, o.label);
    }
    return map;
  });

  return { options, nameOptions, loading, load, labelByUserId, nameByUserId };
}
