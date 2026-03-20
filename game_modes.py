from __future__ import annotations

"""game_modes.py

Manages switching between open world exploration and turn-based battle modes.
Handles seamless transitions, player state persistence, and encounter triggering.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Callable

from openworld import OpenWorldUI, GameMap, load_map_from_lua, create_test_map, InteractableObject
from battle_ui import BattleUI, make_default_player, make_enemy_from_template


class GameModeManager(ttk.Frame):
    """Manages open world ↔ battle transitions with state persistence."""
    
    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        
        self._openworld: OpenWorldUI | None = None
        self._battle_ui: BattleUI | None = None
        
        self._player_name: str = "Hero"
        self._player_element: str = "Fire"
        self._player_hp: int = 100
        self._player_max_hp: int = 100
        self._player_sp: int = 50
        self._player_max_sp: int = 50
        
        self._current_mode: str = "openworld"
        self._last_world_pos: tuple[float, float] = (400, 400)
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Initialize the UI container."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self._openworld = OpenWorldUI(
            self,
            on_encounter=self._trigger_battle,
            on_interact=self._handle_interaction
        )
        self._openworld.grid(row=0, column=0, sticky="nsew")
        
        self._load_map()
    
    def _load_map(self) -> None:
        """Load the world map."""
        base_dir = Path(__file__).parent
        
        lua_map = base_dir / "maps" / "justamap2.lua"
        if lua_map.exists():
            game_map = load_map_from_lua(lua_map)
            if game_map:
                self._openworld.load_map(game_map)
                
                tileset_path = base_dir / "maps" / "tileset.png"
                if tileset_path.exists():
                    self._openworld.load_tileset(str(tileset_path))
                
                self._openworld.spawn_player(self._last_world_pos[0], self._last_world_pos[1])
                return
        
        self._openworld.load_map(create_test_map())
        self._openworld.spawn_player(400, 400)
    
    def _trigger_battle(self, player_x: float, player_y: float) -> None:
        """Transition from open world to battle mode."""
        self._last_world_pos = (player_x, player_y)
        
        self._openworld.stop()
        self._openworld.grid_forget()
        
        self._battle_ui = BattleUI(self)
        self._battle_ui.grid(row=0, column=0, sticky="nsew")
        
        import random
        try:
            import json
            with open("jsons/enemies.json", "r", encoding="utf-8") as f:
                enemies_data = json.load(f)
        except Exception:
            enemies_data = []
        
        enemy_tpl = random.choice(enemies_data) if enemies_data else {"name": "Bandit", "element": "Wind", "hp": 90}
        
        player = make_default_player(self._player_name, self._player_element)
        
        if self._player_hp < player.hp.maximum:
            player.hp.current = self._player_hp
            player.hp.maximum = self._player_max_hp
        if self._player_sp < player.sp.maximum:
            player.sp.current = self._player_sp
            player.sp.maximum = self._player_max_sp
        
        self._battle_ui.start_battle(player, make_enemy_from_template(enemy_tpl))
        
        self._battle_ui._restart_battle = self._on_battle_end
        
        self._current_mode = "battle"
    
    def _on_battle_end(self) -> None:
        """Handle battle ending - return to open world."""
        if not self._battle_ui:
            return
        
        try:
            player = self._battle_ui.engine.get("player")
            self._player_hp = player.hp.current
            self._player_max_hp = player.hp.maximum
            self._player_sp = player.sp.current
            self._player_max_sp = player.sp.maximum
        except Exception:
            pass
        
        self._battle_ui.pack_forget()
        self._battle_ui = None
        
        self._openworld.grid(row=0, column=0, sticky="nsew")
        self._openworld.set_player_position(self._last_world_pos[0], self._last_world_pos[1])
        self._openworld._start_loop()
        
        self._current_mode = "openworld"
    
    def _handle_interaction(self, obj: InteractableObject) -> None:
        """Handle player interacting with world objects."""
        if obj.interact_action == "talk":
            print(f"Talked to {obj.name}")
        elif obj.interact_action == "loot":
            print(f"Opened {obj.name}")
    
    def get_player_stats(self) -> dict:
        """Get player stats for saving/debugging."""
        return {
            "name": self._player_name,
            "element": self._player_element,
            "hp": self._player_hp,
            "max_hp": self._player_max_hp,
            "sp": self._player_sp,
            "max_sp": self._player_max_sp,
            "position": self._last_world_pos,
        }
    
    @property
    def current_mode(self) -> str:
        return self._current_mode
