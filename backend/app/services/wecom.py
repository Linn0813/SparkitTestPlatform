from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_wecom_text(
    webhook_url: str,
    content: str,
    *,
    mentioned_userids: list[str] | None = None,
    mentioned_mobiles: list[str] | None = None,
) -> bool:
    text_body: dict = {"content": content}
    if mentioned_userids:
        text_body["mentioned_list"] = mentioned_userids
    if mentioned_mobiles:
        text_body["mentioned_mobile_list"] = mentioned_mobiles
    payload = {"msgtype": "text", "text": text_body}
    try:
        async with httpx.AsyncClient(timeout=settings.wecom_request_timeout) as client:
            resp = await client.post(webhook_url, json=payload)
            data = resp.json()
            if resp.status_code == 200 and data.get("errcode") == 0:
                return True
            logger.warning("WeCom text webhook failed: %s %s", resp.status_code, data)
    except Exception as e:
        logger.exception("WeCom text webhook error: %s", e)
    return False


async def send_wecom_markdown(webhook_url: str, content: str) -> bool:
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    try:
        async with httpx.AsyncClient(timeout=settings.wecom_request_timeout) as client:
            resp = await client.post(webhook_url, json=payload)
            data = resp.json()
            if resp.status_code == 200 and data.get("errcode") == 0:
                return True
            logger.warning("WeCom webhook failed: %s %s", resp.status_code, data)
    except Exception as e:
        logger.exception("WeCom webhook error: %s", e)
    return False


def build_bug_status_message(
    bug_num: int,
    title: str,
    from_label: str | None,
    to_label: str,
    assignee_name: str | None,
    project_name: str,
    bug_id: str,
) -> str:
    link = f"{settings.app_public_url}/bugs?highlight={bug_id}"
    lines = [
        f"### 缺陷状态变更 {bug_num}",
        f"> **项目**: {project_name}",
        f"> **标题**: {title}",
        f"> **状态**: {from_label or '-'} → **{to_label}**",
    ]
    if assignee_name:
        lines.append(f"> **处理人**: {assignee_name}")
    lines.append(f"> [查看详情]({link})")
    lines.append(f"\n<font color=\"comment\">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</font>")
    return "\n".join(lines)
