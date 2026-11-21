import ctypes
import random
import re
import tkinter as tk
from ctypes import wintypes
from dataclasses import dataclass

import customtkinter as ctk

ROUND_SIZE = 1000
TEST_SIZE = 10
DEFAULT_KEYS = "F21 F22 F23 F24"
RANDOM_MODE = "随机抽取"
LOOP_MODE = "循环序列"
KEY_CODES = {key: ord(key) for key in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"}
KEY_CODES.update({f"F{number}": 0x70 + number - 1 for number in range(13, 25)})
KEY_CODES["SPACE"] = 0x20

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
GA_ROOT = 2
MODIFIERS = (0x10, 0x11, 0x12, 0x5B, 0x5C)  # Shift, Ctrl, Alt, Win


class KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),
    ]


class InputData(ctypes.Union):
    # The mouse member supplies the size and alignment of the Win32 INPUT union.
    _fields_ = [("keyboard", KeyboardInput), ("mouse", MouseInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("data", InputData)]


class WindowsKeyboard:
    def __init__(self):
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int)
        self.user32.SendInput.restype = wintypes.UINT
        self.user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
        self.user32.GetAncestor.restype = wintypes.HWND
        self.user32.GetForegroundWindow.argtypes = ()
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
        self.user32.GetAsyncKeyState.restype = ctypes.c_short

    def is_foreground(self, window_id):
        window = self.user32.GetAncestor(window_id, GA_ROOT)
        return bool(window) and window == self.user32.GetForegroundWindow()

    def modifier_is_down(self):
        return any(self.user32.GetAsyncKeyState(key) & 0x8000 for key in MODIFIERS)

    def tap(self, key):
        code = KEY_CODES[key]
        down = Input(INPUT_KEYBOARD, InputData(keyboard=KeyboardInput(wVk=code)))
        up = Input(INPUT_KEYBOARD, InputData(keyboard=KeyboardInput(wVk=code, dwFlags=KEYEVENTF_KEYUP)))
        events = (Input * 2)(down, up)
        ctypes.set_last_error(0)
        sent = self.user32.SendInput(len(events), events, ctypes.sizeof(Input))
        if sent != len(events):
            error = ctypes.get_last_error()
            if sent == 1:
                self.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(Input))
            raise OSError(error, f"Windows 仅接收了 {sent}/2 个按键事件（错误码 {error}）")


@dataclass(frozen=True)
class RoundSettings:
    keys: tuple[str, ...]
    interval_ms: int
    random_order: bool
    total: int

    @classmethod
    def parse(cls, keys_text, interval_text, random_order, total):
        keys = tuple(re.findall(r"[^\s,，]+", keys_text.strip().upper()))
        if not keys:
            raise ValueError("请输入至少一个按键。")
        for key in keys:
            if key not in KEY_CODES:
                raise ValueError(f"不支持 {key[:20]}。可用 A–Z、0–9、SPACE 或 F13–F24。")

        try:
            interval = int(interval_text)
        except ValueError:
            interval = 0
        if not 1 <= interval <= 60_000:
            raise ValueError("敲击间隔请输入 1 到 60000 之间的整数。")
        return cls(keys, interval, random_order, total)

    def key_at(self, position):
        if self.random_order:
            return random.choice(self.keys)
        return self.keys[position % len(self.keys)]


