#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared config and file I/O for the tree-based project traffic light assistant.

Status file: ~/.claude/desk_assistant_status.json

Format:
  {"projects": {"name": {"status": "idle|working|done", "parent": null|"name",
               "timestamp": "...", "source": "..."}}}

Old formats auto-migrated on read.
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
DEFAULT_AGENT   = DEFAULT_PROJECT

SYNTHETIC_OVERVIEW = "__overview__"

# ── Bilingual text resources ─────────────────────────────────────────────

TEXTS = {
    "zh": {
        "title_single": "{}",
        "title_multi": "项目",
        "idle": "空闲",
        "working": "工作中",
        "complete": "已完成",
        "no_projects": "暂无项目",
        "click_add": "点 \"+\" 添加",
        "project_header": "项目:",
        "add_project": "添加项目...",
        "add_project_title": "添加项目",
        "add_project_prompt": "项目名称:",
        "remove_project": "删除项目...",
        "remove_project_title": "删除项目",
        "remove_confirm": "确认删除 \"{}\"?",
        "remove_btn": "删除",
        "cancel_btn": "取消",
        "exit": "退出",
        "status_bar": "{n} 个项目 | {active_count} 个工作中",
        "set_idle": "[空闲] 设为空闲",
        "set_working": "[工作中] 设为工作中",
        "set_complete": "[已完成] 设为已完成",
        "lang_toggle": "切换 English",
        # Tree UI
        "overview_title": "总览",
        "child_count": "({n})",
        "removing_in": "{n}秒后移除...",
        "add_child": "添加子任务...",
        "add_child_title": "添加子任务",
        "add_child_prompt": "子任务名称:",
        "expand_all": "展开全部",
        "collapse_all": "折叠全部",
        "aggregate": "汇总",
        # CLI
        "list_title": "=== Claude 项目状态监控 ===",
        "list_no_registered": "还没有注册的项目。",
        "list_create_hint": "创建方法: python status_updater.py idle  (创建默认项目)",
        "list_col_project": "项目",
        "list_col_status": "状态",
        "list_col_light": "灯光",
        "list_col_updated": "更新时间",
        "list_col_parent": "父项目",
        "removed_ok": "项目已删除:",
        "removed_not_found": "项目不存在:",
        "removed_children": "  同时移除了 {n} 个子任务",
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
        "opt_parent": "  -p, --parent NAME  父项目名称",
        "opt_lang": "  -l, --lang zh|en   输出语言",
        "light_idle": "空闲",
        "light_working": "工作中",
        "light_complete": "已完成",
    },
    "en": {
        "title_single": "{}",
        "title_multi": "Projects",
        "idle": "Idle",
        "working": "Working",
        "complete": "Complete",
        "no_projects": "No projects",
        "click_add": "Click \"+\" to add",
        "project_header": "Project:",
        "add_project": "Add Project...",
        "add_project_title": "Add Project",
        "add_project_prompt": "Project name:",
        "remove_project": "Remove Project...",
        "remove_project_title": "Remove Project",
        "remove_confirm": "Remove \"{}\"?",
        "remove_btn": "Remove",
        "cancel_btn": "Cancel",
        "exit": "Exit",
        "status_bar": "{n} project(s) | {active_count} working",
        "set_idle": "[IDLE]  Set Idle",
        "set_working": "[WORK] Set Working",
        "set_complete": "[DONE] Set Complete",
        "lang_toggle": "Switch to 中文",
        # Tree UI
        "overview_title": "Overview",
        "child_count": "({n})",
        "removing_in": "Removing in {n}s...",
        "add_child": "Add Child...",
        "add_child_title": "Add Child",
        "add_child_prompt": "Child name:",
        "expand_all": "Expand All",
        "collapse_all": "Collapse All",
        "aggregate": "Aggregate",
        # CLI
        "list_title": "=== Claude Project Status Monitor ===",
        "list_no_registered": "No projects registered yet.",
        "list_create_hint": "Create: python status_updater.py idle  (creates default project)",
        "list_col_project": "Project",
        "list_col_status": "Status",
        "list_col_light": "Light",
        "list_col_updated": "Updated",
        "list_col_parent": "Parent",
        "removed_ok": "Removed project:",
        "removed_not_found": "Project not found:",
        "removed_children": "  Also removed {n} child(ren)",
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
        "opt_parent": "  -p, --parent NAME  Parent project name",
        "opt_lang": "  -l, --lang zh|en   Output language",
        "light_idle": "Idle",
        "light_working": "Working",
        "light_complete": "Complete",
    },
}

