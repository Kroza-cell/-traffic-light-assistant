# Traffic Light Desktop Assistant (Multi-Agent)

> Real-time Claude Code work status monitor — supports multiple agents

Each agent gets a compact card with 3 mini traffic lights:

| Light | Status | Meaning |
|-------|--------|---------|
| Red | Idle | Waiting for tasks |
| Yellow | Working | Currently processing |
| Green | Complete | Task finished |

## Preview

```
+-----------------------------------+
| Claude Agents               +  X  |
|-----------------------------------|
|  default       (o) (o) (o)        |
|                  Idle             |
|-----------------------------------|
|  reviewer      (o) (o) (o)        |
|                Working            |
|-----------------------------------|
|  tester        (o) (o) (o)        |
|                Complete           |
+-----------------------------------+
|  3 agent(s) | 1 working           |
+-----------------------------------+
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

### CLI Commands

```bash
# Set status for default agent
python status_updater.py idle
python status_updater.py working
python status_updater.py done

# Set status for a specific agent
python status_updater.py working --agent reviewer
python status_updater.py done -a tester

# List all agents
python status_updater.py list

# Remove an agent
python status_updater.py remove tester
```

### GUI Controls

| Action | How |
|--------|-----|
| Switch status | Right-click an agent card → select status |
| Add agent | Click **+** button or right-click → Add Agent |
| Remove agent | Right-click the agent card → Remove Agent |
| Move window | Left-click and drag anywhere |
| Close | Click **X** or right-click → Exit |

## How It Works

The GUI reads `~/.claude/desk_assistant_status.json` every second. Any external tool (including Claude Code itself) can write to this file to sync all agents' statuses.

### Status File Format

```json
{
  "agents": {
    "default": {
      "status": "idle",
      "timestamp": "2026-05-31T12:00:00",
      "source": "status_updater_cli"
    },
    "reviewer": {
      "status": "working",
      "timestamp": "2026-05-31T12:01:00",
      "source": "status_updater_cli"
    }
  }
}
```

Old single-agent format is auto-migrated on first read.

## Files

| File | Description |
|------|-------------|
| `traffic_light.py` | Main GUI — multi-agent card layout |
| `status_updater.py` | CLI tool — set/list/remove agents |
| `config.py` | Shared constants and file I/O |
| `run.bat` | Windows quick-launch script |
