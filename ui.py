"""
HUD and panel rendering. All drawing is pure pygame — no image files.
The panel (right 280 px) contains: stats, tower buttons, selected-tower info,
and a controls legend. The game area (left 1000 px) receives the placement ghost.
"""

import pygame
import math
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, PANEL_WIDTH, GAME_WIDTH,
    TOWER_COSTS, TOWER_STATS, TOWER_UPGRADES,
    COLOR_PANEL, COLOR_BLACK, COLOR_WHITE, COLOR_GRAY, COLOR_DARK_GRAY,
    COLOR_RED, COLOR_GREEN, COLOR_GOLD, COLOR_YELLOW, COLOR_CYAN,
    COLOR_SENTINEL, COLOR_GLACIER, COLOR_PYRE, COLOR_CONDUCTOR, COLOR_LONGWATCH,
    COLOR_TIDE_LAUNCHER, COLOR_KRAKEN,
)

LAND_TOWER_ORDER  = ['Sentinel', 'Glacier', 'Pyre', 'Conductor', 'Longwatch']
WATER_TOWER_ORDER = ['TideLauncher', 'Kraken']
TOWER_ORDER       = LAND_TOWER_ORDER + WATER_TOWER_ORDER

TOWER_COLORS = {
    'Sentinel':     COLOR_SENTINEL,
    'Glacier':      COLOR_GLACIER,
    'Pyre':         COLOR_PYRE,
    'Conductor':    COLOR_CONDUCTOR,
    'Longwatch':    COLOR_LONGWATCH,
    'TideLauncher': COLOR_TIDE_LAUNCHER,
    'Kraken':       COLOR_KRAKEN,
}


