export function pickAdjacentItemId<T extends { id: string }>(
  items: T[],
  previousIndex: number
): string | null {
  if (!items.length) return null;
  const idx = previousIndex >= 0 ? Math.min(previousIndex, items.length - 1) : 0;
  return items[idx].id;
}
