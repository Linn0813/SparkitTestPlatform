from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_types import VERSION_TYPES
from app.models.template import VersionWorkflowNodeDef
from app.services.version_workflow_defaults import DEFAULT_VERSION_WORKFLOW_BY_TYPE


def def_lane_indexes(d: VersionWorkflowNodeDef) -> list[int]:
    if d.lane_indexes:
        return sorted(set(int(i) for i in d.lane_indexes))
    return [d.lane_index]


def sync_lane_fields(row: VersionWorkflowNodeDef) -> None:
    indexes = def_lane_indexes(row)
    row.lane_indexes = indexes
    row.lane_index = indexes[0] if indexes else 0


def validate_lane_indexes(lane_indexes: list[int]) -> None:
    if not lane_indexes:
        raise ValueError("至少选择一个阶段列")
    if any(i < 0 for i in lane_indexes):
        raise ValueError("阶段列不能为负数")
    if len(lane_indexes) != len(set(lane_indexes)):
        raise ValueError("阶段列不能重复")


async def load_project_version_workflow_defs(
    db: AsyncSession,
    project_id: str,
    version_type: str,
) -> list[VersionWorkflowNodeDef]:
    result = await db.execute(
        select(VersionWorkflowNodeDef)
        .where(
            VersionWorkflowNodeDef.project_id == project_id,
            VersionWorkflowNodeDef.version_type == version_type,
        )
        .order_by(VersionWorkflowNodeDef.lane_index, VersionWorkflowNodeDef.sort_in_lane)
    )
    return list(result.scalars().all())


async def ensure_project_version_workflow_defs(
    db: AsyncSession,
    project_id: str,
    version_type: str | None = None,
) -> list[VersionWorkflowNodeDef]:
    types_to_seed = [version_type] if version_type else list(VERSION_TYPES)
    for vtype in types_to_seed:
        existing = await load_project_version_workflow_defs(db, project_id, vtype)
        if existing:
            continue
        defaults = DEFAULT_VERSION_WORKFLOW_BY_TYPE.get(vtype, [])
        for item in defaults:
            row = VersionWorkflowNodeDef(
                project_id=project_id,
                version_type=vtype,
                **item,
            )
            sync_lane_fields(row)
            db.add(row)
        await db.flush()
    if version_type:
        return await load_project_version_workflow_defs(db, project_id, version_type)
    result: list[VersionWorkflowNodeDef] = []
    for vtype in VERSION_TYPES:
        result.extend(await load_project_version_workflow_defs(db, project_id, vtype))
    return result


def build_lanes(defs: list[VersionWorkflowNodeDef]) -> list[list[VersionWorkflowNodeDef]]:
    by_lane: dict[int, list[VersionWorkflowNodeDef]] = defaultdict(list)
    for d in defs:
        for lane in def_lane_indexes(d):
            if d not in by_lane[lane]:
                by_lane[lane].append(d)
    lanes: list[list[VersionWorkflowNodeDef]] = []
    for lane_idx in sorted(by_lane.keys()):
        lane = sorted(by_lane[lane_idx], key=lambda x: x.sort_in_lane)
        lanes.append(lane)
    return lanes


def _lanes_by_number(defs: list[VersionWorkflowNodeDef]) -> dict[int, list[VersionWorkflowNodeDef]]:
    by_lane: dict[int, list[VersionWorkflowNodeDef]] = defaultdict(list)
    for d in defs:
        for lane in def_lane_indexes(d):
            if d not in by_lane[lane]:
                by_lane[lane].append(d)
    return {lane: sorted(nodes, key=lambda x: x.sort_in_lane) for lane, nodes in by_lane.items()}


def _track_predecessor_from_map(
    lanes_map: dict[int, list[VersionWorkflowNodeDef]], lane_num: int, sort_in_lane: int
) -> str | None:
    for i in range(lane_num - 1, -1, -1):
        lane = lanes_map.get(i)
        if not lane:
            continue
        for d in lane:
            if d.sort_in_lane == sort_in_lane:
                return d.node_key
    for i in range(lane_num - 1, -1, -1):
        lane = lanes_map.get(i)
        if lane and len(lane) == 1:
            return lane[0].node_key
    return None


def _live_prerequisites_from_map(
    lanes_map: dict[int, list[VersionWorkflowNodeDef]], live_lane: int
) -> tuple[str, ...]:
    tracks: set[int] = set()
    for lane_num in sorted(lanes_map.keys()):
        if lane_num >= live_lane:
            break
        for d in lanes_map[lane_num]:
            tracks.add(d.sort_in_lane)
    deps: list[str] = []
    for track in sorted(tracks):
        terminal: str | None = None
        for lane_num in sorted((n for n in lanes_map.keys() if n < live_lane), reverse=True):
            for d in lanes_map[lane_num]:
                if d.sort_in_lane == track:
                    terminal = d.node_key
                    break
            if terminal:
                break
        if terminal:
            deps.append(terminal)
    return tuple(deps)


def compute_prerequisites(defs: list[VersionWorkflowNodeDef]) -> dict[str, tuple[str, ...]]:
    lanes_map = _lanes_by_number(defs)
    live_lane: int | None = None
    for d in defs:
        if d.node_key == "live":
            live_lane = min(def_lane_indexes(d))
            break

    prereqs: dict[str, tuple[str, ...]] = {}
    for d in defs:
        if d.node_key == "live" and live_lane is not None:
            prereqs[d.node_key] = _live_prerequisites_from_map(lanes_map, live_lane)
            continue
        min_lane = min(def_lane_indexes(d))
        pred = _track_predecessor_from_map(lanes_map, min_lane, d.sort_in_lane)
        prereqs[d.node_key] = (pred,) if pred else ()
    return prereqs


def compute_reopen_set(defs: list[VersionWorkflowNodeDef], node_key: str) -> set[str]:
    prereqs = compute_prerequisites(defs)
    result = {node_key}
    queue = [node_key]
    while queue:
        cur = queue.pop()
        for key, pre in prereqs.items():
            if key not in result and cur in pre:
                result.add(key)
                queue.append(key)
    return result


def label_for_node(defs: list[VersionWorkflowNodeDef], node_key: str) -> str:
    for d in defs:
        if d.node_key == node_key:
            return d.label
    return node_key


def ordered_node_keys(defs: list[VersionWorkflowNodeDef]) -> list[str]:
    keys: list[str] = []
    for lane in build_lanes(defs):
        for d in lane:
            keys.append(d.node_key)
    return keys
