"""
Tower hierarchy. Each subclass overrides _draw_body() and _create_projectile().
Right-click cycles targeting_mode; targeting selection lives in _select_target()
so adding a new mode only requires adding to constants.TARGETING_MODES.

Future upgrade tiers: add an `upgrades` list and multiply stats by tier multipliers
inside _create_projectile() and _select_target().
"""

import pygame
import math
from constants import (TOWER_STATS, TOWER_COSTS, TOWER_UPGRADES, SELL_PERCENTAGE,
                       TARGETING_MODES, TARGETING_FIRST, TARGETING_LAST,
                       TARGETING_STRONGEST, TARGETING_CLOSEST,
                       COLOR_BLACK, COLOR_DARK_GRAY, COLOR_WHITE,
                       COLOR_YELLOW, COLOR_RED, COLOR_GRAY, COLOR_WATER, COLOR_CYAN,
                       COLOR_SENTINEL, COLOR_GLACIER, COLOR_PYRE,
                       COLOR_CONDUCTOR, COLOR_LONGWATCH, COLOR_ORANGE,
                       COLOR_TIDE_LAUNCHER, COLOR_KRAKEN)
from projectile import Projectile, GlacierProjectile


class Tower:
    def __init__(self, x: int, y: int, tower_type: str):
        s = TOWER_STATS[tower_type]
        self.tower_type    = tower_type
        self.x, self.y     = x, y
        self.range         = s['range']
        self.damage        = s['damage']
        self.fire_rate     = s['fire_rate']
        self.proj_speed    = s['proj_speed']
        self.color         = s['color']
        self.cost          = s['cost']
        self.air_targeting = s.get('air_targeting', False)
        self.water_only    = s.get('water_only', False)

        # Per-tower effect stats (defaults for towers that don't use them)
        self.aoe_radius    = s.get('aoe_radius', 0.0)
        self.freeze_duration = s.get('freeze_duration', 0.0)
        self.slow_duration   = s.get('slow_duration', 0.0)
        self.slow_factor     = s.get('slow_factor', 1.0)
        self.burn_damage     = s.get('burn_damage', 0.0)
        self.burn_duration   = s.get('burn_duration', 0.0)
        self.burn_interval   = s.get('burn_interval', 0.5)
        self.chain_count     = s.get('chain_count', 0)
        self.chain_range     = s.get('chain_range', 0.0)
        self.multi_target    = s.get('multi_target', 1)

        self.fire_timer       = 0.0
        self.targeting_mode   = TARGETING_FIRST
        self.target           = None
        self.selected         = False
        # total_spent tracks cost + future upgrades for accurate sell refund
        self.total_spent      = self.cost

        # Upgrade state
        self.upgrade_path  = None   # None | 'A' | 'B'
        self.upgrade_tier  = 0      # 0, 1, or 2
        # Upgrade-specific stats (neutral defaults)
        self.chain_freeze              = 0.0
        self.chain_perma_slow_chance   = 0.0
        self.oneshot_threshold         = 0.0
        self.hit_slow                  = 0.0

    @property
    def sell_value(self) -> int:
        return int(self.total_spent * SELL_PERCENTAGE)

    def cycle_targeting(self):
        idx = TARGETING_MODES.index(self.targeting_mode)
        self.targeting_mode = TARGETING_MODES[(idx + 1) % len(TARGETING_MODES)]

    # ── targeting ─────────────────────────────────────────────────────────────
    def _enemies_in_range(self, enemies: list) -> list:
        result = []
        for e in enemies:
            if not e.alive:
                continue
            if e.flying and not self.air_targeting:
                continue
            if math.hypot(e.x - self.x, e.y - self.y) <= self.range:
                result.append(e)
        return result

    def _select_target(self, enemies: list):
        pool = self._enemies_in_range(enemies)
        if not pool:
            return None
        if self.targeting_mode == TARGETING_FIRST:
            return max(pool, key=lambda e: e.path_progress)
        if self.targeting_mode == TARGETING_LAST:
            return min(pool, key=lambda e: e.path_progress)
        if self.targeting_mode == TARGETING_STRONGEST:
            return max(pool, key=lambda e: e.hp)
        # TARGETING_CLOSEST
        return min(pool, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))

    # ── upgrade ───────────────────────────────────────────────────────────────
    def apply_upgrade(self, path: str, economy) -> bool:
        if self.upgrade_path is not None and self.upgrade_path != path:
            return False
        if self.upgrade_tier >= 2:
            return False
        tiers = TOWER_UPGRADES.get(self.tower_type, {}).get(path)
        if not tiers or self.upgrade_tier >= len(tiers):
            return False
        tier_data = tiers[self.upgrade_tier]
        if not economy.spend(tier_data['cost']):
            return False
        self.total_spent  += tier_data['cost']
        self.upgrade_path  = path
        self.upgrade_tier += 1
        for key, val in tier_data.items():
            if key not in ('cost', 'label'):
                setattr(self, key, val)
        return True

    # ── update ────────────────────────────────────────────────────────────────
    def update(self, dt: float, enemies: list, projectiles: list):
        self.fire_timer -= dt
        self.target = self._select_target(enemies)
        if self.target and self.fire_timer <= 0:
            self.fire_timer = self.fire_rate
            proj = self._create_projectile(self.target, enemies)
            if proj:
                if isinstance(proj, list):
                    projectiles.extend(proj)
                else:
                    projectiles.append(proj)

    def _create_projectile(self, target, all_enemies):
        return Projectile(self.x, self.y, target, self.damage,
                          self.proj_speed, self.color)

    # ── draw ─────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        # Square base
        base = pygame.Rect(self.x - 17, self.y - 17, 34, 34)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, base)
        pygame.draw.rect(surface, COLOR_BLACK, base, 2)
        self._draw_body(surface)
        if self.selected:
            display_r = min(int(self.range), 900)
            pygame.draw.circle(surface, self.color,
                               (int(self.x), int(self.y)), display_r, 1)

    def _draw_body(self, surface: pygame.Surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), 12)


