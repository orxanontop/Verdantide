from __future__ import annotations

"""battle_engine.py

Production-oriented combat core (no UI):
- CTB-style initiative timeline (speed-driven scheduling)
- Data-driven skills, elements, and statuses
- Deterministic event stream (CombatEvent) for UI playback/animation

The goal is to let UI/animation layers stay dumb: they react to events.
"""

import random
from dataclasses import dataclass, field
from pathlib import Path

from character_system import Combatant, ElementLibrary, StatusLibrary
from skill_system import SkillLibrary, SkillDef


@dataclass(slots=True)
class CombatEvent:
    kind: str  # turn|log|action|damage|heal|status|miss|resource
    text: str
    actor: str | None = None
    target: str | None = None
    amount: int | None = None
    tag: str = ""  # effectiveness/crit/status id
    meta: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class Action:
    kind: str  # attack|skill|defend|item
    skill_id: str | None = None
    item_id: str | None = None
    target_id: str | None = None


@dataclass(slots=True)
class ActionPreview:
    title: str
    lines: list[str] = field(default_factory=list)
    target_id: str | None = None


@dataclass(slots=True)
class Content:
    elements: ElementLibrary
    statuses: StatusLibrary
    skills: SkillLibrary

    @staticmethod
    def load(json_dir: Path) -> "Content":
        elements = ElementLibrary.load(json_dir / "elements.json")
        statuses = StatusLibrary.load(json_dir / "statuses.json")
        skills = SkillLibrary.load(json_dir / "skills.json")
        return Content(elements=elements, statuses=statuses, skills=skills)