class AutoClicker(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color="#141a23")
        self.keyboard = WindowsKeyboard()
        self.settings = None
        self.timer = None
        self.count = 0
        self.title("键盘敲击器")
        self.geometry("560x498")
        self.minsize(525, 498)
        self.columnconfigure(0, weight=1)

        self.mode = tk.StringVar(value=RANDOM_MODE)
        self.keys = tk.StringVar(value=DEFAULT_KEYS)
        self.interval = tk.StringVar(value="10")
        self.build_ui()

    def build_ui(self):
        font = "Microsoft YaHei UI"
        muted = "#aab8cb"
        accent = "#75d8bc"
        card_color = "#212b39"

        ctk.CTkLabel(self, text="键盘敲击器", font=(font, 26, "bold")).grid(
            row=0, column=0, sticky="w", padx=26, pady=(22, 14)
        )

        controls = ctk.CTkFrame(self, fg_color=card_color, corner_radius=14)
        controls.grid(row=1, column=0, sticky="ew", padx=26)
        controls.columnconfigure(1, weight=1)
        for row, title in enumerate(("按键模式", "按键列表", "间隔（毫秒）")):
            ctk.CTkLabel(controls, text=title, font=(font, 14)).grid(
                row=row, column=0, sticky="w", padx=(18, 12), pady=(14, 0)
            )

        self.mode_switch = ctk.CTkSegmentedButton(
            controls, values=(RANDOM_MODE, LOOP_MODE), variable=self.mode, font=(font, 13),
            fg_color="#18202b", selected_color="#315c57", selected_hover_color="#3b7068",
        )
        self.mode_switch.grid(row=0, column=1, sticky="ew", padx=(0, 18), pady=(14, 0))
        self.keys_entry = ctk.CTkEntry(controls, textvariable=self.keys, height=36, font=("Segoe UI", 15))
        self.keys_entry.grid(row=1, column=1, sticky="ew", padx=(0, 18), pady=(14, 0))
        self.interval_entry = ctk.CTkEntry(
            controls, textvariable=self.interval, width=104, height=34, font=("Segoe UI", 15)
        )
        self.interval_entry.grid(row=2, column=1, sticky="w", pady=(14, 0))
        ctk.CTkLabel(
            controls, text="按键用空格或逗号分隔，例如 A S D SPACE F24。", font=(font, 12),
            text_color=muted,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(8, 12))

        self.capture = ctk.CTkFrame(self, fg_color=card_color, corner_radius=14)
        self.capture.grid(row=2, column=0, sticky="ew", padx=26, pady=(14, 0))
        self.capture.columnconfigure(0, weight=1)
        tk.Misc.bind(self.capture, "<KeyPress>", self.consume_key)
        tk.Misc.bind(self.capture, "<KeyRelease>", lambda _event: "break")
        tk.Misc.bind(self.capture, "<FocusOut>", self.on_focus_out)

        self.counter = ctk.CTkLabel(self.capture, text="0 / 1000", font=("Segoe UI", 27, "bold"))
        self.counter.grid(row=0, column=0, sticky="w", padx=18, pady=(10, 2))
        self.last_key = ctk.CTkLabel(self.capture, text="", font=(font, 13), text_color=accent)
        self.last_key.grid(row=0, column=1, sticky="e", padx=18, pady=(10, 2))
        self.progress = ctk.CTkProgressBar(self.capture, height=8, progress_color=accent)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(3, 4))
        self.status = ctk.CTkLabel(self.capture, text="就绪", font=(font, 13), text_color=muted, anchor="w")
        self.status.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(4, 8))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=3, column=0, sticky="ew", padx=26, pady=(15, 0))
        buttons.columnconfigure(0, weight=1)
        self.start_button = ctk.CTkButton(
            buttons, text="开始 1000 次", command=lambda: self.start(ROUND_SIZE), height=40,
            font=(font, 14, "bold"), fg_color=accent, hover_color="#a3e7d4", text_color="#102b26",
        )
        self.start_button.grid(row=0, column=0, sticky="ew")
        self.test_button = ctk.CTkButton(
            buttons, text="试敲 10 次", command=lambda: self.start(TEST_SIZE), width=118, height=40,
            font=(font, 13), fg_color="#354457", hover_color="#455770",
        )
        self.test_button.grid(row=0, column=1, padx=8)
        self.stop_button = ctk.CTkButton(
            buttons, text="停止", command=self.stop, width=82, height=40, state="disabled",
            font=(font, 13), fg_color="#354457", hover_color="#455770",
        )
        self.stop_button.grid(row=0, column=2)
        ctk.CTkLabel(self, text="按 Esc 或切换窗口可停止当前轮次。", font=(font, 12), text_color=muted).grid(
            row=4, column=0, sticky="w", padx=26, pady=(5, 12)
        )

    def set_running(self, running):
        state = "disabled" if running else "normal"
        for widget in (self.mode_switch, self.keys_entry, self.interval_entry, self.start_button, self.test_button):
            widget.configure(state=state)
        self.stop_button.configure(state="normal" if running else "disabled")

    def consume_key(self, event):
        if event.keysym == "Escape":
            self.stop()
        return "break"

    def on_focus_out(self, _event):
        self.stop("输入区失去焦点，已停止。")

    def start(self, total):
        if self.settings is not None:
            return
        try:
            self.settings = RoundSettings.parse(
                self.keys.get(), self.interval.get(), self.mode.get() == RANDOM_MODE, total
            )
        except ValueError as error:
            self.status.configure(text=str(error))
            return

        self.count = 0
        self.counter.configure(text=f"0 / {total}")
        self.last_key.configure(text="")
        self.progress.set(0)
        self.status.configure(text="试敲中" if total == TEST_SIZE else "敲击中")
        self.set_running(True)
        self.capture.focus_set()
        self.timer = self.after(30, self.tick)

    def stop(self, message="已停止"):
        if self.settings is None:
            return
        self.settings = None
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.set_running(False)
        self.status.configure(text=message)

    def tick(self):
        self.timer = None
        settings = self.settings
        if settings is None:
            return
        if self.focus_get() is not self.capture or not self.keyboard.is_foreground(self.winfo_id()):
            self.stop("窗口已切换，已停止。")
            return
        if self.keyboard.modifier_is_down():
            self.status.configure(text="松开 Shift、Ctrl、Alt 或 Win 键后继续。")
            self.timer = self.after(50, self.tick)
            return

        key = settings.key_at(self.count)
        try:
            self.keyboard.tap(key)
        except OSError as error:
            self.stop(f"发送失败。{error.strerror}")
            return

        self.count += 1
        self.counter.configure(text=f"{self.count} / {settings.total}")
        self.last_key.configure(text=f"最近按键  {key}")
        self.progress.set(self.count / settings.total)
        if self.count == settings.total:
            self.stop("试敲完成，请查看桌宠计数。" if settings.total == TEST_SIZE else "本轮完成")
        else:
            self.status.configure(text="试敲中" if settings.total == TEST_SIZE else "敲击中")
            self.timer = self.after(settings.interval_ms, self.tick)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    AutoClicker().mainloop()
