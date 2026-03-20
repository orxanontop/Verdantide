from __future__ import annotations

"""game_modes.py

Game mode manager that handles switching between open world exploration
and turn-based battle modes.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Callable

from openworld import OpenWorldUI, GameMap, load_map_from_lua
from battle_ui import BattleUI, make_default_player, make_enemy_from_template
from character_system import Combatant, Resource


class GameModeManager(ttk.Frame):
    """
    Manages switching between open world exploration and turn-based battle.
    
    Usage:
        manager = GameModeManager(root)
        manager.pack(fill="both", expand=True)
        
        # Game starts in open world mode
        # When enemy encounter triggers, switches to battle
        # After battle, returns to open world
    """
    
    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        
        self._current_mode: str = "openworld"
        self._openworld: OpenWorldUI | None = None
        self._battle_ui: BattleUI | None = None
        self._player_data: dict | None = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the base UI container."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self._openworld = OpenWorldUI(self, on_battle_trigger=self._trigger_battle)
        self._openworld.grid(row=0, column=0, sticky="nsew")
        
        self._load_openworld_map()
    
    def _load_openworld_map(self) -> None:
        """Load the map for open world exploration."""
        base_dir = Path(__file__).parent
        
        lua_map_path = base_dir / "maps" / "justamap2.lua"
        
        if lua_map_path.exists():
            game_map = load_map_from_lua(lua_map_path)
            if game_map:
                tileset_path = str(base_dir / "maps" / "tileset.png")
                self._openworld.load_map(game_map, tileset_path)
                self._openworld.spawn_player(400, 400)
                return
        
        fallback_map = GameMap(
            width=20,
            height=15,
            tilewidth=64,
            tileheight=64,
        )
        
        import random
        layer_data = []
        for i in range(20 * 15):
            if random.random() < 0.15:
                layer_data.append(random.choice([33, 34, 42, 43, 51, 52]))
            else:
                layer_data.append(0)
        fallback_map.layers["Tile Layer 1"] = layer_data
        
        for y in [0, 14]:
            for x in range(20):
                idx = y * 20 + x
                if idx < len(layer_data):
                    layer_data[idx] = 11
        fallback_map.layers["Tile Layer 1"] = layer_data
        
        fallback_map.walls = [
            openworld.WallCollider(128, 256, 128, 128),
            openworld.WallCollider(640, 256, 128, 128),
            openworld.WallCollider(0, 768, 640, 64),
        ]
        
        self._openworld.load_map(fallback_map)
        self._openworld.spawn_player(400, 400)
    
    def _trigger_battle(self) -> None:
        """Switch from open world to battle mode."""
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
        
        if enemies_data:
            enemy_tpl = random.choice(enemies_data)
        else:
            enemy_tpl = {"name": "Bandit", "element": "Wind", "hp": 90}
        
        if self._player_data:
            player = make_default_player(self._player_data.get("name", "Hero"), self._player_data.get("element", "Fire"))
        else:
            player = make_default_player("Hero", "Fire")
        
        self._battle_ui.start_battle(player, make_enemy_from_template(enemy_tpl))
        
        self._current_mode = "battle"
    
    def return_to_openworld(self) -> None:
        """Return to open world after battle ends."""
        if self._battle_ui:
            self._battle_ui.pack_forget()
            self._battle_ui = None
        
        if self._openworld:
            self._openworld.grid(row=0, column=0, sticky="nsew")
            self._openworld._start_movement_loop()
        
        self._current_mode = "openworld"
    
    def get_player_stats(self) -> dict:
        """Get player stats for persistence across modes."""
        if self._battle_ui:
            try:
                player = self._battle_ui.engine.get("player")
                return {
                    "name": player.name,
                    "element": player.element,
                    "hp": player.hp.current,
                    "max_hp": player.hp.maximum,
                    "sp": player.sp.current,
                    "max_sp": player.sp.maximum,
                }
            except Exception:
                pass
        return {"name": "Hero", "element": "Fire", "hp": 100, "max_hp": 100, "sp": 50, "max_sp": 50}
    
    @property
    def current_mode(self) -> str:
        """Get the current game mode."""
        return self._current_mode


import openworld


class ModeSwitcher:
    """Utility class for switching between game modes programmatically."""
    
    @staticmethod
    def show_openworld(container: ttk.Frame) -> None:
        """Show open world mode."""
        for child in container.winfo_children():
            child.grid_forget()
        if hasattr(container, '_openworld'):
            container._openworld.grid(row=0, column=0, sticky="nsew")
    
    @staticmethod
    def show_battle(container: ttk.Frame) -> None:
        """Show battle mode."""
        for child in container.winfo_children():
            child.grid_forget()
        if hasattr(container, '_battle_ui'):
            container._battle_ui.grid(row=0, column=0, sticky="nsew")
