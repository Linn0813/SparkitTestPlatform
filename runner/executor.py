"""
执行器：接收 job 描述，驱动 Appium 完成每步操作，逐步上报结果。
"""
from __future__ import annotations

import base64
import logging
import os
import tempfile
import time
from typing import Callable

from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

log = logging.getLogger("executor")

APPIUM_HOST = os.getenv("APPIUM_HOST", "127.0.0.1")
APPIUM_PORT = os.getenv("APPIUM_PORT", "4723")
STEP_TIMEOUT = int(os.getenv("STEP_TIMEOUT", "15"))       # 每步等待元素的超时秒数
DEFAULT_WAIT = int(os.getenv("DEFAULT_WAIT_MS", "500"))   # 每步操作后的固定等待毫秒

StepReporter = Callable[..., None]


# ---------------------------------------------------------------------------
# Selector 解析
# ---------------------------------------------------------------------------

def _by_and_value(selector: str) -> tuple[str, str]:
    """
    把 .env 风格的 selector 字符串转成 (By, value)。

    支持格式：
      ~Text                          → accessibility id
      android=new UiSelector()...   → Android UIAutomator
      xpath=//...                   → XPath
      id=com.pkg:id/element         → resource id
      text=某文字                    → Android text（用 xpath 实现）
    """
    if selector.startswith("~"):
        return AppiumBy.ACCESSIBILITY_ID, selector[1:]
    if selector.startswith("android="):
        return AppiumBy.ANDROID_UIAUTOMATOR, selector[len("android="):]
    if selector.startswith("xpath="):
        return AppiumBy.XPATH, selector[len("xpath="):]
    if selector.startswith("id="):
        return AppiumBy.ID, selector[len("id="):]
    if selector.startswith("text="):
        text = selector[len("text="):]
        return AppiumBy.XPATH, f'//*[@text="{text}"]'
    # 默认当 xpath
    return AppiumBy.XPATH, selector


def _find_element(driver, selector: str, timeout: int):
    by, value = _by_and_value(selector)
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


# ---------------------------------------------------------------------------
# 单步执行
# ---------------------------------------------------------------------------

