from __future__ import annotations

"""openworld.py

Open world exploration system - Tkinter Canvas based.
Handles: tile rendering, player movement, camera, collision, encounters.
"""

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
class TriggerZone:
    x: float
    y: float
    width: float
    height: float
    trigger_type: str = "encounter"
    data: dict = field(default_factory=dict)


@dataclass
class InteractableObject:
    id: str
    name: str
    x: float
    y: float
    sprite_color: str = "#888888"
    interaction_radius: float = 32.0
    interact_action: str = "talk"


@dataclass
class GameMap:
    width: int
    height: int
    tilewidth: int
    tileheight: int
    tilesets: list[dict] = field(default_factory=dict)
    layers: dict[str, TileLayer] = field(default_factory=dict)
    walls: list[WallCollider] = field(default_factory=list)
    triggers: list[TriggerZone] = field(default_factory=list)
    objects: list[InteractableObject] = field(default_factory=list)
    
    def tile_to_pixel(self, tile_x: int, tile_y: int) -> tuple[float, float]:
        return float(tile_x * self.tilewidth), float(tile_y * self.tileheight)
    
    def pixel_to_tile(self, px: float, py: float) -> tuple[int, int]:
        return int(px / self.tilewidth), int(py / self.tileheight)
    
    def get_tile(self, layer_name: str, tile_x: int, tile_y: int) -> int | None:
        layer = self.layers.get(layer_name)
        if not layer or not isinstance(layer, TileLayer):
            return None
        idx = tile_y * layer.width + tile_x
        if 0 <= idx < len(layer.data):
            return layer.data[idx]
        return None


@dataclass
class Player:
    x: float
    y: float
    speed: float = 5.0
    width: float = 32.0
    height: float = 48.0
    direction: str = "down"
    frame: int = 0
    is_moving: bool = False
    in_combat: bool = False
    
    def get_collision_bounds(self) -> tuple[float, float, float, float]:
        hw = self.width / 2
        hh = self.height / 2
        return (self.x - hw, self.y - hh, self.x + hw, self.y + hh)
    
    def collides_with_rect(self, rx: float, ry: float, rw: float, rh: float) -> bool:
        bx1, by1, bx2, by2 = self.get_collision_bounds()
        return not (bx2 < rx or bx1 > rx + rw or by2 < ry or by1 > ry + rh)


class Camera:
    def __init__(self, width: int, height: int):
        self.x: float = 0.0
        self.y: float = 0.0
        self.width = width
        self.height = height
        self.smoothing: float = 0.15
    
    def follow(self, target_x: float, target_y: float, map_width: int, map_height: int) -> None:
        target_cam_x = target_x - self.width / 2
        target_cam_y = target_y - self.height / 2
        
        self.x += (target_cam_x - self.x) * self.smoothing
        self.y += (target_cam_y - self.y) * self.smoothing
        
        self.x = max(0, min(self.x, float(map_width - self.width)))
        self.y = max(0, min(self.y, float(map_height - self.height)))
    
    def world_to_screen(self, world_x: float, world_y: float) -> tuple[int, int]:
        return (int(world_x - self.x), int(world_y - self.y))


class TilesetManager:
    """Loads and manages tileset images."""
    
    def __init__(self):
        self.tiles: dict[int, tk.PhotoImage] = {}
        self.tile_size: int = 32
    
    def load_from_file(self, image_path: str, tile_w: int, tile_h: int) -> bool:
        try:
            base = tk.PhotoImage(file=image_path)
            self.tile_size = tile_w
            tile_id = 1
            
            tile_rows = base.height() // tile_h
            tile_cols = base.width() // tile_w
            
            for row in range(tile_rows):
                for col in range(tile_cols):
                    x = col * tile_w
                    y = row * tile_h
                    tile = self._crop_tile(base, x, y, tile_w, tile_h)
                    self.tiles[tile_id] = tile
                    tile_id += 1
            return True
        except Exception as e:
            print(f"Tileset load failed: {e}")
            return False
    
    def _crop_tile(self, source: tk.PhotoImage, x: int, y: int, w: int, h: int) -> tk.PhotoImage:
        temp = tk.Canvas()
        temp_image = tk.PhotoImage()
        temp_image.configure(width=w, height=h)
        
        try:
            temp_image.put("red", to=(0, 0, w, h))
        except:
            pass
        
        return temp_image
    
    def get_tile(self, tile_id: int) -> tk.PhotoImage | None:
        return self.tiles.get(tile_id)
    
    def get_tile_color(self, tile_id: int) -> str:
        colors = [
            "#4a6741", "#3d5a35", "#5a7a4a", "#4d6842",
            "#3a4a5a", "#2a3a4a", "#4a5a6a", "#3b4b5b",
            "#6a5a4a", "#5a4a3a", "#7a6a5a", "#5b4b3b",
            "#5a5a6a", "#4a4a5a", "#6a6a7a", "#4b4b5b",
        ]
        return colors[tile_id % len(colors)] if tile_id > 0 else "#1a1a2e"


