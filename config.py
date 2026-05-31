#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared config and file I/O for the multi-agent traffic light assistant.

Status file: ~/.claude/desk_assistant_status.json

New format (multi-agent):
  {"agents": {"agent_name": {"status": "idle|working|done", "timestamp": "...", "source": "..."}}}

Old format (single-agent, auto-migrated on read):
  {"status": "idle", "timestamp": "...", "source": "..."}
"""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime

STATUS_FILE = Path.home() / ".claude" / "desk_assistant_status.json"

VALID_STATUSES = {"idle", "working", "done"}

DEFAULT_AGENT = "default"

# light_name -> {active, dim, glow, label}
LIGHT_CONFIG = {
    "red":    {"active": "#ff1a1a", "dim": "#2a0000", "glow": "#ff4444", "label": "Idle"},
    "yellow": {"active": "#ffcc00", "dim": "#2a2000", "glow": "#ffee44", "label": "Working"},
    "green":  {"active": "#00ff44", "dim": "#002a00", "glow": "#44ff66", "label": "Complete"},
}

# status -> light_name
STATUS_TO_ACTIVE = {
    "idle":    "red",
    "working": "yellow",
    "done":    "green",
}

STATUS_TEXT = {
    "idle":    "Idle",
    "working": "Working",
    "done":    "Complete",
}

STATUS_COLORS = {
    "idle":    "#ff1a1a",
    "working": "#ffcc00",
    "done":    "#00ff44",
}

# GUI dimensions
WINDOW_WIDTH  = 230
CARD_HEIGHT   = 60
BASE_HEIGHT   = 80   # title bar + bottom margin


# ── File I/O ──────────────────────────────────────────────────────────────

def read_status_file() -> dict[str, dict]:
    """
    Read and parse the status file.
    Returns: {"agent_name": {"status": ..., "timestamp": ..., "source": ...}}
    Auto-migrates old single-agent format.
    Returns empty dict if file doesn't exist.
    """
    if not STATUS_FILE.exists():
        return {}

    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

    # Detect and migrate old format
    if "agents" not in data:
        # Old format: {"status": ..., "timestamp": ..., "source": ...}
        if "status" in data:
            return {
                DEFAULT_AGENT: {
                    "status": data.get("status", "idle"),
                    "timestamp": data.get("timestamp", ""),
                    "source": data.get("source", "migrated"),
                }
            }
        return {}

    return data.get("agents", {})


def write_status_file(agents: dict[str, dict]) -> None:
    """Write the full agents dictionary to the status file (atomic write)."""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    payload = {"agents": agents}

    # Atomic write: temp file then rename
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(STATUS_FILE.parent),
            prefix=".desk_status_",
            suffix=".tmp",
            text=True,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(STATUS_FILE))
    except Exception:
        # Fallback: direct write
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


def update_agent_status(agent_name: str, status: str, source: str = "unknown") -> None:
    """Set one agent's status and write the file."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    agents = read_status_file()
    agents[agent_name] = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "source": source,
    }
    write_status_file(agents)


def remove_agent(agent_name: str) -> bool:
    """Remove an agent. Returns False if agent didn't exist."""
    agents = read_status_file()
    if agent_name not in agents:
        return False
    del agents[agent_name]
    write_status_file(agents)
    return True
