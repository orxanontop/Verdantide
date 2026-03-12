from __future__ import annotations

"""combat_effects.py

Element and status helpers shared by battle logic and UI.
- Normalizes data into the 3-element triangle (Fire/Ice/Wind)
- Computes elemental multipliers and labels
- Defines small status rules (DoT, skip chance, damage multipliers)
"""

from dataclasses import dataclass


ELEMENTS = ("Fire", "Ice", "Wind")

# UI-friendly palette for cards/icons/log.
ELEMENT_COLORS: dict[str, str] = {
    "Fire": "#ff6b5a",
    "Ice": "#5ad6ff",
    "Wind": "#7dffb2",
    "Neutral": "#c9c9d6",
}


def normalize_element(value: str | None) -> str:
    """Normalizes game data into the 3-element combat triangle."""
    if not value:
        return "Neutral"
    v = str(value).strip().lower()
    if v == "air":
        return "Wind"
    if v == "wind":
        return "Wind"
    if v == "fire":
        return "Fire"
    if v == "ice":
        return "Ice"
    return "Neutral"


def element_multiplier(attacker: str, defender: str) -> tuple[float, str]:
    """Returns (multiplier, label)."""
    a = normalize_element(attacker)
    d = normalize_element(defender)
    if a == "Fire" and d == "Ice":
        return 1.5, "Super Effective"
    if a == "Ice" and d == "Wind":
        return 1.5, "Super Effective"
    if a == "Wind" and d == "Fire":
        return 1.5, "Super Effective"

    if d == "Fire" and a == "Ice":
        return 0.5, "Resisted"
    if d == "Ice" and a == "Wind":
        return 0.5, "Resisted"
    if d == "Wind" and a == "Fire":
        return 0.5, "Resisted"

    return 1.0, ""


@dataclass(slots=True)
class StatusEffect:
    id: str
    name: str
    turns_left: int
    potency: int = 0
    icon: str = ""

    def tick(self) -> None:
        self.turns_left = max(0, int(self.turns_left) - 1)

    def alive(self) -> bool:
        return self.turns_left > 0


def status_icon(effect_id: str) -> str:
    return {
        "burn": "B",
        "freeze": "F",
        "weaken": "W",
        "guard": "G",
        "charge": "C",
    }.get(effect_id, "?")


def build_status(effect_id: str, turns: int, potency: int = 0) -> StatusEffect:
    names = {
        "burn": "Burn",
        "freeze": "Freeze",
        "weaken": "Weaken",
        "guard": "Guard",
        "charge": "Charge",
    }
    return StatusEffect(
        id=effect_id,
        name=names.get(effect_id, effect_id.title()),
        turns_left=int(turns),
        potency=int(potency),
        icon=status_icon(effect_id),
    )


def status_damage_over_time(effect: StatusEffect) -> int:
    if effect.id == "burn":
        return max(1, int(effect.potency))
    return 0


def status_skip_turn_chance(effect: StatusEffect) -> float:
    if effect.id == "freeze":
        return 0.35
    return 0.0


def status_damage_multiplier(effect: StatusEffect) -> float:
    if effect.id == "weaken":
        return 0.85
    return 1.0


def status_incoming_damage_multiplier(effect: StatusEffect) -> float:
    if effect.id == "guard":
        return 0.55
    return 1.0
