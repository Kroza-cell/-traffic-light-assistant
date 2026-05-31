# Traffic Light Desktop Assistant

> Real-time Claude Code work status monitor with traffic light UI

## What it does

A small always-on-top desktop widget that shows your current work status using traffic lights:

| Light | Status | Meaning |
|-------|--------|---------|
| Red | Idle | Waiting for new tasks |
| Yellow | Working | Currently processing |
| Green | Complete | Task finished |

## Preview

```
     +------------------+
     |  Claude Status  X|
     |------------------|
     |                  |
     |    [Red]         |  <-- IDLE (lights up red)
     |                  |
     |    [Yellow]      |  <-- WORKING (lights up yellow)
     |                  |
     |    [Green]       |  <-- COMPLETE (lights up green)
     |                  |
     |------------------|
     | RED - Idle       |
     +------------------+
```

## Requirements

- Python 3.7+
- tkinter (included with Python on Windows/macOS)

## Quick Start

### Launch the GUI

```bash
# Double-click run.bat (Windows)
# OR from terminal:
python traffic_light.py
```

### Set status from command line

```bash
python status_updater.py idle      # Red light
python status_updater.py working   # Yellow light
python status_updater.py done      # Green light
```

### Right-click menu

Right-click the traffic light window to switch status directly.

## How it works

The GUI reads `~/.claude/desk_assistant_status.json` every second. Any external tool (including Claude Code itself) can write to this file to sync the light status.

### Status file format

```json
{
  "status": "working",
  "timestamp": "2026-05-31T11:11:26.202734",
  "source": "status_updater_cli"
}
```

## Files

| File | Description |
|------|-------------|
| `traffic_light.py` | Main GUI application |
| `status_updater.py` | CLI tool to update status |
| `run.bat` | Windows quick-launch script |
