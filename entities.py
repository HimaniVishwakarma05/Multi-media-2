"""
entities.py - Every moving object in LUMI.

Classes:
- Starfield:       scrolling stars, drifting planets and a soft nebula background
- Particle:        one small glowing dot used for trails, sparks and bursts
- Player:          Lumi, the spacecraft controlled by the keyboard
- Collectible:     base class for anything that falls and can be picked up
  - EnergyOrb:     cyan orb worth points
  - PowerUp:       base class for special pick-ups
    - TimeCrystal:     golden crystal that slows hazards (custom mechanic 1)
    - ShieldPowerUp:   blue shield pick-up (custom mechanic 2)
- Asteroid:        lumpy rock that damages Lumi

Helper functions:
- circles_overlap():  circle-based collision test
- spawn_particles():  creates a burst of particles
- draw_glow():        draws a cached soft glow behind any object
"""

import functools
import math
import random

import pygame

import settings


# ----------------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------------
@functools.lru_cache(maxsize=256)
def glow_surface(radius, color):
    """
    Build a transparent image of a soft glowing circle.
    The result is cached, so each (radius, colour) pair is built only once and
    then reused every frame. This keeps the glow effects fast.
    """
    radius = max(1, int(radius))
    size = radius * 2 + 2
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    for step in range(radius, 0, -1):          # draw the outer rings first
        strength = 1 - step / radius           # 0 at the edge, close to 1 at the centre
        alpha = int(10 + 120 * strength * strength)
        pygame.draw.circle(surface, (*color, alpha), (center, center), step)
    return surface


def draw_glow(surface, x, y, radius, color):
    """Draw a soft glow centred on (x, y)."""
    image = glow_surface(int(radius), color)
    surface.blit(image, image.get_rect(center=(int(x), int(y))))


def circles_overlap(x1, y1, r1, x2, y2, r2):
    """
    Circle collision test: two circles overlap when the distance between
    their centres is smaller than the sum of their radii. We compare squared
    distances, which avoids the slower square-root calculation.
    """
    dx = x1 - x2
    dy = y1 - y2
    return dx * dx + dy * dy < (r1 + r2) ** 2


def spawn_particles(particles, x, y, color, count, speed=150, life=0.6):
    """Add a burst of particles that fly outwards from (x, y)."""
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        velocity = random.uniform(0.3, 1.0) * speed
        particles.append(Particle(
            x, y,
            math.cos(angle) * velocity,
            math.sin(angle) * velocity,
            color,
            life * random.uniform(0.7, 1.2),
        ))