LIGHT_LABEL_KEY   = {"red": "light_idle", "yellow": "light_working", "green": "light_complete"}
STATUS_TO_ACTIVE  = {"idle": "red", "working": "yellow", "done": "green"}
STATUS_TEXT_KEY   = {"idle": "idle", "working": "working", "done": "complete"}
STATUS_COLORS     = {"idle": "#ff1a1a", "working": "#ffcc00", "done": "#00ff44"}
LIGHT_CONFIG      = {
    "red":    {"active": "#ff1a1a", "dim": "#2a0000", "glow": "#ff4444"},
    "yellow": {"active": "#ffcc00", "dim": "#2a2000", "glow": "#ffee44"},
    "green":  {"active": "#00ff44", "dim": "#002a00", "glow": "#44ff66"},
}

# ── GUI dimensions ──────────────────────────────────────────────────────
BASE_HEIGHT          = 80
CARD_WINDOW_WIDTH    = 230
CARD_HEIGHT          = 60
CHILD_INDENT         = 20   # pixel indent for child cards
TOGGLE_ZONE_WIDTH    = 30   # px from left edge for expand/collapse click

SINGLE_WINDOW_WIDTH  = 140
SINGLE_WINDOW_HEIGHT = 380
BIG_LIGHT_TOP        = 10
BIG_LIGHT_SPACING    = 80
BIG_LIGHT_CY_OFFSET  = 38
BIG_RING_R           = 32
BIG_GLOW1_R          = 28
BIG_GLOW2_R          = 24
BIG_CORE_R           = 20

# ── Multi-window positioning ───────────────────────────────────────────
WINDOW_SPACING_X  = 160     # horizontal gap between windows (+ window width)
WINDOW_SPACING_Y   = 400    # vertical gap when wrapping rows
WINDOWS_PER_ROW    = 4      # max windows per row before wrapping
WINDOW_START_X     = 100    # first window x
WINDOW_START_Y     = 100    # first window y

# ── Auto-remove ─────────────────────────────────────────────────────────
AUTO_REMOVE_DELAY = 5       # seconds before auto-removing done children
AUTO_REMOVE_TICK  = 1000    # ms between countdown updates

# ── Language helpers ────────────────────────────────────────────────────

def load_lang() -> str:
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
    LANG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump({"lang": lang}, f, ensure_ascii=False, indent=2)

def t(key: str, lang: str = None) -> str:
    if lang is None:
        lang = load_lang()
    return TEXTS.get(lang, TEXTS["zh"]).get(key, key)

def status_label(status: str, lang: str = None) -> str:
    return t(STATUS_TEXT_KEY.get(status, "idle"), lang)

def light_label(light_name: str, lang: str = None) -> str:
    return t(LIGHT_LABEL_KEY.get(light_name, "light_idle"), lang)

# ── Tree building ───────────────────────────────────────────────────────

def build_project_tree(projects: dict[str, dict]) -> list[dict]:
    """
    Build a tree from flat projects dict.

    Each project dict MAY have a 'parent' key.

    Returns list of root nodes:
      [{name, display_name, synthetic, children, status, project}]

    synthetic=True means it's a GUI-only overview, not a real project.
    """
    if not projects:
        return []

    has_parents = any(p.get("parent") for p in projects.values())

    if has_parents:
        return _build_explicit_tree(projects)
    elif len(projects) >= 2:
        return _build_auto_overview(projects)
    else:
        # Single project — no tree needed
        name = next(iter(projects))
        p = projects[name]
        return [{"name": name, "display_name": name, "synthetic": False,
                 "children": [], "status": p.get("status", "idle"), "project": p}]


