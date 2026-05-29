"""
Central game controller. Owns all game objects; routes events to the correct subsystem.

State machine:
  PLAYING  → normal gameplay
  GAME_OVER → lives reached 0 (R to restart)
  WIN       → all waves cleared (R to restart)

Placement mode is a sub-state of PLAYING controlled via ui.selected_tower_type.
"""

import pygame
import math
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GAME_WIDTH, FPS,
    STARTING_LIVES, WAVE_BONUS, AUTO_WAVE_DELAY,
    COLOR_BLACK, COLOR_WHITE, COLOR_RED, COLOR_GOLD,
    TOWER_COSTS, TOWER_STATS,
)
from map         import GameMap
from tower       import (Sentinel, GlacierTower, PyreTower, ConductorTower,
                         LongwatchTower, TideLauncherTower, KrakenTower)
from wave_manager import WaveManager
from economy     import Economy
from ui          import UI

STATE_PLAYING   = 'playing'
STATE_GAME_OVER = 'game_over'
STATE_WIN       = 'win'

TOWER_CLASSES = {
    'Sentinel':     Sentinel,
    'Glacier':      GlacierTower,
    'Pyre':         PyreTower,
    'Conductor':    ConductorTower,
    'Longwatch':    LongwatchTower,
    'TideLauncher': TideLauncherTower,
    'Kraken':       KrakenTower,
}


