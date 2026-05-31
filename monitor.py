#!/usr/bin/env python3
"""
Multi-Window Project Traffic Light Monitor.
Each project gets its own independent traffic light window.

Auto-detects new projects from status file → spawns window.
Auto-closes window when project is removed or done (after 5s countdown).

Start: python monitor.py
"""

import tkinter as tk
from tkinter import simpledialog
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg


# ── Project Window ──────────────────────────────────────────────────────

class ProjectWindow:
    """One independent Toplevel window per project — big traffic light."""

    def __init__(self, monitor, name: str, status: str = "idle"):
        self.monitor = monitor
        self.name = name
        self.current_status = status

        self.win = tk.Toplevel(monitor.root)
        self.win.title(f"Project: {name}")
        self.win.configure(bg="#0d0d0d")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        # Windows: overrideredirect needs this to receive keyboard focus
        if sys.platform == "win32":
            self.win.after(50, self._enable_keyboard_focus)
        self.win.geometry(f"{cfg.SINGLE_WINDOW_WIDTH}x{cfg.SINGLE_WINDOW_HEIGHT}")

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        # Countdown state
        self._done_since: float | None = None
        self._cd_timer: str | None = None

        # Build UI
        self._build_ui()
        self._apply_light(status)

        # Keyboard: bind to Canvas (focusable), not window (unfocusable with overrideredirect)
        self.canvas.configure(takefocus=True)

        def _kc(status):
            return lambda e: self.set_status(status)
        self.canvas.bind("<KeyPress-1>", _kc("idle"))
        self.canvas.bind("<KeyPress-2>", _kc("working"))
        self.canvas.bind("<KeyPress-3>", _kc("done"))
        self.canvas.bind("<KeyPress-i>", _kc("idle"))
        self.canvas.bind("<KeyPress-w>", _kc("working"))
        self.canvas.bind("<KeyPress-d>", _kc("done"))
        self.canvas.bind("<KeyPress-l>", lambda e: self.monitor.toggle_language())
        self.canvas.bind("<KeyPress-a>", lambda e: self.monitor.toggle_autostart())
        self.canvas.bind("<Delete>", lambda e: self._close_self())
        self.canvas.bind("<KeyPress-Escape>", lambda e: self._close_self())

        # Right-click: bind to both window and canvas
        self.win.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        # Left-click drag via tag_bind so it doesn't interfere with close button
        # Left-click: focus canvas (for keyboard) + start drag
        self.canvas.bind("<ButtonPress-1>", lambda e: self.canvas.focus_set(), add="+")
        self.canvas.tag_bind("ui", "<Button-1>", self._start_drag)
        self.canvas.tag_bind("ui", "<Button-1>", lambda e: self.canvas.focus_set(), add="+")
        self.canvas.tag_bind("ui", "<B1-Motion>", self._on_drag)
        # Also bind right-click on ui items to ensure it always fires
        self.canvas.tag_bind("ui", "<Button-3>", self._on_right_click)

    @property
    def lang(self):
        return self.monitor.lang

    def _(self, key, **kw):
        s = cfg.t(key, self.lang)
        return s.format(**kw) if kw else s

    # ── UI Build ──────────────────────────────────────────────────────

    def _build_ui(self):
        w = cfg.SINGLE_WINDOW_WIDTH
        h = cfg.SINGLE_WINDOW_HEIGHT
        self.canvas = tk.Canvas(self.win, width=w, height=h,
                                bg="#0d0d0d", highlightthickness=1,
                                highlightbackground="#333333", highlightcolor="#333333")
        self.canvas.pack(fill="both", expand=True)

        # Title bar area
        self.canvas.create_rectangle(6, 6, w - 6, 32, fill="#0d0d0d", outline="", tags="ui")
        self._title_text = self.canvas.create_text(
            w // 2, 20, text=self.name, fill="#888888",
            font=("Microsoft YaHei UI", 9, "bold"), tags="ui"
        )
        # Close X button
        close_tag = "close_btn"
        self.canvas.create_rectangle(w - 26, 10, w - 4, 30,
                                     fill="", outline="", tags=(close_tag,))
        self._close_text = self.canvas.create_text(w - 15, 20, text="X", fill="#555555",
                                                   font=("Arial", 10, "bold"),
                                                   tags=(close_tag,))
        # Hover effects for close button
        self.canvas.tag_bind(close_tag, "<Enter>",
                             lambda e: self.canvas.itemconfig(self._close_text, fill="#ff4444"))
        self.canvas.tag_bind(close_tag, "<Leave>",
                             lambda e: self.canvas.itemconfig(self._close_text, fill="#555555"))
        self.canvas.tag_bind(close_tag, "<Button-1>",
                             lambda e: self._close_self())
        # Separator
        self.canvas.create_line(10, 34, w - 10, 34, fill="#222222", tags="ui")

        # Project name subtitle
        cx = w // 2
        self.canvas.create_text(cx, 52, text=self.name, fill="#aaaaaa",
                                font=("Microsoft YaHei UI", 10, "bold"), tags="ui")

        # 3 big lights
        self._light_tags = {}
        light_names = ["blue", "yellow", "green"]
        for i, lname in enumerate(light_names):
            y_top = cfg.BIG_LIGHT_TOP + i * cfg.BIG_LIGHT_SPACING + 60
            cy = y_top + cfg.BIG_LIGHT_CY_OFFSET
            RR, G1R, G2R, COR = cfg.BIG_RING_R, cfg.BIG_GLOW1_R, cfg.BIG_GLOW2_R, cfg.BIG_CORE_R

            tags = {}
            tags["ring"]  = self.canvas.create_oval(cx - RR - 2, cy - RR - 2, cx + RR + 2, cy + RR + 2,
                                                    fill="", outline="", width=2, tags="ui")
            tags["glow1"] = self.canvas.create_oval(cx - G1R, cy - G1R, cx + G1R, cy + G1R,
                                                    fill="", outline="", tags="ui")
            tags["glow2"] = self.canvas.create_oval(cx - G2R, cy - G2R, cx + G2R, cy + G2R,
                                                    fill="", outline="", tags="ui")
            tags["core"]  = self.canvas.create_oval(cx - COR, cy - COR, cx + COR, cy + COR,
                                                    fill="", outline="", tags="ui")
            # Label
            label_text = cfg.light_label(lname, self.lang)
            self.canvas.create_text(cx, y_top + cfg.BIG_LIGHT_CY_OFFSET + 38,
                                    text=label_text, fill="#555555",
                                    font=("Microsoft YaHei UI", 7), tags="ui")
            self._light_tags[lname] = tags

        # Status text
        self._status_text_id = self.canvas.create_text(
            cx, h - 40, text="", fill="#888888",
            font=("Microsoft YaHei UI", 9, "bold"), tags="ui"
        )

        # Bottom status bar
        self.canvas.create_line(10, h - 25, w - 10, h - 25, fill="#222222", tags="ui")
        self._bar_text = self.canvas.create_text(
            cx, h - 18, text="", fill="#444444",
            font=("Microsoft YaHei UI", 7), tags="ui"
        )
        # Key hints (subtle, below bar)
        self._key_hint = self.canvas.create_text(
            cx, h - 6, text="[1]Idle [2]Work [3]Done | Del/Esc=Close | A=Start | L=Lang",
            fill="#252525", font=("Microsoft YaHei UI", 5), tags="ui"
        )

    # ── Light Drawing ─────────────────────────────────────────────────

    def _apply_light(self, status: str):
        """Update the 3 lights and status text."""
        light_names = ["blue", "yellow", "green"]
        active = cfg.STATUS_TO_ACTIVE.get(status, "blue")
        c = cfg.LIGHT_CONFIG
        RR, G1R, G2R, COR = cfg.BIG_RING_R, cfg.BIG_GLOW1_R, cfg.BIG_GLOW2_R, cfg.BIG_CORE_R

        for lname in light_names:
            tags = self._light_tags[lname]
            is_active = (lname == active)
            col = c[lname]

            if is_active:
                self.canvas.itemconfig(tags["ring"], fill="#1a1a1a", outline=col["glow"], width=2)
                self.canvas.itemconfig(tags["glow1"], fill=col["glow"])
                self.canvas.itemconfig(tags["glow2"], fill=col["active"])
                self.canvas.itemconfig(tags["core"], fill="#ffffff")
            else:
                self.canvas.itemconfig(tags["ring"], fill="#0d0d0d", outline="#222222", width=1)
                self.canvas.itemconfig(tags["glow1"], fill="#0d0d0d")
                self.canvas.itemconfig(tags["glow2"], fill="#0d0d0d")
                self.canvas.itemconfig(tags["core"], fill="#1a1a1a")

        # Status text
        if self._done_since is not None:
            elapsed = time.time() - self._done_since
            remaining = max(0, cfg.AUTO_REMOVE_DELAY - int(elapsed))
            text = self._("removing_in", n=remaining)
            color = "#ff8844"
        else:
            text = cfg.status_label(status, self.lang)
            color = cfg.STATUS_COLORS.get(status, "#888888")
        self.canvas.itemconfig(self._status_text_id, text=text, fill=color)

        # Bottom bar
        n = self.monitor.project_count()
        active_n = self.monitor.working_count()
        bar = self._("status_bar", n=n, active_count=active_n)
        self.canvas.itemconfig(self._bar_text, text=bar)

    def _update_lights(self):
        """Update lights countdown display (called by timer)."""
        if self._done_since is not None:
            elapsed = time.time() - self._done_since
            remaining = max(0, cfg.AUTO_REMOVE_DELAY - int(elapsed))
            text = self._("removing_in", n=remaining)
            self.canvas.itemconfig(self._status_text_id, text=text, fill="#ff8844")

    # ── Position ──────────────────────────────────────────────────────

    def _auto_position(self):
        idx = list(self.monitor.windows.keys()).index(self.name)
        row = idx // cfg.WINDOWS_PER_ROW
        col = idx % cfg.WINDOWS_PER_ROW
        x = cfg.WINDOW_START_X + col * cfg.WINDOW_SPACING_X
        y = cfg.WINDOW_START_Y + row * cfg.WINDOW_SPACING_Y
        self.win.geometry(f"+{x}+{y}")

    # ── Drag ──────────────────────────────────────────────────────────

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.win.winfo_pointerx() - self._drag_x
        y = self.win.winfo_pointery() - self._drag_y
        self.win.geometry(f"+{x}+{y}")

    # ── Context Menu ──────────────────────────────────────────────────

    def _on_right_click(self, event):
        # Guard: prevent multiple menus from same event (multiple bindings)
        if getattr(self, '_menu_active', False):
            return "break"
        self._menu_active = True
        # Reset guard after menu closes (50ms after posting)
        self.win.after(200, lambda: setattr(self, '_menu_active', False))
        menu = tk.Menu(self.win, tearoff=0, bg="#1e1e1e", fg="#cccccc",
                       activebackground="#333333", activeforeground="#ffffff")
        menu.add_command(label=f"Project: {self.name}",
                         state="disabled", disabledforeground="#888888")
        menu.add_separator()
        menu.add_command(label=self._("set_idle") + "     [1]",
                         command=lambda: self.set_status("idle"))
        menu.add_command(label=self._("set_working") + "   [2]",
                         command=lambda: self.set_status("working"))
        menu.add_command(label=self._("set_complete") + "   [3]",
                         command=lambda: self.set_status("done"))
        menu.add_separator()
        menu.add_command(label=self._("lang_toggle") + "     [L]",
                         command=self.monitor.toggle_language)
        menu.add_separator()
        if cfg.get_autostart_status():
            menu.add_command(label=self._("autostart_disable") + "   [A]",
                             command=self.monitor.toggle_autostart)
        else:
            menu.add_command(label=self._("autostart_enable") + "    [A]",
                             command=self.monitor.toggle_autostart)
        menu.add_separator()
        menu.add_command(label=self._("remove_project") + "     [Del]",
                         command=lambda: self.monitor.remove_project(self.name))
        menu.add_separator()
        menu.add_command(label=self._("exit") + "     [Esc]",
                         command=self.monitor.shutdown)
        menu.post(event.x_root, event.y_root)

    # ── Status Control ────────────────────────────────────────────────

    def set_status(self, status: str):
        if status not in cfg.VALID_STATUSES:
            return
        self.current_status = status
        cfg.update_project_status(self.name, status, source="monitor")
        # Cancel countdown if status changed from done
        if status != "done":
            self._cancel_countdown()
        self._apply_light(status)

    # ── Countdown Engine ──────────────────────────────────────────────

    def start_countdown(self):
        if self._done_since is not None:
            return
        self._done_since = time.time()
        self._tick_countdown()

    def _tick_countdown(self):
        if self._done_since is None:
            return
        elapsed = time.time() - self._done_since
        remaining = cfg.AUTO_REMOVE_DELAY - int(elapsed)
        if remaining <= 0:
            self.monitor.remove_project(self.name)
            return
        self._update_lights()
        self._cd_timer = self.win.after(cfg.AUTO_REMOVE_TICK, self._tick_countdown)

    def _cancel_countdown(self):
        self._done_since = None
        if self._cd_timer:
            try:
                self.win.after_cancel(self._cd_timer)
            except Exception:
                pass
            self._cd_timer = None

    # ── Windows Keyboard Focus Fix ────────────────────────────────────

    def _enable_keyboard_focus(self):
        """On Windows, overrideredirect windows don't get keyboard focus.
        Use Windows API to remove WS_EX_NOACTIVATE from extended style."""
        try:
            import ctypes
            from ctypes import wintypes
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            hwnd = int(self.win.frame(), 16)
            user32 = ctypes.windll.user32
            current = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if current & WS_EX_NOACTIVATE:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current & ~WS_EX_NOACTIVATE)
        except Exception:
            pass

    # ── Close ─────────────────────────────────────────────────────────

    def _close_self(self):
        """Close just this one window and remove its project."""
        self._cancel_countdown()
        self.monitor.remove_project(self.name)

    def destroy(self):
        self._cancel_countdown()
        try:
            self.win.destroy()
        except Exception:
            pass


