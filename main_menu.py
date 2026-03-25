from __future__ import annotations

import pygame

pygame.init()

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640


def draw_gradient_background(screen: pygame.Surface):
    colors = [
        (200, 130, 120),
        (180, 110, 100),
        (140, 80, 90),
        (100, 60, 80),
        (70, 45, 70),
        (50, 35, 60),
        (40, 25, 55),
        (35, 20, 50),
    ]
    
    step_height = SCREEN_HEIGHT // (len(colors) - 1)
    
    for i in range(len(colors) - 1):
        y1 = i * step_height
        y2 = min((i + 1) * step_height, SCREEN_HEIGHT)
        
        for y in range(y1, y2):
            t = (y - y1) / (y2 - y1)
            r = int(colors[i][0] + (colors[i + 1][0] - colors[i][0]) * t)
            g = int(colors[i][1] + (colors[i + 1][1] - colors[i][1]) * t)
            b = int(colors[i][2] + (colors[i + 1][2] - colors[i][2]) * t)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))


def draw_mountains(screen: pygame.Surface):
    pygame.draw.polygon(screen, (30, 15, 45), [
        (0, SCREEN_HEIGHT),
        (150, SCREEN_HEIGHT - 200),
        (300, SCREEN_HEIGHT - 350),
        (450, SCREEN_HEIGHT - 150),
        (600, SCREEN_HEIGHT),
    ])
    
    pygame.draw.polygon(screen, (25, 12, 40), [
        (400, SCREEN_HEIGHT),
        (550, SCREEN_HEIGHT - 180),
        (700, SCREEN_HEIGHT - 320),
        (850, SCREEN_HEIGHT - 220),
        (960, SCREEN_HEIGHT),
    ])
    
    pygame.draw.polygon(screen, (20, 10, 35), [
        (800, SCREEN_HEIGHT),
        (880, SCREEN_HEIGHT - 120),
        (960, SCREEN_HEIGHT),
    ])


class TextButton:
    def __init__(self, x: int, y: int, text: str, font: pygame.font.Font):
        self.text = text
        self.base_font = font
        self.x = x
        self.y = y
        self.hovered = False
        self.base_color = (255, 255, 255)
        self.hover_color = (255, 215, 140)
    
    def update(self, mouse_pos: tuple[int, int]) -> None:
        width, height = self.base_font.size(self.text)
        
        self.hovered = (
            mouse_pos[0] >= self.x - width // 2 and
            mouse_pos[0] <= self.x + width // 2 and
            mouse_pos[1] >= self.y - height // 2 and
            mouse_pos[1] <= self.y + height // 2
        )
    
    def draw(self, screen: pygame.Surface) -> None:
        scale = 1.1 if self.hovered else 1.0
        color = self.hover_color if self.hovered else self.base_color
        
        scaled_size = int(32 * scale)
        scaled_font = pygame.font.SysFont("times", scaled_size)
        
        shadow_surf = scaled_font.render(self.text, True, (20, 10, 30))
        shadow_rect = shadow_surf.get_rect(center=(self.x + 2, self.y + 2))
        screen.blit(shadow_surf, shadow_rect)
        
        text_surf = scaled_font.render(self.text, True, color)
        text_rect = text_surf.get_rect(center=(self.x, self.y))
        screen.blit(text_surf, text_rect)
    
    def get_size(self) -> tuple[int, int]:
        return self.base_font.size(self.text)
    
    def is_clicked(self, mouse_pos: tuple[int, int], clicked: bool) -> bool:
        if not clicked:
            return False
        
        width, height = self.get_size()
        
        return (
            mouse_pos[0] >= self.x - width // 2 and
            mouse_pos[0] <= self.x + width // 2 and
            mouse_pos[1] >= self.y - height // 2 and
            mouse_pos[1] <= self.y + height // 2
        )


BIOME_COLORS = {
    "forest": ((60, 100, 50), (80, 140, 70)),
    "prism_reef": ((60, 140, 150), (255, 150, 200)),
    "emberglow_caves": ((30, 35, 50), (100, 80, 150)),
    "drizzlewood": ((50, 70, 60), (120, 160, 140)),
    "mirrorsteppe": ((180, 190, 200), (200, 210, 220)),
    "nimbus_tundra": ((200, 210, 220), (150, 180, 220)),
    "obsidian_bloom_badlands": ((80, 50, 50), (150, 80, 60)),
    "riftglass_savannah": ((180, 140, 80), (220, 180, 100)),
    "sighing_mangrove": ((40, 80, 60), (80, 140, 100)),
    "aurora_drift": ((40, 60, 100), (150, 100, 200)),
    "hollowspire_jungle": ((50, 90, 50), (100, 160, 80)),
}

