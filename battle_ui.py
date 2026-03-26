from __future__ import annotations

"""battle_ui.py

Modern layered Tkinter battle UI for the data-driven combat engine.

Visual layers:
- Background: forest arena + subtle particles
- Character: left/right sprites with idle/attack/hit/defeat reactions
- Interface: enemy top panel, initiative timeline, player bottom panel + command bar, combat log

This module renders state and plays micro-animations. Core rules live in battle_engine.py.
"""

import math
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk

from animation_system import AnimationController
from battle_engine import Action, BattleEngine, CombatEvent, Content
from character_system import Combatant, Resource


# -----------------------------
# Small UI helpers / primitives
# -----------------------------

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _mix(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex((int(_lerp(r1, r2, t)), int(_lerp(g1, g2, t)), int(_lerp(b1, b2, t))))


def _hp_color(ratio: float, *, warning: bool = False) -> str:
    ratio = max(0.0, min(1.0, ratio))
    if ratio >= 0.55:
        return _mix("#ffcd4a", "#49ff9a", (ratio - 0.55) / 0.45)
    if ratio >= 0.25:
        return _mix("#ff4d4d", "#ffcd4a", (ratio - 0.25) / 0.30)
    if warning and ratio <= 0.25:
        return "#ff2222"
    return "#ff4d4d"


def _hp_color_animated(ratio: float, time_ms: int = 0) -> str:
    ratio = max(0.0, min(1.0, ratio))
    if ratio > 0.25:
        return _hp_color(ratio)
    
    pulse = math.sin(time_ms * 0.008) * 0.3 + 0.7
    base = _hp_color(0.25)
    warning = "#ff2222"
    return _mix(base, warning, pulse)


def _round_rect_points(x1: int, y1: int, x2: int, y2: int, r: int) -> list[int]:
    r = max(0, int(r))
    return [
        x1 + r,
        y1,
        x2 - r,
        y1,
        x2,
        y1,
        x2,
        y1 + r,
        x2,
        y2 - r,
        x2,
        y2,
        x2 - r,
        y2,
        x1 + r,
        y2,
        x1,
        y2,
        x1,
        y2 - r,
        x1,
        y1 + r,
        x1,
        y1,
    ]


def _round_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, r: int, **kw) -> int:
    return canvas.create_polygon(_round_rect_points(x1, y1, x2, y2, r), smooth=True, **kw)


class AnimatedBar:
    """Resource bar with optional HP chip (delayed drain) for modern readability."""

    def __init__(self, canvas: tk.Canvas, x: int, y: int, w: int, h: int, *, chip: bool = False):
        self._c = canvas
        self._x = int(x)
        self._y = int(y)
        self._w = int(w)
        self._h = int(h)

        self._ratio = 1.0
        self._target = 1.0

        self._chip_enabled = bool(chip)
        self._chip_ratio = 1.0
        self._chip_target = 1.0

        self._bg = _round_rect(canvas, x, y, x + w, y + h, 8, fill="#1b2030", outline="#242b3d")
        self._chip = None
        if self._chip_enabled:
            self._chip = _round_rect(canvas, x + 2, y + 2, x + w - 2, y + h - 2, 7, fill="#b91c1c", outline="")
        self._fill = _round_rect(canvas, x + 2, y + 2, x + w - 2, y + h - 2, 7, fill=_hp_color(1.0), outline="")
        self._shine = canvas.create_rectangle(x + 6, y + 4, x + w - 6, y + 6, fill="#ffffff", outline="", stipple="gray75")

    def set_ratio_immediate(self, ratio: float, *, hp_style: bool = True) -> None:
        self._ratio = max(0.0, min(1.0, float(ratio)))
        self._target = self._ratio
        if self._chip_enabled:
            self._chip_ratio = self._ratio
            self._chip_target = self._ratio
        self._redraw(hp_style=hp_style)

    def set_target_ratio(self, ratio: float) -> None:
        r = max(0.0, min(1.0, float(ratio)))
        self._target = r
        if not self._chip_enabled:
            return
        if r >= self._ratio:
            self._chip_ratio = r
            self._chip_target = r
        else:
            self._chip_target = r

    def step(self, t: float, *, hp_style: bool = True) -> None:
        self._ratio = _lerp(self._ratio, self._target, t)
        if self._chip_enabled:
            chip_t = max(0.0, min(1.0, t * 0.38))
            self._chip_ratio = _lerp(self._chip_ratio, self._chip_target, chip_t)
        self._redraw(hp_style=hp_style)

    def _redraw(self, *, hp_style: bool) -> None:
        x1 = self._x + 2
        y1 = self._y + 2
        y2 = self._y + self._h - 2

        inner_w = max(0, int((self._w - 4) * self._ratio))
        chip_w = max(0, int((self._w - 4) * self._chip_ratio)) if self._chip_enabled else 0

        x2 = x1 + inner_w
        cx2 = x1 + chip_w

        if self._chip is not None:
            if chip_w <= 4:
                self._c.itemconfigure(self._chip, state="hidden")
            else:
                self._c.itemconfigure(self._chip, state="normal")
                self._c.coords(self._chip, *_round_rect_points(x1, y1, cx2, y2, 7))

        if inner_w <= 4:
            self._c.itemconfigure(self._fill, state="hidden")
            self._c.itemconfigure(self._shine, state="hidden")
            return

        self._c.itemconfigure(self._fill, state="normal")
        self._c.itemconfigure(self._shine, state="normal")
        self._c.coords(self._fill, *_round_rect_points(x1, y1, x2, y2, 7))
        fill = _hp_color(self._ratio) if hp_style else "#60a5fa"
        self._c.itemconfigure(self._fill, fill=fill)
        self._c.coords(self._shine, x1 + 4, y1 + 2, x2 - 4, y1 + 4)


class AnimatedRing:
    """Small circular gauge for secondary meters (Break)."""

    def __init__(
        self,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        *,
        width: int = 4,
        fg: str = "#fbbf24",
        bg: str = "#263455",
    ):
        self._c = canvas
        self._bbox = (int(x1), int(y1), int(x2), int(y2))
        self._w = int(width)
        self._fg = str(fg)
        self._bg = str(bg)

        self._ratio = 0.0
        self._target = 0.0

        bx1, by1, bx2, by2 = self._bbox
        self._ring_bg = canvas.create_oval(bx1, by1, bx2, by2, outline=self._bg, width=self._w)
        self._ring = canvas.create_arc(
            bx1,
            by1,
            bx2,
            by2,
            start=90,
            extent=0,
            style="arc",
            outline=self._fg,
            width=self._w,
        )

    def set_ratio_immediate(self, ratio: float) -> None:
        self._ratio = max(0.0, min(1.0, float(ratio)))
        self._target = self._ratio
        self._redraw()

    def set_target_ratio(self, ratio: float) -> None:
        self._target = max(0.0, min(1.0, float(ratio)))

    def step(self, t: float) -> None:
        self._ratio = _lerp(self._ratio, self._target, t)
        self._redraw()

    def _redraw(self) -> None:
        extent = -max(0.0, min(1.0, self._ratio)) * 359.999
        try:
            col = _mix("#60a5fa", self._fg, max(0.0, min(1.0, self._ratio)))
            self._c.itemconfigure(self._ring, extent=extent, outline=col)
        except Exception:
            pass


