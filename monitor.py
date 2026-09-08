"""Playwright 监控：打开直播页并检测抽奖倒计时。"""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path(__file__).resolve().parent / ".chrome-profile"
TITLE_MARK = "[抽奖监控]"

# 注入页面：观察 .count-box / .count-time，识别倒计时态
INJECT_JS = r"""
() => {
  const readState = () => {
    const box = document.querySelector(".count-box");
    if (!box) {
      window.__lotteryMonitorState = {
        found: false,
        isCountdown: false,
        text: "",
        status: null,
      };
      return;
    }
    const timeEl = box.querySelector(".count-time");
    const statusEl = timeEl && timeEl.querySelector("[status]");
    const text = timeEl ? String(timeEl.innerText || "").replace(/\s+/g, " ").trim() : "";
    const status = statusEl ? statusEl.getAttribute("status") : null;
    const countdownRe = /\b\d{1,2}:\d{2}(?::\d{2})?\b/;
    const idle = !text || text === "查看结果" || text === "抽奖";
    const isCountdown = status === "1" || (countdownRe.test(text) && !idle);
    window.__lotteryMonitorState = { found: true, isCountdown, text, status };
  };

  if (!window.__lotteryMonitorInstalled) {
    window.__lotteryMonitorInstalled = true;
    const obs = new MutationObserver(readState);
    obs.observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
    });
    window.__lotteryMonitorTimer = setInterval(readState, 400);
  }
  readState();
  const t = document.title || "";
  if (!t.startsWith("[抽奖监控]")) {
    document.title = "[抽奖监控] " + t;
  }
  return window.__lotteryMonitorState || { found: false, isCountdown: false, text: "", status: null };
}
"""


class LotteryMonitor:
    def __init__(
        self,
        url: str,
        headed: bool,
        emit: Callable[[str, dict[str, Any]], None],
    ) -> None:
        self.url = url.strip()
        self.headed = headed
        self.emit = emit
        self._stop = threading.Event()
        self._commands: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._page = None
        self._context = None
        self._was_countdown = False
        self._ready = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._ready.clear()
        self._was_countdown = False
        self._thread = threading.Thread(target=self._run, name="lottery-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._commands.put("stop")

    def jump_to_live(self) -> bool:
        if not self._ready.is_set() or self._stop.is_set():
            return False
        self._commands.put("jump")
        _focus_marked_window()
        return True

    def _run(self) -> None:
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as p:
                self._launch(p)
                self._watch()
        except Exception as exc:
            if not self._stop.is_set():
                self.emit("error", {"message": str(exc)})
        finally:
            self._page = None
            self._context = None
            self.emit("stopped", {})

    def _launch(self, p) -> None:
        launch_kwargs = dict(
            user_data_dir=str(PROFILE_DIR),
            headless=not self.headed,
            viewport={"width": 1440, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
            ignore_default_args=["--enable-automation"],
        )
        try:
            context = p.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
            self.emit("log", {"message": "已使用本机 Chrome 打开页面（登录状态会保留）"})
        except Exception:
            context = p.chromium.launch_persistent_context(**launch_kwargs)
            self.emit("log", {"message": "未找到本机 Chrome，已改用 Playwright Chromium"})

        self._context = context
        page = context.pages[0] if context.pages else context.new_page()
        self._page = page
        page.on("load", lambda: self._safe_inject())
        self.emit("log", {"message": f"正在打开：{self.url}"})
        page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
        self._safe_inject()
        self._ready.set()

    def _safe_inject(self) -> None:
        page = self._page
        if page is None:
            return
        for frame in [page, *page.frames]:
            try:
                frame.evaluate(INJECT_JS)
            except PlaywrightError:
                continue

    def _read_state(self, page) -> dict:
        last = {"found": False, "isCountdown": False, "text": "", "status": None}
        for frame in [page, *page.frames]:
            try:
                state = frame.evaluate(INJECT_JS)
            except PlaywrightError:
                continue
            if state and state.get("found"):
                return state
            if state:
                last = state
        return last

    def _watch(self) -> None:
        missing_ticks = 0
        while not self._stop.is_set():
            self._drain_commands()
            if self._stop.is_set():
                break
            page = self._page
            if page is None:
                break
            try:
                state = self._read_state(page)
            except PlaywrightError as exc:
                if self._stop.is_set():
                    break
                self.emit("log", {"message": f"页面读取失败，3 秒后重试：{exc}"})
                time.sleep(3)
                try:
                    page.reload(wait_until="domcontentloaded", timeout=30000)
                    self._safe_inject()
                except PlaywrightError:
                    pass
                continue

            found = bool(state.get("found"))
            is_countdown = bool(state.get("isCountdown"))
            text = str(state.get("text") or "")
            status = state.get("status")

            if not found:
                missing_ticks += 1
                if missing_ticks == 1:
                    self.emit(
                        "status",
                        {
                            "phase": "waiting",
                            "detail": "未找到抽奖区域，请确认已登录且直播页已打开",
                        },
                    )
                elif missing_ticks == 8:
                    self.emit("log", {"message": "仍未找到 .count-box，若弹出登录页请在浏览器中完成登录"})
            else:
                if missing_ticks:
                    self.emit("log", {"message": "已定位抽奖按钮区域 .count-box"})
                missing_ticks = 0
                if is_countdown:
                    self.emit(
                        "status",
                        {"phase": "countdown", "detail": text, "text": text, "status": status},
                    )
                    if not self._was_countdown:
                        self._was_countdown = True
                        self.emit("lottery_started", {"text": text, "status": status})
                else:
                    self.emit(
                        "status",
                        {
                            "phase": "watching",
                            "detail": text or "抽奖未开始",
                            "text": text,
                            "status": status,
                        },
                    )
                    if self._was_countdown:
                        self._was_countdown = False
                        self.emit("lottery_ended", {"text": text})

            time.sleep(0.35)

        try:
            if self._context is not None:
                self._context.close()
        except Exception:
            pass

    def _drain_commands(self) -> None:
        while True:
            try:
                cmd = self._commands.get_nowait()
            except queue.Empty:
                return
            if cmd == "stop":
                self._stop.set()
                return
            if cmd == "jump":
                self._do_jump()

    def _do_jump(self) -> None:
        page = self._page
        if page is None:
            return
        try:
            page.bring_to_front()
            current = page.url or ""
            if self.url.split("#")[0] not in current:
                page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
                self._safe_inject()
            self.emit("log", {"message": "已切回直播页，请手动点击抽奖按钮"})
        except Exception as exc:
            self.emit("log", {"message": f"跳转失败：{exc}"})
        _focus_marked_window()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._stop.is_set()


def _focus_marked_window() -> None:
    """把带标题标记的 Chrome 窗口拉到前台。"""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return

    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or ""
        if TITLE_MARK in title:
            found.append(hwnd)
        return True

    user32.EnumWindows(enum_proc, 0)
    if not found:
        return
    hwnd = found[0]
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
