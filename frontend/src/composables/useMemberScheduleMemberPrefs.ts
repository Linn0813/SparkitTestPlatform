import { computed, ref, watch, type Ref } from 'vue';
import type { MemberScheduleRow } from '@/types/business';

type StoredPrefs = {
  order: string[];
  visible: Record<string, boolean>;
};

/** 无本地偏好时的默认成员顺序（按显示名匹配，未列出者排在末尾并按姓名排序） */
export const DEFAULT_MEMBER_SCHEDULE_NAME_ORDER = [
  'Kwise',
  'ansin',
  'jerrryliu',
  '假老练_',
  'Linn玲玲',
  'MelodyMai',
  'Suvi',
] as const;

const STORAGE_PREFIX = 'sparkit:memberScheduleMembers:v2:';

function storageKey(projectId: string): string {
  return `${STORAGE_PREFIX}${projectId}`;
}

function loadPrefs(projectId: string): StoredPrefs | null {
  try {
    const raw = localStorage.getItem(storageKey(projectId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object') return null;
    const obj = parsed as Record<string, unknown>;
    const order = obj.order;
    const visible = obj.visible;
    if (!Array.isArray(order) || !visible || typeof visible !== 'object') return null;
    return {
      order: order.filter((id): id is string => typeof id === 'string'),
      visible: Object.fromEntries(
        Object.entries(visible as Record<string, unknown>).filter(
          (entry): entry is [string, boolean] => typeof entry[1] === 'boolean'
        )
      ),
    };
  } catch {
    return null;
  }
}

function savePrefs(projectId: string, prefs: StoredPrefs) {
  localStorage.setItem(storageKey(projectId), JSON.stringify(prefs));
}

function nameOrderIndex(name: string): number {
  const trimmed = name.trim();
  const idx = DEFAULT_MEMBER_SCHEDULE_NAME_ORDER.findIndex(
    (n) => n === trimmed || n.toLowerCase() === trimmed.toLowerCase()
  );
  return idx >= 0 ? idx : DEFAULT_MEMBER_SCHEDULE_NAME_ORDER.length;
}

function defaultOrderFromApi(members: MemberScheduleRow[]): string[] {
  return [...members]
    .sort((a, b) => {
      const byPriority = nameOrderIndex(a.name) - nameOrderIndex(b.name);
      if (byPriority !== 0) return byPriority;
      return a.name.localeCompare(b.name, 'zh-CN');
    })
    .map((m) => m.user_id);
}

function mergeOrder(existing: string[], apiIds: string[]): string[] {
  const apiSet = new Set(apiIds);
  const next = existing.filter((id) => apiSet.has(id));
  for (const id of apiIds) {
    if (!next.includes(id)) next.push(id);
  }
  return next;
}

function mergeVisible(
  existing: Record<string, boolean>,
  apiIds: string[]
): Record<string, boolean> {
  const apiSet = new Set(apiIds);
  const next: Record<string, boolean> = {};
  for (const id of apiIds) {
    next[id] = existing[id] !== false;
  }
  for (const id of Object.keys(existing)) {
    if (!apiSet.has(id)) delete next[id];
  }
  return next;
}

export function useMemberScheduleMemberPrefs(
  projectId: Ref<string | null>,
  apiMembers: Ref<MemberScheduleRow[]>
) {
  const order = ref<string[]>([]);
  const visible = ref<Record<string, boolean>>({});

  const memberMap = computed(() => {
    const map = new Map<string, MemberScheduleRow>();
    for (const m of apiMembers.value) map.set(m.user_id, m);
    return map;
  });

  const orderedMembers = computed(() => {
    const map = memberMap.value;
    const rows: MemberScheduleRow[] = [];
    for (const id of order.value) {
      const row = map.get(id);
      if (row) rows.push(row);
    }
    return rows;
  });

  const displayMembers = computed(() =>
    orderedMembers.value.filter((m) => visible.value[m.user_id] !== false)
  );

  const hasVisibleMember = computed(() => displayMembers.value.length > 0);

  function persist() {
    if (!projectId.value) return;
    savePrefs(projectId.value, {
      order: order.value,
      visible: visible.value,
    });
  }

  function mergeWithApiMembers(members: MemberScheduleRow[]) {
    const apiIds = members.map((m) => m.user_id);
    if (!apiIds.length) {
      order.value = [];
      visible.value = {};
      return;
    }
    if (order.value.length === 0) {
      const stored = projectId.value ? loadPrefs(projectId.value) : null;
      order.value =
        stored?.order?.length ? mergeOrder(stored.order, apiIds) : defaultOrderFromApi(members);
      visible.value = mergeVisible(stored?.visible ?? {}, apiIds);
    } else {
      order.value = mergeOrder(order.value, apiIds);
      visible.value = mergeVisible(visible.value, apiIds);
    }
    persist();
  }

  function resetForProject(_pid: string | null) {
    order.value = [];
    visible.value = {};
  }

  function isMemberVisible(userId: string): boolean {
    return visible.value[userId] !== false;
  }

  function setMemberVisible(userId: string, value: boolean) {
    if (!memberMap.value.has(userId)) return;
    visible.value = { ...visible.value, [userId]: value };
    persist();
  }

  function setAllVisible(value: boolean) {
    const next = { ...visible.value };
    for (const id of order.value) {
      if (memberMap.value.has(id)) next[id] = value;
    }
    visible.value = next;
    persist();
  }

  function moveMember(userId: string, delta: -1 | 1) {
    const idx = order.value.indexOf(userId);
    if (idx < 0) return;
    const j = idx + delta;
    if (j < 0 || j >= order.value.length) return;
    const next = [...order.value];
    [next[idx], next[j]] = [next[j], next[idx]];
    order.value = next;
    persist();
  }

  watch(projectId, (pid) => resetForProject(pid), { immediate: true });

  watch(
    apiMembers,
    (members) => {
      if (!projectId.value) {
        order.value = [];
        visible.value = {};
        return;
      }
      mergeWithApiMembers(members);
    },
    { deep: true }
  );

  return {
    order,
    visible,
    orderedMembers,
    displayMembers,
    hasVisibleMember,
    isMemberVisible,
    setMemberVisible,
    setAllVisible,
    moveMember,
  };
}
