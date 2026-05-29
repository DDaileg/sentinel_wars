# All tunable game values live here so balancing never requires touching logic files.

SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
PANEL_WIDTH   = 280
GAME_WIDTH    = SCREEN_WIDTH - PANEL_WIDTH   # 1000
GAME_HEIGHT   = SCREEN_HEIGHT                # 720
TILE_SIZE     = 40
MAP_COLS      = GAME_WIDTH  // TILE_SIZE     # 25
MAP_ROWS      = GAME_HEIGHT // TILE_SIZE     # 18

FPS = 60

# ── Tile types ──────────────────────────────────────────────────────────────
TILE_GRASS = 0
TILE_PATH  = 1
TILE_WATER = 2

# ── Palette ─────────────────────────────────────────────────────────────────
COLOR_GRASS      = (34,  139,  34)
COLOR_PATH       = (180, 150, 100)
COLOR_WATER      = (64,  164, 223)
COLOR_PANEL      = (22,   22,  38)
COLOR_WHITE      = (255, 255, 255)
COLOR_BLACK      = (0,     0,   0)
COLOR_RED        = (220,  50,  50)
COLOR_GREEN      = (50,  220,  50)
COLOR_BLUE       = (50,  100, 220)
COLOR_YELLOW     = (240, 200,  50)
COLOR_ORANGE     = (240, 140,  30)
COLOR_PURPLE     = (180,  50, 220)
COLOR_CYAN       = (50,  220, 220)
COLOR_GRAY       = (120, 120, 120)
COLOR_DARK_GRAY  = (55,   55,  70)
COLOR_GOLD       = (255, 215,   0)

# Tower colour identities
COLOR_SENTINEL      = (100, 210, 100)
COLOR_GLACIER       = (100, 210, 255)
COLOR_PYRE          = (255, 120,  40)
COLOR_CONDUCTOR     = (200, 100, 255)
COLOR_LONGWATCH     = (200, 200,  60)
COLOR_TIDE_LAUNCHER = ( 30,  60, 120)
COLOR_KRAKEN        = ( 20,  90,  80)

# Enemy colour identities
COLOR_RUNNER     = (210,  80,  80)
COLOR_DASHER     = (80,  210,  80)
COLOR_IRONCLAD   = (110, 110, 130)
COLOR_SWARMLING  = (230, 230,  60)
COLOR_PHANTOM    = (160,  80, 210)
COLOR_COLOSSUS   = (190,  35,  35)

# ── Economy ──────────────────────────────────────────────────────────────────
STARTING_MONEY   = 575
STARTING_LIVES   = 50
WAVE_BONUS       = 50
AUTO_WAVE_DELAY  = 3.0   # seconds between wave complete and auto-start
SELL_PERCENTAGE  = 0.60   # fraction of total_spent returned on sell

TOWER_COSTS = {
    'Sentinel':     100,
    'Glacier':      150,
    'Pyre':         125,
    'Conductor':    175,
    'Longwatch':    200,
    'TideLauncher': 175,
    'Kraken':       250,
}

# ── Tower stats ──────────────────────────────────────────────────────────────
# range in px, fire_rate in seconds between shots, proj_speed in px/s
TOWER_STATS = {
    'Sentinel': {
        'range': 160, 'damage': 15, 'fire_rate': 0.5,
        'proj_speed': 320, 'color': COLOR_SENTINEL, 'cost': 100,
        'air_targeting': True,
    },
    'Glacier': {
        'range': 140, 'damage': 5, 'fire_rate': 2.2,
        'proj_speed': 220, 'color': COLOR_GLACIER, 'cost': 150,
        'freeze_duration': 2.0, 'slow_duration': 3.0, 'slow_factor': 0.35,
        'aoe_radius': 90,
        'air_targeting': False,
    },
    'Pyre': {
        'range': 150, 'damage': 5, 'fire_rate': 1.2,
        'proj_speed': 260, 'color': COLOR_PYRE, 'cost': 125,
        'burn_damage': 8, 'burn_duration': 3.0, 'burn_interval': 0.5,
        'air_targeting': False,
    },
    'Conductor': {
        'range': 185, 'damage': 22, 'fire_rate': 1.0,
        'proj_speed': 420, 'color': COLOR_CONDUCTOR, 'cost': 175,
        'chain_count': 4, 'chain_range': 110,
        'air_targeting': True,
    },
    'Longwatch': {
        # range=9999 → effectively global; hitscan so proj_speed is unused
        'range': 9999, 'damage': 85, 'fire_rate': 2.5,
        'proj_speed': 0, 'color': COLOR_LONGWATCH, 'cost': 200,
        'armor_pierce': True,
        'air_targeting': True,
    },
    'TideLauncher': {
        'range': 200, 'damage': 35, 'fire_rate': 2.8,
        'proj_speed': 160, 'color': COLOR_TIDE_LAUNCHER, 'cost': 175,
        'aoe_radius': 70, 'air_targeting': False, 'water_only': True,
    },
    'Kraken': {
        'range': 120, 'damage': 20, 'fire_rate': 0.8,
        'proj_speed': 300, 'color': COLOR_KRAKEN, 'cost': 250,
        'freeze_duration': 1.5, 'slow_duration': 1.0, 'slow_factor': 0.35,
        'multi_target': 2, 'air_targeting': False, 'water_only': True,
    },
}

