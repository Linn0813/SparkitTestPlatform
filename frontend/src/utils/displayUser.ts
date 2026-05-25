/** 评论/记录等场景展示用户：优先姓名，无姓名时用 userId */
export function displayUserLabel(
  user?: { name?: string | null; email?: string | null } | null,
  userId?: string | null,
  memberLabel?: string | null
): string {
  if (memberLabel && memberLabel !== '—' && !memberLabel.match(/^[0-9a-f-]{36}$/i)) {
    return memberLabel;
  }
  const name = user?.name?.trim();
  if (name) return name;
  if (userId) return userId;
  return '用户';
}