# ── Multi-Window Monitor ────────────────────────────────────────────────

class MultiWindowMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Monitor")
        self.root.geometry("1x1+-200+-200")
        self.root.withdraw()  # Hide root window

        self.lang = cfg.load_lang()
        self.windows: dict[str, ProjectWindow] = {}
        self.project_order: list[str] = []

        # Load current state and create windows
        self._sync()

        # Start polling
        self._poll()

    def _(self, key, **kw):
        s = cfg.t(key, self.lang)
        return s.format(**kw) if kw else s

    def project_count(self) -> int:
        return len(self.project_order)

    def working_count(self) -> int:
        projects = cfg.read_status_file()
        return sum(1 for p in projects.values() if p.get("status") == "working")

    # ── Sync ──────────────────────────────────────────────────────────

    def _sync(self):
        """Full sync: create windows for new projects, remove stale ones."""
        projects = cfg.read_status_file()
        new_names = set(projects.keys())
        old_names = set(self.windows.keys())

        added = new_names - old_names
        removed = old_names - new_names

        # Remove stale windows
        for name in removed:
            self._close_window(name)

        # Add new windows
        for name in sorted(added):
            data = projects[name]
            status = data.get("status", "idle")
            pw = ProjectWindow(self, name, status)
            self.windows[name] = pw
            pw._auto_position()  # position after adding to dict

        # Update order
        self.project_order = sorted(projects.keys())

        # Check status changes and countdowns
        for name, pw in list(self.windows.items()):
            if name not in projects:
                continue
            file_status = projects[name].get("status", "idle")

            if file_status == "done" and pw.current_status != "done":
                pw.current_status = "done"
                pw.start_countdown()
            elif file_status != "done" and pw._done_since is not None:
                pw._cancel_countdown()

            if file_status != pw.current_status and pw._done_since is None:
                pw.current_status = file_status

            pw._apply_light(file_status)

    def _close_window(self, name: str):
        pw = self.windows.pop(name, None)
        if pw:
            pw.destroy()
        if name in self.project_order:
            self.project_order.remove(name)

    # ── Remove Project ────────────────────────────────────────────────

    def remove_project(self, name: str):
        cfg.remove_project(name)
        self._close_window(name)
        self._reposition_all()

    # ── Language ──────────────────────────────────────────────────────

    def toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        cfg.save_lang(self.lang)
        # Defer rebuild to avoid destroying windows inside menu callback
        self.root.after(100, self._rebuild_all_windows)

    def _rebuild_all_windows(self):
        for name in list(self.windows.keys()):
            self._close_window(name)
        self._sync()

    # ── Auto-Start ────────────────────────────────────────────────────

    def toggle_autostart(self):
        """Toggle boot auto-start on/off."""
        current = cfg.get_autostart_status()
        ok = cfg.set_autostart(not current)
        if ok:
            new_state = not current
            # Update status text in all windows to show confirmation
            for pw in self.windows.values():
                status_text = self._("autostart_on") if new_state else self._("autostart_off")
                try:
                    pw.canvas.itemconfig(pw._bar_text, text=status_text,
                                         fill="#ffcc00" if new_state else "#888888")
                    # Restore normal bar text after 2 seconds
                    pw.win.after(2000, lambda w=pw: self._restore_status_bar(w))
                except Exception:
                    pass

    def _restore_status_bar(self, pw):
        try:
            n = self.project_count()
            active_n = self.working_count()
            pw.canvas.itemconfig(pw._bar_text, text=self._("status_bar", n=n, active_count=active_n),
                                 fill="#444444")
        except Exception:
            pass

    # ── Reposition ────────────────────────────────────────────────────

    def _reposition_all(self):
        for i, name in enumerate(sorted(self.windows.keys())):
            row = i // cfg.WINDOWS_PER_ROW
            col = i % cfg.WINDOWS_PER_ROW
            x = cfg.WINDOW_START_X + col * cfg.WINDOW_SPACING_X
            y = cfg.WINDOW_START_Y + row * cfg.WINDOW_SPACING_Y
            pw = self.windows.get(name)
            if pw:
                try:
                    pw.win.geometry(f"+{x}+{y}")
                except Exception:
                    pass

    # ── Shutdown ──────────────────────────────────────────────────────

    def shutdown(self):
        for pw in list(self.windows.values()):
            pw.destroy()
        self.windows.clear()
        try:
            self.root.quit()
        except Exception:
            pass

    # ── Poll ──────────────────────────────────────────────────────────

    def _poll(self):
        try:
            self._sync()
        except Exception:
            pass
        self.root.after(1000, self._poll)

    # ── Run ───────────────────────────────────────────────────────────

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.shutdown()


def main():
    mon = MultiWindowMonitor()
    mon.run()


if __name__ == "__main__":
    main()
