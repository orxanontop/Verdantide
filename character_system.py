from __future__ import annotations

"""character_system.py

Core combat data model (UI-agnostic).

Key design principles:
- Combatant is a lightweight state container: stats/resources/statuses/cooldowns.
- Statuses are data-driven: definitions come from JSON; instances live on combatants.
- All mutation happens through small methods to keep engine logic predictable.

This module does not implement turn order or damage rules; those live in battle_engine.py.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


@dataclass(slots=True)
class Resource:
    current: int
    maximum: int

    def set(self, value: int) -> None:
        self.current = clamp(int(value), 0, int(self.maximum))

    def spend(self, amount: int) -> bool:
        amount = int(amount)
        if amount <= 0:
            return True
        if self.current < amount:
            return False
        self.current -= amount
        return True

    def gain(self, amount: int) -> None:
        self.set(self.current + int(amount))

    def ratio(self) -> float:
        if self.maximum <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current / self.maximum))


@dataclass(frozen=True, slots=True)
class StatusDef:
    id: str
    name: str
    icon: str
    type: str  # dot|ramp_dot|skip|shield|charge

    duration: int = 1
    stacking: str = "refresh"  # refresh|stack
    max_stacks: int = 1

    # Parameters (optional by type)
    potency: int = 0
    chance: float = 0.0
    incoming_mult: float = 1.0
    outgoing_mult: float = 1.0
    speed_mult: float = 1.0
    break_gain_mult: float = 1.0
    break_taken_mult: float = 1.0
    base: int = 0
    ramp_per_turn: int = 0


@dataclass(slots=True)
class StatusInstance:
    defn: StatusDef
    turns_left: int
    stacks: int = 1

    # A small scratchpad for effects that need memory (e.g. poison ramp).
    data: dict[str, int] = field(default_factory=dict)

    def alive(self) -> bool:
        return self.turns_left > 0

    def tick(self) -> None:
        self.turns_left = max(0, int(self.turns_left) - 1)


class StatusLibrary:
    def __init__(self, defs: dict[str, StatusDef]):
        self._defs = dict(defs)

    def get(self, status_id: str) -> StatusDef:
        if status_id not in self._defs:
            raise KeyError(f"Unknown status: {status_id}")
        return self._defs[status_id]

    def all(self) -> list[StatusDef]:
        return list(self._defs.values())

    @staticmethod
    def load(path: Path) -> "StatusLibrary":
        raw = {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}

        defs: dict[str, StatusDef] = {}
        for sid, row in (raw.items() if isinstance(raw, dict) else []):
            try:
                sid = str(sid)
                defs[sid] = StatusDef(
                    id=sid,
                    name=str(row.get("name", sid)).strip(),
                    icon=str(row.get("icon", "?")),
                    type=str(row.get("type", "dot")),
                    duration=int(row.get("duration", 1) or 1),
                    stacking=str(row.get("stacking", "refresh")),
                    max_stacks=int(row.get("max_stacks", 1) or 1),
                    potency=int(row.get("potency", 0) or 0),
                    chance=float(row.get("chance", 0.0) or 0.0),
                    incoming_mult=float(row.get("incoming_mult", 1.0) or 1.0),
                    outgoing_mult=float(row.get("outgoing_mult", 1.0) or 1.0),
                    speed_mult=float(row.get("speed_mult", 1.0) or 1.0),
                    break_gain_mult=float(row.get("break_gain_mult", 1.0) or 1.0),
                    break_taken_mult=float(row.get("break_taken_mult", 1.0) or 1.0),
                    base=int(row.get("base", 0) or 0),
                    ramp_per_turn=int(row.get("ramp_per_turn", 0) or 0),
                )
            except Exception:
                continue

        return StatusLibrary(defs)


@dataclass(frozen=True, slots=True)
class ElementDef:
    id: str
    icon: str
    color: str


class ElementLibrary:
    """Element definitions + a simple triangle matchup table (data-driven)."""

    def __init__(self, elements: dict[str, ElementDef], triangle: set[tuple[str, str]], *, super_mult: float, resisted_mult: float):
        self._elements = dict(elements)
        self._triangle = set(triangle)
        self.super_mult = float(super_mult)
        self.resisted_mult = float(resisted_mult)
        self._by_lower = {k.lower(): k for k in self._elements}

    def normalize(self, value: str | None) -> str:
        if not value:
            return "Neutral" if "Neutral" in self._elements else (next(iter(self._elements), "Neutral"))
        v = str(value).strip().lower()
        if not v:
            return "Neutral" if "Neutral" in self._elements else (next(iter(self._elements), "Neutral"))
        v = {"air": "wind"}.get(v, v)
        return self._by_lower.get(v, "Neutral" if "Neutral" in self._elements else (next(iter(self._elements), "Neutral")))

    def icon(self, elem: str) -> str:
        e = self.normalize(elem)
        return self._elements.get(e, ElementDef("Neutral", "◇", "#c9c9d6")).icon

    def color(self, elem: str) -> str:
        e = self.normalize(elem)
        return self._elements.get(e, ElementDef("Neutral", "◇", "#c9c9d6")).color

    def multiplier(self, attacker: str, defender: str) -> tuple[float, str]:
        a = self.normalize(attacker)
        d = self.normalize(defender)
        if (a, d) in self._triangle:
            return self.super_mult, "Super Effective"
        if (d, a) in self._triangle:
            return self.resisted_mult, "Resisted"
        return 1.0, ""

    @staticmethod
    def load(path: Path) -> "ElementLibrary":
        raw = {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}

        elems: dict[str, ElementDef] = {
            "Fire": ElementDef("Fire", "🔥", "#ff6b5a"),
            "Ice": ElementDef("Ice", "❄", "#5ad6ff"),
            "Wind": ElementDef("Wind", "🌀", "#7dffb2"),
            "Neutral": ElementDef("Neutral", "◇", "#c9c9d6"),
        }
        tri: set[tuple[str, str]] = {("Fire", "Ice"), ("Ice", "Wind"), ("Wind", "Fire")}
        super_mult = 1.5
        resisted_mult = 0.5

        if isinstance(raw, dict):
            try:
                ed = raw.get("elements", {})
                if isinstance(ed, dict):
                    for k, v in ed.items():
                        k = str(k)
                        if not isinstance(v, dict):
                            continue
                        elems[k] = ElementDef(id=k, icon=str(v.get("icon", elems.get(k, elems["Neutral"]).icon)), color=str(v.get("color", elems.get(k, elems["Neutral"]).color)))

                tri_raw = raw.get("triangle", [])
                if isinstance(tri_raw, list):
                    tri = set()
                    for row in tri_raw:
                        if isinstance(row, dict):
                            tri.add((str(row.get("attacker")), str(row.get("defender"))))

                mults = raw.get("multipliers", {})
                if isinstance(mults, dict):
                    super_mult = float(mults.get("super", super_mult) or super_mult)
                    resisted_mult = float(mults.get("resisted", resisted_mult) or resisted_mult)
            except Exception:
                pass

        return ElementLibrary(elems, tri, super_mult=super_mult, resisted_mult=resisted_mult)


@dataclass(slots=True)
class Combatant:
    """Runtime unit state for a battle."""

    id: str
    team: str

    name: str
    element: str = "Neutral"

    hp: Resource = field(default_factory=lambda: Resource(100, 100))
    sp: Resource = field(default_factory=lambda: Resource(50, 50))
    break_gauge: Resource = field(default_factory=lambda: Resource(0, 100))

    attack: int = 14
    defense: int = 6
    speed: int = 10

    accuracy: float = 0.95
    crit_chance: float = 0.08
    crit_mult: float = 1.5

    # Content ids
    skills: list[str] = field(default_factory=list)

    # Runtime state
    statuses: dict[str, StatusInstance] = field(default_factory=dict)
    cooldowns: dict[str, int] = field(default_factory=dict)
    items: dict[str, int] = field(default_factory=lambda: {"potion": 2, "ether": 1})

    next_at: float = 0.0

    def alive(self) -> bool:
        return self.hp.current > 0

    def has(self, status_id: str) -> bool:
        inst = self.statuses.get(status_id)
        return bool(inst) and inst.alive()

    def take_damage(self, amount: int) -> int:
        amount = max(0, int(amount))
        before = self.hp.current
        self.hp.set(before - amount)
        return before - self.hp.current

    def heal(self, amount: int) -> int:
        amount = max(0, int(amount))
        before = self.hp.current
        self.hp.set(before + amount)
        return self.hp.current - before

    def tick_cooldowns(self) -> None:
        for k in list(self.cooldowns.keys()):
            self.cooldowns[k] = max(0, int(self.cooldowns[k]) - 1)
            if self.cooldowns[k] <= 0:
                del self.cooldowns[k]

    def cooldown(self, skill_id: str) -> int:
        return int(self.cooldowns.get(skill_id, 0))

    def set_cooldown(self, skill_id: str, turns: int) -> None:
        turns = max(0, int(turns))
        if turns <= 0:
            return
        self.cooldowns[skill_id] = turns

    def apply_status(self, lib: StatusLibrary, status_id: str, *, duration: int | None = None, stacks: int = 1) -> StatusInstance:
        defn = lib.get(status_id)
        dur = int(duration if duration is not None else defn.duration)
        stacks = max(1, int(stacks))

        existing = self.statuses.get(status_id)
        if existing and existing.alive():
            if defn.stacking == "stack":
                existing.stacks = min(defn.max_stacks, existing.stacks + stacks)
            # refresh duration always
            existing.turns_left = max(existing.turns_left, dur)
            return existing

        inst = StatusInstance(defn=defn, turns_left=dur, stacks=min(defn.max_stacks, stacks))
        self.statuses[status_id] = inst
        return inst

    def remove_status(self, status_id: str) -> None:
        if status_id in self.statuses:
            del self.statuses[status_id]
