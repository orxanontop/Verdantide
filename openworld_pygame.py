from __future__ import annotations

"""
openworld_pygame.py

Pygame-based open world exploration system.
- Loads actual Tiled maps (.lua export)
- Uses actual sprite assets and tilesets
- Biome-based theming
- Random encounter triggers
"""

import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
import pygame
import re


@dataclass
class BiomeColors:
    ground: tuple[int, int, int] = (60, 80, 50)
    ground_alt: tuple[int, int, int] = (50, 70, 45)
    wall: tuple[int, int, int] = (40, 50, 35)
    accent: tuple[int, int, int] = (80, 120, 60)
    decoration: tuple[int, int, int] = (100, 140, 80)
    water: tuple[int, int, int] = (40, 80, 160)
    sky: tuple[int, int, int] = (135, 206, 235)


@dataclass
class BiomeData:
    name: str
    description: str
    colors: BiomeColors
    encounter_rate: float
    enemies: list[str]
    resources: list[str]


BIOME_PRESETS: dict[str, BiomeData] = {
    "Forest": BiomeData(
        name="Forest",
        description="A lush area filled with trees and wildlife.",
        colors=BiomeColors(ground=(60, 100, 50), ground_alt=(50, 85, 45), wall=(40, 60, 30),
                          accent=(80, 140, 70), decoration=(100, 160, 90)),
        encounter_rate=0.15,
        enemies=["Goblin", "Wolf", "Bandit"],
        resources=["Wood", "Herbs", "Berries"]
    ),
    "Prism Reef": BiomeData(
        name="Prism Reef",
        description="Crystal coral reef with rainbow light.",
        colors=BiomeColors(ground=(60, 140, 150), ground_alt=(80, 160, 170), wall=(50, 120, 130),
                          accent=(255, 150, 200), decoration=(200, 100, 255), water=(40, 180, 200)),
        encounter_rate=0.12,
        enemies=["Coral Golem", "Reef Shark", "Prism Ray"],
        resources=["Coral Fragments", "Pearls", "Rainbow Scale"]
    ),
    "Emberglow Caves": BiomeData(
        name="Emberglow Caves",
        description="Caverns with cold-fire lichen.",
        colors=BiomeColors(ground=(30, 35, 50), ground_alt=(40, 45, 60), wall=(20, 25, 40),
                          accent=(100, 80, 150), decoration=(80, 60, 120), sky=(20, 25, 40)),
        encounter_rate=0.20,
        enemies=["Argon Bat", "Ember Sprite", "Lichentooth"],
        resources=["Cold-Fire Lichen", "Copper Ore", "Spark Dust"]
    ),
    "Drizzlewood": BiomeData(
        name="Drizzlewood",
        description="Temperate forest in perpetual dusk.",
        colors=BiomeColors(ground=(50, 70, 60), ground_alt=(60, 80, 70), wall=(40, 55, 50),
                          accent=(120, 160, 140), decoration=(140, 180, 160), sky=(60, 80, 100)),
        encounter_rate=0.13,
        enemies=["Dusk Moth", "Capillary Spider", "Pulsing Bloom"],
        resources=["Resonant Wood", "Dew Oil", "Seed-Vault Resin"]
    ),
    "Nimbus Tundra": BiomeData(
        name="Nimbus Tundra",
        description="High-latitude plain with floating snow boulders.",
        colors=BiomeColors(ground=(200, 210, 220), ground_alt=(180, 195, 210), wall=(160, 175, 190),
                          accent=(150, 180, 220), decoration=(220, 230, 240)),
        encounter_rate=0.10,
        enemies=["Drift Maw", "Snow Boulder Crab", "Aurora Wisp"],
        resources=["Nimbus Snow", "Levity Crystal", "Aurora Thread"]
    ),
}


def get_biome_data(biome_name: str) -> BiomeData:
    return BIOME_PRESETS.get(biome_name, BIOME_PRESETS["Forest"])


@dataclass
class Tile:
    x: int
    y: int
    tile_id: int = 0
    walkable: bool = True


@dataclass
class Wall:
    x: float
    y: float
    width: float
    height: float


@dataclass
class Interactable:
    id: str
    name: str
    x: float
    y: float
    sprite_color: tuple[int, int, int]
    action_type: str = "talk"
    data: dict = field(default_factory=dict)


