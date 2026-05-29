"""
Projectile system. Each instance homes toward a live target.
If the target dies mid-flight the projectile despawns — this keeps missed shots
from being wasted on already-dead enemies during heavy waves.

Chain lightning is resolved recursively at hit-time, not as separate projectiles.
Hitscan (Longwatch) is handled directly in tower.py; no Projectile is created.
"""

import pygame
import math
from constants import COLOR_WHITE, COLOR_GLACIER


class Projectile:
    def __init__(self, x: float, y: float, target, damage: float, speed: float,
                 color: tuple, radius: int = 4,
                 armor_pierce: bool = False,
                 aoe_radius: float = 0.0,
                 burn_damage: float = 0.0, burn_duration: float = 0.0,
                 burn_interval: float = 0.5,
                 freeze_duration: float = 0.0, slow_duration: float = 0.0,
                 slow_factor: float = 1.0,
                 chain_count: int = 0, chain_range: float = 0.0,
                 chain_freeze: float = 0.0,
                 chain_perma_slow_chance: float = 0.0,
                 is_lightning: bool = False,
                 apply_wet: bool = False):

        self.x, self.y  = float(x), float(y)
        self.target      = target
        self.damage      = damage
        self.speed       = speed
        self.color       = color
        self.radius      = radius
        self.armor_pierce = armor_pierce
        self.aoe_radius  = aoe_radius

        # Status-effect parameters baked in at creation so towers don't hold state
        self.burn_damage    = burn_damage
        self.burn_duration  = burn_duration
        self.burn_interval  = burn_interval
        self.freeze_duration = freeze_duration
        self.slow_duration  = slow_duration
        self.slow_factor    = slow_factor

        self.chain_count             = chain_count
        self.chain_range             = chain_range
        self.chain_freeze            = chain_freeze
        self.chain_perma_slow_chance = chain_perma_slow_chance

        self.is_lightning = is_lightning
        self.apply_wet    = apply_wet

        self.active = True

    # ── update ────────────────────────────────────────────────────────────────
    def update(self, dt: float, all_enemies: list,
               aoe_flashes: list = None, chain_flashes: list = None):
        if not self.active:
            return
        if not self.target.alive:
            self.active = False
            return

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        move = self.speed * dt

        if dist <= move:
            self.x, self.y = self.target.x, self.target.y
            self._on_hit(all_enemies, aoe_flashes, chain_flashes)
            self.active = False
        else:
            f = move / dist
            self.x += dx * f
            self.y += dy * f

    # ── hit resolution ────────────────────────────────────────────────────────
    def _on_hit(self, all_enemies: list,
                aoe_flashes: list = None, chain_flashes: list = None):
        # Inline import avoids a circular dependency (effects ← projectile ← tower)
        from effects import BurnEffect, FreezeEffect, SlowEffect

        targets = self._aoe_targets(all_enemies) if self.aoe_radius > 0 else [self.target]

        for enemy in targets:
            if not enemy.alive:
                continue

            # Wet + lightning damage multiplier (direct hit only)
            dmg = self.damage
            if self.is_lightning and enemy is self.target:
                if any(e.effect_type == 'wet' and e.active for e in enemy.effects):
                    dmg *= 1.1

            enemy.apply_damage(dmg, self.armor_pierce)

            if self.burn_damage > 0:
                enemy.apply_effect(BurnEffect(self.burn_duration,
                                              self.burn_damage,
                                              self.burn_interval))
            if self.freeze_duration > 0:
                enemy.apply_effect(FreezeEffect(self.freeze_duration,
                                                self.slow_duration,
                                                self.slow_factor))
            elif self.slow_duration > 0 and self.slow_factor < 1.0:
                enemy.apply_effect(SlowEffect(self.slow_duration, self.slow_factor))

            # Lightning stack accumulation — direct hit = +2
            if self.is_lightning and enemy is self.target:
                enemy.lightning_stacks += 2
                if enemy.lightning_stacks >= 5:
                    enemy.apply_effect(BurnEffect(2.0, 5.0, 0.5))
                    enemy.lightning_stacks = 0

            # Wet application — primary target gets full slow, AoE splash gets diminished
            if self.apply_wet:
                from effects import WetEffect
                if enemy is self.target:
                    enemy.apply_effect(WetEffect(0.95))   # 5% speed reduction (direct)
                else:
                    enemy.apply_effect(WetEffect(0.975))  # 2.5% speed reduction (splash)

        # AoE visual flash
        if self.aoe_radius > 0 and aoe_flashes is not None:
            aoe_flashes.append({
                'x': self.x, 'y': self.y,
                'max_radius': self.aoe_radius,
                'color': self.color,
                'elapsed': 0.0,
                'duration': 0.35,
            })

        # Chain lightning jumps from the primary target outward
        if self.chain_count > 0 and self.target.alive:
            self._chain(all_enemies, self.target, self.chain_count,
                        {id(self.target)}, chain_flashes)

    def _aoe_targets(self, all_enemies: list) -> list:
        result = []
        for e in all_enemies:
            if e.alive and math.hypot(e.x - self.x, e.y - self.y) <= self.aoe_radius:
                result.append(e)
        return result

    def _chain(self, all_enemies: list, source, remaining: int, hit_ids: set,
               chain_flashes: list = None):
        """Jump to the closest un-hit enemy within chain_range, dealing 70% damage."""
        import random
        if remaining <= 0:
            return
        candidates = []
        for e in all_enemies:
            if e.alive and id(e) not in hit_ids and not e.chain_resist:
                d = math.hypot(e.x - source.x, e.y - source.y)
                if d <= self.chain_range:
                    candidates.append((d, e))
        if not candidates:
            return
        candidates.sort(key=lambda t: t[0])
        _, next_e = candidates[0]

        # Wet + lightning damage multiplier for chain jumps
        dmg = self.damage * 0.7
        if self.is_lightning:
            if any(e.effect_type == 'wet' and e.active for e in next_e.effects):
                dmg *= 1.1

        next_e.apply_damage(dmg, self.armor_pierce)
        hit_ids.add(id(next_e))
        # Chain lightning visual arc
        if chain_flashes is not None:
            chain_flashes.append({
                'x1': source.x, 'y1': source.y,
                'x2': next_e.x,  'y2': next_e.y,
                'color': self.color,
                'elapsed': 0.0,
                'duration': 0.25,
            })
        # Conductor upgrade: chain freeze and perma-slow
        if self.chain_freeze > 0:
            from effects import FreezeEffect
            next_e.apply_effect(FreezeEffect(self.chain_freeze, 1.0, 1.0))
        if self.chain_perma_slow_chance > 0 and random.random() < self.chain_perma_slow_chance:
            from effects import SlowEffect
            next_e.apply_effect(SlowEffect(9999.0, 0.5))

        # Lightning stack accumulation — chain hit = +1
        if self.is_lightning:
            next_e.lightning_stacks += 1
            if next_e.lightning_stacks >= 5:
                from effects import BurnEffect
                next_e.apply_effect(BurnEffect(2.0, 5.0, 0.5))
                next_e.lightning_stacks = 0

        self._chain(all_enemies, next_e, remaining - 1, hit_ids, chain_flashes)

    # ── draw ─────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        if not self.active:
            return
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)


class GlacierProjectile(Projectile):
    """Ice-crystal visual: six radiating spikes from a white centre dot."""
    def __init__(self, x, y, target, stats: dict):
        super().__init__(
            x, y, target,
            damage        = stats['damage'],
            speed         = stats['proj_speed'],
            color         = COLOR_GLACIER,
            radius        = 6,
            aoe_radius    = stats['aoe_radius'],
            freeze_duration = stats['freeze_duration'],
            slow_duration = stats['slow_duration'],
            slow_factor   = stats['slow_factor'],
        )

    def draw(self, surface: pygame.Surface):
        if not self.active:
            return
        ix, iy = int(self.x), int(self.y)
        for i in range(6):
            a  = math.radians(60 * i)
            ex = ix + int(9 * math.cos(a))
            ey = iy + int(9 * math.sin(a))
            pygame.draw.line(surface, self.color, (ix, iy), (ex, ey), 2)
        pygame.draw.circle(surface, COLOR_WHITE, (ix, iy), 3)
