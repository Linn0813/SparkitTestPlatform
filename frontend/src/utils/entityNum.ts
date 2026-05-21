/** 列表「编号」列（勿用 `#` 作列名，避免与单元格数字拼成「#1」观感） */
export const NUM_TABLE_COLUMN = {
  title: '编号',
  key: 'num',
  width: 60,
} as const;

export function formatNum(num: number | null | undefined): string {
  if (num == null || Number.isNaN(Number(num))) return '—';
  return String(num);
}

/** 编号 + 标题（需求/版本/缺陷等统一不加 # 前缀） */
export function formatNumWithTitle(num: number, title: string, separator = ' · '): string {
  return `${formatNum(num)}${separator}${title}`;
}
