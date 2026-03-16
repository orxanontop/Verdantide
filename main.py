import json
import os 
import random
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from battle_ui import BattleUI, make_default_player, make_enemy_from_template

ADVANTAGE_FILE = Path("jsons/elemadvantages.json")
ACTIONS_FILE = Path("jsons/actions.json")
BIOMES_FILE = Path("jsons/biomes.json")
RACES_FILE = Path("jsons/races.json")
MAINCHARACTERS_FILE = Path("jsons/mainchar.json")
ENEMIES_FILE = Path("jsons/enemies.json")
CLASSES_FILE = Path("jsons/classes.json")


def read_json(filename, default=None):
     try:
         with open(filename, 'r', encoding='utf-8') as f:
              return json.load(f)
     except:
          return default or []

def write_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
      json.dump(data, f, indent=4)


class mainCharacter:
    def __init__(self, name, Class, uniqueSkill, element):
        self.name = name
        self.Class = Class
        self.uniqueSkill = uniqueSkill
        self.element = element

    def displayInfo(self):
        print(f"Name: {self.name}")
        print(f"Class: {self.Class}")
        print(f"Unique Skill: {self.uniqueSkill}")
        print(f"Element: {self.element}")

class randomMainCharacter:
    @staticmethod
    def randomCharacter(path: Path = MAINCHARACTERS_FILE) -> dict:
        characters = read_json(path, default=[])
        if not characters:
            return {}
        return random.choice(characters)

class Villain:
        def __init__(self, name, Class, uniqueSkill, element, evilPlan,):
            self.name = name
            self.evilPlan = evilPlan
            self.Class = Class
            self.uniqueSkill = uniqueSkill
            self.element = element

        def displayVillainInfo(self):
            print(f"Villain Name: {self.name}")
            print(f"Evil Plan: {self.evilPlan}")
            print(f"Class: {self.Class}")
            print(f"Unique Skill: {self.uniqueSkill}")
            print(f"Element: {self.element}")

class Action:
    def __init__(self, actionType, description):
        self.actionType = actionType
        self.description = description

    def displayAction(self):
        print(f"Action Type: {self.actionType}")
        print(f"Description: {self.description}")

    @staticmethod
    def actionChoice(path_to_json: Path = ACTIONS_FILE) -> dict:
        actions = read_json(path_to_json, default=[])
        if not actions:
            print("No actions available.")
            return None

        for idx, a in enumerate(actions, 1):
            print(f"{idx}. {a['action']}  ({a['difficulty']})")
            print(f"   {a['description']}")
            print(f"   Reward: {a['reward']}\n")

        while True:
            try:
                choice = int(input("Choose an action (number): "))
                if 1 <= choice <= len(actions):
                    return actions[choice - 1]
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

class Biomes:
    def __init__(self, biomeType, characteristics):
        self.biomeType = biomeType
        self.characteristics = characteristics

    def displayBiome(self):
        print(f"Biome Type: {self.biomeType}")
        print(f"Characteristics: {self.characteristics}")

    @staticmethod
    def randomBiome(path_to_json: Path = Path(BIOMES_FILE)) -> dict:
        biomes = read_json(path_to_json, default=[])
        if not biomes:
            return {}
        return random.choice(biomes)
    

class Races:

    @staticmethod
    def randomRace(path: Path = RACES_FILE) -> dict:
        raace = read_json(path, default=[])
        if not raace:
            return {}
        return random.choice(raace)
    
    def __init__(self, raceName, traits, affinities):
        self.raceName = raceName
        self.traits = traits
        self.affinities = affinities
    
    def displayRace(self):
        print(f"Race Name: {self.raceName}")
        print(f"Traits: {self.traits}")
        print(f"Affinities: {self.affinities}")



class element:
    @staticmethod
    def randomElement(path: Path = ADVANTAGE_FILE) -> dict:
        elements = read_json(path, default=None)
        if not elements:
            return {}
        return random.choice(elements)

