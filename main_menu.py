from __future__ import annotations

import pygame

pygame.init()

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640


def draw_gradient_background(screen: pygame.Surface):
    """Draw gradient from dusty pink/orange at top to deep purple at bottom."""
    colors = [
        (200, 130, 120),  # dusty pink
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
    """Draw mountain silhouettes."""
    # Mountain 1 (large, left)
    pygame.draw.polygon(screen, (30, 15, 45), [
        (0, SCREEN_HEIGHT),
        (150, SCREEN_HEIGHT - 200),
        (300, SCREEN_HEIGHT - 350),
        (450, SCREEN_HEIGHT - 150),
        (600, SCREEN_HEIGHT),
    ])
    
    # Mountain 2 (medium, center-right)
    pygame.draw.polygon(screen, (25, 12, 40), [
        (400, SCREEN_HEIGHT),
        (550, SCREEN_HEIGHT - 180),
        (700, SCREEN_HEIGHT - 320),
        (850, SCREEN_HEIGHT - 220),
        (960, SCREEN_HEIGHT),
    ])
    
    # Mountain 3 (small, far right)
    pygame.draw.polygon(screen, (20, 10, 35), [
        (800, SCREEN_HEIGHT),
        (880, SCREEN_HEIGHT - 120),
        (960, SCREEN_HEIGHT),
    ])


class TextButton:
    """Simple text button with hover effects."""
    
    def __init__(self, x: int, y: int, text: str, font: pygame.font.Font):
        self.text = text
        self.base_font = font
        self.x = x
        self.y = y
        self.hovered = False
        self.base_color = (255, 255, 255)
        self.hover_color = (255, 215, 140)  # soft gold
    
    def update(self, mouse_pos: tuple[int, int]) -> None:
        width, height = self.base_font.size(self.text)
        
        self.hovered = (
            mouse_pos[0] >= self.x - width // 2 and
            mouse_pos[0] <= self.x + width // 2 and
            mouse_pos[1] >= self.y - height // 2 and
            mouse_pos[1] <= self.y + height // 2
        )
    
    def draw(self, screen: pygame.Surface) -> None:
        # Scale effect on hover
        scale = 1.1 if self.hovered else 1.0
        color = self.hover_color if self.hovered else self.base_color
        
        # Scale font
        scaled_size = int(32 * scale)
        scaled_font = pygame.font.SysFont("times", scaled_size)
        
        # Draw shadow
        shadow_surf = scaled_font.render(self.text, True, (20, 10, 30))
        shadow_rect = shadow_surf.get_rect(center=(self.x + 2, self.y + 2))
        screen.blit(shadow_surf, shadow_rect)
        
        # Draw text
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


class MenuState:
    """Base class for menu states."""
    
    def __init__(self, screen: pygame.Surface, title_font: pygame.font.Font, button_font: pygame.font.Font):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        self.title_font = title_font
        self.button_font = button_font
        self.buttons = []
        self.back_button = None
    
    def handle_events(self, events: list) -> str | None:
        """Handle events. Return new state name or None."""
        return None
    
    def draw(self) -> None:
        pass


class MainMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        
        # Buttons: Play, Tutorial, Achievements, Credits, Settings
        menu_items = ["Play", "Tutorial", "Achievements", "Credits", "Settings"]
        
        start_y = 220
        spacing = 60
        
        for i, text in enumerate(menu_items):
            y = start_y + i * spacing
            btn = TextButton(self.screen_width // 2, y, text, self.button_font)
            self.buttons.append(btn)
    
    def handle_events(self, events: list) -> str | None:
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
        
        # Title
        title = "Verdantide"
        
        shadow_surf = self.title_font.render(title, True, (20, 10, 30))
        shadow_rect = shadow_surf.get_rect(center=(self.screen_width // 2 + 3, 63))
        self.screen.blit(shadow_surf, shadow_rect)
        
        title_surf = self.title_font.render(title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, 60))
        self.screen.blit(title_surf, title_rect)
        
        for btn in self.buttons:
            btn.draw(self.screen)


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
        self.biomes_per_page = 5
        self.biome_page = 0
        
        # Navigation buttons
        self.prev_btn = TextButton(self.screen_width // 2 - 80, 200, "<", self.button_font)
        self.next_btn = TextButton(self.screen_width // 2 + 80, 200, ">", self.button_font)
        
        # Biome buttons
        self.biome_buttons = []
        for i in range(self.biomes_per_page):
            y = 260 + i * 55
            btn = TextButton(self.screen_width // 2, y, "", self.button_font)
            self.biome_buttons.append(btn)
        
        # Start game button
        self.start_btn = TextButton(self.screen_width // 2, 530, "Start Game", self.button_font)
        
        # Back button
        self.back_button = TextButton(60, self.screen_height - 45, "Back", self.button_font)
    
    def handle_events(self, events: list) -> str | None:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                for btn in [self.prev_btn, self.next_btn, self.back_button, self.start_btn]:
                    btn.update(mouse_pos)
                for btn in self.biome_buttons:
                    btn.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Check back button
                if self.back_button.is_clicked(mouse_pos, True):
                    return "back"
                
                # Check navigation
                if self.prev_btn.is_clicked(mouse_pos, True):
                    self.biome_page = max(0, self.biome_page - 1)
                if self.next_btn.is_clicked(mouse_pos, True):
                    max_page = (len(self.biomes) - 1) // self.biomes_per_page
                    self.biome_page = min(max_page, self.biome_page + 1)
                
                # Check biome selection
                for i, btn in enumerate(self.biome_buttons):
                    if btn.is_clicked(mouse_pos, True):
                        idx = self.biome_page * self.biomes_per_page + i
                        if idx < len(self.biomes):
                            self.selected_biome = idx
                
                # Check start button
                if self.start_btn.is_clicked(mouse_pos, True):
                    return f"start:{self.biomes[self.selected_biome]}"
        
        return None
    
    def draw(self) -> None:
        draw_gradient_background(self.screen)
        draw_mountains(self.screen)
        
        # Title
        title_surf = self.title_font.render("Select Biome", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, 60))
        self.screen.blit(title_surf, title_rect)
        
        # Navigation arrows
        self.prev_btn.draw(self.screen)
        self.next_btn.draw(self.screen)
        
        # Biome buttons
        start_idx = self.biome_page * self.biomes_per_page
        for i in range(self.biomes_per_page):
            idx = start_idx + i
            if idx < len(self.biomes):
                btn = self.biome_buttons[i]
                name = self.biome_names[idx]
                if idx == self.selected_biome:
                    btn.text = f"> {name} <"
                else:
                    btn.text = name
                btn.draw(self.screen)
        
        # Selected biome display
        selected_name = self.biome_names[self.selected_biome]
        info_font = pygame.font.SysFont("times", 20)
        info_surf = info_font.render(f"Selected: {selected_name}", True, (180, 180, 200))
        info_rect = info_surf.get_rect(center=(self.screen_width // 2, 510))
        self.screen.blit(info_surf, info_rect)
        
        # Start button
        self.start_btn.draw(self.screen)
        
        # Back button
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
        
        self.back_button = TextButton(60, self.screen_height - 45, "Back", self.button_font)
    
    def handle_events(self, events: list) -> str | None:
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
        
        # Title
        title_surf = self.title_font.render("Tutorial", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, 60))
        self.screen.blit(title_surf, title_rect)
        
        # Tutorial content
        y = 150
        for title, desc in self.tutorials:
            t_surf = self.button_font.render(title, True, (100, 150, 255))
            self.screen.blit(t_surf, (100, y))
            
            d_surf = pygame.font.SysFont("times", 20).render(desc, True, (180, 180, 200))
            self.screen.blit(d_surf, (120, y + 30))
            
            y += 70
        
        self.back_button.draw(self.screen)


class AchievementsMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        self.back_button = TextButton(60, self.screen_height - 45, "Back", self.button_font)
    
    def handle_events(self, events: list) -> str | None:
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
        
        title_surf = self.title_font.render("Achievements", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, 60))
        self.screen.blit(title_surf, title_rect)
        
        placeholder = pygame.font.SysFont("times", 24).render("No achievements yet!", True, (180, 180, 200))
        placeholder_rect = placeholder.get_rect(center=(self.screen_width // 2, 300))
        self.screen.blit(placeholder, placeholder_rect)
        
        self.back_button.draw(self.screen)


class CreditsMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        self.back_button = TextButton(60, self.screen_height - 45, "Back", self.button_font)
    
    def handle_events(self, events: list) -> str | None:
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
        
        title_surf = self.title_font.render("Credits", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, 60))
        self.screen.blit(title_surf, title_rect)
        
        credits = [
            "Verdantide",
            "",
            "A turn-based RPG",
            "",
            "Built with Python, Pygame & Tkinter",
        ]
        
        y = 200
        for line in credits:
            if line:
                surf = pygame.font.SysFont("times", 28).render(line, True, (200, 200, 220))
            else:
                surf = pygame.font.SysFont("times", 20).render(" ", True, (180, 180, 200))
            rect = surf.get_rect(center=(self.screen_width // 2, y))
            self.screen.blit(surf, rect)
            y += 40
        
        self.back_button.draw(self.screen)


class SettingsMenuState(MenuState):
    def __init__(self, screen, title_font, button_font):
        super().__init__(screen, title_font, button_font)
        
        self.settings = [
            ("Music", True),
            ("Sound Effects", True),
            ("Fullscreen", False),
        ]
        
        self.toggles = {}  # Will hold toggle states
        
        self.back_button = TextButton(60, self.screen_height - 45, "Back", self.button_font)
    
    def handle_events(self, events: list) -> str | None:
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
        
        title_surf = self.title_font.render("Settings", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, 60))
        self.screen.blit(title_surf, title_rect)
        
        # Placeholder settings
        y = 200
        for label, default in self.settings:
            label_surf = pygame.font.SysFont("times", 24).render(label, True, (200, 200, 220))
            self.screen.blit(label_surf, (self.screen_width // 2 - 150, y))
            y += 50
        
        self.back_button.draw(self.screen)


class MenuManager:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        
        self.title_font = pygame.font.SysFont("times", 72)
        self.button_font = pygame.font.SysFont("times", 32)
        
        self.states = {}
        self.current_state = "main"
        
        # Initialize all states
        self.states["main"] = MainMenuState(screen, self.title_font, self.button_font)
        self.states["play"] = PlayMenuState(screen, self.title_font, self.button_font)
        self.states["tutorial"] = TutorialMenuState(screen, self.title_font, self.button_font)
        self.states["achievements"] = AchievementsMenuState(screen, self.title_font, self.button_font)
        self.states["credits"] = CreditsMenuState(screen, self.title_font, self.button_font)
        self.states["settings"] = SettingsMenuState(screen, self.title_font, self.button_font)
    
    def handle_events(self) -> str | None:
        events = pygame.event.get()
        
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
        
        state = self.states[self.current_state]
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
            return result  # Return the biome to start the game
        
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
