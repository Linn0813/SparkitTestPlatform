from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.public_url import build_bug_detail_url

logger = logging.getLogger(__name__)

_WECOM_ERRMSG_ZH: dict[int, str] = {
    93000: "Webhook 地址无效，请从企微群机器人设置中复制完整 URL",
    93004: "机器人不在群内或已被移除",
    93008: "消息内容不符合企微格式要求",
    93017: "机器人被停用，请在企微群中重新启用",
}


@dataclass(frozen=True)
class WecomSendResult:
    ok: bool
    error: str | None = None


def _format_wecom_error(status_code: int, data: dict) -> str:
    errcode = data.get("errcode")
    errmsg = data.get("errmsg") or str(data)
    if isinstance(errcode, int) and errcode in _WECOM_ERRMSG_ZH:
        return _WECOM_ERRMSG_ZH[errcode]
    if isinstance(errcode, int):
        return f"企微返回 errcode={errcode}: {errmsg}"
    return f"企微请求失败 HTTP {status_code}: {errmsg}"


async def _post_wecom(webhook_url: str, payload: dict) -> WecomSendResult:
    url = (webhook_url or "").strip()
    if not url:
        return WecomSendResult(False, "Webhook URL 为空")
    if not url.startswith("https://"):
        return WecomSendResult(False, "Webhook URL 须以 https:// 开头")

    try:
        async with httpx.AsyncClient(timeout=settings.wecom_request_timeout) as client:
            resp = await client.post(url, json=payload)
            try:
                data = resp.json()
            except Exception:
                data = {"errmsg": resp.text[:200]}
            if resp.status_code == 200 and data.get("errcode") == 0:
                return WecomSendResult(True)
            error = _format_wecom_error(resp.status_code, data)
            logger.warning("WeCom webhook failed: %s payload=%s", error, payload.get("msgtype"))
            return WecomSendResult(False, error)
    except httpx.TimeoutException:
        logger.exception("WeCom webhook timeout: %s", url[:80])
        return WecomSendResult(
            False,
            "连接企微超时，请确认服务器能访问 qyapi.weixin.qq.com",
        )
    except Exception as e:
        logger.exception("WeCom webhook error: %s", e)
        return WecomSendResult(False, f"发送失败: {e}")


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
    return (await _post_wecom(webhook_url, payload)).ok


async def send_wecom_text_with_detail(
    webhook_url: str,
    content: str,
    *,
    mentioned_userids: list[str] | None = None,
    mentioned_mobiles: list[str] | None = None,
) -> WecomSendResult:
    text_body: dict = {"content": content}
    if mentioned_userids:
        text_body["mentioned_list"] = mentioned_userids
    if mentioned_mobiles:
        text_body["mentioned_mobile_list"] = mentioned_mobiles
    payload = {"msgtype": "text", "text": text_body}
    return await _post_wecom(webhook_url, payload)


async def send_wecom_markdown(webhook_url: str, content: str) -> bool:
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    return (await _post_wecom(webhook_url, payload)).ok


def build_bug_status_message(
    bug_num: int,
    title: str,
    from_label: str | None,
    to_label: str,
    assignee_name: str | None,
    project_name: str,
    bug_id: str,
) -> str:
    link = build_bug_detail_url(bug_id)
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
