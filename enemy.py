"""
Enemy hierarchy. All subclasses inherit movement and status-effect logic from Enemy.
Subclasses only override _draw_body() for unique visuals.

Flying enemies (Phantom) are skipped by towers that lack air_targeting=True.
path_progress accumulates pixels traveled and is used for first/last targeting.
"""

import pygame
import math
from constants import (ENEMY_STATS, COLOR_BLACK, COLOR_RED, COLOR_GREEN,
                       COLOR_CYAN, COLOR_BLUE, COLOR_ORANGE, COLOR_YELLOW, COLOR_WATER)
from effects import SlowEffect, FreezeEffect, BurnEffect, WetEffect


class Enemy:
    def __init__(self, waypoints: list, enemy_type: str):
        s = ENEMY_STATS[enemy_type]
        self.enemy_type     = enemy_type
        self.waypoints      = waypoints
        self.waypoint_index = 1        # next target waypoint (index 0 = spawn point)

        self.x = float(waypoints[0][0])
        self.y = float(waypoints[0][1])

        self.max_hp     = s['hp']
        self.hp         = float(self.max_hp)
        self.base_speed = s['speed']
        self.armor      = s['armor']   # fraction of damage absorbed
        self.radius     = s['radius']
        self.color      = s['color']
        self.flying     = s['flying']
        self.reward     = s['reward']

        # Cumulative pixels traveled — used for first/last targeting comparisons
        self.path_progress = 0.0

        self.alive       = True
        self.reached_end = False
        self.effects: list = []

        self.freeze_resist    = s.get('freeze_resist', 0.0)
        self.burn_resist      = s.get('burn_resist',   0.0)
        self.chain_resist     = s.get('chain_resist',  False)
        self.lightning_stacks = 0

    # ── speed with effects ────────────────────────────────────────────────────
    @property
    def current_speed(self) -> float:
        for e in self.effects:
            if e.effect_type == 'freeze' and e.active:
                return 0.0
        speed = self.base_speed
        for e in self.effects:
            if e.effect_type in ('slow', 'wet') and e.active:
                speed = min(speed, self.base_speed * e.slow_factor)
        return speed

    # ── damage ────────────────────────────────────────────────────────────────
    def apply_damage(self, amount: float, armor_pierce: bool = False):
        if not armor_pierce:
            amount *= (1.0 - self.armor)
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False

    # ── status effects ────────────────────────────────────────────────────────
    def apply_effect(self, effect):
        """
        Resistances are applied first (scaling or blocking the effect).
        Freeze: extends existing freeze by base/2^n rather than resetting.
        Burn: refreshes duration rather than stacking (prevents infinite DoT abuse).
        Slow: stacks; current_speed takes the minimum multiplier.
        """
        if isinstance(effect, FreezeEffect):
            # Apply freeze resistance: scale duration down
            effective_dur = effect.freeze_duration * (1.0 - self.freeze_resist)
            if effective_dur <= 0.1:
                return   # effectively immune — skip
            effect.duration        = effective_dur
            effect.freeze_duration = effective_dur

            existing = next(
                (e for e in self.effects if e.effect_type == 'freeze' and e.active), None)
            if existing:
                extension = effect.freeze_duration / (2 ** (existing.extension_count + 1))
                existing.duration        += extension
                existing.extension_count += 1
                existing.slow_duration    = max(existing.slow_duration, effect.slow_duration)
            else:
                effect.extension_count = 0
                self.effects.append(effect)

        elif isinstance(effect, BurnEffect):
            # Apply burn resistance: scale damage per tick
            if self.burn_resist >= 1.0:
                return
            effect.damage_per_tick *= (1.0 - self.burn_resist)
            for e in self.effects:
                if e.effect_type == 'burn' and e.active:
                    e.elapsed     = 0.0
                    e.tick_timer  = 0.0
                    e.damage_per_tick = max(e.damage_per_tick, effect.damage_per_tick)
                    return
            self.effects.append(effect)

        elif isinstance(effect, WetEffect):
            for e in self.effects:
                if e.effect_type == 'wet' and e.active:
                    e.elapsed     = 0.0
                    e.slow_factor = min(e.slow_factor, effect.slow_factor)  # stronger wins
                    return
            self.effects.append(effect)

        else:
            self.effects.append(effect)

    # ── update ────────────────────────────────────────────────────────────────
    def update(self, dt: float):
        if not self.alive:
            return

        # Advance and prune effects; queue post-freeze slow
        surviving = []
        for eff in self.effects:
            eff.update(dt)
            if eff.active:
                surviving.append(eff)
            elif eff.effect_type == 'freeze' and not eff.thawed:
                eff.thawed = True
                surviving.append(SlowEffect(eff.slow_duration, eff.slow_factor))
        self.effects = surviving

        # Burn ticks
        for eff in self.effects:
            if eff.effect_type == 'burn' and eff.active and eff.consume_tick():
                self.hp -= eff.damage_per_tick
                if self.hp <= 0:
                    self.alive = False
                    return

        # Movement along waypoints
        if self.waypoint_index >= len(self.waypoints):
            self.reached_end = True
            self.alive = False
            return

        speed = self.current_speed
        if speed <= 0:
            return

        move_dist = speed * dt
        self._advance(move_dist)

    def _advance(self, remaining: float):
        """Consume `remaining` pixels of movement, crossing waypoints as needed."""
        while remaining > 0 and self.waypoint_index < len(self.waypoints):
            tx, ty = self.waypoints[self.waypoint_index]
            dx, dy = tx - self.x, ty - self.y
            dist   = math.hypot(dx, dy)

            if dist <= remaining:
                self.path_progress   += dist
                self.x, self.y        = float(tx), float(ty)
                self.waypoint_index  += 1
                remaining            -= dist
            else:
                f             = remaining / dist
                self.x       += dx * f
                self.y       += dy * f
                self.path_progress += remaining
                remaining     = 0

        if self.waypoint_index >= len(self.waypoints):
            self.reached_end = True
            self.alive       = False

    # ── draw ─────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        if not self.alive:
            return
        ix, iy = int(self.x), int(self.y)
        self._draw_body(surface, ix, iy)
        self._draw_status_rings(surface, ix, iy)
        self._draw_hp_bar(surface, ix, iy)

    def _draw_body(self, surface: pygame.Surface, x: int, y: int):
        pygame.draw.circle(surface, self.color, (x, y), self.radius)
        pygame.draw.circle(surface, COLOR_BLACK, (x, y), self.radius, 2)

    def _draw_status_rings(self, surface: pygame.Surface, x: int, y: int):
        """Thin coloured rings indicate active effects at a glance."""
        slow_offset = 0
        for eff in self.effects:
            if not eff.active:
                continue
            if eff.effect_type == 'freeze':
                pygame.draw.circle(surface, COLOR_CYAN, (x, y), self.radius + 5, 2)
            elif eff.effect_type == 'slow':
                pygame.draw.circle(surface, COLOR_BLUE,
                                   (x, y), self.radius + 3 + slow_offset, 2)
                slow_offset += 3
            elif eff.effect_type == 'burn':
                pygame.draw.circle(surface, COLOR_ORANGE, (x, y), self.radius + 6, 2)
            elif eff.effect_type == 'wet':
                pygame.draw.circle(surface, COLOR_WATER, (x, y), self.radius + 4, 2)

    def _draw_hp_bar(self, surface: pygame.Surface, x: int, y: int):
        bw  = self.radius * 2 + 6
        bh  = 5
        bx  = x - bw // 2
        by  = y - self.radius - 11
        frac = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(surface, COLOR_RED,   (bx, by, bw, bh))
        pygame.draw.rect(surface, COLOR_GREEN, (bx, by, int(bw * frac), bh))
        pygame.draw.rect(surface, COLOR_BLACK, (bx, by, bw, bh), 1)


