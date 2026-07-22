"""
NEON OVERDRIVE: CYBER ARENA
===========================
A complete, premium quality arcade action game built purely with Pygame.
Features procedural vector graphics, synthesized sound effects, dynamic dynamic 
lighting, screen shake, combo mechanics, level progression, and UI state management.

Author: Premium Pygame Developer
Engine: Pygame 2.x
Language: Python 3.8+
"""

import os
import sys
import math
import random
import json
import struct
import pygame

# Initialize Pygame Modules early
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
GAME_TITLE = "NEON OVERDRIVE"
VERSION = "v1.0.0"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
TARGET_FPS = 60
SAVE_FILE = "neon_overdrive_data.json"

# Color Palette (Cyberpunk / Neon Aesthetic)
COLOR_BG = (10, 10, 18)
COLOR_GRID = (25, 28, 48)
COLOR_WHITE = (255, 255, 255)
COLOR_CYAN = (0, 240, 255)
COLOR_MAGENTA = (255, 0, 128)
COLOR_NEON_GREEN = (50, 255, 100)
COLOR_YELLOW = (255, 220, 0)
COLOR_ORANGE = (255, 100, 0)
COLOR_PURPLE = (160, 32, 240)
COLOR_RED = (255, 40, 60)
COLOR_DARK_UI = (18, 18, 30, 210)

