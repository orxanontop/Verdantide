from __future__ import annotations

"""openworld.py

Open world exploration system using Tkinter Canvas.
- Tile-based map rendering
- Player movement with collision detection
- Camera following player
- Random encounter triggers
- Seamless integration with battle UI
"""

import math
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class TileLayer:
    width: int
    height: int
    data: list[int]


@dataclass
class WallCollider:
    x: float
    y: float
    width: float
    height: float


@dataclass
class MapObject:
    name: str
    x: float
    y: float
    width: float
    height: float
    object_type: str = ""
    properties: dict = field(default_factory=dict)


@dataclass
class GameMap:
    width: int
    height: int
    tilewidth: int
    tileheight: int
    tilesets: list[dict] = field(default_factory=dict)
    layers: dict[str, TileLayer] = field(default_factory=dict)
    walls: list[WallCollider] = field(default_factory=list)
    objects: list[MapObject] = field(default_factory=list)
    
    def tile_to_pixel(self, tile_x: int, tile_y: int) -> tuple[float, float]:
        return float(tile_x * self.tilewidth), float(tile_y * self.tileheight)
    
    def pixel_to_tile(self, px: float, py: float) -> tuple[int, int]:
        return int(px / self.tilewidth), int(py / self.tileheight)
    
    def get_tile(self, layer_name: str, tile_x: int, tile_y: int) -> int | None:
        layer = self.layers.get(layer_name)
        if not layer:
            return None
        idx = tile_y * layer.width + tile_x
        if 0 <= idx < len(layer.data):
            return layer.data[idx]
        return None
    
    def is_walkable(self, px: float, py: float) -> bool:
        tx, ty = self.pixel_to_tile(px, py)
        for wall in self.walls:
            if (wall.x <= px < wall.x + wall.width and
                wall.y <= py < wall.y + wall.height):
                return False
        return True


class SpriteSheet:
    """Simple sprite sheet handler for player animation."""
    
    def __init__(self, image_path: str, frame_width: int, frame_height: int):
        self.image_path = image_path
        self.frame_width = frame_width
        self.frame_height = frame_height
        self._frames: dict[str, list[tk.PhotoImage]] = {}
        self._current_anim: str = "down"
        self._frame_index: int = 0
        self._load_spritesheet()
    
    def _load_spritesheet(self) -> None:
        try:
            self._base_image = tk.PhotoImage(file=self.image_path)
        except Exception:
            self._base_image = None
            return
        
        cols = self._base_image.width() // self.frame_width
        rows = self._base_image.height() // self.frame_height
        
        directions = ["down", "left", "right", "up"]
        for row, direction in enumerate(directions):
            if row >= rows:
                break
            frames = []
            for col in range(min(4, cols)):
                x = col * self.frame_width
                y = row * self.frame_height
                frame = self._base_image.subsample(
                    self._base_image, x, y,
                    self.frame_width, self.frame_height
                )
                frames.append(frame)
            self._frames[direction] = frames
    
    def get_frame(self, direction: str = "down", index: int = 0) -> tk.PhotoImage | None:
        frames = self._frames.get(direction, [])
        if not frames:
            return self._frames.get("down", [None] * len(self._frames.get("down", [])))[0] if self._frames.get("down") else None
        return frames[min(index, len(frames) - 1)]
    
    def draw(self, canvas: tk.Canvas, x: float, y: float, direction: str = "down", frame: int = 0) -> int:
        """Draw the sprite on canvas. Returns canvas item id."""
        photo = self.get_frame(direction, frame)
        if photo:
            return canvas.create_image(x, y, image=photo, anchor="center")
        return 0


@dataclass
class Player:
    x: float
    y: float
    speed: float = 5.0
    width: float = 32
    height: float = 32
    direction: str = "down"
    frame: int = 0
    is_moving: bool = False
    
    def get_bounds(self) -> tuple[float, float, float, float]:
        hw = self.width / 2
        hh = self.height / 2
        return (self.x - hw, self.y - hh, self.x + hw, self.y + hh)
    
    def collides_with(self, other: WallCollider) -> bool:
        bx1, by1, bx2, by2 = self.get_bounds()
        return not (bx2 < other.x or bx1 > other.x + other.width or
                   by2 < other.y or by1 > other.y + other.height)


