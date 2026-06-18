"""
Runner 主进程。

用法：
  python runner.py

需要先配置好 .env.local（参考 .env.production）。
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import time

import httpx
from dotenv import load_dotenv

from executor import run_job

load_dotenv(".env.local")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("runner")

# httpx 会把每次 HTTP 请求打成 INFO，噪音太多，只保留 WARNING 以上
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

PLATFORM_URL = os.environ["PLATFORM_URL"].rstrip("/")   # e.g. https://your-platform.com
RUNNER_TOKEN = os.environ["RUNNER_TOKEN"]
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))    # 秒
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))  # 秒

_running = True


def _handle_stop(sig, frame):
    global _running
    log.info("Shutting down runner…")
    _running = False


signal.signal(signal.SIGINT, _handle_stop)
signal.signal(signal.SIGTERM, _handle_stop)


def _headers() -> dict:
    return {}  # token 通过 query param 传，不需要额外 header


def heartbeat(client: httpx.Client) -> None:
    try:
        client.post(
            f"{PLATFORM_URL}/api/v1/ui-automation/runner/heartbeat",
            params={"runner_token": RUNNER_TOKEN},
            timeout=10,
        )
    except Exception as e:
        log.warning("Heartbeat failed: %s", e)


def poll_job(client: httpx.Client) -> dict | None:
    try:
        resp = client.get(
            f"{PLATFORM_URL}/api/v1/ui-automation/runner/next-job",
            params={"runner_token": RUNNER_TOKEN},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("job")
    except Exception as e:
        log.warning("Poll failed: %s", e)
        return None


def report_step(
    client: httpx.Client,
    run_id: str,
    step_index: int,
    step_status: str,
    error_message: str | None = None,
    duration_ms: int | None = None,
    screenshot_bytes: bytes | None = None,
) -> None:
    params = {
        "runner_token": RUNNER_TOKEN,
        "run_id": run_id,
        "step_index": step_index,
        "step_status": step_status,
    }
    if error_message:
        params["error_message"] = error_message
    if duration_ms is not None:
        params["duration_ms"] = str(duration_ms)

    files = None
    if screenshot_bytes:
        files = {"screenshot": ("screenshot.png", screenshot_bytes, "image/png")}

    try:
        client.post(
            f"{PLATFORM_URL}/api/v1/ui-automation/runner/step-result",
            params=params,
            files=files,
            timeout=30,
        )
    except Exception as e:
        log.warning("Step report failed (step %d): %s", step_index, e)


def finish_job(
    client: httpx.Client,
    run_id: str,
    final_status: str,
    error_message: str | None = None,
    video_bytes: bytes | None = None,
) -> None:
    params = {
        "runner_token": RUNNER_TOKEN,
        "run_id": run_id,
        "final_status": final_status,
    }
    if error_message:
        params["error_message"] = error_message

    files = None
    if video_bytes:
        log.info("Uploading recording (%d KB)...", len(video_bytes) // 1024)
        files = {"video": ("recording.mp4", video_bytes, "video/mp4")}

    try:
        client.post(
            f"{PLATFORM_URL}/api/v1/ui-automation/runner/finish-job",
            params=params,
            files=files,
            timeout=120,  # 视频可能较大，给足时间
        )
    except Exception as e:
        log.warning("Finish report failed: %s", e)


def main() -> None:
    log.info("Runner started. Platform: %s", PLATFORM_URL)
    last_heartbeat = 0.0

    with httpx.Client() as client:
        while _running:
            now = time.time()

            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                heartbeat(client)
                last_heartbeat = now

            job = poll_job(client)
            if not job:
                time.sleep(POLL_INTERVAL)
                continue

            run_id = job["run_id"]
            log.info("Got job: run_id=%s", run_id)

            def _report_step(step_index, step_status, error_message=None, duration_ms=None, screenshot_bytes=None):
                report_step(client, run_id, step_index, step_status, error_message, duration_ms, screenshot_bytes)

            final_status, error_message, video_bytes = run_job(job, _report_step)
            finish_job(client, run_id, final_status, error_message, video_bytes)
            log.info("Job finished: run_id=%s status=%s", run_id, final_status)


if __name__ == "__main__":
    main()
