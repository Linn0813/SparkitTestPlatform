/** 返回 UTC+8（Asia/Shanghai）当前日历日，格式 YYYY-MM-DD。 */
export function todayInUtcPlus8(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(new Date());
}