# ── Concrete tower types ──────────────────────────────────────────────────────

class Sentinel(Tower):
    """All-rounder. Barrel rotates toward its current target."""
    def __init__(self, x, y):
        super().__init__(x, y, 'Sentinel')

    def _draw_body(self, surface):
        ix, iy = int(self.x), int(self.y)
        # Barrel direction
        if self.target and self.target.alive:
            angle = math.atan2(self.target.y - self.y, self.target.x - self.x)
        else:
            angle = 0.0
        ex = ix + int(17 * math.cos(angle))
        ey = iy + int(17 * math.sin(angle))
        pygame.draw.line(surface, COLOR_DARK_GRAY, (ix, iy), (ex, ey), 6)
        pygame.draw.circle(surface, COLOR_SENTINEL, (ix, iy), 12)
        pygame.draw.circle(surface, COLOR_WHITE, (ix, iy), 5)


class GlacierTower(Tower):
    """AoE freeze burst. Drawn as a six-spoke snowflake."""
    def __init__(self, x, y):
        super().__init__(x, y, 'Glacier')

    def _draw_body(self, surface):
        ix, iy = int(self.x), int(self.y)
        for i in range(6):
            a  = math.radians(60 * i)
            ex = ix + int(15 * math.cos(a))
            ey = iy + int(15 * math.sin(a))
            pygame.draw.line(surface, COLOR_GLACIER, (ix, iy), (ex, ey), 3)
            # Cross-bars on each spoke
            mx_ = ix + int(9 * math.cos(a))
            my_ = iy + int(9 * math.sin(a))
            pygame.draw.line(surface, COLOR_GLACIER,
                (int(mx_ + 4 * math.cos(a + math.pi/2)),
                 int(my_ + 4 * math.sin(a + math.pi/2))),
                (int(mx_ - 4 * math.cos(a + math.pi/2)),
                 int(my_ - 4 * math.sin(a + math.pi/2))), 2)
        pygame.draw.circle(surface, COLOR_WHITE, (ix, iy), 5)

    def _create_projectile(self, target, all_enemies):
        return GlacierProjectile(self.x, self.y, target, {
            'damage':          self.damage,
            'proj_speed':      self.proj_speed,
            'aoe_radius':      self.aoe_radius,
            'freeze_duration': self.freeze_duration,
            'slow_duration':   self.slow_duration,
            'slow_factor':     self.slow_factor,
        })