class OpenWorldUI(ttk.Frame):
    """Main open world exploration interface."""
    
    def __init__(self, parent: tk.Widget, *, on_encounter: Callable | None = None, on_interact: Callable | None = None):
        super().__init__(parent)
        
        self._on_encounter = on_encounter
        self._on_interact = on_interact
        
        self._canvas_width = 900
        self._canvas_height = 600
        self._tile_size = 64
        
        self._canvas = tk.Canvas(
            self, width=self._canvas_width, height=self._canvas_height,
            bg="#1a1a2e", highlightthickness=0
        )
        self._canvas.pack(fill="both", expand=True)
        
        self._canvas.create_rectangle(0, 0, self._canvas_width, self._canvas_height, fill="#1a1a2e", outline="")
        
        self._camera = Camera(self._canvas_width, self._canvas_height)
        self._tileset = TilesetManager()
        self._game_map: GameMap | None = None
        self._player: Player | None = None
        self._player_sprite_id: int | None = None
        self._object_ids: list[int] = []
        
        self._keys: set[str] = set()
        self._move_job: str | None = None
        self._anim_frame: int = 0
        self._anim_timer: int = 0
        self._encounter_timer: int = 0
        self._encounter_steps: int = 200
        self._running: bool = False
        
        self._setup_controls()
    
    def _setup_controls(self) -> None:
        self.bind("<Configure>", self._on_resize)
        self._canvas.bind("<KeyPress>", self._on_key_press)
        self._canvas.bind("<KeyRelease>", self._on_key_release)
        self._canvas.bind("<space>", self._on_interact)
        self._canvas.bind("<Return>", self._on_interact)
        self._canvas.focus_set()
    
    def _on_resize(self, event) -> None:
        pass
    
    def _on_key_press(self, event: tk.Event) -> None:
        self._keys.add(event.keysym)
    
    def _on_key_release(self, event: tk.Event) -> None:
        self._keys.discard(event.keysym)
    
    def _on_interact(self, event: tk.Event) -> None:
        if not self._player or not self._game_map or not self._on_interact:
            return
        
        for obj in self._game_map.objects:
            dx = self._player.x - obj.x
            dy = self._player.y - obj.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < obj.interaction_radius + self._player.width:
                self._on_interact(obj)
                return
    
    def load_map(self, game_map: GameMap) -> None:
        """Load a map into the world."""
        self._game_map = game_map
        self._tile_size = game_map.tilewidth
        self._camera.x = 0
        self._camera.y = 0
    
    def load_tileset(self, image_path: str) -> bool:
        """Load a tileset image."""
        return self._tileset.load_from_file(image_path, self._tile_size, self._tile_size)
    
    def spawn_player(self, x: float, y: float) -> None:
        """Spawn player at position."""
        self._player = Player(x=x, y=y)
        self._encounter_timer = 0
        if not self._running:
            self._running = True
            self._start_loop()
    
    def _start_loop(self) -> None:
        """Main game loop."""
        if not self._running:
            return
        
        self._update()
        self._render()
        
        self._move_job = self.after(16, self._start_loop)
    
    def _update(self) -> None:
        """Update game state."""
        if not self._player or not self._game_map:
            return
        
        dx, dy = 0, 0
        
        if "Right" in self._keys or "d" in self._keys or "D" in self._keys:
            dx = self._player.speed
            self._player.direction = "right"
        elif "Left" in self._keys or "a" in self._keys or "A" in self._keys:
            dx = -self._player.speed
            self._player.direction = "left"
        
        if "Down" in self._keys or "s" in self._keys or "S" in self._keys:
            dy = self._player.speed
            self._player.direction = "down"
        elif "Up" in self._keys or "w" in self._keys or "W" in self._keys:
            dy = -self._player.speed
            self._player.direction = "up"
        
        self._player.is_moving = dx != 0 or dy != 0
        
        if self._player.is_moving:
            new_x = self._player.x + dx
            new_y = self._player.y + dy
            
            can_x = self._check_movement(new_x, self._player.y)
            can_y = self._check_movement(self._player.x, new_y)
            
            if can_x:
                self._player.x = new_x
            if can_y:
                self._player.y = new_y
            
            self._player.x = max(16, min(self._player.x, float(self._game_map.width * self._tile_size - 16)))
            self._player.y = max(16, min(self._player.y, float(self._game_map.height * self._tile_size - 16)))
            
            self._encounter_timer += 1
            if self._encounter_timer >= self._encounter_steps:
                self._encounter_timer = 0
                if self._on_encounter:
                    self._on_encounter(self._player.x, self._player.y)
            
            self._anim_timer += 1
            if self._anim_timer >= 8:
                self._anim_timer = 0
                self._anim_frame = (self._anim_frame + 1) % 4
        
        self._camera.follow(
            self._player.x, self._player.y,
            self._game_map.width * self._tile_size,
            self._game_map.height * self._tile_size
        )
    
    def _check_movement(self, new_x: float, new_y: float) -> bool:
        """Check if player can move to position."""
        if not self._game_map:
            return True
        
        for wall in self._game_map.walls:
            if self._player.collides_with_rect(wall.x, wall.y, wall.width, wall.height):
                return False
        
        if new_x < 16 or new_y < 16:
            return False
        
        return True
    
    def _render(self) -> None:
        """Render the world."""
        if not self._game_map:
            return
        
        self._canvas.delete("all")
        
        cam_x, cam_y = int(self._camera.x), int(self._camera.y)
        
        start_tx = max(0, cam_x // self._tile_size - 1)
        end_tx = min(self._game_map.width, (cam_x + self._canvas_width) // self._tile_size + 2)
        start_ty = max(0, cam_y // self._tile_size - 1)
        end_ty = min(self._game_map.height, (cam_y + self._canvas_height) // self._tile_size + 2)
        
        for layer_name in ["Tile Layer 1", "Tile Layer 2", "Tile Layer 3"]:
            for ty in range(start_ty, end_ty):
                for tx in range(start_tx, end_tx):
                    tile_id = self._game_map.get_tile(layer_name, tx, ty)
                    if tile_id and tile_id > 0:
                        px = tx * self._tile_size - cam_x
                        py = ty * self._tile_size - cam_y
                        
                        tile_img = self._tileset.get_tile(tile_id)
                        if tile_img:
                            self._canvas.create_image(px, py, image=tile_img, anchor="nw")
                        else:
                            color = self._tileset.get_tile_color(tile_id)
                            self._canvas.create_rectangle(
                                px, py, px + self._tile_size, py + self._tile_size,
                                fill=color, outline=""
                            )
        
        for wall in self._game_map.walls:
            wx = wall.x - cam_x
            wy = wall.y - cam_y
            self._canvas.create_rectangle(
                wx, wy, wx + wall.width, wy + wall.height,
                fill="#2a2a3e", outline="#3a3a4e", width=2
            )
        
        for obj in self._game_map.objects:
            ox, oy = self._camera.world_to_screen(obj.x, obj.y)
            self._canvas.create_oval(
                ox - 16, oy - 16, ox + 16, oy + 16,
                fill=obj.sprite_color, outline="#ffffff", width=2
            )
            self._canvas.create_text(ox, oy - 28, text=obj.name, fill="#ffffff",
                                    font=("Segoe UI", 10, "bold"))
        
        if self._player:
            px, py = self._camera.world_to_screen(self._player.x, self._player.y)
            
            bob_offset = 2 if self._player.is_moving and self._anim_frame % 2 == 0 else 0
            
            self._canvas.create_oval(
                px - 14, py - 28 + bob_offset,
                px + 14, py + 4 + bob_offset,
                fill="#4ecdc4", outline="#1a535c", width=2
            )
            
            self._canvas.create_rectangle(
                px - 12, py + 4 + bob_offset,
                px + 12, py + 28 + bob_offset,
                fill="#2ecc71", outline="#27ae60", width=2
            )
            
            dir_arrows = {"up": "▲", "down": "▼", "left": "◀", "right": "▶"}
            self._canvas.create_text(px, py + 16 + bob_offset,
                                    text=dir_arrows.get(self._player.direction, "▼"),
                                    fill="#ffffff", font=("Segoe UI", 8, "bold"))
        
        self._canvas.create_text(10, 20, text="WASD/Arrows: Move | Space/Enter: Interact",
                                fill="#888888", font=("Segoe UI", 9), anchor="w")
    
    def stop(self) -> None:
        """Stop the game loop."""
        self._running = False
        if self._move_job:
            self.after_cancel(self._move_job)
            self._move_job = None
    
    def get_player_position(self) -> tuple[float, float]:
        """Get player world position."""
        if self._player:
            return (self._player.x, self._player.y)
        return (0, 0)
    
    def set_player_position(self, x: float, y: float) -> None:
        """Set player position."""
        if self._player:
            self._player.x = x
            self._player.y = y


def load_map_from_lua(lua_path: Path) -> GameMap | None:
    """Parse a Tiled Lua export into GameMap."""
    try:
        with open(lua_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        import re
        
        width_m = re.search(r'width\s*=\s*(\d+)', content)
        height_m = re.search(r'height\s*=\s*(\d+)', content)
        tw_m = re.search(r'tilewidth\s*=\s*(\d+)', content)
        th_m = re.search(r'tileheight\s*=\s*(\d+)', content)
        
        if not all([width_m, height_m, tw_m, th_m]):
            return None
        
        game_map = GameMap(
            width=int(width_m.group(1)),
            height=int(height_m.group(1)),
            tilewidth=int(tw_m.group(1)),
            tileheight=int(th_m.group(1)),
        )
        
        layer_pattern = r'name\s*=\s*["\'](Tile Layer \d)["\'].*?encoding\s*=\s*["\']lua["\'].*?data\s*=\s*\{([^}]+)\}'
        for match in re.finditer(layer_pattern, content, re.DOTALL):
            layer_name = match.group(1)
            data_str = match.group(2)
            numbers = [int(x.strip()) for x in data_str.split(',') if x.strip().lstrip('-').isdigit()]
            game_map.layers[layer_name] = TileLayer(
                width=game_map.width,
                height=game_map.height,
                data=numbers[:game_map.width * game_map.height]
            )
        
        for layer_name in ["Object Layer 1", "Walls"]:
            pattern = rf'name\s*=\s*["\'{layer_name}["\'].*?objects\s*=\s*\{{([^}}]+)\}}'
            obj_match = re.search(pattern, content, re.DOTALL)
            if obj_match:
                obj_data = obj_match.group(1)
                for rect in re.finditer(r'x\s*=\s*(\d+).*?y\s*=\s*(\d+).*?width\s*=\s*(\d+).*?height\s*=\s*(\d+)', obj_data, re.DOTALL):
                    x, y, w, h = int(rect.group(1)), int(rect.group(2)), int(rect.group(3)), int(rect.group(4))
                    if w > 0 and h > 0:
                        game_map.walls.append(WallCollider(float(x), float(y), float(w), float(h)))
        
        return game_map
        
    except Exception as e:
        print(f"Map load error: {e}")
        return None


def create_test_map() -> GameMap:
    """Create a simple test map."""
    game_map = GameMap(width=20, height=15, tilewidth=64, tileheight=64)
    
    import random
    layer_data = []
    for i in range(20 * 15):
        if i // 20 == 0 or i // 20 == 14:
            layer_data.append(11)
        elif random.random() < 0.1:
            layer_data.append(random.choice([33, 34, 42, 43]))
        else:
            layer_data.append(0)
    game_map.layers["Tile Layer 1"] = TileLayer(width=20, height=15, data=layer_data)
    
    game_map.walls = [
        WallCollider(384, 0, 320, 128),
        WallCollider(896, 256, 256, 128),
        WallCollider(64, 640, 256, 64),
    ]
    
    game_map.objects = [
        InteractableObject("npc1", "Old Man", 512, 384, "#f39c12", interact_action="talk"),
        InteractableObject("chest1", "Chest", 256, 512, "#9b59b6", interact_action="loot"),
    ]
    
    return game_map