def _execute_step(driver, step: dict, selectors: dict, timeout: int) -> None:
    action = step.get("action", "")
    selector_key = step.get("selector_key", "")
    value = step.get("value", "")

    selector = selectors.get(selector_key, "") if selector_key else ""

    if action == "tap":
        el = _find_element(driver, selector, timeout)
        el.click()

    elif action == "type":
        el = _find_element(driver, selector, timeout)
        el.click()
        el.clear()
        el.send_keys(value)

    elif action == "clear":
        el = _find_element(driver, selector, timeout)
        el.clear()

    elif action == "swipe":
        # value 格式: "up" | "down" | "left" | "right"
        size = driver.get_window_size()
        w, h = size["width"], size["height"]
        directions = {
            "up":    (w // 2, int(h * 0.7), w // 2, int(h * 0.3)),
            "down":  (w // 2, int(h * 0.3), w // 2, int(h * 0.7)),
            "left":  (int(w * 0.8), h // 2, int(w * 0.2), h // 2),
            "right": (int(w * 0.2), h // 2, int(w * 0.8), h // 2),
        }
        coords = directions.get(value.lower())
        if not coords:
            raise ValueError(f"Unknown swipe direction: {value}")
        driver.swipe(*coords, duration=500)

    elif action == "wait":
        # value 是毫秒字符串，例如 "2000"
        ms = int(value) if value else 1000
        time.sleep(ms / 1000)

    elif action == "wait_visible":
        _find_element(driver, selector, timeout)

    elif action == "assert_visible":
        _find_element(driver, selector, timeout)

    elif action == "assert_text":
        el = _find_element(driver, selector, timeout)
        actual = el.text
        if value not in actual:
            raise AssertionError(f"Expected text '{value}' not found in '{actual}'")

    else:
        raise ValueError(f"Unknown action: {action}")


# ---------------------------------------------------------------------------
# 断言
# ---------------------------------------------------------------------------

def _check_assertion(driver, assertion: dict, selectors: dict, timeout: int) -> None:
    assertion_type = assertion.get("type", "")
    selector_key = assertion.get("selector_key", "")
    value = assertion.get("value", "")

    if not assertion_type:
        return  # 没有断言则跳过

    selector = selectors.get(selector_key, "") if selector_key else ""

    if assertion_type == "element_visible":
        _find_element(driver, selector, timeout)

    elif assertion_type == "element_text":
        el = _find_element(driver, selector, timeout)
        if value not in el.text:
            raise AssertionError(f"Expected '{value}' in element text, got '{el.text}'")

    elif assertion_type == "no_element":
        by, val = _by_and_value(selector)
        els = driver.find_elements(by, val)
        if els:
            raise AssertionError(f"Element should not exist: {selector}")

    else:
        raise ValueError(f"Unknown assertion type: {assertion_type}")


# ---------------------------------------------------------------------------
# 能力构建
# ---------------------------------------------------------------------------

def _build_capabilities(job: dict, apk_path: str) -> AppiumOptions:
    app_info = job["app"]
    platform = app_info["platform"]
    options = AppiumOptions()

    if platform == "android":
        options.set_capability("platformName", "Android")
        options.set_capability("appium:automationName", os.getenv("ANDROID_AUTOMATION_NAME", "UiAutomator2"))
        options.set_capability("appium:deviceName", os.getenv("ANDROID_DEVICE_NAME", "Android Device"))
        options.set_capability("appium:app", apk_path)
        options.set_capability("appium:noReset", False)
        options.set_capability("appium:newCommandTimeout", 180)
        options.set_capability("appium:autoGrantPermissions", True)
        options.set_capability("appium:allowDowngrade", True)
        pv = os.getenv("ANDROID_PLATFORM_VERSION", "")
        if pv:
            options.set_capability("appium:platformVersion", pv)

    elif platform == "ios":
        options.set_capability("platformName", "iOS")
        options.set_capability("appium:automationName", "XCUITest")
        options.set_capability("appium:deviceName", os.getenv("IOS_DEVICE_NAME", "iPhone"))
        options.set_capability("appium:app", apk_path)
        options.set_capability("appium:noReset", False)
        options.set_capability("appium:newCommandTimeout", 180)
        pv = os.getenv("IOS_PLATFORM_VERSION", "")
        if pv:
            options.set_capability("appium:platformVersion", pv)
        udid = os.getenv("IOS_UDID", "")
        if udid:
            options.set_capability("appium:udid", udid)

    else:
        raise ValueError(f"Unknown platform: {platform}")

    return options


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def run_job(job: dict, report_step: StepReporter) -> tuple[str, str | None, bytes | None]:
    """
    执行一个 job，逐步上报结果。
    返回 (final_status, error_message, video_bytes)。
    final_status: "passed" | "failed" | "error"
    """
    app_info = job["app"]
    case_info = job["case"]
    steps: list[dict] = case_info.get("steps", [])
    selectors: dict = case_info.get("selectors", {})
    assertion: dict = case_info.get("assertion", {})

    download_url = app_info.get("download_url")
    if not download_url:
        return "error", "No app download URL received from server", None

    suffix = ".apk" if app_info["platform"] == "android" else ".ipa"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    apk_path = tmp.name
    tmp.close()

    try:
        log.info("Downloading app from server...")
        import urllib.request
        urllib.request.urlretrieve(download_url, apk_path)
        log.info("App downloaded to %s", apk_path)
    except Exception as e:
        os.unlink(apk_path)
        return "error", f"Failed to download app: {e}", None

    driver = None
    video_bytes: bytes | None = None
    # 安装步骤索引偏移（占用步骤 0~2）
    INSTALL_STEPS = 3

    try:
        t0 = time.time()
        caps = _build_capabilities(job, apk_path)
        appium_url = f"http://{APPIUM_HOST}:{APPIUM_PORT}"
        log.info("Connecting to Appium at %s", appium_url)

        # 安装记录 - 步骤 0: 下载 App
        report_step(0, "passed", duration_ms=int((time.time() - t0) * 1000))

        t1 = time.time()
        driver = webdriver.Remote(appium_url, options=caps)
        install_ms = int((time.time() - t1) * 1000)

        # 安装记录 - 步骤 1: 安装 App
        report_step(1, "passed", duration_ms=install_ms)

        # 验证 App 是否成功启动
        t2 = time.time()
        if app_info["platform"] == "android":
            current_pkg = driver.current_package
            current_activity = driver.current_activity
            log.info("App launched: package=%s activity=%s", current_pkg, current_activity)
            if not current_pkg or not current_activity:
                report_step(2, "failed", error_message="App failed to launch after installation")
                return "error", "App failed to launch after installation", None

        # 安装记录 - 步骤 2: 启动 App
        report_step(2, "passed", duration_ms=int((time.time() - t2) * 1000))

        # 开始录屏
        try:
            driver.start_recording_screen()
            log.info("Screen recording started")
        except Exception as e:
            log.warning("Failed to start recording: %s", e)

        for i, step in enumerate(steps):
            t = time.time()
            step_idx = i + INSTALL_STEPS
            try:
                _execute_step(driver, step, selectors, STEP_TIMEOUT)
                duration_ms = int((time.time() - t) * 1000)
                report_step(step_idx, "passed", duration_ms=duration_ms)
                log.info("Step %d passed: %s", i, step.get("action"))
                time.sleep(DEFAULT_WAIT / 1000)

            except Exception as e:
                duration_ms = int((time.time() - t) * 1000)
                screenshot_bytes = _take_screenshot(driver)
                report_step(step_idx, "failed", error_message=str(e), duration_ms=duration_ms, screenshot_bytes=screenshot_bytes)
                log.error("Step %d failed: %s", i, e)
                for j in range(i + 1, len(steps)):
                    report_step(j + INSTALL_STEPS, "skipped")
                video_bytes = _stop_recording(driver)
                return "failed", str(e), video_bytes

        # 执行断言
        try:
            _check_assertion(driver, assertion, selectors, STEP_TIMEOUT)
        except Exception as e:
            screenshot_bytes = _take_screenshot(driver)
            report_step(len(steps) + INSTALL_STEPS, "failed", error_message=str(e), screenshot_bytes=screenshot_bytes)
            video_bytes = _stop_recording(driver)
            return "failed", f"Assertion failed: {e}", video_bytes

        video_bytes = _stop_recording(driver)
        return "passed", None, video_bytes

    except WebDriverException as e:
        log.error("Appium connection error: %s", e)
        if driver:
            video_bytes = _stop_recording(driver)
        return "error", f"Appium error: {e}", video_bytes
    except Exception as e:
        log.error("Unexpected error: %s", e)
        if driver:
            video_bytes = _stop_recording(driver)
        return "error", str(e), video_bytes
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        try:
            os.unlink(apk_path)
        except Exception:
            pass


def _stop_recording(driver) -> bytes | None:
    try:
        b64 = driver.stop_recording_screen()
        return base64.b64decode(b64)
    except Exception as e:
        log.warning("Failed to stop recording: %s", e)
        return None


def _take_screenshot(driver) -> bytes | None:
    try:
        return base64.b64decode(driver.get_screenshot_as_base64())
    except Exception:
        return None
