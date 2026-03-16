from __future__ import annotations

"""combat_phases.py

Modular turn resolution phases for cleaner architecture.
Each phase is a separate class handling its specific responsibility.
"""

from dataclasses import dataclass, field
from typing import Callable

from battle_engine import Action, CombatEvent, Combatant
from character_system import StatusLibrary, ElementLibrary
from skill_system import SkillLibrary, SkillDef


@dataclass
class PhaseContext:
    """Shared context passed through all phases of a turn."""
    engine: "BattleEngineCore"
    actor: Combatant
    action: Action
    events: list[CombatEvent] = field(default_factory=list)
    target: Combatant | None = None
    skill: SkillDef | None = None


class TurnPhase:
    """Base class for all combat phases."""
    
    def execute(self, ctx: PhaseContext) -> bool:
        """Execute the phase. Returns True if turn should continue, False to end early."""
        raise NotImplementedError


class StatusTickPhase(TurnPhase):
    """Handles status effect ticking at turn start."""
    
    def execute(self, ctx: PhaseContext) -> bool:
        ctx.events.extend(ctx.engine._tick_statuses_start_turn(ctx.actor))
        return not ctx.engine.is_over()


class SkipCheckPhase(TurnPhase):
    """Checks if actor should skip turn due to status."""
    
    def execute(self, ctx: PhaseContext) -> bool:
        skip, sid = ctx.engine._should_skip_turn(ctx.actor)
        if skip:
            ctx.events.append(CombatEvent(
                kind="log",
                actor=ctx.actor.id,
                text=f"{ctx.actor.id} is frozen and loses the turn!",
                tag=sid
            ))
            ctx.engine._advance_clock(ctx.actor)
            ctx.engine.active_id = ctx.engine._next_actor_id()
            return False
        return True


class ChargeCheckPhase(TurnPhase):
    """Checks if charged status forces heavy strike."""
    
    def execute(self, ctx: PhaseContext) -> bool:
        if ctx.actor.has("charge"):
            ctx.action = Action(kind="skill", skill_id="__heavy_strike__")
        return True


class ActionResolutionPhase(TurnPhase):
    """Main action resolution - dispatches to appropriate handler."""
    
    def execute(self, ctx: PhaseContext) -> bool:
        if ctx.action.kind == "attack":
            if ctx.target:
                ctx.events.extend(ctx.engine._resolve_damage(
                    ctx.actor, ctx.target,
                    base_power=1.0, accuracy=1.0,
                    element_override="Neutral", break_bonus=0
                ))
        
        elif ctx.action.kind == "defend":
            ctx.actor.apply_status(ctx.engine.content.statuses, "shield", duration=1, stacks=1)
            ctx.events.append(CombatEvent(
                kind="status",
                actor=ctx.actor.id,
                target=ctx.actor.id,
                text=f"{ctx.actor.id} raises a shield.",
                tag="shield"
            ))
        
        elif ctx.action.kind == "item":
            ctx.events.extend(ctx.engine._resolve_item(ctx.actor, ctx.action.item_id or ""))
        
        elif ctx.action.kind == "skill":
            ctx.events.extend(ctx.engine._resolve_skill(ctx.actor, ctx.action.skill_id or "", target_id=ctx.action.target_id))
        
        else:
            ctx.events.append(CombatEvent(kind="log", actor=ctx.actor.id, text="..."))
        
        return True


class TimelineAdvancePhase(TurnPhase):
    """Advances the CTB timeline after action completes."""
    
    def execute(self, ctx: PhaseContext) -> bool:
        time_mult = 1.0
        if ctx.action.kind == "skill":
            if ctx.action.skill_id == "__heavy_strike__":
                time_mult = 1.25
            elif ctx.skill:
                time_mult = ctx.engine._action_time_mult(ctx.action, skill=ctx.skill)
        else:
            time_mult = ctx.engine._action_time_mult(ctx.action)
        
        ctx.engine._advance_clock(ctx.actor, time_mult=time_mult)
        ctx.engine.active_id = ctx.engine._next_actor_id()
        
        if ctx.engine.is_over():
            win = ctx.engine.winner_team()
            if win == "player":
                ctx.events.append(CombatEvent(kind="log", text="Victory!"))
            else:
                ctx.events.append(CombatEvent(kind="log", text="Defeat..."))
        
        return True


