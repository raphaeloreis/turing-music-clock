# Turing Music Clock

**English** · [Português](README.pt-BR.md)

> Music visualizer **and** digital/flip clock with live CPU & GPU stats for the **Turing Smart Screen 3.5"** USB display.

![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)
![Python](https://img.shields.io/badge/python-3.9%E2%80%933.12-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

When music is playing, the screen shows the album art, title and artist. When nothing is playing, it turns into a **clock** — choose between a **7-segment digital** look or a **split-flap (airport board)** look — with **CPU/GPU temperature and usage** and the date.

<div align="center">

| Now playing | Flip clock | Digital clock |
|:---:|:---:|:---:|
| ![now playing](docs/now-playing.png) | ![flip clock](docs/idle-flip.png) | ![digital clock](docs/idle-digital.png) |

</div>

> Fork of [turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python) (via [spel987/turing-3.5-screen-music-visualizer](https://github.com/spel987/turing-3.5-screen-music-visualizer)). See [Credits](#credits).

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running](#running)
- [Configuration](#configuration)
- [Start on boot](#start-on-boot)
- [CPU temperature (LibreHardwareMonitor)](#cpu-temperature-librehardwaremonitor)
- [Troubleshooting](#troubleshooting)
- [How it works](#how-it-works)
- [Credits](#credits)
- [License](#license)

## Features

- 🎵 **Now-playing screen** — album art, title, artist and a blurred background, read straight from the Windows media session (SMTC).
- 🕐 **Idle clock in two styles** (`digital` 7-segment or `flip` airport board), selectable via one setting.
- 🌡️ **CPU & GPU temperature + usage**, with the CPU temperature color-coded by range on the digital screen.
- 📅 **Date** with the weekday.
- 🔌 **Auto-reconnect** — if the USB cable is unplugged and replugged, it recovers on its own (no manual restart).
- 🌑 **Turns the screen off on exit / shutdown**, so it never freezes on the last frame (useful when USB ports stay powered).
- 🪶 **Lightweight** (~0.5% CPU, ~190 MB RAM) — it only redraws when something actually changes.
- 🚀 **One-command installer** + optional "start with Windows".

## Requirements

| Item | Needed for |
|---|---|
| **Turing Smart Screen 3.5"** (revision A) | everything — it's the target display |
| **Windows** | the media integration (SMTC / `winrt`) is Windows-only |
| **Python 3.9–3.12** | the installer sets it up via `winget` if missing |
| **NVIDIA GPU** *(optional)* | GPU temperature/usage (via `nvidia-smi`, already bundled with the driver) |
| **LibreHardwareMonitor** *(optional)* | CPU **temperature** — [see below](#cpu-temperature-librehardwaremonitor) |

Without an NVIDIA GPU or without LibreHardwareMonitor, the app still runs — the missing values simply show as `--`.

## Installation

In **PowerShell**:

```powershell
git clone https://github.com/raphaeloreis/turing-music-clock.git
cd turing-music-clock
.\install.ps1
```

`install.ps1` installs Python (if missing), creates a virtual environment (`.venv`), installs the dependencies and offers to start the app with Windows.

> If PowerShell blocks the script, allow it for the current session:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

## Running

```powershell
.\run.ps1
```

Keep the display connected over USB. The COM port is auto-detected; set it manually via `COM_PORT` if needed (see below).

## Configuration

The main settings live at the top of `music-visualizer.py`:

| Setting | Values | What it does |
|---|---|---|
| `COM_PORT` | `"AUTO"` or e.g. `"COM5"` | display serial port (auto-detected by default) |
| `IDLE_STYLE` | `"digital"` / `"flip"` | idle clock style |
| `IDLE_ACCENT` | RGB, e.g. `(56, 225, 255)` | digital clock color |
| `TEMP_REFRESH_SEC` | e.g. `3` | how often sensors are read |
| `RECONNECT_WAIT` | e.g. `3` | seconds between reconnection attempts |

**Screen orientation:** in the main block, `SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)` — swap for `LANDSCAPE`, `PORTRAIT` or `REVERSE_PORTRAIT`.

## Start on boot

```powershell
.\scripts\setup-autostart.ps1
```

Creates a scheduled task that starts the app at logon (30 s delay, hidden, no window). To remove it:

```powershell
Unregister-ScheduledTask -TaskName TuringMusicClock
```

## CPU temperature (LibreHardwareMonitor)

On Windows, CPU temperature can't be read directly from Python — it needs a kernel driver and admin rights (exactly what hardware-monitor apps do). The reliable way is to use **LibreHardwareMonitor** as the source:

1. Download [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) (portable).
2. Run it **as administrator** (required to read the CPU sensor).
3. In **Options**, enable **Run web server** (default port `8085`) and, optionally, **Start Minimized** + **Minimize To Tray**.
4. The app reads the temperature from `http://localhost:8085/data.json` (change it via `LHM_URL` in the code).

To start LibreHardwareMonitor **elevated** on boot, create a task in an **administrator** PowerShell, adjusting the executable path:

```powershell
$exe = "C:\path\to\LibreHardwareMonitor\LibreHardwareMonitor.exe"
$me  = "$env:USERDOMAIN\$env:USERNAME"
$action    = New-ScheduledTaskAction    -Execute $exe -WorkingDirectory (Split-Path $exe)
$trigger   = New-ScheduledTaskTrigger   -AtLogOn -User $me
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName "LibreHardwareMonitor" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
```

> **GPU** temperature/usage needs none of this — it comes from `nvidia-smi`, already installed with the NVIDIA driver.

## Troubleshooting

**The screen stays frozen with the last frame after I shut down the PC.**
Some motherboards keep the USB ports powered when off, so the display never loses power. The app sends a *screen off* command on exit to avoid this. If it still freezes, your Windows shutdown may be killing the process before it can clean up — as a fallback, disable USB power at shutdown in the BIOS (ErP / "USB power in S5").

**`Cannot open COM port ... Access denied`.**
Another program is holding the port — usually the vendor app (**UsbMonitor / UsbPCMonitor**). Close it and disable its autostart. Only one program can use the display at a time.

**White screen / `Cannot find COM port automatically`.**
The display wasn't detected. Check the cable, confirm it appears under *Device Manager → Ports (COM & LPT)*, and if needed set `COM_PORT` manually (e.g. `"COM5"`).

**CPU temperature shows `--`.**
LibreHardwareMonitor isn't running **as administrator**, its web server is off, or the port isn't `8085`. Open `http://localhost:8085` in a browser to confirm the CPU sensor has a value.

**GPU temperature/usage shows `--`.**
`nvidia-smi` wasn't found — expected on non-NVIDIA GPUs, or if the driver isn't installed.

**PowerShell won't run `install.ps1`.**
Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once, then try again.

**It doesn't start on boot.**
Make sure the vendor app (UsbMonitor) isn't set to autostart — it grabs the COM port before this app. Check the `TuringMusicClock` task exists in Task Scheduler.

## How it works

- The display speaks a simple serial protocol handled by the `library/` code (from the upstream project).
- `music-visualizer.py` builds each frame with **Pillow** and sends it over serial.
- Media info comes from the Windows **SMTC** API via `winrt`; **CPU usage** from `psutil`; **GPU** temp/usage from `nvidia-smi`; **CPU temperature** from LibreHardwareMonitor's local web server.
- The loop redraws once per second but **only sends the frame when it changed**, which keeps it light and avoids visible refreshing while idle.

## Credits

- **Original developer:** [mathoudebine](https://github.com/mathoudebine) — [turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python) (the display communication library).
- **Base fork:** [spel987](https://github.com/spel987) — [turing-3.5-screen-music-visualizer](https://github.com/spel987/turing-3.5-screen-music-visualizer) (the music visualizer).
- **This fork:** digital/flip clock, CPU/GPU stats, idle screen, auto-reconnect, screen-off on exit, optimizations and installer.

### Fonts

- [DSEG](https://github.com/keshikan/DSEG) (7-segment clock) — SIL Open Font License.
- [Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue) (flip clock) — SIL Open Font License.
- [Roboto](https://fonts.google.com/specimen/Roboto) — Apache License 2.0.

## License

[GPL-3.0](LICENSE), inherited from the original project. The bundled fonts keep their own licenses (see `res/fonts/`).
