from __future__ import annotations

"""battle_logic.py

Pure combat rules (no UI):
- CTB/initiative scheduling using Speed
- Action resolution (attack, skills, items, defend, heavy charge/strike)
- Element triangle effectiveness and status effects

Produces CombatEvent objects consumed by the UI.
"""

import random
from dataclasses import dataclass, field

from character_stats import CharacterStats
from combat_effects import (
    build_status,
    element_multiplier,
    normalize_element,
    status_damage_multiplier,
    status_damage_over_time,
    status_incoming_damage_multiplier,
    status_skip_turn_chance,
)


@dataclass(slots=True)
class CombatEvent:
    kind: str  # log|turn|damage|heal|status|miss|effect
    text: str
    actor: str | None = None
    target: str | None = None
    amount: int | None = None
    tag: str = ""  # effectiveness, crit, etc.


@dataclass(slots=True)
class BattleUnit:
    id: str
    stats: CharacterStats
    statuses: dict[str, object] = field(default_factory=dict)

    # Simple inventory for demo purposes (expand later).
    items: dict[str, int] = field(default_factory=lambda: {"potion": 2, "ether": 1})

    # CTB scheduling
    next_at: float = 0.0

    def alive(self) -> bool:
        return self.stats.is_alive()

    def has(self, status_id: str) -> bool:
        eff = self.statuses.get(status_id)
        return bool(eff) and getattr(eff, "turns_left", 0) > 0

    def put(self, status) -> None:
        self.statuses[status.id] = status

    def remove(self, status_id: str) -> None:
        if status_id in self.statuses:
            del self.statuses[status_id]


