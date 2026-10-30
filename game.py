"""
game.py - The GameManager, the brain of LUMI.

It owns the game states (menu, instructions, playing, paused, game over),
applies the gameplay rules, spawns objects, checks collisions, saves the high
score, and asks entities.py and ui.py to draw everything.

The main loop in main.py calls three methods every frame:
    handle_event(event)  -> react to keyboard and mouse input
    update(dt)           -> move objects and apply the rules
    draw()               -> render the current state to the screen
"""

import json
import os
import random
from datetime import datetime

import pygame

import settings
from audio import AudioManager
from entities import (Asteroid, EnergyOrb, Player, ShieldPowerUp, Starfield,
                      TimeCrystal, circles_overlap, spawn_particles)
from ui import (Button, FloatingText, Fonts, MenuDecor, ScreenEffects,
                draw_game_over, draw_hud, draw_instructions, draw_pause_overlay,
                draw_title_screen)

# The five game states. The whole game is always in exactly one of them.
MENU = "menu"
INSTRUCTIONS = "instructions"
PLAYING = "playing"
PAUSED = "paused"
GAME_OVER = "game_over"


# ----------------------------------------------------------------------------
# High-score file
# ----------------------------------------------------------------------------
def load_high_score():
    """Read the best score from highscore.json. A missing or damaged file gives 0."""
    try:
        with open(settings.HIGHSCORE_FILE, "r", encoding="utf-8") as file:
            return int(json.load(file).get("high_score", 0))
    except (OSError, ValueError, AttributeError):
        return 0


def save_high_score(score):
    """Write the best score to highscore.json so it survives restarting the app."""
    try:
        with open(settings.HIGHSCORE_FILE, "w", encoding="utf-8") as file:
            json.dump({"high_score": int(score)}, file, indent=4)
    except OSError:
        pass                          # the game keeps running even if saving fails


