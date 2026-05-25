import { switchContext } from '@/api/auth';
import { getTemplate } from '@/api/templates';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';
import type { TemplateField } from '@/types/business';

export type TemplateScene = 'functional_case' | 'bug' | 'requirement';

/** 确保顶栏上下文与目标项目一致后再拉取模板（避免设置页与编辑页项目不一致） */
export async function ensureContextForProject(projectId: string): Promise<void> {
  const ctx = useContextStore();
  const auth = useAuthStore();
  if (ctx.projectId === projectId) return;

  const { data } = await switchContext(projectId);
  ctx.applyFromMe(data);
  auth.user = data.user;
  auth.me = data;
}

export async function fetchProjectTemplateFields(
  projectId: string,
  scene: TemplateScene
): Promise<TemplateField[]> {
  await ensureContextForProject(projectId);
  const { data } = await getTemplate(projectId, scene);
  return data.fields ?? [];
}