class BattleEngine:
    """Pure logic for turn order and action resolution."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self.turn_index = 0
        self.player: BattleUnit | None = None
        self.enemy: BattleUnit | None = None
        self.active_id: str = "player"

    def new_battle(self, player: CharacterStats, enemy: CharacterStats) -> None:
        self.turn_index = 0
        self.player = BattleUnit(id="player", stats=player)
        self.enemy = BattleUnit(id="enemy", stats=enemy)

        # Stagger initial times slightly so speed matters immediately.
        self.player.next_at = 0.0
        self.enemy.next_at = 0.02

        self.active_id = self._next_actor_id()

    def units(self) -> list[BattleUnit]:
        return [u for u in (self.player, self.enemy) if u is not None]

    def get(self, unit_id: str) -> BattleUnit:
        u = self.player if unit_id == "player" else self.enemy
        if u is None:
            raise RuntimeError("Battle not initialized")
        return u

    def is_over(self) -> bool:
        if not self.player or not self.enemy:
            return True
        return (not self.player.alive()) or (not self.enemy.alive())

    def winner(self) -> str | None:
        if not self.player or not self.enemy:
            return None
        if self.player.alive() and not self.enemy.alive():
            return "player"
        if self.enemy.alive() and not self.player.alive():
            return "enemy"
        return None

    def upcoming_turns(self, count: int = 6) -> list[str]:
        """Returns list of upcoming actor ids, CTB-style."""
        if not self.player or not self.enemy:
            return []
        sim = {
            "player": float(self.player.next_at),
            "enemy": float(self.enemy.next_at),
        }
        speeds = {
            "player": max(1, int(self.player.stats.speed)),
            "enemy": max(1, int(self.enemy.stats.speed)),
        }

        out: list[str] = []
        for _ in range(max(0, int(count))):
            actor_id = "player" if sim["player"] <= sim["enemy"] else "enemy"
            out.append(actor_id)
            sim[actor_id] += 100.0 / speeds[actor_id]
        return out

    def _next_actor_id(self) -> str:
        if not self.player or not self.enemy:
            return "player"
        return "player" if self.player.next_at <= self.enemy.next_at else "enemy"

    def _advance_clock(self, actor_id: str) -> None:
        u = self.get(actor_id)
        u.next_at += 100.0 / max(1, int(u.stats.speed))

    def _tick_statuses_start_turn(self, u: BattleUnit) -> list[CombatEvent]:
        events: list[CombatEvent] = []

        # Guard expires when your next turn starts (if it wasn't consumed).
        if u.has("guard"):
            # We keep it for the enemy's turn; drop when owner begins their turn.
            u.remove("guard")

        # Damage over time.
        for eff in list(u.statuses.values()):
            dot = status_damage_over_time(eff)
            if dot > 0 and u.alive():
                dealt = u.stats.take_damage(dot)
                events.append(
                    CombatEvent(
                        kind="damage",
                        actor=None,
                        target=u.id,
                        amount=dealt,
                        text=f"{u.stats.name} suffers {dealt} from {eff.name}.",
                        tag=eff.id,
                    )
                )

        # Tick durations.
        for key, eff in list(u.statuses.items()):
            if getattr(eff, "id", "") == "charge":
                # Charge is consumed by the next action, not duration-based.
                continue
            eff.tick()
            if not eff.alive():
                del u.statuses[key]
                events.append(
                    CombatEvent(
                        kind="status",
                        actor=None,
                        target=u.id,
                        text=f"{u.stats.name}'s {eff.name} fades.",
                    )
                )

        return events

    def _try_skip_turn(self, u: BattleUnit) -> bool:
        for eff in u.statuses.values():
            chance = status_skip_turn_chance(eff)
            if chance > 0.0 and self._rng.random() < chance:
                return True
        return False

    def _damage(self, attacker: BattleUnit, defender: BattleUnit, *, mult: float, acc_mult: float = 1.0) -> list[CombatEvent]:
        events: list[CombatEvent] = []

        if not attacker.alive() or not defender.alive():
            return events

        hit_roll = self._rng.random()
        accuracy = max(0.05, min(1.0, attacker.stats.accuracy * acc_mult))
        if hit_roll > accuracy:
            events.append(
                CombatEvent(
                    kind="miss",
                    actor=attacker.id,
                    target=defender.id,
                    text=f"{attacker.stats.name} misses!",
                )
            )
            return events

        base = attacker.stats.attack + self._rng.randint(-2, 2)
        base = max(1, int(round(base - defender.stats.defense * 0.55)))

        # Element triangle
        elem_mult, elem_tag = element_multiplier(attacker.stats.element, defender.stats.element)

        # Attacker debuffs
        for eff in attacker.statuses.values():
            mult *= status_damage_multiplier(eff)

        # Defender buffs
        if defender.has("guard"):
            mult *= status_incoming_damage_multiplier(defender.statuses["guard"])
            defender.remove("guard")

        # Crit
        is_crit = self._rng.random() < max(0.0, min(1.0, attacker.stats.crit_chance))
        if is_crit:
            mult *= attacker.stats.crit_mult

        dmg = int(round(base * mult * elem_mult))
        dmg = max(1, dmg)
        dealt = defender.stats.take_damage(dmg)

        tag = ""
        if elem_tag:
            tag = elem_tag
        if is_crit:
            tag = (tag + " | " if tag else "") + "CRIT"

        events.append(
            CombatEvent(
                kind="damage",
                actor=attacker.id,
                target=defender.id,
                amount=dealt,
                text=f"{attacker.stats.name} hits {defender.stats.name} for {dealt}.",
                tag=tag,
            )
        )
        return events

    def _apply_skill_side_effects(self, attacker: BattleUnit, defender: BattleUnit, skill_id: str) -> list[CombatEvent]:
        events: list[CombatEvent] = []
        if not attacker.alive() or not defender.alive():
            return events

        elem = normalize_element(attacker.stats.element)
        if skill_id == "elemental":
            if elem == "Fire":
                defender.put(build_status("burn", turns=2, potency=4))
                events.append(
                    CombatEvent(
                        kind="status",
                        actor=attacker.id,
                        target=defender.id,
                        text=f"{defender.stats.name} is Burned!",
                        tag="burn",
                    )
                )
            elif elem == "Ice":
                defender.put(build_status("freeze", turns=2, potency=0))
                events.append(
                    CombatEvent(
                        kind="status",
                        actor=attacker.id,
                        target=defender.id,
                        text=f"{defender.stats.name} is Frozen!",
                        tag="freeze",
                    )
                )
            elif elem == "Wind":
                defender.put(build_status("weaken", turns=2, potency=0))
                events.append(
                    CombatEvent(
                        kind="status",
                        actor=attacker.id,
                        target=defender.id,
                        text=f"{defender.stats.name} is Weakened!",
                        tag="weaken",
                    )
                )
        return events

    def _use_item(self, user: BattleUnit, item_id: str) -> list[CombatEvent]:
        events: list[CombatEvent] = []
        if user.items.get(item_id, 0) <= 0:
            events.append(CombatEvent(kind="log", actor=user.id, text="No items left."))
            return events

        if item_id == "potion":
            user.items[item_id] -= 1
            healed = user.stats.heal(28)
            events.append(
                CombatEvent(
                    kind="heal",
                    actor=user.id,
                    target=user.id,
                    amount=healed,
                    text=f"{user.stats.name} drinks a Potion (+{healed}).",
                )
            )
            return events

        if item_id == "ether":
            user.items[item_id] -= 1
            before = user.stats.sp.current
            user.stats.sp.gain(20)
            gained = user.stats.sp.current - before
            events.append(
                CombatEvent(
                    kind="effect",
                    actor=user.id,
                    target=user.id,
                    amount=gained,
                    text=f"{user.stats.name} uses Ether (+{gained} SP).",
                )
            )
            return events

        events.append(CombatEvent(kind="log", actor=user.id, text="Nothing happens."))
        return events

    def player_action(self, action_id: str, payload: str | None = None) -> list[CombatEvent]:
        if not self.player or not self.enemy:
            return [CombatEvent(kind="log", text="Battle not started.")]
        if self.is_over():
            return []

        if self.active_id != "player":
            return [CombatEvent(kind="log", text="Not your turn.")]

        events: list[CombatEvent] = []
        events.extend(self._take_turn("player", action_id, payload))
        events.extend(self._auto_enemy_until_player())
        return events

    def _auto_enemy_until_player(self) -> list[CombatEvent]:
        events: list[CombatEvent] = []
        guard = 0
        while not self.is_over() and self.active_id == "enemy" and guard < 6:
            events.extend(self._take_turn("enemy", None, None))
            guard += 1
        return events

    def _enemy_choose(self) -> tuple[str, str | None]:
        enemy = self.get("enemy")
        if enemy.has("charge"):
            return "heavy_strike", None
        # Basic AI: heal sometimes, otherwise pressure.
        if enemy.stats.hp.ratio() <= 0.35 and self._rng.random() < 0.35:
            if enemy.items.get("potion", 0) > 0:
                return "item", "potion"
        roll = self._rng.random()
        if roll < 0.15:
            return "defend", None
        if roll < 0.35:
            return "heavy_charge", None
        if roll < 0.75 and enemy.stats.sp.current >= 10:
            return "skill", "elemental"
        return "attack", None

    def _take_turn(self, actor_id: str, action_id: str | None, payload: str | None) -> list[CombatEvent]:
        actor = self.get(actor_id)
        target = self.get("enemy" if actor_id == "player" else "player")
        if not actor.alive() or not target.alive():
            self.active_id = self._next_actor_id()
            return []

        self.turn_index += 1
        events: list[CombatEvent] = []
        events.append(
            CombatEvent(
                kind="turn",
                actor=actor.id,
                text=f"Turn {self.turn_index}: {actor.stats.name}",
            )
        )

        events.extend(self._tick_statuses_start_turn(actor))
        if self.is_over():
            self.active_id = self._next_actor_id()
            return events

        if self._try_skip_turn(actor):
            events.append(
                CombatEvent(
                    kind="log",
                    actor=actor.id,
                    text=f"{actor.stats.name} is frozen and loses the turn!",
                    tag="freeze",
                )
            )
            self._advance_clock(actor.id)
            self.active_id = self._next_actor_id()
            return events

        # Forced charge completion.
        if actor.has("charge"):
            action_id = "heavy_strike"
            payload = None

        if actor_id == "enemy" and action_id is None:
            action_id, payload = self._enemy_choose()

        # Resolve action.
        if action_id == "attack":
            events.extend(self._damage(actor, target, mult=1.0, acc_mult=1.0))
        elif action_id == "heavy_charge":
            actor.put(build_status("charge", turns=1, potency=0))
            events.append(
                CombatEvent(
                    kind="status",
                    actor=actor.id,
                    target=actor.id,
                    text=f"{actor.stats.name} begins charging a heavy attack!",
                    tag="charge",
                )
            )
        elif action_id == "heavy_strike":
            actor.remove("charge")
            events.extend(self._damage(actor, target, mult=1.65, acc_mult=0.85))
        elif action_id == "defend":
            actor.put(build_status("guard", turns=1, potency=0))
            events.append(
                CombatEvent(
                    kind="status",
                    actor=actor.id,
                    target=actor.id,
                    text=f"{actor.stats.name} raises a guard.",
                    tag="guard",
                )
            )
        elif action_id == "skill":
            skill_id = payload or "elemental"

            if skill_id == "focus":
                healed = actor.stats.heal(12)
                before = actor.stats.sp.current
                actor.stats.sp.gain(10)
                gained = actor.stats.sp.current - before
                events.append(
                    CombatEvent(
                        kind="heal",
                        actor=actor.id,
                        target=actor.id,
                        amount=healed,
                        text=f"{actor.stats.name} focuses (+{healed} HP).",
                        tag="skill",
                    )
                )
                if gained > 0:
                    events.append(
                        CombatEvent(
                            kind="effect",
                            actor=actor.id,
                            target=actor.id,
                            amount=gained,
                            text=f"{actor.stats.name} recovers +{gained} SP.",
                            tag="skill",
                        )
                    )

            elif skill_id == "burst":
                if not actor.stats.sp.spend(20):
                    events.append(
                        CombatEvent(
                            kind="log",
                            actor=actor.id,
                            text=f"{actor.stats.name} lacks SP.",
                        )
                    )
                else:
                    events.append(
                        CombatEvent(
                            kind="effect",
                            actor=actor.id,
                            text=f"{actor.stats.name} unleashes a Burst!",
                            tag="skill",
                        )
                    )
                    events.extend(self._damage(actor, target, mult=1.55, acc_mult=0.90))
                    events.extend(self._apply_skill_side_effects(actor, target, "elemental"))

            else:  # elemental
                if not actor.stats.sp.spend(10):
                    events.append(
                        CombatEvent(
                            kind="log",
                            actor=actor.id,
                            text=f"{actor.stats.name} lacks SP.",
                        )
                    )
                else:
                    events.append(
                        CombatEvent(
                            kind="effect",
                            actor=actor.id,
                            text=f"{actor.stats.name} casts a skill!",
                            tag="skill",
                        )
                    )
                    events.extend(self._damage(actor, target, mult=1.2, acc_mult=0.95))
                    events.extend(self._apply_skill_side_effects(actor, target, skill_id))
        elif action_id == "item":
            item_id = payload or "potion"
            events.extend(self._use_item(actor, item_id))
        else:
            events.append(CombatEvent(kind="log", actor=actor.id, text="..."))

        # Advance CTB and decide next actor.
        self._advance_clock(actor.id)
        self.active_id = self._next_actor_id()

        # End-of-battle marker.
        if self.is_over():
            win = self.winner()
            if win == "player":
                events.append(CombatEvent(kind="log", text="Victory!"))
            elif win == "enemy":
                events.append(CombatEvent(kind="log", text="Defeat..."))

        return events