@dataclass
class GameWorld:
    width: int
    height: int
    tile_size: int = 32
    tiles: list[list[Tile]] = field(default_factory=list)
    walls: list[Wall] = field(default_factory=list)
    interactables: list[Interactable] = field(default_factory=list)
    biome: BiomeData | None = None
    tileset_image: pygame.Surface | None = None
    tileset_cols: int = 0

    def tile_at(self, x: int, y: int) -> Tile | None:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None


@dataclass
class Player:
    x: float
    y: float
    width: float = 28
    height: float = 28
    speed: float = 200.0
    direction: str = "down"
    is_moving: bool = False
    anim_frame: int = 0
    anim_timer: float = 0.0


class Camera:
    def __init__(self, width: int, height: int):
        self.x: float = 0.0
        self.y: float = 0.0
        self.width = width
        self.height = height
        self.smoothing: float = 0.1

    def follow(self, target_x: float, target_y: float, world_width: int, world_height: int) -> None:
        target_cam_x = target_x - self.width / 2
        target_cam_y = target_y - self.height / 2

        self.x += (target_cam_x - self.x) * self.smoothing
        self.y += (target_cam_y - self.y) * self.smoothing

        self.x = max(0, min(self.x, world_width - self.width))
        self.y = max(0, min(self.y, world_height - self.height))

    def world_to_screen(self, world_x: float, world_y: float) -> tuple[int, int]:
        return (int(world_x - self.x), int(world_y - self.y))


