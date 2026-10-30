"""
ui.py - Everything the player sees on top of the game world.

Classes:
- Fonts:          loads every font size once, at start-up
- Button:         mouse-clickable button with an animated hover glow
- ScreenEffects:  screen flash and screen shake for important events
- FloatingText:   popups such as "+10" that drift upwards and fade
- MenuDecor:      animated ship and floating orbs on the title screen

Drawing functions:
- draw_text(), draw_glow_text(), draw_panel(), draw_rect_glow()
- draw_hud(), draw_title_screen(), draw_instructions(),
  draw_pause_overlay(), draw_game_over()
"""

import math
import random

import pygame

import settings
from entities import EnergyOrb, Player

# Futuristic-looking fonts first; pygame falls back to a default font if none exist.
FONT_NAMES = "bahnschrift,trebuchetms,verdana,arial"

INSTRUCTION_RULES = [
    "Collect cyan energy orbs for +10 points each.",
    "Avoid violet asteroids. Each hit costs one life and 5 points.",
    "Golden Time Crystals give +25 points and slow all hazards for 5 seconds.",
    "Blue shield pick-ups absorb the next asteroid hit.",
    "You start with 3 lives. The game ends when lives run out or the timer reaches zero.",
    "The galaxy grows more dangerous as time and score increase.",
]

INSTRUCTION_CONTROLS = [
    "Move: Arrow keys or W A S D",
    "Pause and resume: P or Escape",
    "Mute and unmute sound: M",
    "Start or restart: Enter",
    "Save a screenshot: F12",
]


def lerp_color(color_a, color_b, amount):
    """Blend two colours. amount 0.0 gives color_a, 1.0 gives color_b."""
    return tuple(int(a + (b - a) * amount) for a, b in zip(color_a, color_b))


class Fonts:
    """Every font size used by the game, created once at start-up."""

    def __init__(self):
        self.title = pygame.font.SysFont(FONT_NAMES, 64, bold=True)
        self.heading = pygame.font.SysFont(FONT_NAMES, 44, bold=True)
        self.large = pygame.font.SysFont(FONT_NAMES, 28, bold=True)
        self.medium = pygame.font.SysFont(FONT_NAMES, 22)
        self.small = pygame.font.SysFont(FONT_NAMES, 17)
        self.hud = pygame.font.SysFont(FONT_NAMES, 24, bold=True)


# ----------------------------------------------------------------------------
# Drawing helpers
# ----------------------------------------------------------------------------
def draw_text(surface, text, font, color, position, anchor="center"):
    """
    Draw one line of text. 'anchor' says which point of the text sits at
    'position', for example "center", "topleft" or "midright".
    """
    image = font.render(text, True, color)
    rect = image.get_rect()
    setattr(rect, anchor, (int(position[0]), int(position[1])))   # Rect needs whole pixels
    surface.blit(image, rect)
    return rect


def draw_glow_text(surface, text, font, color, glow_color, position):
    """Text with a coloured outline behind it, for a neon look."""
    x, y = position
    for offset_x, offset_y in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        draw_text(surface, text, font, glow_color, (x + offset_x, y + offset_y))
    draw_text(surface, text, font, color, position)


def draw_panel(surface, rect, alpha=170):
    """A semi-transparent rounded panel used behind HUD text."""
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (*settings.PANEL, alpha), panel.get_rect(), border_radius=10)
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, settings.GREY, rect, width=1, border_radius=10)


def draw_rect_glow(surface, rect, color, strength):
    """A soft halo around a rectangle, made from several faded rounded rectangles."""
    pad = 12
    halo = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
    for ring in range(pad, 0, -2):              # outer rings first, brighter inner rings last
        fade = 1 - ring / pad                   # 0 at the outer edge, close to 1 near the button
        alpha = int(strength * (5 + 45 * fade * fade))
        ring_rect = pygame.Rect(0, 0, rect.width + ring * 2, rect.height + ring * 2)
        ring_rect.center = halo.get_rect().center
        pygame.draw.rect(halo, (*color, alpha), ring_rect, border_radius=12 + ring)
    surface.blit(halo, halo.get_rect(center=rect.center))


