from __future__ import annotations

"""character_stats.py

UI-agnostic data containers for combat stats and resources.
- Resource supports spend/gain/clamp/ratio
- CharacterStats owns HP/SP and core battle stats
"""

from dataclasses import dataclass, field


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


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


@dataclass(slots=True)
class CharacterStats:
    """UI-agnostic combat stats container."""

    name: str
    element: str = "Neutral"

    hp: Resource = field(default_factory=lambda: Resource(100, 100))
    sp: Resource = field(default_factory=lambda: Resource(50, 50))  # stamina / mana

    attack: int = 14
    defense: int = 6
    speed: int = 10
    accuracy: float = 0.95
    crit_chance: float = 0.08
    crit_mult: float = 1.5

    def is_alive(self) -> bool:
        return self.hp.current > 0

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
