# Traffic Light Desktop Monitor

> AI-powered real-time status monitor — light changes automatically with Claude Code state

Each project gets its own **always-on-top** floating window. The light color is **auto-controlled by Claude Code hooks** — no manual input needed.

| Light | Status | Color | When |
|-------|--------|-------|------|
| Blue | Idle | `#3399ff` | Claude waiting for your input |
| Yellow | Working | `#ffcc00` | Claude processing your request |
| Green | Complete | `#00ff44` | Task done (5s auto-close) |

## Preview

```
 Single project (140x380)
+------------+
| default  X |
|------------|
|            |
|   (blue)   |  <-- Idle: waiting for you
|            |
|  (yellow)  |  <-- Working: processing
|            |
|  (green)   |  <-- Complete: task done
|            |
|   Idle     |
|------------|
| 1 projects |
+------------+
```

## AI Auto-Control (Claude Code Hooks)

The light changes **automatically** based on Claude Code's state:

| Hook | Trigger | Action |
|------|---------|--------|
| `PreToolUse` | Claude executes any tool | Blue → Yellow |
| `Stop` | Claude finishes, waits for input | Yellow → Blue |

Setup: copy `claude-settings.example.json` to `~/.claude/settings.json` and update the paths, or merge with your existing settings.

## Features

- **AI-Controlled**: Status auto-updates via Claude Code hooks — hands-free
- **Multi-Window**: Each project = one independent traffic light window
- **Auto-Detect**: New projects appear automatically via 1-second file polling
- **Auto-Cleanup**: Completed projects auto-close after 5-second countdown
- **Bilingual**: Chinese / English toggle (CLI + right-click menu)
- **Boot Auto-Start**: `python status_updater.py autostart on` for Windows startup
- **Always-on-Top**: Windows stay visible above other apps
- **Draggable**: Click and drag to reposition each window

## Requirements

- Python 3.7+
- tkinter (included with Python on Windows/macOS)
- Claude Code (for AI auto-control)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Kroza-cell/-traffic-light-assistant.git
cd -traffic-light-assistant

# Launch the multi-window monitor
python monitor.py

# Auto-control: configure Claude Code hooks (see claude-settings.example.json)
```

Or double-click **`run.bat`** on Windows.

## CLI Commands

```bash
# Set status (optional — normally auto-controlled by hooks)
python status_updater.py idle          # Blue light (idle)
python status_updater.py working       # Yellow light (working)
python status_updater.py done          # Green light (complete, auto-remove 5s)

# Target a specific project
python status_updater.py working --agent "Frontend"
python status_updater.py done -a "Backend"

# List all projects
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
| Switch status (manual) | Right-click → select status |
| Close window | Click `X` or right-click → Remove |
| Toggle language | Right-click → language toggle |
| Toggle auto-start | Right-click → auto-start toggle |
| Move window | Click and drag anywhere |

## Status File

Monitor reads `~/.claude/desk_assistant_status.json`:

```json
{
  "projects": {
    "Frontend": {
      "status": "working",
      "timestamp": "2026-05-31T12:00:00",
      "source": "claude_hook",
      "parent": null
    }
  }
}
```

## Files

| File | Description |
|------|-------------|
| `monitor.py` | **Main** — multi-window monitor |
| `status_updater.py` | CLI tool — set/list/remove/autostart |
| `config.py` | Shared constants, file I/O, i18n |
| `traffic_light.py` | Legacy tree-mode GUI |
| `run.bat` | Windows quick-launch |
| `claude-settings.example.json` | Claude Code hooks setup |

## License

MIT