# ----------------------------------------------------------------------------
# Background
# ----------------------------------------------------------------------------
class Starfield:
    """Background: scrolling stars, slow planets and a soft nebula glow."""

    def __init__(self):
        self.time = 0.0
        self.stars = [self._new_star(random_height=True) for _ in range(settings.STAR_COUNT)]
        self.planets = []
        for _ in range(settings.PLANET_COUNT):
            self.planets.append({
                "x": random.uniform(0, settings.WIDTH),
                "y": random.uniform(0, settings.HEIGHT),
                "radius": random.randint(18, 48),
                "color": random.choice([settings.VIOLET, settings.ELECTRIC_CYAN, settings.CORAL_RED]),
                "speed": random.uniform(6, 14),
            })
        self.nebula = self._build_nebula()

    def _new_star(self, random_height=False):
        """Create one star. 'depth' decides how fast and how bright it looks."""
        return {
            "x": random.uniform(0, settings.WIDTH),
            "y": random.uniform(0, settings.HEIGHT) if random_height else -2.0,
            "depth": random.uniform(0.2, 1.0),       # near stars move faster (parallax)
            "twinkle": random.uniform(0, math.tau),  # offset for the twinkle animation
        }

    def _build_nebula(self):
        """Draw the soft colour clouds once. They are reused every frame."""
        nebula = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
        blobs = [
            (200, 150, 320, settings.VIOLET),
            (760, 470, 380, settings.ELECTRIC_CYAN),
            (560, 230, 220, settings.VIOLET),
        ]
        for center_x, center_y, radius, color in blobs:
            for step in range(radius, 0, -8):      # outer rings first, brighter inner rings last
                strength = 1 - step / radius
                alpha = int(38 * strength * strength)
                pygame.draw.circle(nebula, (*color, alpha), (center_x, center_y), step)
        return nebula

    def update(self, dt):
        """Move the stars and planets downwards so the ship seems to fly forwards."""
        self.time += dt
        for star in self.stars:
            star["y"] += (20 + 80 * star["depth"]) * dt
            if star["y"] > settings.HEIGHT:
                star.update(self._new_star())      # recycle the star at the top
        for planet in self.planets:
            planet["y"] += planet["speed"] * dt
            if planet["y"] - planet["radius"] > settings.HEIGHT:
                planet["y"] = -planet["radius"] * 2
                planet["x"] = random.uniform(0, settings.WIDTH)

    def draw(self, surface):
        surface.fill(settings.MIDNIGHT_NAVY)
        surface.blit(self.nebula, (0, 0))
        for planet in self.planets:
            x, y, radius = int(planet["x"]), int(planet["y"]), planet["radius"]
            body = tuple(int(channel * 0.3) for channel in planet["color"])  # dark planet body
            pygame.draw.circle(surface, body, (x, y), radius)
            pygame.draw.circle(surface, planet["color"], (x, y), radius, 2)  # glowing rim
        for star in self.stars:
            # Each star twinkles by changing its brightness over time.
            brightness = 0.6 + 0.4 * math.sin(self.time * 2 + star["twinkle"])
            level = int(90 + 150 * star["depth"] * brightness)
            size = 2 if star["depth"] > 0.75 else 1
            surface.fill((level, level, level + 10), (int(star["x"]), int(star["y"]), size, size))