class CombatLog(tk.Frame):
    """Stylized event feed with fade-in and turn separators."""

    def __init__(self, parent: tk.Widget, *, bg: str):
        super().__init__(parent, bg=bg)
        self._text = tk.Text(
            self,
            height=7,
            wrap="word",
            bg=bg,
            fg="#d9deea",
            insertbackground="#d9deea",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#20283a",
        )
        self._scroll = ttk.Scrollbar(self, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=self._scroll.set)

        self._text.pack(side="left", fill="both", expand=True)
        self._scroll.pack(side="right", fill="y")

        self._text.tag_configure("turn", foreground="#a5b4fc")
        self._text.tag_configure("player", foreground="#7dd3fc")
        self._text.tag_configure("enemy", foreground="#fb7185")
        self._text.tag_configure("system", foreground="#b0b8ca")

        self._text.configure(state="disabled")

    _line_id = 0

    def _tag_color(self, tag: str) -> str:
        return {
            "turn": "#a5b4fc",
            "player": "#7dd3fc",
            "enemy": "#fb7185",
            "system": "#b0b8ca",
        }.get(tag, "#b0b8ca")

    def line(self, msg: str, *, tag: str = "system") -> None:
        self._text.configure(state="normal")

        ts = time.strftime("%H:%M")
        if tag == "turn":
            self._text.insert("end", "\n", ("system",))
            self._text.insert("end", "— " * 14 + "\n", ("system",))

        self._text.insert("end", f"[{ts}] ", ("system",))

        msg_start = self._text.index("end-1c")
        self._text.insert("end", msg + "\n")
        msg_end = self._text.index("end-1c")

        CombatLog._line_id += 1
        line_tag = f"fade_{CombatLog._line_id}"
        self._text.tag_add(line_tag, msg_start, msg_end)

        final = self._tag_color(tag)
        self._text.tag_configure(line_tag, foreground="#6b7280")

        def step(color: str):
            try:
                self._text.tag_configure(line_tag, foreground=color)
            except Exception:
                pass

        self.after(60, lambda: step(_mix("#6b7280", final, 0.55)))
        self.after(120, lambda: step(_mix("#6b7280", final, 0.80)))
        self.after(180, lambda: step(final))

        self._text.see("end")
        self._text.configure(state="disabled")


class Tooltip:
    """Tiny tooltip helper for skill descriptions."""

    def __init__(self, widget: tk.Widget, *, bg: str = "#111827", fg: str = "#e5e7eb"):
        self._w = widget
        self._tip: tk.Toplevel | None = None
        self._bg = bg
        self._fg = fg

    def show(self, text: str, x: int, y: int) -> None:
        self.hide()
        tip = tk.Toplevel(self._w)
        tip.wm_overrideredirect(True)
        tip.configure(bg=self._bg)
        lbl = tk.Label(tip, text=text, bg=self._bg, fg=self._fg, font=("Segoe UI", 10), justify="left", padx=10, pady=8)
        lbl.pack()
        tip.wm_geometry(f"+{x}+{y}")
        self._tip = tip

    def hide(self) -> None:
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
        self._tip = None


class ActionButton(tk.Button):
    """Command button with hover glow, click feedback, and disabled-state styling."""

    def __init__(
        self,
        parent,
        *,
        icon: str,
        text: str,
        command,
        theme: dict[str, str],
        hint: str = "",
        hint_fn=None,
        on_hint=None,
        shortcut: str = "",
    ):
        label = f"{icon}  {text}"
        if shortcut:
            label = f"{label}  [{shortcut}]"

        super().__init__(
            parent,
            text=label,
            command=command,
            font=("Segoe UI", 11, "bold"),
            bd=0,
            relief="flat",
            padx=14,
            pady=10,
            bg=theme["btn"],
            fg=theme["btn_fg"],
            activebackground=theme["btn_active"],
            activeforeground=theme["btn_fg"],
            disabledforeground=theme.get("btn_disabled_fg", "#6b7280"),
            highlightthickness=1,
            highlightbackground=theme["btn_border"],
            cursor="hand2",
        )
        self._theme = theme
        self._hint = hint or ""
        self._hint_fn = hint_fn
        self._on_hint = on_hint
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _evt=None):
        if str(self["state"]) != "disabled":
            self.configure(bg=self._theme["btn_hover"], highlightbackground=self._theme["btn_glow"])
        if self._on_hint:
            hint = self._hint
            if self._hint_fn:
                try:
                    dyn = self._hint_fn()
                    if dyn:
                        hint = dyn
                except Exception:
                    pass
            try:
                self._on_hint(hint or "")
            except Exception:
                pass

    def _on_leave(self, _evt=None):
        self.configure(bg=self._theme["btn"], highlightbackground=self._theme["btn_border"])
        if self._on_hint:
            try:
                self._on_hint("")
            except Exception:
                pass
# -----------------------------
# Interface widgets
# -----------------------------


class UnitPanel(tk.Canvas):
    """Top/bottom status panel for a combatant (portrait, bars, statuses)."""

    _STATUS_COLORS = {
        "burn": "#fb923c",
        "freeze": "#60a5fa",
        "poison": "#a78bfa",
        "shield": "#5eead4",
        "charge": "#fbbf24",
        "broken": "#fbbf24",
        "exposed": "#f472b6",
        "haste": "#34d399",
        "fury": "#f97316",
        "weaken": "#94a3b8",
        "slow": "#94a3b8",
    }

    def __init__(self, parent, *, theme: dict[str, str], content: Content, width: int, height: int, portrait: bool):
        super().__init__(parent, width=width, height=height, bg=theme["bg"], highlightthickness=0)
        self._theme = theme
        self._content = content
        self._panel_w = int(width)
        self._panel_h = int(height)
        self._portrait_enabled = bool(portrait)

        # panel
        _round_rect(self, 8, 10, width - 8, height - 6, 18, fill="#000000", outline="", stipple="gray50")
        _round_rect(self, 4, 6, width - 12, height - 10, 18, fill=theme["panel"], outline=theme["panel_border"], width=2)

        px = 18
        if self._portrait_enabled:
            _round_rect(self, 18, 18, 78, 78, 12, fill="#0f172a", outline="#22304f")
            self._portrait_icon = self.create_text(48, 48, text="◼", fill=theme["muted"], font=("Segoe UI", 16, "bold"))
            px = 90
        else:
            self._portrait_icon = None

        self._name_id = self.create_text(px, 26, text="", anchor="w", fill=theme["txt"], font=("Segoe UI", 12, "bold"))

        self._elem_circle = self.create_oval(width - 54, 16, width - 24, 46, fill="#c9c9d6", outline="#0f172a", width=2)
        self._elem_icon = self.create_text(width - 39, 31, text="◇", fill="#0b0f17", font=("Segoe UI", 11, "bold"))

        # Break gauge ring around the element icon.
        self.break_ring = AnimatedRing(self, width - 58, 12, width - 20, 50, width=4, fg="#fbbf24", bg=theme["panel_border"])

        # bars
        self._hp_text = self.create_text(px, 52, text="", anchor="w", fill=theme["muted"], font=("Segoe UI", 9, "bold"))
        self._sp_text = self.create_text(px, 80, text="", anchor="w", fill=theme["muted"], font=("Segoe UI", 9, "bold"))

        self.hp_bar = AnimatedBar(self, px, 60, width - px - 24, 14, chip=True)
        self.sp_bar = AnimatedBar(self, px, 88, width - px - 24, 10, chip=False)

        self._status_ids: list[int] = []

    def update_from_unit(self, unit: Combatant, *, immediate: bool) -> None:
        e = self._content.elements.normalize(unit.element)
        self.itemconfigure(self._name_id, text=unit.name)

        self.itemconfigure(self._elem_circle, fill=self._content.elements.color(e))
        self.itemconfigure(self._elem_icon, text=self._content.elements.icon(e))

        if self._portrait_icon is not None:
            # portrait is a placeholder; use the element icon for now.
            self.itemconfigure(self._portrait_icon, text=self._content.elements.icon(e))

        self.itemconfigure(self._hp_text, text=f"HP {unit.hp.current}/{unit.hp.maximum}")
        self.itemconfigure(self._sp_text, text=f"SP {unit.sp.current}/{unit.sp.maximum}")

        if immediate:
            self.hp_bar.set_ratio_immediate(unit.hp.ratio(), hp_style=True)
            self.sp_bar.set_ratio_immediate(unit.sp.ratio(), hp_style=False)
            self.break_ring.set_ratio_immediate(unit.break_gauge.ratio())
        else:
            self.hp_bar.set_target_ratio(unit.hp.ratio())
            self.sp_bar.set_target_ratio(unit.sp.ratio())
            self.break_ring.set_target_ratio(unit.break_gauge.ratio())

        for i in self._status_ids:
            self.delete(i)
        self._status_ids.clear()

        x = 18
        y = self._panel_h - 26
        for sid, inst in unit.statuses.items():
            if not inst.alive():
                continue
            badge = f"{inst.defn.icon}{inst.turns_left}"
            col = self._STATUS_COLORS.get(sid, "#fbbf24")
            rect = self.create_rectangle(x, y, x + 40, y + 16, fill="#0f172a", outline="#22304f")
            txt = self.create_text(x + 20, y + 8, text=badge, fill=col, font=("Segoe UI", 8, "bold"))
            self._status_ids.extend([rect, txt])
            x += 46