# ── Tower upgrade paths ────────────────────────────────────────────────────────
# Each path has 2 tiers. Keys in tier dicts map directly to tower instance attrs.
TOWER_UPGRADES = {
    'Sentinel': {
        'A': [
            {'cost': 75,  'label': 'Dmg+ (22)',  'damage': 22},
            {'cost': 125, 'label': 'Dmg++ (32)', 'damage': 32},
        ],
        'B': [
            {'cost': 75,  'label': 'Rng/Spd',   'range': 200, 'fire_rate': 0.35},
            {'cost': 125, 'label': 'Rng/Spd+',  'range': 240, 'fire_rate': 0.25},
        ],
    },
    'Glacier': {
        'A': [
            {'cost': 100, 'label': 'Freeze 3s',   'freeze_duration': 3.0},
            {'cost': 150, 'label': 'Freeze 4.5s', 'freeze_duration': 4.5, 'aoe_radius': 120},
        ],
        'B': [
            {'cost': 100, 'label': 'Slow 0.20',   'slow_factor': 0.20},
            {'cost': 150, 'label': 'Slow 0.05+',  'slow_factor': 0.05, 'slow_duration': 5.0},
        ],
    },
    'Pyre': {
        'A': [
            {'cost': 100, 'label': 'Burn 14',  'burn_damage': 14},
            {'cost': 150, 'label': 'Burn 22+', 'burn_damage': 22, 'burn_duration': 4.5},
        ],
        'B': [
            {'cost': 125, 'label': '2-target', 'multi_target': 2},
            {'cost': 175, 'label': '3-target', 'multi_target': 3},
        ],
    },
    'Conductor': {
        'A': [
            {'cost': 100, 'label': '6 chains', 'chain_count': 6},
            {'cost': 150, 'label': '9 chains', 'chain_count': 9},
        ],
        'B': [
            {'cost': 125, 'label': 'Stun 0.5s', 'chain_freeze': 0.5},
            {'cost': 175, 'label': 'Stun 1s+',  'chain_freeze': 1.0, 'chain_perma_slow_chance': 0.15},
        ],
    },
    'Longwatch': {
        'A': [
            {'cost': 125, 'label': 'Dmg 130',   'damage': 130},
            {'cost': 200, 'label': 'Dmg 200+',  'damage': 200, 'oneshot_threshold': 0.20},
        ],
        'B': [
            {'cost': 125, 'label': 'Rate 1.8s', 'fire_rate': 1.8},
            {'cost': 200, 'label': 'Rate 1.2s+','fire_rate': 1.2, 'hit_slow': 0.5},
        ],
    },
    'TideLauncher': {
        'A': [
            {'cost': 100, 'label': 'Dmg+ (50)',   'damage': 50},
            {'cost': 150, 'label': 'Dmg++ (70)',  'damage': 70, 'aoe_radius': 100},
        ],
        'B': [
            {'cost': 100, 'label': 'Rate 2.0s',   'fire_rate': 2.0},
            {'cost': 150, 'label': 'Rate 1.4s',   'fire_rate': 1.4},
        ],
    },
    'Kraken': {
        'A': [
            {'cost': 100, 'label': 'Grab 3',   'multi_target': 3},
            {'cost': 150, 'label': 'Grab 4+',  'multi_target': 4, 'freeze_duration': 2.5},
        ],
        'B': [
            {'cost': 100, 'label': 'Rng+ 160',  'range': 160},
            {'cost': 150, 'label': 'Rng++ 200', 'range': 200, 'damage': 35},
        ],
    },
}

# ── Enemy stats ───────────────────────────────────────────────────────────────
# armor = fraction of damage absorbed (0.4 → 40% reduction)
ENEMY_STATS = {
    'Runner': {
        'speed': 80,  'hp': 100,  'armor': 0.0,  'radius': 12,
        'color': COLOR_RUNNER,    'flying': False, 'reward': 7,
        'freeze_resist': 0.0, 'burn_resist': 0.0, 'chain_resist': False,
        'is_elite': False, 'leak_damage': 1,
    },
    'Dasher': {
        'speed': 165, 'hp': 50,   'armor': 0.0,  'radius': 10,
        'color': COLOR_DASHER,    'flying': False, 'reward': 6,
        'freeze_resist': 0.0, 'burn_resist': 0.0, 'chain_resist': False,
        'is_elite': False, 'leak_damage': 1,
    },
    'Ironclad': {
        'speed': 50,  'hp': 250,  'armor': 0.40, 'radius': 16,
        'color': COLOR_IRONCLAD,  'flying': False, 'reward': 14,
        'freeze_resist': 0.5, 'burn_resist': 0.5, 'chain_resist': False,
        'is_elite': True, 'leak_damage': 3,
    },
    'Swarmling': {
        'speed': 210, 'hp': 28,   'armor': 0.0,  'radius': 8,
        'color': COLOR_SWARMLING, 'flying': False, 'reward': 4,
        'freeze_resist': 0.0, 'burn_resist': 0.0, 'chain_resist': False,
        'is_elite': False, 'leak_damage': 1,
    },
    'Phantom': {
        'speed': 105, 'hp': 85,   'armor': 0.0,  'radius': 11,
        'color': COLOR_PHANTOM,   'flying': True,  'reward': 11,
        'freeze_resist': 0.0, 'burn_resist': 0.0, 'chain_resist': True,
        'is_elite': False, 'leak_damage': 1,
    },
    'Colossus': {
        'speed': 38,  'hp': 1000, 'armor': 0.30, 'radius': 26,
        'color': COLOR_COLOSSUS,  'flying': False, 'reward': 50,
        'freeze_resist': 0.75, 'burn_resist': 0.5, 'chain_resist': False,
        'is_elite': True, 'leak_damage': 10,
    },
}

# ── Targeting ─────────────────────────────────────────────────────────────────
TARGETING_FIRST    = 'first'
TARGETING_LAST     = 'last'
TARGETING_STRONGEST = 'strongest'
TARGETING_CLOSEST  = 'closest'
TARGETING_MODES    = [TARGETING_FIRST, TARGETING_LAST,
                      TARGETING_STRONGEST, TARGETING_CLOSEST]
