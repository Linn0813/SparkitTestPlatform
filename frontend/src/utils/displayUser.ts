/** 评论/记录等场景展示用户：姓名 + 邮箱，避免只显示「系统管理员」等易误解的名称 */
export function displayUserLabel(
  user?: { name?: string | null; email?: string | null } | null,
  userId?: string | null,
  memberLabel?: string | null
): string {
  if (memberLabel && memberLabel !== '—' && !memberLabel.match(/^[0-9a-f-]{36}$/i)) {
    return memberLabel;
  }
  const name = user?.name?.trim();
  const email = user?.email?.trim();
  if (name && email) return `${name} (${email})`;
  if (name) return name;
  if (email) return email;
  if (userId) return userId;
  return '用户';
}