class BattleEngine:
    """Turn loop + combat resolution. UI consumes the event stream."""

    def __init__(self, *, content: Content | None = None, seed: int | None = None):
        self.content = content or Content.load(Path("jsons"))
        self._rng = random.Random(seed)

        self.turn_index = 0
        self.units: dict[str, Combatant] = {}
        self.active_id: str = ""

    # ---------
    # Setup
    # ---------

    def new_battle(self, units: list[Combatant]) -> None:
        self.turn_index = 0
        self.units = {u.id: u for u in units}

        # Stagger a touch so speed matters immediately.
        for i, u in enumerate(self.units.values()):
            u.next_at = float(i) * 0.02

        self.active_id = self._next_actor_id()

    def get(self, unit_id: str) -> Combatant:
        if unit_id not in self.units:
            raise KeyError(unit_id)
        return self.units[unit_id]

    def alive_units(self) -> list[Combatant]:
        return [u for u in self.units.values() if u.alive()]

    def teams_alive(self) -> set[str]:
        return {u.team for u in self.alive_units()}

    def is_over(self) -> bool:
        return len(self.teams_alive()) <= 1

    def winner_team(self) -> str | None:
        alive = list(self.teams_alive())
        if len(alive) == 1:
            return alive[0]
        return None

    # ---------
    # Timeline
    # ---------

    def upcoming_turns(self, count: int = 8) -> list[str]:
        """Simulate upcoming CTB turns without mutating real unit state."""
        live = [u for u in self.units.values() if u.alive()]
        if not live:
            return []

        sim_next = {u.id: float(u.next_at) for u in live}
        sim_speed = {u.id: self._effective_speed(u) for u in live}

        out: list[str] = []
        for _ in range(max(0, int(count))):
            actor_id = min(sim_next, key=lambda k: sim_next[k])
            out.append(actor_id)
            sim_next[actor_id] += 100.0 / sim_speed[actor_id]
        return out

    def _next_actor_id(self) -> str:
        live = [u for u in self.units.values() if u.alive()]
        if not live:
            return ""
        return min(live, key=lambda u: u.next_at).id

    def _effective_speed(self, unit: Combatant) -> int:
        """Speed with status multipliers applied (for timeline scheduling)."""
        base = max(1.0, float(unit.speed))
        mult = 1.0
        for inst in unit.statuses.values():
            if not inst.alive():
                continue
            sm = float(getattr(inst.defn, "speed_mult", 1.0) or 1.0)
            if sm == 1.0:
                continue
            mult *= sm ** max(1, int(inst.stacks))
        return max(1, int(round(base * mult)))

    def _advance_clock(self, actor: Combatant) -> None:
        actor.next_at += 100.0 / self._effective_speed(actor)

    # ---------
    # Public turn entrypoint
    # ---------

    def player_action(self, action: Action) -> list[CombatEvent]:
        """Resolve a player-selected action, then auto-run AI until player is active again."""
        if self.is_over():
            return []
        if self.active_id != "player":
            return [CombatEvent(kind="log", text="Not your turn.")]

        events: list[CombatEvent] = []
        events.extend(self._take_turn("player", action))
        events.extend(self._auto_enemy_until_player(max_steps=8))
        return events

    # ---------
    # Action preview (UI hinting)
    # ---------

    def preview_action(self, actor_id: str, action: Action) -> ActionPreview | None:
        if actor_id not in self.units:
            return None
        actor = self.get(actor_id)
        if not actor.alive():
            return None

        target: Combatant | None = None
        if action.kind in ("attack", "skill"):
            target = self._choose_target(actor, action.target_id)

        lines: list[str] = []
        title = ""

        if action.kind == "attack":
            title = "Attack"
            if target:
                lines.append(f"Target: {target.name}")
            lines.extend(
                self._estimate_damage(
                    actor,
                    target,
                    base_power=1.0,
                    accuracy=1.0,
                    element_override="Neutral",
                    crit_bonus=0.0,
                    break_bonus=0,
                )
            )

        elif action.kind == "defend":
            title = "Defend"
            try:
                shield = self.content.statuses.get("shield")
                lines.append(f"Gain {shield.name} ({shield.duration}T, x{shield.incoming_mult:.2f} dmg)")
            except Exception:
                lines.append("Reduce the next incoming hit.")

        elif action.kind == "item":
            title = "Item"
            lines.extend(self._preview_item(action.item_id or "", actor))

        elif action.kind == "skill":
            try:
                sd = self.content.skills.get(action.skill_id or "")
            except Exception:
                return ActionPreview(title="Skill", lines=["Unknown skill."])

            title = sd.name
            if sd.kind in ("support", "stance"):
                if sd.heal > 0:
                    lines.append(f"Heal +{sd.heal} HP")
                if sd.gain_sp > 0:
                    lines.append(f"Gain +{sd.gain_sp} SP")
                lines.extend(self._preview_status_lines(actor, actor, sd.apply_status))
            else:
                if target:
                    lines.append(f"Target: {target.name}")
                elem = actor.element if sd.element == "auto" else sd.element
                lines.extend(
                    self._estimate_damage(
                        actor,
                        target,
                        base_power=sd.base_power,
                        accuracy=sd.accuracy,
                        element_override=elem,
                        crit_bonus=sd.crit_bonus,
                        break_bonus=int(getattr(sd, "break_bonus", 0) or 0),
                    )
                )
                lines.extend(self._preview_status_lines(actor, target, sd.apply_status))

        else:
            title = "Action"

        return ActionPreview(title=title, lines=[ln for ln in lines if ln], target_id=(target.id if target else None))

    # ---------
    # Turn resolution
    # ---------

    def _auto_enemy_until_player(self, *, max_steps: int) -> list[CombatEvent]:
        events: list[CombatEvent] = []
        steps = 0
        while not self.is_over() and self.active_id != "player" and steps < int(max_steps):
            # Engine itself is UI-agnostic; AI lives in enemy_ai.py.
            from enemy_ai import choose_enemy_action  # local import avoids cycles

            actor = self.get(self.active_id)
            ai_action = choose_enemy_action(self, actor)
            events.extend(self._take_turn(actor.id, ai_action))
            steps += 1
        return events

    def _choose_default_target(self, actor: Combatant) -> Combatant | None:
        enemies = [u for u in self.units.values() if u.alive() and u.team != actor.team]
        if not enemies:
            return None
        # Prefer the lowest HP% target to create pressure.
        return min(enemies, key=lambda u: u.hp.ratio())

    def _choose_target(self, actor: Combatant, target_id: str | None) -> Combatant | None:
        if target_id:
            t = self.units.get(str(target_id))
            if t and t.alive() and t.team != actor.team:
                return t
        return self._choose_default_target(actor)

    def _tick_statuses_start_turn(self, actor: Combatant) -> list[CombatEvent]:
        events: list[CombatEvent] = []

        # Cooldowns tick at the start of your turn.
        actor.tick_cooldowns()

        # Gentle SP regen to keep pacing snappy (silent UI event animates the bar).
        before_sp = actor.sp.current
        actor.sp.gain(2)
        gained_sp = actor.sp.current - before_sp
        if gained_sp > 0:
            events.append(
                CombatEvent(
                    kind="resource",
                    actor=actor.id,
                    target=actor.id,
                    amount=gained_sp,
                    text="",
                    tag="sp",
                    meta={"silent": True, "sp_to": actor.sp.current, "sp_max": actor.sp.maximum, "reason": "turn_regen"},
                )
            )

        # DoT and per-turn logic.
        for sid, inst in list(actor.statuses.items()):
            if not inst.alive():
                continue

            t = inst.defn.type
            if t == "dot":
                dmg = max(1, int(inst.defn.potency)) * max(1, int(inst.stacks))
                dealt = actor.take_damage(dmg)
                events.append(
                    CombatEvent(
                        kind="damage",
                        actor=None,
                        target=actor.id,
                        amount=dealt,
                        text=f"{actor.name} suffers {dealt} from {inst.defn.name}.",
                        tag=sid,
                        meta={"animation": "dot", "hp_to": actor.hp.current, "hp_max": actor.hp.maximum},
                    )
                )

            elif t == "ramp_dot":
                # Increasing damage each time this triggers.
                ticks = int(inst.data.get("ticks", 0)) + 1
                inst.data["ticks"] = ticks
                dmg = (max(0, int(inst.defn.base)) + max(0, int(inst.defn.ramp_per_turn)) * ticks) * max(1, int(inst.stacks))
                dmg = max(1, int(dmg))
                dealt = actor.take_damage(dmg)
                events.append(
                    CombatEvent(
                        kind="damage",
                        actor=None,
                        target=actor.id,
                        amount=dealt,
                        text=f"{actor.name} takes {dealt} poison damage.",
                        tag=sid,
                        meta={"animation": "dot", "hp_to": actor.hp.current, "hp_max": actor.hp.maximum},
                    )
                )

            # charge is consumed by action, not by ticking

        # Duration ticks down (skip charge so it can trigger).
        for sid, inst in list(actor.statuses.items()):
            if not inst.alive():
                del actor.statuses[sid]
                continue
            if inst.defn.type == "charge":
                continue
            inst.tick()
            if not inst.alive():
                del actor.statuses[sid]
                events.append(CombatEvent(kind="status", actor=None, target=actor.id, text=f"{actor.name}'s {inst.defn.name} fades.", tag=sid))

        return events

    def _should_skip_turn(self, actor: Combatant) -> tuple[bool, str]:
        for sid, inst in actor.statuses.items():
            if not inst.alive():
                continue
            if inst.defn.type == "skip":
                if self._rng.random() < max(0.0, min(1.0, float(inst.defn.chance))):
                    return True, sid
        return False, ""

    def _take_turn(self, actor_id: str, action: Action) -> list[CombatEvent]:
        actor = self.get(actor_id)
        if not actor.alive():
            self.active_id = self._next_actor_id()
            return []

        self.turn_index += 1
        events: list[CombatEvent] = [CombatEvent(kind="turn", actor=actor.id, text=f"Turn {self.turn_index}: {actor.name}")]

        events.extend(self._tick_statuses_start_turn(actor))
        if self.is_over():
            self.active_id = self._next_actor_id()
            return events

        skip, sid = self._should_skip_turn(actor)
        if skip:
            events.append(CombatEvent(kind="log", actor=actor.id, text=f"{actor.name} is frozen and loses the turn!", tag=sid))
            self._advance_clock(actor)
            self.active_id = self._next_actor_id()
            return events

        # Forced heavy strike if charged.
        if actor.has("charge"):
            action = Action(kind="skill", skill_id="__heavy_strike__")

        # Resolve.
        if action.kind == "attack":
            target = self._choose_target(actor, action.target_id)
            if target:
                events.extend(self._resolve_damage(actor, target, base_power=1.0, accuracy=1.0, element_override="Neutral", break_bonus=0))

        elif action.kind == "defend":
            actor.apply_status(self.content.statuses, "shield", duration=1, stacks=1)
            events.append(CombatEvent(kind="status", actor=actor.id, target=actor.id, text=f"{actor.name} raises a shield.", tag="shield"))

        elif action.kind == "item":
            events.extend(self._resolve_item(actor, action.item_id or ""))

        elif action.kind == "skill":
            events.extend(self._resolve_skill(actor, action.skill_id or "", target_id=action.target_id))

        else:
            events.append(CombatEvent(kind="log", actor=actor.id, text="..."))

        self._advance_clock(actor)
        self.active_id = self._next_actor_id()

        if self.is_over():
            win = self.winner_team()
            if win == "player":
                events.append(CombatEvent(kind="log", text="Victory!"))
            else:
                events.append(CombatEvent(kind="log", text="Defeat..."))

        return events

    # ---------
    # Resolution helpers
    # ---------

    def _resolve_item(self, user: Combatant, item_id: str) -> list[CombatEvent]:
        events: list[CombatEvent] = []
        if user.items.get(item_id, 0) <= 0:
            return [CombatEvent(kind="log", actor=user.id, text="No items left.")]

        if item_id == "potion":
            user.items[item_id] -= 1
            healed = user.heal(28)
            events.append(
                CombatEvent(
                    kind="heal",
                    actor=user.id,
                    target=user.id,
                    amount=healed,
                    text=f"{user.name} drinks a Potion (+{healed}).",
                    meta={"hp_to": user.hp.current, "hp_max": user.hp.maximum, "animation": "potion"},
                )
            )
            return events

        if item_id == "ether":
            user.items[item_id] -= 1
            before = user.sp.current
            user.sp.gain(20)
            gained = user.sp.current - before
            events.append(
                CombatEvent(
                    kind="resource",
                    actor=user.id,
                    target=user.id,
                    amount=gained,
                    text=f"{user.name} uses Ether (+{gained} SP).",
                    tag="sp",
                    meta={"sp_to": user.sp.current, "sp_max": user.sp.maximum, "animation": "ether"},
                )
            )
            return events

        return [CombatEvent(kind="log", actor=user.id, text="Nothing happens.")]

    def _resolve_skill(self, actor: Combatant, skill_id: str, *, target_id: str | None = None) -> list[CombatEvent]:
        events: list[CombatEvent] = []

        # Built-in forced heavy strike (kept internal so content stays simple).
        if skill_id == "__heavy_strike__":
            actor.remove_status("charge")
            tgt = self._choose_default_target(actor)
            if not tgt:
                return []
            events.append(CombatEvent(kind="action", actor=actor.id, target=tgt.id, text=f"{actor.name} unleashes a Heavy Strike!", tag="heavy"))
            events.extend(self._resolve_damage(actor, tgt, base_power=1.65, accuracy=0.85, element_override="Neutral", animation="heavy", break_bonus=18))
            return events

        # Normal data-driven skill.
        try:
            sd = self.content.skills.get(skill_id)
        except KeyError:
            return [CombatEvent(kind="log", actor=actor.id, text="Unknown skill.")]

        if actor.cooldown(sd.id) > 0:
            return [CombatEvent(kind="log", actor=actor.id, text=f"{sd.name} is on cooldown.")]

        before_sp = actor.sp.current
        if not actor.sp.spend(sd.cost_sp):
            return [CombatEvent(kind="log", actor=actor.id, text=f"{actor.name} lacks SP.")]
        spent = before_sp - actor.sp.current
        if spent > 0:
            events.append(
                CombatEvent(
                    kind="resource",
                    actor=actor.id,
                    target=actor.id,
                    amount=-spent,
                    text="",
                    tag="sp",
                    meta={"silent": True, "sp_to": actor.sp.current, "sp_max": actor.sp.maximum, "reason": "skill_cost"},
                )
            )

        if sd.cooldown > 0:
            actor.set_cooldown(sd.id, sd.cooldown)

        if sd.kind == "support":
            healed = 0
            if sd.heal > 0:
                healed = actor.heal(sd.heal)
                events.append(
                    CombatEvent(
                        kind="heal",
                        actor=actor.id,
                        target=actor.id,
                        amount=healed,
                        text=f"{actor.name} uses {sd.name} (+{healed} HP).",
                        tag=sd.id,
                        meta={"animation": sd.animation, "hp_to": actor.hp.current, "hp_max": actor.hp.maximum},
                    )
                )
            if sd.gain_sp > 0:
                before = actor.sp.current
                actor.sp.gain(sd.gain_sp)
                gained = actor.sp.current - before
                events.append(
                    CombatEvent(
                        kind="resource",
                        actor=actor.id,
                        target=actor.id,
                        amount=gained,
                        text=f"{actor.name} recovers +{gained} SP.",
                        tag="sp",
                        meta={"animation": sd.animation, "sp_to": actor.sp.current, "sp_max": actor.sp.maximum},
                    )
                )
            events.extend(self._apply_skill_statuses(actor, actor, sd))
            return events

        if sd.kind == "stance":
            events.append(CombatEvent(kind="action", actor=actor.id, target=actor.id, text=f"{actor.name} uses {sd.name}.", tag=sd.id, meta={"animation": sd.animation}))
            events.extend(self._apply_skill_statuses(actor, actor, sd))
            return events

        # Attack skill
        target = self._choose_target(actor, target_id)
        if not target:
            return []

        events.append(CombatEvent(kind="action", actor=actor.id, target=target.id, text=f"{actor.name} uses {sd.name}!", tag=sd.id, meta={"animation": sd.animation}))
        elem = actor.element if sd.element == "auto" else sd.element
        events.extend(
            self._resolve_damage(
                actor,
                target,
                base_power=sd.base_power,
                accuracy=sd.accuracy,
                element_override=elem,
                crit_bonus=sd.crit_bonus,
                animation=sd.animation,
                break_bonus=int(getattr(sd, "break_bonus", 0) or 0),
            )
        )
        events.extend(self._apply_skill_statuses(actor, target, sd))
        return events

    def _apply_skill_statuses(self, actor: Combatant, target: Combatant, sd: SkillDef) -> list[CombatEvent]:
        events: list[CombatEvent] = []
        spec = sd.apply_status

        def apply_one(status_id: str, *, duration: int | None, stacks: int, chance: float):
            if self._rng.random() > max(0.0, min(1.0, float(chance))):
                return
            inst = target.apply_status(self.content.statuses, status_id, duration=duration, stacks=stacks)
            events.append(CombatEvent(kind="status", actor=actor.id, target=target.id, text=f"{target.name} gains {inst.defn.name}.", tag=status_id))

        # Alias: based on attacker element.
        if isinstance(spec, str) and spec == "auto_by_element":
            elem = self.content.elements.normalize(actor.element)
            if elem == "Fire":
                apply_one("burn", duration=2, stacks=1, chance=1.0)
            elif elem == "Ice":
                apply_one("freeze", duration=2, stacks=1, chance=1.0)
            elif elem == "Wind":
                apply_one("poison", duration=3, stacks=1, chance=1.0)
            return events

        # Explicit list.
        if isinstance(spec, list):
            for row in spec:
                if not isinstance(row, dict):
                    continue
                apply_one(
                    str(row.get("id", "")),
                    duration=(int(row.get("duration")) if row.get("duration") is not None else None),
                    stacks=int(row.get("stacks", 1) or 1),
                    chance=float(row.get("chance", 1.0) or 1.0),
                )

        return events

    def _preview_status_lines(self, actor: Combatant, target: Combatant | None, spec: object) -> list[str]:
        lines: list[str] = []
        if target is None:
            return lines

        def add_line(status_id: str, duration: int | None, chance: float) -> None:
            try:
                defn = self.content.statuses.get(status_id)
                name = defn.name
                turns = int(duration if duration is not None else defn.duration)
            except Exception:
                name = status_id
                turns = int(duration or 1)
            pct = int(round(max(0.0, min(1.0, float(chance))) * 100))
            verb = "Gain" if target.id == actor.id else "Inflict"
            lines.append(f"{verb} {name} ({turns}T, {pct}%)")

        if isinstance(spec, str) and spec == "auto_by_element":
            elem = self.content.elements.normalize(actor.element)
            if elem == "Fire":
                add_line("burn", None, 1.0)
            elif elem == "Ice":
                add_line("freeze", None, 1.0)
            elif elem == "Wind":
                add_line("poison", None, 1.0)
            return lines

        if isinstance(spec, list):
            for row in spec:
                if not isinstance(row, dict):
                    continue
                add_line(
                    str(row.get("id", "")),
                    duration=(int(row.get("duration")) if row.get("duration") is not None else None),
                    chance=float(row.get("chance", 1.0) or 1.0),
                )

        return lines

    def _preview_item(self, item_id: str, user: Combatant) -> list[str]:
        if item_id == "potion":
            return [f"Restore 28 HP (x{user.items.get(item_id, 0)})"]
        if item_id == "ether":
            return [f"Restore 20 SP (x{user.items.get(item_id, 0)})"]
        return ["No effect"]

    def _collect_outgoing_mult(self, attacker: Combatant) -> float:
        mult = 1.0
        for inst in attacker.statuses.values():
            if not inst.alive():
                continue
            m = float(getattr(inst.defn, "outgoing_mult", 1.0) or 1.0)
            if m == 1.0:
                continue
            mult *= m ** max(1, int(inst.stacks))
        return mult

    def _collect_incoming_mult(self, defender: Combatant) -> tuple[float, list[str]]:
        mult = 1.0
        consume: list[str] = []
        for sid, inst in defender.statuses.items():
            if not inst.alive():
                continue
            m = float(getattr(inst.defn, "incoming_mult", 1.0) or 1.0)
            if m == 1.0:
                continue
            if inst.defn.type == "shield":
                mult *= max(0.05, m)
                consume.append(sid)
            else:
                mult *= m ** max(1, int(inst.stacks))
        return mult, consume

    def _estimate_damage(
        self,
        attacker: Combatant,
        defender: Combatant | None,
        *,
        base_power: float,
        accuracy: float,
        element_override: str,
        crit_bonus: float,
        break_bonus: int,
    ) -> list[str]:
        if defender is None or (not attacker.alive()) or (not defender.alive()):
            return ["No target."]

        acc = max(0.05, min(1.0, float(attacker.accuracy) * float(accuracy)))
        crit = max(0.0, min(1.0, float(attacker.crit_chance) + float(crit_bonus)))

        base = float(attacker.attack) * float(base_power)
        base -= float(defender.defense) * 0.55
        base = max(1.0, base)

        elem_mult, label = self.content.elements.multiplier(element_override, defender.element)
        incoming_mult, _consume = self._collect_incoming_mult(defender)
        outgoing_mult = self._collect_outgoing_mult(attacker)

        expected_crit = 1.0 + crit * (float(attacker.crit_mult) - 1.0)
        est = int(round(base * elem_mult * incoming_mult * outgoing_mult * expected_crit))
        est = max(1, est)

        break_gain = self._compute_break_gain(est, label, is_crit=False, break_bonus=break_bonus)

        lines = [f"Hit: {int(round(acc * 100))}%"]
        if crit > 0:
            lines.append(f"Crit: {int(round(crit * 100))}%")
        if label:
            lines.append(label)
        lines.append(f"Est. Dmg: {est}")
        if break_gain > 0:
            lines.append(f"Break +{break_gain}")
        return lines

    def _compute_break_gain(self, dealt: int, effectiveness: str, *, is_crit: bool, break_bonus: int) -> int:
        base = 6 + min(14, int(max(0, int(dealt)) * 0.18))
        if effectiveness == "Super Effective":
            base += 10
        elif effectiveness == "Resisted":
            base = max(0, base - 4)
        if is_crit:
            base += 6
        base += max(0, int(break_bonus))
        return max(0, int(base))

    def _resolve_damage(
        self,
        attacker: Combatant,
        defender: Combatant,
        *,
        base_power: float,
        accuracy: float,
        element_override: str,
        crit_bonus: float = 0.0,
        animation: str = "slash",
        break_bonus: int = 0,
    ) -> list[CombatEvent]:
        if not attacker.alive() or not defender.alive():
            return []

        events: list[CombatEvent] = []

        # Accuracy gate
        hit_roll = self._rng.random()
        acc = max(0.05, min(1.0, float(attacker.accuracy) * float(accuracy)))
        if hit_roll > acc:
            events.append(CombatEvent(kind="miss", actor=attacker.id, target=defender.id, text=f"{attacker.name} misses!", meta={"animation": animation}))
            return events

        # Base damage with small variance
        variance = self._rng.uniform(0.92, 1.08)
        base = float(attacker.attack) * float(base_power) * variance
        base -= float(defender.defense) * 0.55
        base = max(1.0, base)

        # Element
        mult, label = self.content.elements.multiplier(element_override, defender.element)

        # Outgoing + incoming modifiers (shield consumes on hit).
        outgoing_mult = self._collect_outgoing_mult(attacker)
        incoming_mult, consume = self._collect_incoming_mult(defender)

        # Crit
        is_crit = self._rng.random() < max(0.0, min(1.0, float(attacker.crit_chance) + float(crit_bonus)))
        if is_crit:
            base *= float(attacker.crit_mult)

        dmg = int(round(base * mult * incoming_mult * outgoing_mult))
        dmg = max(1, dmg)
        dealt = defender.take_damage(dmg)

        for sid in consume:
            defender.remove_status(sid)

        tag = ""
        if label:
            tag = label
        if is_crit:
            tag = (tag + " | " if tag else "") + "CRIT"

        events.append(
            CombatEvent(
                kind="damage",
                actor=attacker.id,
                target=defender.id,
                amount=dealt,
                text=f"{attacker.name} hits {defender.name} for {dealt}.",
                tag=tag,
                meta={
                    "animation": animation,
                    "element": element_override,
                    "crit": is_crit,
                    "hp_to": defender.hp.current,
                    "hp_max": defender.hp.maximum,
                },
            )
        )

        # Break gauge build-up (separate resource events so UI can animate deterministically).
        events.extend(self._apply_break(attacker, defender, dealt=dealt, effectiveness=label, is_crit=is_crit, break_bonus=break_bonus))
        return events

    def _apply_break(
        self,
        attacker: Combatant,
        defender: Combatant,
        *,
        dealt: int,
        effectiveness: str,
        is_crit: bool,
        break_bonus: int,
    ) -> list[CombatEvent]:
        if not defender.alive() or defender.break_gauge.maximum <= 0:
            return []

        # Don't build break on a unit that's already in a broken state.
        if defender.has("broken"):
            return []

        gain = self._compute_break_gain(dealt, effectiveness, is_crit=is_crit, break_bonus=break_bonus)
        if gain <= 0:
            return []

        events: list[CombatEvent] = []
        before = defender.break_gauge.current
        defender.break_gauge.gain(gain)
        after = defender.break_gauge.current
        if after != before:
            events.append(
                CombatEvent(
                    kind="resource",
                    actor=attacker.id,
                    target=defender.id,
                    amount=after - before,
                    text="",
                    tag="break",
                    meta={"silent": True, "break_to": after, "break_max": defender.break_gauge.maximum},
                )
            )

        if defender.break_gauge.current >= defender.break_gauge.maximum:
            # Trigger break: apply a stun-like status and reset the gauge.
            try:
                defender.apply_status(self.content.statuses, "broken", duration=2, stacks=1)
                events.append(CombatEvent(kind="status", actor=attacker.id, target=defender.id, amount=None, text=f"{defender.name} is Broken!", tag="broken", meta={"animation": "break"}))
            except Exception:
                pass

            defender.break_gauge.set(0)
            events.append(
                CombatEvent(
                    kind="resource",
                    actor=attacker.id,
                    target=defender.id,
                    amount=0,
                    text="",
                    tag="break",
                    meta={"silent": True, "break_to": 0, "break_max": defender.break_gauge.maximum, "reason": "break_reset"},
                )
            )

        return events