BIOME_DESCRIPTIONS = {
    "forest": "A lush area filled with trees and wildlife.",
    "prism_reef": "Crystal coral reef with rainbow light.",
    "emberglow_caves": "Caverns with cold-fire lichen.",
    "drizzlewood": "Temperate forest in perpetual dusk.",
    "mirrorsteppe": "Grassland with reflective dews.",
    "nimbus_tundra": "High-latitude plain with floating snow.",
    "obsidian_bloom_badlands": "Volcanic terrain with strange flowers.",
    "riftglass_savannah": "Savanna with glass-like formations.",
    "sighing_mangrove": "Tidal wetland with whispering trees.",
    "aurora_drift": "Frozen sea with dancing lights.",
    "hollowspire_jungle": "Dense jungle around ancient ruins.",
}


class MenuState:
    def __init__(self, screen: pygame.Surface, title_font: pygame.font.Font, button_font: pygame.font.Font):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        self.title_font = title_font
        self.button_font = button_font
    
    def handle_events(self, events: list, menu_manager=None) -> str | None:
        return None
    
    def draw(self) -> None:
        pass


class MainMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        
        menu_items = ["Play", "Tutorial", "Achievements", "Credits", "Settings"]
        
        start_y = int(180 * scale)
        spacing = int(55 * scale)
        
        self.buttons = []
        for i, text in enumerate(menu_items):
            y = start_y + i * spacing
            btn = TextButton(self.screen_width // 2, y, text, self.button_font)
            self.buttons.append(btn)
    
    def handle_events(self, events: list, menu_manager=None) -> str | None:
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
                for btn in self.buttons:
                    btn.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                for btn in self.buttons:
                    if btn.is_clicked(mouse_pos, True):
                        return btn.text
        
        return None
    
    def draw(self) -> None:
        draw_gradient_background(self.screen)
        draw_mountains(self.screen)
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        
        title = "Verdantide"
        title_font = pygame.font.SysFont("times", int(64 * scale))
        
        shadow_surf = title_font.render(title, True, (20, 10, 30))
        shadow_rect = shadow_surf.get_rect(center=(self.screen_width // 2 + 3, int(55 * scale) + 3))
        self.screen.blit(shadow_surf, shadow_rect)
        
        title_surf = title_font.render(title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, int(55 * scale)))
        self.screen.blit(title_surf, title_rect)
        
        for btn in self.buttons:
            btn.draw(self.screen)
        
        hint_font = pygame.font.SysFont("times", int(14 * scale))
        hint = hint_font.render("Press F11 for fullscreen", True, (120, 120, 140))
        hint_rect = hint.get_rect(center=(self.screen_width // 2, self.screen_height - int(20 * scale)))
        self.screen.blit(hint, hint_rect)


class PlayMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        
        self.biomes = [
            "forest", "prism_reef", "emberglow_caves", "drizzlewood",
            "mirrorsteppe", "nimbus_tundra", "obsidian_bloom_badlands",
            "riftglass_savannah", "sighing_mangrove", "aurora_drift", "hollowspire_jungle"
        ]
        
        self.biome_names = [
            "Forest", "Prism Reef", "Emberglow Caves", "Drizzlewood",
            "Mirrorsteppe", "Nimbus Tundra", "Obsidian Bloom Badlands",
            "Riftglass Savannah", "Sighing Mangrove", "Aurora Drift", "Hollowspire Jungle"
        ]
        
        self.selected_biome = 0
        self.scroll_offset = 0
        self.max_visible = 5
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        self.card_width = int(500 * scale)
        self.card_height = int(55 * scale)
        self.card_spacing = int(10 * scale)
        self.card_start_y = int(100 * scale)
        
        self.start_btn = TextButton(self.screen_width // 2, int(560 * scale), "Start Game", self.button_font)
        self.back_button = TextButton(int(50 * scale), int(self.screen_height - 45 * scale), "Back", self.button_font)
        
        self.scroll_up_btn = TextButton(self.screen_width // 2 + int(280 * scale), self.card_start_y + int(20 * scale), "▲", pygame.font.SysFont("times", int(20 * scale)))
        self.scroll_down_btn = TextButton(self.screen_width // 2 + int(280 * scale), self.card_start_y + int((self.max_visible - 1) * (self.card_height + self.card_spacing) + 20 * scale), "▼", pygame.font.SysFont("times", int(20 * scale)))
        
        self.hovered_card = None
    
    def handle_events(self, events: list, menu_manager=None) -> str | None:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.back_button.update(mouse_pos)
                self.start_btn.update(mouse_pos)
                self.scroll_up_btn.update(mouse_pos)
                self.scroll_down_btn.update(mouse_pos)
                
                self.hovered_card = None
                scale = min(self.screen_width / 960, self.screen_height / 640)
                for i in range(self.max_visible):
                    idx = i + self.scroll_offset
                    if idx < len(self.biomes):
                        card_x = self.screen_width // 2 - self.card_width // 2
                        card_y = self.card_start_y + i * (self.card_height + self.card_spacing)
                        card_rect = pygame.Rect(card_x, card_y, self.card_width, self.card_height)
                        if card_rect.collidepoint(mouse_pos):
                            self.hovered_card = idx
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.is_clicked(mouse_pos, True):
                    return "back"
                
                if self.scroll_up_btn.is_clicked(mouse_pos, True):
                    self.scroll_offset = max(0, self.scroll_offset - 1)
                if self.scroll_down_btn.is_clicked(mouse_pos, True):
                    max_offset = max(0, len(self.biomes) - self.max_visible)
                    self.scroll_offset = min(max_offset, self.scroll_offset + 1)
                
                for i in range(self.max_visible):
                    idx = i + self.scroll_offset
                    if idx < len(self.biomes):
                        card_x = self.screen_width // 2 - self.card_width // 2
                        card_y = self.card_start_y + i * (self.card_height + self.card_spacing)
                        card_rect = pygame.Rect(card_x, card_y, self.card_width, self.card_height)
                        if card_rect.collidepoint(mouse_pos):
                            self.selected_biome = idx
                
                if self.start_btn.is_clicked(mouse_pos, True):
                    return f"start:{self.biomes[self.selected_biome]}"
        
        return None
    
    def draw(self) -> None:
        draw_gradient_background(self.screen)
        draw_mountains(self.screen)
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 50))
        self.screen.blit(overlay, (0, 0))
        
        title_font = pygame.font.SysFont("times", int(52 * scale))
        title_surf = title_font.render("Select Biome", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, int(45 * scale)))
        self.screen.blit(title_surf, title_rect)
        
        for i in range(self.max_visible):
            idx = i + self.scroll_offset
            if idx >= len(self.biomes):
                break
            
            biome_key = self.biomes[idx]
            biome_name = self.biome_names[idx]
            is_selected = (idx == self.selected_biome)
            is_hovered = (idx == self.hovered_card)
            
            card_x = self.screen_width // 2 - self.card_width // 2
            card_y = self.card_start_y + i * (self.card_height + self.card_spacing)
            
            primary_color, accent_color = BIOME_COLORS.get(biome_key, ((60, 80, 100), (100, 150, 200)))
            
            card_rect = pygame.Rect(card_x, card_y, self.card_width, self.card_height)
            
            if is_selected:
                pygame.draw.rect(self.screen, accent_color, card_rect, int(3 * scale), border_radius=int(10 * scale))
                card_bg = tuple(min(255, c + 30) for c in primary_color)
                pygame.draw.rect(self.screen, card_bg, card_rect, border_radius=int(10 * scale))
            elif is_hovered:
                card_bg = tuple(min(255, c + 15) for c in primary_color)
                pygame.draw.rect(self.screen, card_bg, card_rect, border_radius=int(10 * scale))
            else:
                card_bg = tuple(int(c * 0.6) for c in primary_color)
                pygame.draw.rect(self.screen, card_bg, card_rect, border_radius=int(10 * scale))
            
            name_font = pygame.font.SysFont("times", int(22 * scale))
            name_surf = name_font.render(biome_name, True, (255, 255, 255))
            shadow_surf = name_font.render(biome_name, True, (0, 0, 0))
            self.screen.blit(shadow_surf, (card_x + int(20 * scale) + 2, card_y + int(12 * scale) + 2))
            self.screen.blit(name_surf, (card_x + int(20 * scale), card_y + int(12 * scale)))
            
            desc = BIOME_DESCRIPTIONS.get(biome_key, "")
            desc_font = pygame.font.SysFont("times", int(12 * scale))
            desc_surf = desc_font.render(desc, True, (180, 180, 180))
            self.screen.blit(desc_surf, (card_x + int(20 * scale), card_y + int(32 * scale)))
            
            if is_selected:
                check_surf = pygame.font.SysFont("times", int(20 * scale)).render("✓", True, accent_color)
                self.screen.blit(check_surf, (card_x + self.card_width - int(35 * scale), card_y + int(18 * scale)))
        
        if self.scroll_offset > 0:
            self.scroll_up_btn.draw(self.screen)
        if self.scroll_offset < len(self.biomes) - self.max_visible:
            self.scroll_down_btn.draw(self.screen)
        
        selected_key = self.biomes[self.selected_biome]
        selected_name = self.biome_names[self.selected_biome]
        selected_desc = BIOME_DESCRIPTIONS.get(selected_key, "")
        
        info_panel = pygame.Rect(int(40 * scale), int(420 * scale), self.screen_width - int(80 * scale), int(50 * scale))
        pygame.draw.rect(self.screen, (20, 15, 30), info_panel, border_radius=int(10 * scale))
        pygame.draw.rect(self.screen, (100, 80, 150), info_panel, int(2 * scale), border_radius=int(10 * scale))
        
        info_name = pygame.font.SysFont("times", int(20 * scale)).render(selected_name, True, (255, 215, 140))
        self.screen.blit(info_name, (int(55 * scale), int(428 * scale)))
        
        info_desc = pygame.font.SysFont("times", int(14 * scale)).render(selected_desc, True, (180, 180, 200))
        self.screen.blit(info_desc, (int(55 * scale), int(452 * scale)))
        
        self.start_btn.draw(self.screen)
        self.back_button.draw(self.screen)


class TutorialMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        
        self.tutorials = [
            ("Movement", "Use WASD or Arrow Keys to move around"),
            ("Combat", "Random encounters trigger turn-based battles"),
            ("Skills", "Each skill costs SP and has cooldowns"),
            ("Elements", "Fire > Ice > Wind > Fire"),
            ("Break", "Fill the break gauge to stun enemies!"),
        ]
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        self.back_button = TextButton(int(50 * scale), int(self.screen_height - 45 * scale), "Back", self.button_font)
    
    def handle_events(self, events: list, menu_manager=None) -> str | None:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.back_button.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.is_clicked(mouse_pos, True):
                    return "back"
        
        return None
    
    def draw(self) -> None:
        draw_gradient_background(self.screen)
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        
        title_font = pygame.font.SysFont("times", int(52 * scale))
        title_surf = title_font.render("Tutorial", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, int(50 * scale)))
        self.screen.blit(title_surf, title_rect)
        
        y = int(120 * scale)
        for title, desc in self.tutorials:
            t_surf = pygame.font.SysFont("times", int(24 * scale)).render(title, True, (100, 150, 255))
            self.screen.blit(t_surf, (int(80 * scale), y))
            
            d_surf = pygame.font.SysFont("times", int(18 * scale)).render(desc, True, (180, 180, 200))
            self.screen.blit(d_surf, (int(100 * scale), y + int(28 * scale)))
            
            y += int(65 * scale)
        
        self.back_button.draw(self.screen)


class AchievementsMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        scale = min(self.screen_width / 960, self.screen_height / 640)
        self.back_button = TextButton(int(50 * scale), int(self.screen_height - 45 * scale), "Back", self.button_font)
    
    def handle_events(self, events: list, menu_manager=None) -> str | None:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.back_button.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.is_clicked(mouse_pos, True):
                    return "back"
        
        return None
    
    def draw(self) -> None:
        draw_gradient_background(self.screen)
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        
        title_font = pygame.font.SysFont("times", int(52 * scale))
        title_surf = title_font.render("Achievements", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, int(50 * scale)))
        self.screen.blit(title_surf, title_rect)
        
        placeholder = pygame.font.SysFont("times", int(22 * scale)).render("No achievements yet!", True, (180, 180, 200))
        placeholder_rect = placeholder.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
        self.screen.blit(placeholder, placeholder_rect)
        
        self.back_button.draw(self.screen)


class CreditsMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        scale = min(self.screen_width / 960, self.screen_height / 640)
        self.back_button = TextButton(int(50 * scale), int(self.screen_height - 45 * scale), "Back", self.button_font)
    
    def handle_events(self, events: list, menu_manager=None) -> str | None:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.back_button.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.is_clicked(mouse_pos, True):
                    return "back"
        
        return None
    
    def draw(self) -> None:
        draw_gradient_background(self.screen)
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        
        title_font = pygame.font.SysFont("times", int(52 * scale))
        title_surf = title_font.render("Credits", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, int(50 * scale)))
        self.screen.blit(title_surf, title_rect)
        
        credits = [
            "Verdantide",
            "",
            "An openworld turn-based RPG",
            "Orxan Majidli",
            "Built with Python, Pygame & Tkinter and a little bit of lua",
        ]
        
        y = int(160 * scale)
        for line in credits:
            if line:
                surf = pygame.font.SysFont("times", int(24 * scale)).render(line, True, (200, 200, 220))
            else:
                surf = pygame.font.SysFont("times", int(18 * scale)).render(" ", True, (180, 180, 200))
            rect = surf.get_rect(center=(self.screen_width // 2, y))
            self.screen.blit(surf, rect)
            y += int(40 * scale)
        
        self.back_button.draw(self.screen)


class SettingsMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        
        self.settings = [
            ("Music", True),
            ("Sound Effects", True),
        ]
        
        self.toggles = {}
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        self.back_button = TextButton(int(50 * scale), int(self.screen_height - 45 * scale), "Back", self.button_font)
        self.fullscreen_btn = None
    
    def handle_events(self, events: list, menu_manager=None) -> str | None:
        mouse_pos = pygame.mouse.get_pos()
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        
        self.fullscreen_btn = TextButton(
            self.screen_width // 2, 
            int(300 * scale), 
            "Toggle Fullscreen", 
            self.button_font
        )
        
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.back_button.update(mouse_pos)
                self.fullscreen_btn.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.is_clicked(mouse_pos, True):
                    return "back"
                if self.fullscreen_btn.is_clicked(mouse_pos, True):
                    if menu_manager:
                        menu_manager.toggle_fullscreen()
        
        return None
    
    def draw(self) -> None:
        draw_gradient_background(self.screen)
        
        scale = min(self.screen_width / 960, self.screen_height / 640)
        
        title_font = pygame.font.SysFont("times", int(52 * scale))
        title_surf = title_font.render("Settings", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, int(50 * scale)))
        self.screen.blit(title_surf, title_rect)
        
        y = int(160 * scale)
        for label, default in self.settings:
            label_surf = pygame.font.SysFont("times", int(24 * scale)).render(label, True, (200, 200, 220))
            self.screen.blit(label_surf, (self.screen_width // 2 - int(150 * scale), y))
            y += int(50 * scale)
        
        if self.fullscreen_btn:
            self.fullscreen_btn.draw(self.screen)
        
        self.back_button.draw(self.screen)


class MenuManager:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        self.fullscreen = False
        
        self.title_font = pygame.font.SysFont("times", 72)
        self.button_font = pygame.font.SysFont("times", 32)
        
        self.states = {}
        self.current_state = "main"
        
        self.states["main"] = MainMenuState(screen, self.title_font, self.button_font)
        self.states["play"] = PlayMenuState(screen, self.title_font, self.button_font)
        self.states["tutorial"] = TutorialMenuState(screen, self.title_font, self.button_font)
        self.states["achievements"] = AchievementsMenuState(screen, self.title_font, self.button_font)
        self.states["credits"] = CreditsMenuState(screen, self.title_font, self.button_font)
        self.states["settings"] = SettingsMenuState(screen, self.title_font, self.button_font)
    
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()
        
        self.states["main"] = MainMenuState(self.screen, self.title_font, self.button_font)
        self.states["play"] = PlayMenuState(self.screen, self.title_font, self.button_font)
        self.states["tutorial"] = TutorialMenuState(self.screen, self.title_font, self.button_font)
        self.states["achievements"] = AchievementsMenuState(self.screen, self.title_font, self.button_font)
        self.states["credits"] = CreditsMenuState(self.screen, self.title_font, self.button_font)
        self.states["settings"] = SettingsMenuState(self.screen, self.title_font, self.button_font)
    
    def handle_events(self) -> str | None:
        events = pygame.event.get()
        
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE and self.fullscreen:
                    self.toggle_fullscreen()
        
        state = self.states[self.current_state]
        
        if self.current_state == "settings":
            result = state.handle_events(events, self)
        else:
            result = state.handle_events(events)
        
        if result == "back":
            self.current_state = "main"
        elif result == "Play":
            self.current_state = "play"
        elif result == "Tutorial":
            self.current_state = "tutorial"
        elif result == "Achievements":
            self.current_state = "achievements"
        elif result == "Credits":
            self.current_state = "credits"
        elif result == "Settings":
            self.current_state = "settings"
        elif result and result.startswith("start:"):
            return result
        
        return None
    
    def draw(self) -> None:
        state = self.states[self.current_state]
        state.draw()


def run_menu() -> str | None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Verdantide")
    
    clock = pygame.time.Clock()
    
    menu = MenuManager(screen)
    running = True
    
    while running:
        result = menu.handle_events()
        menu.draw()
        
        if result == "quit":
            running = False
        elif result and result.startswith("start:"):
            biome = result.split(":")[1]
            pygame.quit()
            return f"game:{biome}"
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    return None


if __name__ == "__main__":
    run_menu()
