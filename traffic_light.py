#!/usr/bin/env python3
"""
Tree-based Project Traffic Light Desktop Assistant.
Red = Idle | Yellow = Working | Green = Complete

Auto-detects projects, groups them under "Overview" parent.
Expand/collapse children. Auto-removes completed sub-tasks after 5s.

Reads/Writes ~/.claude/desk_assistant_status.json
"""

import tkinter as tk
from tkinter import simpledialog
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg


class ProjectTrafficApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Project Status Monitor")
        self.root.configure(bg="#0d0d0d")

        self.lang = cfg.load_lang()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Flattened project data from file
        self.projects: dict[str, dict] = {}
        self.project_order: list[str] = []

        # Tree state
        self.tree_roots: list[dict] = []
        self.display_order: list[str] = []   # flattened visible order
        self.expanded: set[str] = set()      # expanded parent names
        self.tree_mode = False
        self.last_count = 0

        # Auto-remove state
        self._done_since: dict[str, float] = {}
        self._countdown: dict[str, int] = {}
        self._cd_timers: dict[str, str] = {}

        # Drag
        self._drag_x = 0
        self._drag_y = 0

        # Load data
        self._reload_from_file()
        self._build_tree()
        self._resize_window()
        self.root.geometry(f"+100+100")

        # Bindings
        self.root.bind("<Button-1>", self._on_left_click)
        self.root.bind("<B1-Motion>", self._on_drag)
        self.root.bind("<Button-3>", self._on_right_click)

        # Build UI
        self._build_ui()
        self._draw_content()
        self._update_status_bar()
        self.last_count = len(self.project_order)

        # Poll
        self._poll_status_file()

    def _(self, key, **kwargs):
        s = cfg.t(key, self.lang)
        if kwargs:
            s = s.format(**kwargs)
        return s

    # ── UI Shell ────────────────────────────────────────────────────────

    def _build_ui(self):
        self.bg_frame = tk.Frame(self.root, bg="#0d0d0d", highlightthickness=1,
                                 highlightbackground="#333333", highlightcolor="#333333")
        self.bg_frame.pack(fill="both", expand=True)

        # Title bar
        self.title_bar = tk.Frame(self.bg_frame, bg="#0d0d0d", height=30)
        self.title_bar.pack(fill="x", padx=8, pady=(8, 0))
        self.title_bar.pack_propagate(False)

        self.title_label = tk.Label(self.title_bar, text="", bg="#0d0d0d",
                                    fg="#888888", font=("Microsoft YaHei UI", 9, "bold"))
        self.title_label.pack(side="left")

        # Lang toggle
        lang_btn = tk.Label(self.title_bar, text="EN" if self.lang == "zh" else "中",
                            bg="#0d0d0d", fg="#888888",
                            font=("Microsoft YaHei UI", 8, "bold"), cursor="hand2")
        lang_btn.pack(side="right", padx=(0, 6))
        lang_btn.bind("<Button-1>", lambda e: self._toggle_language())
        lang_btn.bind("<Enter>", lambda e: lang_btn.config(fg="#ffcc00"))
        lang_btn.bind("<Leave>", lambda e: lang_btn.config(fg="#888888"))

        # Add project
        add_btn = tk.Label(self.title_bar, text="+", bg="#0d0d0d", fg="#666666",
                           font=("Arial", 12, "bold"), cursor="hand2")
        add_btn.pack(side="right", padx=(0, 4))
        add_btn.bind("<Button-1>", lambda e: self._gui_add_project())
        add_btn.bind("<Enter>", lambda e: add_btn.config(fg="#44ff66"))
        add_btn.bind("<Leave>", lambda e: add_btn.config(fg="#666666"))

        # Close
        close_btn = tk.Label(self.title_bar, text="X", bg="#0d0d0d", fg="#666666",
                             font=("Arial", 10), cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.root.quit())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ff4444"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#666666"))

        # Separator
        tk.Frame(self.bg_frame, bg="#222222", height=1).pack(fill="x", padx=10, pady=(6, 4))

        # Canvas
        self.canvas = tk.Canvas(self.bg_frame, bg="#0d0d0d", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=2)

        # Status bar
        tk.Frame(self.bg_frame, bg="#222222", height=1).pack(fill="x", padx=10, pady=(4, 4))
        self.status_label = tk.Label(self.bg_frame, text="", bg="#0d0d0d",
                                     fg="#555555", font=("Microsoft YaHei UI", 7), anchor="w")
        self.status_label.pack(fill="x", padx=8, pady=(0, 6))

        self._update_title()

    # ── Language ─────────────────────────────────────────────────────────

    def _toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        cfg.save_lang(self.lang)
        self._update_title()
        for child in self.title_bar.winfo_children():
            if isinstance(child, tk.Label) and child.cget("text") in ("EN", "中"):
                child.config(text="EN" if self.lang == "zh" else "中")
        self._draw_content()
        self._update_status_bar()

    def _update_title(self):
        n = len(self.project_order)
        if n <= 1 and not self.tree_mode:
            name = self.project_order[0] if self.project_order else ""
            self.title_label.config(text=self._("title_single").replace("{}", name))
        else:
            self.title_label.config(text=self._("title_multi"))

    # ── Tree Building ────────────────────────────────────────────────────

    def _build_tree(self):
        """Build tree structure from flat projects."""
        roots = cfg.build_project_tree(self.projects)

        # Localize overview display name
        for r in roots:
            if r["synthetic"]:
                r["display_name"] = cfg.localize_overview(self.lang)

        self.tree_roots = roots
        self.tree_mode = (len(roots) >= 1 and
                          (roots[0]["synthetic"] or len(roots) > 1 or roots[0].get("children")))

        # Keep expanded set clean
        valid = {r["name"] for r in roots if r.get("children")}
        self.expanded &= valid

        # Build display order
        self._rebuild_display_order()

    def _rebuild_display_order(self):
        order = []
        for r in self.tree_roots:
            order.append(r["name"])
            if r["name"] in self.expanded:
                for child in r.get("children", []):
                    order.append(child)
        self.display_order = order

    def _real_project_count(self) -> int:
        """Count real (non-synthetic) projects."""
        return len(self.projects)

    def _visible_rows(self) -> int:
        return len(self.display_order) if self.display_order else (0 if not self.project_order else 1)

    def _active_working_count(self) -> int:
        return sum(1 for p in self.projects.values() if p.get("status") == "working")

    # ── Content Drawing ──────────────────────────────────────────────────

    def _draw_content(self):
        self.canvas.delete("content")
        self._build_tree()
        self._rebuild_display_order()

        n = self._real_project_count()

        if self.tree_mode:
            self._draw_tree()
        elif n == 1:
            self._draw_single_light()
        elif n == 0:
            self._draw_empty()
        else:
            # Fallback: multi-card (shouldn't normally hit this)
            self._draw_tree()

    def _draw_empty(self):
        w = self._canvas_width()
        self.canvas.create_text(w // 2, 20, text=self._("no_projects"),
                                fill="#444444", font=("Microsoft YaHei UI", 9), tags="content")
        self.canvas.create_text(w // 2, 38, text=self._("click_add"),
                                fill="#333333", font=("Microsoft YaHei UI", 7), tags="content")

    # ── Single Big Light ─────────────────────────────────────────────────

    def _draw_single_light(self):
        name = self.project_order[0]
        status = self.projects.get(name, {}).get("status", "idle")
        active_light = cfg.STATUS_TO_ACTIVE.get(status, "red")
        w = cfg.SINGLE_WINDOW_WIDTH - 4
        cx = w // 2

        self.canvas.create_text(cx, 14, text=name, fill="#aaaaaa",
                                font=("Microsoft YaHei UI", 10, "bold"), tags="content")

        light_names = ["red", "yellow", "green"]
        for i, lname in enumerate(light_names):
            y_top = cfg.BIG_LIGHT_TOP + i * cfg.BIG_LIGHT_SPACING + 24
            cy = y_top + cfg.BIG_LIGHT_CY_OFFSET
            is_active = (lname == active_light)
            c = cfg.LIGHT_CONFIG[lname]
            RR, G1R, G2R, COR = cfg.BIG_RING_R, cfg.BIG_GLOW1_R, cfg.BIG_GLOW2_R, cfg.BIG_CORE_R

            if is_active:
                self.canvas.create_oval(cx - RR - 2, cy - RR - 2, cx + RR + 2, cy + RR + 2,
                                        fill="#1a1a1a", outline=c["glow"], width=2, tags="content")
                self.canvas.create_oval(cx - G1R, cy - G1R, cx + G1R, cy + G1R,
                                        fill=c["glow"], outline="", tags="content")
                self.canvas.create_oval(cx - G2R, cy - G2R, cx + G2R, cy + G2R,
                                        fill=c["active"], outline="", tags="content")
                self.canvas.create_oval(cx - COR, cy - COR, cx + COR, cy + COR,
                                        fill="#ffffff", outline="", tags="content")
            else:
                self.canvas.create_oval(cx - RR - 1, cy - RR - 1, cx + RR + 1, cy + RR + 1,
                                        fill="#0d0d0d", outline="#222222", width=1, tags="content")
                self.canvas.create_oval(cx - RR, cy - RR, cx + RR, cy + RR,
                                        fill="#0d0d0d", outline="", tags="content")
                self.canvas.create_oval(cx - COR, cy - COR, cx + COR, cy + COR,
                                        fill="#1a1a1a", outline="", tags="content")

            label_text = cfg.light_label(lname, self.lang)
            self.canvas.create_text(cx, y_top + cfg.BIG_LIGHT_CY_OFFSET + 38,
                                    text=label_text, fill="#555555",
                                    font=("Microsoft YaHei UI", 7), tags="content")

        status_text = cfg.status_label(status, self.lang)
        status_color = cfg.STATUS_COLORS.get(status, "#888888")
        self.canvas.create_text(cx, cfg.SINGLE_WINDOW_HEIGHT - cfg.BASE_HEIGHT - 10,
                                text=status_text, fill=status_color,
                                font=("Microsoft YaHei UI", 9, "bold"), tags="content")

    # ── Tree Mode Drawing ────────────────────────────────────────────────

    def _draw_tree(self):
        if not self.display_order:
            self._draw_empty()
            return

        w = cfg.CARD_WINDOW_WIDTH - 4
        for idx, name in enumerate(self.display_order):
            y0 = idx * cfg.CARD_HEIGHT
            node_info = self._get_node_info(name)

            if node_info.get("synthetic"):
                self._draw_parent_card(name, node_info, y0, w)
            elif self._is_child(name):
                self._draw_child_card(name, node_info, y0, w)
            else:
                self._draw_child_card(name, node_info, y0, w, indent=0)

    def _get_node_info(self, name: str) -> dict:
        """Get combined node info (tree node + project data)."""
        for r in self.tree_roots:
            if r["name"] == name:
                return r
            for c in r.get("children", []):
                if c == name:
                    return {"name": name, "display_name": name, "synthetic": False,
                            "children": [], "project": self.projects.get(name, {}),
                            "status": self.projects.get(name, {}).get("status", "idle")}
        return {"name": name, "display_name": name, "synthetic": False,
                "children": [], "status": "idle", "project": self.projects.get(name, {})}

    def _is_child(self, name: str) -> bool:
        for r in self.tree_roots:
            if name in r.get("children", []):
                return True
        return False

    def _draw_parent_card(self, name: str, node: dict, y0: int, w: int):
        """Overview card with expand/collapse toggle."""
        expanded = name in self.expanded
        toggle = "V" if expanded else ">"
        children = node.get("children", [])
        status = node.get("status", "idle")
        active_light = cfg.STATUS_TO_ACTIVE.get(status, "red")
        tag = f"parent_{name}"

        # Background
        self.canvas.create_rectangle(2, y0, w, y0 + cfg.CARD_HEIGHT - 2,
                                     fill="#0f0f0f", outline="", tags=("content", tag))
        # Highlight left edge
        self.canvas.create_rectangle(2, y0, 4, y0 + cfg.CARD_HEIGHT - 2,
                                     fill="#333333", outline="", tags=("content", tag))

        # Toggle zone (clickable)
        self.canvas.create_rectangle(4, y0, cfg.TOGGLE_ZONE_WIDTH, y0 + cfg.CARD_HEIGHT - 2,
                                     fill="", outline="", tags=("content", f"{tag}_toggle"))

        # Toggle symbol
        self.canvas.create_text(14, y0 + cfg.CARD_HEIGHT // 2, text=toggle,
                                fill="#888888", font=("Arial", 10, "bold"),
                                tags=("content", tag))

        # Name + child count
        display = node.get("display_name", name)
        count_text = self._("child_count").replace("{n}", str(len(children))) if children else ""
        full_text = f"{display} {count_text}" if count_text else display
        self.canvas.create_text(35, y0 + 22, text=full_text, anchor="w",
                                fill="#cccccc", font=("Microsoft YaHei UI", 9, "bold"),
                                tags=("content", tag))
        # Aggregate label
        agg_text = self._("aggregate")
        self.canvas.create_text(35, y0 + 42, text=agg_text, anchor="w",
                                fill="#666666", font=("Microsoft YaHei UI", 7),
                                tags=("content", tag))

        # 3 mini lights (right-aligned)
        light_cx = {"red": 100, "yellow": 122, "green": 144}
        cy = y0 + 32
        RING_R = 9
        for lname in ["red", "yellow", "green"]:
            cx = light_cx[lname]
            is_active = (lname == active_light)
            c = cfg.LIGHT_CONFIG[lname]
            if is_active:
                self.canvas.create_oval(cx - RING_R - 2, cy - RING_R - 2,
                                        cx + RING_R + 2, cy + RING_R + 2,
                                        fill="#1a1a1a", outline=c["glow"], width=1, tags=("content", tag))
                self.canvas.create_oval(cx - RING_R, cy - RING_R, cx + RING_R, cy + RING_R,
                                        fill=c["glow"], outline="", tags=("content", tag))
                self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6,
                                        fill=c["active"], outline="", tags=("content", tag))
                self.canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                                        fill="#ffffff", outline="", tags=("content", tag))
            else:
                self.canvas.create_oval(cx - RING_R - 1, cy - RING_R - 1,
                                        cx + RING_R + 1, cy + RING_R + 1,
                                        fill="#0d0d0d", outline="#222222", width=1, tags=("content", tag))
                self.canvas.create_oval(cx - RING_R, cy - RING_R, cx + RING_R, cy + RING_R,
                                        fill="#0d0d0d", outline="", tags=("content", tag))
                self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                                        fill="#1a1a1a", outline="", tags=("content", tag))

        # Status text
        status_text = cfg.status_label(status, self.lang)
        status_color = cfg.STATUS_COLORS.get(status, "#888888")
        self.canvas.create_text(light_cx["yellow"], y0 + 50, text=status_text,
                                fill=status_color, font=("Microsoft YaHei UI", 7),
                                tags=("content", tag))

        # Separator
        self.canvas.create_line(8, y0 + cfg.CARD_HEIGHT - 2, w - 8, y0 + cfg.CARD_HEIGHT - 2,
                                fill="#1a1a1a", tags=("content", tag))

    def _draw_child_card(self, name: str, node: dict, y0: int, w: int, indent: int = None):
        """Compact child card with optional indent and edge line."""
        if indent is None:
            indent = cfg.CHILD_INDENT
        status = node.get("status", "idle")
        active_light = cfg.STATUS_TO_ACTIVE.get(status, "red")
        tag = f"child_{name}"

        # Background
        self.canvas.create_rectangle(indent, y0, w, y0 + cfg.CARD_HEIGHT - 2,
                                     fill="#0a0a0a", outline="", tags=("content", tag))
        if indent > 0:
            # Left edge accent line
            self.canvas.create_line(indent, y0 + 4, indent, y0 + cfg.CARD_HEIGHT - 6,
                                    fill="#2a2a2a", tags=("content", tag))

        # Name
        self.canvas.create_text(indent + 10, y0 + 18, text=name, anchor="w",
                                fill="#cccccc", font=("Microsoft YaHei UI", 8, "bold"),
                                tags=("content", tag))

        # Countdown or status label
        if name in self._done_since:
            remaining = self._countdown.get(name, 0)
            status_text = self._("removing_in").replace("{n}", str(remaining))
            status_color = "#ff8844"
        else:
            status_text = cfg.status_label(status, self.lang)
            status_color = cfg.STATUS_COLORS.get(status, "#888888")
        self.canvas.create_text(indent + 10, y0 + 38, text=status_text, anchor="w",
                                fill=status_color, font=("Microsoft YaHei UI", 7),
                                tags=("content", tag))

        # 3 mini lights (right-aligned, shifted by indent)
        light_cx = {"red": 100 + indent - 5, "yellow": 122 + indent - 5, "green": 144 + indent - 5}
        cy = y0 + 28
        RING_R = 8
        for lname in ["red", "yellow", "green"]:
            cx = light_cx[lname]
            is_active = (lname == active_light)
            c = cfg.LIGHT_CONFIG[lname]
            if is_active:
                self.canvas.create_oval(cx - RING_R - 1, cy - RING_R - 1,
                                        cx + RING_R + 1, cy + RING_R + 1,
                                        fill="#1a1a1a", outline=c["glow"], width=1, tags=("content", tag))
                self.canvas.create_oval(cx - RING_R, cy - RING_R, cx + RING_R, cy + RING_R,
                                        fill=c["glow"], outline="", tags=("content", tag))
                self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                                        fill=c["active"], outline="", tags=("content", tag))
                self.canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2,
                                        fill="#ffffff", outline="", tags=("content", tag))
            else:
                self.canvas.create_oval(cx - RING_R - 1, cy - RING_R - 1,
                                        cx + RING_R + 1, cy + RING_R + 1,
                                        fill="#0d0d0d", outline="#1a1a1a", width=1, tags=("content", tag))
                self.canvas.create_oval(cx - RING_R, cy - RING_R, cx + RING_R, cy + RING_R,
                                        fill="#0d0d0d", outline="", tags=("content", tag))
                self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                                        fill="#141414", outline="", tags=("content", tag))

        # Separator
        self.canvas.create_line(indent + 8, y0 + cfg.CARD_HEIGHT - 2,
                                w - 8, y0 + cfg.CARD_HEIGHT - 2,
                                fill="#151515", tags=("content", tag))

    # ── Window Sizing ───────────────────────────────────────────────────

    def _canvas_width(self) -> int:
        if self.tree_mode or self._real_project_count() > 1:
            return cfg.CARD_WINDOW_WIDTH - 4
        return cfg.SINGLE_WINDOW_WIDTH - 4

    def _resize_window(self):
        n = self._real_project_count()
        if n <= 1 and not self.tree_mode:
            w = cfg.SINGLE_WINDOW_WIDTH
            h = cfg.SINGLE_WINDOW_HEIGHT
        else:
            w = cfg.CARD_WINDOW_WIDTH
            rows = max(len(self.display_order), 1)
            h = cfg.BASE_HEIGHT + rows * cfg.CARD_HEIGHT

        self.root.geometry(f"{w}x{h}")
        if hasattr(self, "canvas"):
            self.canvas.configure(width=w - 4, height=h - cfg.BASE_HEIGHT)

    def _update_status_bar(self):
        n = self._real_project_count()
        active = self._active_working_count()
        self.status_label.config(text=self._("status_bar", n=n, active_count=active))

    # ── Drag & Click ────────────────────────────────────────────────────

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_pointerx() - self._drag_x
        y = self.root.winfo_pointery() - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _on_left_click(self, event):
        """Left click: toggle expand/collapse if in zone, else start drag."""
        if not self.tree_mode:
            self._start_drag(event)
            return

        canvas_y = event.y - self.canvas.winfo_y()
        canvas_x = event.x - self.canvas.winfo_x()

        # Find which row was clicked
        row = canvas_y // cfg.CARD_HEIGHT
        if 0 <= row < len(self.display_order):
            name = self.display_order[row]
            # Check if this is a parent with children, and click in toggle zone
            node = self._get_node_info(name)
            if node.get("synthetic") or node.get("children"):
                if canvas_x < cfg.TOGGLE_ZONE_WIDTH:
                    self._toggle_parent(name)
                    return

        self._start_drag(event)

    def _toggle_parent(self, name: str):
        if name in self.expanded:
            self.expanded.discard(name)
        else:
            self.expanded.add(name)
        self._rebuild_display_order()
        self._resize_window()
        self._draw_content()
        self._update_status_bar()
        self._write_to_file()

    # ── Right-click Menu ────────────────────────────────────────────────

    def _on_right_click(self, event):
        n = self._real_project_count()
        if n == 0:
            self._show_global_menu(event)
            return

        canvas_y = event.y - self.canvas.winfo_y()
        canvas_x = event.x - self.canvas.winfo_x()

        if n == 1 and not self.tree_mode:
            self._show_project_menu(event, self.project_order[0])
            return

        # Tree mode: determine which row
        row = canvas_y // cfg.CARD_HEIGHT
        if 0 <= row < len(self.display_order):
            name = self.display_order[row]
            node = self._get_node_info(name)
            if node.get("synthetic"):
                self._show_overview_menu(event, name, node)
            else:
                self._show_project_menu(event, name)
        else:
            self._show_global_menu(event)

    def _show_overview_menu(self, event, name: str, node: dict):
        menu = tk.Menu(self.root, tearoff=0, bg="#1e1e1e", fg="#cccccc",
                       activebackground="#333333", activeforeground="#ffffff")
        display = node.get("display_name", name)
        menu.add_command(label=f"{self._('project_header')} {display}",
                         state="disabled", disabledforeground="#888888")
        menu.add_separator()
        if name in self.expanded:
            menu.add_command(label=self._("collapse_all"),
                             command=lambda: self._toggle_parent(name))
        else:
            menu.add_command(label=self._("expand_all"),
                             command=lambda: self._toggle_parent(name))
        menu.add_command(label=self._("add_child"), command=lambda: self._gui_add_child(name))
        menu.add_separator()
        menu.add_command(label=self._("add_project"), command=self._gui_add_project)
        menu.add_separator()
        menu.add_command(label=self._("lang_toggle"), command=self._toggle_language)
        menu.add_separator()
        menu.add_command(label=self._("exit"), command=self.root.quit)
        menu.post(event.x_root, event.y_root)

    def _show_project_menu(self, event, name: str):
        menu = tk.Menu(self.root, tearoff=0, bg="#1e1e1e", fg="#cccccc",
                       activebackground="#333333", activeforeground="#ffffff")
        menu.add_command(label=f"{self._('project_header')} {name}",
                         state="disabled", disabledforeground="#888888")
        menu.add_separator()
        menu.add_command(label=self._("set_idle"),
                         command=lambda: self.set_status(name, "idle"))
        menu.add_command(label=self._("set_working"),
                         command=lambda: self.set_status(name, "working"))
        menu.add_command(label=self._("set_complete"),
                         command=lambda: self.set_status(name, "done"))
        menu.add_separator()
        menu.add_command(label=self._("add_project"), command=self._gui_add_project)
        menu.add_separator()
        menu.add_command(label=self._("remove_project"),
                         command=lambda: self._gui_remove_project(name))
        menu.add_separator()
        menu.add_command(label=self._("lang_toggle"), command=self._toggle_language)
        menu.add_separator()
        menu.add_command(label=self._("exit"), command=self.root.quit)
        menu.post(event.x_root, event.y_root)

    def _show_global_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg="#1e1e1e", fg="#cccccc",
                       activebackground="#333333", activeforeground="#ffffff")
        menu.add_command(label=self._("add_project"), command=self._gui_add_project)
        menu.add_separator()
        menu.add_command(label=self._("lang_toggle"), command=self._toggle_language)
        menu.add_separator()
        menu.add_command(label=self._("exit"), command=self.root.quit)
        menu.post(event.x_root, event.y_root)

    # ── GUI Actions ────────────────────────────────────────────────────

    def _gui_add_project(self):
        name = simpledialog.askstring(
            self._("add_project_title"),
            self._("add_project_prompt"),
            parent=self.root,
        )
        if name and name.strip():
            name = name.strip()
            if name not in self.projects:
                self.projects[name] = {"status": "idle", "parent": None,
                                       "timestamp": "", "source": "traffic_light_app"}
                self._after_change()

    def _gui_add_child(self, parent_name: str):
        name = simpledialog.askstring(
            self._("add_child_title"),
            self._("add_child_prompt"),
            parent=self.root,
        )
        if name and name.strip():
            name = name.strip()
            if name not in self.projects:
                parent = None if parent_name == cfg.SYNTHETIC_OVERVIEW else parent_name
                self.projects[name] = {"status": "idle", "parent": parent,
                                       "timestamp": "", "source": "traffic_light_app"}
                self._after_change()

    def _gui_remove_project(self, name: str):
        confirm = tk.Toplevel(self.root)
        confirm.title(self._("remove_project_title"))
        confirm.geometry("240x100")
        confirm.configure(bg="#1e1e1e")
        confirm.overrideredirect(True)
        confirm.geometry(f"+{self.root.winfo_x() + 30}+{self.root.winfo_y() + 80}")

        tk.Label(confirm, text=self._("remove_confirm").replace("{}", name),
                 bg="#1e1e1e", fg="#cccccc",
                 font=("Microsoft YaHei UI", 9)).pack(pady=(12, 6))

        btn_frame = tk.Frame(confirm, bg="#1e1e1e")
        btn_frame.pack()

        def do_remove():
            # Cancel any auto-remove for this project
            self._cancel_auto_remove(name)
            if name in self.projects:
                del self.projects[name]
            # Remove children from memory too
            for n in list(self.projects.keys()):
                if self.projects[n].get("parent") == name:
                    self._cancel_auto_remove(n)
                    del self.projects[n]
            cfg.remove_project(name)
            self._after_change()
            confirm.destroy()

        tk.Button(btn_frame, text=self._("remove_btn"), command=do_remove,
                  bg="#ff4444", fg="#ffffff", relief="flat", padx=12).pack(side="left", padx=4)
        tk.Button(btn_frame, text=self._("cancel_btn"), command=confirm.destroy,
                  bg="#333333", fg="#cccccc", relief="flat", padx=12).pack(side="left", padx=4)

    # ── Status Control ──────────────────────────────────────────────────

    def set_status(self, name: str, status: str):
        if status not in cfg.VALID_STATUSES:
            return
        self.projects[name]["status"] = status
        cfg.update_project_status(name, status, source="traffic_light_app",
                                  parent=self.projects[name].get("parent"))

        # If changed to non-done, cancel auto-remove
        if status != "done" and name in self._done_since:
            self._cancel_auto_remove(name)

        self._build_tree()
        self._rebuild_display_order()
        self._resize_window()
        self._draw_content()
        self._update_status_bar()

    def _after_change(self):
        """Rebuild and redraw after project add/remove."""
        self._build_tree()
        self._rebuild_display_order()
        self._resize_window()
        self._draw_content()
        self._update_title()
        self._update_status_bar()
        self._write_to_file()
        self.last_count = self._real_project_count()

    # ── Auto-Remove Engine ──────────────────────────────────────────────

    def _check_auto_remove(self):
        """Check all projects for auto-remove eligibility."""
        now = time.time()
        for name in list(self.projects.keys()):
            # Skip synthetic parents
            is_synthetic = any(r["name"] == name and r["synthetic"]
                               for r in self.tree_roots)
            if is_synthetic:
                continue

            status = self.projects[name].get("status", "idle")

            if status == "done":
                if name not in self._done_since:
                    self._start_auto_remove(name)
                elif now - self._done_since[name] >= cfg.AUTO_REMOVE_DELAY:
                    self._execute_remove(name)
                # else: still counting down — display is updated in _draw_content
            else:
                if name in self._done_since:
                    self._cancel_auto_remove(name)

    def _start_auto_remove(self, name: str):
        self._done_since[name] = time.time()
        self._countdown[name] = cfg.AUTO_REMOVE_DELAY
        self._schedule_countdown_tick(name)

    def _schedule_countdown_tick(self, name: str):
        if name not in self._done_since:
            return
        elapsed = time.time() - self._done_since[name]
        remaining = max(0, cfg.AUTO_REMOVE_DELAY - int(elapsed))
        self._countdown[name] = remaining
        # Redraw to show updated countdown
        self._draw_content()
        if remaining > 0:
            tid = self.root.after(cfg.AUTO_REMOVE_TICK,
                                  lambda: self._schedule_countdown_tick(name))
            self._cd_timers[name] = tid

    def _execute_remove(self, name: str):
        """Remove project from memory and file."""
        self._cancel_auto_remove(name)
        if name in self.projects:
            del self.projects[name]
        cfg.remove_project(name)
        self._after_change()

    def _cancel_auto_remove(self, name: str):
        self._done_since.pop(name, None)
        self._countdown.pop(name, None)
        tid = self._cd_timers.pop(name, None)
        if tid:
            try:
                self.root.after_cancel(tid)
            except Exception:
                pass

    # ── File Sync ──────────────────────────────────────────────────────

    def _write_to_file(self):
        # Filter out synthetic overview
        real = {k: v for k, v in self.projects.items()}
        cfg.write_status_file(real)

    def _reload_from_file(self):
        file_projects = cfg.read_status_file()

        old_names = set(self.projects.keys())
        new_names = set(file_projects.keys())
        added = new_names - old_names
        removed = old_names - new_names

        self.projects = file_projects
        # Maintain order: remove deleted, append new
        self.project_order = [n for n in self.project_order if n not in removed]
        for n in sorted(added):
            if n not in self.project_order:
                self.project_order.append(n)

        changed = bool(added or removed or self._status_changed(file_projects))
        # Also check auto-remove state changes
        for name in list(self._done_since.keys()):
            if name not in self.projects:
                self._cancel_auto_remove(name)
            elif self.projects[name].get("status") != "done":
                self._cancel_auto_remove(name)

        return changed

    def _status_changed(self, file_projects: dict) -> bool:
        for name, data in file_projects.items():
            old = self.projects.get(name, {}).get("status")
            new = data.get("status")
            if old != new:
                return True
        return False

    def _poll_status_file(self):
        try:
            changed = self._reload_from_file()
            self._check_auto_remove()
            if changed or self._done_since:
                was_single = self.last_count <= 1 and not self.tree_mode
                self._build_tree()
                self._rebuild_display_order()
                is_single = self._real_project_count() <= 1 and not self.tree_mode
                if was_single != is_single:
                    self._resize_window()
                self._draw_content()
                self._update_title()
                self._update_status_bar()
                self.last_count = self._real_project_count()
        except Exception:
            pass
        self.root.after(1000, self._poll_status_file)

    # ── Run ────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


def main():
    app = ProjectTrafficApp()
    app.run()


if __name__ == "__main__":
    main()