class PhaseSequence:
    """Manages the execution order of combat phases."""
    
    def __init__(self, phases: list[TurnPhase]):
        self.phases = phases
    
    def execute(self, ctx: PhaseContext) -> list[CombatEvent]:
        for phase in self.phases:
            if not phase.execute(ctx):
                break
        return ctx.events


class ExploitSystem:
    """Handles elemental exploit bonuses for combo damage."""
    
    def __init__(self, elements: ElementLibrary):
        self.elements = elements
    
    def compute_exploit_bonus(
        self,
        attacker: Combatant,
        defender: Combatant,
        element: str,
        base_damage: int,
    ) -> tuple[int, str, list[CombatEvent]]:
        """
        Calculate exploit bonus for hitting elemental weakness.
        Returns (bonus_damage, exploit_label, events).
        """
        mult, label = self.elements.multiplier(element, defender.element)
        events = []
        
        if label == "Super Effective":
            bonus = int(base_damage * 0.5)
            events.append(CombatEvent(
                kind="log",
                actor=attacker.id,
                target=defender.id,
                text=f"Exploit! {bonus} bonus damage!",
                tag="exploit"
            ))
            return bonus, "Exploit", events
        
        return 0, "", events
    
    def compute_break_exploit(
        self,
        attacker: Combatant,
        defender: Combatant,
        element: str,
        base_break: int,
    ) -> int:
        """Calculate additional break gauge gain from exploits."""
        mult, label = self.elements.multiplier(element, defender.element)
        if label == "Super Effective":
            return int(base_break * 0.5)
        return 0


