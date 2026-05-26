import { ref, watch } from 'vue';
import {
  listRequirementOptions,
  listRequirementRoles,
  type RequirementOptionDef,
  type RequirementRoleDef,
} from '@/api/templates';

const rolesCache = new Map<string, RequirementRoleDef[]>();
const optionsCache = new Map<string, RequirementOptionDef[]>();

function optionsCacheKey(projectId: string, category?: string) {
  return category ? `${projectId}:${category}` : `${projectId}:all`;
}

export function invalidateRequirementProjectConfig(projectId: string) {
  rolesCache.delete(projectId);
  for (const key of optionsCache.keys()) {
    if (key.startsWith(`${projectId}:`)) optionsCache.delete(key);
  }
}

export async function loadRequirementRoles(projectId: string, force = false): Promise<RequirementRoleDef[]> {
  if (!force && rolesCache.has(projectId)) {
    return rolesCache.get(projectId)!;
  }
  const { data } = await listRequirementRoles(projectId);
  const sorted = [...data].sort((a, b) => a.sort - b.sort || a.role_key.localeCompare(b.role_key));
  rolesCache.set(projectId, sorted);
  return sorted;
}

export async function loadRequirementOptions(
  projectId: string,
  category?: 'priority' | 'req_type',
  force = false
): Promise<RequirementOptionDef[]> {
  const key = optionsCacheKey(projectId, category);
  if (!force && optionsCache.has(key)) {
    return optionsCache.get(key)!;
  }
  const { data } = await listRequirementOptions(projectId, category);
  const sorted = [...data].sort((a, b) => a.sort - b.sort || a.option_key.localeCompare(b.option_key));
  optionsCache.set(key, sorted);
  if (!category) {
    for (const cat of ['priority', 'req_type'] as const) {
      optionsCache.set(
        optionsCacheKey(projectId, cat),
        sorted.filter((o) => o.category === cat)
      );
    }
  }
  return sorted;
}

export function useRequirementProjectConfig(projectId: () => string | null) {
  const roles = ref<RequirementRoleDef[]>([]);
  const priorityOptions = ref<RequirementOptionDef[]>([]);
  const typeOptions = ref<RequirementOptionDef[]>([]);
  const loading = ref(false);

  async function reload(force = false) {
    const pid = projectId();
    if (!pid) {
      roles.value = [];
      priorityOptions.value = [];
      typeOptions.value = [];
      return;
    }
    loading.value = true;
    try {
      const [r, p, t] = await Promise.all([
        loadRequirementRoles(pid, force),
        loadRequirementOptions(pid, 'priority', force),
        loadRequirementOptions(pid, 'req_type', force),
      ]);
      roles.value = r;
      priorityOptions.value = p;
      typeOptions.value = t;
    } finally {
      loading.value = false;
    }
  }

  function priorityLabel(key: string): string {
    return priorityOptions.value.find((o) => o.option_key === key)?.label ?? key;
  }

  function typeLabel(key: string): string {
    return typeOptions.value.find((o) => o.option_key === key)?.label ?? key;
  }

  function roleLabel(key: string): string {
    return roles.value.find((r) => r.role_key === key)?.label ?? key;
  }

  watch(projectId, () => void reload(), { immediate: true });

  return {
    roles,
    priorityOptions,
    typeOptions,
    loading,
    reload,
    priorityLabel,
    typeLabel,
    roleLabel,
  };
}