def run_cli():
    """Original console version of the generator."""
    rele = element.randomElement()
    if rele:
        print(f"random element: {rele.get('element', 'Unknown')}")
    print("-" * 40)

    rmc = randomMainCharacter.randomCharacter()
    if rmc:
        print(f"name: {rmc.get('name', 'Unknown')}")
    print("-" * 40)

    rbiome = Biomes.randomBiome()
    if rbiome:
        print(f"\nRandom Biome Selected: {rbiome.get('biome', 'Unknown')}")
    print("-" * 40)

    rrace = Races.randomRace()
    if rrace:
        print(f"\nRandom Race Selected: {rrace.get('name', 'Unknown')}")
    print("-" * 40)

    selected = Action.actionChoice()
    if selected:
        print(f"\nSelected Action: {selected.get('action', 'Unknown')}")


def run_gui():
    """Tkinter GUI with modernized 2026-style indie RPG battle screen."""

    root = tk.Tk()
    root.title("Manga RPG - Battle")
    root.geometry("1180x720")
    root.minsize(1020, 640)

    # App styling baseline
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    app_bg = "#0b0f17"
    text_fg = "#d9deea"
    accent = "#fbbf24"

    root.configure(bg=app_bg)
    style.configure("App.TFrame", background=app_bg)
    style.configure("Panel.TLabelframe", background=app_bg, foreground=text_fg)
    style.configure("Panel.TLabelframe.Label", background=app_bg, foreground=accent, font=("Segoe UI", 11, "bold"))
    style.configure("App.TLabel", background=app_bg, foreground=text_fg, font=("Segoe UI", 10))
    style.configure("AppTitle.TLabel", background=app_bg, foreground=accent, font=("Segoe UI", 16, "bold"))
    style.configure("App.TButton", font=("Segoe UI", 10, "bold"), padding=6)

    base_dir = Path(__file__).parent

    # Load data for hero/enemy roll.
    enemies_data = read_json(base_dir / ENEMIES_FILE, default=[])
    characters_data = read_json(base_dir / MAINCHARACTERS_FILE, default=[])
    elem_data = read_json(base_dir / ADVANTAGE_FILE, default=[])

    # Layout: left (tips), right (battle)
    main = ttk.Frame(root, style="App.TFrame")
    main.pack(fill="both", expand=True)

    left = ttk.Frame(main, style="App.TFrame")
    right = ttk.Frame(main, style="App.TFrame")
    left.configure(width=260)
    left.pack(side="left", fill="y", padx=12, pady=14)
    left.pack_propagate(False)
    right.pack(side="right", fill="both", expand=True, padx=14, pady=14)

    hero_names = [c.get("name", "Hero") for c in characters_data] or ["Hero"]
    elem_names = [e.get("element", "Neutral") for e in elem_data] or ["Fire", "Ice", "Wind"]

    info = ttk.LabelFrame(left, text="Tips", style="Panel.TLabelframe")
    info.pack(fill="x", pady=(0, 10))
    ttk.Label(
        info,
        text=(
            "Fire > Ice\n"
            "Ice > Wind\n"
            "Wind > Fire\n\n"
            "Heavy is a charge: the next turn it hits hard but can miss.\n"
            "Defend reduces the next incoming hit.\n"
            "Sunder builds Break and applies Exposed.\n"
            "Rally grants Fury (+damage).\n"
            "Crippling Slash inflicts Weaken (-damage).\n"
            "When Break fills (💥), the target loses its next turn."
        ),
        style="App.TLabel",
        justify="left",
        wraplength=220,
    ).pack(anchor="w", padx=10, pady=10)

    battle = BattleUI(right)
    battle.pack(fill="both", expand=True)

    def start_encounter():
        try:
            enemy_tpl = random.choice(enemies_data) if enemies_data else {"name": "Bandit", "element": "Air", "hp": 90}
            battle.start_battle(
                make_default_player(random.choice(hero_names), random.choice(elem_names or ["Fire", "Ice", "Wind"])),
                make_enemy_from_template(enemy_tpl),
            )
        except Exception as e:
            messagebox.showerror("Battle Error", str(e))

    # Kick off a first encounter.
    start_encounter()

    root.mainloop()

if __name__ == "__main__":
    run_gui()
