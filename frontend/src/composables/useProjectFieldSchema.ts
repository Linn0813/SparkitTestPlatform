import { computed, ref, watch, type Ref } from 'vue';
import type { DataTableColumns } from 'naive-ui';
import { fetchProjectTemplateFields, type TemplateScene } from '@/composables/useProjectTemplate';
import {
  buildFieldCatalog,
  buildTemplateTableColumns,
  detailTemplateFields,
  listTableTemplateFields,
  type EntityScene,
  type TemplateFieldFormatContext,
} from '@/schemas/entityFieldSchema';
import type { TemplateField } from '@/types/business';

const cache = new Map<string, TemplateField[]>();

function cacheKey(projectId: string, scene: EntityScene): string {
  return `${projectId}:${scene}`;
}

export function invalidateProjectFieldSchemaCache(projectId: string, scene?: EntityScene) {
  if (scene) {
    cache.delete(cacheKey(projectId, scene));
    return;
  }
  for (const k of cache.keys()) {
    if (k.startsWith(`${projectId}:`)) cache.delete(k);
  }
}

export function useProjectFieldSchema(
  scene: EntityScene,
  projectId: Ref<string | null>
) {
  const templateFields = ref<TemplateField[]>([]);
  const loading = ref(false);

  const templateFieldsForUi = computed(() => detailTemplateFields(scene, templateFields.value));
  const listFields = computed(() => listTableTemplateFields(scene, templateFields.value));
  const filterCatalog = computed(() => buildFieldCatalog(scene, templateFields.value));

  function buildListColumns<T extends { custom_fields?: Record<string, unknown> }>(
    ctx?: TemplateFieldFormatContext
  ): DataTableColumns<T> {
    return buildTemplateTableColumns(listFields.value, ctx) as DataTableColumns<T>;
  }

  async function reload(force = false) {
    const pid = projectId.value;
    if (!pid) {
      templateFields.value = [];
      return;
    }
    const key = cacheKey(pid, scene);
    if (!force && cache.has(key)) {
      templateFields.value = cache.get(key)!;
      return;
    }
    loading.value = true;
    try {
      const fields = await fetchProjectTemplateFields(pid, scene as TemplateScene);
      cache.set(key, fields);
      templateFields.value = fields;
    } finally {
      loading.value = false;
    }
  }

  function invalidateCache(pid?: string | null) {
    if (pid) {
      cache.delete(cacheKey(pid, scene));
    } else {
      for (const k of cache.keys()) {
        if (k.endsWith(`:${scene}`)) cache.delete(k);
      }
    }
  }

  watch(
    projectId,
    (pid) => {
      if (pid) reload();
      else templateFields.value = [];
    },
    { immediate: true }
  );

  return {
    templateFields,
    templateFieldsForUi,
    listFields,
    filterCatalog,
    loading,
    reload,
    invalidateCache,
    buildListColumns,
  };
}
