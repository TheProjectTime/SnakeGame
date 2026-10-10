"""
=============================================================================
CLASSIC SNAKE GAME — MODERN ARCADE EDITION
=============================================================================
A premium, modern arcade Snake Game built with Python 3, Pygame, and SQLite.
Features:
  - Custom UI matching modern dark-navy & neon-mint arcade aesthetics.
  - 3D-shaded snake with directional cartoon eyes and animated tongue.
  - 3D glossy apple with specular reflections and green leaf stem.
  - Interactive top HUD with Score, High Score, Speed, and clickable Pause/Mute buttons.
  - Start screen with mascot, 3D title, interactive 'PLAY NOW' button, and controls guide.
  - Game Over & Pause modals with seamless mouse and keyboard interaction.
  - Persistent all-time high scores backed by an SQLite database (snake_scores.db).
  - Procedural retro audio (eat chime, game over, start chord) with mute toggle.
=============================================================================
"""

import json
import math
import os
import random
import sqlite3
import sys
import time
import pygame

# ---------------------------------------------------------------------------
# WINDOW & GRID DIMENSIONS
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 560
WINDOW_HEIGHT = 700

# Board geometry (26 columns x 26 rows = 676 cells)
BOARD_X = 20
BOARD_Y = 100
BOARD_SIZE = 520
GRID_CELLS = 26
CELL_SIZE = BOARD_SIZE // GRID_CELLS  # 20 px per cell

# Top HUD geometry
HUD_X = 20
HUD_Y = 16
HUD_W = 520
HUD_H = 68

# Bottom controls bar geometry
FOOTER_X = 20
FOOTER_Y = 636
FOOTER_W = 520
FOOTER_H = 48

# Speeds & Balancing
BASE_SPEED = 9                        # Starting snake moves per second (FPS)
MAX_SPEED = 22                         # Maximum speed cap
POINTS_PER_FOOD = 10                  # Score per apple

# ---------------------------------------------------------------------------
# COLOR PALETTE (Modern Arcade Navy & Mint Glow)
# ---------------------------------------------------------------------------
COLOR_BG_DARK = (3, 10, 24)           # Deep cosmic navy background
COLOR_CARD_BG = (6, 19, 41)          # Dark navy container cards
COLOR_CARD_BORDER = (14, 48, 102)    # Sleek cyan-blue container border
COLOR_CARD_BORDER_GLOW = (22, 74, 155)
COLOR_GRID_BG = (4, 13, 33)          # Dark game board background
COLOR_GRID_LINES = (12, 35, 74)      # Subtle grid lines
COLOR_GRID_BORDER = (12, 43, 94)     # Outer board border

COLOR_SNAKE_HEAD = (0, 240, 118)     # Bright vibrant mint head
COLOR_SNAKE_BODY = (0, 215, 95)      # Emerald body
COLOR_SNAKE_BODY_ALT = (0, 195, 85)  # Segment variation
COLOR_SNAKE_SHINE = (140, 255, 190)  # Top highlight
COLOR_SNAKE_DEAD = (235, 60, 60)     # Red on crash

COLOR_APPLE = (255, 59, 48)          # Vibrant red apple
COLOR_APPLE_DARK = (210, 35, 25)     # 3D shadow on apple
COLOR_APPLE_SHINE = (255, 185, 175)  # Glossy highlight
COLOR_APPLE_LEAF = (52, 199, 89)     # Bright green leaf

COLOR_TEXT_MAIN = (255, 255, 255)    # Crisp white
COLOR_TEXT_MUTED = (122, 156, 214)   # Slate blue (labels: SCORE, BEST, SPEED)
COLOR_MINT = (0, 230, 118)           # Neon mint green
COLOR_GOLD = (255, 204, 0)           # Trophy & Best record gold
COLOR_CORAL = (255, 82, 82)          # Game over coral
COLOR_BTN_GREEN_TOP = (0, 245, 125)  # Play button gradient top
COLOR_BTN_GREEN_BOT = (0, 195, 95)   # Play button gradient bottom

# ---------------------------------------------------------------------------
# SQLITE DATABASE & PERSISTENCE
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(BASE_DIR, "snake_scores.db")
LEGACY_HIGH_SCORE_FILE = os.path.join(BASE_DIR, "high_score.json")


def init_db():
    """Initializes SQLite database and creates high_scores table."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS high_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    score INTEGER NOT NULL,
                    achieved_at TEXT NOT NULL
                )
            """)
            conn.commit()

            # Migrate from legacy high_score.json if present and DB is empty
            cursor.execute("SELECT COUNT(*) FROM high_scores")
            count = cursor.fetchone()[0]
            if count == 0 and os.path.exists(LEGACY_HIGH_SCORE_FILE):
                try:
                    with open(LEGACY_HIGH_SCORE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        legacy = int(data.get("high_score", 0))
                        if legacy > 0:
                            cursor.execute(
                                "INSERT INTO high_scores (score, achieved_at) VALUES (?, ?)",
                                (legacy, time.strftime("%Y-%m-%d %H:%M:%S"))
                            )
                            conn.commit()
                except Exception:
                    pass
    except Exception:
        pass


def load_high_score():
    """Retrieves all-time highest score from SQLite."""
    try:
        init_db()
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(score) FROM high_scores")
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0])
    except Exception:
        pass
    return 0


def save_high_score(score):
    """Inserts a new score record into SQLite."""
    try:
        init_db()
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO high_scores (score, achieved_at) VALUES (?, ?)",
                (int(score), now_str)
            )
            conn.commit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# PROCEDURAL AUDIO SYSTEM
# ---------------------------------------------------------------------------
class SoundManager:
    """Lightweight in-memory procedural audio generator with mute toggle."""
    def __init__(self):
        self.muted = False
        self.enabled = False
        self.eat_sound = None
        self.game_over_sound = None
        self.start_sound = None

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._create_procedural_sounds()
            self.enabled = True
        except Exception:
            self.enabled = False

    def _synthesize_wav(self, frequencies, duration=0.1, volume=0.25):
        import io
        import struct
        import wave

        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        buf = io.BytesIO()

        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            frames = bytearray()

            for i in range(num_samples):
                t = i / sample_rate
                decay = max(0.0, 1.0 - (i / num_samples))
                freq_idx = int((i / num_samples) * len(frequencies))
                freq = frequencies[min(freq_idx, len(frequencies) - 1)]

                sample_val = int(32767 * volume * decay * math.sin(2 * math.pi * freq * t))
                clamped_val = max(-32768, min(32767, sample_val))
                frames.extend(struct.pack("<h", clamped_val))

            wav.writeframes(frames)

        buf.seek(0)
        return pygame.mixer.Sound(buf)

    def _create_procedural_sounds(self):
        try:
            self.eat_sound = self._synthesize_wav([520, 650, 780], duration=0.08, volume=0.22)
            self.game_over_sound = self._synthesize_wav([220, 160, 110, 80], duration=0.22, volume=0.28)
            self.start_sound = self._synthesize_wav([440, 554, 659], duration=0.12, volume=0.20)
        except Exception:
            pass

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted

    def play_eat(self):
        if self.enabled and not self.muted and self.eat_sound:
            try:
                self.eat_sound.play()
            except Exception:
                pass

    def play_game_over(self):
        if self.enabled and not self.muted and self.game_over_sound:
            try:
                self.game_over_sound.play()
            except Exception:
                pass

    def play_start(self):
        if self.enabled and not self.muted and self.start_sound:
            try:
                self.start_sound.play()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# VISUAL PARTICLES & EFFECTS