class CombatPhaseEngine:
    """Core battle logic extracted from BattleEngine for cleaner architecture."""
    
    def __init__(self, content, rng, units: dict):
        self.content = content
        self._rng = rng
        self.units = units
        self.turn_index = 0
        self.active_id = ""
        self.exploit_system = ExploitSystem(content.elements)
        
        self.phase_sequence = PhaseSequence([
            StatusTickPhase(),
            SkipCheckPhase(),
            ChargeCheckPhase(),
            ActionResolutionPhase(),
            TimelineAdvancePhase(),
        ])
    
    def take_turn(self, actor_id: str, action: Action) -> list[CombatEvent]:
        actor = self.units.get(actor_id)
        if not actor or not actor.alive():
            self.active_id = self._next_actor_id()
            return []
        
        self.turn_index += 1
        events = [CombatEvent(
            kind="turn",
            actor=actor.id,
            text=f"Turn {self.turn_index}: {actor.id}"
        )]
        
        actor, action, events, target, skill = self._prepare_context(actor, action, events)
        
        ctx = PhaseContext(
            engine=self,
            actor=actor,
            action=action,
            events=events,
            target=target,
            skill=skill,
        )
        
        events.extend(self.phase_sequence.execute(ctx))
        return events
    
    def _prepare_context(self, actor, action, events):
        target = None
        skill = None
        
        if action.kind == "skill" and action.skill_id:
            try:
                skill = self.content.skills.get(action.skill_id)
            except Exception:
                skill = None
        
        return actor, action, events, target, skill
    
    def _next_actor_id(self) -> str:
        live = [u for u in self.units.values() if u.alive()]
        if not live:
            return ""
        return min(live, key=lambda u: u.next_at).id
    
    def is_over(self) -> bool:
        teams = {u.team for u in self.units.values() if u.alive()}
        return len(teams) <= 1
    
    def winner_team(self) -> str | None:
        alive = list({u.team for u in self.units.values() if u.alive()})
        if len(alive) == 1:
            return alive[0]
        return None
    
    def _tick_statuses_start_turn(self, actor: Combatant) -> list[CombatEvent]:
        events = []
        actor.tick_cooldowns()
        
        before_sp = actor.sp.current
        actor.sp.gain(2)
        gained_sp = actor.sp.current - before_sp
        if gained_sp > 0:
            events.append(CombatEvent(
                kind="resource",
                actor=actor.id,
                target=actor.id,
                amount=gained_sp,
                text="",
                tag="sp",
                meta={"silent": True, "sp_to": actor.sp.current, "sp_max": actor.sp.maximum, "reason": "turn_regen"},
            ))
        
        for sid, inst in list(actor.statuses.items()):
            if not inst.alive():
                continue
            
            t = inst.defn.type
            if t == "dot":
                dmg = max(1, int(inst.defn.potency)) * max(1, int(inst.stacks))
                dealt = actor.take_damage(dmg)
                events.append(CombatEvent(
                    kind="damage",
                    actor=None,
                    target=actor.id,
                    amount=dealt,
                    text=f"{actor.id} suffers {dealt} from {inst.defn.name}.",
                    tag=sid,
                    meta={"animation": "dot", "hp_to": actor.hp.current, "hp_max": actor.hp.maximum},
                ))
            
            elif t == "ramp_dot":
                ticks = int(inst.data.get("ticks", 0)) + 1
                inst.data["ticks"] = ticks
                dmg = (max(0, int(inst.defn.base)) + max(0, int(inst.defn.ramp_per_turn)) * ticks) * max(1, int(inst.stacks))
                dmg = max(1, int(dmg))
                dealt = actor.take_damage(dmg)
                events.append(CombatEvent(
                    kind="damage",
                    actor=None,
                    target=actor.id,
                    amount=dealt,
                    text=f"{actor.id} takes {dealt} poison damage.",
                    tag=sid,
                    meta={"animation": "dot", "hp_to": actor.hp.current, "hp_max": actor.hp.maximum},
                ))
        
        for sid, inst in list(actor.statuses.items()):
            if not inst.alive():
                del actor.statuses[sid]
                continue
            if inst.defn.type == "charge":
                continue
            inst.tick()
            if not inst.alive():
                del actor.statuses[sid]
                events.append(CombatEvent(
                    kind="status",
                    actor=None,
                    target=actor.id,
                    text=f"{actor.id}'s {inst.defn.name} fades.",
                    tag=sid
                ))
        
        return events
    
    def _should_skip_turn(self, actor: Combatant) -> tuple[bool, str]:
        for sid, inst in actor.statuses.items():
            if not inst.alive():
                continue
            if inst.defn.type == "skip":
                if self._rng.random() < max(0.0, min(1.0, float(inst.defn.chance))):
                    return True, sid
        return False, ""
    
    def _advance_clock(self, actor: Combatant, *, time_mult: float = 1.0) -> None:
        time_mult = max(0.3, float(time_mult))
        speed = self._effective_speed(actor)
        actor.next_at += (100.0 / speed) * time_mult
    
    def _effective_speed(self, unit: Combatant) -> int:
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
    
    def _action_time_mult(self, action: Action, *, skill: SkillDef | None = None) -> float:
        if action.kind == "defend":
            return 0.9
        if action.kind == "item":
            return 0.85
        if action.kind == "skill" and skill is not None:
            return max(0.5, float(getattr(skill, "time_mult", 1.0) or 1.0))
        return 1.0
    
    def _resolve_damage(self, attacker, defender, **kwargs) -> list[CombatEvent]:
        return []
    
    def _resolve_item(self, user, item_id: str) -> list[CombatEvent]:
        return []
    
    def _resolve_skill(self, actor, skill_id: str, **kwargs) -> list[CombatEvent]:
        return []
