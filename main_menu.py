from __future__ import annotations

"""
main_menu.py

Modern sleek main menu for the RPG game.
"""

import pygame

pygame.init()


class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.base_color = (30, 35, 45)
        self.hover_color = (60, 80, 120)
        self.pressed_color = (80, 100, 150)
        self.current_color = self.base_color
        self.hovered = False
        self.pressed = False
        self.hover_scale = 1.0
        self.font = pygame.font.Font(None, 36)
    
    def update(self, mouse_pos: tuple[int, int]) -> None:
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        if self.pressed and self.hovered:
            self.current_color = self.pressed_color
            self.hover_scale = 0.95
        elif self.hovered:
            self.current_color = self.hover_color
            self.hover_scale = min(1.05, self.hover_scale + 0.02)
        else:
            self.current_color = self.base_color
            self.hover_scale = max(1.0, self.hover_scale - 0.02)
    
    def draw(self, surface: pygame.Surface) -> None:
        if self.hovered:
            glow_rect = self.rect.inflate(int(self.rect.width * 0.05), int(self.rect.height * 0.1))
            pygame.draw.rect(surface, (50, 80, 150), glow_rect, border_radius=12)
        
        pygame.draw.rect(surface, self.current_color, self.rect, border_radius=10)
        
        border_color = (100, 140, 220) if self.hovered else (60, 90, 160)
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=10)
        
        text_surf = self.font.render(self.text, True, (220, 225, 235))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def is_hovered(self) -> bool:
        return self.hovered