# ---------------------------------------------------------------------------
class FloatingSquare:
    """Floating neon dust square on the start screen."""
    def __init__(self):
        self.reset()
        self.y = random.uniform(20, WINDOW_HEIGHT - 20)

    def reset(self):
        self.x = random.uniform(20, WINDOW_WIDTH - 20)
        self.y = random.uniform(WINDOW_HEIGHT - 40, WINDOW_HEIGHT)
        self.size = random.randint(4, 9)
        self.speed = random.uniform(0.3, 0.9)
        self.color = random.choice([
            (0, 230, 118, random.randint(70, 150)),
            (0, 180, 255, random.randint(60, 130)),
            (0, 255, 180, random.randint(80, 160)),
        ])

    def update(self):
        self.y -= self.speed
        if self.y < -10:
            self.reset()

    def draw(self, surface):
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        s.fill(self.color)
        surface.blit(s, (int(self.x), int(self.y)))


class SparkleParticle:
    """Food eaten sparkle particle."""
    def __init__(self, x, y, color):
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.5, 4.2)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.lifetime = random.randint(14, 24)
        self.max_lifetime = self.lifetime
        self.size = random.uniform(3.0, 5.0)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.94
        self.vy *= 0.94
        self.lifetime -= 1

    def draw(self, surface):
        if self.lifetime <= 0:
            return
        p = self.lifetime / self.max_lifetime
        size = max(1, int(self.size * p))
        alpha = int(255 * p)
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], alpha), (size, size), size)
        surface.blit(s, (int(self.x - size), int(self.y - size)))


class FloatingText:
    """Floating '+10' popup indicator."""
    def __init__(self, text, x, y, font, color=COLOR_GOLD):
        self.text = text
        self.x = float(x)
        self.y = float(y)
        self.font = font
        self.color = color
        self.lifetime = 26
        self.max_lifetime = 26

    def update(self):
        self.y -= 1.0
        self.lifetime -= 1

    def draw(self, surface):
        if self.lifetime <= 0:
            return
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        rendered = self.font.render(self.text, True, self.color)
        temp = pygame.Surface(rendered.get_size(), pygame.SRCALPHA)
        temp.blit(rendered, (0, 0))
        temp.set_alpha(alpha)
        surface.blit(temp, (int(self.x), int(self.y)))


# ---------------------------------------------------------------------------
# DIRECTIONS
# ---------------------------------------------------------------------------
DIR_UP = (0, -1)
DIR_DOWN = (0, 1)
DIR_LEFT = (-1, 0)
DIR_RIGHT = (1, 0)

OPPOSITES = {
    DIR_UP: DIR_DOWN,
    DIR_DOWN: DIR_UP,
    DIR_LEFT: DIR_RIGHT,
    DIR_RIGHT: DIR_LEFT,
}


