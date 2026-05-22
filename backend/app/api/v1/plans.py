from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case as sql_case
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_tester
from app.models.case import TestCase
from app.models.plan import ExecuteResult, PlanCase, PlanCaseResult, PlanStatus, TestPlan
from app.models.project_version import ProjectVersion
from app.models.requirement import BugPlanLink
from app.schemas.case import TestCaseOut
from app.services.case_module_paths import build_module_path_map, load_project_modules
from app.services.serializers import case_out as serialize_case
from app.schemas.version import VersionBrief
from app.services.versions import validate_version_id
from app.schemas.plan import (
    PlanCaseAdd,
    PlanCaseOut,
    PlanCaseResultOut,
    PlanCaseResultUpdate,
    PlanStatsOut,
    TestPlanCreate,
    TestPlanListItemOut,
    TestPlanOut,
    TestPlanUpdate,
)

router = APIRouter(prefix="/plans", tags=["plans"])


async def _plan_out(plan: TestPlan, db: AsyncSession) -> TestPlanOut:
    version = None
    if plan.version_id:
        v = await db.get(ProjectVersion, plan.version_id)
        if v:
            version = VersionBrief(id=v.id, num=v.num, name=v.name)
    base = TestPlanOut.model_validate(plan)
    return base.model_copy(update={"version": version})


async def _plan_stats_by_plan_id(db: AsyncSession, project_id: str) -> dict[str, dict[str, int]]:
    """Aggregate case counts per plan for list view."""
    rows = await db.execute(
        select(
            PlanCase.plan_id,
            func.count(PlanCase.id).label("case_total"),
            func.sum(
                sql_case((PlanCaseResult.result == ExecuteResult.pass_, 1), else_=0)
            ).label("pass_count"),
            func.sum(
                sql_case((PlanCaseResult.result == ExecuteResult.fail, 1), else_=0)
            ).label("fail_count"),
            func.sum(
                sql_case((PlanCaseResult.result == ExecuteResult.block, 1), else_=0)
            ).label("block_count"),
            func.sum(
                sql_case((PlanCaseResult.result == ExecuteResult.skip, 1), else_=0)
            ).label("skip_count"),
            func.sum(
                sql_case(
                    (
                        (PlanCaseResult.result == ExecuteResult.not_run)
                        | (PlanCaseResult.result.is_(None)),
                        1,
                    ),
                    else_=0,
                )
            ).label("not_run_count"),
        )
        .select_from(PlanCase)
        .join(TestPlan, TestPlan.id == PlanCase.plan_id)
        .outerjoin(PlanCaseResult, PlanCaseResult.plan_case_id == PlanCase.id)
        .where(TestPlan.project_id == project_id)
        .group_by(PlanCase.plan_id)
    )
    out: dict[str, dict[str, int]] = {}
    for row in rows.all():
        plan_id = row.plan_id
        case_total = int(row.case_total or 0)
        pass_count = int(row.pass_count or 0)
        fail_count = int(row.fail_count or 0)
        block_count = int(row.block_count or 0)
        skip_count = int(row.skip_count or 0)
        not_run_count = int(row.not_run_count or 0)
        executed = case_total - not_run_count
        pass_rate = round((pass_count / executed * 100) if executed else 0.0, 1)
        out[plan_id] = {
            "case_total": case_total,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "block_count": block_count,
            "skip_count": skip_count,
            "not_run_count": not_run_count,
            "pass_rate": pass_rate,
        }
    return out


def _plan_case_out(
    pc: PlanCase,
    case_out: TestCaseOut | None,
    result: PlanCaseResult | None,
) -> PlanCaseOut:
    return PlanCaseOut(
        id=pc.id,
        plan_id=pc.plan_id,
        case_id=pc.case_id,
        sort=pc.sort,
        case=case_out,
        result=PlanCaseResultOut.model_validate(result) if result else None,
    )


async def _plan_case_row_out(
    db: AsyncSession,
    pc: PlanCase,
    case: TestCase | None,
    result: PlanCaseResult | None,
    path_map: dict[str, str],
) -> PlanCaseOut:
    serialized: TestCaseOut | None = None
    if case and not case.deleted:
        serialized = await serialize_case(case, db, module_path=path_map.get(case.module_id))
    return _plan_case_out(pc, serialized, result)


@router.get("", response_model=list[TestPlanListItemOut])
async def list_plans(
    version_id: Optional[str] = None,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TestPlan).where(TestPlan.project_id == ctx.project_id)
    if version_id is not None:
        stmt = stmt.where(TestPlan.version_id == version_id)
    result = await db.execute(stmt.order_by(TestPlan.updated_at.desc()))
    plans = list(result.scalars().all())
    stats_map = await _plan_stats_by_plan_id(db, ctx.project_id)
    out: list[TestPlanListItemOut] = []
    for p in plans:
        base = await _plan_out(p, db)
        agg = stats_map.get(p.id, {})
        out.append(
            TestPlanListItemOut(
                **base.model_dump(),
                case_total=agg.get("case_total", 0),
                pass_count=agg.get("pass_count", 0),
                fail_count=agg.get("fail_count", 0),
                block_count=agg.get("block_count", 0),
                skip_count=agg.get("skip_count", 0),
                not_run_count=agg.get("not_run_count", 0),
                pass_rate=agg.get("pass_rate", 0.0),
            )
        )
    return out