class UI:
    def __init__(self):
        self.panel_x = SCREEN_WIDTH - PANEL_WIDTH

        self.font_title = pygame.font.SysFont('monospace', 20, bold=True)
        self.font_mid   = pygame.font.SysFont('monospace', 17)
        self.font_small = pygame.font.SysFont('monospace', 13)

        self.selected_tower_type = None   # panel selection for placement
        self.hovered_tower_type  = None

        # Auto-wave and speed toggle — side-by-side at y=202
        half_w = (PANEL_WIDTH - 24) // 2
        self._auto_wave_btn = pygame.Rect(self.panel_x + 10,           202, half_w, 26)
        self._speed_btn     = pygame.Rect(self.panel_x + 14 + half_w,  202, half_w, 26)

        # Build tower button rects — smaller to fit 7 total (5 land + 2 water)
        self._buttons: dict[str, pygame.Rect] = {}
        btn_w  = PANEL_WIDTH - 20
        btn_h  = 44
        btn_gap = 4
        base_y  = 245
        y = base_y
        for name in LAND_TOWER_ORDER:
            self._buttons[name] = pygame.Rect(self.panel_x + 10, y, btn_w, btn_h)
            y += btn_h + btn_gap
        self._water_label_y = y + 4   # separator label position
        y += 18                        # space for label
        for name in WATER_TOWER_ORDER:
            self._buttons[name] = pygame.Rect(self.panel_x + 10, y, btn_w, btn_h)
            y += btn_h + btn_gap

        # Upgrade button rects — populated each draw frame when a tower is selected
        self._upgrade_btns: dict[str, pygame.Rect] = {}

    # ── input helpers ─────────────────────────────────────────────────────────
    def is_panel_click(self, mx: int, my: int) -> bool:
        return mx >= self.panel_x

    def handle_click(self, mx: int, my: int, economy):
        """Returns a string token identifying what was clicked, or None."""
        if self._auto_wave_btn.collidepoint(mx, my):
            return 'toggle_auto_wave'
        if self._speed_btn.collidepoint(mx, my):
            return 'toggle_speed'
        for key, rect in self._upgrade_btns.items():
            if rect.collidepoint(mx, my):
                return f'upgrade_{key}'
        for name, rect in self._buttons.items():
            if rect.collidepoint(mx, my):
                if economy.can_afford(TOWER_COSTS[name]):
                    self.selected_tower_type = (
                        None if self.selected_tower_type == name else name)
                return name
        return None

    def handle_hover(self, mx: int, my: int):
        self.hovered_tower_type = next(
            (n for n, r in self._buttons.items() if r.collidepoint(mx, my)), None)

    def clear_selection(self):
        self.selected_tower_type = None

    # ── main draw ─────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, economy, lives: int,
             wave_number: int, total_waves: int, wave_active: bool,
             selected_tower_obj=None, auto_wave: bool = False,
             auto_wave_timer: float = 0.0, speed_mult: float = 1.0):

        money = economy.money
        px = self.panel_x
        # Background
        pygame.draw.rect(surface, COLOR_PANEL,
                         pygame.Rect(px, 0, PANEL_WIDTH, SCREEN_HEIGHT))
        pygame.draw.line(surface, COLOR_GRAY, (px, 0), (px, SCREEN_HEIGHT), 2)

        x, y = px + 10, 10

        # ── Title
        self._text(surface, 'SENTINEL WARS', x, y, self.font_title, COLOR_GOLD)
        y += 30
        self._hline(surface, y); y += 8

        # ── Stats
        self._stat(surface, x, y, 'MONEY',  f'${money}',          COLOR_GOLD)
        y += 28
        self._stat(surface, x, y, 'LIVES',  str(lives),
                   COLOR_GREEN if lives > 5 else COLOR_RED)
        y += 28
        self._stat(surface, x, y, 'WAVE',   f'{wave_number}/{total_waves}', COLOR_WHITE)
        y += 28
        status      = 'ACTIVE' if wave_active else 'READY'
        status_col  = COLOR_RED if wave_active else COLOR_GREEN
        self._stat(surface, x, y, 'STATUS', status, status_col)
        y += 28

        if not wave_active:
            hint = self.font_small.render('[SPACE] Start Wave', True, COLOR_YELLOW)
            surface.blit(hint, (x, y))

        # ── Auto-wave + speed toggle buttons (side-by-side)
        self._draw_auto_wave_btn(surface, auto_wave, auto_wave_timer)
        self._draw_speed_btn(surface, speed_mult)

        self._hline(surface, 236); y = 244

        # ── Tower buttons OR upgrade panel
        if selected_tower_obj:
            self._draw_tower_info(surface, selected_tower_obj, economy)
        else:
            self._upgrade_btns.clear()
            self._text(surface, 'PLACE TOWER:', x, y, self.font_mid, COLOR_WHITE)
            y += 22
            for name in LAND_TOWER_ORDER:
                self._draw_tower_button(surface, name, money)
            # Water tower separator
            self._text(surface, '── WATER ──',
                       x, self._water_label_y, self.font_small, COLOR_CYAN)
            for name in WATER_TOWER_ORDER:
                self._draw_tower_button(surface, name, money)

        # ── Controls legend at bottom
        legend_y = SCREEN_HEIGHT - 100
        self._hline(surface, legend_y)
        for i, line in enumerate([
            'LClick: Place/Select',
            'RClick: Cycle target',
            '[S]:Sell [U]:Upgrade',
            '[A]:Auto  [2]:Speed',
        ]):
            self._text(surface, line, x, legend_y + 6 + i * 17,
                       self.font_small, COLOR_GRAY)

    # ── auto-wave button ──────────────────────────────────────────────────────
    def _draw_auto_wave_btn(self, surface: pygame.Surface,
                            auto_wave: bool, auto_wave_timer: float):
        rect  = self._auto_wave_btn
        bg    = (30, 90, 30) if auto_wave else (40, 40, 55)
        bdr   = COLOR_GREEN  if auto_wave else COLOR_GRAY
        pygame.draw.rect(surface, bg,  rect, border_radius=4)
        pygame.draw.rect(surface, bdr, rect, 1, border_radius=4)
        label = 'AUTO: ON' if auto_wave else 'AUTO: OFF'
        col   = COLOR_GREEN if auto_wave else COLOR_GRAY
        self._text(surface, label, rect.x + 5, rect.y + 6, self.font_small, col)
        if auto_wave and auto_wave_timer > 0:
            cd = self.font_small.render(f'{auto_wave_timer:.1f}s', True, COLOR_YELLOW)
            surface.blit(cd, (rect.right - cd.get_width() - 4, rect.y + 6))

    # ── speed button ──────────────────────────────────────────────────────────
    def _draw_speed_btn(self, surface: pygame.Surface, speed_mult: float):
        rect  = self._speed_btn
        is_2x = speed_mult >= 2.0
        bg    = (90, 60, 20) if is_2x else (40, 40, 55)
        bdr   = COLOR_YELLOW if is_2x else COLOR_GRAY
        pygame.draw.rect(surface, bg,  rect, border_radius=4)
        pygame.draw.rect(surface, bdr, rect, 1, border_radius=4)
        label = 'SPEED: 2x' if is_2x else 'SPEED: 1x'
        col   = COLOR_YELLOW if is_2x else COLOR_GRAY
        self._text(surface, label, rect.x + 5, rect.y + 6, self.font_small, col)

    # ── tower button ──────────────────────────────────────────────────────────
    def _draw_tower_button(self, surface: pygame.Surface, name: str, money: int):
        rect        = self._buttons[name]
        cost        = TOWER_COSTS[name]
        can_afford  = money >= cost
        is_selected = self.selected_tower_type == name
        is_hovered  = self.hovered_tower_type  == name
        col         = TOWER_COLORS[name]
        is_water    = name in WATER_TOWER_ORDER

        if is_selected:
            bg  = tuple(min(c + 55, 255) for c in col)
            bdr = COLOR_YELLOW; bw = 3
        elif is_hovered and can_afford:
            bg  = COLOR_DARK_GRAY; bdr = col; bw = 2
        else:
            bg  = (28, 28, 44); bdr = (col if can_afford else COLOR_GRAY); bw = 1

        pygame.draw.rect(surface, bg,  rect, border_radius=5)
        pygame.draw.rect(surface, bdr, rect, bw, border_radius=5)

        # Mini icon — water towers get a wave decoration
        ic = col if can_afford else COLOR_DARK_GRAY
        ix, iy = rect.x + 22, rect.centery
        pygame.draw.circle(surface, ic, (ix, iy), 10)
        pygame.draw.circle(surface, COLOR_BLACK, (ix, iy), 10, 1)
        if is_water:
            pygame.draw.arc(surface, COLOR_CYAN,
                            pygame.Rect(ix - 8, iy - 3, 16, 8), 0, math.pi, 2)

        # Label + cost
        nc = COLOR_WHITE if can_afford else COLOR_GRAY
        label = 'Tide' if name == 'TideLauncher' else name
        self._text(surface, label,      rect.x + 38, rect.y + 4,  self.font_small, nc)
        cc = COLOR_GOLD if can_afford else COLOR_RED
        self._text(surface, f'${cost}', rect.x + 38, rect.y + 22, self.font_small, cc)

    # ── selected tower info + upgrade panel ───────────────────────────────────
    def _draw_tower_info(self, surface: pygame.Surface, tower, economy):
        """Upgrade panel shown when a placed tower is selected."""
        self._upgrade_btns.clear()
        x   = self.panel_x + 10
        y   = 244
        col = TOWER_COLORS.get(tower.tower_type, COLOR_WHITE)

        self._text(surface, tower.tower_type + ' [SEL]', x, y, self.font_mid, col)
        y += 22
        self._text(surface, f'Target: {tower.targeting_mode}',
                   x, y, self.font_small, COLOR_CYAN)
        y += 18
        self._text(surface, f'Sell: ${tower.sell_value}  [S]',
                   x, y, self.font_small, COLOR_GOLD)
        y += 18
        self._text(surface, 'RClick: change target',
                   x, y, self.font_small, COLOR_GRAY)
        y += 22
        self._hline(surface, y); y += 8
        self._text(surface, 'UPGRADES:', x, y, self.font_mid, COLOR_WHITE)
        y += 22

        upgrades   = TOWER_UPGRADES.get(tower.tower_type, {})
        btn_w      = PANEL_WIDTH - 20
        for path in ('A', 'B'):
            tiers       = upgrades.get(path, [])
            path_locked = (tower.upgrade_path is not None
                           and tower.upgrade_path != path)
            for tier_idx, tier_data in enumerate(tiers):
                bought    = (tower.upgrade_path == path
                             and tower.upgrade_tier > tier_idx)
                available = (not path_locked
                             and tower.upgrade_tier == tier_idx
                             and tower.upgrade_path in (None, path))

                rect = pygame.Rect(x, y, btn_w, 34)

                if bought:
                    bg, bdr = (20, 60, 20), COLOR_GREEN
                elif path_locked or not available:
                    bg, bdr = (18, 18, 28), (45, 45, 55)
                elif economy.can_afford(tier_data['cost']):
                    bg, bdr = (30, 30, 55), col
                else:
                    bg, bdr = (30, 30, 55), COLOR_GRAY

                pygame.draw.rect(surface, bg,  rect, border_radius=4)
                pygame.draw.rect(surface, bdr, rect, 1, border_radius=4)

                key = f'{path}{tier_idx + 1}'
                self._upgrade_btns[key] = rect

                if bought:
                    status_col, status = COLOR_GREEN, 'OWNED'
                elif path_locked or not available:
                    status_col, status = (45, 45, 55), 'LOCKED'
                elif economy.can_afford(tier_data['cost']):
                    status_col, status = COLOR_GOLD, f'${tier_data["cost"]}'
                else:
                    status_col, status = COLOR_RED, f'${tier_data["cost"]}'

                label_col = COLOR_WHITE if (bought or available) else (55, 55, 65)
                self._text(surface, f'[{path}{tier_idx+1}] {tier_data["label"]}',
                           x + 5, y + 4, self.font_small, label_col)
                sc = self.font_small.render(status, True, status_col)
                surface.blit(sc, (rect.right - sc.get_width() - 5, y + 4))
                y += 38

        if y + 14 < SCREEN_HEIGHT - 104:
            self._text(surface, '[U] upgrade  click btn',
                       x, y + 4, self.font_small, COLOR_GRAY)

    # ── placement preview ─────────────────────────────────────────────────────
    def draw_placement_preview(self, surface: pygame.Surface, mx: int, my: int,
                                tower_type: str, game_map, towers: list):
        if mx >= self.panel_x:
            return
        is_water_tower = TOWER_STATS[tower_type].get('water_only', False)
        if is_water_tower:
            on_water = game_map.is_water_tile(mx, my)
            occupied = game_map.is_tile_occupied(mx, my, towers)
            can      = on_water and not occupied
        else:
            can = (game_map.is_buildable(mx, my) and
                   not game_map.is_tile_occupied(mx, my, towers))

        sx, sy = game_map.snap_to_tile_center(mx, my)
        col    = TOWER_COLORS[tower_type]

        if can:
            raw_r = TOWER_STATS[tower_type]['range']
            display_r = min(int(raw_r), 900)
            alpha = pygame.Surface((GAME_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(alpha, (*col, 35), (sx, sy), display_r)
            surface.blit(alpha, (0, 0))
            pygame.draw.circle(surface, col, (sx, sy), 15, 2)
        else:
            pygame.draw.circle(surface, COLOR_RED, (sx, sy), 15, 2)
            pygame.draw.line(surface, COLOR_RED, (sx - 10, sy - 10), (sx + 10, sy + 10), 2)
            pygame.draw.line(surface, COLOR_RED, (sx + 10, sy - 10), (sx - 10, sy + 10), 2)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _text(self, surface, text, x, y, font, color):
        surface.blit(font.render(text, True, color), (x, y))

    def _stat(self, surface, x, y, label, value, vcolor):
        lbl = self.font_small.render(f'{label}:', True, COLOR_GRAY)
        val = self.font_mid.render(value, True, vcolor)
        surface.blit(lbl, (x, y + 4))
        surface.blit(val, (x + 80, y))

    def _hline(self, surface, y):
        pygame.draw.line(surface, COLOR_GRAY,
                         (self.panel_x + 5, y),
                         (self.panel_x + PANEL_WIDTH - 5, y), 1)
