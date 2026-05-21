import { computed, ref, watch, type Ref } from 'vue';
import { listProjectMembers } from '@/api/projects';

export function useProjectMemberOptions(projectId: Ref<string | null | undefined>) {
  const loading = ref(false);
  const options = ref<{ label: string; value: string }[]>([]);

  async function load() {
    const id = projectId.value;
    if (!id) {
      options.value = [];
      return;
    }
    loading.value = true;
    try {
      const { data } = await listProjectMembers(id);
      options.value = data.map((m) => ({
        label: m.user?.name ? `${m.user.name} (${m.user.email})` : m.user_id,
        value: m.user_id,
      }));
    } catch {
      options.value = [];
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

  return { options, loading, load, labelByUserId };
}
