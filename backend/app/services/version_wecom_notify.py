from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_nodes import NODE_TO_WECOM_EVENT, VERSION_NODE_LABELS
from app.core.public_url import build_version_detail_url
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.template import ProjectIntegration
from app.models.user import User
from app.models.version_workflow import VersionWecomNotifyRule
from app.services.wecom import send_wecom_text
from app.services.wecom_notify import _build_mentions, _safe_template_render

logger = logging.getLogger(__name__)


async def is_version_wecom_configured(db: AsyncSession, project_id: str) -> bool:
    result = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    integ = result.scalar_one_or_none()
    return bool(
        integ
        and integ.version_wecom_enabled
        and (integ.version_wecom_webhook_url or "").strip()
    )


async def _send_version_wecom(
    db: AsyncSession,
    *,
    project_id: str,
    template: str,
    context: dict[str, str],
    target_ids: list[str],
    log_version_id: str,
) -> int | None:
    if not await is_version_wecom_configured(db, project_id):
        return None

    result = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    integ = result.scalar_one_or_none()
    if not integ or not integ.version_wecom_webhook_url:
        return None

    content = _safe_template_render(template, context)
    mention_count = 0
    if target_ids:
        prefix, mentioned_mobiles, unbound_names, mention_count = await _build_mentions(
            db, target_ids
        )
        if prefix:
            content = prefix + content
        if unbound_names:
            logger.warning(
                "Version WeCom notify: target(s) have no wecom mobile bound (version=%s, names=%s)",
                log_version_id,
                "、".join(unbound_names),
            )
    else:
        mentioned_mobiles = []

    ok = await send_wecom_text(
        integ.version_wecom_webhook_url,
        content,
        mentioned_mobiles=mentioned_mobiles or None,
    )
    if not ok:
        return None
    return mention_count if target_ids else 0


async def notify_version_node_complete(
    db: AsyncSession,
    version: ProjectVersion,
    node_key: str,
    operator_id: str,
) -> int | None:
    event_key = NODE_TO_WECOM_EVENT.get(node_key)
    if not event_key:
        return None

    rule_result = await db.execute(
        select(VersionWecomNotifyRule).where(
            VersionWecomNotifyRule.project_id == version.project_id,
            VersionWecomNotifyRule.event_key == event_key,
            VersionWecomNotifyRule.enabled.is_(True),
        )
    )
    rule = rule_result.scalar_one_or_none()
    if not rule:
        return None

    project = await db.get(Project, version.project_id)
    operator = await db.get(User, operator_id)
    integ_result = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == version.project_id)
    )
    integ = integ_result.scalar_one_or_none()
    project_url = integ.app_public_url if integ else None

    context = {
        "version": version.name,
        "project": project.name if project else "-",
        "node": VERSION_NODE_LABELS.get(node_key, node_key),
        "operator": operator.name if operator else "-",
        "link": build_version_detail_url(version.id, project_url=project_url),
    }

    target_ids = list(rule.notify_user_ids or [])
    return await _send_version_wecom(
        db,
        project_id=version.project_id,
        template=rule.message_template,
        context=context,
        target_ids=target_ids,
        log_version_id=version.id,
    )
