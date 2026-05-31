#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Project Status Updater — set work status from command line.
Supports Chinese (zh) / English (en) output.

Usage:
  python status_updater.py <status> [-a PROJECT] [-l zh|en]
  python status_updater.py list [-l zh|en]
  python status_updater.py remove <name> [-l zh|en]

Status values:
  idle      RED light    — idle / waiting
  working   YELLOW light — working / processing
  done      GREEN light  — task complete
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg


def parse_args(argv):
    args = {
        "status": None,
        "project": cfg.DEFAULT_PROJECT,
        "command": None,
        "target": None,
        "lang": cfg.load_lang(),
    }

    i = 0
    positional = []
    while i < len(argv):
        a = argv[i]
        if a in ("-a", "--agent", "-p", "--project"):
            if i + 1 < len(argv):
                args["project"] = argv[i + 1]
                i += 2
            else:
                print(cfg.t("err_project_required", args["lang"]))
                sys.exit(1)
        elif a in ("-l", "--lang"):
            if i + 1 < len(argv):
                lang = argv[i + 1]
                if lang in ("zh", "en"):
                    args["lang"] = lang
                else:
                    print(f"[ERROR] Invalid language: {lang}. Use 'zh' or 'en'.")
                    sys.exit(1)
                i += 2
            else:
                print("[ERROR] --lang requires 'zh' or 'en'")
                sys.exit(1)
        elif a in ("-h", "--help"):
            print_help(args["lang"])
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
            print(cfg.t("err_unknown_cmd", args["lang"]), first)
            print_help(args["lang"])
            sys.exit(1)

    return args


def print_help(lang: str = "zh"):
    print(__doc__)
    print(cfg.t("options", lang))
    print(cfg.t("opt_project", lang))
    print(cfg.t("opt_lang", lang))
    print("  -h, --help         Show this help")


def cmd_set(status, name, lang):
    try:
        cfg.update_project_status(name, status, source="status_updater_cli")
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    light_name = cfg.STATUS_TO_ACTIVE[status]
    label = cfg.status_label(status, lang)
    proj_text = cfg.t("project_label", lang)
    status_text = cfg.t("status_updated", lang)
    print(f"[{light_name.upper()}] {proj_text} '{name}' {status_text}: {label}")


def cmd_list(lang):
    projects = cfg.read_status_file()
    if not projects:
        print(cfg.t("list_no_registered", lang))
        print(cfg.t("list_create_hint", lang))
        return

    col_proj = cfg.t("list_col_project", lang)
    col_status = cfg.t("list_col_status", lang)
    col_light = cfg.t("list_col_light", lang)
    col_updated = cfg.t("list_col_updated", lang)

    print(f"{col_proj:<20} {col_status:<10} {col_light:<8} {col_updated}")
    print("-" * 65)
    for name, data in sorted(projects.items()):
        status = data.get("status", "?")
        light = cfg.STATUS_TO_ACTIVE.get(status, "?")
        label = cfg.status_label(status, lang)
        ts = data.get("timestamp", "?")[:19]
        print(f"{name:<20} {label:<10} {light:<8} {ts}")


def cmd_remove(name, lang):
    ok = cfg.remove_project(name)
    if ok:
        print(f"{cfg.t('removed_ok', lang)} {name}")
    else:
        print(f"{cfg.t('removed_not_found', lang)} {name}")


def main():
    if len(sys.argv) < 2:
        default_lang = cfg.load_lang()
        print(cfg.t("list_title", default_lang))
        print()
        cmd_list(default_lang)
        print()
        print_help(default_lang)
        sys.exit(0)

    argv = sys.argv[1:]
    args = parse_args(argv)

    if args["command"] == "list":
        cmd_list(args["lang"])
    elif args["command"] == "remove":
        cmd_remove(args["target"], args["lang"])
    elif args["status"]:
        cmd_set(args["status"], args["project"], args["lang"])
    else:
        print(cfg.t("err_no_command", args["lang"]))
        print_help(args["lang"])
        sys.exit(1)


if __name__ == "__main__":
    main()
