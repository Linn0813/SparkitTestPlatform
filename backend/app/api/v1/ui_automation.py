from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_tester
from app.models.ui_automation import (
    MobileApp,
    MobilePlatform,
    UIElement,
    UIRunner,
    UIRunStatus,
    UIStepStatus,
    UITestCase,
    UITestRun,
    UITestStepResult,
)
from app.schemas.ui_automation import (
    MobileAppOut,
    UIElementCreate,
    UIElementOut,
    UIElementUpdate,
    UIRunnerCreate,
    UIRunnerOut,
    UIRunnerWithToken,
    UITestCaseCreate,
    UITestCaseListItem,
    UITestCaseOut,
    UITestCaseUpdate,
    UITestRunCreate,
    UITestRunListItem,
    UITestRunOut,
    UITestStepResultOut,
)
from app.services import minio_storage

router = APIRouter(prefix="/ui-automation", tags=["ui-automation"])

_APK_CONTENT_TYPES = {"application/vnd.android.package-archive", "application/octet-stream"}
_IPA_CONTENT_TYPES = {"application/octet-stream"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _app_storage_key(project_id: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    return f"mobile-apps/{project_id}/{uuid.uuid4()}.{ext}"


def _screenshot_storage_key(run_id: str, step_index: int) -> str:
    return f"ui-screenshots/{run_id}/step-{step_index}.png"


async def _get_case(db: AsyncSession, project_id: str, case_id: str) -> UITestCase:
    case = await db.get(UITestCase, case_id)
    if not case or case.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UI test case not found")
    return case


async def _get_run(db: AsyncSession, project_id: str, run_id: str) -> UITestRun:
    run = await db.get(UITestRun, run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found")
    return run


async def _step_results(db: AsyncSession, run_id: str) -> list[UITestStepResultOut]:
    from app.services.file_storage import build_file_download_url
    rows = await db.execute(
        select(UITestStepResult)
        .where(UITestStepResult.run_id == run_id)
        .order_by(UITestStepResult.step_index)
    )
    results = []
    for r in rows.scalars().all():
        out = UITestStepResultOut.model_validate(r)
        if r.screenshot_key:
            out = out.model_copy(update={"screenshot_url": build_file_download_url(r.screenshot_key)})
        results.append(out)
    return results


async def _run_out(db: AsyncSession, run: UITestRun) -> UITestRunOut:
    from app.services.file_storage import build_file_download_url
    steps = await _step_results(db, run.id)
    base = UITestRunOut.model_validate(run)
    video_url = build_file_download_url(run.video_key) if run.video_key else None
    return base.model_copy(update={"step_results": steps, "video_url": video_url})


# ---------------------------------------------------------------------------
# 用例 CRUD
# ---------------------------------------------------------------------------

@router.get("/cases", response_model=list[UITestCaseListItem])
async def list_ui_cases(
    platform: Optional[MobilePlatform] = None,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UITestCase).where(UITestCase.project_id == ctx.project_id)
    if platform:
        stmt = stmt.where(UITestCase.platform == platform)
    result = await db.execute(stmt.order_by(UITestCase.updated_at.desc()))
    return [UITestCaseListItem.model_validate(c) for c in result.scalars().all()]


@router.post("/cases", response_model=UITestCaseOut, status_code=status.HTTP_201_CREATED)
async def create_ui_case(
    body: UITestCaseCreate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    case = UITestCase(
        project_id=ctx.project_id,
        name=body.name,
        platform=body.platform,
        description=body.description,
        selectors=body.selectors,
        steps=body.steps,
        assertion=body.assertion,
        created_by=ctx.user.id,
    )
    db.add(case)
    await db.flush()
    await db.refresh(case)
    return UITestCaseOut.model_validate(case)


@router.get("/cases/{case_id}", response_model=UITestCaseOut)
async def get_ui_case(
    case_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    return UITestCaseOut.model_validate(await _get_case(db, ctx.project_id, case_id))


@router.patch("/cases/{case_id}", response_model=UITestCaseOut)
async def update_ui_case(
    case_id: str,
    body: UITestCaseUpdate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    case = await _get_case(db, ctx.project_id, case_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(case, k, v)
    await db.flush()
    await db.refresh(case)
    return UITestCaseOut.model_validate(case)


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ui_case(
    case_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    case = await _get_case(db, ctx.project_id, case_id)
    await db.delete(case)


# ---------------------------------------------------------------------------
# App 包管理
# ---------------------------------------------------------------------------

@router.get("/apps", response_model=list[MobileAppOut])
async def list_mobile_apps(
    platform: Optional[MobilePlatform] = None,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MobileApp).where(MobileApp.project_id == ctx.project_id)
    if platform:
        stmt = stmt.where(MobileApp.platform == platform)
    result = await db.execute(stmt.order_by(MobileApp.uploaded_at.desc()))
    return [MobileAppOut.model_validate(a) for a in result.scalars().all()]


@router.post("/apps", response_model=MobileAppOut, status_code=status.HTTP_201_CREATED)
async def upload_mobile_app(
    platform: MobilePlatform,
    version: str,
    file: UploadFile = File(...),
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "app.bin"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if platform == MobilePlatform.android and ext != "apk":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Android app must be an .apk file")
    if platform == MobilePlatform.ios and ext != "ipa":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="iOS app must be an .ipa file")

    data = await file.read()
    storage_key = _app_storage_key(ctx.project_id, filename)
    content_type = file.content_type or "application/octet-stream"
    await minio_storage.put_object(storage_key, data, content_type)

    app = MobileApp(
        project_id=ctx.project_id,
        platform=platform,
        version=version.strip(),
        filename=filename,
        storage_key=storage_key,
        size=len(data),
        uploaded_by=ctx.user.id,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)
    return MobileAppOut.model_validate(app)


@router.delete("/apps/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mobile_app(
    app_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(MobileApp, app_id)
    if not app or app.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    await minio_storage.delete_object(app.storage_key)
    await db.delete(app)


# ---------------------------------------------------------------------------
# Runner 管理
# ---------------------------------------------------------------------------

@router.get("/runners", response_model=list[UIRunnerOut])
async def list_runners(
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UIRunner).where(UIRunner.project_id == ctx.project_id).order_by(UIRunner.created_at.desc())
    )
    return [UIRunnerOut.model_validate(r) for r in result.scalars().all()]


@router.post("/runners", response_model=UIRunnerWithToken, status_code=status.HTTP_201_CREATED)
async def create_runner(
    body: UIRunnerCreate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    token = secrets.token_hex(32)
    runner = UIRunner(
        project_id=ctx.project_id,
        name=body.name,
        platform=body.platform,
        token=token,
    )
    db.add(runner)
    await db.flush()
    await db.refresh(runner)
    out = UIRunnerWithToken.model_validate(runner)
    return out.model_copy(update={"token": token})


@router.delete("/runners/{runner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_runner(
    runner_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    runner = await db.get(UIRunner, runner_id)
    if not runner or runner.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Runner not found")
    await db.delete(runner)


# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------

@router.post("/runs", response_model=UITestRunOut, status_code=status.HTTP_201_CREATED)
async def trigger_run(
    body: UITestRunCreate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    case = await _get_case(db, ctx.project_id, body.case_id)
    app = await db.get(MobileApp, body.app_id)
    if not app or app.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    if app.platform != case.platform:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"App platform ({app.platform}) does not match case platform ({case.platform})",
        )

    run = UITestRun(
        project_id=ctx.project_id,
        case_id=body.case_id,
        app_id=body.app_id,
        status=UIRunStatus.pending,
        triggered_by=ctx.user.id,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return await _run_out(db, run)


@router.get("/runs", response_model=list[UITestRunListItem])
async def list_runs(
    case_id: Optional[str] = None,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UITestRun).where(UITestRun.project_id == ctx.project_id)
    if case_id:
        stmt = stmt.where(UITestRun.case_id == case_id)
    result = await db.execute(stmt.order_by(UITestRun.created_at.desc()))
    return [UITestRunListItem.model_validate(r) for r in result.scalars().all()]


@router.get("/runs/{run_id}", response_model=UITestRunOut)
async def get_run(
    run_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    run = await _get_run(db, ctx.project_id, run_id)
    return await _run_out(db, run)


# ---------------------------------------------------------------------------
# 元素库
# ---------------------------------------------------------------------------

@router.get("/elements", response_model=list[UIElementOut])
async def list_elements(
    platform: Optional[MobilePlatform] = None,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UIElement).where(UIElement.project_id == ctx.project_id)
    if platform:
        stmt = stmt.where(UIElement.platform == platform)
    result = await db.execute(stmt.order_by(UIElement.name))
    return [UIElementOut.model_validate(e) for e in result.scalars().all()]


@router.post("/elements", response_model=UIElementOut, status_code=status.HTTP_201_CREATED)
async def create_element(
    body: UIElementCreate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    el = UIElement(
        project_id=ctx.project_id,
        platform=body.platform,
        name=body.name,
        selector=body.selector,
        description=body.description,
        created_by=ctx.user.id,
    )
    db.add(el)
    await db.flush()
    await db.refresh(el)
    return UIElementOut.model_validate(el)


@router.patch("/elements/{element_id}", response_model=UIElementOut)
async def update_element(
    element_id: str,
    body: UIElementUpdate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    el = await db.get(UIElement, element_id)
    if not el or el.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(el, k, v)
    await db.flush()
    await db.refresh(el)
    return UIElementOut.model_validate(el)


@router.delete("/elements/{element_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_element(
    element_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    el = await db.get(UIElement, element_id)
    if not el or el.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element not found")
    await db.delete(el)


# ---------------------------------------------------------------------------
# Runner 专用接口（用 token 鉴权，不走 JWT）
# ---------------------------------------------------------------------------

async def _auth_runner(
    runner_token: str,
    db: AsyncSession,
) -> UIRunner:
    result = await db.execute(select(UIRunner).where(UIRunner.token == runner_token))
    runner = result.scalar_one_or_none()
    if not runner:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid runner token")
    return runner


@router.post("/runner/heartbeat")
async def runner_heartbeat(
    runner_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Runner 每 30s 调用一次，保持在线状态。"""
    runner = await _auth_runner(runner_token, db)
    runner.last_heartbeat_at = _now()
    await db.flush()
    return {"ok": True}


@router.get("/runner/next-job")
async def runner_poll_job(
    runner_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Runner 轮询：领取一个 pending 任务。返回 null 表示暂无任务。"""
    runner = await _auth_runner(runner_token, db)
    runner.last_heartbeat_at = _now()

    result = await db.execute(
        select(UITestRun)
        .where(
            UITestRun.status == UIRunStatus.pending,
            UITestRun.project_id == runner.project_id,
        )
        .order_by(UITestRun.created_at.asc())
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if not run:
        return {"job": None}

    run.status = UIRunStatus.running
    run.runner_id = runner.id
    run.started_at = _now()
    await db.flush()

    case = await db.get(UITestCase, run.case_id)
    app = await db.get(MobileApp, run.app_id)

    download_url = minio_storage.presigned_get_url(app.storage_key, expires_seconds=3600)

    return {
        "job": {
            "run_id": run.id,
            "case": {
                "selectors": case.selectors,
                "steps": case.steps,
                "assertion": case.assertion,
            },
            "app": {
                "filename": app.filename,
                "platform": app.platform,
                "download_url": download_url,
            },
        }
    }


@router.post("/runner/step-result")
async def runner_report_step(
    runner_token: str,
    run_id: str,
    step_index: int,
    step_status: UIStepStatus,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    screenshot: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Runner 每完成一步后上报结果。"""
    runner = await _auth_runner(runner_token, db)

    run = await db.get(UITestRun, run_id)
    if not run or run.runner_id != runner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Run not assigned to this runner")

    screenshot_key = None
    if screenshot:
        data = await screenshot.read()
        screenshot_key = _screenshot_storage_key(run_id, step_index)
        await minio_storage.put_object(screenshot_key, data, "image/png")

    existing = await db.execute(
        select(UITestStepResult).where(
            UITestStepResult.run_id == run_id,
            UITestStepResult.step_index == step_index,
        )
    )
    step_result = existing.scalar_one_or_none()
    if step_result:
        step_result.status = step_status
        step_result.error_message = error_message
        step_result.duration_ms = duration_ms
        step_result.screenshot_key = screenshot_key
        step_result.executed_at = _now()
    else:
        step_result = UITestStepResult(
            run_id=run_id,
            step_index=step_index,
            status=step_status,
            error_message=error_message,
            duration_ms=duration_ms,
            screenshot_key=screenshot_key,
            executed_at=_now(),
        )
        db.add(step_result)

    await db.flush()
    return {"ok": True}


@router.post("/runner/finish-job")
async def runner_finish_job(
    runner_token: str,
    run_id: str,
    final_status: UIRunStatus,
    error_message: Optional[str] = None,
    video: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Runner 执行完成后上报最终状态，可附带录屏视频。"""
    runner = await _auth_runner(runner_token, db)

    run = await db.get(UITestRun, run_id)
    if not run or run.runner_id != runner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Run not assigned to this runner")
    if final_status not in (UIRunStatus.passed, UIRunStatus.failed, UIRunStatus.error):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid final status")

    if video:
        data = await video.read()
        video_key = f"ui-videos/{run_id}/recording.mp4"
        await minio_storage.put_object(video_key, data, "video/mp4")
        run.video_key = video_key

    run.status = final_status
    run.error_message = error_message
    run.finished_at = _now()
    await db.flush()
    return {"ok": True}
