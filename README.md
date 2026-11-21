# Windows Key Tapper

一个用 Python 和 CustomTkinter 编写的 Windows 桌面工具。每轮模拟 1000 次键盘敲击，可用来触发 Wuwa Tappo 等监听系统输入的桌宠。

> **仅支持 Windows。** 预期结果以本文的使用步骤为前提。请先启动目标应用，保持敲击器窗口在前台，并用「试敲 10 次」确认目标应用能识别模拟输入。目标应用的实际计数取决于其输入处理方式。

## 安装与启动

需要 Windows 和带 Tkinter 的 Python。项目使用 Python 3.12 验证，依赖记录在 [requirements.txt](requirements.txt)。

首次使用时，在项目目录打开 PowerShell，创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

已有 `.venv` 和依赖时，可以直接启动：

```powershell
.\.venv\Scripts\pythonw.exe .\autoclicker.py
```

如果窗口未出现，可以用 `python.exe` 替换 `pythonw.exe`，在 PowerShell 查看启动错误。

## 使用方法

1. 先打开桌宠，再打开敲击器。默认从 `F21 F22 F23 F24` 随机抽取，每次间隔 10 毫秒。
2. 也可以选择「循环序列」，输入 `A S D SPACE`。程序会执行 `A → S → D → 空格`，再从头重复。支持 `A–Z`、`0–9`、`SPACE` 和 `F13–F24`，可以用空格、中英文逗号分隔。间隔可填 1 到 60000 毫秒的整数。
3. 点击「试敲 10 次」确认桌宠有反应，再点击「开始 1000 次」。界面显示已发送次数和最近按键，到目标次数自动停止。
4. 运行时让敲击器保持在前台。点击「停止」、按 `Esc` 或切换窗口都会结束当前轮次。重新开始时从 0 计数。

## 技术实现

- **系统输入**。`WindowsKeyboard` 通过 `ctypes` 调用 Win32 `SendInput`。每次敲击提交同一个虚拟键的按下和释放事件。Windows 接收两条事件后，界面计数加一。
- **输入接收**。运行时焦点移到窗口内专用的接收区。Tk 按键绑定返回 `break`，终止按键事件在界面内继续传播。每次发送前还会检查输入区焦点和 Windows 前台窗口。按住 `Shift`、`Ctrl`、`Alt` 或 `Win` 时会暂缓发送，避免与模拟按键组合。
- **按键选择**。`RoundSettings` 在开始时校验并保存本轮设置。随机模式每次用 `random.choice()` 抽取，允许连续出现相同按键。循环模式用当前次数对序列长度取余。
- **计时与停止**。Tk 的 `after()` 每次安排下一次敲击，让界面在等待期间仍能响应。停止时用 `after_cancel()` 取消尚未执行的任务。实际间隔受 Windows 和界面事件循环调度影响。

## 使用 AI 声明

本程序完全由 ChatGPT 6.2 Sol 实现。