class PyreTower(Tower):
    """Burn/DoT. Animated flame flickers each frame."""
    def __init__(self, x, y):
        super().__init__(x, y, 'Pyre')
        self._anim = 0.0
        self._frame = 0

    def update(self, dt, enemies, projectiles):
        self._anim += dt
        if self._anim >= 0.18:
            self._anim  = 0.0
            self._frame = (self._frame + 1) % 3
        super().update(dt, enemies, projectiles)

    def _draw_body(self, surface):
        ix, iy = int(self.x), int(self.y)
        wobble = self._frame - 1   # -1, 0, 1
        # Three layered flame triangles
        for i, (col, tip_off) in enumerate([
            (COLOR_PYRE,   wobble),
            (COLOR_ORANGE, wobble + 2),
            (COLOR_YELLOW, wobble),
        ]):
            pts = [(ix + tip_off, iy - 15 + i * 2),
                   (ix - 9 + i,  iy + 8),
                   (ix + 9 - i,  iy + 8)]
            pygame.draw.polygon(surface, col, pts)
        pygame.draw.circle(surface, COLOR_WHITE, (ix, iy + 5), 4)

    def _create_projectile(self, target, all_enemies):
        projs = [Projectile(self.x, self.y, target,
                            damage=self.damage, speed=self.proj_speed,
                            color=self.color, radius=5,
                            burn_damage=self.burn_damage,
                            burn_duration=self.burn_duration,
                            burn_interval=self.burn_interval)]
        if self.multi_target > 1:
            extras = [e for e in self._enemies_in_range(all_enemies)
                      if e is not target][:self.multi_target - 1]
            for extra in extras:
                projs.append(Projectile(self.x, self.y, extra,
                                        damage=self.damage, speed=self.proj_speed,
                                        color=self.color, radius=5,
                                        burn_damage=self.burn_damage,
                                        burn_duration=self.burn_duration,
                                        burn_interval=self.burn_interval))
        return projs


class ConductorTower(Tower):
    """Chain lightning. Drawn as a Tesla-coil post with a lightning bolt."""
    def __init__(self, x, y):
        super().__init__(x, y, 'Conductor')

    def _draw_body(self, surface):
        ix, iy = int(self.x), int(self.y)
        # Post
        pygame.draw.rect(surface, COLOR_CONDUCTOR, (ix - 4, iy - 16, 8, 22))
        # Coil sphere
        pygame.draw.circle(surface, COLOR_YELLOW, (ix, iy - 16), 8)
        pygame.draw.circle(surface, COLOR_CONDUCTOR, (ix, iy - 16), 6)
        # Lightning bolt zig-zag
        bolt = [(ix + 3, iy - 24), (ix - 2, iy - 16),
                (ix + 3, iy - 16), (ix - 3, iy - 8)]
        pygame.draw.lines(surface, COLOR_YELLOW, False, bolt, 2)

    def _create_projectile(self, target, all_enemies):
        return Projectile(self.x, self.y, target,
                          damage=self.damage, speed=self.proj_speed,
                          color=self.color, radius=4,
                          chain_count=self.chain_count,
                          chain_range=self.chain_range,
                          chain_freeze=self.chain_freeze,
                          chain_perma_slow_chance=self.chain_perma_slow_chance,
                          is_lightning=True)


class LongwatchTower(Tower):
    """
    Hitscan sniper with global range and armor pierce.
    No projectile object is created; damage is applied instantly in update().
    A brief flash line gives visual feedback.
    """
    def __init__(self, x, y):
        super().__init__(x, y, 'Longwatch')
        self._flash_timer  = 0.0
        self._flash_target = None   # (x, y) snapshot at time of shot

    def update(self, dt, enemies, projectiles):
        # Override to skip projectile creation entirely (hitscan)
        self._flash_timer = max(0.0, self._flash_timer - dt)
        self.fire_timer  -= dt
        self.target       = self._select_target(enemies)
        if self.target and self.fire_timer <= 0:
            self.fire_timer = self.fire_rate
            # Path A Tier 2: one-shot enemies below threshold HP %
            if (self.oneshot_threshold > 0
                    and self.target.hp / self.target.max_hp < self.oneshot_threshold):
                self.target.apply_damage(self.target.hp + 1, armor_pierce=True)
            else:
                self.target.apply_damage(self.damage, armor_pierce=True)
            # Path B Tier 2: slow on hit
            if self.hit_slow > 0:
                from effects import SlowEffect
                self.target.apply_effect(SlowEffect(self.hit_slow, 0.5))
            self._flash_timer  = 0.12
            self._flash_target = (int(self.target.x), int(self.target.y))

    def _draw_body(self, surface):
        ix, iy = int(self.x), int(self.y)
        # Long barrel
        pygame.draw.rect(surface, COLOR_LONGWATCH, (ix - 3, iy - 20, 6, 26))
        # Scope housing
        pygame.draw.circle(surface, COLOR_LONGWATCH, (ix, iy - 10), 9)
        pygame.draw.circle(surface, COLOR_DARK_GRAY, (ix, iy - 10), 6)
        # Crosshair reticle
        pygame.draw.line(surface, COLOR_LONGWATCH, (ix - 9, iy - 10), (ix + 9, iy - 10), 1)
        pygame.draw.line(surface, COLOR_LONGWATCH, (ix, iy - 19), (ix, iy - 1), 1)
        # Hitscan flash
        if self._flash_timer > 0 and self._flash_target:
            pygame.draw.line(surface, COLOR_YELLOW,
                             (ix, iy), self._flash_target, 1)


