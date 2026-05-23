import type { InjectionKey } from 'vue';
import type { BugItem } from '@/types/business';

export type WorkbenchBugListSource = 'daily' | 'unplanned' | 'fixed' | 'follower';

export interface WorkbenchBugDrawerApi {
  open: (id: string, list: BugItem[], source: WorkbenchBugListSource) => void;
}

export const WORKBENCH_BUG_DRAWER_KEY: InjectionKey<WorkbenchBugDrawerApi> = Symbol('workbenchBugDrawer');
