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

    # If enemy is broken, they can't act - but this is handled by engine
    if actor.has("broken"):
        return Action(kind="attack")

    target = engine._choose_default_target(actor)
    if not target:
        return Action(kind="attack")

    # Build candidate list with enhanced decision matrix
    candidates: list[tuple[float, Action]] = []

    def add(weight: float, action: Action):
        if weight <= 0:
            return
        candidates.append((float(weight), action))

    def status_ids(spec) -> set[str]:
        ids: set[str] = set()
        if isinstance(spec, list):
            for row in spec:
                if isinstance(row, dict):
                    sid = str(row.get("id", "")).strip()
                    if sid:
                        ids.add(sid)
        return ids

    def score_attack(*, base_power: float, accuracy: float, element: str, crit_bonus: float, break_bonus: int, time_mult: float, timeline_push: float) -> float:
        est = engine.estimate_damage(
            actor,
            target,
            base_power=base_power,
            accuracy=accuracy,
            element_override=element,
            crit_bonus=crit_bonus,
            break_bonus=break_bonus,
        )
        score = float(est.expected_damage)
        
        # Factor in break gauge state
        br = float(target.break_gauge.ratio())
        score += float(est.break_gain) * (0.45 + br)
        
        # Heavily prioritize breaking when gauge is near full
        if br > 0.7:
            score *= 1.4

        if est.effectiveness == "Super Effective":
            score *= 1.25
        elif est.effectiveness == "Resisted":
            score *= 0.75

        if target.has("broken"):
            score *= 1.15

        if timeline_push > 0:
            score += 10.0 * float(timeline_push)

        # Prefer faster actions when behind in timeline
        if time_mult < 1.0:
            score *= 1.15

        return score / max(0.5, float(time_mult))

    # Baseline attack
    add(
        score_attack(
            base_power=1.0,
            accuracy=1.0,
            element="Neutral",
            crit_bonus=0.0,
            break_bonus=0,
            time_mult=1.0,
            timeline_push=0.0,
        ),
        Action(kind="attack"),
    )

    # Defend strategically - more when low HP or when target has break ready
    defend_weight = 0.3
    if actor.hp.ratio() < 0.35:
        defend_weight += 0.8
    if target.break_gauge.ratio() > 0.6:
        defend_weight += 0.5
    add(defend_weight, Action(kind="defend"))

    # Items (if available) - prioritize when desperate
    if actor.items.get("potion", 0) > 0:
        missing = 1.0 - float(actor.hp.ratio())
        if missing >= 0.25:
            add(2.0 + missing * 4.0, Action(kind="item", item_id="potion"))

    if actor.items.get("ether", 0) > 0:
        sp_missing = 1.0 - float(actor.sp.ratio())
        if sp_missing >= 0.35:
            add(1.2 + sp_missing * 2.5, Action(kind="item", item_id="ether"))

    # Skills with enhanced scoring
    for sid in list(actor.skills or []):
        try:
            sd = engine.content.skills.get(sid)
        except Exception:
            continue

        if actor.cooldown(sd.id) > 0:
            continue
        if sd.cost_sp > actor.sp.current:
            continue

        time_mult = float(getattr(sd, "time_mult", 1.0) or 1.0)
        timeline_push = float(getattr(sd, "timeline_push", 0.0) or 0.0)

        if sd.kind in ("support", "stance"):
            w = 0.7
            missing = 1.0 - float(actor.hp.ratio())
            if sd.heal > 0:
                w += (sd.heal * (0.18 + missing * 0.7))
            if sd.gain_sp > 0:
                sp_missing = 1.0 - float(actor.sp.ratio())
                w += (sd.gain_sp * (0.1 + sp_missing * 0.4))

            ids = status_ids(sd.apply_status)
            if "haste" in ids and (not actor.has("haste")):
                w += 2.5
            if "fury" in ids and (not actor.has("fury")):
                w += 2.2
            if "charge" in ids and (not actor.has("charge")):
                w += 1.8
            if "shield" in ids and (not actor.has("shield")):
                if actor.hp.ratio() < 0.5:
                    w += 2.0

            w = w / max(0.5, time_mult)
            add(w, Action(kind="skill", skill_id=sd.id))
            continue

        # Attack skill scoring with elemental exploitation
        elem = actor.element if sd.element == "auto" else sd.element
        w = score_attack(
            base_power=sd.base_power,
            accuracy=sd.accuracy,
            element=elem,
            crit_bonus=sd.crit_bonus,
            break_bonus=int(getattr(sd, "break_bonus", 0) or 0),
            time_mult=time_mult,
            timeline_push=timeline_push,
        )

        ids = status_ids(sd.apply_status)
        
        # Prioritize applying debuffs that aren't on target
        if "weaken" in ids and (not target.has("weaken")):
            w += 3.2
        if "exposed" in ids and (not target.has("exposed")):
            w += 3.7
        if "poison" in ids and (not target.has("poison")):
            w += 2.5
        if "burn" in ids and (not target.has("burn")):
            w += 2.8
        if "freeze" in ids and (not target.has("freeze")):
            w += 2.8

        # Prefer burst skills when target is low HP
        if "burst" in str(sd.id).lower() and target.hp.ratio() < 0.55:
            w += 2.5
        
        # Prefer timeline push skills to delay dangerous targets
        if timeline_push > 0.3 and target.has("charge"):
            w += 3.0

        # Cooldown skills are stronger; bias toward using them if ready
        w += min(1.2, 0.3 * max(0, int(sd.cooldown)))

        add(w, Action(kind="skill", skill_id=sd.id))

    # If no candidates, fallback to basic attack
    if not candidates:
        return Action(kind="attack")

    # Weighted random choice - add small noise to prevent exact repeats
    total = sum(w for w, _a in candidates)
    roll = rng.random() * total
    acc = 0.0
    for w, a in candidates:
        acc += w
        if roll <= acc:
            return a

    return candidates[-1][1]
