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
LANG_FILE   = Path.home() / ".claude" / "desk_assistant_lang.json"

VALID_STATUSES = {"idle", "working", "done"}

DEFAULT_AGENT = "default"

# ── Bilingual text resources ─────────────────────────────────────────────

TEXTS = {
    "zh": {
        "title": "Claude 状态",
        "idle": "空闲",
        "working": "工作中",
        "complete": "已完成",
        "no_agents": "暂无 Agent",
        "click_add": '点 "+" 添加',
        "agent_header": "Agent:",
        "add_agent": "添加 Agent...",
        "add_agent_title": "添加 Agent",
        "add_agent_prompt": "Agent 名称:",
        "remove_agent": "删除 Agent...",
        "remove_agent_title": "删除 Agent",
        "remove_confirm": '确认删除 "{}"?',
        "remove_btn": "删除",
        "cancel_btn": "取消",
        "exit": "退出",
        "status_bar": "{} 个 Agent | {} 个工作中",
        "set_idle": "[空闲] 设为空闲",
        "set_working": "[工作中] 设为工作中",
        "set_complete": "[已完成] 设为已完成",
        "lang_toggle": "切换 English",
        "status_file_label": "状态文件:",
        "usage": "用法:",
        "positional_status": "[idle|working|done]",
        "positional_command": "[list|remove]",
        "options": "选项:",
        "opt_agent": "  -a, --agent NAME   目标 Agent 名称",
        "opt_lang": "  -l, --lang zh|en   输出语言",
        "list_title": "=== Claude 多 Agent 状态监控 ===",
        "list_no_registered": "还没有注册的 Agent。",
        "list_create_hint": "创建方法: python status_updater.py idle  (创建默认 Agent)",
        "list_col_agent": "Agent",
        "list_col_status": "状态",
        "list_col_light": "灯光",
        "list_col_updated": "更新时间",
        "removed_ok": "Agent 已删除:",
        "removed_not_found": "Agent 不存在:",
        "err_agent_required": "[错误] --agent 需要指定名称",
        "err_unknown_cmd": "[错误] 未知命令/状态:",
        "err_no_command": "[错误] 没有指定命令",
        "err_invalid_status": "[错误] 无效状态:",
        "err_valid_values": "  有效值:",
        "status_updated": "状态已更新",
        "agent_label": "Agent",
        "remove_agent_cli": "删除 Agent",
    },
    "en": {
        "title": "Claude Agents",
        "idle": "Idle",
        "working": "Working",
        "complete": "Complete",
        "no_agents": "No agents",
        "click_add": 'Click "+" to add',
        "agent_header": "Agent:",
        "add_agent": "Add Agent...",
        "add_agent_title": "Add Agent",
        "add_agent_prompt": "Agent name:",
        "remove_agent": "Remove Agent...",
        "remove_agent_title": "Remove Agent",
        "remove_confirm": 'Remove "{}"?',
        "remove_btn": "Remove",
        "cancel_btn": "Cancel",
        "exit": "Exit",
        "status_bar": "{} agent(s) | {} working",
        "set_idle": "[IDLE]  Set Idle",
        "set_working": "[WORK] Set Working",
        "set_complete": "[DONE] Set Complete",
        "lang_toggle": "Switch to 中文",
        "status_file_label": "Status File:",
        "usage": "Usage:",
        "positional_status": "[idle|working|done]",
        "positional_command": "[list|remove]",
        "options": "Options:",
        "opt_agent": "  -a, --agent NAME   Target agent name",
        "opt_lang": "  -l, --lang zh|en   Output language",
        "list_title": "=== Claude Multi-Agent Status Monitor ===",
        "list_no_registered": "No agents registered yet.",
        "list_create_hint": "Create: python status_updater.py idle  (creates default agent)",
        "list_col_agent": "Agent",
        "list_col_status": "Status",
        "list_col_light": "Light",
        "list_col_updated": "Updated",
        "removed_ok": "Removed agent:",
        "removed_not_found": "Agent not found:",
        "err_agent_required": "[ERROR] --agent requires a name",
        "err_unknown_cmd": "[ERROR] Unknown command/status:",
        "err_no_command": "[ERROR] No command given",
        "err_invalid_status": "[ERROR] Invalid status:",
        "err_valid_values": "  Valid:",
        "status_updated": "Status updated",
        "agent_label": "Agent",
        "remove_agent_cli": "Remove Agent",
    },
}

# light_name -> label key in TEXTS
LIGHT_LABEL_KEY = {
    "red":    "idle",
    "yellow": "working",
    "green":  "complete",
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

# GUI dimensions
WINDOW_WIDTH  = 230
CARD_HEIGHT   = 60
BASE_HEIGHT   = 80   # title bar + bottom margin


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
    key = LIGHT_LABEL_KEY.get(light_name, "idle")
    return t(key, lang)


# Keep for backward compatibility with old code references
LIGHT_CONFIG = {
    "red":    {"active": "#ff1a1a", "dim": "#2a0000", "glow": "#ff4444", "label": "Idle"},
    "yellow": {"active": "#ffcc00", "dim": "#2a2000", "glow": "#ffee44", "label": "Working"},
    "green":  {"active": "#00ff44", "dim": "#002a00", "glow": "#44ff66", "label": "Complete"},
}


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