# ==============================================================================
# PROCEDURAL AUDIO SYNTHESIZER (No External Sound Files Required)
# ==============================================================================
class SoundFXManager:
    """Generates procedural sound effects using math waveforms and 16-bit PCM buffer."""
    def __init__(self):
        self.sounds = {}
        self.enabled = True
        self.volume = 0.7
        self.sample_rate = 22050
        self.generate_all_sounds()

    def _pack_pcm(self, samples):
        """Converts floating point audio samples (-1.0 to 1.0) into stereo 16-bit PCM bytes."""
        byte_array = bytearray()
        for sample in samples:
            clamped = max(-1.0, min(1.0, sample))
            val = int(clamped * 32767)
            # Duplicate for Left/Right stereo channels
            packed = struct.pack('<h', val)
            byte_array.extend(packed)
            byte_array.extend(packed)
        return bytes(byte_array)

    def generate_all_sounds(self):
        """Pre-synthesizes laser, explosion, hit, powerup, click, and shockwave sounds."""
        try:
            # 1. Laser Sound
            laser_samples = []
            duration = 0.12
            total_samples = int(self.sample_rate * duration)
            for i in range(total_samples):
                t = i / self.sample_rate
                freq = 850 * (1.0 - t / duration) + 120
                sample = math.sin(2 * math.pi * freq * t) * (1.0 - t / duration)
                laser_samples.append(sample * 0.5)
            self.sounds['laser'] = pygame.mixer.Sound(buffer=self._pack_pcm(laser_samples))

            # 2. Explosion Sound
            exp_samples = []
            duration = 0.45
            total_samples = int(self.sample_rate * duration)
            for i in range(total_samples):
                t = i / self.sample_rate
                decay = math.exp(-6.0 * t / duration)
                noise = (random.random() * 2.0 - 1.0)
                freq = 120 * (1.0 - t / duration)
                sub = math.sin(2 * math.pi * freq * t)
                sample = (noise * 0.7 + sub * 0.3) * decay
                exp_samples.append(sample * 0.6)
            self.sounds['explosion'] = pygame.mixer.Sound(buffer=self._pack_pcm(exp_samples))

            # 3. Hit Sound
            hit_samples = []
            duration = 0.08
            total_samples = int(self.sample_rate * duration)
            for i in range(total_samples):
                t = i / self.sample_rate
                decay = (1.0 - t / duration)
                sample = (random.random() * 2.0 - 1.0) * decay
                hit_samples.append(sample * 0.4)
            self.sounds['hit'] = pygame.mixer.Sound(buffer=self._pack_pcm(hit_samples))

            # 4. Powerup Sound
            pow_samples = []
            duration = 0.25
            total_samples = int(self.sample_rate * duration)
            for i in range(total_samples):
                t = i / self.sample_rate
                freq = 400 + (t / duration) * 800
                sample = math.sin(2 * math.pi * freq * t) * (1.0 - t / duration)
                pow_samples.append(sample * 0.5)
            self.sounds['powerup'] = pygame.mixer.Sound(buffer=self._pack_pcm(pow_samples))

            # 5. UI Click Sound
            click_samples = []
            duration = 0.04
            total_samples = int(self.sample_rate * duration)
            for i in range(total_samples):
                t = i / self.sample_rate
                sample = math.sin(2 * math.pi * 1200 * t) * (1.0 - t / duration)
                click_samples.append(sample * 0.3)
            self.sounds['click'] = pygame.mixer.Sound(buffer=self._pack_pcm(click_samples))

            # 6. Nova Sound
            nova_samples = []
            duration = 0.6
            total_samples = int(self.sample_rate * duration)
            for i in range(total_samples):
                t = i / self.sample_rate
                freq = 150 + math.sin(t * 30) * 80
                sample = (random.random() * 0.3 + math.sin(2 * math.pi * freq * t) * 0.7) * (1.0 - t / duration)
                nova_samples.append(sample * 0.7)
            self.sounds['nova'] = pygame.mixer.Sound(buffer=self._pack_pcm(nova_samples))

            self.update_volume()
        except Exception as e:
            print(f"[SoundFXManager] Audio synthesis warning: {e}")

    def play(self, name):
        """Plays sound effect if audio is enabled."""
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    def set_volume(self, vol):
        """Sets global sound volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, vol))
        self.update_volume()

    def update_volume(self):
        for sound in self.sounds.values():
            sound.set_volume(self.volume)

# ==============================================================================
# SAVE / LOAD SYSTEM
# ==============================================================================
class SaveSystem:
    """Handles JSON storage for high scores and user configuration settings."""
    @staticmethod
    def load_data():
        default_data = {
            "highscore": 0,
            "volume": 0.7,
            "shake_enabled": True,
            "fullscreen": False
        }
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r') as f:
                    data = json.load(f)
                    default_data.update(data)
            except Exception as e:
                print(f"[SaveSystem] Error loading file: {e}")
        return default_data

    @staticmethod
    def save_data(data):
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[SaveSystem] Error saving file: {e}")

# ==============================================================================
# VISUAL EFFECTS: GLOW GENERATOR, PARTICLES, SCREEN SHAKE
# ==============================================================================
class DynamicGlowCache:
    """Pre-renders blurred surface textures for vector neon glowing effects."""
    def __init__(self):
        self.cache = {}

    def get_glow_circle(self, radius, color):
        key = (radius, color)
        if key not in self.cache:
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            r, g, b = color[:3]
            for r_offset in range(radius, 0, -2):
                alpha = int(255 * (1.0 - (r_offset / radius) ** 1.5) * 0.3)
                pygame.draw.circle(surf, (r, g, b, alpha), (radius, radius), r_offset)
            self.cache[key] = surf
        return self.cache[key]

class Particle:
    """High-performance glowing visual particle."""
    def __init__(self, x, y, vx, vy, color, radius, lifetime, shape="circle"):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.radius = radius
        self.max_lifetime = lifetime
        self.lifetime = lifetime
        self.shape = shape

    def update(self, dt):
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vx *= 0.96
        self.vy *= 0.96
        self.lifetime -= dt

    def draw(self, surface, camera_offset=(0,0)):
        if self.lifetime <= 0:
            return
        ratio = self.lifetime / self.max_lifetime
        curr_radius = max(1, int(self.radius * ratio))
        px = int(self.x + camera_offset[0])
        py = int(self.y + camera_offset[1])

        r, g, b = self.color
        alpha_color = (r, g, b)
        
        if self.shape == "circle":
            pygame.draw.circle(surface, alpha_color, (px, py), curr_radius)
        elif self.shape == "square":
            rect = pygame.Rect(px - curr_radius, py - curr_radius, curr_radius * 2, curr_radius * 2)
            pygame.draw.rect(surface, alpha_color, rect)

class FloatingText:
    """Floating UI text notification for Combos and Score events."""
    def __init__(self, x, y, text, color, font, duration=1.0, size_scale=1.0):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.font = font
        self.max_duration = duration
        self.duration = duration
        self.size_scale = size_scale

    def update(self, dt):
        self.y -= 25 * dt
        self.duration -= dt

    def draw(self, surface, camera_offset=(0,0)):
        if self.duration <= 0:
            return
        alpha = max(0, min(255, int(255 * (self.duration / self.max_duration))))
        rendered = self.font.render(self.text, True, self.color)
        
        # Apply fade alpha
        surf = pygame.Surface(rendered.get_size(), pygame.SRCALPHA)
        surf.fill((255, 255, 255, alpha))
        rendered.blit(surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        px = int(self.x + camera_offset[0] - rendered.get_width() / 2)
        py = int(self.y + camera_offset[1] - rendered.get_height() / 2)
        surface.blit(rendered, (px, py))

class CameraShake:
    """Screen shake manager for punchy impact feedback."""
    def __init__(self):
        self.intensity = 0.0
        self.decay = 5.0
        self.offset_x = 0
        self.offset_y = 0
        self.enabled = True

    def add_shake(self, amount):
        if self.enabled:
            self.intensity = min(35.0, self.intensity + amount)

    def update(self, dt):
        if self.intensity > 0:
            self.offset_x = random.uniform(-self.intensity, self.intensity)
            self.offset_y = random.uniform(-self.intensity, self.intensity)
            self.intensity = max(0.0, self.intensity - self.decay * dt * 10)
        else:
            self.offset_x = 0
            self.offset_y = 0

    def get_offset(self):
        return (int(self.offset_x), int(self.offset_y))

# ==============================================================================
# UI COMPONENTS
# ==============================================================================
class Button:
    """Interactive GUI Button with hover, click animations, and glow dynamics."""
    def __init__(self, x, y, width, height, text, font, callback, primary_color=COLOR_CYAN):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.callback = callback
        self.primary_color = primary_color
        self.is_hovered = False
        self.anim_hover = 0.0

    def update(self, dt, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        target = 1.0 if self.is_hovered else 0.0
        self.anim_hover += (target - self.anim_hover) * 15 * dt

    def handle_event(self, event, sound_mgr):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                sound_mgr.play('click')
                self.callback()

    def draw(self, surface):
        # Draw dynamic glow container
        glow_padding = int(self.anim_hover * 6)
        expanded_rect = self.rect.inflate(glow_padding * 2, glow_padding * 2)
        
        # Base glass surface
        btn_surf = pygame.Surface((expanded_rect.width, expanded_rect.height), pygame.SRCALPHA)
        bg_alpha = int(120 + self.anim_hover * 80)
        btn_surf.fill((15, 20, 35, bg_alpha))
        
        # Border
        border_color = [min(255, int(c * (0.6 + 0.4 * self.anim_hover))) for c in self.primary_color]
        border_width = 2 + int(self.anim_hover * 2)
        pygame.draw.rect(btn_surf, border_color, btn_surf.get_rect(), border_width, border_radius=6)
        
        surface.blit(btn_surf, expanded_rect.topleft)

        # Text Render
        text_color = COLOR_WHITE if not self.is_hovered else self.primary_color
        txt_rendered = self.font.render(self.text, True, text_color)
        txt_rect = txt_rendered.get_rect(center=self.rect.center)
        surface.blit(txt_rendered, txt_rect)

class Slider:
    """Interactive UI Volume / Value Slider."""
    def __init__(self, x, y, width, height, label, font, initial_val, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.font = font
        self.value = initial_val  # 0.0 to 1.0
        self.callback = callback
        self.is_dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_dragging = True
                self._update_val(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_dragging = False
        elif event.type == pygame.MOUSEMOTION and self.is_dragging:
            self._update_val(event.pos[0])

    def _update_val(self, mouse_x):
        rel_x = mouse_x - self.rect.x
        self.value = max(0.0, min(1.0, rel_x / self.rect.width))
        self.callback(self.value)

    def draw(self, surface):
        # Render Label
        lbl_surf = self.font.render(f"{self.label}: {int(self.value * 100)}%", True, COLOR_WHITE)
        surface.blit(lbl_surf, (self.rect.x, self.rect.y - 28))

        # Track background
        pygame.draw.rect(surface, (30, 35, 55), self.rect, border_radius=4)
        
        # Filled track
        fill_width = int(self.rect.width * self.value)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        pygame.draw.rect(surface, COLOR_CYAN, fill_rect, border_radius=4)

        # Handle Knob
        handle_x = self.rect.x + fill_width
        pygame.draw.circle(surface, COLOR_WHITE, (handle_x, self.rect.centery), self.rect.height // 2 + 3)

# ==============================================================================
# GAME ENTITIES
# ==============================================================================
class Player:
    """Player Controlled Ship with rotation, vector geometry, dash & nova bomb."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 18
        self.angle = 0
        self.speed = 380
        self.health = 100
        self.max_health = 100
        self.shield = 50
        self.max_shield = 50
        self.shield_regen_cooldown = 0
        
        # Dash Ability
        self.dash_cooldown = 0
        self.dash_timer = 0
        self.is_dashing = False
        
        # Nova Ability
        self.nova_energy = 0.0  # Charges from 0 to 100
        
        # Weaponry
        self.shoot_cooldown = 0
        self.weapon_level = 1  # 1: Single, 2: Dual, 3: Triple Pulse
        
    def handle_input(self, dt, mouse_pos):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

        # Normalize vector movement
        dist = math.hypot(dx, dy)
        if dist > 0:
            dx /= dist
            dy /= dist

        current_speed = self.speed * (2.2 if self.is_dashing else 1.0)
        self.x += dx * current_speed * dt
        self.y += dy * current_speed * dt

        # Rotate towards mouse cursor
        rel_x = mouse_pos[0] - self.x
        rel_y = mouse_pos[1] - self.y
        self.angle = math.atan2(rel_y, rel_x)

    def trigger_dash(self, sound_mgr, particles):
        if self.dash_cooldown <= 0:
            self.is_dashing = True
            self.dash_timer = 0.18
            self.dash_cooldown = 1.2
            sound_mgr.play('laser')
            # Create Dash Trail
            for _ in range(12):
                particles.append(Particle(
                    self.x, self.y,
                    random.uniform(-100, 100), random.uniform(-100, 100),
                    COLOR_CYAN, random.randint(4, 8), 0.3
                ))

    def update(self, dt, screen_bounds):
        # Boundaries enforcement
        self.x = max(self.radius, min(screen_bounds[0] - self.radius, self.x))
        self.y = max(self.radius, min(screen_bounds[1] - self.radius, self.y))

        # Cooldown ticks
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt
        if self.dash_timer > 0:
            self.dash_timer -= dt
        else:
            self.is_dashing = False

        # Shield Regen Logic
        if self.shield_regen_cooldown > 0:
            self.shield_regen_cooldown -= dt
        else:
            if self.shield < self.max_shield:
                self.shield = min(self.max_shield, self.shield + 12 * dt)

    def take_damage(self, amount, camera, sound_mgr):
        if self.is_dashing:
            return  # Invulnerable while dashing
        
        camera.add_shake(12)
        sound_mgr.play('hit')
        self.shield_regen_cooldown = 3.0
        
        if self.shield > 0:
            self.shield -= amount
            if self.shield < 0:
                self.health += self.shield  # Absorb spillover
                self.shield = 0
        else:
            self.health -= amount

    def draw(self, surface, glow_cache, camera_offset=(0,0)):
        px = int(self.x + camera_offset[0])
        py = int(self.y + camera_offset[1])

        # Draw Glow Surface
        glow_color = COLOR_CYAN if not self.is_dashing else COLOR_MAGENTA
        glow_surf = glow_cache.get_glow_circle(40, glow_color)
        surface.blit(glow_surf, (px - 40, py - 40), special_flags=pygame.BLEND_ADD)

        # Calculate polygon points for futuristic fighter geometry
        p1 = (px + math.cos(self.angle) * 22, py + math.sin(self.angle) * 22)
        p2 = (px + math.cos(self.angle + 2.5) * 16, py + math.sin(self.angle + 2.5) * 16)
        p3 = (px + math.cos(self.angle - 2.5) * 16, py + math.sin(self.angle - 2.5) * 16)

        # Draw Fighter Poly
        pygame.draw.polygon(surface, COLOR_WHITE, [p1, p2, p3])
        pygame.draw.polygon(surface, glow_color, [p1, p2, p3], 2)

        # Draw Shield Aura
        if self.shield > 0:
            shield_alpha = int(100 + (self.shield / self.max_shield) * 125)
            s_surf = pygame.Surface((self.radius * 2 + 12, self.radius * 2 + 12), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (0, 240, 255, shield_alpha), (self.radius + 6, self.radius + 6), self.radius + 4, 2)
            surface.blit(s_surf, (px - self.radius - 6, py - self.radius - 6))