# ---------------------------------------------------------------------------
# SNAKE & FOOD ENTITIES
# ---------------------------------------------------------------------------
class Snake:
    """3D-shaded rounded capsule snake with cartoon eyes and tongue."""
    def __init__(self):
        self.reset()

    def reset(self):
        mid_x = GRID_CELLS // 2
        mid_y = GRID_CELLS // 2
        self.body = [
            (mid_x, mid_y),
            (mid_x - 1, mid_y),
            (mid_x - 2, mid_y),
        ]
        self.direction = DIR_RIGHT
        self.next_direction = DIR_RIGHT
        self.grow_pending = 0
        self.is_dead = False
        self.tongue_timer = 0

    @property
    def head(self):
        return self.body[0]

    def set_direction(self, new_dir):
        if new_dir != OPPOSITES.get(self.direction):
            self.next_direction = new_dir

    def update(self):
        self.direction = self.next_direction
        hx, hy = self.head
        dx, dy = self.direction
        new_head = (hx + dx, hy + dy)

        # 1. Wall collision
        nx, ny = new_head
        if nx < 0 or nx >= GRID_CELLS or ny < 0 or ny >= GRID_CELLS:
            self.is_dead = True
            return True, False

        # 2. Self collision
        if new_head in self.body:
            self.is_dead = True
            return False, True

        self.body.insert(0, new_head)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()

        self.tongue_timer = (self.tongue_timer + 1) % 10
        return False, False

    def grow(self):
        self.grow_pending += 1

    def draw(self, surface):
        """Draws segments with 3D drop shadow, rounded body, and cartoon head."""
        # 1. Draw soft drop shadows for all segments
        shadow_surf = pygame.Surface((CELL_SIZE + 4, CELL_SIZE + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 75), (0, 0, CELL_SIZE + 2, CELL_SIZE + 2), border_radius=7)
        for gx, gy in self.body:
            px = BOARD_X + gx * CELL_SIZE
            py = BOARD_Y + gy * CELL_SIZE
            surface.blit(shadow_surf, (px + 2, py + 3))

        # 2. Draw body segments (from tail to neck)
        for i in range(len(self.body) - 1, 0, -1):
            gx, gy = self.body[i]
            px = BOARD_X + gx * CELL_SIZE
            py = BOARD_Y + gy * CELL_SIZE

            color = COLOR_SNAKE_BODY if (i % 2 == 0) else COLOR_SNAKE_BODY_ALT
            if self.is_dead:
                color = (130, 45, 45) if (i % 2 == 0) else (100, 35, 35)

            # Main rounded rectangle segment
            seg_rect = pygame.Rect(px + 1, py + 1, CELL_SIZE - 2, CELL_SIZE - 2)
            pygame.draw.rect(surface, color, seg_rect, border_radius=6)

            # Top highlight / specular gloss
            shine_rect = pygame.Rect(px + 3, py + 2, CELL_SIZE - 6, (CELL_SIZE // 2) - 2)
            pygame.draw.rect(surface, COLOR_SNAKE_SHINE, shine_rect, border_radius=4)

        # 3. Draw Head
        hx, hy = self.head
        head_px = BOARD_X + hx * CELL_SIZE
        head_py = BOARD_Y + hy * CELL_SIZE
        head_rect = pygame.Rect(head_px + 1, head_py + 1, CELL_SIZE - 2, CELL_SIZE - 2)
        head_color = COLOR_SNAKE_DEAD if self.is_dead else COLOR_SNAKE_HEAD
        pygame.draw.rect(surface, head_color, head_rect, border_radius=7)

        # Top highlight on head
        h_shine = pygame.Rect(head_px + 3, head_py + 2, CELL_SIZE - 6, (CELL_SIZE // 2) - 2)
        pygame.draw.rect(surface, (180, 255, 215), h_shine, border_radius=4)

        # 4. Draw cartoon eye and flickering red tongue
        self._draw_head_details(surface, head_px, head_py)

    def _draw_head_details(self, surface, px, py):
        dx, dy = self.direction

        # Tongue (flickers every few frames)
        if not self.is_dead and self.tongue_timer < 5:
            tongue_color = (255, 75, 95)
            if dx == 1:   # Right
                tip = (px + CELL_SIZE + 4, py + CELL_SIZE // 2)
                base = (px + CELL_SIZE - 1, py + CELL_SIZE // 2)
            elif dx == -1: # Left
                tip = (px - 4, py + CELL_SIZE // 2)
                base = (px + 1, py + CELL_SIZE // 2)
            elif dy == -1: # Up
                tip = (px + CELL_SIZE // 2, py - 4)
                base = (px + CELL_SIZE // 2, py + 1)
            else:          # Down
                tip = (px + CELL_SIZE // 2, py + CELL_SIZE + 4)
                base = (px + CELL_SIZE // 2, py + CELL_SIZE - 1)
            pygame.draw.line(surface, tongue_color, base, tip, 2)

        # Large expressive cartoon eye (as seen in screenshots)
        if dx == 1:   # Facing Right
            eye_center = (px + 13, py + 9)
            pupil_offset = (1, 0)
        elif dx == -1: # Facing Left
            eye_center = (px + 7, py + 9)
            pupil_offset = (-1, 0)
        elif dy == -1: # Facing Up
            eye_center = (px + 9, py + 7)
            pupil_offset = (0, -1)
        else:          # Facing Down
            eye_center = (px + 9, py + 13)
            pupil_offset = (0, 1)

        # White sclera
        pygame.draw.circle(surface, (255, 255, 255), eye_center, 4)
        # Black pupil
        pupil = (eye_center[0] + pupil_offset[0], eye_center[1] + pupil_offset[1])
        pygame.draw.circle(surface, (20, 20, 25), pupil, 2)
        # Specular shine dot
        shine = (pupil[0] - 1, pupil[1] - 1)
        pygame.draw.circle(surface, (255, 255, 255), shine, 1)


class Food:
    """3D glossy apple with specular highlight and leaf stem."""
    def __init__(self):
        self.position = (0, 0)

    def respawn(self, snake_body):
        occupied = set(snake_body)
        while True:
            candidate = (random.randint(0, GRID_CELLS - 1), random.randint(0, GRID_CELLS - 1))
            if candidate not in occupied:
                self.position = candidate
                break

    def draw(self, surface):
        gx, gy = self.position
        px = BOARD_X + gx * CELL_SIZE
        py = BOARD_Y + gy * CELL_SIZE

        cx = px + CELL_SIZE // 2
        cy = py + CELL_SIZE // 2 + 1
        r = (CELL_SIZE // 2) - 1

        # Drop shadow
        shadow_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(shadow_surf, (0, 0, 0, 90), (r + 2, r + 2), r)
        surface.blit(shadow_surf, (cx - r, cy - r + 3))

        # Apple body (dark base for 3D depth)
        pygame.draw.circle(surface, COLOR_APPLE_DARK, (cx, cy), r)
        # Apple top gradient sphere
        pygame.draw.circle(surface, COLOR_APPLE, (cx - 1, cy - 1), r - 1)

        # Specular reflection shine
        pygame.draw.circle(surface, COLOR_APPLE_SHINE, (cx - 3, cy - 3), 2)

        # Green leaf & stem
        pygame.draw.line(surface, (90, 60, 30), (cx, cy - r), (cx + 1, cy - r - 3), 2)
        leaf_pts = [(cx + 1, cy - r - 2), (cx + 5, cy - r - 5), (cx + 4, cy - r)]
        pygame.draw.polygon(surface, COLOR_APPLE_LEAF, leaf_pts)


# ---------------------------------------------------------------------------
# UI DRAWING HELPERS (ICONS & CARDS)
# ---------------------------------------------------------------------------
def draw_rounded_card(surface, rect, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=2, radius=12):
    """Draws a sleek rounded card with custom borders."""
    r = pygame.Rect(rect)
    pygame.draw.rect(surface, bg_color, r, border_radius=radius)
    if border_width > 0:
        pygame.draw.rect(surface, border_color, r, width=border_width, border_radius=radius)


def draw_trophy_icon(surface, x, y, size=22, color=COLOR_GOLD):
    """Draws a clean gold trophy icon."""
    cx = x + size // 2
    # Cup body
    cup_pts = [
        (cx - 7, y + 4),
        (cx + 7, y + 4),
        (cx + 5, y + 12),
        (cx - 5, y + 12)
    ]
    pygame.draw.polygon(surface, color, cup_pts)
    # Cup handles
    pygame.draw.arc(surface, color, (cx - 10, y + 4, 6, 7), math.pi / 2, 3 * math.pi / 2, 2)
    pygame.draw.arc(surface, color, (cx + 4, y + 4, 6, 7), -math.pi / 2, math.pi / 2, 2)
    # Stand stem
    pygame.draw.line(surface, color, (cx, y + 12), (cx, y + 16), 2)
    # Base
    pygame.draw.line(surface, color, (cx - 6, y + 16), (cx + 6, y + 16), 2)


def draw_speedometer_icon(surface, x, y, size=22, color=(0, 180, 255)):
    """Draws a clean speedometer dial gauge icon."""
    cx = x + size // 2
    cy = y + size // 2 + 2
    r = 9
    # Gauge arc
    pygame.draw.arc(surface, color, (cx - r, cy - r, r * 2, r * 2), math.pi * 0.8, math.pi * 2.2, 2)
    # Center hub
    pygame.draw.circle(surface, color, (cx, cy), 2)
    # Needle pointing towards top-right
    needle_end = (cx + 5, cy - 5)
    pygame.draw.line(surface, color, (cx, cy), needle_end, 2)


def draw_pause_icon(surface, x, y, size=18, paused=False, color=COLOR_MINT):
    """Draws pause bars (||) or play triangle (▶)."""
    cx = x + size // 2
    cy = y + size // 2
    if paused:
        pts = [(cx - 4, cy - 6), (cx + 6, cy), (cx - 4, cy + 6)]
        pygame.draw.polygon(surface, color, pts)
    else:
        pygame.draw.rect(surface, color, (cx - 5, cy - 6, 3, 12), border_radius=1)
        pygame.draw.rect(surface, color, (cx + 2, cy - 6, 3, 12), border_radius=1)


def draw_speaker_icon(surface, x, y, size=18, muted=False, color=COLOR_TEXT_MUTED):
    """Draws speaker with audio waves or mute slash."""
    cx = x + size // 2
    cy = y + size // 2
    # Speaker cone
    cone_pts = [
        (cx - 6, cy - 3),
        (cx - 3, cy - 3),
        (cx + 2, cy - 6),
        (cx + 2, cy + 6),
        (cx - 3, cy + 3),
        (cx - 6, cy + 3)
    ]
    pygame.draw.polygon(surface, color, cone_pts)
    if muted:
        pygame.draw.line(surface, COLOR_CORAL, (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
    else:
        # Waves
        pygame.draw.arc(surface, color, (cx, cy - 5, 8, 10), -math.pi / 3, math.pi / 3, 2)


def draw_key_badge(surface, text, x, y, w=28, h=28, font=None, active=False):
    """Draws a sleek keyboard shortcut badge like [W], [A], [S], [D], [P], [R]."""
    rect = pygame.Rect(x, y, w, h)
    bg = (18, 32, 58) if active else (10, 24, 48)
    border = COLOR_MINT if active else (24, 58, 110)
    pygame.draw.rect(surface, bg, rect, border_radius=6)
    pygame.draw.rect(surface, border, rect, width=1, border_radius=6)
    if font:
        txt = font.render(text, True, COLOR_TEXT_MAIN)
        surface.blit(txt, txt.get_rect(center=rect.center))


# ---------------------------------------------------------------------------
# MAIN GAME APPLICATION CLASS
# ---------------------------------------------------------------------------
class SnakeGameApp:
    """Modern arcade Snake Game matching the target UI design."""
    STATE_START = "START"
    STATE_PLAYING = "PLAYING"
    STATE_PAUSED = "PAUSED"
    STATE_GAME_OVER = "GAME_OVER"

    def __init__(self):
        pygame.init()
        pygame.font.init()

        # Desktop window
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Classic Snake Game")
        self._set_window_icon()
        self.clock = pygame.time.Clock()

        # Typography
        self.font_title_3d = pygame.font.SysFont(["segoeui", "arialblack", "impact", "arial"], 52, bold=True)
        self.font_h1 = pygame.font.SysFont(["segoeui", "arial", "helvetica"], 26, bold=True)
        self.font_h2 = pygame.font.SysFont(["segoeui", "arial", "helvetica"], 20, bold=True)
        self.font_h3 = pygame.font.SysFont(["segoeui", "arial", "helvetica"], 16, bold=True)
        self.font_hud_val = pygame.font.SysFont(["consolas", "lucidaconsole", "monospace"], 22, bold=True)
        self.font_body = pygame.font.SysFont(["segoeui", "arial", "helvetica"], 13)
        self.font_badge = pygame.font.SysFont(["segoeui", "arial", "helvetica"], 12, bold=True)
        self.font_small = pygame.font.SysFont(["segoeui", "arial", "helvetica"], 11, bold=True)

        # Audio
        self.sound = SoundManager()

        # State & Entities
        self.state = self.STATE_START
        self.snake = Snake()
        self.food = Food()
        self.score = 0
        self.high_score = load_high_score()
        self.new_high_score_achieved = False

        # Visual FX
        self.floating_squares = [FloatingSquare() for _ in range(16)]
        self.particles = []
        self.floating_texts = []
        self.screen_shake = 0
        self.move_timer = 0.0
        self.running = True

        # Mouse & Buttons
        self.mouse_pos = (0, 0)
        self.play_btn_hover = False
        self.pause_btn_hover = False
        self.sound_btn_hover = False

        self.food.respawn(self.snake.body)

    def _set_window_icon(self):
        """Creates a cute green snake icon for the window titlebar."""
        try:
            icon = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.rect(icon, COLOR_SNAKE_HEAD, (4, 4, 24, 24), border_radius=8)
            pygame.draw.circle(icon, (255, 255, 255), (20, 12), 4)
            pygame.draw.circle(icon, (20, 20, 20), (22, 12), 2)
            pygame.draw.line(icon, (255, 60, 60), (28, 16), (32, 16), 2)
            pygame.display.set_icon(icon)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # GAME STATE TRANSITIONS
    # -----------------------------------------------------------------------
    def start_new_game(self):
        self.snake.reset()
        self.food.respawn(self.snake.body)
        self.score = 0
        self.new_high_score_achieved = False
        self.particles.clear()
        self.floating_texts.clear()
        self.screen_shake = 0
        self.move_timer = 0.0
        self.state = self.STATE_PLAYING
        self.sound.play_start()

    def toggle_pause(self):
        if self.state == self.STATE_PLAYING:
            self.state = self.STATE_PAUSED
        elif self.state == self.STATE_PAUSED:
            self.state = self.STATE_PLAYING

    def trigger_game_over(self):
        self.state = self.STATE_GAME_OVER
        self.screen_shake = 8
        self.sound.play_game_over()
        if self.score > self.high_score:
            self.high_score = self.score
            self.new_high_score_achieved = True
            save_high_score(self.high_score)

    def get_current_speed(self):
        speed_bonus = self.score // 30
        return min(MAX_SPEED, BASE_SPEED + speed_bonus)

    # -----------------------------------------------------------------------
    # EVENT HANDLING
    # -----------------------------------------------------------------------
    def handle_events(self):
        self.mouse_pos = pygame.mouse.get_pos()

        # Update HUD button rects
        hud_pause_rect = pygame.Rect(HUD_X + HUD_W - 85, HUD_Y + (HUD_H - 36) // 2, 36, 36)
        hud_sound_rect = pygame.Rect(HUD_X + HUD_W - 42, HUD_Y + (HUD_H - 36) // 2, 36, 36)

        self.pause_btn_hover = hud_pause_rect.collidepoint(self.mouse_pos)
        self.sound_btn_hover = hud_sound_rect.collidepoint(self.mouse_pos)

        # Start screen Play Button rect
        play_btn_rect = pygame.Rect(75, 375, 410, 56)
        self.play_btn_hover = (self.state == self.STATE_START and play_btn_rect.collidepoint(self.mouse_pos))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # Mouse Clicks
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == self.STATE_START:
                    if play_btn_rect.collidepoint(event.pos):
                        self.start_new_game()
                        return
                elif self.state in (self.STATE_PLAYING, self.STATE_PAUSED):
                    if hud_pause_rect.collidepoint(event.pos):
                        self.toggle_pause()
                        return
                    elif hud_sound_rect.collidepoint(event.pos):
                        self.sound.toggle_mute()
                        return
                elif self.state == self.STATE_GAME_OVER:
                    # Click to restart on game over button
                    go_btn_rect = pygame.Rect(WINDOW_WIDTH // 2 - 120, 440, 240, 50)
                    if go_btn_rect.collidepoint(event.pos):
                        self.start_new_game()
                        return

            # Keyboard Events
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state in (self.STATE_START, self.STATE_GAME_OVER, self.STATE_PAUSED):
                        self.running = False
                        return
                    elif self.state == self.STATE_PLAYING:
                        self.toggle_pause()
                        return

                # P key toggles Pause
                if event.key == pygame.K_p:
                    if self.state in (self.STATE_PLAYING, self.STATE_PAUSED):
                        self.toggle_pause()
                        return

                # R key or Space to Start/Restart
                if event.key in (pygame.K_SPACE, pygame.K_r, pygame.K_RETURN):
                    if self.state in (self.STATE_START, self.STATE_GAME_OVER):
                        self.start_new_game()
                        return
                    elif self.state == self.STATE_PAUSED:
                        self.toggle_pause()
                        return

                # M key to toggle sound
                if event.key == pygame.K_m:
                    self.sound.toggle_mute()
                    return

                # Movement Controls (Arrow Keys + WASD)
                if self.state == self.STATE_PLAYING:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.snake.set_direction(DIR_UP)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.snake.set_direction(DIR_DOWN)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.snake.set_direction(DIR_LEFT)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.snake.set_direction(DIR_RIGHT)

    # -----------------------------------------------------------------------
    # UPDATE CYCLE
    # -----------------------------------------------------------------------
    def update(self, dt):
        for sq in self.floating_squares:
            sq.update()

        for p in self.particles[:]:
            p.update()
            if p.lifetime <= 0:
                self.particles.remove(p)

        for ft in self.floating_texts[:]:
            ft.update()
            if ft.lifetime <= 0:
                self.floating_texts.remove(ft)

        if self.screen_shake > 0:
            self.screen_shake -= 1

        if self.state != self.STATE_PLAYING:
            return

        speed = self.get_current_speed()
        self.move_timer += dt

        if self.move_timer >= (1.0 / speed):
            self.move_timer -= (1.0 / speed)

            hit_wall, hit_self = self.snake.update()
            if hit_wall or hit_self:
                self.trigger_game_over()
                return

            if self.snake.head == self.food.position:
                self.score += POINTS_PER_FOOD
                self.snake.grow()
                self.sound.play_eat()

                fx, fy = self.food.position
                px = BOARD_X + fx * CELL_SIZE
                py = BOARD_Y + fy * CELL_SIZE
                self.floating_texts.append(
                    FloatingText(f"+{POINTS_PER_FOOD}", px, py - 4, self.font_hud_val)
                )

                cx = px + CELL_SIZE // 2
                cy = py + CELL_SIZE // 2
                for _ in range(10):
                    c = random.choice([COLOR_APPLE, COLOR_MINT, COLOR_GOLD, (255, 255, 255)])
                    self.particles.append(SparkleParticle(cx, cy, c))

                self.food.respawn(self.snake.body)

    # -----------------------------------------------------------------------
    # RENDERING METHODS
    # -----------------------------------------------------------------------
    def draw_top_hud(self, surface):
        """Renders the dashboard matching Image 2."""
        hud_rect = pygame.Rect(HUD_X, HUD_Y, HUD_W, HUD_H)
        draw_rounded_card(surface, hud_rect, COLOR_CARD_BG, COLOR_CARD_BORDER, radius=14)

        # 1. SCORE Block
        score_lbl = self.font_small.render("SCORE", True, COLOR_TEXT_MUTED)
        surface.blit(score_lbl, (HUD_X + 22, HUD_Y + 14))
        score_val = self.font_hud_val.render(f"{self.score:03d}", True, COLOR_MINT)
        surface.blit(score_val, (HUD_X + 20, HUD_Y + 30))

        # Divider 1
        pygame.draw.line(surface, COLOR_CARD_BORDER, (HUD_X + 115, HUD_Y + 16), (HUD_X + 115, HUD_Y + HUD_H - 16), 1)

        # 2. BEST High Score Block
        draw_trophy_icon(surface, HUD_X + 130, HUD_Y + 22, size=24, color=COLOR_GOLD)
        best_lbl = self.font_small.render("BEST", True, COLOR_TEXT_MUTED)
        surface.blit(best_lbl, (HUD_X + 162, HUD_Y + 14))
        best_val = self.font_hud_val.render(f"{self.high_score:03d}", True, COLOR_GOLD)
        surface.blit(best_val, (HUD_X + 162, HUD_Y + 30))

        # Divider 2
        pygame.draw.line(surface, COLOR_CARD_BORDER, (HUD_X + 245, HUD_Y + 16), (HUD_X + 245, HUD_Y + HUD_H - 16), 1)

        # 3. SPEED Block
        draw_speedometer_icon(surface, HUD_X + 260, HUD_Y + 22, size=24, color=(0, 180, 255))
        speed_lbl = self.font_small.render("SPEED", True, COLOR_TEXT_MUTED)
        surface.blit(speed_lbl, (HUD_X + 292, HUD_Y + 14))
        cur_spd = self.get_current_speed()
        spd_val = self.font_h3.render(f"{cur_spd} FPS", True, COLOR_TEXT_MAIN)
        surface.blit(spd_val, (HUD_X + 292, HUD_Y + 32))

        # 4. Action Buttons (Right)
        # Pause Button (Circular with neon glow border)
        p_cx = HUD_X + HUD_W - 67
        p_cy = HUD_Y + HUD_H // 2
        p_radius = 18
        p_border = COLOR_MINT if (self.state == self.STATE_PAUSED or self.pause_btn_hover) else (0, 170, 95)
        pygame.draw.circle(surface, (10, 24, 48), (p_cx, p_cy), p_radius)
        pygame.draw.circle(surface, p_border, (p_cx, p_cy), p_radius, width=2)
        draw_pause_icon(surface, p_cx - 9, p_cy - 9, size=18, paused=(self.state == self.STATE_PAUSED), color=p_border)

        # Sound Button (Circular)
        s_cx = HUD_X + HUD_W - 24
        s_cy = HUD_Y + HUD_H // 2
        s_radius = 18
        s_border = (0, 180, 255) if self.sound_btn_hover else COLOR_CARD_BORDER
        pygame.draw.circle(surface, (10, 24, 48), (s_cx, s_cy), s_radius)
        pygame.draw.circle(surface, s_border, (s_cx, s_cy), s_radius, width=2)
        draw_speaker_icon(surface, s_cx - 9, s_cy - 9, size=18, muted=self.sound.muted, color=COLOR_TEXT_MAIN)

    def draw_game_board(self, surface):
        """Renders the game board frame and grid lines matching Image 2."""
        board_rect = pygame.Rect(BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE)
        # Outer glow frame
        draw_rounded_card(surface, board_rect, COLOR_GRID_BG, COLOR_GRID_BORDER, border_width=2, radius=12)

        # Subtle dark-blue grid lines
        for i in range(1, GRID_CELLS):
            x = BOARD_X + i * CELL_SIZE
            pygame.draw.line(surface, COLOR_GRID_LINES, (x, BOARD_Y), (x, BOARD_Y + BOARD_SIZE), 1)
            y = BOARD_Y + i * CELL_SIZE
            pygame.draw.line(surface, COLOR_GRID_LINES, (BOARD_X, y), (BOARD_X + BOARD_SIZE, y), 1)

    def draw_bottom_bar(self, surface):
        """Renders the bottom controls reminder matching Image 2."""
        bar_rect = pygame.Rect(FOOTER_X, FOOTER_Y, FOOTER_W, FOOTER_H)
        draw_rounded_card(surface, bar_rect, COLOR_CARD_BG, COLOR_CARD_BORDER, border_width=1, radius=10)

        # Arrow keys icon layout
        base_x = FOOTER_X + 16
        base_y = FOOTER_Y + 10
        draw_key_badge(surface, "↑", base_x + 18, base_y, 16, 14, self.font_badge)
        draw_key_badge(surface, "←", base_x, base_y + 16, 16, 14, self.font_badge)
        draw_key_badge(surface, "↓", base_x + 18, base_y + 16, 16, 14, self.font_badge)
        draw_key_badge(surface, "→", base_x + 36, base_y + 16, 16, 14, self.font_badge)

        # Divider
        pygame.draw.line(surface, COLOR_CARD_BORDER, (FOOTER_X + 80, FOOTER_Y + 12), (FOOTER_X + 80, FOOTER_Y + FOOTER_H - 12), 1)

        # Move instruction text
        lbl = self.font_body.render("Move: Arrow Keys or WASD", True, COLOR_TEXT_MUTED)
        surface.blit(lbl, (FOOTER_X + 96, FOOTER_Y + 15))

        # Pause and Restart shortcuts
        draw_key_badge(surface, "P", FOOTER_X + 330, FOOTER_Y + 12, 22, 22, self.font_badge)
        p_txt = self.font_body.render("Pause", True, COLOR_TEXT_MUTED)
        surface.blit(p_txt, (FOOTER_X + 358, FOOTER_Y + 15))

        draw_key_badge(surface, "R", FOOTER_X + 418, FOOTER_Y + 12, 22, 22, self.font_badge)
        r_txt = self.font_body.render("Restart", True, COLOR_TEXT_MUTED)
        surface.blit(r_txt, (FOOTER_X + 446, FOOTER_Y + 15))

    # -----------------------------------------------------------------------
    # START SCREEN (MATCHING IMAGE 1)
    # -----------------------------------------------------------------------
    def draw_start_screen(self, surface):
        """Renders the stunning start screen matching Image 1 exactly."""
        # 1. Floating particles
        for sq in self.floating_squares:
            sq.draw(surface)

        center_x = WINDOW_WIDTH // 2

        # 2. Cute Mascot Snake at Top
        self._draw_mascot_snake(surface, center_x, 82)

        # 3. Big 3D "SNAKE" Title
        title_y = 145
        # Extruded 3D depth layers
        for offset in range(5, 0, -1):
            shadow = self.font_title_3d.render("SNAKE", True, (0, 70, 35))
            surface.blit(shadow, shadow.get_rect(center=(center_x, title_y + offset)))
        # Top vibrant mint gradient text
        main_title = self.font_title_3d.render("SNAKE", True, (43, 253, 138))
        surface.blit(main_title, main_title.get_rect(center=(center_x, title_y)))

        # Subtitle
        sub = self.font_h3.render("Eat. Grow. Beat your best.", True, COLOR_TEXT_MAIN)
        surface.blit(sub, sub.get_rect(center=(center_x, 206)))

        # 4. Middle Card Container
        card_rect = pygame.Rect(45, 235, 470, 225)
        draw_rounded_card(surface, card_rect, COLOR_CARD_BG, COLOR_CARD_BORDER, border_width=2, radius=18)

        # Left Inset Preview Box
        prev_rect = pygame.Rect(68, 255, 215, 85)
        draw_rounded_card(surface, prev_rect, (4, 13, 33), (12, 40, 85), border_width=1, radius=12)

        # Mini grid inside preview box
        for gx in range(prev_rect.left + 15, prev_rect.right, 20):
            pygame.draw.line(surface, (10, 30, 65), (gx, prev_rect.top), (gx, prev_rect.bottom), 1)
        for gy in range(prev_rect.top + 15, prev_rect.bottom, 20):
            pygame.draw.line(surface, (10, 30, 65), (prev_rect.left, gy), (prev_rect.right, gy), 1)

        # Mini caterpillar snake
        seg_y = prev_rect.centery
        for seg_idx, sx in enumerate([prev_rect.left + 35, prev_rect.left + 55, prev_rect.left + 75]):
            pygame.draw.rect(surface, COLOR_SNAKE_BODY, (sx, seg_y - 8, 16, 16), border_radius=5)
            pygame.draw.rect(surface, COLOR_SNAKE_SHINE, (sx + 2, seg_y - 6, 12, 4), border_radius=2)
        # Head
        hx = prev_rect.left + 95
        pygame.draw.rect(surface, COLOR_SNAKE_HEAD, (hx, seg_y - 9, 18, 18), border_radius=6)
        pygame.draw.circle(surface, (255, 255, 255), (hx + 12, seg_y - 1), 4)
        pygame.draw.circle(surface, (20, 20, 20), (hx + 13, seg_y - 1), 2)

        # Mini glossy apple
        ax = prev_rect.right - 45
        ay = seg_y
        pygame.draw.circle(surface, COLOR_APPLE, (ax, ay), 10)
        pygame.draw.circle(surface, COLOR_APPLE_SHINE, (ax - 3, ay - 3), 2)
        pygame.draw.line(surface, (52, 199, 89), (ax, ay - 10), (ax + 2, ay - 14), 2)

        # Sparkles in preview
        self._draw_sparkle_star(surface, prev_rect.left + 85, prev_rect.top + 15, (0, 255, 180))
        self._draw_sparkle_star(surface, prev_rect.right - 65, prev_rect.top + 18, (0, 230, 255))
        self._draw_sparkle_star(surface, prev_rect.left + 115, prev_rect.bottom - 18, (0, 230, 150))

        # Divider line
        pygame.draw.line(surface, COLOR_CARD_BORDER, (300, 260), (300, 335), 1)

        # Right High Score Box
        draw_trophy_icon(surface, 325, 275, size=28, color=COLOR_GOLD)
        hs_lbl = self.font_small.render("HIGH SCORE", True, COLOR_TEXT_MUTED)
        surface.blit(hs_lbl, (360, 272))
        hs_val = self.font_h1.render(f"{self.high_score}", True, COLOR_MINT)
        surface.blit(hs_val, (360, 292))

        # Big "PLAY NOW" Pill Button
        btn_rect = pygame.Rect(75, 365, 410, 60)
        # Glow halo under button
        halo_surf = pygame.Surface((424, 74), pygame.SRCALPHA)
        pygame.draw.rect(halo_surf, (0, 230, 118, 45 if self.play_btn_hover else 30), (0, 0, 424, 74), border_radius=37)
        surface.blit(halo_surf, (btn_rect.x - 7, btn_rect.y - 7))

        # Button background
        btn_color_top = (40, 255, 145) if self.play_btn_hover else COLOR_BTN_GREEN_TOP
        btn_color_bot = (0, 215, 105) if self.play_btn_hover else COLOR_BTN_GREEN_BOT
        pygame.draw.rect(surface, btn_color_bot, btn_rect, border_radius=30)
        pygame.draw.rect(surface, btn_color_top, (btn_rect.x, btn_rect.y, btn_rect.w, btn_rect.h - 4), border_radius=30)

        # Button Text with play triangle
        play_txt = self.font_h1.render("▶  PLAY NOW", True, (3, 24, 12))
        surface.blit(play_txt, play_txt.get_rect(center=btn_rect.center))

        # 5. Bottom Controls Card
        ctrl_rect = pygame.Rect(35, 495, 490, 155)
        draw_rounded_card(surface, ctrl_rect, COLOR_CARD_BG, COLOR_CARD_BORDER, border_width=2, radius=18)

        # MOVE Section
        move_lbl = self.font_small.render("MOVE", True, COLOR_TEXT_MUTED)
        surface.blit(move_lbl, (ctrl_rect.left + 24, ctrl_rect.top + 16))

        # Arrow Keys
        ak_x = ctrl_rect.left + 50
        ak_y = ctrl_rect.top + 45
        draw_key_badge(surface, "↑", ak_x + 30, ak_y, 28, 28, self.font_badge)
        draw_key_badge(surface, "←", ak_x, ak_y + 34, 28, 28, self.font_badge)
        draw_key_badge(surface, "↓", ak_x + 30, ak_y + 34, 28, 28, self.font_badge)
        draw_key_badge(surface, "→", ak_x + 60, ak_y + 34, 28, 28, self.font_badge)

        or_txt = self.font_body.render("or", True, COLOR_TEXT_MUTED)
        surface.blit(or_txt, (ak_x + 105, ak_y + 24))

        # WASD Keys
        wasd_x = ak_x + 135
        draw_key_badge(surface, "W", wasd_x + 30, ak_y, 28, 28, self.font_badge)
        draw_key_badge(surface, "A", wasd_x, ak_y + 34, 28, 28, self.font_badge)
        draw_key_badge(surface, "S", wasd_x + 30, ak_y + 34, 28, 28, self.font_badge)
        draw_key_badge(surface, "D", wasd_x + 60, ak_y + 34, 28, 28, self.font_badge)

        # Divider
        pygame.draw.line(surface, COLOR_CARD_BORDER, (ctrl_rect.left + 305, ctrl_rect.top + 30), (ctrl_rect.left + 305, ctrl_rect.bottom - 30), 1)

        # PAUSE Section
        p_lbl = self.font_small.render("PAUSE", True, COLOR_TEXT_MUTED)
        surface.blit(p_lbl, (ctrl_rect.left + 328, ctrl_rect.top + 32))
        draw_key_badge(surface, "P", ctrl_rect.left + 332, ctrl_rect.top + 58, 32, 32, self.font_h3)

        # RESTART Section
        r_lbl = self.font_small.render("RESTART", True, COLOR_TEXT_MUTED)
        surface.blit(r_lbl, (ctrl_rect.left + 408, ctrl_rect.top + 32))
        draw_key_badge(surface, "R", ctrl_rect.left + 418, ctrl_rect.top + 58, 32, 32, self.font_h3)

    def _draw_mascot_snake(self, surface, cx, cy):
        """Draws the cute cartoon snake mascot from Image 1."""
        # Body segments
        pygame.draw.rect(surface, (0, 185, 80), (cx - 45, cy + 5, 24, 24), border_radius=8)
        pygame.draw.rect(surface, (0, 215, 95), (cx - 30, cy - 8, 24, 30), border_radius=9)
        pygame.draw.rect(surface, (0, 240, 118), (cx - 10, cy - 18, 32, 36), border_radius=11)
        # Head
        head_rect = pygame.Rect(cx - 5, cy - 24, 46, 38)
        pygame.draw.rect(surface, COLOR_SNAKE_HEAD, head_rect, border_radius=14)
        # Highlight on head
        pygame.draw.rect(surface, (140, 255, 190), (head_rect.x + 4, head_rect.y + 4, head_rect.w - 8, 10), border_radius=6)

        # Big Cartoon Eye
        eye_cx = head_rect.x + 24
        eye_cy = head_rect.y + 14
        pygame.draw.circle(surface, (255, 255, 255), (eye_cx, eye_cy), 10)
        pygame.draw.circle(surface, (20, 20, 25), (eye_cx + 2, eye_cy), 6)
        pygame.draw.circle(surface, (255, 255, 255), (eye_cx + 4, eye_cy - 2), 2)

        # Red tongue sticking out
        tongue_pts = [
            (head_rect.right - 2, eye_cy + 8),
            (head_rect.right + 12, eye_cy + 8),
            (head_rect.right + 16, eye_cy + 5),
            (head_rect.right + 12, eye_cy + 8),
            (head_rect.right + 16, eye_cy + 11)
        ]
        pygame.draw.lines(surface, (255, 65, 85), False, tongue_pts, 3)

    def _draw_sparkle_star(self, surface, cx, cy, color):
        """Draws a 4-point sparkle cross."""
        pts = [
            (cx, cy - 6),
            (cx + 2, cy - 2),
            (cx + 6, cy),
            (cx + 2, cy + 2),
            (cx, cy + 6),
            (cx - 2, cy + 2),
            (cx - 6, cy),
            (cx - 2, cy - 2)
        ]
        pygame.draw.polygon(surface, color, pts)

    # -----------------------------------------------------------------------
    # PAUSE & GAME OVER OVERLAYS
    # -----------------------------------------------------------------------
    def draw_pause_modal(self, surface):
        """Draws frosted glass pause modal in modern arcade styling."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((3, 10, 24, 195))
        surface.blit(overlay, (0, 0))

        card_rect = pygame.Rect(80, 210, 400, 260)
        draw_rounded_card(surface, card_rect, COLOR_CARD_BG, COLOR_CARD_BORDER, border_width=2, radius=18)

        cx = card_rect.centerx
        title = self.font_h1.render("GAME PAUSED", True, COLOR_GOLD)
        surface.blit(title, title.get_rect(center=(cx, 260)))

        # Score reminder
        sub = self.font_body.render(f"Current Score: {self.score}   •   Best: {self.high_score}", True, COLOR_TEXT_MUTED)
        surface.blit(sub, sub.get_rect(center=(cx, 295)))

        # Resume Button
        res_btn = pygame.Rect(cx - 140, 330, 280, 48)
        pygame.draw.rect(surface, COLOR_BTN_GREEN_BOT, res_btn, border_radius=24)
        pygame.draw.rect(surface, COLOR_BTN_GREEN_TOP, (res_btn.x, res_btn.y, res_btn.w, res_btn.h - 3), border_radius=24)
        res_txt = self.font_h3.render("▶  RESUME  [P / SPACE]", True, (3, 24, 12))
        surface.blit(res_txt, res_txt.get_rect(center=res_btn.center))

        # Quit hint
        quit_txt = self.font_body.render("Press [R] to Restart   •   [ESC] to Quit", True, COLOR_TEXT_MUTED)
        surface.blit(quit_txt, quit_txt.get_rect(center=(cx, 420)))

    def draw_game_over_modal(self, surface):
        """Draws sleek arcade Game Over modal."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 12, 28, 215))
        surface.blit(overlay, (0, 0))

        card_rect = pygame.Rect(65, 175, 430, 350)
        draw_rounded_card(surface, card_rect, COLOR_CARD_BG, (120, 35, 45), border_width=2, radius=20)

        cx = card_rect.centerx

        # Title
        title = self.font_h1.render("GAME OVER", True, COLOR_CORAL)
        surface.blit(title, title.get_rect(center=(cx, 220)))

        # Score & High score box
        stat_rect = pygame.Rect(cx - 160, 255, 320, 80)
        draw_rounded_card(surface, stat_rect, (4, 13, 33), COLOR_CARD_BORDER, border_width=1, radius=12)

        s_txt = self.font_small.render("FINAL SCORE", True, COLOR_TEXT_MUTED)
        surface.blit(s_txt, (stat_rect.left + 35, stat_rect.top + 16))
        s_val = self.font_h1.render(f"{self.score}", True, COLOR_MINT)
        surface.blit(s_val, (stat_rect.left + 35, stat_rect.top + 36))

        pygame.draw.line(surface, COLOR_CARD_BORDER, (stat_rect.centerx, stat_rect.top + 12), (stat_rect.centerx, stat_rect.bottom - 12), 1)

        b_txt = self.font_small.render("ALL-TIME BEST", True, COLOR_TEXT_MUTED)
        surface.blit(b_txt, (stat_rect.centerx + 30, stat_rect.top + 16))
        b_val = self.font_h1.render(f"{self.high_score}", True, COLOR_GOLD)
        surface.blit(b_val, (stat_rect.centerx + 30, stat_rect.top + 36))

        # New Record notification
        if self.new_high_score_achieved:
            badge = self.font_h3.render("★ NEW RECORD HIGH SCORE! ★", True, COLOR_GOLD)
            surface.blit(badge, badge.get_rect(center=(cx, 360)))

        # Play Again Button
        btn_rect = pygame.Rect(cx - 150, 395, 300, 52)
        pygame.draw.rect(surface, COLOR_BTN_GREEN_BOT, btn_rect, border_radius=26)
        pygame.draw.rect(surface, COLOR_BTN_GREEN_TOP, (btn_rect.x, btn_rect.y, btn_rect.w, btn_rect.h - 3), border_radius=26)
        pa_txt = self.font_h2.render("▶  PLAY AGAIN", True, (3, 24, 12))
        surface.blit(pa_txt, pa_txt.get_rect(center=btn_rect.center))

        quit_txt = self.font_body.render("Press [SPACE / R] to Play Again   •   [ESC] to Quit", True, COLOR_TEXT_MUTED)
        surface.blit(quit_txt, quit_txt.get_rect(center=(cx, 480)))

    # -----------------------------------------------------------------------
    # MASTER RENDER
    # -----------------------------------------------------------------------
    def render(self):
        shake_x = 0
        shake_y = 0
        if self.screen_shake > 0:
            shake_x = random.randint(-2, 2)
            shake_y = random.randint(-2, 2)

        canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        canvas.fill(COLOR_BG_DARK)

        if self.state == self.STATE_START:
            self.draw_start_screen(canvas)
        else:
            # Active Gameplay Screens
            self.draw_top_hud(canvas)
            self.draw_game_board(canvas)
            self.food.draw(canvas)
            self.snake.draw(canvas)

            # Particles & Floating Popups
            for p in self.particles:
                p.draw(canvas)
            for ft in self.floating_texts:
                ft.draw(canvas)

            self.draw_bottom_bar(canvas)

            if self.state == self.STATE_PAUSED:
                self.draw_pause_modal(canvas)
            elif self.state == self.STATE_GAME_OVER:
                self.draw_game_over_modal(canvas)

        self.screen.fill((0, 0, 0))
        self.screen.blit(canvas, (shake_x, shake_y))
        pygame.display.flip()

    # -----------------------------------------------------------------------
    # RUN LOOP
    # -----------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()

        pygame.quit()
        sys.exit(0)


# ---------------------------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = SnakeGameApp()
    app.run()
