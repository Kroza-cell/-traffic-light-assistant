#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Multi-Agent Status Updater — set work status from command line.

Usage:
  python status_updater.py <status> [-a AGENT]     Set status (default agent: "default")
  python status_updater.py list                      List all agents
  python status_updater.py remove <name>             Remove an agent

Status values:
  idle      RED light    — idle / waiting
  working   YELLOW light — working / processing
  done      GREEN light  — task complete
"""

import sys
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg


def parse_args(argv):
    """Simple arg parser — no stdlib dependency, works on all Python 3.x."""
    args = {"status": None, "agent": cfg.DEFAULT_AGENT, "command": None, "target": None}

    i = 0
    positional = []
    while i < len(argv):
        a = argv[i]
        if a in ("-a", "--agent"):
            if i + 1 < len(argv):
                args["agent"] = argv[i + 1]
                i += 2
            else:
                print("[ERROR] --agent requires a name")
                sys.exit(1)
        elif a in ("-h", "--help"):
            print_help()
            sys.exit(0)
        else:
            positional.append(a)
            i += 1

    if len(positional) >= 1:
        first = positional[0].lower()
        if first in ("list", "ls"):
            args["command"] = "list"
        elif first == "remove" and len(positional) >= 2:
            args["command"] = "remove"
            args["target"] = positional[1]
        elif first in cfg.VALID_STATUSES:
            args["status"] = first
        else:
            print(f"[ERROR] Unknown command/status: {first}")
            print_help()
            sys.exit(1)

    return args


def print_help():
    print(__doc__)
    print("Options:")
    print("  -a, --agent NAME   Target agent name (default: 'default')")
    print("  -h, --help         Show this help")


def cmd_set(status, agent_name):
    """Set an agent's status."""
    try:
        cfg.update_agent_status(agent_name, status, source="status_updater_cli")
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    light_name = cfg.STATUS_TO_ACTIVE[status]
    label = cfg.STATUS_TEXT[status]
    print(f"[{light_name.upper()}] Agent '{agent_name}' -> {label}")


def cmd_list():
    """List all registered agents."""
    agents = cfg.read_status_file()
    if not agents:
        print("No agents registered yet.")
        print(f"Use: python status_updater.py idle  (creates '{cfg.DEFAULT_AGENT}' agent)")
        return

    print(f"{'Agent':<20} {'Status':<10} {'Light':<8} {'Updated'}")
    print("-" * 65)
    for name, data in sorted(agents.items()):
        status = data.get("status", "?")
        light = cfg.STATUS_TO_ACTIVE.get(status, "?")
        label = cfg.STATUS_TEXT.get(status, status)
        ts = data.get("timestamp", "?")[:19]  # truncate microseconds
        print(f"{name:<20} {label:<10} {light:<8} {ts}")


def cmd_remove(agent_name):
    """Remove an agent."""
    ok = cfg.remove_agent(agent_name)
    if ok:
        print(f"Removed agent: {agent_name}")
    else:
        print(f"Agent '{agent_name}' not found.")


def main():
    if len(sys.argv) < 2:
        print("=== Claude Multi-Agent Status Updater ===")
        print()
        cmd_list()
        print()
        print_help()
        sys.exit(0)

    argv = sys.argv[1:]
    args = parse_args(argv)

    if args["command"] == "list":
        cmd_list()
    elif args["command"] == "remove":
        cmd_remove(args["target"])
    elif args["status"]:
        cmd_set(args["status"], args["agent"])
    else:
        print("[ERROR] No command given")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