class Projectile:
    """Laser bullet fired by player or enemies."""
    def __init__(self, x, y, angle, speed=850, is_enemy=False, damage=25, color=COLOR_CYAN):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.angle = angle
        self.is_enemy = is_enemy
        self.damage = damage
        self.color = color
        self.radius = 4
        self.alive = True

    def update(self, dt, bounds):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -20 or self.x > bounds[0] + 20 or self.y < -20 or self.y > bounds[1] + 20:
            self.alive = False

    def draw(self, surface, camera_offset=(0,0)):
        px = int(self.x + camera_offset[0])
        py = int(self.y + camera_offset[1])
        tail_x = int(px - math.cos(self.angle) * 12)
        tail_y = int(py - math.sin(self.angle) * 12)
        
        pygame.draw.line(surface, COLOR_WHITE, (px, py), (tail_x, tail_y), 3)
        pygame.draw.line(surface, self.color, (px, py), (tail_x, tail_y), 1)

class Enemy:
    """Base class for varied vector cyber enemies."""
    def __init__(self, x, y, enemy_type=1):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type  # 1: Chaser, 2: Shooter, 3: Heavy Tank, 4: Boss
        self.alive = True
        
        # Setup stats based on archetype
        if enemy_type == 1: # Fast Chaser
            self.hp = 30
            self.max_hp = 30
            self.speed = 180
            self.radius = 14
            self.color = COLOR_RED
            self.score_value = 100
        elif enemy_type == 2: # Ranged Shooter
            self.hp = 50
            self.max_hp = 50
            self.speed = 110
            self.radius = 18
            self.color = COLOR_ORANGE
            self.shoot_cooldown = 2.0
            self.score_value = 250
        elif enemy_type == 3: # Heavy Tank
            self.hp = 160
            self.max_hp = 160
            self.speed = 65
            self.radius = 26
            self.color = COLOR_PURPLE
            self.score_value = 500
        elif enemy_type == 4: # Level Boss
            self.hp = 1200
            self.max_hp = 1200
            self.speed = 45
            self.radius = 50
            self.color = COLOR_MAGENTA
            self.shoot_cooldown = 1.0
            self.score_value = 5000

        self.angle = 0

    def update(self, dt, player, projectiles, sound_mgr):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            dx /= dist
            dy /= dist
        
        self.angle = math.atan2(dy, dx)

        # Movement Behaviors
        if self.enemy_type == 1 or self.enemy_type == 3:
            self.x += dx * self.speed * dt
            self.y += dy * self.speed * dt
        elif self.enemy_type == 2: # Keep distance and shoot
            if dist > 250:
                self.x += dx * self.speed * dt
                self.y += dy * self.speed * dt
            elif dist < 150:
                self.x -= dx * self.speed * dt
                self.y -= dy * self.speed * dt
            
            # Weapon Logic
            self.shoot_cooldown -= dt
            if self.shoot_cooldown <= 0:
                self.shoot_cooldown = 2.2
                projectiles.append(Projectile(self.x, self.y, self.angle, speed=400, is_enemy=True, damage=15, color=COLOR_ORANGE))
                sound_mgr.play('laser')
                
        elif self.enemy_type == 4: # Boss Mechanics
            self.x += dx * self.speed * dt
            self.y += dy * self.speed * dt
            self.shoot_cooldown -= dt
            if self.shoot_cooldown <= 0:
                self.shoot_cooldown = 1.2
                # Circular burst pattern
                for a_step in range(8):
                    burst_angle = self.angle + (a_step * math.pi / 4)
                    projectiles.append(Projectile(self.x, self.y, burst_angle, speed=350, is_enemy=True, damage=20, color=COLOR_MAGENTA))
                sound_mgr.play('laser')

    def draw(self, surface, camera_offset=(0,0)):
        px = int(self.x + camera_offset[0])
        py = int(self.y + camera_offset[1])

        if self.enemy_type == 1:
            # Diamond shape
            pts = [
                (px + math.cos(self.angle) * self.radius, py + math.sin(self.angle) * self.radius),
                (px + math.cos(self.angle + 1.57) * (self.radius*0.7), py + math.sin(self.angle + 1.57) * (self.radius*0.7)),
                (px + math.cos(self.angle + 3.14) * self.radius, py + math.sin(self.angle + 3.14) * self.radius),
                (px + math.cos(self.angle - 1.57) * (self.radius*0.7), py + math.sin(self.angle - 1.57) * (self.radius*0.7))
            ]
            pygame.draw.polygon(surface, self.color, pts, 2)
        elif self.enemy_type == 2:
            # Pentagon shape
            pts = [(px + math.cos(self.angle + i * 1.25) * self.radius, py + math.sin(self.angle + i * 1.25) * self.radius) for i in range(5)]
            pygame.draw.polygon(surface, self.color, pts, 2)
        elif self.enemy_type == 3 or self.enemy_type == 4:
            # Hexagon / Octagon heavy geometry
            sides = 6 if self.enemy_type == 3 else 8
            pts = [(px + math.cos(self.angle + i * (2*math.pi/sides)) * self.radius, py + math.sin(self.angle + i * (2*math.pi/sides)) * self.radius) for i in range(sides)]
            pygame.draw.polygon(surface, COLOR_WHITE, pts, 1)
            pygame.draw.polygon(surface, self.color, pts, 3)

        # Health Bar overlay for Tank & Boss
        if self.hp < self.max_hp and self.enemy_type in (3, 4):
            bar_w = self.radius * 2
            bar_h = 4
            health_pct = max(0, self.hp / self.max_hp)
            pygame.draw.rect(surface, (50, 50, 50), (px - self.radius, py - self.radius - 12, bar_w, bar_h))
            pygame.draw.rect(surface, self.color, (px - self.radius, py - self.radius - 12, int(bar_w * health_pct), bar_h))

