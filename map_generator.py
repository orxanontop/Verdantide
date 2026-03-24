"""
map_generator.py

Generates Tiled-compatible Lua maps for each biome.
Each biome gets a unique map with appropriate tiles and obstacles.
"""

import random
import json
from pathlib import Path


BIOMES = [
    {
        "name": "Forest",
        "tiles": [1, 2, 3, 11, 12, 14, 33, 34, 42, 43],
        "walkable": [1, 2, 3],
        "obstacles": [11, 12, 14, 33, 34, 42, 43],
        "water": [],
        "colors": {"ground": "#3d5a35", "wall": "#2d4a25", "accent": "#5a7a4a"}
    },
    {
        "name": "Prism Reef",
        "tiles": [1, 2, 7, 8, 9, 25, 26, 27],
        "walkable": [1, 2],
        "obstacles": [],
        "water": [7, 8, 9, 25, 26, 27],
        "colors": {"ground": "#3a8a9a", "wall": "#2a6a7a", "accent": "#7acaea"}
    },
    {
        "name": "Emberglow Caves",
        "tiles": [10, 11, 12, 13, 14, 15, 16],
        "walkable": [10],
        "obstacles": [11, 12, 13, 14, 15, 16],
        "water": [],
        "colors": {"ground": "#1e232a", "wall": "#141820", "accent": "#4a3a5a"}
    },
    {
        "name": "Drizzlewood",
        "tiles": [1, 2, 3, 11, 14, 33, 34, 51, 52],
        "walkable": [1, 2, 3],
        "obstacles": [11, 14, 33, 34, 51, 52],
        "water": [],
        "colors": {"ground": "#324646", "wall": "#223636", "accent": "#5a7a7a"}
    },
    {
        "name": "Mirrorsteppe",
        "tiles": [1, 2, 3, 10, 11],
        "walkable": [1, 2, 3],
        "obstacles": [10, 11],
        "water": [],
        "colors": {"ground": "#c8c8d0", "wall": "#a8a8b0", "accent": "#e8e8f0"}
    },
    {
        "name": "Nimbus Tundra",
        "tiles": [1, 2, 3, 10, 11, 33, 34],
        "walkable": [1, 2, 3],
        "obstacles": [10, 11, 33, 34],
        "water": [],
        "colors": {"ground": "#c8d0d8", "wall": "#a8b0b8", "accent": "#e8f0f8"}
    },
    {
        "name": "Obsidian Bloom Badlands",
        "tiles": [10, 11, 12, 13, 14, 15, 16],
        "walkable": [10],
        "obstacles": [11, 12, 13, 14, 15, 16],
        "water": [],
        "colors": {"ground": "#141418", "wall": "#0a0a0c", "accent": "#6a2a4a"}
    },
    {
        "name": "Riftglass Savannah",
        "tiles": [1, 2, 3, 10, 11, 37, 38, 39],
        "walkable": [1, 2, 3, 37, 38, 39],
        "obstacles": [10, 11],
        "water": [],
        "colors": {"ground": "#8a7a5a", "wall": "#6a5a4a", "accent": "#ba9a7a"}
    },
    {
        "name": "Sighing Mangrove",
        "tiles": [1, 2, 7, 8, 9, 25, 26, 27, 33, 34, 51, 52],
        "walkable": [1, 2],
        "obstacles": [33, 34, 51, 52],
        "water": [7, 8, 9, 25, 26, 27],
        "colors": {"ground": "#2a4a3a", "wall": "#1a3a2a", "accent": "#4a7a5a"}
    },
    {
        "name": "Aurora Drift",
        "tiles": [1, 2, 3, 10, 11, 33, 34],
        "walkable": [1, 2, 3],
        "obstacles": [10, 11, 33, 34],
        "water": [],
        "colors": {"ground": "#8090a8", "wall": "#607080", "accent": "#a0b0c8"}
    },
    {
        "name": "Hollowspire Jungle",
        "tiles": [1, 2, 3, 11, 14, 33, 34, 42, 43, 51, 52],
        "walkable": [1, 2, 3],
        "obstacles": [11, 14, 33, 34, 42, 43, 51, 52],
        "water": [],
        "colors": {"ground": "#2a5a2a", "wall": "#1a4a1a", "accent": "#4a8a4a"}
    },
]


