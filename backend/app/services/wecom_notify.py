from __future__ import annotations

from string import Template

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.bug import Bug
from app.models.project import Project
from app.models.template import BugStatus, ProjectIntegration
from app.models.user import User
from app.models.wecom_rule import BugWecomNotifyRule
from app.services.links import get_bug_follower_ids
from app.services.wecom import send_wecom_text

DEFAULT_STATUS_TEMPLATE = (
    "【缺陷 {num}】{title}\n"
    "项目：{project}\n"
    "提出人：{reporter}\n"
    "跟进人：{followers}\n"
    "状态：{from_status} → {to_status}\n"
    "{link}"
)

DEFAULT_CREATE_TEMPLATE = (
    "【新建缺陷 {num}】{title}\n"
    "项目：{project}\n"
    "提出人：{reporter}\n"
    "跟进人：{followers}\n"
    "{link}"
)


def _safe_template_render(tpl: str, mapping: dict[str, str]) -> str:
    try:
        return Template(tpl).safe_substitute(mapping)
    except Exception:
        return tpl


async def _user_names(db: AsyncSession, user_ids: list[str]) -> str:
    if not user_ids:
        return "-"
    names: list[str] = []
    for uid in user_ids:
        u = await db.get(User, uid)
        names.append(u.name if u else uid)
    return "、".join(names)


def _collect_user_ids_for_roles(
    bug: Bug,
    follower_ids: list[str],
    roles: list[str],
) -> list[str]:
    ids: list[str] = []
    if "reporter" in roles and bug.reporter_id:
        ids.append(bug.reporter_id)
    if "followers" in roles:
        ids.extend(follower_ids)
    if "assignee" in roles and bug.assignee_id:
        ids.append(bug.assignee_id)
    seen: set[str] = set()
    out: list[str] = []
    for uid in ids:
        if uid and uid not in seen:
            seen.add(uid)
            out.append(uid)
    return out


async def _resolve_mentions(db: AsyncSession, user_ids: list[str]) -> tuple[list[str], list[str]]:
    userids: list[str] = []
    mobiles: list[str] = []
    for uid in user_ids:
        u = await db.get(User, uid)
        if not u:
            continue
        if u.wecom_userid:
            userids.append(u.wecom_userid)
        elif u.wecom_mobile:
            mobiles.append(u.wecom_mobile)
    return userids, mobiles


async def _build_context(
    db: AsyncSession,
    bug: Bug,
    follower_ids: list[str],
    *,
    from_label: str | None = None,
    to_label: str | None = None,
) -> dict[str, str]:
    project = await db.get(Project, bug.project_id)
    reporter = await db.get(User, bug.reporter_id)
    link = f"{settings.app_public_url}/bugs/{bug.id}"
    return {
        "project": project.name if project else bug.project_id,
        "num": str(bug.num),
        "title": bug.title,
        "from_status": from_label or "-",
        "to_status": to_label or "-",
        "reporter": reporter.name if reporter else "-",
        "followers": await _user_names(db, follower_ids),
        "link": link,
    }


async def is_wecom_configured(db: AsyncSession, project_id: str) -> bool:
    """项目已开启企微且配置了 Webhook 时才发送通知。"""
    integ_q = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    integ = integ_q.scalar_one_or_none()
    return bool(integ and integ.wecom_enabled and (integ.wecom_webhook_url or "").strip())


async def send_bug_wecom_notification(
    db: AsyncSession,
    bug: Bug,
    *,
    template: str,
    roles: list[str],
    from_label: str | None = None,
    to_label: str | None = None,
) -> int:
    """发送群通知并 @ 对应成员。返回成功 @ 的人数（有 userid 或手机号）。"""
    if not await is_wecom_configured(db, bug.project_id):
        return 0

    integ_q = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == bug.project_id)
    )
    integ = integ_q.scalar_one_or_none()
    if not integ or not integ.wecom_webhook_url:
        return 0

    follower_ids = await get_bug_follower_ids(db, bug.id)
    target_ids = _collect_user_ids_for_roles(bug, follower_ids, roles)
    if not target_ids:
        return 0

    ctx = await _build_context(db, bug, follower_ids, from_label=from_label, to_label=to_label)
    content = _safe_template_render(template, ctx)
    mentioned_userids, mentioned_mobiles = await _resolve_mentions(db, target_ids)
    ok = await send_wecom_text(
        integ.wecom_webhook_url,
        content,
        mentioned_userids=mentioned_userids,
        mentioned_mobiles=mentioned_mobiles,
    )
    if not ok:
        return 0
    return len(mentioned_userids) + len(mentioned_mobiles)


async def notify_bug_created(db: AsyncSession, bug: Bug) -> int:
    if not await is_wecom_configured(db, bug.project_id):
        return 0

    result = await db.execute(
        select(BugWecomNotifyRule).where(
            BugWecomNotifyRule.project_id == bug.project_id,
            BugWecomNotifyRule.kind == "create",
            BugWecomNotifyRule.enabled.is_(True),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return 0

    roles = rule.notify_roles if isinstance(rule.notify_roles, list) else ["reporter", "followers"]
    status_row = await db.execute(
        select(BugStatus).where(
            BugStatus.project_id == bug.project_id, BugStatus.key == bug.status_key
        )
    )
    status = status_row.scalar_one_or_none()
    to_label = status.label if status else bug.status_key
    return await send_bug_wecom_notification(
        db,
        bug,
        template=rule.message_template,
        roles=roles,
        from_label="-",
        to_label=to_label,
    )


async def notify_bug_status_change(
    db: AsyncSession,
    bug: Bug,
    from_key: str | None,
    to_key: str,
) -> int:
    if not from_key:
        return 0
    if not await is_wecom_configured(db, bug.project_id):
        return 0

    result = await db.execute(
        select(BugWecomNotifyRule).where(
            BugWecomNotifyRule.project_id == bug.project_id,
            BugWecomNotifyRule.kind == "transition",
            BugWecomNotifyRule.from_status_key == from_key,
            BugWecomNotifyRule.to_status_key == to_key,
            BugWecomNotifyRule.enabled.is_(True),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return 0

    from_label = None
    fr = await db.execute(
        select(BugStatus).where(BugStatus.project_id == bug.project_id, BugStatus.key == from_key)
    )
    f = fr.scalar_one_or_none()
    from_label = f.label if f else from_key

    status_row = await db.execute(
        select(BugStatus).where(BugStatus.project_id == bug.project_id, BugStatus.key == to_key)
    )
    target = status_row.scalar_one_or_none()
    to_label = target.label if target else to_key

    roles = rule.notify_roles if isinstance(rule.notify_roles, list) else ["reporter", "followers"]
    return await send_bug_wecom_notification(
        db,
        bug,
        template=rule.message_template,
        roles=roles,
        from_label=from_label,
        to_label=to_label,
    )
