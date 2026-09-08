"""直播抽奖监控桌面程序。"""

from __future__ import annotations

import json
import queue
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from monitor import LotteryMonitor
from notifier import LotteryToast

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

BG = "#16181f"
SURFACE = "#212532"
INPUT_BG = "#2a2f40"
TEXT = "#eef1f7"
MUTED = "#8b93a7"
ACCENT = "#3d8bfd"
OK = "#3dd68c"
WARN = "#f5a524"
DANGER = "#f76c6c"

DEFAULT_URL = (
    "https://qlive.woa.com/user/live"
    "?liveId=443e07926a9e00260001bc9c58e0affe&isShare=true"
)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_config(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("直播抽奖监控")
        self.geometry("560x680")
        self.minsize(520, 620)
        self.configure(bg=BG)

        self.events: queue.Queue = queue.Queue()
        self.monitor: LotteryMonitor | None = None
        self.toast = LotteryToast(self, self._jump_to_live)

        cfg = load_config()
        self.url_var = tk.StringVar(value=cfg.get("url") or DEFAULT_URL)
        self.headed_var = tk.BooleanVar(value=bool(cfg.get("headed", True)))
        self.phase_var = tk.StringVar(value="空闲")
        self.detail_var = tk.StringVar(value="输入直播地址后开始监控")

        self._build_style()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(150, self._pump_events)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("Card.TLabel", background=SURFACE, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("Phase.TLabel", background=SURFACE, foreground=ACCENT, font=("Microsoft YaHei UI", 14, "bold"))
        style.configure("Detail.TLabel", background=SURFACE, foreground=OK, font=("Consolas", 16, "bold"))
        style.configure("TCheckbutton", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.map("TCheckbutton", background=[("active", BG)])

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="TFrame")
        root.pack(fill="both", expand=True, padx=20, pady=18)

        ttk.Label(root, text="直播抽奖监控", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            root,
            text="自动打开直播页，发现倒计时后右下角提醒。跳转后请手动点击抽奖。",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(4, 16))

        ttk.Label(root, text="直播地址").pack(anchor="w")
        url_box = tk.Text(
            root,
            height=3,
            wrap="word",
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=8,
        )
        url_box.pack(fill="x", pady=(6, 10))
        url_box.insert("1.0", self.url_var.get())
        self.url_box = url_box

        ttk.Checkbutton(
            root,
            text="显示浏览器窗口（首次使用请勾选，方便完成企业微信 / SSO 登录）",
            variable=self.headed_var,
        ).pack(anchor="w", pady=(0, 14))

        btns = ttk.Frame(root, style="TFrame")
        btns.pack(fill="x", pady=(0, 16))

        self.start_btn = tk.Button(
            btns,
            text="开始监控",
            command=self._start,
            bg=ACCENT,
            fg="white",
            activebackground="#2f74d8",
            activeforeground="white",
            relief="flat",
            font=("Microsoft YaHei UI", 11, "bold"),
            cursor="hand2",
            padx=18,
            pady=7,
        )
        self.start_btn.pack(side="left")

        self.stop_btn = tk.Button(
            btns,
            text="停止监控",
            command=self._stop,
            bg="#3a4152",
            fg=TEXT,
            activebackground="#4a5266",
            activeforeground=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", 11),
            cursor="hand2",
            padx=18,
            pady=7,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(10, 0))

        self.jump_btn = tk.Button(
            btns,
            text="前往直播",
            command=self._jump_to_live,
            bg="#2d6a4f",
            fg="white",
            activebackground="#1b4332",
            activeforeground="white",
            relief="flat",
            font=("Microsoft YaHei UI", 11),
            cursor="hand2",
            padx=18,
            pady=7,
            state="disabled",
        )
        self.jump_btn.pack(side="left", padx=(10, 0))

        card = ttk.Frame(root, style="Card.TFrame")
        card.pack(fill="x", pady=(0, 14))
        inner = ttk.Frame(card, style="Card.TFrame")
        inner.pack(fill="x", padx=16, pady=14)
        ttk.Label(inner, text="当前状态", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(inner, textvariable=self.phase_var, style="Phase.TLabel").pack(anchor="w", pady=(2, 8))
        ttk.Label(inner, text="抽奖区域 / 倒计时", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(inner, textvariable=self.detail_var, style="Detail.TLabel").pack(anchor="w", pady=(2, 0))

        ttk.Label(root, text="运行日志").pack(anchor="w", pady=(0, 6))
        log = tk.Text(
            root,
            height=14,
            wrap="word",
            bg=INPUT_BG,
            fg=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", 9),
            state="disabled",
            padx=10,
            pady=8,
        )
        log.pack(fill="both", expand=True)
        self.log_box = log

    def _current_url(self) -> str:
        return self.url_box.get("1.0", "end").strip()

    def _append_log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_running(self, running: bool) -> None:
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")
        self.jump_btn.configure(state="normal" if running else "disabled")
        self.url_box.configure(state="disabled" if running else "normal")

    def _start(self) -> None:
        url = self._current_url()
        if not url.startswith("http"):
            messagebox.showwarning("提示", "请输入完整的直播地址（以 http 开头）")
            return
        save_config({"url": url, "headed": self.headed_var.get()})
        self.monitor = LotteryMonitor(url, self.headed_var.get(), self._emit)
        self.monitor.start()
        self._set_running(True)
        self.phase_var.set("启动中")
        self.detail_var.set("正在打开浏览器…")
        self._append_log("开始监控")

    def _stop(self) -> None:
        if self.monitor:
            self.monitor.stop()
        self.toast.close()
        self.phase_var.set("正在停止")
        self._append_log("正在关闭浏览器…")

    def _jump_to_live(self) -> None:
        if not self.monitor or not self.monitor.jump_to_live():
            messagebox.showinfo("提示", "浏览器尚未就绪，或窗口已被关闭。请重新开始监控。")
            return
        self._append_log("已请求将直播页置于前台")

    def _emit(self, kind: str, payload: dict) -> None:
        self.events.put((kind, payload))

    def _pump_events(self) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle(kind, payload)
        self.after(150, self._pump_events)

    def _handle(self, kind: str, payload: dict) -> None:
        if kind == "log":
            self._append_log(payload.get("message", ""))
        elif kind == "error":
            self._append_log("错误：" + payload.get("message", ""))
            self.phase_var.set("出错")
            self.detail_var.set(payload.get("message", "")[:80])
        elif kind == "status":
            phase = payload.get("phase")
            detail = payload.get("detail") or ""
            mapping = {
                "waiting": "等待页面 / 登录",
                "watching": "监控中 · 抽奖未开始",
                "countdown": "监控中 · 抽奖倒计时",
            }
            self.phase_var.set(mapping.get(phase, phase or ""))
            self.detail_var.set(detail or "--")
            if phase == "countdown":
                self.toast.update_time(detail)
        elif kind == "lottery_started":
            text = payload.get("text") or "倒计时中"
            self._append_log(f"检测到抽奖倒计时：{text}")
            self.toast.show(text)
            self.lift()
        elif kind == "lottery_ended":
            self._append_log("倒计时结束，恢复等待下一次抽奖")
            self.toast.close()
        elif kind == "stopped":
            self.monitor = None
            self._set_running(False)
            self.phase_var.set("已停止")
            self.detail_var.set("可以重新开始监控")
            self._append_log("监控已停止")

    def _on_close(self) -> None:
        if self.monitor:
            self.monitor.stop()
        self.toast.close()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
