# Traffic Light Desktop Monitor

> Real-time project status monitor — independent traffic light window per project

Each project gets its own **always-on-top** floating window with a classic traffic light display:

| Light | Status | Color |
|-------|--------|-------|
| Blue | Idle | `#3399ff` |
| Yellow | Working | `#ffcc00` |
| Green | Complete | `#00ff44` |

## Preview

```
 Single project (140x380)        Multi-project grid
+------------+                +------------+ +------------+
| default  X |                | default  X | | backend  X |
|------------|                |------------| |------------|
|  default   |                |            | |            |
|            |                |   (blue)   | |   (blue)   |
| (  blue  ) | <-- Idle       |            | |            |
|            |                |            | |            |
| ( yellow ) | <-- Working    |  (yellow)  | | ( yellow ) |
|            |                |            | |            |
| ( green  ) | <-- Complete   |            | |            |
|            |                |  (green)   | | ( green  ) |
|   Idle     |                |            | |            |
|------------|                |  Working   | |   Idle     |
| 1 projects |                |------------| |------------|
+------------+                +------------+ +------------+

 Keyboard shortcuts visible at bottom of each window
```

## Features

- **Multi-Window**: Each project = one independent traffic light window
- **Auto-Detect**: New projects appear automatically via file polling
- **Auto-Cleanup**: Completed projects auto-close after 5-second countdown
- **Keyboard Shortcuts**: `[1]` Idle `[2]` Work `[3]` Done `[Del]` Close `[L]` Lang `[A]` Boot
- **Bilingual**: Chinese / English toggle (CLI + GUI)
- **Boot Auto-Start**: `python status_updater.py autostart on` to launch at login
- **Always-on-Top**: Windows stay visible above other apps
- **Draggable**: Click and drag to reposition each window

## Requirements

- Python 3.7+
- tkinter (included with Python on Windows/macOS)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Kroza-cell/-traffic-light-assistant.git
cd -traffic-light-assistant

# Launch the multi-window monitor
python monitor.py

# Set a project status from CLI
python status_updater.py working -a "My Project"
python status_updater.py done -a "My Project"    # Auto-closes after 5s
python status_updater.py idle -a "My Project"
```

Or double-click **`run.bat`** on Windows.

## CLI Commands

```bash
# Set status
python status_updater.py idle          # Blue light (idle)
python status_updater.py working       # Yellow light (working)
python status_updater.py done          # Green light (complete, auto-remove 5s)

# Target a specific project
python status_updater.py working --agent "Frontend"
python status_updater.py done -a "Backend"

# List all projects (with hierarchy)
python status_updater.py list
python status_updater.py list -l zh    # Chinese output

# Remove a project
python status_updater.py remove "Project Name"

# Boot auto-start
python status_updater.py autostart on   # Enable
python status_updater.py autostart off  # Disable
python status_updater.py autostart      # Check status
```

## GUI Controls

| Action | How |
|--------|-----|
| Switch status | Right-click → select, or keyboard `[1]`/`[2]`/`[3]` |
| Close window | Click `X`, press `Delete`/`Esc`, or right-click → Remove |
| Toggle language | Press `[L]` or right-click → language toggle |
| Toggle auto-start | Press `[A]` or right-click → auto-start toggle |
| Move window | Click and drag anywhere on the window |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` / `I` | Idle (blue) |
| `2` / `W` | Working (yellow) |
| `3` / `D` | Complete (green) |
| `Delete` / `Esc` | Close window |
| `L` | Switch language |
| `A` | Toggle boot auto-start |

## Status File

Monitor reads `~/.claude/desk_assistant_status.json` every second:

```json
{
  "projects": {
    "Frontend": {
      "status": "working",
      "timestamp": "2026-05-31T12:00:00",
      "source": "status_updater_cli",
      "parent": null
    },
    "Backend": {
      "status": "idle",
      "timestamp": "2026-05-31T12:01:00",
      "source": "status_updater_cli",
      "parent": null
    }
  }
}
```

## Files

| File | Description |
|------|-------------|
| `monitor.py` | **Main** — multi-window monitor with all features |
| `status_updater.py` | CLI tool — set/list/remove/autostart |
| `config.py` | Shared constants, file I/O, i18n, tree logic |
| `traffic_light.py` | Legacy tree-mode GUI (use `monitor.py` instead) |
| `run.bat` | Windows quick-launch |

## Auto-Start with Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "python \"path/to/monitor.py\" 2>&1 &",
        "timeout": 5
      }]
    }]
  }
}
```

## License

MIT
