from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.wecom import _format_wecom_error, send_wecom_text_with_detail


def test_format_wecom_error_known_code():
    msg = _format_wecom_error(200, {"errcode": 93000, "errmsg": "invalid webhook url"})
    assert "Webhook 地址无效" in msg


def test_format_wecom_error_unknown_code():
    msg = _format_wecom_error(200, {"errcode": 12345, "errmsg": "unknown"})
    assert "errcode=12345" in msg


@pytest.mark.asyncio
async def test_send_wecom_text_rejects_non_https():
    result = await send_wecom_text_with_detail("http://example.com/hook", "hi")
    assert not result.ok
    assert result.error is not None
    assert "https" in result.error


@pytest.mark.asyncio
async def test_send_wecom_text_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.services.wecom.httpx.AsyncClient", return_value=mock_client):
        result = await send_wecom_text_with_detail(
            "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
            "hello",
        )

    assert result.ok
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["msgtype"] == "text"
    assert payload["text"]["content"] == "hello"