class TideLauncherTower(Tower):
    """Water-only. Slow cannonballs with AoE splash on impact."""
    def __init__(self, x, y):
        super().__init__(x, y, 'TideLauncher')
        self._ripple_timer = 0.0
        self._ripple_phase = 0

    def update(self, dt, enemies, projectiles):
        self._ripple_timer += dt
        if self._ripple_timer >= 0.35:
            self._ripple_timer = 0.0
            self._ripple_phase = (self._ripple_phase + 1) % 3
        super().update(dt, enemies, projectiles)

    def _draw_body(self, surface):
        ix, iy = int(self.x), int(self.y)
        # Animated water ripple rings
        for i in range(3):
            r = 8 + ((i + self._ripple_phase) % 3) * 5
            alpha_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(alpha_surf, (*COLOR_WATER, 70), (r + 2, r + 2), r, 2)
            surface.blit(alpha_surf, (ix - r - 2, iy - r - 2))
        # Dark navy body
        pygame.draw.circle(surface, COLOR_TIDE_LAUNCHER, (ix, iy), 13)
        # White cannonball icon
        pygame.draw.circle(surface, COLOR_WHITE, (ix, iy), 6)
        pygame.draw.circle(surface, COLOR_BLACK, (ix, iy), 6, 1)

    def _create_projectile(self, target, all_enemies):
        return Projectile(self.x, self.y, target,
                          damage=self.damage, speed=self.proj_speed,
                          color=self.color, radius=8,
                          aoe_radius=self.aoe_radius,
                          apply_wet=True)


class KrakenTower(Tower):
    """Water-only. Grabs up to 2 enemies at once, applying a freeze."""
    def __init__(self, x, y):
        super().__init__(x, y, 'Kraken')
        self._tentacle_anim  = 0.0
        self._arm_extended   = False

    def update(self, dt, enemies, projectiles):
        self._tentacle_anim += dt
        # Extend arms briefly at the moment of firing
        self._arm_extended = self._tentacle_anim >= self.fire_rate * 0.85
        super().update(dt, enemies, projectiles)
        if self.fire_timer == self.fire_rate:   # just fired — reset anim
            self._tentacle_anim = 0.0

    def _draw_body(self, surface):
        ix, iy = int(self.x), int(self.y)
        num_arms = 6
        for i in range(num_arms):
            angle  = math.radians(360 / num_arms * i)
            reach  = 18 if (self._arm_extended and i % 2 == 0) else 13
            ex = ix + int(reach * math.cos(angle))
            ey = iy + int(reach * math.sin(angle))
            pygame.draw.line(surface, COLOR_KRAKEN, (ix, iy), (ex, ey), 4)
        pygame.draw.circle(surface, COLOR_KRAKEN, (ix, iy), 11)
        pygame.draw.circle(surface, COLOR_CYAN, (ix, iy), 5)

    def _create_projectile(self, target, all_enemies):
        projs = [Projectile(self.x, self.y, target,
                            damage=self.damage, speed=self.proj_speed,
                            color=self.color, radius=5,
                            freeze_duration=self.freeze_duration,
                            slow_duration=self.slow_duration,
                            slow_factor=self.slow_factor,
                            apply_wet=True)]
        if self.multi_target >= 2:
            extras = [e for e in self._enemies_in_range(all_enemies)
                      if e is not target][:self.multi_target - 1]
            for extra in extras:
                projs.append(Projectile(self.x, self.y, extra,
                                        damage=self.damage, speed=self.proj_speed,
                                        color=self.color, radius=5,
                                        freeze_duration=self.freeze_duration,
                                        slow_duration=self.slow_duration,
                                        slow_factor=self.slow_factor,
                                        apply_wet=True))
        return projs
