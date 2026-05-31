#!/usr/bin/env python3
"""
Traffic Light Desktop Assistant — Claude Code Status Monitor
RED    = Idle / Waiting for task
YELLOW = Working / Processing
GREEN  = Task complete

Reads ~/.claude/desk_assistant_status.json for status sync.
"""

import tkinter as tk
import json
import sys
from pathlib import Path
from datetime import datetime

STATUS_FILE = Path.home() / ".claude" / "desk_assistant_status.json"

# Light config: {name: {active, dim, glow, label}}
LIGHT_CONFIG = {
    "red":    {"active": "#ff1a1a", "dim": "#2a0000", "glow": "#ff4444", "label": "Idle"},
    "yellow": {"active": "#ffcc00", "dim": "#2a2000", "glow": "#ffee44", "label": "Working"},
    "green":  {"active": "#00ff44", "dim": "#002a00", "glow": "#44ff66", "label": "Complete"},
}

STATUS_TO_ACTIVE = {
    "idle":    "red",
    "working": "yellow",
    "done":    "green",
}

STATUS_TEXT = {
    "idle":    "RED - Idle / Waiting",
    "working": "YELLOW - Working",
    "done":    "GREEN - Task Complete",
}

STATUS_COLORS = {
    "idle":    "#ff1a1a",
    "working": "#ffcc00",
    "done":    "#00ff44",
}

STATUS_MENU_ICONS = {
    "idle":    "[IDLE]",
    "working": "[WORK]",
    "done":    "[DONE]",
}


class TrafficLightApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Claude Status Monitor")
        self.root.geometry("130x380+100+100")

        # Borderless + always-on-top
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0d0d0d")

        self.bg_frame = tk.Frame(self.root, bg="#0d0d0d", highlightthickness=1,
                                 highlightbackground="#333333", highlightcolor="#333333")
        self.bg_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # ---- Drag support ----
        self._drag_x = 0
        self._drag_y = 0
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._on_drag)

        # ---- Right-click menu ----
        self.menu = tk.Menu(self.root, tearoff=0, bg="#1e1e1e", fg="#cccccc",
                            activebackground="#333333", activeforeground="#ffffff")
        self.menu.add_command(label="[IDLE]  Set Idle", command=lambda: self.set_status("idle"))
        self.menu.add_command(label="[WORK] Set Working", command=lambda: self.set_status("working"))
        self.menu.add_command(label="[DONE] Set Complete", command=lambda: self.set_status("done"))
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self.root.quit)
        self.root.bind("<Button-3>", lambda e: self.menu.post(e.x_root, e.y_root))

        # ---- Title bar ----
        title_bar = tk.Frame(self.bg_frame, bg="#0d0d0d", height=30)
        title_bar.pack(fill="x", padx=8, pady=(8, 0))
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="Claude Status", bg="#0d0d0d", fg="#888888",
                 font=("Microsoft YaHei UI", 9, "bold")).pack(side="left")
        close_btn = tk.Label(title_bar, text="X", bg="#0d0d0d", fg="#666666",
                             font=("Arial", 10), cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.root.quit())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ff4444"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#666666"))

        # ---- Separator ----
        tk.Frame(self.bg_frame, bg="#222222", height=1).pack(fill="x", padx=10, pady=(6, 10))

        # ---- Traffic light canvas ----
        self.canvas = tk.Canvas(self.bg_frame, width=110, height=260,
                                bg="#0d0d0d", highlightthickness=0)
        self.canvas.pack()

        # Draw three lights: red (top), yellow (middle), green (bottom)
        self.light_ids = {}
        positions = [("red", 10), ("yellow", 90), ("green", 170)]

        for name, y_top in positions:
            cx, cy = 55, y_top + 35
            ids = {}

            ids["ring"] = self.canvas.create_oval(
                cx - 32, cy - 32, cx + 32, cy + 32,
                fill="#1a1a1a", outline="#333333", width=2, tags=name
            )
            ids["glow1"] = self.canvas.create_oval(
                cx - 28, cy - 28, cx + 28, cy + 28,
                fill="#0d0d0d", outline="", width=0, tags=name
            )
            ids["glow2"] = self.canvas.create_oval(
                cx - 24, cy - 24, cx + 24, cy + 24,
                fill="#0d0d0d", outline="", width=0, tags=name
            )
            ids["light"] = self.canvas.create_oval(
                cx - 20, cy - 20, cx + 20, cy + 20,
                fill="#111111", outline="", width=0, tags=name
            )
            ids["label"] = self.canvas.create_text(
                cx, y_top + 75,
                text=LIGHT_CONFIG[name]["label"],
                fill="#555555", font=("Microsoft YaHei UI", 8), tags=name
            )

            self.light_ids[name] = ids

        # ---- Bottom status text ----
        tk.Frame(self.bg_frame, bg="#222222", height=1).pack(fill="x", padx=10, pady=(6, 6))

        self.status_label = tk.Label(
            self.bg_frame, text="RED - Idle / Waiting",
            bg="#0d0d0d", fg="#ff1a1a",
            font=("Microsoft YaHei UI", 8), wraplength=120
        )
        self.status_label.pack(pady=(0, 8))

        # Current state
        self.current_status = "idle"
        self._apply_light_state("idle")

        # Start file polling
        self._poll_status_file()

    # ---- Drag handlers ----
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_pointerx() - self._drag_x
        y = self.root.winfo_pointery() - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ---- Status control ----
    def set_status(self, status: str):
        """Switch traffic light and write to file"""
        self._apply_light_state(status)
        self._write_status_file(status)

    def _apply_light_state(self, status: str):
        """Update GUI light display"""
        active_name = STATUS_TO_ACTIVE.get(status, "red")
        cfg = LIGHT_CONFIG

        for name in ["red", "yellow", "green"]:
            ids = self.light_ids[name]
            is_active = (name == active_name)

            if is_active:
                self.canvas.itemconfig(ids["ring"], fill="#2a2a2a", outline=cfg[name]["glow"], width=2)
                self.canvas.itemconfig(ids["glow1"], fill=cfg[name]["glow"])
                self.canvas.itemconfig(ids["glow2"], fill=cfg[name]["active"])
                self.canvas.itemconfig(ids["light"], fill="#ffffff")
                self.canvas.itemconfig(ids["label"], fill=cfg[name]["active"])
            else:
                self.canvas.itemconfig(ids["ring"], fill="#111111", outline="#2a2a2a", width=1)
                self.canvas.itemconfig(ids["glow1"], fill="#0d0d0d")
                self.canvas.itemconfig(ids["glow2"], fill="#0d0d0d")
                self.canvas.itemconfig(ids["light"], fill="#1a1a1a")
                self.canvas.itemconfig(ids["label"], fill="#444444")

        self.status_label.config(text=STATUS_TEXT.get(status, ""),
                                 fg=STATUS_COLORS.get(status, "#888888"))
        self.current_status = status

    def _write_status_file(self, status: str):
        """Write status to JSON file for external sync"""
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "source": "traffic_light_app",
            }
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _poll_status_file(self):
        """Check status file every second for external updates"""
        try:
            if STATUS_FILE.exists():
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                file_status = data.get("status")
                if file_status and file_status in STATUS_TO_ACTIVE and file_status != self.current_status:
                    self._apply_light_state(file_status)
        except Exception:
            pass
        self.root.after(1000, self._poll_status_file)

    def run(self):
        self.root.mainloop()


def main():
    app = TrafficLightApp()
    app.run()


if __name__ == "__main__":
    main()