def _build_auto_overview(projects: dict[str, dict]) -> list[dict]:
    """Auto-group all projects under a synthetic overview parent."""
    children = sorted(projects.keys())
    c_statuses = [projects[c].get("status", "idle") for c in children]
    agg = compute_aggregate_status(c_statuses)
    return [{
        "name": SYNTHETIC_OVERVIEW,
        "display_name": "总览",
        "synthetic": True,
        "children": children,
        "status": agg,
        "project": None,
    }]


def _build_explicit_tree(projects: dict[str, dict]) -> list[dict]:
    """Build tree from explicit parent fields."""
    children_of: dict[str, list[str]] = {}
    roots: list[str] = []

    for name in projects:
        parent = projects[name].get("parent")
        if parent and parent in projects:
            children_of.setdefault(parent, []).append(name)
        else:
            roots.append(name)

    result = []
    for name in sorted(roots):
        kids = sorted(children_of.get(name, []))
        c_statuses = [projects[c].get("status", "idle") for c in kids]
        agg = compute_aggregate_status(c_statuses) if kids else projects[name].get("status", "idle")
        result.append({
            "name": name, "display_name": name, "synthetic": False,
            "children": kids, "status": agg,
            "project": projects[name],
        })
    return result


def compute_aggregate_status(child_statuses: list[str]) -> str:
    """Compute parent status: any working->yellow, all done->green, else red."""
    if not child_statuses:
        return "idle"
    if any(s == "working" for s in child_statuses):
        return "working"
    if all(s == "done" for s in child_statuses):
        return "done"
    return "idle"


def localize_overview(lang: str = None) -> str:
    return t("overview_title", lang)

# ── File I/O ──────────────────────────────────────────────────────────────

def _normalize_key(data: dict) -> dict:
    if "projects" in data:
        return data
    if "agents" in data:
        data["projects"] = data.pop("agents")
        return data
    return data


def read_status_file() -> dict[str, dict]:
    if not STATUS_FILE.exists():
        return {}

    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

    data = _normalize_key(data)

    if "projects" not in data:
        if "status" in data:
            return {DEFAULT_PROJECT: {
                "status": data.get("status", "idle"),
                "timestamp": data.get("timestamp", ""),
                "source": data.get("source", "migrated"),
                "parent": None,
            }}
        return {}

    # Ensure every project has parent field
    for name in list(data["projects"]):
        if "parent" not in data["projects"][name]:
            data["projects"][name]["parent"] = None

    return data.get("projects", {})


def write_status_file(projects: dict[str, dict]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"projects": projects}
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(STATUS_FILE.parent), prefix=".desk_status_",
            suffix=".tmp", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(STATUS_FILE))
    except Exception:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


def update_project_status(name: str, status: str, source: str = "unknown",
                          parent: str | None = None) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    projects = read_status_file()
    entry = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "source": source,
    }
    # Preserve existing parent if not explicitly provided
    existing = projects.get(name, {})
    if parent is not None:
        entry["parent"] = parent if parent else None
    elif "parent" in existing:
        entry["parent"] = existing["parent"]
    else:
        entry["parent"] = None

    projects[name] = entry
    write_status_file(projects)


def remove_project(name: str) -> tuple[bool, list[str]]:
    """Remove a project. Returns (ok, removed_children_names)."""
    projects = read_status_file()
    if name not in projects:
        return False, []

    # Find and remove children
    removed_children = []
    for pname in list(projects.keys()):
        if pname != name and projects[pname].get("parent") == name:
            removed_children.append(pname)
            del projects[pname]

    del projects[name]
    removed_children.sort()
    write_status_file(projects)
    return True, removed_children


# ── Backward-compat aliases ────────────────────────────────────────────

update_agent_status = update_project_status
remove_agent = remove_project
