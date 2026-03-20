from __future__ import annotations

"""
game_modes_pygame.py

Integration layer between Pygame open world and Tkinter battle system.
Handles seamless transitions, player state persistence, and encounter triggering.
"""

import random
import json
from pathlib import Path
from typing import Callable, Protocol

import pygame


class BattleController(Protocol):
    """Protocol for battle system integration."""
    def start_battle(self, player, enemy) -> None: ...
    def is_battle_over(self) -> bool: ...
    def get_winner(self) -> str | None: ...
    def get_player(self): ...


class GameStateManager:
    """Manages game state across open world and battle modes."""
    
    def __init__(self):
        self.player_name: str = "Hero"
        self.player_element: str = "Fire"
        self.player_hp: int = 100
        self.player_max_hp: int = 100
        self.player_sp: int = 50
        self.player_max_sp: int = 50
        self.world_position: tuple[float, float] = (960, 960)
    
    def save_from_battle(self, player) -> None:
        """Save player state from battle end."""
        self.player_hp = player.hp.current
        self.player_max_hp = player.hp.maximum
        self.player_sp = player.sp.current
        self.player_max_sp = player.sp.maximum
    
    def to_dict(self) -> dict:
        return {
            "name": self.player_name,
            "element": self.player_element,
            "hp": self.player_hp,
            "max_hp": self.player_max_hp,
            "sp": self.player_sp,
            "max_sp": self.player_max_sp,
            "position": self.world_position,
        }


class OpenWorldBattleGame:
    """
    Main game controller that manages open world ↔ battle transitions.
    Uses Pygame for open world and Tkinter for battle.
    """
    
    def __init__(
        self,
        screen_width: int = 960,
        screen_height: int = 640,
        map_file: str = "justamap3.lua",
        biome_name: str = "Forest"
    ):
        pygame.init()
        pygame.display.set_caption("Manga RPG")
        
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.clock = pygame.time.Clock()
        
        self.state = GameStateManager()
        
        self.current_mode: str = "openworld"
        self.running: bool = True
        
        self.base_path = Path(__file__).parent
        
        self._openworld = None
        self._battle_root = None
        self._battle_app = None
        
        self._initialize_openworld(screen_width, screen_height, map_file, biome_name)
    
    def _initialize_openworld(
        self,
        screen_width: int,
        screen_height: int,
        map_file: str,
        biome_name: str
    ) -> None:
        """Initialize the open world component."""
        from openworld_pygame import OpenWorldPygame
        
        self._openworld = OpenWorldPygame(
            screen_width=screen_width,
            screen_height=screen_height,
            map_file=map_file,
            biome_name=biome_name
        )
        
        self._openworld.set_encounter_callback(self._on_encounter)
        self._openworld.set_interact_callback(self._on_interact)
        
        if self.state.world_position != (0, 0):
            self._openworld.player.x = self.state.world_position[0]
            self._openworld.player.y = self.state.world_position[1]
    
    def _on_encounter(self, x: float, y: float) -> None:
        """Handle random encounter trigger."""
        self.state.world_position = (x, y)
        self._start_battle()
    
    def _on_interact(self, obj) -> None:
        """Handle player interaction with objects."""
        print(f"Interacted with {obj.name}")
    
    def _start_battle(self) -> None:
        """Switch to battle mode."""
        self.current_mode = "battle"
        self.running = False
        
        pygame.quit()
        
        import tkinter as tk
        from battle_ui import BattleUI, make_default_player, make_enemy_from_template
        
        self._battle_root = tk.Tk()
        self._battle_root.title("Battle!")
        
        enemies_data = []
        try:
            with open("jsons/enemies.json", "r", encoding="utf-8") as f:
                enemies_data = json.load(f)
        except:
            pass
        
        enemy_tpl = random.choice(enemies_data) if enemies_data else {"name": "Bandit", "element": "Wind", "hp": 90}
        
        player = make_default_player(self.state.player_name, self.state.player_element)
        player.hp.current = min(self.state.player_hp, player.hp.maximum)
        player.hp.maximum = self.state.player_max_hp
        player.sp.current = min(self.state.player_sp, player.sp.maximum)
        player.sp.maximum = self.state.player_max_sp
        
        self._battle_ui = BattleUI(self._battle_root)
        self._battle_ui.pack(fill="both", expand=True)
        
        original_restart = self._battle_ui._restart_battle
        
        def on_battle_end():
            original_restart()
            self._return_to_openworld()
        
        self._battle_ui._restart_battle = on_battle_end
        
        self._battle_ui.start_battle(player, make_enemy_from_template(enemy_tpl))
        
        self._battle_root.mainloop()
    
    def _return_to_openworld(self) -> None:
        """Return to open world after battle."""
        try:
            player = self._battle_ui.engine.get("player")
            self.state.save_from_battle(player)
        except:
            pass
        
        self._battle_root.destroy()
        self._battle_root = None
        self._battle_ui = None
        
        self.__init__(
            screen_width=960,
            screen_height=640,
            map_file="justamap3.lua",
            biome_name="Forest"
        )
        self.state.world_position = self.state.world_position
        
        self.current_mode = "openworld"
        self.running = True
        
        if hasattr(self, '_openworld') and self._openworld:
            self._openworld.player.x = self.state.world_position[0]
            self._openworld.player.y = self.state.world_position[1]
    
    def start(self) -> None:
        """Start the game loop."""
        if self._openworld:
            self._openworld.start()


def run_game(
    map_file: str = "justamap3.lua",
    biome_name: str = "Forest"
) -> None:
    """Run the game with specified map and biome."""
    game = OpenWorldBattleGame(
        screen_width=960,
        screen_height=640,
        map_file=map_file,
        biome_name=biome_name
    )
    game.start()


if __name__ == "__main__":
    run_game()