class PowerUp:
    """Collectible drop providing tactical advantages."""
    def __init__(self, x, y, ptype):
        self.x = x
        self.y = y
        self.ptype = ptype  # 'health', 'shield', 'weapon', 'nova'
        self.radius = 12
        self.alive = True
        self.anim_t = random.uniform(0, 6.28)

        if ptype == 'health':   self.color = COLOR_NEON_GREEN
        elif ptype == 'shield': self.color = COLOR_CYAN
        elif ptype == 'weapon': self.color = COLOR_YELLOW
        elif ptype == 'nova':   self.color = COLOR_MAGENTA

    def update(self, dt):
        self.anim_t += dt * 4

    def draw(self, surface, glow_cache, camera_offset=(0,0)):
        px = int(self.x + camera_offset[0])
        py = int(self.y + camera_offset[1] + math.sin(self.anim_t) * 4)

        glow = glow_cache.get_glow_circle(24, self.color)
        surface.blit(glow, (px - 24, py - 24), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surface, COLOR_WHITE, (px, py), 6)
        pygame.draw.circle(surface, self.color, (px, py), 8, 2)

# ==============================================================================
# MAIN GAME ENGINE CLASS
# ==============================================================================
class NeonOverdriveGame:
    """Core Game Controller Engine managing states, rendering, logic & events."""
    def __init__(self):
        # Display setup
        self.screen_width = DEFAULT_WIDTH
        self.screen_height = DEFAULT_HEIGHT
        self.fullscreen = False
        
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), flags)
        pygame.display.set_caption(GAME_TITLE)
        
        self.clock = pygame.time.Clock()
        self.is_running = True

        # Systems Init
        self.save_data = SaveSystem.load_data()
        self.sound_mgr = SoundFXManager()
        self.sound_mgr.set_volume(self.save_data.get("volume", 0.7))
        
        self.camera = CameraShake()
        self.camera.enabled = self.save_data.get("shake_enabled", True)
        self.glow_cache = DynamicGlowCache()

        # Fonts
        self.font_title = pygame.font.SysFont("Impact", 64)
        self.font_large = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_medium = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_small = pygame.font.SysFont("Consolas", 14, bold=True)

        # Game State Machine ('LOADING', 'MENU', 'SETTINGS', 'PLAYING', 'PAUSED', 'GAMEOVER', 'VICTORY')
        self.state = 'LOADING'
        self.loading_progress = 0.0

        # High Score & Stats
        self.highscore = self.save_data.get("highscore", 0)
        self.score = 0
        self.multiplier = 1
        self.combo_count = 0
        self.combo_timer = 0.0
        self.current_level = 1
        self.enemies_killed = 0

        # Entity collections
        self.player = None
        self.projectiles = []
        self.enemies = []
        self.powerups = []
        self.particles = []
        self.floating_texts = []

        # UI Elements
        self.ui_buttons = {}
        self.ui_sliders = {}
        self.init_ui()

        # Starfield Parallax
        self.stars = [
            [random.randint(0, DEFAULT_WIDTH), random.randint(0, DEFAULT_HEIGHT), random.uniform(0.5, 2.5)]
            for _ in range(120)
        ]

    def init_ui(self):
        """Build UI layouts for state transitions."""
        cx = self.screen_width // 2
        cy = self.screen_height // 2

        # Menu Buttons
        self.ui_buttons['menu_play'] = Button(cx - 110, cy - 20, 220, 50, "START GAME", self.font_medium, self.start_new_game, COLOR_CYAN)
        self.ui_buttons['menu_settings'] = Button(cx - 110, cy + 45, 220, 50, "SETTINGS", self.font_medium, lambda: self.set_state('SETTINGS'), COLOR_CYAN)
        self.ui_buttons['menu_exit'] = Button(cx - 110, cy + 110, 220, 50, "EXIT", self.font_medium, self.quit_game, COLOR_RED)

        # Settings Controls
        self.ui_sliders['vol_slider'] = Slider(cx - 120, cy - 40, 240, 20, "SOUND VOLUME", self.font_medium, self.sound_mgr.volume, self.sound_mgr.set_volume)
        self.ui_buttons['toggle_shake'] = Button(cx - 120, cy + 20, 240, 45, f"SHAKE: {'ON' if self.camera.enabled else 'OFF'}", self.font_medium, self.toggle_shake, COLOR_CYAN)
        self.ui_buttons['toggle_fullscreen'] = Button(cx - 120, cy + 80, 240, 45, "TOGGLE FULLSCREEN", self.font_medium, self.toggle_fullscreen_mode, COLOR_CYAN)
        self.ui_buttons['settings_back'] = Button(cx - 120, cy + 150, 240, 45, "BACK TO MENU", self.font_medium, lambda: self.set_state('MENU'), COLOR_WHITE)

        # Pause Menu
        self.ui_buttons['pause_resume'] = Button(cx - 110, cy - 50, 220, 50, "RESUME", self.font_medium, lambda: self.set_state('PLAYING'), COLOR_CYAN)
        self.ui_buttons['pause_restart'] = Button(cx - 110, cy + 15, 220, 50, "RESTART", self.font_medium, self.start_new_game, COLOR_YELLOW)
        self.ui_buttons['pause_menu'] = Button(cx - 110, cy + 80, 220, 50, "MAIN MENU", self.font_medium, lambda: self.set_state('MENU'), COLOR_RED)

        # Game Over / Victory Screen
        self.ui_buttons['gov_retry'] = Button(cx - 110, cy + 80, 220, 50, "PLAY AGAIN", self.font_medium, self.start_new_game, COLOR_NEON_GREEN)
        self.ui_buttons['gov_menu'] = Button(cx - 110, cy + 145, 220, 50, "MAIN MENU", self.font_medium, lambda: self.set_state('MENU'), COLOR_WHITE)

    def set_state(self, new_state):
        self.state = new_state
        self.sound_mgr.play('click')

    def toggle_shake(self):
        self.camera.enabled = not self.camera.enabled
        self.ui_buttons['toggle_shake'].text = f"SHAKE: {'ON' if self.camera.enabled else 'OFF'}"
        self.save_data['shake_enabled'] = self.camera.enabled
        SaveSystem.save_data(self.save_data)

    def toggle_fullscreen_mode(self):
        self.fullscreen = not self.fullscreen
        self.save_data['fullscreen'] = self.fullscreen
        SaveSystem.save_data(self.save_data)
        
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
            self.screen = pygame.display.set_mode((0, 0), flags)
            self.screen_width, self.screen_height = self.screen.get_size()
        else:
            self.screen_width = DEFAULT_WIDTH
            self.screen_height = DEFAULT_HEIGHT
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), flags)
        self.init_ui()

    def start_new_game(self):
        self.player = Player(self.screen_width // 2, self.screen_height // 2)
        self.projectiles.clear()
        self.enemies.clear()
        self.powerups.clear()
        self.particles.clear()
        self.floating_texts.clear()
        
        self.score = 0
        self.multiplier = 1
        self.combo_count = 0
        self.combo_timer = 0
        self.current_level = 1
        self.enemies_killed = 0
        
        self.spawn_wave()
        self.set_state('PLAYING')

    def spawn_wave(self):
        """Spawns wave enemies scaling in difficulty per level."""
        enemy_count = 6 + self.current_level * 3
        is_boss_level = (self.current_level % 3 == 0)

        if is_boss_level:
            # Spawn Boss
            bx = self.screen_width // 2
            by = 100
            self.enemies.append(Enemy(bx, by, enemy_type=4))
            self.floating_texts.append(FloatingText(bx, by + 60, "BOSS DETECTED!", COLOR_MAGENTA, self.font_large, 3.0))
        else:
            for _ in range(enemy_count):
                # Spawn around screen edges
                side = random.randint(0, 3)
                if side == 0: x, y = random.randint(0, self.screen_width), -30
                elif side == 1: x, y = self.screen_width + 30, random.randint(0, self.screen_height)
                elif side == 2: x, y = random.randint(0, self.screen_width), self.screen_height + 30
                else: x, y = -30, random.randint(0, self.screen_height)

                # Pick enemy archetype
                roll = random.random()
                if roll < 0.6: etype = 1
                elif roll < 0.85: etype = 2
                else: etype = 3

                self.enemies.append(Enemy(x, y, etype))

    def trigger_nova(self):
        """Activates powerful Nova Pulse clearing nearby bullets and heavy damage."""
        if self.player.nova_energy >= 100.0:
            self.player.nova_energy = 0.0
            self.camera.add_shake(25)
            self.sound_mgr.play('nova')

            # Shockwave Particles
            for i in range(72):
                a = i * (math.pi / 36.0)
                vx = math.cos(a) * 600
                vy = math.sin(a) * 600
                self.particles.append(Particle(self.player.x, self.player.y, vx, vy, COLOR_MAGENTA, 6, 0.6, "circle"))

            # Clear nearby enemy bullets
            self.projectiles = [p for p in self.projectiles if not p.is_enemy]

            # Damage enemies in blast radius
            for enemy in self.enemies:
                dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
                if dist < 350:
                    enemy.hp -= 250
                    if enemy.hp <= 0:
                        self.handle_enemy_death(enemy)

    def handle_enemy_death(self, enemy):
        """Handles point calculation, combo scaling, drops, and death explosion particles."""
        enemy.alive = False
        self.enemies_killed += 1
        self.camera.add_shake(6 if enemy.enemy_type != 4 else 20)
        self.sound_mgr.play('explosion')

        # Multiplier and Score logic
        self.combo_count += 1
        self.combo_timer = 3.0
        self.multiplier = min(10, 1 + self.combo_count // 5)
        gained_score = enemy.score_value * self.multiplier
        self.score += gained_score

        # Charge Nova energy
        self.player.nova_energy = min(100.0, self.player.nova_energy + 12.0)

        # Floating score text
        self.floating_texts.append(FloatingText(enemy.x, enemy.y, f"+{gained_score}", COLOR_CYAN, self.font_medium))
        if self.combo_count % 5 == 0:
            self.floating_texts.append(FloatingText(self.player.x, self.player.y - 40, f"{self.combo_count}x COMBO!", COLOR_YELLOW, self.font_large))

        # Explosive particle burst
        p_color = enemy.color
        for _ in range(18 if enemy.enemy_type != 4 else 60):
            vx = random.uniform(-250, 250)
            vy = random.uniform(-250, 250)
            self.particles.append(Particle(enemy.x, enemy.y, vx, vy, p_color, random.randint(3, 7), random.uniform(0.3, 0.7)))

        # Chance to drop powerups
        if random.random() < 0.22 or enemy.enemy_type == 4:
            ptype = random.choice(['health', 'shield', 'weapon', 'nova'])
            self.powerups.append(PowerUp(enemy.x, enemy.y, ptype))

        # Check HighScore update
        if self.score > self.highscore:
            self.highscore = self.score
            self.save_data['highscore'] = self.highscore
            SaveSystem.save_data(self.save_data)

    def fire_player_weapon(self):
        """Fires weaponry depending on player's current weapon tier."""
        if self.player.shoot_cooldown <= 0:
            self.player.shoot_cooldown = 0.12
            self.sound_mgr.play('laser')
            
            p_x, p_y, angle = self.player.x, self.player.y, self.player.angle
            
            if self.player.weapon_level == 1:
                self.projectiles.append(Projectile(p_x, p_y, angle, color=COLOR_CYAN))
            elif self.player.weapon_level == 2:
                # Dual parallel shot
                off_x = math.cos(angle + 1.57) * 8
                off_y = math.sin(angle + 1.57) * 8
                self.projectiles.append(Projectile(p_x + off_x, p_y + off_y, angle, color=COLOR_CYAN))
                self.projectiles.append(Projectile(p_x - off_x, p_y - off_y, angle, color=COLOR_CYAN))
            elif self.player.weapon_level >= 3:
                # Spread Shot
                self.projectiles.append(Projectile(p_x, p_y, angle, color=COLOR_CYAN))
                self.projectiles.append(Projectile(p_x, p_y, angle - 0.15, color=COLOR_CYAN))
                self.projectiles.append(Projectile(p_x, p_y, angle + 0.15, color=COLOR_CYAN))

    # ==========================================================================
    # UPDATE LOGIC
    # ==========================================================================
    def update(self, dt):
        """Main Physics & Logic updates."""
        # Screen Shake Decay
        self.camera.update(dt)

        # Starfield Parallax Scroll
        for star in self.stars:
            star[1] += star[2] * 20 * dt
            if star[1] > self.screen_height:
                star[1] = 0
                star[0] = random.randint(0, self.screen_width)

        if self.state == 'LOADING':
            self.loading_progress += dt * 1.5
            if self.loading_progress >= 1.0:
                self.set_state('MENU')
            return

        if self.state != 'PLAYING':
            # Update background UI elements on non-playing states
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.ui_buttons.values():
                btn.update(dt, mouse_pos)
            return

        # --- GAMEPLAY UPDATE LOOP ---
        mouse_pos = pygame.mouse.get_pos()
        self.player.handle_input(dt, mouse_pos)
        self.player.update(dt, (self.screen_width, self.screen_height))

        # Mouse Shooting trigger
        if pygame.mouse.get_pressed()[0]:
            self.fire_player_weapon()

        # Update Combo Decay
        if self.combo_timer > 0:
            self.combo_timer -= dt
        else:
            self.combo_count = 0
            self.multiplier = 1

        # Projectiles update
        for proj in self.projectiles:
            proj.update(dt, (self.screen_width, self.screen_height))
        self.projectiles = [p for p in self.projectiles if p.alive]

        # Particles update
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.lifetime > 0]

        # Floating Texts update
        for txt in self.floating_texts:
            txt.update(dt)
        self.floating_texts = [t for t in self.floating_texts if t.duration > 0]

        # Powerups update
        for pow_up in self.powerups:
            pow_up.update(dt)
            # Collision with player
            dist = math.hypot(pow_up.x - self.player.x, pow_up.y - self.player.y)
            if dist < self.player.radius + pow_up.radius:
                self.sound_mgr.play('powerup')
                if pow_up.ptype == 'health':
                    self.player.health = min(self.player.max_health, self.player.health + 35)
                elif pow_up.ptype == 'shield':
                    self.player.shield = self.player.max_shield
                elif pow_up.ptype == 'weapon':
                    self.player.weapon_level = min(3, self.player.weapon_level + 1)
                elif pow_up.ptype == 'nova':
                    self.player.nova_energy = 100.0
                pow_up.alive = False
        self.powerups = [p for p in self.powerups if p.alive]

        # Enemies Update & Collisions
        for enemy in self.enemies:
            enemy.update(dt, self.player, self.projectiles, self.sound_mgr)

            # Player-Enemy Collision
            dist_p = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist_p < enemy.radius + self.player.radius:
                self.player.take_damage(25, self.camera, self.sound_mgr)
                enemy.hp -= 40
                if enemy.hp <= 0:
                    self.handle_enemy_death(enemy)

            # Projectile-Enemy Collisions
            for proj in self.projectiles:
                if not proj.is_enemy and proj.alive:
                    dist_b = math.hypot(enemy.x - proj.x, enemy.y - proj.y)
                    if dist_b < enemy.radius + proj.radius:
                        proj.alive = False
                        enemy.hp -= proj.damage
                        self.sound_mgr.play('hit')
                        
                        # Hit Sparks
                        for _ in range(3):
                            self.particles.append(Particle(proj.x, proj.y, random.uniform(-80, 80), random.uniform(-80, 80), COLOR_WHITE, 3, 0.2))

                        if enemy.hp <= 0:
                            self.handle_enemy_death(enemy)

        self.enemies = [e for e in self.enemies if e.alive]

        # Enemy Bullet Collision with Player
        for proj in self.projectiles:
            if proj.is_enemy and proj.alive:
                dist = math.hypot(self.player.x - proj.x, self.player.y - proj.y)
                if dist < self.player.radius + proj.radius:
                    proj.alive = False
                    self.player.take_damage(proj.damage, self.camera, self.sound_mgr)

        # Check Player Death
        if self.player.health <= 0:
            self.sound_mgr.play('explosion')
            self.camera.add_shake(30)
            self.set_state('GAMEOVER')

        # Level Progression Check
        if len(self.enemies) == 0:
            self.current_level += 1
            self.floating_texts.append(FloatingText(self.screen_width // 2, self.screen_height // 2 - 50, f"LEVEL {self.current_level} CLEAR!", COLOR_NEON_GREEN, self.font_large, 2.5))
            self.spawn_wave()

    # ==========================================================================
    # RENDERING ENGINE
    # ==========================================================================
    def draw_grid_background(self):
        """Renders futuristic grid pattern."""
        self.screen.fill(COLOR_BG)
        cam_offset = self.camera.get_offset()

        # Stars
        for star in self.stars:
            sx = int(star[0] + cam_offset[0] * 0.2)
            sy = int(star[1] + cam_offset[1] * 0.2)
            color = (180, 200, 255) if star[2] > 1.5 else (80, 90, 120)
            pygame.draw.circle(self.screen, color, (sx % self.screen_width, sy % self.screen_height), int(star[2]))

        # Vector Grid Lines
        grid_size = 64
        off_x = cam_offset[0] % grid_size
        off_y = cam_offset[1] % grid_size
        
        for x in range(0, self.screen_width + grid_size, grid_size):
            pygame.draw.line(self.screen, COLOR_GRID, (x + off_x, 0), (x + off_x, self.screen_height))
        for y in range(0, self.screen_height + grid_size, grid_size):
            pygame.draw.line(self.screen, COLOR_GRID, (0, y + off_y), (self.screen_width, y + off_y))

    def draw_hud(self):
        """Displays Player HUD (Health, Shield, Score, Combo, Level)."""
        cam_off = self.camera.get_offset()
        
        # Health & Shield Bars Container
        hud_surface = pygame.Surface((320, 90), pygame.SRCALPHA)
        hud_surface.fill((15, 18, 30, 200))
        pygame.draw.rect(hud_surface, COLOR_CYAN, hud_surface.get_rect(), 1, border_radius=6)
        
        # Health Bar
        pygame.draw.rect(hud_surface, (50, 15, 20), (15, 20, 200, 12), border_radius=3)
        hp_pct = max(0, self.player.health / self.player.max_health)
        pygame.draw.rect(hud_surface, COLOR_RED, (15, 20, int(200 * hp_pct), 12), border_radius=3)
        lbl_hp = self.font_small.render("HP", True, COLOR_WHITE)
        hud_surface.blit(lbl_hp, (222, 18))

        # Shield Bar
        pygame.draw.rect(hud_surface, (15, 30, 50), (15, 42, 200, 10), border_radius=3)
        sp_pct = max(0, self.player.shield / self.player.max_shield)
        pygame.draw.rect(hud_surface, COLOR_CYAN, (15, 42, int(200 * sp_pct), 10), border_radius=3)
        lbl_sp = self.font_small.render("SHD", True, COLOR_WHITE)
        hud_surface.blit(lbl_sp, (222, 40))

        # Nova Bar
        pygame.draw.rect(hud_surface, (40, 15, 40), (15, 60, 200, 8), border_radius=3)
        nv_pct = max(0, self.player.nova_energy / 100.0)
        nova_col = COLOR_MAGENTA if self.player.nova_energy >= 100.0 else COLOR_PURPLE
        pygame.draw.rect(hud_surface, nova_col, (15, 60, int(200 * nv_pct), 8), border_radius=3)
        lbl_nv = self.font_small.render("NOVA [E]", True, COLOR_MAGENTA if self.player.nova_energy >= 100 else COLOR_WHITE)
        hud_surface.blit(lbl_nv, (222, 56))

        self.screen.blit(hud_surface, (20 + cam_off[0], 20 + cam_off[1]))

        # Score & Level Banner
        score_txt = self.font_large.render(f"{self.score:07d}", True, COLOR_WHITE)
        self.screen.blit(score_txt, (self.screen_width - score_txt.get_width() - 25, 20))

        lvl_txt = self.font_medium.render(f"LEVEL {self.current_level}", True, COLOR_CYAN)
        self.screen.blit(lvl_txt, (self.screen_width - lvl_txt.get_width() - 25, 65))

        # Multiplier Dynamic HUD Banner
        if self.multiplier > 1:
            mult_txt = self.font_large.render(f"{self.multiplier}x MULTIPLIER", True, COLOR_YELLOW)
            self.screen.blit(mult_txt, (self.screen_width // 2 - mult_txt.get_width() // 2, 25))

        # FPS Counter
        fps = int(self.clock.get_fps())
        fps_txt = self.font_small.render(f"FPS: {fps}", True, COLOR_NEON_GREEN if fps >= 55 else COLOR_RED)
        self.screen.blit(fps_txt, (10, self.screen_height - 25))

    def render(self):
        """Renders graphics depending on state."""
        self.draw_grid_background()
        cam_off = self.camera.get_offset()

        if self.state == 'LOADING':
            # Render animated splash loading screen
            cx, cy = self.screen_width // 2, self.screen_height // 2
            title = self.font_title.render("NEON OVERDRIVE", True, COLOR_CYAN)
            self.screen.blit(title, (cx - title.get_width() // 2, cy - 80))

            # Loading Bar Outer Frame
            bar_rect = pygame.Rect(cx - 150, cy + 20, 300, 16)
            pygame.draw.rect(self.screen, (30, 35, 60), bar_rect, border_radius=8)
            
            # Progress fill
            fill_rect = pygame.Rect(cx - 150, cy + 20, int(300 * self.loading_progress), 16)
            pygame.draw.rect(self.screen, COLOR_CYAN, fill_rect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_WHITE, bar_rect, 2, border_radius=8)

        elif self.state == 'MENU':
            cx, cy = self.screen_width // 2, self.screen_height // 2
            title = self.font_title.render("NEON OVERDRIVE", True, COLOR_CYAN)
            glow_title = self.glow_cache.get_glow_circle(120, COLOR_CYAN)
            
            self.screen.blit(glow_title, (cx - 120, cy - 200), special_flags=pygame.BLEND_ADD)
            self.screen.blit(title, (cx - title.get_width() // 2, cy - 140))

            hs_txt = self.font_medium.render(f"BEST SCORE: {self.highscore:07d}", True, COLOR_YELLOW)
            self.screen.blit(hs_txt, (cx - hs_txt.get_width() // 2, cy - 70))

            self.ui_buttons['menu_play'].draw(self.screen)
            self.ui_buttons['menu_settings'].draw(self.screen)
            self.ui_buttons['menu_exit'].draw(self.screen)

        elif self.state == 'SETTINGS':
            cx, cy = self.screen_width // 2, self.screen_height // 2
            title = self.font_large.render("SYSTEM SETTINGS", True, COLOR_WHITE)
            self.screen.blit(title, (cx - title.get_width() // 2, cy - 120))

            self.ui_sliders['vol_slider'].draw(self.screen)
            self.ui_buttons['toggle_shake'].draw(self.screen)
            self.ui_buttons['toggle_fullscreen'].draw(self.screen)
            self.ui_buttons['settings_back'].draw(self.screen)

        elif self.state in ('PLAYING', 'PAUSED', 'GAMEOVER'):
            # Draw Game World
            for p in self.powerups:
                p.draw(self.screen, self.glow_cache, cam_off)

            for enemy in self.enemies:
                enemy.draw(self.screen, cam_off)

            for proj in self.projectiles:
                proj.draw(self.screen, cam_off)

            if self.player and self.player.health > 0:
                self.player.draw(self.screen, self.glow_cache, cam_off)

            for p in self.particles:
                p.draw(self.screen, cam_off)

            for txt in self.floating_texts:
                txt.draw(self.screen, cam_off)

            self.draw_hud()

            # State Overlays
            if self.state == 'PAUSED':
                overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                overlay.fill((5, 5, 12, 180))
                self.screen.blit(overlay, (0, 0))

                cx, cy = self.screen_width // 2, self.screen_height // 2
                title = self.font_large.render("GAME PAUSED", True, COLOR_WHITE)
                self.screen.blit(title, (cx - title.get_width() // 2, cy - 120))

                self.ui_buttons['pause_resume'].draw(self.screen)
                self.ui_buttons['pause_restart'].draw(self.screen)
                self.ui_buttons['pause_menu'].draw(self.screen)

            elif self.state == 'GAMEOVER':
                overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                overlay.fill((20, 5, 10, 210))
                self.screen.blit(overlay, (0, 0))

                cx, cy = self.screen_width // 2, self.screen_height // 2
                title = self.font_title.render("SYSTEM CRASHED", True, COLOR_RED)
                self.screen.blit(title, (cx - title.get_width() // 2, cy - 140))

                score_info = self.font_large.render(f"FINAL SCORE: {self.score}", True, COLOR_WHITE)
                self.screen.blit(score_info, (cx - score_info.get_width() // 2, cy - 60))

                kills_info = self.font_medium.render(f"ENEMIES PURGED: {self.enemies_killed}", True, COLOR_CYAN)
                self.screen.blit(kills_info, (cx - kills_info.get_width() // 2, cy - 10))

                self.ui_buttons['gov_retry'].draw(self.screen)
                self.ui_buttons['gov_menu'].draw(self.screen)

        pygame.display.flip()

    # ==========================================================================
    # INPUT EVENT CONTROLLER
    # ==========================================================================
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == 'PLAYING':
                        self.set_state('PAUSED')
                    elif self.state == 'PAUSED':
                        self.set_state('PLAYING')
                    elif self.state == 'SETTINGS':
                        self.set_state('MENU')

                if self.state == 'PLAYING':
                    if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        self.player.trigger_dash(self.sound_mgr, self.particles)
                    elif event.key == pygame.K_e:
                        self.trigger_nova()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3 and self.state == 'PLAYING':  # Right Click Dash
                    self.player.trigger_dash(self.sound_mgr, self.particles)

            # Route UI events based on active Machine State
            if self.state == 'MENU':
                self.ui_buttons['menu_play'].handle_event(event, self.sound_mgr)
                self.ui_buttons['menu_settings'].handle_event(event, self.sound_mgr)
                self.ui_buttons['menu_exit'].handle_event(event, self.sound_mgr)

            elif self.state == 'SETTINGS':
                self.ui_sliders['vol_slider'].handle_event(event)
                self.ui_buttons['toggle_shake'].handle_event(event, self.sound_mgr)
                self.ui_buttons['toggle_fullscreen'].handle_event(event, self.sound_mgr)
                self.ui_buttons['settings_back'].handle_event(event, self.sound_mgr)

            elif self.state == 'PAUSED':
                self.ui_buttons['pause_resume'].handle_event(event, self.sound_mgr)
                self.ui_buttons['pause_restart'].handle_event(event, self.sound_mgr)
                self.ui_buttons['pause_menu'].handle_event(event, self.sound_mgr)

            elif self.state == 'GAMEOVER':
                self.ui_buttons['gov_retry'].handle_event(event, self.sound_mgr)
                self.ui_buttons['gov_menu'].handle_event(event, self.sound_mgr)

    def quit_game(self):
        """Gracefully closes Pygame and writes settings to local storage."""
        SaveSystem.save_data(self.save_data)
        self.is_running = False
        pygame.quit()
        sys.exit()

    def run(self):
        """Primary Engine Game Loop operating at fixed target FPS."""
        while self.is_running:
            dt = self.clock.tick(TARGET_FPS) / 1000.0  # Delta Time in Seconds
            dt = min(0.05, dt)  # Cap max delta time to prevent physics clipping
            
            self.handle_events()
            self.update(dt)
            self.render()

# ==============================================================================
# MAIN APPLICATION ENTRY POINT
# ==============================================================================
if __name__ == '__main__':
    # Launch Neon Overdrive Engine
    game = NeonOverdriveGame()
    game.run()
