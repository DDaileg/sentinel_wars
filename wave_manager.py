"""
Wave definitions and spawn scheduling.
Each wave is a list of groups; each group spawns `count` enemies of `type`
with `interval` seconds between each, starting `delay` seconds into the wave.

To add a new wave: append a new list of groups to WAVE_DEFINITIONS.
To rebalance: tweak counts/intervals; all enemy stats live in constants.py.
"""

from constants import ENEMY_STATS   # used implicitly via _spawn_enemy

# Wave definitions are intentionally verbose so each wave's intent is readable.
WAVE_DEFINITIONS = [
    # Wave 1 — tutorial: only Runners
    [{'type': 'Runner',    'count':  8, 'interval': 1.2, 'delay': 0.0}],

    # Wave 2 — add speed with Dashers
    [{'type': 'Runner',    'count': 10, 'interval': 1.0, 'delay': 0.0},
     {'type': 'Dasher',    'count':  5, 'interval': 0.8, 'delay': 3.0}],

    # Wave 3 — introduce armor (Ironclad)
    [{'type': 'Runner',    'count':  8, 'interval': 0.9, 'delay': 0.0},
     {'type': 'Ironclad',  'count':  3, 'interval': 2.0, 'delay': 2.5},
     {'type': 'Dasher',    'count':  6, 'interval': 0.7, 'delay': 6.0}],

    # Wave 4 — swarm density + flying Phantoms
    [{'type': 'Swarmling', 'count': 20, 'interval': 0.28,'delay': 0.0},
     {'type': 'Phantom',   'count':  4, 'interval': 1.5, 'delay': 4.0},
     {'type': 'Runner',    'count':  6, 'interval': 1.0, 'delay': 6.5}],

    # Wave 5 — first Colossus boss
    [{'type': 'Runner',    'count': 10, 'interval': 0.8, 'delay': 0.0},
     {'type': 'Ironclad',  'count':  4, 'interval': 1.5, 'delay': 3.0},
     {'type': 'Colossus',  'count':  1, 'interval': 0.0, 'delay': 9.0}],

    # Wave 6 — speed + swarm blitz
    [{'type': 'Dasher',    'count': 15, 'interval': 0.45,'delay': 0.0},
     {'type': 'Swarmling', 'count': 25, 'interval': 0.22,'delay': 2.0},
     {'type': 'Phantom',   'count':  6, 'interval': 1.1, 'delay': 5.5}],

    # Wave 7 — armored assault + flying
    [{'type': 'Ironclad',  'count':  8, 'interval': 1.1, 'delay': 0.0},
     {'type': 'Phantom',   'count':  8, 'interval': 0.9, 'delay': 4.0},
     {'type': 'Colossus',  'count':  2, 'interval': 5.0, 'delay': 7.0}],

    # Wave 8 — final gauntlet: everything at once
    [{'type': 'Swarmling', 'count': 30, 'interval': 0.18,'delay': 0.0},
     {'type': 'Dasher',    'count': 20, 'interval': 0.35,'delay': 2.5},
     {'type': 'Ironclad',  'count': 10, 'interval': 0.8, 'delay': 5.5},
     {'type': 'Phantom',   'count': 10, 'interval': 0.75,'delay': 9.0},
     {'type': 'Colossus',  'count':  3, 'interval': 4.5, 'delay': 12.0}],
]


class WaveManager:
    def __init__(self, waypoints: list):
        self.waypoints    = waypoints
        self.total_waves  = len(WAVE_DEFINITIONS)
        self.current_wave = 0   # 0-indexed internally
        self.wave_active  = False
        self.wave_complete = False
        self.game_won     = False

        self._spawn_queue = []
        self._elapsed     = 0.0

    @property
    def wave_number(self) -> int:
        """1-indexed wave number for HUD display. Clamped to total_waves."""
        return min(self.current_wave + 1, self.total_waves)

    def start_wave(self):
        if self.current_wave >= self.total_waves:
            self.game_won = True
            return
        self.wave_active   = True
        self.wave_complete = False
        self._elapsed      = 0.0
        self._spawn_queue  = []

        for group in WAVE_DEFINITIONS[self.current_wave]:
            for i in range(group['count']):
                t = group['delay'] + i * group['interval']
                self._spawn_queue.append((t, group['type']))

        self._spawn_queue.sort(key=lambda x: x[0])

    def update(self, dt: float, enemies: list) -> list:
        """Advance time, spawn due enemies, detect wave completion. Returns spawned list."""
        if not self.wave_active:
            return []

        self._elapsed += dt
        spawned = []

        while self._spawn_queue and self._spawn_queue[0][0] <= self._elapsed:
            _, etype = self._spawn_queue.pop(0)
            e = self._spawn_enemy(etype)
            enemies.append(e)
            spawned.append(e)

        # Wave ends when the spawn queue is exhausted and no enemies remain alive
        if not self._spawn_queue and not any(e.alive for e in enemies):
            self.wave_active   = False
            self.wave_complete = True
            self.current_wave += 1
            if self.current_wave >= self.total_waves:
                self.game_won = True

        return spawned

    def _spawn_enemy(self, enemy_type: str):
        # Late import to avoid circular dependency at module load time
        from enemy import Runner, Dasher, Ironclad, Swarmling, Phantom, Colossus
        classes = {
            'Runner':    Runner,
            'Dasher':    Dasher,
            'Ironclad':  Ironclad,
            'Swarmling': Swarmling,
            'Phantom':   Phantom,
            'Colossus':  Colossus,
        }
        return classes[enemy_type](self.waypoints)
