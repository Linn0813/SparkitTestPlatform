const DETAIL_ZH: Record<string, string> = {
  'Invalid email or password': '邮箱或密码错误',
  'User is disabled': '账号已禁用',
  'Email already exists': '该邮箱已存在',
  'Current password incorrect': '当前密码不正确',
};

function translateDetail(detail: string): string {
  return DETAIL_ZH[detail] ?? detail;
}

function messageFromValidationItem(item: { msg?: string; loc?: unknown[] }): string | null {
  if (!item?.msg) return null;
  const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null;
  if (field === 'password') return '密码至少 6 位';
  if (field === 'email') return '邮箱格式不正确';
  if (field === 'name') return '请填写姓名';
  return item.msg;
}

/** 从 axios / FastAPI 错误响应中提取可展示文案 */
export function apiErrorMessage(e: unknown, fallback: string): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return translateDetail(detail.trim());
  }
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    return messageFromValidationItem(first) ?? fallback;
  }
  return fallback;
}
