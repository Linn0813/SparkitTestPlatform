const TZ = 'Asia/Shanghai';

/** Parse YYYY-MM-DD as UTC+8 calendar date. */
export function parseDateOnly(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

export function formatDateOnly(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function addDays(iso: string, days: number): string {
  const d = parseDateOnly(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return formatDateOnly(d);
}

export function diffDays(a: string, b: string): number {
  const ms = parseDateOnly(a).getTime() - parseDateOnly(b).getTime();
  return Math.round(ms / 86400000);
}

/** Inclusive day list from start to end. */
export function eachDayInRange(start: string, end: string): string[] {
  const days: string[] = [];
  let cur = start;
  while (diffDays(cur, end) <= 0) {
    days.push(cur);
    if (cur === end) break;
    cur = addDays(cur, 1);
  }
  return days;
}

/** Monday of the week containing today (UTC+8), as YYYY-MM-DD. */
export function mondayOfWeekContaining(iso: string): string {
  const d = parseDateOnly(iso);
  const dow = d.getUTCDay();
  const offset = dow === 0 ? -6 : 1 - dow;
  d.setUTCDate(d.getUTCDate() + offset);
  return formatDateOnly(d);
}

/** Default window length: one calendar week (Mon–Sun, UTC+8). */
export const SCHEDULE_WEEK_DAYS = 7;

/** Default window: Monday through Sunday of the week containing today. */
export function defaultScheduleRange(todayIso?: string): { start: string; end: string } {
  const today = todayIso ?? new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date());
  const start = mondayOfWeekContaining(today);
  const end = addDays(start, SCHEDULE_WEEK_DAYS - 1);
  return { start, end };
}

/** Short range for toolbar subtitle, e.g. 5/26（周一）– 6/8（周日） */
export function formatRangeSubtitle(start: string, end: string): string {
  const s = parseDateOnly(start);
  const e = parseDateOnly(end);
  const fmt = (d: Date) => `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
  const sDow = s.getUTCDay();
  const eDow = e.getUTCDay();
  const startTag = sDow === 1 ? '（周一）' : '';
  const endTag = eDow === 0 ? '（周日）' : '';
  return `${fmt(s)}${startTag} – ${fmt(e)}${endTag}`;
}

export function isWeekendDay(iso: string): boolean {
  const dow = parseDateOnly(iso).getUTCDay();
  return dow === 0 || dow === 6;
}

export function formatRangeTitle(start: string, end: string): string {
  const s = parseDateOnly(start);
  const e = parseDateOnly(end);
  const y = s.getUTCFullYear();
  if (s.getUTCFullYear() === e.getUTCFullYear() && s.getUTCMonth() === e.getUTCMonth()) {
    return `${y}年 ${s.getUTCMonth() + 1}月`;
  }
  if (s.getUTCFullYear() === e.getUTCFullYear()) {
    return `${y}年 ${s.getUTCMonth() + 1}月–${e.getUTCMonth() + 1}月`;
  }
  return `${formatDateOnly(s)} ~ ${formatDateOnly(e)}`;
}

const WEEKDAY_ZH = ['日', '一', '二', '三', '四', '五', '六'];

export function formatDayHeader(iso: string, todayIso: string): { weekday: string; label: string; isToday: boolean } {
  const d = parseDateOnly(iso);
  const weekday = WEEKDAY_ZH[d.getUTCDay()];
  const label = `${d.getUTCMonth() + 1}-${d.getUTCDate()}`;
  const isToday = iso === todayIso;
  return { weekday, label, isToday };
}
