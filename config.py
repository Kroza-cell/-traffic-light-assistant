#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared config and file I/O for the multi-project traffic light assistant.

Status file: ~/.claude/desk_assistant_status.json

Format (multi-project):
  {"projects": {"name": {"status": "idle|working|done", "timestamp": "...", "source": "..."}}}

Old formats auto-migrated on read:
  - {"agents": {...}}                          (renamed key)
  - {"status": "idle", "timestamp": "...", ...} (single-agent v1)
"""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime

STATUS_FILE = Path.home() / ".claude" / "desk_assistant_status.json"
LANG_FILE   = Path.home() / ".claude" / "desk_assistant_lang.json"

VALID_STATUSES = {"idle", "working", "done"}

DEFAULT_PROJECT = "default"
DEFAULT_AGENT   = DEFAULT_PROJECT  # backward compat alias

# ── Bilingual text resources ─────────────────────────────────────────────

TEXTS = {
    "zh": {
        # Title bar
        "title_single": "{}",
        "title_multi": "项目",
        # Status labels
        "idle": "空闲",
        "working": "工作中",
        "complete": "已完成",
        # Empty state
        "no_projects": "暂无项目",
        "click_add": '点 "+" 添加',
        # Menus
        "project_header": "项目:",
        "add_project": "添加项目...",
        "add_project_title": "添加项目",
        "add_project_prompt": "项目名称:",
        "remove_project": "删除项目...",
        "remove_project_title": "删除项目",
        "remove_confirm": '确认删除 "{}"?',
        "remove_btn": "删除",
        "cancel_btn": "取消",
        "exit": "退出",
        "status_bar": "{} 个项目 | {} 个工作中",
        "set_idle": "[空闲] 设为空闲",
        "set_working": "[工作中] 设为工作中",
        "set_complete": "[已完成] 设为已完成",
        "lang_toggle": "切换 English",
        # CLI
        "list_title": "=== Claude 项目状态监控 ===",
        "list_no_registered": "还没有注册的项目。",
        "list_create_hint": "创建方法: python status_updater.py idle  (创建默认项目)",
        "list_col_project": "项目",
        "list_col_status": "状态",
        "list_col_light": "灯光",
        "list_col_updated": "更新时间",
        "removed_ok": "项目已删除:",
        "removed_not_found": "项目不存在:",
        "err_project_required": "[错误] --project 需要指定名称",
        "err_unknown_cmd": "[错误] 未知命令/状态:",
        "err_no_command": "[错误] 没有指定命令",
        "status_updated": "状态已更新",
        "project_label": "项目",
        "usage": "用法:",
        "positional_status": "[idle|working|done]",
        "positional_command": "[list|remove]",
        "options": "选项:",
        "opt_project": "  -a, --agent NAME   目标项目名称",
        "opt_lang": "  -l, --lang zh|en   输出语言",
        "light_idle": "空闲",
        "light_working": "工作中",
        "light_complete": "已完成",
    },
    "en": {
        # Title bar
        "title_single": "{}",
        "title_multi": "Projects",
        # Status labels
        "idle": "Idle",
        "working": "Working",
        "complete": "Complete",
        # Empty state
        "no_projects": "No projects",
        "click_add": 'Click "+" to add',
        # Menus
        "project_header": "Project:",
        "add_project": "Add Project...",
        "add_project_title": "Add Project",
        "add_project_prompt": "Project name:",
        "remove_project": "Remove Project...",
        "remove_project_title": "Remove Project",
        "remove_confirm": 'Remove "{}"?',
        "remove_btn": "Remove",
        "cancel_btn": "Cancel",
        "exit": "Exit",
        "status_bar": "{} project(s) | {} working",
        "set_idle": "[IDLE]  Set Idle",
        "set_working": "[WORK] Set Working",
        "set_complete": "[DONE] Set Complete",
        "lang_toggle": "Switch to 中文",
        # CLI
        "list_title": "=== Claude Project Status Monitor ===",
        "list_no_registered": "No projects registered yet.",
        "list_create_hint": "Create: python status_updater.py idle  (creates default project)",
        "list_col_project": "Project",
        "list_col_status": "Status",
        "list_col_light": "Light",
        "list_col_updated": "Updated",
        "removed_ok": "Removed project:",
        "removed_not_found": "Project not found:",
        "err_project_required": "[ERROR] --project requires a name",
        "err_unknown_cmd": "[ERROR] Unknown command/status:",
        "err_no_command": "[ERROR] No command given",
        "status_updated": "Status updated",
        "project_label": "Project",
        "usage": "Usage:",
        "positional_status": "[idle|working|done]",
        "positional_command": "[list|remove]",
        "options": "Options:",
        "opt_project": "  -a, --agent NAME   Target project name",
        "opt_lang": "  -l, --lang zh|en   Output language",
        "light_idle": "Idle",
        "light_working": "Working",
        "light_complete": "Complete",
    },
}

# light_name -> text key
LIGHT_LABEL_KEY = {
    "red":    "light_idle",
    "yellow": "light_working",
    "green":  "light_complete",
}

# status -> light_name
STATUS_TO_ACTIVE = {
    "idle":    "red",
    "working": "yellow",
    "done":    "green",
}

# status key -> text key
STATUS_TEXT_KEY = {
    "idle":    "idle",
    "working": "working",
    "done":    "complete",
}

STATUS_COLORS = {
    "idle":    "#ff1a1a",
    "working": "#ffcc00",
    "done":    "#00ff44",
}

LIGHT_CONFIG = {
    "red":    {"active": "#ff1a1a", "dim": "#2a0000", "glow": "#ff4444"},
    "yellow": {"active": "#ffcc00", "dim": "#2a2000", "glow": "#ffee44"},
    "green":  {"active": "#00ff44", "dim": "#002a00", "glow": "#44ff66"},
}

# ── GUI dimensions ──────────────────────────────────────────────────────

# Shared
BASE_HEIGHT = 80  # title bar + status bar combined height (used by both modes)

# Multi-project (card list) mode
CARD_WINDOW_WIDTH = 230
CARD_HEIGHT       = 60
CARD_BASE_HEIGHT  = BASE_HEIGHT  # alias

# Single-project (big light) mode
SINGLE_WINDOW_WIDTH  = 140
SINGLE_WINDOW_HEIGHT = 380
SINGLE_CANVAS_MARGIN = 30  # reserved space below status text
BIG_LIGHT_TOP        = 10    # y offset for first light
BIG_LIGHT_SPACING    = 80    # vertical gap between lights
BIG_LIGHT_CY_OFFSET  = 38    # circle center offset from top of each light area
BIG_RING_R           = 32    # outer ring radius
BIG_GLOW1_R          = 28    # glow layer 1
BIG_GLOW2_R          = 24    # glow layer 2
BIG_CORE_R           = 20    # core light


# ── Language helpers ────────────────────────────────────────────────────

def load_lang() -> str:
    """Load language preference. Returns 'zh' or 'en'. Default: 'zh'."""
    if LANG_FILE.exists():
        try:
            with open(LANG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            lang = data.get("lang", "zh")
            if lang in ("zh", "en"):
                return lang
        except (json.JSONDecodeError, IOError):
            pass
    return "zh"


def save_lang(lang: str) -> None:
    """Persist language preference."""
    LANG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump({"lang": lang}, f, ensure_ascii=False, indent=2)


def t(key: str, lang: str = None) -> str:
    """Translate a key to the given language. Falls back to 'zh' then key itself."""
    if lang is None:
        lang = load_lang()
    return TEXTS.get(lang, TEXTS["zh"]).get(key, key)


def status_label(status: str, lang: str = None) -> str:
    """Get display label for a status value."""
    key = STATUS_TEXT_KEY.get(status, "idle")
    return t(key, lang)


def light_label(light_name: str, lang: str = None) -> str:
    """Get display label for a light color name."""
    key = LIGHT_LABEL_KEY.get(light_name, "light_idle")
    return t(key, lang)


# ── File I/O ──────────────────────────────────────────────────────────────

def _normalize_key(data: dict) -> dict:
    """Normalize old keys to new 'projects' key. Mutates in place."""
    if "projects" in data:
        return data
    if "agents" in data:
        # v2 format using old key name
        data["projects"] = data.pop("agents")
        return data
    return data


def read_status_file() -> dict[str, dict]:
    """
    Read and parse the status file.
    Returns: {"project_name": {"status": ..., "timestamp": ..., "source": ...}}
    Auto-migrates old formats.
    Returns empty dict if file doesn't exist.
    """
    if not STATUS_FILE.exists():
        return {}

    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

    data = _normalize_key(data)

    if "projects" not in data:
        # Old single-agent format: {"status": "idle", ...}
        if "status" in data:
            return {
                DEFAULT_PROJECT: {
                    "status": data.get("status", "idle"),
                    "timestamp": data.get("timestamp", ""),
                    "source": data.get("source", "migrated"),
                }
            }
        return {}

    return data.get("projects", {})


def write_status_file(projects: dict[str, dict]) -> None:
    """Write the full projects dictionary to the status file (atomic write)."""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    payload = {"projects": projects}

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
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


def update_project_status(name: str, status: str, source: str = "unknown") -> None:
    """Set one project's status and write the file."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    projects = read_status_file()
    projects[name] = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "source": source,
    }
    write_status_file(projects)


def remove_project(name: str) -> bool:
    """Remove a project. Returns False if project didn't exist."""
    projects = read_status_file()
    if name not in projects:
        return False
    del projects[name]
    write_status_file(projects)
    return True


# ── Backward-compat aliases ────────────────────────────────────────────

update_agent_status = update_project_status
remove_agent = remove_project
