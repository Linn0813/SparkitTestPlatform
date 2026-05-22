from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.public_url import build_bug_detail_url
from app.models.bug import Bug
from app.models.project import Project
from app.models.template import BugStatus, ProjectIntegration
from app.models.user import User
from app.models.wecom_rule import BugWecomNotifyRule
from app.services.links import get_bug_follower_ids
from app.services.wecom import send_wecom_text
from app.services.wecom_rule_utils import rule_matches_transition, rule_transition_keys

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

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
    def repl(match: re.Match[str]) -> str:
        return mapping.get(match.group(1), match.group(0))

    return _PLACEHOLDER_RE.sub(repl, tpl)


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


def _is_phone_number(value: str) -> bool:
    s = value.strip().lstrip("+").replace(" ", "").replace("-", "")
    return bool(s) and s.isdigit() and len(s) >= 7


def _normalize_mobile(value: str) -> str:
    return value.strip().lstrip("+").replace(" ", "").replace("-", "")


async def _build_mentions(
    db: AsyncSession, user_ids: list[str]
) -> tuple[str, list[str], list[str], int]:
    """
    组装 @ 策略（按用户）：
    - 有手机号：走 mentioned_mobile_list（企微官方方式，不在正文重复 @）
    - 有 userid：正文 <@userid>（可选，兼容少数已填账号的用户）
    - 均未绑定：正文纯文本 @姓名 作提示
    返回 (正文前缀, mentioned_mobiles, 未绑定姓名, 成功 @ 人数)
    """
    prefix_parts: list[str] = []
    mobiles: list[str] = []
    unbound: list[str] = []
    mention_count = 0

    for uid in user_ids:
        u = await db.get(User, uid)
        if not u:
            continue
        mobile_raw = (u.wecom_mobile or "").strip()
        userid_raw = (u.wecom_userid or "").strip()
        if mobile_raw and _is_phone_number(mobile_raw):
            mobiles.append(_normalize_mobile(mobile_raw))
            mention_count += 1
        elif userid_raw:
            prefix_parts.append(f"<@{userid_raw}>")
            mention_count += 1
        elif mobile_raw:
            prefix_parts.append(f"<@{mobile_raw}>")
            mention_count += 1
        else:
            if u.name:
                prefix_parts.append(f"@{u.name}")
            unbound.append(u.name or uid)

    prefix = (" ".join(prefix_parts) + "\n") if prefix_parts else ""
    return prefix, mobiles, unbound, mention_count


async def _build_context(
    db: AsyncSession,
    bug: Bug,
    follower_ids: list[str],
    *,
    from_label: str | None = None,
    to_label: str | None = None,
    project_public_url: str | None = None,
) -> dict[str, str]:
    project = await db.get(Project, bug.project_id)
    reporter = await db.get(User, bug.reporter_id)
    link = build_bug_detail_url(bug.id, project_url=project_public_url)
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
) -> int | None:
    """发送群通知并 @ 对应成员。返回 None 表示未发送；否则为成功 @ 的人数。"""
    if not await is_wecom_configured(db, bug.project_id):
        return None

    integ_q = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == bug.project_id)
    )
    integ = integ_q.scalar_one_or_none()
    if not integ or not integ.wecom_webhook_url:
        return None

    follower_ids = await get_bug_follower_ids(db, bug.id)
    target_ids = _collect_user_ids_for_roles(bug, follower_ids, roles)

    ctx = await _build_context(
        db,
        bug,
        follower_ids,
        from_label=from_label,
        to_label=to_label,
        project_public_url=integ.app_public_url,
    )
    content = _safe_template_render(template, ctx)
    mention_count = 0
    if target_ids:
        prefix, mentioned_mobiles, unbound_names, mention_count = await _build_mentions(
            db, target_ids
        )
        if prefix:
            content = prefix + content
        if unbound_names:
            logger.warning(
                "WeCom notify: target(s) have no wecom mobile bound (bug=%s, names=%s)",
                bug.id,
                "、".join(unbound_names),
            )
    else:
        mentioned_mobiles = []
    ok = await send_wecom_text(
        integ.wecom_webhook_url,
        content,
        mentioned_mobiles=mentioned_mobiles or None,
    )
    if not ok:
        return None
    return mention_count if target_ids else 0


async def notify_bug_created(db: AsyncSession, bug: Bug) -> int | None:
    if not await is_wecom_configured(db, bug.project_id):
        return None

    result = await db.execute(
        select(BugWecomNotifyRule).where(
            BugWecomNotifyRule.project_id == bug.project_id,
            BugWecomNotifyRule.kind == "create",
            BugWecomNotifyRule.enabled.is_(True),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return None

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
) -> int | None:
    if not from_key:
        return None
    if not await is_wecom_configured(db, bug.project_id):
        return None

    result = await db.execute(
        select(BugWecomNotifyRule)
        .where(
            BugWecomNotifyRule.project_id == bug.project_id,
            BugWecomNotifyRule.kind == "transition",
            BugWecomNotifyRule.enabled.is_(True),
        )
        .order_by(BugWecomNotifyRule.created_at)
    )
    rule = None
    for candidate in result.scalars().all():
        from_keys, to_keys = rule_transition_keys(candidate)
        if rule_matches_transition(from_key, to_key, from_keys, to_keys):
            rule = candidate
            break
    if not rule:
        return None

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
