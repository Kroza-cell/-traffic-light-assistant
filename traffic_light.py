#!/usr/bin/env python3
"""
Multi-Agent Traffic Light Desktop Assistant
Red = Idle | Yellow = Working | Green = Complete

Each agent is shown as a compact card with 3 mini horizontal lights.
Reads/Writes ~/.claude/desk_assistant_status.json
"""

import tkinter as tk
from tkinter import simpledialog
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg


class MultiAgentTrafficApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Claude Multi-Agent Monitor")
        self.root.configure(bg="#0d0d0d")

        # Borderless + always-on-top
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Internal state
        self.agents: dict[str, dict] = {}       # agent_name -> {status, timestamp, source}
        self.agent_order: list[str] = []         # insertion order
        self._drag_x = 0
        self._drag_y = 0

        # Load initial state
        self._reload_from_file()

        # Set initial window size
        self._resize_window()

        # Position window
        self.root.geometry(f"+100+100")

        # ---- Drag support ----
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._on_drag)

        # ---- Right-click on canvas ----
        self.root.bind("<Button-3>", self._on_right_click)

        # ---- Build UI ----
        self._build_ui()
        self._draw_all_cards()
        self._update_title()

        # ---- Start polling ----
        self._poll_status_file()

    # ── UI Construction ───────────────────────────────────────────────

    def _build_ui(self):
        """Create the static UI shell: title bar + canvas."""
        # Outer frame
        self.bg_frame = tk.Frame(self.root, bg="#0d0d0d", highlightthickness=1,
                                 highlightbackground="#333333", highlightcolor="#333333")
        self.bg_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Title bar
        self.title_bar = tk.Frame(self.bg_frame, bg="#0d0d0d", height=30)
        self.title_bar.pack(fill="x", padx=8, pady=(8, 0))
        self.title_bar.pack_propagate(False)

        self.title_label = tk.Label(self.title_bar, text="Claude Agents",
                                    bg="#0d0d0d", fg="#888888",
                                    font=("Microsoft YaHei UI", 9, "bold"))
        self.title_label.pack(side="left")

        # Add agent button [+]
        add_btn = tk.Label(self.title_bar, text="+", bg="#0d0d0d", fg="#666666",
                           font=("Arial", 12, "bold"), cursor="hand2")
        add_btn.pack(side="right", padx=(0, 4))
        add_btn.bind("<Button-1>", lambda e: self._gui_add_agent())
        add_btn.bind("<Enter>", lambda e: add_btn.config(fg="#44ff66"))
        add_btn.bind("<Leave>", lambda e: add_btn.config(fg="#666666"))

        # Close button
        close_btn = tk.Label(self.title_bar, text="X", bg="#0d0d0d", fg="#666666",
                             font=("Arial", 10), cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.root.quit())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ff4444"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#666666"))

        # Separator
        tk.Frame(self.bg_frame, bg="#222222", height=1).pack(fill="x", padx=10, pady=(6, 4))

        # Scrollable canvas for agent cards
        self.canvas = tk.Canvas(self.bg_frame, width=cfg.WINDOW_WIDTH - 4,
                                bg="#0d0d0d", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=2)

        # Bottom status bar
        tk.Frame(self.bg_frame, bg="#222222", height=1).pack(fill="x", padx=10, pady=(4, 4))
        self.status_label = tk.Label(self.bg_frame, text="",
                                     bg="#0d0d0d", fg="#555555",
                                     font=("Microsoft YaHei UI", 7), anchor="w")
        self.status_label.pack(fill="x", padx=8, pady=(0, 6))

    # ── Card Drawing ──────────────────────────────────────────────────

    def _draw_all_cards(self):
        """Full redraw of all agent cards."""
        self.canvas.delete("card")
        self._card_elements: dict[str, dict] = {}  # agent_name -> {red: {ring,glow1,glow2,core}, yellow:..., green:..., label, name_text}

        if not self.agent_order:
            self.canvas.create_text(
                cfg.WINDOW_WIDTH // 2 - 2, 20,
                text="No agents", fill="#444444",
                font=("Microsoft YaHei UI", 9), tags="card"
            )
            self.canvas.create_text(
                cfg.WINDOW_WIDTH // 2 - 2, 38,
                text='Click "+" to add', fill="#333333",
                font=("Microsoft YaHei UI", 7), tags="card"
            )
            return

        for idx, name in enumerate(self.agent_order):
            data = self.agents.get(name, {})
            status = data.get("status", "idle")
            self._draw_one_card(name, status, idx)

    def _draw_one_card(self, agent_name: str, status: str, row_index: int):
        """Draw a single agent card at the given row index."""
        y0 = row_index * cfg.CARD_HEIGHT
        active_light = cfg.STATUS_TO_ACTIVE.get(status, "red")
        cfg_lights = cfg.LIGHT_CONFIG
        w = cfg.WINDOW_WIDTH - 4

        # Card background (subtle)
        bg_tag = f"card_{agent_name}"
        self.canvas.create_rectangle(
            0, y0, w, y0 + cfg.CARD_HEIGHT - 2,
            fill="#0f0f0f", outline="", tags=("card", bg_tag)
        )

        # Agent name
        self.canvas.create_text(
            10, y0 + 22, text=agent_name, anchor="w",
            fill="#cccccc", font=("Microsoft YaHei UI", 9, "bold"),
            tags=("card", bg_tag)
        )

        # 3 mini traffic lights — horizontal row
        # Positions: red=100, yellow=122, green=144
        light_names = ["red", "yellow", "green"]
        light_cx = {"red": 100, "yellow": 122, "green": 144}
        cy = y0 + 32
        RING_R = 9

        for lname in light_names:
            cx = light_cx[lname]
            is_active = (lname == active_light)
            c = cfg_lights[lname]
            tag = f"card_{agent_name}"
            elements = self._card_elements.setdefault(agent_name, {})

            if is_active:
                # Glowing ring
                self.canvas.create_oval(
                    cx - RING_R - 2, cy - RING_R - 2,
                    cx + RING_R + 2, cy + RING_R + 2,
                    fill="#1a1a1a", outline=c["glow"], width=1, tags=("card", tag)
                )
                # Glow1
                self.canvas.create_oval(
                    cx - RING_R, cy - RING_R,
                    cx + RING_R, cy + RING_R,
                    fill=c["glow"], outline="", tags=("card", tag)
                )
                # Glow2
                self.canvas.create_oval(
                    cx - 6, cy - 6, cx + 6, cy + 6,
                    fill=c["active"], outline="", tags=("card", tag)
                )
                # Core (white center)
                self.canvas.create_oval(
                    cx - 3, cy - 3, cx + 3, cy + 3,
                    fill="#ffffff", outline="", tags=("card", tag)
                )
            else:
                # Dim
                self.canvas.create_oval(
                    cx - RING_R - 1, cy - RING_R - 1,
                    cx + RING_R + 1, cy + RING_R + 1,
                    fill="#0d0d0d", outline="#222222", width=1, tags=("card", tag)
                )
                self.canvas.create_oval(
                    cx - RING_R, cy - RING_R,
                    cx + RING_R, cy + RING_R,
                    fill="#0d0d0d", outline="", tags=("card", tag)
                )
                self.canvas.create_oval(
                    cx - 5, cy - 5, cx + 5, cy + 5,
                    fill="#1a1a1a", outline="", tags=("card", tag)
                )

        # Status label below lights
        status_text = cfg.STATUS_TEXT.get(status, status)
        status_color = cfg.STATUS_COLORS.get(status, "#888888")
        self.canvas.create_text(
            light_cx["yellow"], y0 + 50,
            text=status_text, fill=status_color,
            font=("Microsoft YaHei UI", 7), tags=("card", bg_tag)
        )

        # Separator line
        self.canvas.create_line(
            8, y0 + cfg.CARD_HEIGHT - 2, w - 8, y0 + cfg.CARD_HEIGHT - 2,
            fill="#1a1a1a", tags=("card", bg_tag)
        )

    # ── Light State Update (incremental) ──────────────────────────────

    def _update_card_light(self, agent_name: str, status: str):
        """Incremental update: redraw just one card's lights."""
        if agent_name not in self.agent_order:
            return
        idx = self.agent_order.index(agent_name)
        # Clear old elements for this card
        tag = f"card_{agent_name}"
        self.canvas.delete(tag)
        if agent_name in self._card_elements:
            del self._card_elements[agent_name]
        # Redraw
        self._draw_one_card(agent_name, status, idx)

    # ── Window Sizing ─────────────────────────────────────────────────

    def _resize_window(self):
        """Calculate and set window geometry."""
        n = max(len(self.agent_order), 1)  # at least 1 card height for "no agents"
        card_area = n * cfg.CARD_HEIGHT
        canvas_height = max(card_area, 60)
        total_height = cfg.BASE_HEIGHT + canvas_height
        self.root.geometry(f"{cfg.WINDOW_WIDTH}x{total_height}")

        if hasattr(self, "canvas"):
            self.canvas.configure(height=canvas_height)

    def _update_title(self):
        """Update title bar and status bar text."""
        n = len(self.agent_order)
        active_count = sum(
            1 for a in self.agent_order
            if self.agents.get(a, {}).get("status") == "working"
        )
        self.status_label.config(
            text=f"{n} agent(s) | {active_count} working"
        )

    # ── Drag ──────────────────────────────────────────────────────────

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_pointerx() - self._drag_x
        y = self.root.winfo_pointery() - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ── Right-click Menu ──────────────────────────────────────────────

    def _on_right_click(self, event):
        """Determine which agent card was clicked, show context menu."""
        row = event.y // cfg.CARD_HEIGHT
        if 0 <= row < len(self.agent_order):
            agent_name = self.agent_order[row]
            self._show_agent_menu(event, agent_name)
        else:
            self._show_global_menu(event)

    def _show_agent_menu(self, event, agent_name: str):
        menu = tk.Menu(self.root, tearoff=0, bg="#1e1e1e", fg="#cccccc",
                       activebackground="#333333", activeforeground="#ffffff")
        menu.add_command(label=f"Agent: {agent_name}", state="disabled",
                         disabledforeground="#888888")
        menu.add_separator()
        menu.add_command(label="[IDLE]  Set Idle",
                         command=lambda: self.set_status(agent_name, "idle"))
        menu.add_command(label="[WORK] Set Working",
                         command=lambda: self.set_status(agent_name, "working"))
        menu.add_command(label="[DONE] Set Complete",
                         command=lambda: self.set_status(agent_name, "done"))
        menu.add_separator()
        menu.add_command(label="Add Agent...",
                         command=self._gui_add_agent)
        menu.add_command(label="Remove Agent...",
                         command=lambda: self._gui_remove_agent(agent_name))
        menu.add_separator()
        menu.add_command(label="Exit", command=self.root.quit)
        menu.post(event.x_root, event.y_root)

    def _show_global_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg="#1e1e1e", fg="#cccccc",
                       activebackground="#333333", activeforeground="#ffffff")
        menu.add_command(label="Add Agent...", command=self._gui_add_agent)
        menu.add_separator()
        menu.add_command(label="Exit", command=self.root.quit)
        menu.post(event.x_root, event.y_root)

    # ── GUI Actions ───────────────────────────────────────────────────

    def _gui_add_agent(self):
        name = simpledialog.askstring("Add Agent", "Agent name:",
                                      parent=self.root)
        if name and name.strip():
            name = name.strip()
            if name not in self.agents:
                self.agents[name] = {
                    "status": "idle",
                    "timestamp": "",
                    "source": "traffic_light_app",
                }
                self.agent_order.append(name)
                self._resize_window()
                self._draw_all_cards()
                self._update_title()
                self._write_to_file()

    def _gui_remove_agent(self, agent_name: str):
        # Confirm dialog using a simple toplevel
        confirm = tk.Toplevel(self.root)
        confirm.title("Remove Agent")
        confirm.geometry("220x100")
        confirm.configure(bg="#1e1e1e")
        confirm.overrideredirect(True)
        # Center on parent
        confirm.geometry(f"+{self.root.winfo_x() + 30}+{self.root.winfo_y() + 80}")

        tk.Label(confirm, text=f'Remove "{agent_name}"?',
                 bg="#1e1e1e", fg="#cccccc",
                 font=("Microsoft YaHei UI", 9)).pack(pady=(12, 6))

        btn_frame = tk.Frame(confirm, bg="#1e1e1e")
        btn_frame.pack()

        def do_remove():
            if agent_name in self.agents:
                del self.agents[agent_name]
                self.agent_order.remove(agent_name)
                self._resize_window()
                self._draw_all_cards()
                self._update_title()
                self._write_to_file()
            confirm.destroy()

        tk.Button(btn_frame, text="Remove", command=do_remove,
                  bg="#ff4444", fg="#ffffff", relief="flat", padx=12).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", command=confirm.destroy,
                  bg="#333333", fg="#cccccc", relief="flat", padx=12).pack(side="left", padx=4)

    # ── Status Control ────────────────────────────────────────────────

    def set_status(self, agent_name: str, status: str):
        """Set an agent's status and sync to file."""
        if status not in cfg.VALID_STATUSES:
            return
        self.agents[agent_name] = {
            "status": status,
            "timestamp": "",
            "source": "traffic_light_app",
        }
        cfg.update_agent_status(agent_name, status, source="traffic_light_app")
        self._update_card_light(agent_name, status)
        self._update_title()

    # ── File Sync ─────────────────────────────────────────────────────

    def _write_to_file(self):
        """Write current state to file."""
        cfg.write_status_file(self.agents)

    def _reload_from_file(self):
        """Load agents from file, detecting new/removed/changed."""
        file_agents = cfg.read_status_file()

        # Detect changes
        old_names = set(self.agent_order)
        new_names = set(file_agents.keys())

        added = new_names - old_names
        removed = old_names - new_names

        # Build new order: keep existing order, append new agents
        for name in self.agent_order[:]:
            if name in removed:
                self.agent_order.remove(name)
        for name in sorted(added):  # sort for deterministic order
            if name not in self.agent_order:
                self.agent_order.append(name)

        self.agents = file_agents

        return added or removed or self._status_changed(file_agents)

    def _status_changed(self, file_agents: dict) -> bool:
        """Check if any agent's status differs from current GUI state."""
        for name, data in file_agents.items():
            old = self.agents.get(name, {}).get("status")
            new = data.get("status")
            if old != new:
                return True
        return False

    def _poll_status_file(self):
        """Check status file every second for external changes."""
        try:
            changed = self._reload_from_file()
            if changed:
                # Full redraw when agents are added/removed
                self._resize_window()
                self._draw_all_cards()
                self._update_title()
            else:
                # Incremental update for status changes only
                for name in self.agent_order:
                    data = self.agents.get(name, {})
                    status = data.get("status", "idle")
                    self._update_card_light(name, status)
        except Exception:
            pass
        self.root.after(1000, self._poll_status_file)

    # ── Run ───────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


def main():
    app = MultiAgentTrafficApp()
    app.run()


if __name__ == "__main__":
    main()
