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
    
    def __init__(self, map_file: str = "maps/forest.lua", biome_name: str = "Forest"):
        self.player_name: str = "Hero"
        self.player_element: str = "Fire"
        self.player_hp: int = 100
        self.player_max_hp: int = 100
        self.player_sp: int = 50
        self.player_max_sp: int = 50
        self.world_position: tuple[float, float] = (960, 960)
        self.current_map: str = map_file
        self.current_biome: str = biome_name
    
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
        
        self.state = GameStateManager(map_file, biome_name)
        
        self.current_mode: str = "openworld"
        self.running: bool = True
        
        self.base_path = Path(__file__).parent
        
        self._openworld = None
        self._battle_root = None
        self._battle_app = None
        self._battle_ui = None
        
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
        self.current_mode = "battle"
        if self._openworld:
            self._openworld.stop()
    
    def _on_interact(self, obj) -> None:
        """Handle player interaction with objects."""
        print(f"Interacted with {obj.name}")
    
    def _start_battle(self) -> None:
        """Switch to battle mode."""
        self.current_mode = "battle"
        
        pygame.quit()
        
        import tkinter as tk
        from battle_ui import BattleUI, make_default_player, make_enemy_from_template
        
        self._battle_root = tk.Tk()
        self._battle_root.title("Battle!")
        self._battle_root.geometry("960x640")
        self._battle_root.minsize(960, 640)
        self._battle_root.bind("<Escape>", lambda e: self._battle_root.destroy())
        
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
        
        # Set callback to close window when player wins
        def on_victory():
            self._battle_root.destroy()
        
        self._battle_ui._on_battle_end_callback = on_victory
        
        self._battle_ui.start_battle(player, make_enemy_from_template(enemy_tpl))
        
        self._battle_root.mainloop()
        
        # After Tkinter window closes, return to openworld
        self._return_to_openworld()
    
    def _return_to_openworld(self) -> None:
        """Return to open world after battle."""
        try:
            if self._battle_ui and hasattr(self._battle_ui, 'engine'):
                player = self._battle_ui.engine.get("player")
                self.state.save_from_battle(player)
        except:
            pass
        
        if self._battle_root:
            try:
                self._battle_root.destroy()
            except:
                pass
        self._battle_root = None
        self._battle_ui = None
        
        # Reinitialize pygame and openworld
        pygame.init()
        pygame.display.set_caption("Verdantide")
        self.screen = pygame.display.set_mode((960, 640))
        
        # Get current map and biome from state
        map_file = getattr(self.state, 'current_map', 'maps/forest.lua')
        biome = getattr(self.state, 'current_biome', 'Forest')
        
        # Store position before reinitializing
        saved_x = self.state.world_position[0]
        saved_y = self.state.world_position[1]
        
        self._initialize_openworld(960, 640, map_file, biome)
        
        # Restore player position after initializing
        self._openworld.player.x = saved_x
        self._openworld.player.y = saved_y
        
        self.current_mode = "openworld"
        self.running = True
    
    def start(self) -> None:
        """Start the game loop."""
        while self.running:
            if not self._openworld:
                self._initialize_openworld(960, 640, self.state.current_map, self.state.current_biome)

            self.current_mode = "openworld"
            self._openworld.start()

            if self.current_mode == "battle":
                self._start_battle()
                continue

            # Openworld exited without a battle trigger (user quit).
            self.running = False


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
