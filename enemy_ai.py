from __future__ import annotations

"""enemy_ai.py

Enemy decision module.

This is intentionally simple but scalable:
- Enumerate legal actions (attack/defend/items/skills)
- Score each using a few heuristics (HP pressure, SP economy, elemental matchup)
- Weighted-random choice to avoid deterministic patterns

In a full game you can swap this for behavior trees/utility AI per enemy profile.
"""

import random

from battle_engine import Action, BattleEngine


def choose_enemy_action(engine: BattleEngine, actor) -> Action:
    rng = getattr(engine, "_rng", random.Random())

    # If already charging, the engine will force heavy strike, but we can be explicit.
    if actor.has("charge"):
        return Action(kind="skill", skill_id="__heavy_strike__")

    target = engine._choose_default_target(actor)
    if not target:
        return Action(kind="attack")

    # Build candidate list
    candidates: list[tuple[float, Action]] = []

    def add(weight: float, action: Action):
        if weight <= 0:
            return
        candidates.append((float(weight), action))

    # Baseline attack
    add(1.0, Action(kind="attack"))

    # Defend occasionally, more when low HP
    add(0.25 + (0.9 if actor.hp.ratio() < 0.35 else 0.0), Action(kind="defend"))

    # Items (if available)
    if actor.items.get("potion", 0) > 0 and actor.hp.ratio() < 0.45:
        add(2.2, Action(kind="item", item_id="potion"))

    if actor.items.get("ether", 0) > 0 and actor.sp.ratio() < 0.35:
        add(1.4, Action(kind="item", item_id="ether"))

    # Skills
    for sid in list(actor.skills or []):
        try:
            sd = engine.content.skills.get(sid)
        except Exception:
            continue

        if actor.cooldown(sd.id) > 0:
            continue
        if sd.cost_sp > actor.sp.current:
            continue

        # Base desire for using a skill
        w = 0.9

        # Prefer burst-like skills when target is low.
        if "burst" in sd.id and target.hp.ratio() < 0.55:
            w += 1.0

        # Prefer sunder-like pressure when it will matter.
        if "sunder" in sd.id and (not target.has("exposed")):
            w += 0.55

        # Prefer quick-step when not already hasted.
        if "quick_step" in sd.id and (not actor.has("haste")):
            w += 0.65

        # Prefer focus-type support when low.
        if sd.kind == "support" and actor.hp.ratio() < 0.55:
            w += 1.0

        # Elemental advantage
        elem = actor.element if sd.element == "auto" else sd.element
        mult, label = engine.content.elements.multiplier(elem, target.element)
        if mult >= engine.content.elements.super_mult:
            w += 1.1
        elif mult <= engine.content.elements.resisted_mult:
            w -= 0.35

        # Break pressure: use high-break skills when target is close to breaking.
        try:
            br = float(target.break_gauge.ratio())
        except Exception:
            br = 0.0
        if br >= 0.55 and int(getattr(sd, "break_bonus", 0) or 0) >= 10:
            w += 0.85

        # Cooldown skills are stronger; bias toward using them if ready.
        w += min(0.6, 0.2 * max(0, int(sd.cooldown)))

        add(w, Action(kind="skill", skill_id=sd.id))

    # If no candidates, fallback.
    if not candidates:
        return Action(kind="attack")

    # Weighted random choice
    total = sum(w for w, _a in candidates)
    roll = rng.random() * total
    acc = 0.0
    for w, a in candidates:
        acc += w
        if roll <= acc:
            return a

    return candidates[-1][1]