# ----------------------------------------------------------------------------
# Interactive and animated helpers
# ----------------------------------------------------------------------------
class Button:
    """A clickable button. Hovering makes it lift and glow with a smooth animation."""

    def __init__(self, label, center, action, size=(260, 54)):
        self.label = label
        self.action = action                  # text returned when the button is clicked
        self.rect = pygame.Rect(0, 0, size[0], size[1])
        self.rect.center = center
        self.hover_amount = 0.0               # animates between 0 (idle) and 1 (hovered)

    def update(self, mouse_pos, dt):
        target = 1.0 if self.rect.collidepoint(mouse_pos) else 0.0
        self.hover_amount += (target - self.hover_amount) * min(1.0, 12 * dt)

    def handle_event(self, event):
        """Return the button's action if it was clicked with the left mouse button."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return self.action
        return None

    def draw(self, surface, font):
        lifted = self.rect.move(0, -int(3 * self.hover_amount))
        if self.hover_amount > 0.02:
            draw_rect_glow(surface, lifted, settings.ELECTRIC_CYAN, self.hover_amount)
        body = lerp_color(settings.PANEL, (22, 62, 92), self.hover_amount)
        pygame.draw.rect(surface, body, lifted, border_radius=12)
        border = lerp_color(settings.GREY, settings.ELECTRIC_CYAN, self.hover_amount)
        pygame.draw.rect(surface, border, lifted, width=2, border_radius=12)
        text_color = lerp_color(settings.WHITE, settings.ELECTRIC_CYAN, self.hover_amount)
        draw_text(surface, self.label, font, text_color, lifted.center)


class ScreenEffects:
    """Screen flash (a coloured overlay) and screen shake for important events."""

    def __init__(self):
        self.flash_color = settings.CORAL_RED
        self.flash_timer = 0.0
        self.flash_duration = 1.0
        self.shake_timer = 0.0
        self.shake_duration = 1.0
        self.shake_strength = 0.0
        self.overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)

    def flash(self, color, duration=0.25):
        self.flash_color = color
        self.flash_timer = duration
        self.flash_duration = duration

    def shake(self, strength=8, duration=0.3):
        self.shake_strength = strength
        self.shake_timer = duration
        self.shake_duration = duration

    def update(self, dt):
        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.shake_timer = max(0.0, self.shake_timer - dt)

    def shake_offset(self):
        """A random pixel offset for this frame. The shake gets weaker over time."""
        if self.shake_timer <= 0:
            return (0, 0)
        amount = self.shake_strength * (self.shake_timer / self.shake_duration)
        return (round(random.uniform(-amount, amount)), round(random.uniform(-amount, amount)))

    def draw_flash(self, surface):
        if self.flash_timer > 0:
            ratio = self.flash_timer / self.flash_duration       # 1.0 at the start, 0.0 at the end
            self.overlay.fill((*self.flash_color, int(120 * ratio)))
            surface.blit(self.overlay, (0, 0))


class FloatingText:
    """A popup such as '+10' that drifts upwards and fades out."""

    def __init__(self, text, x, y, color, life=0.9):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.life = life
        self.max_life = life

    def update(self, dt):
        """Returns False when the popup has finished and should be removed."""
        self.y -= 40 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface, font):
        ratio = max(0.0, self.life / self.max_life)
        color = lerp_color(settings.MIDNIGHT_NAVY, self.color, ratio)   # fade out
        draw_text(surface, self.text, font, color, (int(self.x), int(self.y)))


class MenuDecor:
    """Animated ship and floating orbs on the title screen. Decoration only."""

    def __init__(self):
        self.ship = Player()
        self.orbs = []
        self.time = 0.0
        self.spawn_timer = 0.0

    def update(self, dt):
        self.time += dt
        self.ship.update(dt)
        # The ship bobs gently on the left side of the screen, away from the buttons.
        self.ship.x = 170 + math.sin(self.time * 0.9) * 25
        self.ship.y = 340 + math.sin(self.time * 1.7) * 30
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.orbs) < 10:
            self.orbs.append(EnergyOrb(random.uniform(700, 900), -12))
            self.spawn_timer = 0.6
        for orb in self.orbs:
            orb.update(dt)
        self.orbs = [orb for orb in self.orbs if orb.alive]

    def draw(self, surface):
        for orb in self.orbs:
            orb.draw(surface)
        self.ship.draw(surface)


# ----------------------------------------------------------------------------
# HUD (drawn over the gameplay)
# ----------------------------------------------------------------------------
def draw_hud(surface, fonts, score, lives, time_left, level, high_score,
             shield_active, slow_time_left, muted):
    """Draw the score, timer, lives, difficulty level and active power-up indicators."""
    width, height = settings.WIDTH, settings.HEIGHT

    # Top-left: score and best score.
    left = pygame.Rect(12, 12, 230, 84)
    draw_panel(surface, left)
    draw_text(surface, "SCORE", fonts.small, settings.GREY, (left.x + 14, left.y + 10), "topleft")
    draw_text(surface, str(score), fonts.hud, settings.ELECTRIC_CYAN, (left.x + 14, left.y + 30), "topleft")
    draw_text(surface, f"BEST {high_score}", fonts.small, settings.GOLDEN_YELLOW,
              (left.x + 14, left.y + 60), "topleft")

    # Top-centre: countdown timer, turns red during the last 10 seconds.
    seconds = max(0, math.ceil(time_left))
    timer_rect = pygame.Rect(0, 12, 170, 56)
    timer_rect.centerx = width // 2
    draw_panel(surface, timer_rect)
    timer_color = settings.CORAL_RED if seconds <= 10 else settings.WHITE
    draw_text(surface, f"{seconds // 60}:{seconds % 60:02d}", fonts.hud, timer_color, timer_rect.center)

    # Top-right: lives as small ship icons, plus the difficulty level.
    right = pygame.Rect(width - 12 - 230, 12, 230, 84)
    draw_panel(surface, right)
    draw_text(surface, "LIVES", fonts.small, settings.GREY, (right.x + 14, right.y + 10), "topleft")
    for index in range(settings.START_LIVES):
        cx = right.x + 90 + index * 30
        cy = right.y + 22
        points = [(cx, cy - 8), (cx + 8, cy + 7), (cx - 8, cy + 7)]
        if index < lives:
            pygame.draw.polygon(surface, settings.ELECTRIC_CYAN, points)
        else:
            pygame.draw.polygon(surface, settings.GREY, points, 2)
    draw_text(surface, f"DIFFICULTY  LEVEL {level}", fonts.small, settings.WHITE,
              (right.x + 14, right.y + 60), "topleft")

    # Bottom-left: active power-up indicators.
    if shield_active:
        shield_rect = pygame.Rect(12, height - 74, 220, 30)
        draw_panel(surface, shield_rect)
        draw_text(surface, "SHIELD ACTIVE", fonts.small, settings.SHIELD_BLUE, shield_rect.center)

    if slow_time_left > 0:
        slow_rect = pygame.Rect(12, height - 38, 220, 26)
        draw_panel(surface, slow_rect)
        draw_text(surface, "TIME SLOW", fonts.small, settings.GOLDEN_YELLOW,
                  (slow_rect.x + 8, slow_rect.centery), "midleft")
        bar_back = pygame.Rect(slow_rect.x + 104, slow_rect.centery - 4, 108, 8)
        pygame.draw.rect(surface, settings.GREY, bar_back, border_radius=4)
        fraction = slow_time_left / settings.CRYSTAL_SLOW_TIME
        bar_fill = pygame.Rect(bar_back.x, bar_back.y, int(bar_back.width * fraction), bar_back.height)
        pygame.draw.rect(surface, settings.GOLDEN_YELLOW, bar_fill, border_radius=4)

    # Bottom-right: sound status.
    sound_text = "SOUND OFF (M)" if muted else "SOUND ON (M)"
    draw_text(surface, sound_text, fonts.small, settings.GREY, (width - 12, height - 12), "bottomright")


# ----------------------------------------------------------------------------
# Full screens
# ----------------------------------------------------------------------------
def draw_title_screen(surface, fonts, buttons, high_score, time):
    """Title, buttons, high score and controls guide. The background is drawn by the caller."""
    width, height = settings.WIDTH, settings.HEIGHT
    bob = math.sin(time * 2) * 4                 # the title gently floats up and down

    draw_glow_text(surface, "LUMI", fonts.title, settings.ELECTRIC_CYAN,
                   settings.VIOLET, (width // 2, 110 + bob))
    draw_text(surface, "THE COSMIC COLLECTOR", fonts.medium, settings.GOLDEN_YELLOW,
              (width // 2, 168))

    for button in buttons:
        button.draw(surface, fonts.large)

    draw_text(surface, f"HIGH SCORE  {high_score}", fonts.large, settings.GOLDEN_YELLOW,
              (width // 2, 500))

    guide = pygame.Rect(0, 0, 680, 56)
    guide.center = (width // 2, 584)
    draw_panel(surface, guide)
    draw_text(surface, "Move: Arrows or WASD     Pause: P or Esc     Mute: M     Start: Enter",
              fonts.small, settings.WHITE, guide.center)


def draw_instructions(surface, fonts, back_button):
    """The 'How to play' screen with the rules and controls."""
    width = settings.WIDTH
    draw_glow_text(surface, "HOW TO PLAY", fonts.heading, settings.ELECTRIC_CYAN,
                   settings.VIOLET, (width // 2, 70))

    for index, line in enumerate(INSTRUCTION_RULES):
        draw_text(surface, line, fonts.medium, settings.WHITE, (width // 2, 140 + index * 42))

    draw_text(surface, "CONTROLS", fonts.large, settings.GOLDEN_YELLOW, (width // 2, 400))
    for index, line in enumerate(INSTRUCTION_CONTROLS):
        draw_text(surface, line, fonts.medium, settings.WHITE, (width // 2, 436 + index * 30))

    back_button.draw(surface, fonts.large)


def draw_pause_overlay(surface, fonts):
    """Dim the frozen game and show the pause message."""
    shade = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
    shade.fill((*settings.MIDNIGHT_NAVY, 170))
    surface.blit(shade, (0, 0))
    draw_glow_text(surface, "PAUSED", fonts.heading, settings.WHITE,
                   settings.ELECTRIC_CYAN, (settings.WIDTH // 2, settings.HEIGHT // 2 - 20))
    draw_text(surface, "Press P or Escape to resume", fonts.medium, settings.GREY,
              (settings.WIDTH // 2, settings.HEIGHT // 2 + 30))


def draw_game_over(surface, fonts, time, final_score, high_score, orbs_collected,
                   collisions, new_record, buttons):
    """Game-over screen with a flickering heading, the final stats and the buttons."""
    width, height = settings.WIDTH, settings.HEIGHT

    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    shade.fill((*settings.MIDNIGHT_NAVY, 190))
    surface.blit(shade, (0, 0))

    # Visual effect: the heading flickers sideways and pulses its glow.
    flicker = math.sin(time * 25) * 2
    draw_glow_text(surface, "GAME OVER", fonts.title, settings.CORAL_RED,
                   (120, 30, 50), (width // 2 + flicker, 110))

    stats = pygame.Rect(0, 0, 440, 230)
    stats.center = (width // 2, 320)
    draw_panel(surface, stats)
    rows = [
        ("Final score", str(final_score)),
        ("Highest score", str(high_score)),
        ("Energy orbs collected", str(orbs_collected)),
        ("Asteroid collisions survived", str(collisions)),
    ]
    for index, (label, value) in enumerate(rows):
        y = stats.y + 36 + index * 46
        draw_text(surface, label, fonts.medium, settings.GREY, (stats.x + 24, y), "midleft")
        draw_text(surface, value, fonts.large, settings.WHITE, (stats.right - 24, y), "midright")

    if new_record:
        pulse = 0.5 + 0.5 * math.sin(time * 5)
        color = lerp_color(settings.GOLDEN_YELLOW, settings.WHITE, pulse * 0.5)
        draw_text(surface, "NEW HIGH SCORE!", fonts.large, color, (width // 2, 455))

    for button in buttons:
        button.draw(surface, fonts.large)