class SpriteSheet:
    def __init__(self, filename: str, frame_width: int, frame_height: int):
        try:
            self.sheet = pygame.image.load(filename).convert_alpha()
        except pygame.error:
            self.sheet = None
            return

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cols = self.sheet.get_width() // frame_width
        self.rows = self.sheet.get_height() // frame_height

        self._animations: dict[str, list[pygame.Surface]] = {}
        self._load_animations()

    def _load_animations(self) -> None:
        if not self.sheet:
            return

        directions = ["down", "left", "right", "up"]
        for row, direction in enumerate(directions):
            if row >= self.rows:
                break
            frames = []
            for col in range(min(4, self.cols)):
                frame = self._extract_frame(col, row)
                frames.append(frame)
            self._animations[direction] = frames

    def _extract_frame(self, col: int, row: int) -> pygame.Surface:
        if not self.sheet:
            surf = pygame.Surface((self.frame_width, self.frame_height), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            return surf

        x = col * self.frame_width
        y = row * self.frame_height
        frame = pygame.Surface((self.frame_width, self.frame_height), pygame.SRCALPHA)
        frame.blit(self.sheet, (0, 0), (x, y, self.frame_width, self.frame_height))
        return frame

    def get_frame(self, direction: str = "down", index: int = 0) -> pygame.Surface:
        frames = self._animations.get(direction, [])
        if not frames:
            frames = self._animations.get("down", [])
        if not frames:
            surf = pygame.Surface((self.frame_width, self.frame_height), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            return surf
        return frames[min(index, len(frames) - 1)]


def load_lua_map(lua_path: Path, base_path: Path) -> GameWorld | None:
    """Load a Tiled Lua export map."""
    try:
        with open(lua_path, "r", encoding="utf-8") as f:
            content = f.read()

        width_m = re.search(r'width\s*=\s*(\d+)', content)
        height_m = re.search(r'height\s*=\s*(\d+)', content)
        tw_m = re.search(r'tilewidth\s*=\s*(\d+)', content)
        th_m = re.search(r'tileheight\s*=\s*(\d+)', content)

        if not all([width_m, height_m, tw_m, th_m]):
            return None

        width = int(width_m.group(1))
        height = int(height_m.group(1))
        tile_size = int(tw_m.group(1))

        world = GameWorld(width=width, height=height, tile_size=tile_size)

        tileset_path = base_path / "tileset.png"
        if tileset_path.exists():
            try:
                world.tileset_image = pygame.image.load(str(tileset_path)).convert_alpha()
                world.tileset_cols = 9
            except:
                pass

        layer_pattern = r'name\s*=\s*["\'](Tile Layer \d)["\'].*?encoding\s*=\s*["\']lua["\'].*?data\s*=\s*\{([^}]+)\}'
        layer_data_map = {}

        for match in re.finditer(layer_pattern, content, re.DOTALL):
            layer_name = match.group(1)
            data_str = match.group(2)
            numbers = []
            for x in data_str.split(','):
                x = x.strip()
                if x.lstrip('-').isdigit():
                    numbers.append(int(x))
            layer_data_map[layer_name] = numbers

        layer_names = sorted(layer_data_map.keys(), key=lambda n: int(re.search(r'\d', n).group()))

        for y in range(height):
            row = []
            for x in range(width):
                tile = Tile(x=x, y=y, tile_id=0, walkable=True)

                for layer_name in reversed(layer_names):
                    data = layer_data_map.get(layer_name, [])
                    idx = y * width + x
                    if idx < len(data):
                        tile_id = data[idx]
                        if tile_id > 0:
                            tile.tile_id = tile_id
                            break

                row.append(tile)
            world.tiles.append(row)

        for layer_name in ["Object Layer 1", "Walls"]:
            pattern = rf'name\s*=\s*["\'{layer_name}["\'].*?objects\s*=\s*\{{([^}}]+)\}}'
            obj_match = re.search(pattern, content, re.DOTALL)
            if obj_match:
                obj_data = obj_match.group(1)
                for rect in re.finditer(r'x\s*=\s*(\d+).*?y\s*=\s*(\d+).*?width\s*=\s*(\d+).*?height\s*=\s*(\d+)', obj_data, re.DOTALL):
                    x, y, w, h = int(rect.group(1)), int(rect.group(2)), int(rect.group(3)), int(rect.group(4))
                    if w > 0 and h > 0:
                        world.walls.append(Wall(float(x), float(y), float(w), float(h)))

        return world

    except Exception as e:
        print(f"Map load error: {e}")
        return None


def create_fallback_world(biome: BiomeData, width: int = 30, height: int = 30) -> GameWorld:
    """Create a fallback procedural world."""
    world = GameWorld(width=width, height=height, tile_size=64, biome=biome)

    tiles = []
    for y in range(height):
        row = []
        for x in range(width):
            tile = Tile(x=x, y=y, tile_id=0, walkable=True)

            if y == 0 or y == height - 1 or x == 0 or x == width - 1:
                tile.tile_id = 11
            else:
                noise = random.random()
                if noise < 0.05:
                    tile.tile_id = random.choice([33, 34, 42, 43, 51, 52])
                elif noise < 0.08:
                    tile.tile_id = 14
                    world.walls.append(Wall(float(x * 64), float(y * 64), 64, 64))
                else:
                    tile.tile_id = random.choice([1, 2, 3])

            row.append(tile)
        tiles.append(row)

    world.tiles = tiles

    world.interactables = [
        Interactable("npc1", "Traveler", width * 64 / 2, height * 64 / 2,
                    (255, 200, 100), "talk"),
    ]

    return world


class OpenWorldPygame:
    def __init__(
        self,
        screen_width: int = 960,
        screen_height: int = 640,
        map_file: str = "justamap3.lua",
        biome_name: str = "Forest"
    ):
        pygame.init()
        pygame.display.set_caption("Manga RPG - Open World")

        self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.clock = pygame.time.Clock()
        self.running = True
        self._paused = False

        self.screen_width = screen_width
        self.screen_height = screen_height

        self.camera = Camera(screen_width, screen_height)

        self.base_path = Path(__file__).parent
        maps_path = self.base_path / "maps"
        map_path = maps_path / map_file

        biome = get_biome_data(biome_name)

        if map_path.exists():
            self.world = load_lua_map(map_path, maps_path)
            if self.world:
                self.world.biome = biome
        else:
            self.world = create_fallback_world(biome)

        tileset_path = maps_path / "tileset.png"
        if self.world and tileset_path.exists() and self.world.tileset_image is None:
            try:
                self.world.tileset_image = pygame.image.load(str(tileset_path)).convert_alpha()
                self.world.tileset_cols = 9
            except:
                pass

        self._tile_cache: dict[int, pygame.Surface] = {}

        self.player_sprites = None
        player_sprite_path = self.base_path / "sprites" / "player-sheet.png"
        if player_sprite_path.exists():
            self.player_sprites = SpriteSheet(str(player_sprite_path), 12, 18)

        self.player = Player(
            x=self.world.width * self.world.tile_size / 2,
            y=self.world.height * self.world.tile_size / 2
        )

        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        self._keys_pressed: set = set()
        self._step_counter: int = 0
        self._encounter_cooldown: int = 200

        self._on_encounter: Callable | None = None
        self._on_interact: Callable | None = None

    def _get_tile_surface(self, tile_id: int) -> pygame.Surface:
        if tile_id in self._tile_cache:
            return self._tile_cache[tile_id]

        size = self.world.tile_size
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        
        ground_tiles = [0, 1, 2, 3, 4, 5, 6]
        wall_tiles = [10, 11, 12, 13, 14, 15, 16]
        tree_tiles = [33, 34, 35, 36, 42, 43, 44, 45, 51, 52, 53, 54]
        water_tiles = [7, 8, 9, 25, 26, 27]
        path_tiles = [37, 38, 39, 46, 47, 48]
        
        if tile_id in ground_tiles:
            shade = (60 + (tile_id * 5) % 40, 90 + (tile_id * 7) % 30, 50 + (tile_id * 3) % 20)
            surf.fill(shade)
            pygame.draw.rect(surf, tuple(max(0, c - 8) for c in shade), (0, 0, size, size), 1)
        elif tile_id in wall_tiles:
            surf.fill((50, 60, 40))
            pygame.draw.rect(surf, (40, 50, 30), (0, 0, size, size), 2)
            for i in range(3):
                pygame.draw.line(surf, (35, 45, 25), (2, 4 + i * 10), (size - 2, 4 + i * 10))
        elif tile_id in tree_tiles:
            surf.fill((45, 70, 40))
            center_x, center_y = size // 2, size // 2
            pygame.draw.circle(surf, (60, 90, 55), (center_x, center_y - 4), size // 3)
            pygame.draw.circle(surf, (50, 80, 50), (center_x - 6, center_y + 2), size // 4)
            pygame.draw.circle(surf, (55, 85, 52), (center_x + 6, center_y + 2), size // 4)
        elif tile_id in water_tiles:
            surf.fill((50, 130, 170))
            pygame.draw.rect(surf, (60, 150, 190), (0, 0, size // 2, size), 1)
            pygame.draw.rect(surf, (55, 140, 180), (size // 4, size // 4, size // 2, size // 2), 1)
        elif tile_id in path_tiles:
            surf.fill((100, 85, 60))
            pygame.draw.rect(surf, (90, 75, 50), (4, 4, size - 8, size - 8), 1)
        elif tile_id > 0:
            surf.fill((60 + (tile_id % 7) * 10, 80 + (tile_id % 5) * 12, 50 + (tile_id % 3) * 15))
            pygame.draw.rect(surf, (50, 70, 40), (0, 0, size, size), 1)
        else:
            surf.fill((70, 100, 60))

        self._tile_cache[tile_id] = surf
        return surf

    def set_encounter_callback(self, callback: Callable) -> None:
        self._on_encounter = callback

    def set_interact_callback(self, callback: Callable) -> None:
        self._on_interact = callback

    def start(self) -> None:
        self.running = True
        pygame.event.set_grab(True)
        pygame.key.set_repeat(100, 50)
        
        while self.running:
            self._handle_events()
            if not self._paused:
                self._update()
            self._render()
            self.clock.tick(60)

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._try_interact()

    def _update(self) -> None:
        dx, dy = 0.0, 0.0

        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = self.player.speed / 60
            self.player.direction = "right"
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -self.player.speed / 60
            self.player.direction = "left"

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = self.player.speed / 60
            self.player.direction = "down"
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -self.player.speed / 60
            self.player.direction = "up"

        self.player.is_moving = dx != 0 or dy != 0

        if self.player.is_moving:
            new_x = self.player.x + dx
            new_y = self.player.y + dy

            can_x = self._check_movement(new_x, self.player.y)
            can_y = self._check_movement(self.player.x, new_y)

            if can_x:
                self.player.x = new_x
            if can_y:
                self.player.y = new_y

            max_x = float(self.world.width * self.world.tile_size - 16)
            max_y = float(self.world.height * self.world.tile_size - 16)
            self.player.x = max(16, min(self.player.x, max_x))
            self.player.y = max(16, min(self.player.y, max_y))

            self.player.anim_timer += 1 / 60
            if self.player.anim_timer > 0.15:
                self.player.anim_timer = 0
                self.player.anim_frame = (self.player.anim_frame + 1) % 4

            self._step_counter += 1
            if self._step_counter >= self._encounter_cooldown:
                self._step_counter = 0
                if random.random() < self.world.biome.encounter_rate and self._on_encounter:
                    self._on_encounter(self.player.x, self.player.y)
        else:
            self.player.anim_frame = 0

        self.camera.follow(
            self.player.x, self.player.y,
            self.world.width * self.world.tile_size,
            self.world.height * self.world.tile_size
        )

    def _check_movement(self, new_x: float, new_y: float) -> bool:
        return True

    def _try_interact(self) -> None:
        if not self._on_interact:
            return

        for obj in self.world.interactables:
            dist = math.sqrt((self.player.x - obj.x) ** 2 + (self.player.y - obj.y) ** 2)
            if dist < 48:
                self._on_interact(obj)
                return

    def _render(self) -> None:
        if not self.world or not self.world.biome:
            self.screen.fill((100, 100, 100))
            return
            
        bg_color = self.world.biome.colors.sky
        self.screen.fill(bg_color)

        tile_size = self.world.tile_size
        start_x = max(0, int(self.camera.x // tile_size) - 1)
        end_x = min(self.world.width, int((self.camera.x + self.screen_width) // tile_size) + 2)
        start_y = max(0, int(self.camera.y // tile_size) - 1)
        end_y = min(self.world.height, int((self.camera.y + self.screen_height) // tile_size) + 2)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.world.tiles[y][x]
                screen_x, screen_y = self.camera.world_to_screen(x * tile_size, y * tile_size)

                surf = self._get_tile_surface(tile.tile_id)
                self.screen.blit(surf, (screen_x, screen_y))

        for wall in self.world.walls:
            screen_x, screen_y = self.camera.world_to_screen(wall.x, wall.y)
            pygame.draw.rect(self.screen, (60, 40, 30),
                          (screen_x, screen_y, wall.width, wall.height), 3)

        for obj in self.world.interactables:
            screen_x, screen_y = self.camera.world_to_screen(obj.x, obj.y)

            pygame.draw.circle(self.screen, obj.sprite_color, (screen_x, screen_y), 20)
            pygame.draw.circle(self.screen, (255, 255, 255), (screen_x, screen_y), 20, 2)

            text = self.font.render(obj.name, True, (255, 255, 255))
            text_rect = text.get_rect(center=(screen_x, screen_y - 40))
            pygame.draw.rect(self.screen, (0, 0, 0), text_rect.inflate(8, 4))
            self.screen.blit(text, text_rect)

        screen_x, screen_y = self.camera.world_to_screen(self.player.x, self.player.y)

        bob = 2 if self.player.is_moving and self.player.anim_frame % 2 == 0 else 0

        if self.player_sprites:
            sprite = self.player_sprites.get_frame(self.player.direction, self.player.anim_frame)
            scaled_sprite = pygame.transform.scale(sprite, (80, 120))
            self.screen.blit(scaled_sprite, (screen_x - 40, screen_y - 80 + bob))
        else:
            pygame.draw.ellipse(self.screen, (78, 205, 196),
                              (screen_x - 14, screen_y - 28 + bob, 28, 20))
            pygame.draw.rect(self.screen, (46, 204, 113),
                           (screen_x - 12, screen_y - 10 + bob, 24, 20))

        controls_text = "WASD: Move | SPACE: Interact | ESC: Quit"
        text_surf = self.small_font.render(controls_text, True, (150, 150, 150))
        self.screen.blit(text_surf, (10, self.screen_height - 25))

        biome_text = f"Biome: {self.world.biome.name}"
        text_surf = self.small_font.render(biome_text, True, (200, 200, 200))
        self.screen.blit(text_surf, (10, 10))

        pygame.display.flip()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self.running = False

    def get_player_position(self) -> tuple[float, float]:
        return (self.player.x, self.player.y)

    def get_world(self) -> GameWorld:
        return self.world
