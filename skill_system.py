from __future__ import annotations

"""skill_system.py

Data-driven skill framework.

- SkillDef: immutable definition loaded from JSON.
- SkillLibrary: loads/validates skill content.
- Cooldowns are stored per-combatant (engine-owned) to keep UI stateless.

This file intentionally contains no Tk/UI code.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SkillDef:
    id: str
    name: str
    icon: str
    kind: str  # attack|support|stance
    element: str  # Fire|Ice|Wind|Neutral|auto

    # Attack skills
    base_power: float = 1.0
    accuracy: float = 1.0
    crit_bonus: float = 0.0

    # Support skills
    heal: int = 0
    gain_sp: int = 0

    # Economy
    cost_sp: int = 0
    cooldown: int = 0

    target: str = "enemy"  # enemy|self|ally
    apply_status: object = None  # string alias or list[dict]
    animation: str = "slash"
    description: str = ""


class SkillLibrary:
    """Loads skill definitions from JSON and exposes a stable lookup API."""

    def __init__(self, skills: dict[str, SkillDef]):
        self._skills = dict(skills)

    def get(self, skill_id: str) -> SkillDef:
        if skill_id not in self._skills:
            raise KeyError(f"Unknown skill: {skill_id}")
        return self._skills[skill_id]

    def all(self) -> list[SkillDef]:
        return list(self._skills.values())

    @staticmethod
    def load(path: Path) -> "SkillLibrary":
        raw = []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raw = []

        skills: dict[str, SkillDef] = {}
        for row in raw if isinstance(raw, list) else []:
            try:
                sid = str(row.get("id", "")).strip()
                if not sid:
                    continue
                skills[sid] = SkillDef(
                    id=sid,
                    name=str(row.get("name", sid)).strip(),
                    icon=str(row.get("icon", "✦")),
                    kind=str(row.get("kind", "attack")),
                    element=str(row.get("element", "Neutral")),
                    base_power=float(row.get("base_power", 1.0) or 1.0),
                    accuracy=float(row.get("accuracy", 1.0) or 1.0),
                    crit_bonus=float(row.get("crit_bonus", 0.0) or 0.0),
                    heal=int(row.get("heal", 0) or 0),
                    gain_sp=int(row.get("gain_sp", 0) or 0),
                    cost_sp=int(row.get("cost_sp", 0) or 0),
                    cooldown=int(row.get("cooldown", 0) or 0),
                    target=str(row.get("target", "enemy")),
                    apply_status=row.get("apply_status"),
                    animation=str(row.get("animation", "slash")),
                    description=str(row.get("description", "")),
                )
            except Exception:
                continue

        return SkillLibrary(skills)