# ----------------------------------------------------------------------------
# Particles
# ----------------------------------------------------------------------------
class Particle:
    """A tiny dot that flies away and fades out. Used for sparks and trails."""

    def __init__(self, x, y, vx, vy, color, life):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life

    def update(self, dt):
        """Move the particle and count down its life. Returns False when it should be removed."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        slowdown = max(0.0, 1 - 3 * dt)            # particles gradually slow down
        self.vx *= slowdown
        self.vy *= slowdown
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        ratio = max(0.0, self.life / self.max_life)          # 1.0 new, 0.0 finished
        radius = 1 + int(3 * ratio)
        # Fade the colour towards the background navy as the particle ages.
        color = tuple(int(navy + (c - navy) * ratio)
                      for c, navy in zip(self.color, settings.MIDNIGHT_NAVY))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), radius)


# ----------------------------------------------------------------------------
# The player
# ----------------------------------------------------------------------------
class Player:
    """Lumi, the spacecraft controlled by the player."""

    def __init__(self):
        self.x = settings.WIDTH / 2
        self.y = settings.HEIGHT - 90
        self.radius = settings.PLAYER_RADIUS
        self.tilt = 0.0                  # -1 leaning left, +1 leaning right (for drawing)
        self.invulnerable_timer = 0.0    # seconds of protection left after a hit
        self.shield_active = False       # True after collecting a shield power-up
        self.time = 0.0                  # running clock for animations

    def move(self, direction_x, direction_y, dt):
        """Move using a direction whose parts are between -1 and 1."""
        length = math.hypot(direction_x, direction_y)
        if length > 0:
            direction_x /= length        # normalise so diagonal movement is not faster
            direction_y /= length
        self.x += direction_x * settings.PLAYER_SPEED * dt
        self.y += direction_y * settings.PLAYER_SPEED * dt
        self.tilt += (direction_x - self.tilt) * min(1.0, 10 * dt)   # smooth lean
        # Keep Lumi inside the screen.
        self.x = max(self.radius, min(settings.WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(settings.HEIGHT - self.radius, self.y))

    def update(self, dt):
        self.time += dt
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)

    def start_invulnerability(self):
        """Called after a hit so the same collision cannot remove more lives."""
        self.invulnerable_timer = settings.INVULNERABLE_TIME

    @property
    def is_invulnerable(self):
        return self.invulnerable_timer > 0

    def draw(self, surface):
        # Blink while invulnerable so the player can see the protection period.
        if self.is_invulnerable and int(self.invulnerable_timer * 12) % 2 == 0:
            return

        x, y = self.x, self.y
        body_color = settings.SHIELD_BLUE if self.shield_active else settings.ELECTRIC_CYAN

        # Engine flames: two flickering tongues behind the wings.
        flicker = 0.5 + 0.5 * math.sin(self.time * 30)
        for offset_x in (-6, 6):
            flame_length = 8 + 5 * flicker + random.uniform(0, 3)
            flame = [
                (x + offset_x - 4, y + 10),
                (x + offset_x + 4, y + 10),
                (x + offset_x, y + 10 + flame_length),
            ]
            pygame.draw.polygon(surface, settings.GOLDEN_YELLOW, flame)

        # Shield: a pulsing blue bubble around the ship (visible change of appearance).
        if self.shield_active:
            pulse = settings.SHIELD_BUBBLE_RADIUS + 3 * math.sin(self.time * 6)
            draw_glow(surface, x, y, int(pulse), settings.SHIELD_BLUE)
            pygame.draw.circle(surface, settings.SHIELD_BLUE, (int(x), int(y)), int(pulse), 2)

        # Ship body: nose at the top, wings at the bottom, notch in the middle.
        draw_glow(surface, x, y, 24, body_color)
        shape = [(x, y - 18), (x + 14, y + 12), (x, y + 6), (x - 14, y + 12)]
        pygame.draw.polygon(surface, body_color, shape)
        pygame.draw.polygon(surface, settings.WHITE, shape, 1)
        pygame.draw.circle(surface, settings.WHITE, (int(x), int(y - 2)), 3)   # cockpit


# ----------------------------------------------------------------------------
# Collectibles
# ----------------------------------------------------------------------------
class Collectible:
    """Base class for anything that drifts down the screen and can be picked up."""

    def __init__(self, x, y, radius, fall_speed):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.fall_speed = fall_speed
        self.age = 0.0          # time since it appeared, used for animation
        self.alive = True       # set to False when collected or off screen

    def update(self, dt):
        self.age += dt
        self.y += self.fall_speed * dt
        if self.y - self.radius > settings.HEIGHT:
            self.alive = False

    def draw(self, surface):
        raise NotImplementedError("Each collectible must draw itself.")


class EnergyOrb(Collectible):
    """Cyan energy orb. Collecting it gives +10 points."""

    def __init__(self, x, y):
        super().__init__(x, y, settings.ORB_RADIUS, random.uniform(60, 100))
        self.phase = random.uniform(0, math.tau)   # makes each orb pulse differently

    def draw(self, surface):
        pulse = 0.5 + 0.5 * math.sin(self.age * 4 + self.phase)   # 0 to 1
        cx, cy = int(self.x), int(self.y)
        draw_glow(surface, cx, cy, int(self.radius * (1.8 + 0.5 * pulse)), settings.ELECTRIC_CYAN)
        pygame.draw.circle(surface, settings.ELECTRIC_CYAN, (cx, cy),
                           int(self.radius * (0.8 + 0.2 * pulse)))
        pygame.draw.circle(surface, settings.WHITE, (cx, cy), 3)
        # A small spark orbits the orb to make it feel alive.
        spark_angle = self.age * 3 + self.phase
        spark_x = cx + math.cos(spark_angle) * self.radius * 1.5
        spark_y = cy + math.sin(spark_angle) * self.radius * 1.5
        pygame.draw.circle(surface, settings.WHITE, (int(spark_x), int(spark_y)), 2)


class PowerUp(Collectible):
    """Base class for special pick-ups. Each subclass draws and applies itself differently."""

    def __init__(self, x, y, radius):
        super().__init__(x, y, radius, 55)


class TimeCrystal(PowerUp):
    """Golden crystal. Collecting it gives +25 points and slows every hazard for five seconds."""

    def __init__(self, x, y):
        super().__init__(x, y, settings.CRYSTAL_RADIUS)

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        # Squashing the diamond's width makes it look like it is turning.
        width_factor = 0.35 + 0.65 * abs(math.cos(self.age * 2.0))
        draw_glow(surface, cx, cy, int(r * 2.2), settings.GOLDEN_YELLOW)
        diamond = [
            (cx, cy - r),
            (cx + r * width_factor, cy),
            (cx, cy + r),
            (cx - r * width_factor, cy),
        ]
        pygame.draw.polygon(surface, settings.GOLDEN_YELLOW, diamond)
        pygame.draw.polygon(surface, settings.WHITE, diamond, 1)
        pygame.draw.circle(surface, settings.WHITE, (cx, cy - r // 3), 2)   # shine


class ShieldPowerUp(PowerUp):
    """Blue shield pick-up. Collecting it protects Lumi from the next asteroid hit."""

    def __init__(self, x, y):
        super().__init__(x, y, settings.SHIELD_RADIUS)

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        pulse = 0.5 + 0.5 * math.sin(self.age * 5)
        draw_glow(surface, cx, cy, int(self.radius * (2.0 + 0.4 * pulse)), settings.SHIELD_BLUE)
        pygame.draw.circle(surface, settings.SHIELD_BLUE, (cx, cy), self.radius, 3)
        pygame.draw.circle(surface, settings.SHIELD_BLUE, (cx, cy), int(self.radius * 0.45))
        # A white dot circles the shield symbol.
        orbit_angle = self.age * 2.5
        orbit_x = cx + math.cos(orbit_angle) * (self.radius + 6)
        orbit_y = cy + math.sin(orbit_angle) * (self.radius + 6)
        pygame.draw.circle(surface, settings.WHITE, (int(orbit_x), int(orbit_y)), 2)


# ----------------------------------------------------------------------------
# Hazards
# ----------------------------------------------------------------------------
class Asteroid:
    """A lumpy purple-red rock. Touching it costs Lumi a life unless the shield absorbs it."""

    def __init__(self, speed):
        self.radius = random.randint(settings.ASTEROID_MIN_RADIUS, settings.ASTEROID_MAX_RADIUS)
        self.x = random.uniform(self.radius, settings.WIDTH - self.radius)
        self.y = -self.radius * 2.0
        self.speed = speed                        # downward speed before any slow-motion
        self.drift = random.uniform(-25, 25)      # slight sideways movement
        self.angle = random.uniform(0, math.tau)
        self.spin = random.uniform(-1.5, 1.5)     # rotation in radians per second
        self.alive = True
        # A random distance for each of 9 corners, so every rock has its own shape.
        self.corners = []
        for index in range(9):
            corner_angle = index * math.tau / 9
            distance = self.radius * random.uniform(0.75, 1.0)
            self.corners.append((corner_angle, distance))

    def update(self, dt, speed_factor=1.0):
        """speed_factor is 1.0 normally and smaller while the Time Crystal slows hazards."""
        step = dt * speed_factor
        self.y += self.speed * step
        self.x += self.drift * step
        self.angle += self.spin * step
        # Bounce off the left and right edges of the screen.
        if self.x - self.radius < 0 or self.x + self.radius > settings.WIDTH:
            self.drift = -self.drift
            self.x = max(self.radius, min(settings.WIDTH - self.radius, self.x))
        if self.y - self.radius > settings.HEIGHT:
            self.alive = False

    def draw(self, surface):
        cx, cy = self.x, self.y
        draw_glow(surface, int(cx), int(cy), int(self.radius * 1.5), settings.VIOLET)
        points = []
        for corner_angle, distance in self.corners:
            angle = corner_angle + self.angle     # rotate the outline
            points.append((cx + math.cos(angle) * distance, cy + math.sin(angle) * distance))
        pygame.draw.polygon(surface, settings.VIOLET, points)
        pygame.draw.polygon(surface, settings.CORAL_RED, points, 2)
        # A crater makes the rock look three-dimensional.
        pygame.draw.circle(surface, (90, 50, 150),
                           (int(cx + self.radius * 0.25), int(cy - self.radius * 0.2)),
                           max(2, int(self.radius * 0.22)))
