"""
Map definition. The tile grid is data-driven: swap WAYPOINT_TILES for a new list
and the entire path regenerates. Water tiles are decorative and future boat-tower
support can check for TILE_WATER here.
"""

import pygame
from constants import (TILE_SIZE, MAP_COLS, MAP_ROWS, GAME_WIDTH, GAME_HEIGHT,
                       TILE_GRASS, TILE_PATH, TILE_WATER,
                       COLOR_GRASS, COLOR_PATH, COLOR_WATER, COLOR_BLACK, COLOR_RED)

# Path defined as (col, row) tile coordinates.
# (-1, 8) and (25, 4) are intentionally off-screen — enemies enter/exit there.
WAYPOINT_TILES = [
    (-1,  8),   # spawn (off left edge)
    ( 6,  8),
    ( 6,  2),
    (13,  2),
    (13, 15),
    (19, 15),
    (19,  4),
    (25,  4),   # exit (off right edge)
]


def _tile_center(col: int, row: int) -> tuple[int, int]:
    return (col * TILE_SIZE + TILE_SIZE // 2,
            row * TILE_SIZE + TILE_SIZE // 2)


# Pixel-space waypoints used by Enemy movement code
WAYPOINTS = [_tile_center(c, r) for c, r in WAYPOINT_TILES]


def _build_grid():
    """
    Derive a 2-D tile grid from WAYPOINT_TILES.
    Segments between consecutive waypoints must be axis-aligned (no diagonals).
    """
    grid = [[TILE_GRASS] * MAP_COLS for _ in range(MAP_ROWS)]

    def clamp_col(c): return max(0, min(MAP_COLS - 1, c))
    def clamp_row(r): return max(0, min(MAP_ROWS - 1, r))

    for i in range(len(WAYPOINT_TILES) - 1):
        c0, r0 = WAYPOINT_TILES[i]
        c1, r1 = WAYPOINT_TILES[i + 1]
        c0, c1 = clamp_col(c0), clamp_col(c1)
        r0, r1 = clamp_row(r0), clamp_row(r1)

        if c0 == c1:  # vertical segment
            for r in range(min(r0, r1), max(r0, r1) + 1):
                grid[r][c0] = TILE_PATH
        else:          # horizontal segment
            for c in range(min(c0, c1), max(c0, c1) + 1):
                grid[r0][c] = TILE_PATH

    # Water lake — above the top horizontal path (row 2, cols 6–13)
    # Water towers here cover the long top path segment
    for r in range(0, 2):
        for c in range(5, 14):
            if grid[r][c] == TILE_GRASS:
                grid[r][c] = TILE_WATER

    # Water lake — below the bottom horizontal path (row 15, cols 13–19)
    # Water towers here cover the long bottom path segment
    for r in range(16, 18):
        for c in range(12, 21):
            if grid[r][c] == TILE_GRASS:
                grid[r][c] = TILE_WATER

    return grid


class GameMap:
    def __init__(self):
        self.grid      = _build_grid()
        self.waypoints = WAYPOINTS
        self._surface  = self._build_surface()

    # ── surface pre-render ────────────────────────────────────────────────────
    def _build_surface(self) -> pygame.Surface:
        surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        for row in range(MAP_ROWS):
            for col in range(MAP_COLS):
                tile = self.grid[row][col]
                rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE,
                                   TILE_SIZE, TILE_SIZE)
                if tile == TILE_GRASS:
                    pygame.draw.rect(surf, COLOR_GRASS, rect)
                    pygame.draw.rect(surf, (22, 110, 22), rect, 1)
                elif tile == TILE_PATH:
                    pygame.draw.rect(surf, COLOR_PATH, rect)
                    pygame.draw.rect(surf, (148, 118, 78), rect, 1)
                elif tile == TILE_WATER:
                    pygame.draw.rect(surf, COLOR_WATER, rect)
                    pygame.draw.rect(surf, (40, 140, 200), rect, 1)

        # Entry arrow
        ex, ey = 4, 8 * TILE_SIZE + TILE_SIZE // 2
        pygame.draw.polygon(surf, COLOR_RED,
            [(ex, ey - 9), (ex + 18, ey), (ex, ey + 9)])

        # Exit arrow
        xx = GAME_WIDTH - 20
        xy = 4 * TILE_SIZE + TILE_SIZE // 2
        pygame.draw.polygon(surf, COLOR_RED,
            [(xx - 4, xy - 9), (xx + 14, xy), (xx - 4, xy + 9)])

        return surf

    # ── public API ────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        surface.blit(self._surface, (0, 0))

    def _to_tile(self, px: int, py: int) -> tuple[int, int]:
        return px // TILE_SIZE, py // TILE_SIZE

    def is_buildable(self, px: int, py: int) -> bool:
        col, row = self._to_tile(px, py)
        if 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS:
            return self.grid[row][col] == TILE_GRASS
        return False

    def snap_to_tile_center(self, px: int, py: int) -> tuple[int, int]:
        col, row = self._to_tile(px, py)
        col = max(0, min(MAP_COLS - 1, col))
        row = max(0, min(MAP_ROWS - 1, row))
        return _tile_center(col, row)

    def is_tile_occupied(self, px: int, py: int, towers: list) -> bool:
        sx, sy = self.snap_to_tile_center(px, py)
        for t in towers:
            tx, ty = self.snap_to_tile_center(t.x, t.y)
            if tx == sx and ty == sy:
                return True
        return False

    def is_water_tile(self, px: int, py: int) -> bool:
        col, row = self._to_tile(px, py)
        return (0 <= col < MAP_COLS and 0 <= row < MAP_ROWS
                and self.grid[row][col] == TILE_WATER)

    def is_water_buildable(self, px: int, py: int, towers: list) -> bool:
        return self.is_water_tile(px, py) and not self.is_tile_occupied(px, py, towers)