class InitiativeBar(tk.Canvas):
    """Horizontal turn order preview (CTB timeline)."""

    def __init__(self, parent, *, theme: dict[str, str], content: Content, width: int = 420, height: int = 42):
        super().__init__(parent, width=width, height=height, bg=theme["bg"], highlightthickness=0)
        self._theme = theme
        self._content = content

    def render(self, engine: BattleEngine, *, count: int = 10) -> None:
        self.delete("all")
        q = engine.upcoming_turns(count)
        active = engine.active_id

        x = 10
        for i, uid in enumerate(q):
            u = engine.get(uid)
            is_active = i == 0 and uid == active
            
            # Highlight active turn with glow effect
            if is_active:
                self.create_oval(x - 2, 6, x + 30, 38, fill="", outline="#fbbf24", width=3)
                ring = "#fbbf24"
                fill = "#1a1f2e"
            else:
                ring = self._content.elements.color(u.element)
                fill = "#0f172a"
            
            self.create_oval(x, 8, x + 28, 36, fill=fill, outline=ring, width=(2 if is_active else 1))
            icon = self._content.elements.icon(u.element)
            self.create_text(x + 14, 22, text=icon, fill="#e5e7eb", font=("Segoe UI", 12, "bold"))

            # Small intent/status hint with better visibility
            if u.has("broken"):
                self.create_text(x + 14, 38, text="BROKEN", fill="#fbbf24", font=("Segoe UI", 6, "bold"))
            elif u.has("charge"):
                self.create_text(x + 14, 38, text="CHARGE", fill="#fbbf24", font=("Segoe UI", 6, "bold"))
            elif u.has("shield"):
                self.create_text(x + 14, 38, text="SHIELD", fill="#5eead4", font=("Segoe UI", 6, "bold"))
            elif u.has("freeze"):
                self.create_text(x + 14, 38, text="FROZEN", fill="#60a5fa", font=("Segoe UI", 6, "bold"))
            x += 36
# -----------------------------
# Battle scene
# -----------------------------