class Game:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock  = pygame.time.Clock()
        self.state  = STATE_PLAYING

        self.game_map     = GameMap()
        self.wave_manager = WaveManager(self.game_map.waypoints)
        self.economy      = Economy()
        self.ui           = UI()

        self.enemies:     list = []
        self.towers:      list = []
        self.projectiles: list = []

        self.lives          = STARTING_LIVES
        self.selected_tower = None   # a placed tower the player has clicked on

        self._wave_bonus_timer  = 0.0   # duration to show "Wave N Complete" popup
        self._completed_wave_n  = 0     # which wave number just finished
        self._auto_wave         = False
        self._auto_wave_timer   = 0.0
        self._speed_mult        = 1.0

        self.aoe_flashes:   list = []
        self.chain_flashes: list = []

        self.font_big  = pygame.font.SysFont('monospace', 60, bold=True)
        self.font_mid  = pygame.font.SysFont('monospace', 26)
        self.font_small= pygame.font.SysFont('monospace', 18)

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)   # cap to avoid lag spirals

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self._handle_event(event)

            if self.state == STATE_PLAYING:
                self._update(dt * self._speed_mult)

            self._draw()

        pygame.quit()

    # ── event handling ────────────────────────────────────────────────────────
    def _handle_event(self, event: pygame.event.Event):
        # Global restart from end screens
        if self.state in (STATE_GAME_OVER, STATE_WIN):
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.__init__(self.screen)
            return

        if event.type == pygame.KEYDOWN:
            self._handle_key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            self.ui.handle_hover(mx, my)
            if event.button == 1:
                self._handle_lclick(mx, my)
            elif event.button == 3:
                self._handle_rclick(mx, my)
        elif event.type == pygame.MOUSEMOTION:
            self.ui.handle_hover(*event.pos)

    def _handle_key(self, key: int):
        if key == pygame.K_ESCAPE:
            self.ui.clear_selection()
            self._deselect_tower()
        elif key == pygame.K_SPACE:
            if not self.wave_manager.wave_active:
                self.wave_manager.start_wave()
        elif key == pygame.K_a:
            self._auto_wave = not self._auto_wave
            self._auto_wave_timer = 0.0
        elif key == pygame.K_2:
            self._speed_mult = 1.0 if self._speed_mult == 2.0 else 2.0
        elif key == pygame.K_s:
            if self.selected_tower:
                self.economy.sell_tower(self.selected_tower)
                self.towers.remove(self.selected_tower)
                self.selected_tower = None
        elif key == pygame.K_u:
            if self.selected_tower:
                t = self.selected_tower
                path = t.upgrade_path or 'A'
                t.apply_upgrade(path, self.economy)

    def _handle_lclick(self, mx: int, my: int):
        if self.ui.is_panel_click(mx, my):
            result = self.ui.handle_click(mx, my, self.economy)
            if result == 'toggle_auto_wave':
                self._auto_wave = not self._auto_wave
                self._auto_wave_timer = 0.0
            elif result == 'toggle_speed':
                self._speed_mult = 1.0 if self._speed_mult == 2.0 else 2.0
            elif result and result.startswith('upgrade_'):
                path = result[len('upgrade_'):]   # e.g. 'A1'
                if self.selected_tower:
                    self.selected_tower.apply_upgrade(path[0], self.economy)
            else:
                self._deselect_tower()
            return

        if self.ui.selected_tower_type:
            self._try_place_tower(mx, my)
        else:
            clicked = self._tower_at(mx, my)
            self._deselect_tower()
            if clicked:
                self.selected_tower = clicked
                clicked.selected    = True

    def _handle_rclick(self, mx: int, my: int):
        if self.ui.is_panel_click(mx, my):
            return
        tower = self._tower_at(mx, my)
        if tower:
            tower.cycle_targeting()

    # ── placement ─────────────────────────────────────────────────────────────
    def _try_place_tower(self, mx: int, my: int):
        ttype     = self.ui.selected_tower_type
        is_water  = TOWER_STATS[ttype].get('water_only', False)
        if is_water:
            valid = self.game_map.is_water_buildable(mx, my, self.towers)
        else:
            valid = (self.game_map.is_buildable(mx, my) and
                     not self.game_map.is_tile_occupied(mx, my, self.towers))
        if valid:
            cost = TOWER_COSTS[ttype]
            if self.economy.spend(cost):
                sx, sy = self.game_map.snap_to_tile_center(mx, my)
                self.towers.append(TOWER_CLASSES[ttype](sx, sy))
                # Stay in placement mode so player can place multiple towers

    def _tower_at(self, mx: int, my: int):
        """Return the first tower within click radius, else None."""
        return next(
            (t for t in self.towers if math.hypot(t.x - mx, t.y - my) <= 20),
            None)

    def _deselect_tower(self):
        if self.selected_tower:
            self.selected_tower.selected = False
            self.selected_tower = None

    # ── update ────────────────────────────────────────────────────────────────
    def _update(self, dt: float):
        # Wave manager may set wave_complete this frame
        prev_complete = self.wave_manager.wave_complete
        self.wave_manager.update(dt, self.enemies)

        # Trigger wave-complete bonus exactly once per wave
        if self.wave_manager.wave_complete and not prev_complete:
            self.economy.wave_bonus()
            self._wave_bonus_timer = 2.5
            self._completed_wave_n = self.wave_manager.current_wave  # already incremented
            if self._auto_wave:
                self._auto_wave_timer = AUTO_WAVE_DELAY

        if self._wave_bonus_timer > 0:
            self._wave_bonus_timer -= dt

        # Auto-wave countdown
        if (self._auto_wave and self.wave_manager.wave_complete
                and not self.wave_manager.wave_active
                and not self.wave_manager.game_won):
            if self._auto_wave_timer > 0:
                self._auto_wave_timer -= dt
            else:
                self.wave_manager.start_wave()
                self._auto_wave_timer = 0.0

        if self.wave_manager.game_won:
            self.state = STATE_WIN
            return

        # Towers fire
        for tower in self.towers:
            tower.update(dt, self.enemies, self.projectiles)

        # Projectiles
        self.projectiles = [p for p in self.projectiles if p.active]
        for proj in self.projectiles:
            proj.update(dt, self.enemies, self.aoe_flashes, self.chain_flashes)
        self.projectiles = [p for p in self.projectiles if p.active]

        # Advance and prune visual flash timers
        for f in self.aoe_flashes + self.chain_flashes:
            f['elapsed'] += dt
        self.aoe_flashes   = [f for f in self.aoe_flashes   if f['elapsed'] < f['duration']]
        self.chain_flashes = [f for f in self.chain_flashes if f['elapsed'] < f['duration']]

        # Enemies
        for enemy in self.enemies:
            enemy.update(dt)

        # Resolve dead enemies
        alive, dead = [], []
        for e in self.enemies:
            (alive if e.alive else dead).append(e)
        self.enemies = alive

        for e in dead:
            if e.reached_end:
                self.lives -= 1
            else:
                self.economy.earn(e.reward)

        if self.lives <= 0:
            self.state = STATE_GAME_OVER

    # ── draw ─────────────────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill(COLOR_BLACK)

        self.game_map.draw(self.screen)

        # AoE impact rings — draw behind towers/enemies
        for f in self.aoe_flashes:
            prog   = f['elapsed'] / f['duration']
            radius = max(1, int(f['max_radius'] * prog))
            alpha  = int(200 * (1.0 - prog))
            surf   = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*f['color'], alpha), (radius + 2, radius + 2), radius, 3)
            self.screen.blit(surf, (int(f['x']) - radius - 2, int(f['y']) - radius - 2))

        for tower in self.towers:
            tower.draw(self.screen)

        for enemy in self.enemies:
            enemy.draw(self.screen)

        for proj in self.projectiles:
            proj.draw(self.screen)

        # Chain lightning arcs — draw over enemies, below UI
        if self.chain_flashes:
            arc_surf = pygame.Surface((GAME_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for f in self.chain_flashes:
                prog  = f['elapsed'] / f['duration']
                alpha = int(255 * (1.0 - prog))
                width = max(1, 3 - int(2 * prog))
                pygame.draw.line(arc_surf, (*f['color'], alpha),
                                 (int(f['x1']), int(f['y1'])),
                                 (int(f['x2']), int(f['y2'])), width)
            self.screen.blit(arc_surf, (0, 0))

        # Placement ghost
        if self.ui.selected_tower_type:
            mx, my = pygame.mouse.get_pos()
            self.ui.draw_placement_preview(
                self.screen, mx, my,
                self.ui.selected_tower_type,
                self.game_map, self.towers)

        # Panel
        self.ui.draw(
            self.screen,
            self.economy,
            self.lives,
            self.wave_manager.wave_number,
            self.wave_manager.total_waves,
            self.wave_manager.wave_active,
            selected_tower_obj=self.selected_tower,
            auto_wave=self._auto_wave,
            auto_wave_timer=self._auto_wave_timer,
            speed_mult=self._speed_mult,
        )

        # Wave-complete popup
        if self._wave_bonus_timer > 0:
            msg  = f'Wave {self._completed_wave_n} Complete!  +${WAVE_BONUS}'
            surf = self.font_small.render(msg, True, COLOR_GOLD)
            r    = surf.get_rect(center=(GAME_WIDTH // 2, 55))
            bg   = pygame.Surface((r.width + 24, r.height + 12))
            bg.fill((20, 20, 40))
            self.screen.blit(bg, (r.x - 12, r.y - 6))
            pygame.draw.rect(self.screen, COLOR_GOLD,
                             (r.x - 12, r.y - 6, r.width + 24, r.height + 12), 2)
            self.screen.blit(surf, r)

        if self.state == STATE_GAME_OVER:
            self._draw_overlay('GAME OVER', COLOR_RED,   'Press R to restart')
        elif self.state == STATE_WIN:
            self._draw_overlay('VICTORY!',  COLOR_GOLD,  'Press R to play again')

        pygame.display.flip()

    def _draw_overlay(self, title: str, color: tuple, subtitle: str):
        # Semi-transparent dark veil over the game area only
        veil = pygame.Surface((GAME_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 165))
        self.screen.blit(veil, (0, 0))

        ts = self.font_big.render(title, True, color)
        tr = ts.get_rect(center=(GAME_WIDTH // 2, SCREEN_HEIGHT // 2 - 45))
        self.screen.blit(ts, tr)

        ss = self.font_mid.render(subtitle, True, COLOR_WHITE)
        sr = ss.get_rect(center=(GAME_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(ss, sr)