class ToggleButton:
    def __init__(self, x: int, y: int, width: int, height: int, label: str, initial_state: bool = True):
        self.label = label
        self.is_on = initial_state
        self.rect = pygame.Rect(x, y, width, height)
        self.switch_rect = pygame.Rect(x + width - 70, y + 8, 60, height - 16)
        self.hovered = False
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
    
    def update(self, mouse_pos: tuple[int, int]) -> None:
        self.hovered = self.rect.collidepoint(mouse_pos)
    
    def handle_click(self, mouse_pos: tuple[int, int]) -> bool:
        if self.switch_rect.collidepoint(mouse_pos):
            self.is_on = not self.is_on
            return True
        return False
    
    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (25, 30, 40), self.rect, border_radius=8)
        
        if self.hovered:
            pygame.draw.rect(surface, (35, 45, 60), self.rect, border_radius=8)
        
        label_surf = self.small_font.render(self.label, True, (180, 185, 200))
        surface.blit(label_surf, (self.rect.x + 15, self.rect.y + self.rect.height // 2 - 8))
        
        knob_x = self.switch_rect.x + 4 if self.is_on else self.switch_rect.x + self.switch_rect.width - 34
        
        pygame.draw.rect(surface, (40, 50, 80) if self.is_on else (80, 80, 100), 
                       self.switch_rect, border_radius=10)
        
        pygame.draw.circle(surface, (220, 230, 255) if self.is_on else (150, 155, 170), 
                         (knob_x + 15, self.switch_rect.centery), 13)
        
        if self.is_on:
            on_surf = self.small_font.render("ON", True, (180, 230, 150))
        else:
            on_surf = self.small_font.render("OFF", True, (150, 150, 160))
        on_rect = on_surf.get_rect(center=(self.switch_rect.centerx, self.switch_rect.centery))
        surface.blit(on_surf, on_rect)


class MainMenu:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        self.buttons = []
        self.running = True
        
        center_x = self.screen_width // 2
        button_width = 280
        button_height = 55
        start_y = 180
        spacing = 70
        
        menu_items = ["Play", "Customize", "Tutorial", "Achievements", "Credits", "Settings"]
        
        for i, text in enumerate(menu_items):
            y = start_y + i * spacing
            btn = Button(center_x - button_width // 2, y, button_width, button_height, text)
            self.buttons.append(btn)
    
    def handle_events(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return "quit"
            
            if event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
                for btn in self.buttons:
                    btn.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for btn in self.buttons:
                    if btn.rect.collidepoint(mouse_pos):
                        btn.pressed = True
            
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_pos = pygame.mouse.get_pos()
                for btn in self.buttons:
                    if btn.rect.collidepoint(mouse_pos) and btn.pressed:
                        btn.pressed = False
                        return btn.text
                    btn.pressed = False
        
        return None
    
    def draw(self) -> None:
        self.screen.fill((12, 15, 25))
        
        for i in range(5):
            alpha = 15 - i * 3
            glow = pygame.Surface((self.screen_width, 150), pygame.SRCALPHA)
            pygame.draw.rect(glow, (40, 80, 180, max(0, alpha)), 
                          (0, 50 + i * 10, self.screen_width, 100 - i * 15), border_radius=20)
            self.screen.blit(glow, (0, 0))
        
        title_font = pygame.font.Font(None, 80)
        title = title_font.render("MANGA RPG", True, (100, 150, 255))
        title_rect = title.get_rect(center=(self.screen_width // 2, 80))
        shadow = title_font.render("MANGA RPG", True, (40, 50, 100))
        shadow_rect = title_rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(title, title_rect)
        
        subtitle = pygame.font.Font(None, 28).render("Open World Adventure", True, (150, 160, 180))
        subtitle_rect = subtitle.get_rect(center=(self.screen_width // 2, 130))
        self.screen.blit(subtitle, subtitle_rect)
        
        for btn in self.buttons:
            btn.draw(self.screen)
        
        version = pygame.font.Font(None, 20).render("v1.0.0", True, (80, 90, 110))
        self.screen.blit(version, (15, self.screen_height - 30))


class SubMenu:
    def __init__(self, screen: pygame.Surface, title: str, on_back: str):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        self.title = title
        self.on_back = on_back
        self.running = True
        self.buttons = []
        
        self.back_btn = Button(20, self.screen_height - 60, 120, 45, "Back")
        self.buttons.append(self.back_btn)
    
    def handle_events(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return "quit"
            
            if event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
                for btn in self.buttons:
                    btn.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for btn in self.buttons:
                    if btn.rect.collidepoint(mouse_pos):
                        btn.pressed = True
            
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_pos = pygame.mouse.get_pos()
                for btn in self.buttons:
                    if btn.rect.collidepoint(mouse_pos) and btn.pressed:
                        btn.pressed = False
                        if btn.text == "Back":
                            return self.on_back
                        return btn.text
                    btn.pressed = False
        
        return None
    
    def draw(self) -> None:
        self.screen.fill((12, 15, 25))
        
        header = pygame.Surface((self.screen_width, 90), pygame.SRCALPHA)
        pygame.draw.rect(header, (20, 25, 40), header.get_rect(), border_radius=15)
        pygame.draw.line(header, (60, 100, 180), (30, 88), (self.screen_width - 30, 88), 2)
        self.screen.blit(header, (0, 0))
        
        title_font = pygame.font.Font(None, 52)
        title = title_font.render(self.title, True, (200, 210, 230))
        title_rect = title.get_rect(center=(self.screen_width // 2, 50))
        self.screen.blit(title, title_rect)
        
        for btn in self.buttons:
            btn.draw(self.screen)


class PlayMenu(SubMenu):
    def __init__(self, screen: pygame.Surface, on_back: str, on_start: str):
        super().__init__(screen, "Play", on_back)
        self.on_start = on_start
        
        center_x = self.screen_width // 2
        self.new_game_btn = Button(center_x - 140, 160, 280, 60, "New Game")
        self.continue_btn = Button(center_x - 140, 240, 280, 60, "Continue")
        self.buttons.extend([self.new_game_btn, self.continue_btn])
    
    def handle_events(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return "quit"
            
            if event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
                for btn in self.buttons:
                    btn.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for btn in self.buttons:
                    if btn.rect.collidepoint(mouse_pos):
                        btn.pressed = True
            
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_pos = pygame.mouse.get_pos()
                for btn in self.buttons:
                    if btn.rect.collidepoint(mouse_pos) and btn.pressed:
                        btn.pressed = False
                        if btn.text == "Back":
                            return self.on_back
                        elif btn.text in ["New Game", "Continue"]:
                            return self.on_start
                    btn.pressed = False
        
        return None
    
    def draw(self) -> None:
        super().draw()
        
        hint = pygame.font.Font(None, 24).render("Start a new adventure or continue where you left off.", True, (130, 140, 160))
        hint_rect = hint.get_rect(center=(self.screen_width // 2, 340))
        self.screen.blit(hint, hint_rect)


class CustomizeMenu(SubMenu):
    def __init__(self, screen: pygame.Surface, on_back: str):
        super().__init__(screen, "Customize", on_back)
    
    def draw(self) -> None:
        super().draw()
        
        center = (self.screen_width // 2, self.screen_height // 2)
        
        placeholder = pygame.font.Font(None, 36).render("Character Customization", True, (150, 160, 180))
        placeholder_rect = placeholder.get_rect(center=(center[0], center[1] - 30))
        self.screen.blit(placeholder, placeholder_rect)
        
        coming = pygame.font.Font(None, 28).render("(Coming Soon)", True, (100, 110, 130))
        coming_rect = coming.get_rect(center=(center[0], center[1] + 20))
        self.screen.blit(coming, coming_rect)


class TutorialMenu(SubMenu):
    def __init__(self, screen: pygame.Surface, on_back: str):
        super().__init__(screen, "Tutorial", on_back)
        
        self.tutorials = [
            ("Movement", "WASD or Arrow Keys to move around"),
            ("Combat", "Random encounters trigger turn-based battles"),
            ("Skills", "Each skill costs SP and has cooldowns"),
            ("Elements", "Fire > Ice > Wind > Fire"),
            ("Break", "Fill the break gauge to stun enemies!"),
        ]
    
    def draw(self) -> None:
        super().draw()
        
        y = 140
        for title, desc in self.tutorials:
            t_surf = pygame.font.Font(None, 30).render(title, True, (100, 150, 255))
            self.screen.blit(t_surf, (100, y))
            
            d_surf = pygame.font.Font(None, 24).render(desc, True, (160, 170, 190))
            self.screen.blit(d_surf, (100, y + 32))
            y += 80


class AchievementsMenu(SubMenu):
    def __init__(self, screen: pygame.Surface, on_back: str):
        super().__init__(screen, "Achievements", on_back)
    
    def draw(self) -> None:
        super().draw()
        
        center = (self.screen_width // 2, self.screen_height // 2)
        
        placeholder = pygame.font.Font(None, 36).render("Achievements System", True, (150, 160, 180))
        placeholder_rect = placeholder.get_rect(center=(center[0], center[1] - 30))
        self.screen.blit(placeholder, placeholder_rect)
        
        coming = pygame.font.Font(None, 28).render("(Coming Soon)", True, (100, 110, 130))
        coming_rect = coming.get_rect(center=(center[0], center[1] + 20))
        self.screen.blit(coming, coming_rect)


class CreditsMenu(SubMenu):
    def __init__(self, screen: pygame.Surface, on_back: str):
        super().__init__(screen, "Credits", on_back)
        
        self.credits = [
            ("MANGA RPG", 52, (100, 150, 255)),
            ("An Open World Adventure", 28, (180, 190, 210)),
            ("", 20, (0, 0, 0)),
            ("Created with Python & Pygame", 26, (150, 160, 180)),
            ("", 20, (0, 0, 0)),
            ("Special Thanks", 34, (200, 180, 100)),
            ("OpenCode AI Assistant", 24, (150, 160, 180)),
            ("Tiled Map Editor", 24, (150, 160, 180)),
            ("", 20, (0, 0, 0)),
            ("2024-2026", 26, (100, 110, 130)),
        ]
    
    def draw(self) -> None:
        super().draw()
        
        y = 140
        for text, size, color in self.credits:
            if text:
                surf = pygame.font.Font(None, size).render(text, True, color)
                rect = surf.get_rect(center=(self.screen_width // 2, y))
                self.screen.blit(surf, rect)
            y += size + 12


class SettingsMenu(SubMenu):
    def __init__(self, screen: pygame.Surface, on_back: str):
        super().__init__(screen, "Settings", on_back)
        
        self.settings = {
            "Music Volume": True,
            "SFX Volume": True,
            "Fullscreen": False,
            "VSync": True,
            "Auto-Save": True,
            "Show FPS": False,
        }
        
        self.toggle_buttons: list[ToggleButton] = []
        self.buttons = []
        
        self.back_btn = Button(20, 20, 120, 45, "Back")
        self.buttons.append(self.back_btn)
        
        self._create_toggles()
    
    def _create_toggles(self) -> None:
        self.toggle_buttons = []
        
        categories = [
            ("Sound", ["Music Volume", "SFX Volume"]),
            ("Graphics", ["Fullscreen", "VSync"]),
            ("Gameplay", ["Auto-Save", "Show FPS"]),
        ]
        
        y = 140
        for category, items in categories:
            for item in items:
                toggle = ToggleButton(100, y, 350, 45, item, self.settings.get(item, True))
                self.toggle_buttons.append(toggle)
                y += 55
            y += 10
    
    def handle_events(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return "quit"
            
            if event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
                for btn in self.buttons:
                    btn.update(mouse_pos)
                for toggle in self.toggle_buttons:
                    toggle.update(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                for btn in self.buttons:
                    if btn.rect.collidepoint(mouse_pos):
                        btn.pressed = True
            
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_pos = event.pos
                for btn in self.buttons:
                    if btn.rect.collidepoint(mouse_pos) and btn.pressed:
                        btn.pressed = False
                        if btn.text == "Back":
                            return self.on_back
                    btn.pressed = False
                
                for toggle in self.toggle_buttons:
                    if toggle.handle_click(mouse_pos):
                        self.settings[toggle.label] = toggle.is_on
        
        return None
    
    def draw(self) -> None:
        self.screen.fill((12, 15, 25))
        
        header = pygame.Surface((self.screen_width, 90), pygame.SRCALPHA)
        pygame.draw.rect(header, (20, 25, 40), header.get_rect(), border_radius=15)
        pygame.draw.line(header, (60, 100, 180), (30, 88), (self.screen_width - 30, 88), 2)
        self.screen.blit(header, (0, 0))
        
        title_font = pygame.font.Font(None, 52)
        title = title_font.render("Settings", True, (200, 210, 230))
        title_rect = title.get_rect(center=(self.screen_width // 2, 50))
        self.screen.blit(title, title_rect)
        
        y = 140
        categories = [
            ("Sound", ["Music Volume", "SFX Volume"]),
            ("Graphics", ["Fullscreen", "VSync"]),
            ("Gameplay", ["Auto-Save", "Show FPS"]),
        ]
        
        for category, items in categories:
            cat_surf = pygame.font.Font(None, 32).render(category, True, (100, 150, 255))
            self.screen.blit(cat_surf, (100, y))
            y += 40
            
            for item in items:
                for toggle in self.toggle_buttons:
                    if toggle.label == item:
                        toggle.rect.y = y
                        toggle.switch_rect.y = y + 8
                        toggle.draw(self.screen)
                        break
                y += 55
            y += 15
        
        for btn in self.buttons:
            btn.draw(self.screen)


def run_menu() -> str | None:
    pygame.init()
    screen = pygame.display.set_mode((960, 640))
    pygame.display.set_caption("Manga RPG - Main Menu")
    
    clock = pygame.time.Clock()
    
    current_menu = "main"
    menu_stack = []
    
    main_menu = MainMenu(screen)
    play_menu = None
    customize_menu = None
    tutorial_menu = None
    achievements_menu = None
    credits_menu = None
    settings_menu = None
    
    running = True
    
    while running:
        result = None
        
        if current_menu == "main":
            result = main_menu.handle_events()
            main_menu.draw()
            
            if result == "Play":
                play_menu = PlayMenu(screen, "main", "game")
                current_menu = "play"
            elif result == "Customize":
                customize_menu = CustomizeMenu(screen, "main")
                current_menu = "customize"
            elif result == "Tutorial":
                tutorial_menu = TutorialMenu(screen, "main")
                current_menu = "tutorial"
            elif result == "Achievements":
                achievements_menu = AchievementsMenu(screen, "main")
                current_menu = "achievements"
            elif result == "Credits":
                credits_menu = CreditsMenu(screen, "main")
                current_menu = "credits"
            elif result == "Settings":
                settings_menu = SettingsMenu(screen, "main")
                current_menu = "settings"
            elif result == "quit":
                running = False
        
        elif current_menu == "play":
            result = play_menu.handle_events()
            play_menu.draw()
            
            if result == "main":
                play_menu = None
                current_menu = "main"
            elif result == "game":
                running = False
        
        elif current_menu == "customize":
            result = customize_menu.handle_events()
            customize_menu.draw()
            
            if result == "main":
                customize_menu = None
                current_menu = "main"
        
        elif current_menu == "tutorial":
            result = tutorial_menu.handle_events()
            tutorial_menu.draw()
            
            if result == "main":
                tutorial_menu = None
                current_menu = "main"
        
        elif current_menu == "achievements":
            result = achievements_menu.handle_events()
            achievements_menu.draw()
            
            if result == "main":
                achievements_menu = None
                current_menu = "main"
        
        elif current_menu == "credits":
            result = credits_menu.handle_events()
            credits_menu.draw()
            
            if result == "main":
                credits_menu = None
                current_menu = "main"
        
        elif current_menu == "settings":
            result = settings_menu.handle_events()
            settings_menu.draw()
            
            if result == "main":
                settings_menu = None
                current_menu = "main"
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    
    if result == "game" or (current_menu == "play" and not running):
        return "game"
    return None


if __name__ == "__main__":
    result = run_menu()
    if result == "game":
        print("Starting game...")
        from game_modes_pygame import run_game
        run_game()