class BattleUI(ttk.Frame):
    """Modern battle interface wired to the scalable data-driven combat engine."""

    def __init__(self, parent: tk.Widget):
        super().__init__(parent)

        self.theme = {
            "bg": "#0b0f17",
            "panel": "#101626",
            "panel2": "#0f1524",
            "panel_border": "#1f2a3f",
            "txt": "#d9deea",
            "muted": "#9aa6be",
            "btn": "#141c2f",
            "btn_hover": "#18233a",
            "btn_active": "#1b2a46",
            "btn_border": "#263455",
            "btn_glow": "#5eead4",
            "btn_fg": "#e5e7eb",
            "btn_disabled_fg": "#6b7280",
        }

        self.content = Content.load(Path("jsons"))
        self.engine = BattleEngine(content=self.content)
        self.anim = AnimationController(self)

        self._busy = False
        self._shortcuts_bound = False

        # Arena sprite ids + anchors
        self._player_anchor = (220, 230)
        self._enemy_anchor = (540, 220)
        self._player_sprite: int | None = None
        self._enemy_sprite: int | None = None

        # Callback for when battle ends (to return to openworld)
        self._on_battle_end_callback = None

        # Bind Escape key to close skill menu
        self.bind("<Escape>", lambda e: self._close_menus())

        # particle state
        self._particles: list[int] = []
        self._particle_job: str | None = None
        self._idle_job: str | None = None

        self._build_styles(parent)
        self._build_layout()

    def _build_styles(self, root):
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Battle.TFrame", background=self.theme["bg"])
        style.configure("BattleTitle.TLabel", background=self.theme["bg"], foreground="#fbbf24", font=("Segoe UI", 16, "bold"))

    def _build_layout(self) -> None:
        self.configure(style="Battle.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # TOP: enemy panel + timeline
        top = ttk.Frame(self, style="Battle.TFrame")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 10))
        top.columnconfigure(1, weight=1)

        title_frame = ttk.Frame(top, style="Battle.TFrame")
        title_frame.grid(row=0, column=0, sticky="w")
        ttk.Label(title_frame, text="BATTLE", style="BattleTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.turn_counter = ttk.Label(title_frame, text="Turn 1", style="BattleTitle.TLabel", foreground="#9aa6be")
        self.turn_counter.grid(row=0, column=1, sticky="w", padx=(20, 0))

        self.enemy_panel = UnitPanel(top, theme=self.theme, content=self.content, width=420, height=124, portrait=False)
        self.enemy_panel.grid(row=1, column=0, sticky="w", pady=(10, 0))

        self.timeline = InitiativeBar(top, theme=self.theme, content=self.content, width=420, height=42)
        self.timeline.grid(row=1, column=1, sticky="e", padx=(10, 0), pady=(10, 0))

        # MID: arena - responsive canvas
        self.arena = tk.Canvas(
            self,
            bg=self.theme["bg"],
            highlightthickness=1,
            highlightbackground=self.theme["panel_border"],
            relief="flat",
        )
        self.arena.grid(row=1, column=0, sticky="nsew", padx=16)

        # BOTTOM: log + player panel + command bar
        bottom = ttk.Frame(self, style="Battle.TFrame")
        bottom.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 16))
        bottom.columnconfigure(0, weight=1)

        self.log = CombatLog(bottom, bg=self.theme["panel2"])
        self.log.grid(row=0, column=0, sticky="ew")

        self.player_panel = UnitPanel(bottom, theme=self.theme, content=self.content, width=520, height=132, portrait=True)
        self.player_panel.grid(row=1, column=0, sticky="w", pady=(10, 0))

        self.hint = tk.Label(
            bottom,
            text="",
            bg=self.theme["bg"],
            fg=self.theme["muted"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify="left",
        )
        self.hint.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        self.action_bar = tk.Frame(bottom, bg=self.theme["bg"])
        self.action_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        for i in range(4):
            self.action_bar.columnconfigure(i, weight=1)

        self.btn_attack = ActionButton(
            self.action_bar,
            icon="⚔",
            text="Attack",
            command=lambda: self._on_action(Action(kind="attack")),
            theme=self.theme,
            hint="Attack: fast, reliable damage.",
            hint_fn=lambda: self._action_preview_text(Action(kind="attack")),
            on_hint=self._set_hint,
            shortcut="1",
        )
        self.btn_skill = ActionButton(
            self.action_bar,
            icon="✦",
            text="Skill",
            command=self._open_skill_menu,
            theme=self.theme,
            hint="Skill: costs SP, may apply statuses, can have cooldowns.",
            on_hint=self._set_hint,
            shortcut="2",
        )
        self.btn_defend = ActionButton(
            self.action_bar,
            icon="🛡",
            text="Defend",
            command=lambda: self._on_action(Action(kind="defend")),
            theme=self.theme,
            hint="Defend: apply a short Shield (reduces next hit).",
            hint_fn=lambda: self._action_preview_text(Action(kind="defend")),
            on_hint=self._set_hint,
            shortcut="3",
        )
        self.btn_item = ActionButton(
            self.action_bar,
            icon="☉",
            text="Item",
            command=self._open_item_menu,
            theme=self.theme,
            hint="Item: limited-use utility.",
            on_hint=self._set_hint,
            shortcut="4",
        )

        self.btn_attack.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.btn_skill.grid(row=0, column=1, sticky="ew", padx=10)
        self.btn_defend.grid(row=0, column=2, sticky="ew", padx=10)
        self.btn_item.grid(row=0, column=3, sticky="ew", padx=(10, 0))

        # Keyboard shortcut hint bar
        hint_bar = tk.Frame(bottom, bg=self.theme["bg"])
        hint_bar.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        for i in range(4):
            hint_bar.columnconfigure(i, weight=1)
        
        shortcuts = [("1", "Attack"), ("2", "Skill"), ("3", "Defend"), ("4", "Item")]
        for i, (key, action) in enumerate(shortcuts):
            tk.Label(
                hint_bar,
                text=f"[{key}] {action}",
                bg=self.theme["bg"],
                fg=self.theme["muted"],
                font=("Segoe UI", 8),
            ).grid(row=0, column=i, sticky="ew")

        # Overlay row for submenus (skills/items)
        self.menu_overlay = tk.Frame(bottom, bg=self.theme["bg"])
        self.menu_overlay.grid(row=5, column=0, sticky="ew")
        self.menu_overlay.columnconfigure(0, weight=1)
        self.menu_overlay.grid_remove()

        self.skill_menu: tk.Frame | None = None
        self.item_menu: tk.Frame | None = None
        self._tooltip = Tooltip(self)

        self._draw_arena_background()
        self._spawn_particles()

        # Bind resize event for responsive elements
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        """Handle window resize to make elements responsive."""
        width = event.width
        # Update wraplength for hint
        self.hint.configure(wraplength=width - 32)
        # Redraw arena
        if hasattr(self, '_draw_arena_background'):
            self._draw_arena_background()

    # -----------------------------
    # Battle start / wiring
    # -----------------------------

    def start_battle(self, player: Combatant, enemy: Combatant) -> None:
        """Initialize a new encounter."""
        self.engine.new_battle([player, enemy])
        self._draw_sprites()
        self._refresh_panels(immediate=True)
        self._refresh_timeline()
        self._set_controls_enabled(self.engine.active_id == "player")
        self.log.line("A foe emerges from the forest.", tag="turn")
        self._announce_turn()
        self._bind_shortcuts_once()

    def _restart_battle(self) -> None:
        """Restart the battle with a new enemy."""
        import random
        try:
            enemies_data = []
            try:
                import json
                with open("jsons/enemies.json", "r", encoding="utf-8") as f:
                    enemies_data = json.load(f)
            except Exception:
                pass
            
            # Get current player to reuse their stats
            player = self.engine.get("player")
            
            # Reset player HP and SP
            player.hp.current = player.hp.maximum
            player.sp.current = player.sp.maximum
            player.statuses.clear()
            player.cooldowns.clear()
            player.next_at = 0.0
            
            # Create new enemy
            if enemies_data:
                enemy_tpl = random.choice(enemies_data)
                enemy = make_enemy_from_template(enemy_tpl)
            else:
                enemy = make_enemy_from_template({"name": "Bandit", "element": "Wind", "hp": 90})
            
            # Reset break gauge
            enemy.break_gauge.current = 0
            
            # Start new battle
            self.start_battle(player, enemy)
            self.log.line("New battle begins!", tag="turn")
            
        except Exception as e:
            print(f"Restart error: {e}")
            self.log.line("Failed to restart. Please close and reopen.", tag="system")

    def _bind_shortcuts_once(self) -> None:
        if self._shortcuts_bound:
            return
        self._shortcuts_bound = True
        root = self.winfo_toplevel()

        def on_key(e):
            if self._busy or self.engine.is_over():
                return
            k = (e.keysym or "").lower()

            # When a submenu is open, prevent accidental actions.
            if self.skill_menu is not None or self.item_menu is not None:
                if k in ("escape",):
                    self._close_menus()
                    return "break"
                return "break"

            if k in ("1", "kp_1"):
                self._on_action(Action(kind="attack"))
                return "break"
            if k in ("2", "kp_2"):
                self._open_skill_menu()
                return "break"
            if k in ("3", "kp_3"):
                self._on_action(Action(kind="defend"))
                return "break"
            if k in ("4", "kp_4"):
                self._open_item_menu()
                return "break"
            if k in ("escape",):
                self._close_menus()
                return "break"

        root.bind("<Key>", on_key)

    # -----------------------------
    # UI refresh
    # -----------------------------

    def _set_hint(self, text: str) -> None:
        try:
            self.hint.configure(text=text or "")
        except Exception:
            pass

    def _action_preview_text(self, action: Action, *, include_title: bool = True) -> str:
        try:
            preview = self.engine.preview_action("player", action)
        except Exception:
            return ""
        if not preview:
            return ""
        lines = [ln for ln in preview.lines if ln]
        if not lines:
            return preview.title if include_title else ""
        body = " | ".join(lines)
        return f"{preview.title}\n{body}" if include_title else body

    def _refresh_panels(self, *, immediate: bool) -> None:
        if not self.engine.units:
            return
        p = self.engine.get("player")
        e = self.engine.get("enemy")
        self.player_panel.update_from_unit(p, immediate=immediate)
        self.enemy_panel.update_from_unit(e, immediate=immediate)

    def _refresh_timeline(self) -> None:
        self.timeline.render(self.engine, count=10)

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for b in (self.btn_attack, self.btn_skill, self.btn_defend, self.btn_item):
            b.configure(state=state)

    def _announce_turn(self) -> None:
        if self.engine.is_over():
            self._set_controls_enabled(False)
            return
        
        # Update turn counter
        turn = self.engine.turn_index
        self.turn_counter.configure(text=f"Turn {turn}")
        
        if self.engine.active_id == "player":
            if self.engine.get("player").has("charge"):
                self.log.line("Charge ready: Heavy Strike will trigger.", tag="turn")
            else:
                self.log.line("Your move.", tag="turn")
        else:
            self.log.line("Enemy acts...", tag="turn")
            self._telegraph_attack(self.engine.active_id, lambda: None)

    # -----------------------------
    # Background / ambience
    # -----------------------------

    def _draw_arena_background(self) -> None:
        c = self.arena
        c.delete("bg")
        w = int(c["width"])
        h = int(c["height"])

        top = "#07101a"
        mid = "#0b1a16"
        bot = self.theme["bg"]
        for i in range(24):
            t = i / 23
            col = _mix(top, mid, min(1.0, t * 1.2))
            y1 = int(h * t)
            y2 = int(h * (t + 1 / 24))
            c.create_rectangle(0, y1, w, y2, fill=col, outline="", tags=("bg",))

        c.create_rectangle(0, int(h * 0.62), w, h, fill=_mix(mid, bot, 0.55), outline="", tags=("bg",))

        # Light shafts (stipple bitmaps must be valid on Windows Tk)
        for i in range(6):
            x = 40 + i * 150
            c.create_polygon(
                x,
                0,
                x + 80,
                0,
                x + 260,
                h,
                x + 170,
                h,
                fill="#ffffff",
                outline="",
                stipple="gray75",
                tags=("bg",),
            )

        # Mist bokeh
        for i in range(14):
            r = 18 + (i % 5) * 10
            x = 90 + (i * 63) % (w - 90)
            y = 40 + ((i * 37) % int(h * 0.55))
            c.create_oval(x - r, y - r, x + r, y + r, fill="#ffffff", outline="", stipple="gray75", tags=("bg",))

        c.create_oval(-120, int(h * 0.58), w + 120, h + 120, fill="#000000", outline="", stipple="gray50", tags=("bg",))

    def _spawn_particles(self) -> None:
        c = self.arena
        c.delete("particle")
        self._particles.clear()
        w = int(c["width"])
        h = int(c["height"])

        # subtle ambience particles
        for i in range(20):
            r = 2 + (i % 3)
            x = 40 + (i * 43) % (w - 80)
            y = int(h * 0.15) + (i * 29) % int(h * 0.55)
            p = c.create_oval(x - r, y - r, x + r, y + r, fill="#ffffff", outline="", stipple="gray75", tags=("particle",))
            self._particles.append(p)

        def tick():
            if not self.winfo_exists():
                return
            for pid in list(self._particles):
                try:
                    x1, y1, x2, y2 = c.coords(pid)
                except Exception:
                    continue
                dy = -1
                c.move(pid, 0, dy)
                # wrap
                if y2 < int(h * 0.1):
                    c.move(pid, 0, int(h * 0.55))
            self._particle_job = self.after(60, tick)

        if self._particle_job is not None:
            try:
                self.after_cancel(self._particle_job)
            except Exception:
                pass
        tick()

    # -----------------------------
    # Character layer
    # -----------------------------

    def _draw_sprites(self) -> None:
        c = self.arena
        c.delete("sprite")

        px, py = self._player_anchor
        ex, ey = self._enemy_anchor

        self._player_sprite = c.create_oval(px - 34, py - 70, px + 34, py - 2, fill="#2dd4bf", outline="#0f172a", width=2, tags=("sprite", "player"))
        c.create_rectangle(px - 22, py - 2, px + 22, py + 62, fill="#0ea5e9", outline="#0f172a", width=2, tags=("sprite", "player"))

        self._enemy_sprite = c.create_polygon(
            ex - 52,
            ey + 52,
            ex,
            ey - 76,
            ex + 56,
            ey + 52,
            ex,
            ey + 76,
            fill="#fb7185",
            outline="#0f172a",
            width=2,
            smooth=True,
            tags=("sprite", "enemy"),
        )

        # Idle bob (very subtle)
        if self._idle_job is not None:
            try:
                self.after_cancel(self._idle_job)
            except Exception:
                pass

        t0 = time.perf_counter()

        def idle():
            if not self.winfo_exists():
                return
            t = time.perf_counter() - t0
            amp = 1.8
            dy = int(math.sin(t * 2.2) * amp)
            for tag in ("player", "enemy"):
                ids = c.find_withtag(tag)
                for iid in ids:
                    c.move(iid, 0, dy - getattr(self, f"_{tag}_idle_dy", 0))
                setattr(self, f"_{tag}_idle_dy", dy)
            self._idle_job = self.after(90, idle)

        idle()

    # -----------------------------
    # Commands / submenus
    # -----------------------------

    def _on_action(self, action: Action) -> None:
        if self._busy or self.engine.is_over():
            return
        if self.engine.active_id != "player":
            return
        self._close_menus()
        events = self.engine.player_action(action)
        self._play_events(events)

    def _close_menus(self) -> None:
        self._tooltip.hide()
        for w in (self.skill_menu, self.item_menu):
            if w is not None:
                w.destroy()
        self.skill_menu = None
        self.item_menu = None
        try:
            self.menu_overlay.grid_remove()
        except Exception:
            pass

    def _open_skill_menu(self) -> None:
        if self._busy or self.engine.active_id != "player":
            return
        # Toggle skill menu - if already open, close it
        if self.skill_menu is not None:
            self._close_menus()
            return
        self._close_menus()
        try:
            self.menu_overlay.grid()
        except Exception:
            pass

        actor = self.engine.get("player")

        m = tk.Frame(self.menu_overlay, bg=self.theme["bg"], highlightthickness=1, highlightbackground=self.theme["panel_border"])
        m.grid(row=0, column=0, sticky="ew", pady=(10, 0))

        # 3 columns makes room for cooldown/cost info.
        cols = 3
        for i in range(cols):
            m.columnconfigure(i, weight=1)

        skill_ids = list(actor.skills)
        if not skill_ids:
            tk.Label(m, text="No skills", bg=self.theme["bg"], fg=self.theme["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=10)
            self.skill_menu = m
            return

        def mk_tile(sid: str, idx: int):
            sd = self.content.skills.get(sid)
            cd = actor.cooldown(sid)
            enabled = (cd <= 0) and (actor.sp.current >= sd.cost_sp)

            tm = float(getattr(sd, "time_mult", 1.0) or 1.0)
            tm_tag = f"  |  T {tm:.2f}" if abs(tm - 1.0) >= 0.05 else ""
            label = f"{sd.icon}  {sd.name}\nSP {sd.cost_sp}  |  CD {cd}{tm_tag}" if cd > 0 else f"{sd.icon}  {sd.name}\nSP {sd.cost_sp}{tm_tag}"

            b = tk.Button(
                m,
                text=label,
                command=(lambda: self._on_action(Action(kind="skill", skill_id=sid))) if enabled else None,
                font=("Segoe UI", 10, "bold"),
                bd=0,
                relief="flat",
                padx=12,
                pady=10,
                bg=self.theme["btn"],
                fg=self.theme["btn_fg"],
                activebackground=self.theme["btn_active"],
                activeforeground=self.theme["btn_fg"],
                disabledforeground=self.theme["btn_disabled_fg"],
                cursor="hand2",
                justify="left",
                anchor="w",
            )
            if not enabled:
                b.configure(state="disabled")

            # tooltip + hint
            def on_enter(_e=None):
                preview = self._action_preview_text(Action(kind="skill", skill_id=sid), include_title=False)
                base = sd.description or ""
                hint = base
                if preview:
                    hint = f"{base}\n{preview}" if base else preview
                self._set_hint(hint)
                try:
                    rx = b.winfo_rootx() + 20
                    ry = b.winfo_rooty() - 10
                    self._tooltip.show(sd.description or sd.name, rx, ry)
                except Exception:
                    pass

            def on_leave(_e=None):
                self._set_hint("")
                self._tooltip.hide()

            b.bind("<Enter>", on_enter)
            b.bind("<Leave>", on_leave)

            r = idx // cols
            c = idx % cols
            b.grid(row=r, column=c, sticky="ew", padx=8, pady=8)
            return b

        buttons: list[tk.Button] = []
        for i, sid in enumerate(skill_ids):
            try:
                buttons.append(mk_tile(sid, i))
            except Exception:
                continue

        # Keyboard shortcuts inside the skill grid (Q/W/E/R/A/S/D/F)
        keys = ["q", "w", "e", "r", "a", "s", "d", "f"]
        mapping = {}
        for i, b in enumerate(buttons[: len(keys)]):
            mapping[keys[i]] = b

        def on_key(e):
            k = (e.keysym or "").lower()
            if k == "escape":
                self._close_menus()
                return "break"
            b = mapping.get(k)
            if b is not None and str(b["state"]) != "disabled":
                try:
                    b.invoke()
                except Exception:
                    pass
                return "break"
            return "break"

        m.bind("<Key>", on_key)
        m.focus_set()

        self.skill_menu = m

    def _open_item_menu(self) -> None:
        if self._busy or self.engine.active_id != "player":
            return
        # Toggle item menu - if already open, close it
        if self.item_menu is not None:
            self._close_menus()
            return
        self._close_menus()
        try:
            self.menu_overlay.grid()
        except Exception:
            pass

        actor = self.engine.get("player")
        p_count = int(actor.items.get("potion", 0))
        e_count = int(actor.items.get("ether", 0))

        m = tk.Frame(self.menu_overlay, bg=self.theme["bg"], highlightthickness=1, highlightbackground=self.theme["panel_border"])
        m.grid(row=0, column=0, sticky="ew", pady=(10, 0))
        for i in range(2):
            m.columnconfigure(i, weight=1)

        def mk_item(icon: str, name: str, item_id: str, count: int, hint: str, col: int):
            b = ActionButton(
                m,
                icon=icon,
                text=f"{name} x{count}",
                command=lambda: self._on_action(Action(kind="item", item_id=item_id)),
                theme=self.theme,
                hint=hint,
                hint_fn=lambda: self._action_preview_text(Action(kind="item", item_id=item_id), include_title=False),
                on_hint=self._set_hint,
                shortcut="",
            )
            b.configure(font=("Segoe UI", 10, "bold"))
            if count <= 0:
                b.configure(state="disabled")
            b.grid(row=0, column=col, sticky="ew", padx=8, pady=10)

        mk_item("🧪", "Potion", "potion", p_count, "Potion: heal 28 HP.", 0)
        mk_item("🔷", "Ether", "ether", e_count, "Ether: restore 20 SP.", 1)

        self.item_menu = m
    # -----------------------------
    # Animation / feedback
    # -----------------------------

    def _sprite_id(self, unit_id: str) -> int:
        if unit_id == "player":
            return int(self._player_sprite or 0)
        return int(self._enemy_sprite or 0)

    def _anchor(self, unit_id: str) -> tuple[int, int]:
        return self._player_anchor if unit_id == "player" else self._enemy_anchor

    def _lunge(
        self,
        attacker_id: str,
        done,
        *,
        target_id: str | None = None,
        distance: int = 18,
        duration_ms: int = 180,
    ) -> None:
        c = self.arena
        sprite = self._sprite_id(attacker_id)
        ax, _ = self._anchor(attacker_id)
        tx, _ = self._anchor(target_id or ("enemy" if attacker_id == "player" else "player"))
        dir_ = 1 if tx > ax else -1

        def upd(t):
            dx = int(math.sin(t * math.pi) * int(distance) * dir_)
            c.move(sprite, dx - getattr(self, "_last_dx", 0), 0)
            self._last_dx = dx

        def end():
            c.move(sprite, -getattr(self, "_last_dx", 0), 0)
            self._last_dx = 0
            done()

        self.anim.tween(int(duration_ms), upd, end, easing="in_out_quad")

    def _projectile(self, attacker_id: str, target_id: str, *, color: str, done, kind: str) -> None:
        c = self.arena
        ax, ay = self._anchor(attacker_id)
        tx, ty = self._anchor(target_id)
        ay -= 34
        ty -= 34

        r = 7 if kind == "burst" else 6
        orb = c.create_oval(ax - r, ay - r, ax + r, ay + r, fill=color, outline="", tags=("fx",))
        trail = c.create_line(ax, ay, ax, ay, fill=_mix(color, "#ffffff", 0.15), width=3, capstyle="round", tags=("fx",))

        def upd(t):
            # Slight arc for readability.
            x = int(_lerp(ax, tx, t))
            arc = math.sin(t * math.pi) * (22 if kind == "burst" else 16)
            y = int(_lerp(ay, ty, t) - arc)
            c.coords(orb, x - r, y - r, x + r, y + r)
            c.coords(trail, ax, ay, x, y)
            c.itemconfigure(orb, fill=_mix(color, "#ffffff", 0.25 * (1.0 - t)))

        def end():
            c.delete(orb)
            c.delete(trail)
            done()

        self.anim.tween(220 if kind == "burst" else 200, upd, end, easing="in_out_quad")

    def _shake(self, target_id: str, done) -> None:
        c = self.arena
        sprite = self._sprite_id(target_id)

        def upd(t):
            amp = (1.0 - t) * 7
            dx = int(math.sin(t * 10 * math.pi) * amp)
            dy = int(math.cos(t * 8 * math.pi) * (amp * 0.35))
            c.move(sprite, dx - getattr(self, "_shake_dx", 0), dy - getattr(self, "_shake_dy", 0))
            self._shake_dx = dx
            self._shake_dy = dy

        def end():
            c.move(sprite, -getattr(self, "_shake_dx", 0), -getattr(self, "_shake_dy", 0))
            self._shake_dx = 0
            self._shake_dy = 0
            done()

        self.anim.tween(170, upd, end, easing="out_cubic")

    def _screen_shake(self, intensity: float, done) -> None:
        """Shake the whole arena (bg + sprites) for heavy hits."""
        c = self.arena
        intensity = max(0.0, float(intensity))

        def upd(t):
            amp = (1.0 - t) * intensity
            dx = int(math.sin(t * 12 * math.pi) * amp)
            c.move("bg", dx - getattr(self, "_cam_dx", 0), 0)
            c.move("particle", dx - getattr(self, "_cam_dx", 0), 0)
            c.move("sprite", dx - getattr(self, "_cam_dx", 0), 0)
            c.move("fx", dx - getattr(self, "_cam_dx", 0), 0)
            self._cam_dx = dx

        def end():
            c.move("bg", -getattr(self, "_cam_dx", 0), 0)
            c.move("particle", -getattr(self, "_cam_dx", 0), 0)
            c.move("sprite", -getattr(self, "_cam_dx", 0), 0)
            c.move("fx", -getattr(self, "_cam_dx", 0), 0)
            self._cam_dx = 0
            done()

        self.anim.tween(160, upd, end, easing="out_cubic")
    def _flash(self, target_id: str, done, *, color: str) -> None:
        c = self.arena
        x, y = self._anchor(target_id)
        r = 62
        flash = c.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="", stipple="gray50", tags=("fx",))

        def upd(t):
            rr = int(_lerp(r, 18, t))
            c.coords(flash, x - rr, y - rr, x + rr, y + rr)
            c.itemconfigure(flash, fill=_mix(color, self.theme["bg"], t * 0.55))

        def end():
            c.delete(flash)
            done()

        self.anim.tween(140, upd, end)

    def _shield_pop(self, target_id: str, done) -> None:
        c = self.arena
        x, y = self._anchor(target_id)
        r0 = 16
        r1 = 72
        ring = c.create_oval(x - r0, y - r0, x + r0, y + r0, outline="#5eead4", width=3, tags=("fx",))
        badge = c.create_text(x, y - 84, text="SHIELD", fill="#5eead4", font=("Segoe UI", 11, "bold"), tags=("fx",))

        def upd(t):
            rr = int(_lerp(r0, r1, t))
            c.coords(ring, x - rr, y - rr, x + rr, y + rr)
            c.itemconfigure(ring, outline=_mix("#5eead4", self.theme["bg"], t * 0.8))
            c.itemconfigure(badge, fill=_mix("#5eead4", self.theme["bg"], t * 0.65))

        def end():
            c.delete(ring)
            c.delete(badge)
            done()

        self.anim.tween(220, upd, end)

    def _pop_label(self, target_id: str, text: str, color: str) -> None:
        c = self.arena
        x, y = self._anchor(target_id)
        txt = c.create_text(x, y - 98, text=text, fill=color, font=("Segoe UI", 11, "bold"), tags=("fx",))

        def upd(t):
            dy = int(_lerp(0, -12, t))
            c.coords(txt, x, y - 98 + dy)
            c.itemconfigure(txt, fill=_mix(color, self.theme["bg"], t * 0.78))

        def end():
            c.delete(txt)

        self.anim.tween(240, upd, end)

    def _float_number(self, target_id: str, amount: int, color: str, done) -> None:
        c = self.arena
        x, y = self._anchor(target_id)
        txt = c.create_text(x, y - 124, text=f"{amount}", fill=color, font=("Segoe UI", 12, "bold"), tags=("fx",))

        def upd(t):
            dy = int(_lerp(0, -18, t))
            c.coords(txt, x, y - 124 + dy)
            c.itemconfigure(txt, fill=_mix(color, self.theme["bg"], t * 0.85))

        def end():
            c.delete(txt)
            done()

        self.anim.tween(280, upd, end)

    def _mark_defeated(self, unit_id: str) -> None:
        c = self.arena
        sprite = self._sprite_id(unit_id)
        if sprite:
            try:
                c.itemconfigure(sprite, fill="#111827")
                c.move(sprite, 0, 18)
            except Exception:
                pass

    def _show_victory_effect(self, done) -> None:
        """Celebration effect when player wins."""
        c = self.arena
        w = int(c["width"])
        h = int(c["height"])
        
        # Golden glow overlay
        glow = c.create_rectangle(0, 0, w, h, fill="", outline="", tags=("fx",))
        
        # Victory text
        txt = c.create_text(w // 2, h // 2, text="VICTORY!", fill="#fbbf24", font=("Segoe UI", 36, "bold"), tags=("fx",))
        
        def upd(t):
            # Pulse the text
            scale = 1.0 + math.sin(t * math.pi * 2) * 0.1
            c.itemconfigure(txt, fill=_mix("#fbbf24", "#ffffff", t * 0.5))
        
        def end():
            c.delete(glow)
            c.delete(txt)
            done()
        
        self.anim.tween(600, upd, end)

    def _show_defeat_effect(self, done) -> None:
        """Somber effect when player loses."""
        c = self.arena
        w = int(c["width"])
        h = int(c["height"])
        
        # Dark overlay
        overlay = c.create_rectangle(0, 0, w, h, fill="#000000", outline="", tags=("fx",))
        c.itemconfigure(overlay, stipple="gray50")
        
        txt = c.create_text(w // 2, h // 2, text="DEFEAT...", fill="#6b7280", font=("Segoe UI", 36, "bold"), tags=("fx",))
        
        def upd(t):
            c.itemconfigure(overlay, fill=_mix("#000000", "#1f2937", t))
        
        def end():
            c.delete(overlay)
            c.delete(txt)
            done()
        
        self.anim.tween(500, upd, end)

    def _telegraph_attack(self, unit_id: str, done) -> None:
        """Telegraph that a unit is about to act - shake + outline glow."""
        c = self.arena
        sprite = self._sprite_id(unit_id)
        if not sprite:
            done()
            return
        
        x, y = self._anchor(unit_id)
        
        # Create warning ring
        r = 52
        ring = c.create_oval(x - r, y - r, x + r, y + r, fill="", outline="#fbbf24", width=2, tags=("fx", "telegraph"))
        
        def upd(t):
            # Pulse the ring
            pulse = math.sin(t * math.pi * 3) * 0.3 + 0.7
            c.itemconfigure(ring, outline=_mix("#fbbf24", "#ff6b5a", t))
        
        def end():
            c.delete(ring)
            done()
        
        self.anim.tween(400, upd, end)

    def _particle_burst(self, target_id: str, color: str, done, *, count: int = 8) -> None:
        """Particle burst effect on elemental hit."""
        c = self.arena
        x, y = self._anchor(target_id)
        y -= 34
        
        particles = []
        for i in range(count):
            angle = (math.pi * 2 * i) / count
            r = 4 + (i % 3) * 2
            px = x + math.cos(angle) * 8
            py = y + math.sin(angle) * 8
            p = c.create_oval(px - r, py - r, px + r, py + r, fill=color, outline="", tags=("fx",))
            particles.append((p, angle, 28 + (i % 4) * 6))
        
        def upd(t):
            for p, angle, dist in particles:
                dx = math.cos(angle) * dist * t
                dy = math.sin(angle) * dist * t - (t * 20)
                orig_x, orig_y = self._anchor(target_id)
                orig_y -= 34
                c.coords(p, orig_x + dx - 3, orig_y + dy - 3, orig_x + dx + 3, orig_y + dy + 3)
                c.itemconfigure(p, fill=_mix(color, self.theme["bg"], t * 0.8))
        
        def end():
            for p, _, _ in particles:
                c.delete(p)
            done()
        
        self.anim.tween(300, upd, end)

    # -----------------------------
    # Event playback
    # -----------------------------

    def _play_events(self, events: list[CombatEvent]) -> None:
        if not events:
            self._refresh_panels(immediate=True)
            self._refresh_timeline()
            self._set_controls_enabled(self.engine.active_id == "player" and not self.engine.is_over())
            self._announce_turn()
            return

        self._busy = True
        self._set_controls_enabled(False)

        steps = [lambda done, ev=ev: self._play_event(ev, done) for ev in events]

        def finish():
            self._busy = False
            self._refresh_panels(immediate=True)
            self._refresh_timeline()
            
            # Check if battle is over and trigger restart
            if self.engine.is_over():
                winner = self.engine.winner_team()
                if winner:
                    # If player won, close battle and return to openworld
                    if winner == "player":
                        self.log.line("Victory! Returning to world...", tag="system")
                        if self._on_battle_end_callback:
                            self.after(1500, self._on_battle_end_callback)
                        else:
                            self.after(1500, self.quit)
                    else:
                        self.log.line("Defeat! Restarting...", tag="system")
                        self.after(3000, self._restart_battle)
                return
            
            self._set_controls_enabled(self.engine.active_id == "player" and not self.engine.is_over())
            self._announce_turn()

        self.anim.run_sequence(steps, on_done=finish)

    def _play_event(self, ev: CombatEvent, done) -> None:
        # Log first for responsiveness (unless silent).
        tag = "system"
        if ev.kind == "turn":
            tag = "turn"
        elif ev.actor == "player":
            tag = "player"
        elif ev.actor == "enemy":
            tag = "enemy"

        silent = bool(ev.meta.get("silent")) if isinstance(ev.meta, dict) else False
        if (ev.text or "").strip() and not silent:
            if ev.tag and ev.kind in ("damage", "miss"):
                self.log.line(f"{ev.text} ({ev.tag})", tag=tag)
            else:
                self.log.line(ev.text, tag=tag)

        self._refresh_panels(immediate=False)

        def ratio_from(meta: object, cur_key: str, max_key: str) -> float | None:
            if not isinstance(meta, dict):
                return None
            cur = meta.get(cur_key)
            mx = meta.get(max_key)
            try:
                cur_i = int(cur)  # type: ignore[arg-type]
                mx_i = int(mx)  # type: ignore[arg-type]
            except Exception:
                return None
            if mx_i <= 0:
                return None
            return max(0.0, min(1.0, cur_i / mx_i))

        if ev.kind == "damage" and ev.target and ev.amount is not None:
            target_id = ev.target
            attacker_id = ev.actor or ("enemy" if target_id == "player" else "player")

            # Element-tinted feedback
            elem = str(ev.meta.get("element", "Neutral")) if isinstance(ev.meta, dict) else "Neutral"
            fx_col = self.content.elements.color(elem)
            num_col = fx_col
            if ev.tag:
                if "Super Effective" in ev.tag:
                    num_col = "#fbbf24"
                elif "Resisted" in ev.tag:
                    num_col = "#93c5fd"

            anim_kind = str(ev.meta.get("animation", "")) if isinstance(ev.meta, dict) else ""
            is_heavy = anim_kind == "heavy"
            is_crit = ("CRIT" in (ev.tag or "")) or (bool(ev.meta.get("crit")) if isinstance(ev.meta, dict) else False)

            def after_lunge():
                ratio = ratio_from(ev.meta, "hp_to", "hp_max")
                if ratio is None:
                    ratio = self.engine.get(target_id).hp.ratio()

                panel = self.player_panel if target_id == "player" else self.enemy_panel
                panel.hp_bar.set_target_ratio(ratio)

                def bar_upd(t):
                    panel.hp_bar.step(t, hp_style=True)

                self.anim.tween(250, bar_upd, None)

                if ev.tag:
                    if "Super Effective" in ev.tag:
                        self._pop_label(target_id, "Super Effective!", "#fbbf24")
                        self._particle_burst(target_id, fx_col, lambda: None)
                    elif "Resisted" in ev.tag:
                        self._pop_label(target_id, "Resisted", "#93c5fd")
                    if "CRIT" in ev.tag:
                        self._pop_label(target_id, "Critical!", "#f472b6")

                def after_hit():
                    # defeat state
                    if not self.engine.get(target_id).alive():
                        self._mark_defeated(target_id)
                    self._float_number(target_id, ev.amount or 0, num_col, done)

                def hit_fx():
                    self._flash(target_id, lambda: self._shake(target_id, after_hit), color=fx_col)

                if is_heavy or is_crit:
                    self._screen_shake(10.0 if is_heavy else 6.0, hit_fx)
                else:
                    hit_fx()

            if anim_kind in ("blast", "burst"):
                self._projectile(attacker_id, target_id, color=fx_col, done=after_lunge, kind=anim_kind)
            else:
                dist = 22 if anim_kind in ("heavy", "sunder") else (12 if anim_kind == "sting" else 18)
                dur = 200 if anim_kind in ("heavy", "sunder") else (140 if anim_kind == "sting" else 180)
                self._lunge(attacker_id, after_lunge, target_id=target_id, distance=dist, duration_ms=dur)
            return

        if ev.kind == "heal" and ev.target and ev.amount is not None:
            target_id = ev.target
            ratio = ratio_from(ev.meta, "hp_to", "hp_max")
            if ratio is None:
                ratio = self.engine.get(target_id).hp.ratio()

            panel = self.player_panel if target_id == "player" else self.enemy_panel
            panel.hp_bar.set_target_ratio(ratio)

            def bar_upd(t):
                panel.hp_bar.step(t, hp_style=True)

            self.anim.tween(230, bar_upd, None)
            self._float_number(target_id, ev.amount, "#7dffb2", done)
            return

        if ev.kind == "resource" and ev.tag == "sp" and (ev.target or ev.actor):
            uid = ev.target or ev.actor or "player"
            ratio = ratio_from(ev.meta, "sp_to", "sp_max")
            if ratio is None:
                ratio = self.engine.get(uid).sp.ratio()

            panel = self.player_panel if uid == "player" else self.enemy_panel
            panel.sp_bar.set_target_ratio(ratio)
            self.anim.tween(230, lambda t: panel.sp_bar.step(t, hp_style=False), done)
            return

        if ev.kind == "resource" and ev.tag == "break" and ev.target:
            uid = ev.target
            ratio = ratio_from(ev.meta, "break_to", "break_max")
            if ratio is None:
                ratio = self.engine.get(uid).break_gauge.ratio()

            panel = self.player_panel if uid == "player" else self.enemy_panel
            panel.break_ring.set_target_ratio(ratio)
            self.anim.tween(190, lambda t: panel.break_ring.step(t), done)
            return

        if ev.kind == "status" and ev.tag == "shield" and ev.target:
            self._shield_pop(ev.target, done)
            return

        if ev.kind == "status" and ev.tag == "broken" and ev.target:
            self._pop_label(ev.target, "BREAK!", "#fbbf24")
            self._screen_shake(6.0, done)
            return

        if ev.kind == "status" and ev.tag == "exposed" and ev.target:
            self._pop_label(ev.target, "EXPOSED", "#f472b6")
            self.after(110, done)
            return

        if ev.kind == "status" and ev.tag == "haste" and ev.target:
            self._pop_label(ev.target, "HASTE", "#34d399")
            self.after(110, done)
            return

        if ev.kind == "status" and ev.tag == "fury" and ev.target:
            self._pop_label(ev.target, "FURY", "#f97316")
            self.after(110, done)
            return

        if ev.kind == "status" and ev.tag == "weaken" and ev.target:
            self._pop_label(ev.target, "WEAKEN", "#94a3b8")
            self.after(110, done)
            return

        if ev.kind == "status" and ev.tag == "slow" and ev.target:
            self._pop_label(ev.target, "SLOW", "#94a3b8")
            self.after(110, done)
            return

        if ev.kind == "status" and ev.tag == "charge" and ev.target:
            self._pop_label(ev.target, "CHARGING", "#fbbf24")
            self.after(90, done)
            return

        if ev.kind == "timeline" and ev.target:
            self._pop_label(ev.target, "DELAY", "#93c5fd")
            self.after(110, done)
            return

        if ev.kind == "exploit" and ev.target and ev.amount is not None:
            target_id = ev.target
            self._pop_label(target_id, f"EXPLOIT! +{ev.amount}", "#fbbf24")
            self._flash(target_id, lambda: self._shake(target_id, done), color="#fbbf24")
            return

        if ev.kind == "victory":
            self._show_victory_effect(done)
            return

        if ev.kind == "defeat":
            self._show_defeat_effect(done)
            return

        if ev.kind == "miss" and ev.target:
            attacker_id = ev.actor or "player"
            self._lunge(attacker_id, done)
            return

        self.after(70, done)


# -----------------------------
# Convenience constructors (used by main.py)
# -----------------------------


_DEFAULT_CONTENT = Content.load(Path("jsons"))


def make_default_player(name: str, element: str) -> Combatant:
    e = _DEFAULT_CONTENT.elements.normalize(element)
    return Combatant(
        id="player",
        team="player",
        name=name or "Hero",
        element=e,
        hp=Resource(100, 100),
        sp=Resource(50, 50),
        attack=15,
        defense=7,
        speed=11,
        skills=["elemental", "burst", "focus", "sunder", "rally", "crippling_slash"],
    )


def make_enemy_from_template(tpl: dict) -> Combatant:
    name = tpl.get("name", "Enemy")
    elem = _DEFAULT_CONTENT.elements.normalize(tpl.get("element", "Neutral"))
    hp = int(tpl.get("hp", 90))

    atk_min = int(tpl.get("attack_min", 8))
    atk_max = int(tpl.get("attack_max", 14))
    attack = int(round((atk_min + atk_max) / 2)) + 1

    skills = tpl.get("skills")
    if not isinstance(skills, list) or not skills:
        skills = ["elemental", "burst", "crippling_slash", "sunder", "focus", "rally"]

    return Combatant(
        id="enemy",
        team="enemy",
        name=name,
        element=elem,
        hp=Resource(hp, hp),
        sp=Resource(40, 40),
        attack=attack,
        defense=6,
        speed=9 + int(hp < 90),
        accuracy=0.92,
        crit_chance=0.06,
        skills=[str(s) for s in skills],
    )