class GameManager:
    """Coordinates every part of the game. One instance lives for the whole session."""

    def __init__(self, screen):
        self.screen = screen
        self.scene = pygame.Surface((settings.WIDTH, settings.HEIGHT))  # drawn here, then shaken onto the screen
        self.fonts = Fonts()
        self.audio = AudioManager()
        self.audio.start_music()
        self.starfield = Starfield()
        self.decor = MenuDecor()
        self.effects = ScreenEffects()
        self.high_score = load_high_score()

        self.state = MENU
        self.running = True
        self.total_time = 0.0            # global clock for animations
        self.take_screenshot = False

        center_x = settings.WIDTH // 2
        self.menu_buttons = [
            Button("START GAME", (center_x, 280), "start"),
            Button("HOW TO PLAY", (center_x, 350), "instructions"),
            Button("QUIT", (center_x, 420), "quit"),
        ]
        self.back_button = Button("BACK", (center_x, 600), "menu")
        self.game_over_buttons = [
            Button("RESTART", (center_x, 500), "restart"),
            Button("MAIN MENU", (center_x, 570), "menu"),
        ]
        self.reset_game()

    # ------------------------------------------------------------------
    # Starting and resetting a match
    # ------------------------------------------------------------------
    def reset_game(self):
        """Put every gameplay value back to its starting state. The window is not recreated."""
        self.player = Player()
        self.orbs = []           # cyan energy orbs
        self.asteroids = []      # hazards
        self.powerups = []       # Time Crystals and shield pick-ups
        self.particles = []
        self.texts = []          # floating "+10" popups
        self.score = 0
        self.lives = settings.START_LIVES
        self.time_left = settings.GAME_DURATION
        self.elapsed = 0.0       # seconds played, used for difficulty
        self.level = 1
        self.orbs_collected = 0
        self.collisions = 0      # asteroid hits Lumi survived
        self.slow_timer = 0.0    # seconds of Time Crystal slow-motion left
        self.orb_timer = 0.0
        self.asteroid_timer = settings.ASTEROID_BASE_SPAWN
        self.crystal_timer = settings.CRYSTAL_SPAWN_INTERVAL
        self.shield_timer = settings.SHIELD_SPAWN_INTERVAL
        self.new_record = False

    def start_game(self):
        self.reset_game()
        self.state = PLAYING

    # ------------------------------------------------------------------
    # Input: keyboard and mouse events
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:          # the window's close button
            self.running = False
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_click(event)

    def _handle_key(self, key):
        # Keys that work in every state.
        if key == pygame.K_F12:
            self.take_screenshot = True
            return
        if key == pygame.K_m:
            self.audio.toggle_mute()
            return

        # Keys that depend on the current state.
        enter_keys = (pygame.K_RETURN, pygame.K_KP_ENTER)
        if self.state == MENU and key in enter_keys:
            self.start_game()
        elif self.state == INSTRUCTIONS and key == pygame.K_ESCAPE:
            self.state = MENU
        elif self.state == PLAYING and key in (pygame.K_p, pygame.K_ESCAPE):
            self.state = PAUSED
        elif self.state == PAUSED and key in (pygame.K_p, pygame.K_ESCAPE):
            self.state = PLAYING
        elif self.state == GAME_OVER and key in enter_keys:
            self.start_game()

    def _handle_click(self, event):
        if self.state == MENU:
            buttons = self.menu_buttons
        elif self.state == INSTRUCTIONS:
            buttons = [self.back_button]
        elif self.state == GAME_OVER:
            buttons = self.game_over_buttons
        else:
            return
        for button in buttons:
            action = button.handle_event(event)
            if action:
                self._run_action(action)
                return

    def _run_action(self, action):
        if action in ("start", "restart"):
            self.start_game()
        elif action == "instructions":
            self.state = INSTRUCTIONS
        elif action == "menu":
            self.state = MENU
        elif action == "quit":
            self.running = False

    # ------------------------------------------------------------------
    # Update: move objects and apply the rules every frame
    # ------------------------------------------------------------------
    def update(self, dt):
        self.total_time += dt
        if self.state == PAUSED:
            return                                 # the game is frozen while paused

        self.effects.update(dt)
        self.starfield.update(dt)
        mouse = pygame.mouse.get_pos()

        if self.state == MENU:
            self.decor.update(dt)
            self._update_buttons(self.menu_buttons, mouse, dt)
        elif self.state == INSTRUCTIONS:
            self._update_buttons([self.back_button], mouse, dt)
        elif self.state == PLAYING:
            self._update_playing(dt)
        elif self.state == GAME_OVER:
            self._update_buttons(self.game_over_buttons, mouse, dt)
            self._update_effects(dt)

    def _update_buttons(self, buttons, mouse, dt):
        for button in buttons:
            button.update(mouse, dt)

    def _update_effects(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]

    def _update_playing(self, dt):
        player = self.player

        # Movement: arrow keys or WASD. Pressed keys are read every frame.
        keys = pygame.key.get_pressed()
        direction_x = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        direction_y = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        player.move(direction_x, direction_y, dt)
        player.update(dt)
        spawn_particles(self.particles, player.x, player.y + 12, settings.ELECTRIC_CYAN, 1, speed=20, life=0.3)

        # Clocks and difficulty.
        self.elapsed += dt
        self.time_left -= dt
        self.slow_timer = max(0.0, self.slow_timer - dt)
        self.level = self._compute_level()

        self._spawn_objects(dt)

        # Move everything. While the Time Crystal is active, hazards move slower.
        hazard_speed = settings.CRYSTAL_SLOW_FACTOR if self.slow_timer > 0 else 1.0
        for orb in self.orbs:
            orb.update(dt)
        for item in self.powerups:
            item.update(dt)
        for rock in self.asteroids:
            rock.update(dt, hazard_speed)

        self._check_collisions()

        # Remove everything that was collected, hit, or left the screen.
        self.orbs = [orb for orb in self.orbs if orb.alive]
        self.powerups = [item for item in self.powerups if item.alive]
        self.asteroids = [rock for rock in self.asteroids if rock.alive]
        self._update_effects(dt)

        if self.time_left <= 0:
            self.time_left = 0
            self._end_game()

    # ------------------------------------------------------------------
    # Difficulty and spawning (custom mechanic 3)
    # ------------------------------------------------------------------
    def _compute_level(self):
        """Difficulty rises with time survived and with points scored."""
        by_time = int(self.elapsed / settings.LEVEL_TIME_STEP)
        by_score = self.score // settings.LEVEL_SCORE_STEP
        return min(settings.MAX_LEVEL, 1 + by_time + by_score)

    def _has_powerup(self, kind):
        return any(isinstance(item, kind) for item in self.powerups)

    def _spawn_objects(self, dt):
        level = self.level
        width = settings.WIDTH

        # Energy orbs: a steady stream, never more than MAX_ORBS on screen.
        self.orb_timer -= dt
        if self.orb_timer <= 0:
            self.orb_timer = settings.ORB_SPAWN_INTERVAL * random.uniform(0.7, 1.3)
            if len(self.orbs) < settings.MAX_ORBS:
                x = random.uniform(settings.ORB_RADIUS, width - settings.ORB_RADIUS)
                self.orbs.append(EnergyOrb(x, -settings.ORB_RADIUS))

        # Asteroids: higher levels mean faster spawns, faster rocks and more of them.
        self.asteroid_timer -= dt
        if self.asteroid_timer <= 0:
            interval = max(settings.ASTEROID_MIN_SPAWN,
                           settings.ASTEROID_BASE_SPAWN - settings.ASTEROID_SPAWN_DROP * (level - 1))
            self.asteroid_timer = interval * random.uniform(0.8, 1.2)
            max_hazards = min(settings.ASTEROID_MAX_CAP, settings.ASTEROID_BASE_MAX + level - 1)
            if len(self.asteroids) < max_hazards:
                speed = (settings.ASTEROID_BASE_SPEED
                         + settings.ASTEROID_SPEED_PER_LEVEL * (level - 1)
                         + random.uniform(-10, 20))
                self.asteroids.append(Asteroid(speed))

        # Time Crystal: rare, and only one on screen at a time.
        self.crystal_timer -= dt
        if self.crystal_timer <= 0:
            self.crystal_timer = settings.CRYSTAL_SPAWN_INTERVAL * random.uniform(0.8, 1.2)
            if not self._has_powerup(TimeCrystal):
                self.powerups.append(TimeCrystal(random.uniform(40, width - 40), -20))

        # Shield pick-up: appears regularly, one on screen at a time.
        self.shield_timer -= dt
        if self.shield_timer <= 0:
            self.shield_timer = settings.SHIELD_SPAWN_INTERVAL * random.uniform(0.8, 1.2)
            if not self._has_powerup(ShieldPowerUp):
                self.powerups.append(ShieldPowerUp(random.uniform(40, width - 40), -20))

    # ------------------------------------------------------------------
    # Collisions and scoring rules (custom mechanics 1 and 2 live here)
    # ------------------------------------------------------------------
    def _check_collisions(self):
        player = self.player

        # Rule 1: collecting an energy orb gives +10 points.
        for orb in self.orbs:
            if orb.alive and circles_overlap(player.x, player.y, player.radius,
                                             orb.x, orb.y, orb.radius):
                orb.alive = False
                self.score += settings.ORB_POINTS
                self.orbs_collected += 1
                self.audio.play("collect")
                spawn_particles(self.particles, orb.x, orb.y, settings.ELECTRIC_CYAN, 14)
                self._popup(f"+{settings.ORB_POINTS}", orb.x, orb.y, settings.ELECTRIC_CYAN)

        # Time Crystal and shield pick-ups.
        for item in self.powerups:
            if item.alive and circles_overlap(player.x, player.y, player.radius,
                                              item.x, item.y, item.radius):
                item.alive = False
                if isinstance(item, TimeCrystal):
                    self._collect_crystal(item)
                else:
                    self._collect_shield(item)

        # Rules 2, 7 and the shield: asteroid collisions.
        for rock in self.asteroids:
            if not rock.alive or not circles_overlap(player.x, player.y, player.radius,
                                                     rock.x, rock.y, rock.radius):
                continue
            if player.is_invulnerable:
                continue                         # brief protection after a hit (rule 7)
            rock.alive = False                   # the asteroid is destroyed by any hit
            self._hit_by_asteroid(rock)
            if self.state != PLAYING:
                break                            # the last life was lost; stop checking

    def _collect_crystal(self, crystal):
        """Rule 4 and custom mechanic 1: +25 points and every hazard slows for 5 seconds."""
        self.score += settings.CRYSTAL_POINTS
        self.slow_timer = settings.CRYSTAL_SLOW_TIME
        self.audio.play("crystal")
        self.effects.flash(settings.GOLDEN_YELLOW, 0.3)
        spawn_particles(self.particles, crystal.x, crystal.y, settings.GOLDEN_YELLOW, 24, speed=220, life=0.9)
        self._popup(f"+{settings.CRYSTAL_POINTS}  TIME SLOW", crystal.x, crystal.y, settings.GOLDEN_YELLOW)

    def _collect_shield(self, shield):
        """Custom mechanic 2: the next asteroid hit is absorbed."""
        self.player.shield_active = True
        self.audio.play("shield")
        spawn_particles(self.particles, shield.x, shield.y, settings.SHIELD_BLUE, 20, speed=180)
        self._popup("SHIELD ONLINE", shield.x, shield.y, settings.SHIELD_BLUE)

    def _hit_by_asteroid(self, rock):
        player = self.player
        if player.shield_active:
            # The shield absorbs this hit and then breaks.
            player.shield_active = False
            self.collisions += 1
            self.audio.play("block")
            self.effects.shake(5, 0.2)
            self.effects.flash(settings.SHIELD_BLUE, 0.2)
            spawn_particles(self.particles, rock.x, rock.y, settings.SHIELD_BLUE, 22, speed=200)
            self._popup("BLOCKED", rock.x, rock.y, settings.SHIELD_BLUE)
            return

        # No shield: lose one life and the score penalty (rule 2).
        self.lives -= 1
        self.score = max(0, self.score - settings.ASTEROID_PENALTY)   # never below zero
        player.start_invulnerability()
        self.audio.play("hit")
        self.effects.shake(12, 0.4)
        self.effects.flash(settings.CORAL_RED, 0.3)
        spawn_particles(self.particles, player.x, player.y, settings.CORAL_RED, 30, speed=260, life=0.8)
        self._popup(f"-{settings.ASTEROID_PENALTY}", player.x, player.y - 20, settings.CORAL_RED)
        if self.lives <= 0:
            self._end_game()
        else:
            self.collisions += 1                 # a hit Lumi survived

    def _popup(self, text, x, y, color):
        self.texts.append(FloatingText(text, x, y, color))

    # ------------------------------------------------------------------
    # Ending the match
    # ------------------------------------------------------------------
    def _end_game(self):
        if self.state == GAME_OVER:
            return                               # make sure this only runs once
        self.state = GAME_OVER
        self.new_record = self.score > self.high_score
        if self.new_record:
            self.high_score = self.score
        save_high_score(self.high_score)
        self.audio.play("game_over")
        self.effects.shake(10, 0.5)
        self.effects.flash(settings.CORAL_RED, 0.6)

    def shutdown(self):
        """Called when the window closes. Keeps a record score even if the match was not finished."""
        if self.state in (PLAYING, PAUSED) and self.score > self.high_score:
            self.high_score = self.score
        save_high_score(self.high_score)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self):
        scene = self.scene
        self.starfield.draw(scene)

        if self.state == MENU:
            self.decor.draw(scene)
            draw_title_screen(scene, self.fonts, self.menu_buttons, self.high_score, self.total_time)
        elif self.state == INSTRUCTIONS:
            draw_instructions(scene, self.fonts, self.back_button)
        else:
            self._draw_world(scene)
            if self.state == PAUSED:
                draw_pause_overlay(scene, self.fonts)
            elif self.state == GAME_OVER:
                draw_game_over(scene, self.fonts, self.total_time, self.score, self.high_score,
                               self.orbs_collected, self.collisions, self.new_record,
                               self.game_over_buttons)

        # Screen shake: the whole scene is moved by a small random offset.
        offset_x, offset_y = self.effects.shake_offset()
        self.screen.fill(settings.MIDNIGHT_NAVY)
        self.screen.blit(scene, (offset_x, offset_y))

        if self.take_screenshot:
            self._save_screenshot()

    def _draw_world(self, scene):
        """Draw the gameplay objects, the screen flash and the HUD."""
        for item in self.powerups:
            item.draw(scene)
        for orb in self.orbs:
            orb.draw(scene)
        for rock in self.asteroids:
            rock.draw(scene)
        for particle in self.particles:
            particle.draw(scene)
        self.player.draw(scene)
        for text in self.texts:
            text.draw(scene, self.fonts.medium)
        self.effects.draw_flash(scene)
        draw_hud(scene, self.fonts, self.score, self.lives, self.time_left, self.level,
                 self.high_score, self.player.shield_active, self.slow_timer, self.audio.muted)

    def _save_screenshot(self):
        """F12 saves the current frame to the screenshots folder."""
        self.take_screenshot = False
        os.makedirs(settings.SCREENSHOT_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(settings.SCREENSHOT_DIR, f"lumi_{stamp}.png")
        pygame.image.save(self.screen, path)