def generate_map(biome: dict, width: int = 30, height: int = 20, seed: int = None) -> dict:
    """Generate a map dictionary for a biome."""
    if seed:
        random.seed(seed)
    
    walkable = biome["walkable"]
    obstacles = biome["obstacles"]
    water = biome.get("water", [])
    
    layers = {
        "Tile Layer 1": [],
        "Tile Layer 2": [],
    }
    
    for y in range(height):
        row = []
        for x in range(width):
            if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                row.append(11)
            else:
                rand = random.random()
                if rand < 0.7:
                    row.append(random.choice(walkable) if walkable else 1)
                elif rand < 0.85:
                    row.append(random.choice(obstacles) if obstacles else 11)
                else:
                    row.append(random.choice(walkable) if walkable else 1)
        layers["Tile Layer 1"].extend(row)
    
    if water:
        for y in range(height):
            for x in range(width):
                if x > 2 and x < width - 3 and y > 2 and y < height - 3:
                    if random.random() < 0.1:
                        idx = y * width + x
                        if layers["Tile Layer 1"][idx] in walkable:
                            layers["Tile Layer 1"][idx] = random.choice(water)
    
    return {
        "width": width,
        "height": height,
        "layers": layers
    }


def create_lua_export(biome: dict, map_data: dict) -> str:
    """Create a Tiled Lua export string."""
    width = map_data["width"]
    height = map_data["height"]
    
    lua = f"""return {{
  version = "1.10",
  luaversion = "5.1",
  tiledversion = "1.11.2",
  class = "",
  orientation = "orthogonal",
  renderorder = "right-down",
  width = {width},
  height = {height},
  tilewidth = 64,
  tileheight = 64,
  nextlayerid = 3,
  nextobjectid = 1,
  properties = {{}},
  tilesets = {{
    {{
      name = "{biome['name']}Tiles",
      firstgid = 1,
      class = "",
      tilewidth = 64,
      tileheight = 64,
      spacing = 0,
      margin = 0,
      columns = 9,
      image = "tileset.png",
      imagewidth = 576,
      imageheight = 384,
      objectalignment = "unspecified",
      tilerendersize = "tile",
      fillmode = "stretch",
      tileoffset = {{ x = 0, y = 0 }},
      grid = {{ orientation = "orthogonal", width = 64, height = 64 }},
      properties = {{}},
      wangsets = {{}},
      tilecount = 54,
      tiles = {{}}
    }}
  }},
  layers = {{
    {{
      type = "tilelayer",
      x = 0,
      y = 0,
      width = {width},
      height = {height},
      id = 1,
      name = "Tile Layer 1",
      class = "",
      visible = true,
      opacity = 1,
      offsetx = 0,
      offsety = 0,
      parallaxx = 1,
      parallaxy = 1,
      properties = {{}},
      encoding = "lua",
      data = {{"""
    
    for i, tile_id in enumerate(map_data["layers"]["Tile Layer 1"]):
        if i % width == 0:
            lua += "\n        "
        lua += f"{tile_id}, "
    
    lua += """
      }
    },
    {
      type = "tilelayer",
      x = 0,
      y = 0,
      width = """ + str(width) + """,
      height = """ + str(height) + """,
      id = 2,
      name = "Tile Layer 2",
      class = "",
      visible = true,
      opacity = 1,
      offsetx = 0,
      offsety = 0,
      parallaxx = 1,
      parallaxy = 1,
      properties = {},
      encoding = "lua",
      data = {"""
    
    for y in range(height):
        for x in range(width):
            lua += "0, "
    
    lua += """
      }
    }
  }}
}"""
    
    return lua


def generate_all_maps(output_dir: Path):
    """Generate all biome maps."""
    output_dir.mkdir(exist_ok=True)
    
    for i, biome in enumerate(BIOMES):
        map_data = generate_map(biome, seed=i*100)
        lua_content = create_lua_export(biome, map_data)
        
        filename = biome["name"].lower().replace(" ", "_") + ".lua"
        filepath = output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(lua_content)
        
        print(f"Created: {filename}")
    
    print(f"\nGenerated {len(BIOMES)} biome maps!")


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    maps_dir = base_dir / "maps"
    
    generate_all_maps(maps_dir)