class Camera:
    """Simple camera that follows the player."""
    
    def __init__(self, width: int, height: int):
        self.x: float = 0.0
        self.y: float = 0.0
        self.width = width
        self.height = height
        self.smoothing: float = 0.1
    
    def follow(self, target_x: float, target_y: float, map_width: int, map_height: int) -> None:
        target_cam_x = target_x - self.width / 2
        target_cam_y = target_y - self.height / 2
        
        self.x += (target_cam_x - self.x) * self.smoothing
        self.y += (target_cam_y - self.y) * self.smoothing
        
        self.x = max(0, min(self.x, float(map_width - self.width)))
        self.y = max(0, min(self.y, float(map_height - self.height)))
    
    def world_to_screen(self, world_x: float, world_y: float) -> tuple[int, int]:
        return (int(world_x - self.x), int(world_y - self.y))


class OpenWorldUI(ttk.Frame):
    """Open world exploration interface."""
    
    def __init__(self, parent: tk.Widget, *, on_battle_trigger: Callable | None = None):
        super().__init__(parent)
        
        self._on_battle_trigger = on_battle_trigger
        
        self._canvas_width = 900
        self._canvas_height = 600
        self._tile_size = 32
        
        self._world = tk.Canvas(
            self,
            width=self._canvas_width,
            height=self._canvas_height,
            bg="#1a1a2e",
            highlightthickness=0,
        )
        self._world.pack(fill="both", expand=True)
        
        self._camera = Camera(self._canvas_width, self._canvas_height)
        self._game_map: GameMap | None = None
        self._player: Player | None = None
        self._walls: list = []
        self._tile_images: dict[int, tk.PhotoImage] = {}
        self._player_sprite_id: int | None = None
        self._encounter_timer: int = 0
        self._encounter_threshold: int = 300
        self._moving: bool = False
        
        self._keys_pressed: set[str] = set()
        self._animation_job: str | None = None
        self._move_job: str | None = None
        self._anim_frame: int = 0
        self._anim_timer: int = 0
        
        self._setup_controls()
    
    def _setup_controls(self) -> None:
        self._world.bind("<KeyPress>", self._on_key_press)
        self._world.bind("<KeyRelease>", self._on_key_release)
        self._world.focus_set()
    
    def _on_key_press(self, event: tk.Event) -> None:
        self._keys_pressed.add(event.keysym)
        self._moving = True
    
    def _on_key_release(self, event: tk.Event) -> None:
        self._keys_pressed.discard(event.keysym)
        if not self._keys_pressed:
            self._moving = False
    
    def load_map(self, map_data: GameMap, tileset_image: str | None = None) -> None:
        """Load a map into the world."""
        self._game_map = map_data
        self._camera.x = 0
        self._camera.y = 0
        
        self._walls = []
        for wall in map_data.walls:
            self._walls.append(wall)
        
        if tileset_image:
            self._load_tileset(tileset_image, map_data.tilewidth, map_data.tileheight)
        
        self._render_map()
    
    def _load_tileset(self, image_path: str, tile_w: int, tile_h: int) -> None:
        """Load tileset image and split into individual tiles."""
        try:
            base = tk.PhotoImage(file=image_path)
            cols = base.width() // tile_w
            tile_id = 0
            for y in range(0, base.height(), tile_h):
                for x in range(0, base.width(), tile_w):
                    tile = base.subsample(base, x, y, tile_w, tile_h)
                    self._tile_images[tile_id + 1] = tile
                    tile_id += 1
        except Exception as e:
            print(f"Could not load tileset: {e}")
    
    def _render_map(self) -> None:
        """Render the current map state."""
        self._world.delete("all")
        self._walls.clear()
        
        if not self._game_map:
            return
        
        map_w = self._game_map.width * self._game_map.tilewidth
        map_h = self._game_map.height * self._game_map.tileheight
        
        cam_x, cam_y = int(self._camera.x), int(self._camera.y)
        
        start_tx = max(0, cam_x // self._game_map.tilewidth - 1)
        end_tx = min(self._game_map.width, (cam_x + self._canvas_width) // self._game_map.tilewidth + 2)
        start_ty = max(0, cam_y // self._game_map.tileheight - 1)
        end_ty = min(self._game_map.height, (cam_y + self._canvas_height) // self._game_map.tileheight + 2)
        
        for layer_name in ["Tile Layer 1", "Tile Layer 2", "Tile Layer 3"]:
            layer = self._game_map.layers.get(layer_name)
            if not layer:
                continue
            
            for ty in range(start_ty, end_ty):
                for tx in range(start_tx, end_tx):
                    tile_id = self._game_map.get_tile(layer_name, tx, ty)
                    if tile_id and tile_id > 0:
                        px = tx * self._game_map.tilewidth - cam_x
                        py = ty * self._game_map.tileheight - cam_y
                        
                        if tile_id in self._tile_images:
                            self._world.create_image(px, py, image=self._tile_images[tile_id], anchor="nw")
                        else:
                            color = self._get_tile_color(tile_id)
                            self._world.create_rectangle(
                                px, py,
                                px + self._game_map.tilewidth,
                                py + self._game_map.tileheight,
                                fill=color, outline=""
                            )
        
        for wall in self._game_map.walls:
            wx = wall.x - cam_x
            wy = wall.y - cam_y
            self._world.create_rectangle(
                wx, wy,
                wx + wall.width,
                wy + wall.height,
                fill="#333344", outline="#444455", width=2
            )
    
    def _get_tile_color(self, tile_id: int) -> str:
        """Get a color for a tile based on its ID (for testing without tileset)."""
        colors = [
            "#4a6741", "#3d5a35", "#5a7a4a",
            "#3a4a5a", "#2a3a4a", "#4a5a6a",
            "#6a5a4a", "#5a4a3a", "#7a6a5a",
        ]
        return colors[tile_id % len(colors)]
    
    def spawn_player(self, x: float, y: float) -> None:
        """Spawn the player at the given position."""
        self._player = Player(x=x, y=y)
        self._encounter_timer = 0
        self._start_movement_loop()
    
    def _start_movement_loop(self) -> None:
        """Start the continuous movement update loop."""
        if self._move_job:
            self.after_cancel(self._move_job)
        
        def update():
            if not self._player:
                return
            
            dx, dy = 0, 0
            
            if "Right" in self._keys_pressed or "d" in self._keys_pressed or "D" in self._keys_pressed:
                dx = self._player.speed
                self._player.direction = "right"
            elif "Left" in self._keys_pressed or "a" in self._keys_pressed or "A" in self._keys_pressed:
                dx = -self._player.speed
                self._player.direction = "left"
            
            if "Down" in self._keys_pressed or "s" in self._keys_pressed or "S" in self._keys_pressed:
                dy = self._player.speed
                self._player.direction = "down"
            elif "Up" in self._keys_pressed or "w" in self._keys_pressed or "W" in self._keys_pressed:
                dy = -self._player.speed
                self._player.direction = "up"
            
            self._player.is_moving = dx != 0 or dy != 0
            
            if self._player.is_moving and self._game_map:
                new_x = self._player.x + dx
                new_y = self._player.y + dy
                
                can_move_x = True
                can_move_y = True
                
                for wall in self._game_map.walls:
                    test_player_x = Player(new_x, self._player.y)
                    test_player_y = Player(self._player.x, new_y)
                    
                    if test_player_x.collides_with(wall):
                        can_move_x = False
                    if test_player_y.collides_with(wall):
                        can_move_y = False
                
                if can_move_x:
                    self._player.x = new_x
                if can_move_y:
                    self._player.y = new_y
                
                self._player.x = max(16, min(self._player.x, float(self._game_map.width * self._game_map.tilewidth - 16)))
                self._player.y = max(16, min(self._player.y, float(self._game_map.height * self._game_map.tileheight - 16)))
                
                if self._moving:
                    self._encounter_timer += 1
                    if self._encounter_timer >= self._encounter_threshold:
                        self._encounter_timer = 0
                        self._try_trigger_encounter()
            
            self._update_camera()
            self._draw_frame()
            
            self._move_job = self.after(16, update)
        
        update()
    
    def _update_camera(self) -> None:
        """Update camera position."""
        if not self._player or not self._game_map:
            return
        
        map_w = self._game_map.width * self._game_map.tilewidth
        map_h = self._game_map.height * self._game_map.tileheight
        self._camera.follow(self._player.x, self._player.y, map_w, map_h)
    
    def _draw_frame(self) -> None:
        """Draw a single frame."""
        self._render_map()
        
        if not self._player:
            return
        
        sx, sy = self._camera.world_to_screen(self._player.x, self._player.y)
        
        if self._player.is_moving:
            self._anim_timer += 1
            if self._anim_timer >= 10:
                self._anim_timer = 0
                self._anim_frame = (self._anim_frame + 1) % 4
        else:
            self._anim_frame = 0
        
        self._world.create_oval(
            sx - 12, sy - 24,
            sx + 12, sy + 8,
            fill="#4ecdc4", outline="#1a1a2e", width=2
        )
        self._world.create_rectangle(
            sx - 10, sy - 8,
            sx + 10, sy + 24,
            fill="#2ecc71", outline="#1a1a2e", width=2
        )
        
        dir_symbols = {"up": "▲", "down": "▼", "left": "◀", "right": "▶"}
        self._world.create_text(sx, sy + 8, text=dir_symbols.get(self._player.direction, "▼"), 
                                fill="#fff", font=("Segoe UI", 10, "bold"))
    
    def _try_trigger_encounter(self) -> None:
        """Try to trigger a random battle encounter."""
        import random
        if random.random() < 0.3:
            if self._on_battle_trigger:
                self._on_battle_trigger()
    
    def get_player_position(self) -> tuple[float, float]:
        """Get current player position."""
        if self._player:
            return (self._player.x, self._player.y)
        return (0, 0)
    
    def stop(self) -> None:
        """Stop the movement loop."""
        if self._move_job:
            self.after_cancel(self._move_job)
            self._move_job = None


def load_map_from_lua(lua_path: Path) -> GameMap | None:
    """Load a map from a Lua export file."""
    try:
        with open(lua_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        import re
        
        width_match = re.search(r'width\s*=\s*(\d+)', content)
        height_match = re.search(r'height\s*=\s*(\d+)', content)
        tilewidth_match = re.search(r'tilewidth\s*=\s*(\d+)', content)
        tileheight_match = re.search(r'tileheight\s*=\s*(\d+)', content)
        
        if not all([width_match, height_match, tilewidth_match, tileheight_match]):
            return None
        
        width = int(width_match.group(1))
        height = int(height_match.group(1))
        tilewidth = int(tilewidth_match.group(1))
        tileheight = int(tileheight_match.group(1))
        
        map_obj = GameMap(
            width=width,
            height=height,
            tilewidth=tilewidth,
            tileheight=tileheight,
        )
        
        for layer_num in [1, 2, 3]:
            pattern = rf'name\s*=\s*["\']Tile Layer {layer_num}["\'].*?data\s*=\s*\{{(.*?)\}}'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                data_str = match.group(1)
                data = [int(x.strip()) for x in data_str.split(',') if x.strip().isdigit()]
                map_obj.layers[f"Tile Layer {layer_num}"] = TileLayer(width, height, data)
        
        obj_pattern = r'name\s*=\s*["\']Object Layer 1["\'].*?objects\s*=\s*\{(.*?)\}'
        obj_match = re.search(obj_pattern, content, re.DOTALL)
        if obj_match:
            obj_data = obj_match.group(1)
            rect_matches = re.findall(r'x\s*=\s*(\d+).*?y\s*=\s*(\d+).*?width\s*=\s*(\d+).*?height\s*=\s*(\d+)', obj_data, re.DOTALL)
            for x, y, w, h in rect_matches:
                if int(w) > 0 and int(h) > 0:
                    map_obj.walls.append(WallCollider(float(x), float(y), float(w), float(h)))
        
        obj_layer_pattern = r'name\s*=\s*["\']Walls["\'].*?objects\s*=\s*\{(.*?)\}'
        obj_layer_match = re.search(obj_layer_pattern, content, re.DOTALL)
        if obj_layer_match:
            obj_data = obj_layer_match.group(1)
            rect_matches = re.findall(r'x\s*=\s*(\d+).*?y\s*=\s*(\d+).*?width\s*=\s*(\d+).*?height\s*=\s*(\d+)', obj_data, re.DOTALL)
            for x, y, w, h in rect_matches:
                if int(w) > 0 and int(h) > 0:
                    map_obj.walls.append(WallCollider(float(x), float(y), float(w), float(h)))
        
        return map_obj
        
    except Exception as e:
        print(f"Error loading map: {e}")
        return None