# ── Concrete enemy types ──────────────────────────────────────────────────────

class Runner(Enemy):
    """Standard, well-balanced. Drawn as a circle with a brighter inner disc."""
    def __init__(self, waypoints):
        super().__init__(waypoints, 'Runner')

    def _draw_body(self, surface, x, y):
        pygame.draw.circle(surface, self.color, (x, y), self.radius)
        pygame.draw.circle(surface, (240, 130, 130), (x, y), self.radius - 5)
        pygame.draw.circle(surface, COLOR_BLACK, (x, y), self.radius, 2)


class Dasher(Enemy):
    """Fast, low HP. Elongated ellipse conveys speed."""
    def __init__(self, waypoints):
        super().__init__(waypoints, 'Dasher')

    def _draw_body(self, surface, x, y):
        r = self.radius
        rect = pygame.Rect(x - r - 5, y - r + 3, (r + 5) * 2, (r - 3) * 2)
        pygame.draw.ellipse(surface, self.color, rect)
        pygame.draw.ellipse(surface, COLOR_BLACK, rect, 2)


class Ironclad(Enemy):
    """Armored, slow, high HP. Hexagon suggests heavy plating."""
    def __init__(self, waypoints):
        super().__init__(waypoints, 'Ironclad')

    def _draw_body(self, surface, x, y):
        r = self.radius
        pts  = [(x + r * math.cos(math.radians(60 * i - 30)),
                 y + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
        ipts = [(x + (r - 6) * math.cos(math.radians(60 * i - 30)),
                 y + (r - 6) * math.sin(math.radians(60 * i - 30))) for i in range(6)]
        pygame.draw.polygon(surface, self.color, pts)
        pygame.draw.polygon(surface, (170, 170, 190), ipts)
        pygame.draw.polygon(surface, COLOR_BLACK, pts, 2)


class Swarmling(Enemy):
    """Very fast, very low HP. Diamond shape; spawns in dense clusters."""
    def __init__(self, waypoints):
        super().__init__(waypoints, 'Swarmling')

    def _draw_body(self, surface, x, y):
        r = self.radius
        pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
        pygame.draw.polygon(surface, self.color, pts)
        pygame.draw.polygon(surface, COLOR_BLACK, pts, 1)


class Phantom(Enemy):
    """
    Flying enemy — bypasses ground-level towers (air_targeting=False).
    Wings on the sides and a yellow altitude dot distinguish it visually.
    """
    def __init__(self, waypoints):
        super().__init__(waypoints, 'Phantom')

    def _draw_body(self, surface, x, y):
        r = self.radius
        pygame.draw.circle(surface, self.color, (x, y), r)
        # Wing triangles
        pygame.draw.polygon(surface, (190, 120, 240),
            [(x - r, y), (x - r - 12, y - 8), (x - r - 12, y + 8)])
        pygame.draw.polygon(surface, (190, 120, 240),
            [(x + r, y), (x + r + 12, y - 8), (x + r + 12, y + 8)])
        pygame.draw.circle(surface, COLOR_BLACK, (x, y), r, 2)
        # Altitude indicator
        pygame.draw.circle(surface, COLOR_YELLOW, (x, y - r - 6), 3)


class Colossus(Enemy):
    """Boss. Large octagon, glowing eyes — visually imposing."""
    def __init__(self, waypoints):
        super().__init__(waypoints, 'Colossus')

    def _draw_body(self, surface, x, y):
        r = self.radius
        pts  = [(x + r * math.cos(math.radians(45 * i)),
                 y + r * math.sin(math.radians(45 * i))) for i in range(8)]
        ipts = [(x + (r - 7) * math.cos(math.radians(45 * i)),
                 y + (r - 7) * math.sin(math.radians(45 * i))) for i in range(8)]
        pygame.draw.polygon(surface, self.color, pts)
        pygame.draw.polygon(surface, (220, 70, 70), ipts)
        pygame.draw.polygon(surface, COLOR_BLACK, pts, 3)
        # Eyes
        for ex_off in (-9, 9):
            pygame.draw.circle(surface, COLOR_YELLOW, (x + ex_off, y - 6), 4)
            pygame.draw.circle(surface, COLOR_BLACK,  (x + ex_off, y - 6), 2)
