import { describe, expect, it } from 'vitest';
import type { MemberScheduleItem } from '@/types/business';
import { groupUnscheduledItems } from './scheduleLayout';

function task(
  partial: Partial<MemberScheduleItem> & { id: string; requirement_id?: string }
): MemberScheduleItem {
  return {
    item_type: 'requirement_node_task',
    title: partial.title ?? '任务',
    assignee_id: 'u1',
    estimate_points: null,
    scheduled_start: null,
    scheduled_end: null,
    requirement_title: partial.requirement_title ?? '需求 A',
    node_label: partial.node_label ?? '节点',
    ...partial,
  };
}

function bug(partial: Partial<MemberScheduleItem> & { id: string }): MemberScheduleItem {
  return {
    item_type: 'bug',
    title: partial.title ?? '缺陷',
    assignee_id: 'u1',
    estimate_points: null,
    scheduled_start: null,
    scheduled_end: null,
    bug_id: partial.bug_id ?? 'bug-1',
    bug_title: partial.bug_title ?? '缺陷标题',
    ...partial,
  };
}

describe('groupUnscheduledItems', () => {
  it('merges tasks with the same requirement_id', () => {
    const items = [
      task({ id: 't1', requirement_id: 'r1', node_label: '发版验证', title: '已发版' }),
      task({ id: 't2', requirement_id: 'r1', node_label: '用例设计', title: '用例设计' }),
    ];
    const groups = groupUnscheduledItems(items);
    expect(groups).toHaveLength(1);
    expect(groups[0].kind).toBe('requirement');
    expect(groups[0].requirement_id).toBe('r1');
    expect(groups[0].items).toHaveLength(2);
    expect(groups[0].items.map((i) => i.id)).toEqual(['t1', 't2']);
  });

  it('keeps separate groups for different requirements', () => {
    const items = [
      task({ id: 't1', requirement_id: 'r1', requirement_title: '需求一' }),
      task({ id: 't2', requirement_id: 'r2', requirement_title: '需求二' }),
    ];
    const groups = groupUnscheduledItems(items);
    expect(groups).toHaveLength(2);
    expect(groups[0].title).toBe('需求一');
    expect(groups[1].title).toBe('需求二');
  });

  it('preserves group order by first occurrence', () => {
    const items = [
      task({ id: 't1', requirement_id: 'r2', requirement_title: 'B' }),
      task({ id: 't2', requirement_id: 'r1', requirement_title: 'A' }),
      task({ id: 't3', requirement_id: 'r2', requirement_title: 'B' }),
    ];
    const groups = groupUnscheduledItems(items);
    expect(groups.map((g) => g.requirement_id)).toEqual(['r2', 'r1']);
    expect(groups[0].items).toHaveLength(2);
  });

  it('keeps bugs as one item per group', () => {
    const items = [
      task({ id: 't1', requirement_id: 'r1' }),
      bug({ id: 'b1', bug_id: 'bug-1', bug_title: '缺陷 X' }),
      bug({ id: 'b2', bug_id: 'bug-2', bug_title: '缺陷 Y' }),
    ];
    const groups = groupUnscheduledItems(items);
    expect(groups).toHaveLength(3);
    expect(groups[0].kind).toBe('requirement');
    expect(groups[1].kind).toBe('bug');
    expect(groups[2].kind).toBe('bug');
    expect(groups[1].items).toHaveLength(1);
  });

  it('falls back to single-task group when requirement_id is missing', () => {
    const items = [task({ id: 't1', requirement_id: undefined, title: '孤立任务' })];
    const groups = groupUnscheduledItems(items);
    expect(groups).toHaveLength(1);
    expect(groups[0].key).toBe('task:t1');
    expect(groups[0].items).toHaveLength(1);
  });
});
