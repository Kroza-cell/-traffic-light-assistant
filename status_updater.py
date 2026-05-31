#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Status Updater — set work status from command line
Usage:
  python status_updater.py idle      # IDLE  -> RED light
  python status_updater.py working   # WORK  -> YELLOW light
  python status_updater.py done      # DONE  -> GREEN light
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STATUS_FILE = Path.home() / ".claude" / "desk_assistant_status.json"

VALID_STATUSES = {"idle", "working", "done"}

STATUS_LABELS = {
    "idle":    "[RED]",
    "working": "[YELLOW]",
    "done":    "[GREEN]",
}

STATUS_DESC = {
    "idle":    "Idle / Waiting for task",
    "working": "Working / Processing",
    "done":    "Task complete",
}


def set_status(status: str):
    if status not in VALID_STATUSES:
        print(f"[ERROR] Invalid status: {status}")
        print(f"  Valid: {', '.join(VALID_STATUSES)}")
        sys.exit(1)

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "source": "status_updater_cli",
    }

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    label = STATUS_LABELS.get(status, "")
    desc = STATUS_DESC.get(status, "")
    print(f"{label} Status updated: {status} ({desc})")
    print(f"  File: {STATUS_FILE}")


def show_current():
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        status = data.get("status", "unknown")
        label = STATUS_LABELS.get(status, "")
        desc = STATUS_DESC.get(status, "?")
        ts = data.get("timestamp", "?")
        print(f"{label} Current status: {status} ({desc})")
        print(f"  Updated: {ts}")
    else:
        print("[!] Status file not found (no status set yet)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=== Claude Status Updater ===")
        show_current()
        print()
        print("Usage: python status_updater.py [idle|working|done]")
        print("  idle    -> RED light (idle)")
        print("  working -> YELLOW light (working)")
        print("  done    -> GREEN light (task complete)")
        sys.exit(0)

    set_status(sys.argv[1])
