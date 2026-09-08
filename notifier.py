"""屏幕右下角置顶提醒弹窗。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

BG = "#1b1f2a"
CARD = "#262c3a"
ACCENT = "#3d8bfd"
TEXT = "#f2f4f8"
MUTED = "#9aa3b5"
OK = "#3dd68c"


class LotteryToast:
    def __init__(self, master: tk.Misc, on_jump: Callable[[], None]) -> None:
        self.master = master
        self.on_jump = on_jump
        self.win: tk.Toplevel | None = None
        self._time_var = tk.StringVar(value="")

    def show(self, countdown_text: str) -> None:
        self._time_var.set(countdown_text or "进行中")
        if self.win is not None and self.win.winfo_exists():
            self.win.lift()
            self.win.attributes("-topmost", True)
            return
        self._build()

    def update_time(self, countdown_text: str) -> None:
        if self.win is not None and self.win.winfo_exists():
            self._time_var.set(countdown_text or "进行中")

    def close(self) -> None:
        if self.win is not None and self.win.winfo_exists():
            self.win.destroy()
        self.win = None

    def _build(self) -> None:
        win = tk.Toplevel(self.master)
        self.win = win
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=BG)

        width, height = 340, 168
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = sw - width - 24
        y = sh - height - 72
        win.geometry(f"{width}x{height}+{x}+{y}")

        frame = tk.Frame(win, bg=CARD, highlightbackground=ACCENT, highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(
            frame,
            text="检测到抽奖倒计时",
            bg=CARD,
            fg=TEXT,
            font=("Microsoft YaHei UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 4))

        tk.Label(
            frame,
            textvariable=self._time_var,
            bg=CARD,
            fg=OK,
            font=("Consolas", 20, "bold"),
            anchor="w",
        ).pack(fill="x", padx=16)

        tk.Label(
            frame,
            text="点击后会把直播页拉到前台，请再手动点抽奖",
            bg=CARD,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 10))

        btns = tk.Frame(frame, bg=CARD)
        btns.pack(fill="x", padx=16, pady=(0, 14))

        jump = tk.Button(
            btns,
            text="前往直播",
            command=self._jump,
            bg=ACCENT,
            fg="white",
            activebackground="#2f74d8",
            activeforeground="white",
            relief="flat",
            font=("Microsoft YaHei UI", 10, "bold"),
            cursor="hand2",
            padx=14,
            pady=5,
        )
        jump.pack(side="left")

        close = tk.Button(
            btns,
            text="关闭",
            command=self.close,
            bg="#3a4152",
            fg=TEXT,
            activebackground="#4a5266",
            activeforeground=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", 10),
            cursor="hand2",
            padx=14,
            pady=5,
        )
        close.pack(side="left", padx=(8, 0))

        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            win.bell()

    def _jump(self) -> None:
        self.on_jump()
        self.close()