@router.post("", response_model=TestPlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: TestPlanCreate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    try:
        await validate_version_id(db, ctx.project_id, body.version_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    plan = TestPlan(
        project_id=ctx.project_id,
        name=body.name,
        status=body.status,
        description=body.description,
        version_id=body.version_id,
        owner_id=ctx.user.id,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return await _plan_out(plan, db)


@router.get("/{plan_id}", response_model=TestPlanOut)
async def get_plan(
    plan_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(TestPlan, plan_id)
    if not plan or plan.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return await _plan_out(plan, db)


@router.patch("/{plan_id}", response_model=TestPlanOut)
async def update_plan(
    plan_id: str,
    body: TestPlanUpdate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(TestPlan, plan_id)
    if not plan or plan.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    data = body.model_dump(exclude_unset=True)
    if "version_id" in data:
        try:
            await validate_version_id(db, ctx.project_id, data.get("version_id"))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    for k, v in data.items():
        setattr(plan, k, v)
    await db.flush()
    await db.refresh(plan)
    return await _plan_out(plan, db)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(TestPlan, plan_id)
    if not plan or plan.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    pc_ids_sq = select(PlanCase.id).where(PlanCase.plan_id == plan_id)
    await db.execute(delete(PlanCaseResult).where(PlanCaseResult.plan_case_id.in_(pc_ids_sq)))
    await db.execute(delete(PlanCase).where(PlanCase.plan_id == plan_id))
    await db.execute(delete(BugPlanLink).where(BugPlanLink.plan_id == plan_id))
    await db.delete(plan)


@router.get("/{plan_id}/cases", response_model=list[PlanCaseOut])
async def list_plan_cases(
    plan_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(TestPlan, plan_id)
    if not plan or plan.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    pcs = await db.execute(select(PlanCase).where(PlanCase.plan_id == plan_id).order_by(PlanCase.sort))
    modules = await load_project_modules(db, plan.project_id)
    path_map = build_module_path_map(modules)
    out: list[PlanCaseOut] = []
    for pc in pcs.scalars().all():
        case = await db.get(TestCase, pc.case_id)
        res_q = await db.execute(select(PlanCaseResult).where(PlanCaseResult.plan_case_id == pc.id))
        out.append(await _plan_case_row_out(db, pc, case, res_q.scalar_one_or_none(), path_map))
    return out


@router.post("/{plan_id}/cases", response_model=list[PlanCaseOut])
async def add_plan_cases(
    plan_id: str,
    body: PlanCaseAdd,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(TestPlan, plan_id)
    if not plan or plan.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    max_sort = await db.execute(select(func.max(PlanCase.sort)).where(PlanCase.plan_id == plan_id))
    base = max_sort.scalar() or 0
    modules = await load_project_modules(db, plan.project_id)
    path_map = build_module_path_map(modules)
    created: list[PlanCaseOut] = []
    for i, cid in enumerate(body.case_ids):
        case = await db.get(TestCase, cid)
        if not case or case.project_id != ctx.project_id or case.deleted:
            continue
        existing = await db.execute(
            select(PlanCase).where(PlanCase.plan_id == plan_id, PlanCase.case_id == cid)
        )
        if existing.scalar_one_or_none():
            continue
        pc = PlanCase(plan_id=plan_id, case_id=cid, sort=base + i + 1)
        db.add(pc)
        await db.flush()
        result_row = PlanCaseResult(plan_case_id=pc.id, result=ExecuteResult.not_run)
        db.add(result_row)
        await db.flush()
        created.append(await _plan_case_row_out(db, pc, case, result_row, path_map))
    return created


@router.delete("/{plan_id}/cases/{plan_case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_plan_case(
    plan_id: str,
    plan_case_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    pc = await db.get(PlanCase, plan_case_id)
    if not pc or pc.plan_id != plan_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan case not found")
    res = await db.execute(select(PlanCaseResult).where(PlanCaseResult.plan_case_id == pc.id))
    r = res.scalar_one_or_none()
    if r:
        await db.delete(r)
    await db.delete(pc)


@router.post("/{plan_id}/results", response_model=PlanCaseResultOut)
async def update_result(
    plan_id: str,
    body: PlanCaseResultUpdate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    pc = await db.get(PlanCase, body.plan_case_id)
    if not pc or pc.plan_id != plan_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan case not found")
    res_q = await db.execute(select(PlanCaseResult).where(PlanCaseResult.plan_case_id == pc.id))
    result = res_q.scalar_one_or_none()
    if not result:
        result = PlanCaseResult(plan_case_id=pc.id)
        db.add(result)
    result.result = body.result
    result.comment = body.comment
    result.executor_id = ctx.user.id
    result.executed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()
    await db.refresh(result)
    return PlanCaseResultOut.model_validate(result)


@router.get("/{plan_id}/stats", response_model=PlanStatsOut)
async def plan_stats(
    plan_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(TestPlan, plan_id)
    if not plan or plan.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    pcs = await db.execute(select(PlanCase).where(PlanCase.plan_id == plan_id))
    total = 0
    counts = {ExecuteResult.not_run: 0, ExecuteResult.pass_: 0, ExecuteResult.fail: 0, ExecuteResult.block: 0, ExecuteResult.skip: 0}
    for pc in pcs.scalars().all():
        total += 1
        res_q = await db.execute(select(PlanCaseResult).where(PlanCaseResult.plan_case_id == pc.id))
        r = res_q.scalar_one_or_none()
        key = r.result if r else ExecuteResult.not_run
        counts[key] = counts.get(key, 0) + 1
    executed = total - counts[ExecuteResult.not_run]
    pass_rate = (counts[ExecuteResult.pass_] / executed * 100) if executed else 0.0
    return PlanStatsOut(
        total=total,
        not_run=counts[ExecuteResult.not_run],
        pass_count=counts[ExecuteResult.pass_],
        fail_count=counts[ExecuteResult.fail],
        block_count=counts[ExecuteResult.block],
        skip_count=counts[ExecuteResult.skip],
        pass_rate=round(pass_rate, 1),
    )
