"""
Status effects are composed onto enemies at runtime (not inheritance).
Each effect is a self-contained object that knows its own duration and parameters.
The enemy's update loop drives ticks and transitions (e.g. freeze → slow on thaw).
"""


class StatusEffect:
    def __init__(self, effect_type: str, duration: float):
        self.effect_type = effect_type
        self.duration    = duration
        self.elapsed     = 0.0
        self.active      = True

    def update(self, dt: float):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.active = False

    @property
    def remaining(self) -> float:
        return max(0.0, self.duration - self.elapsed)


class SlowEffect(StatusEffect):
    """slow_factor is a speed multiplier: 0.35 → enemy moves at 35% normal speed."""
    def __init__(self, duration: float, slow_factor: float):
        super().__init__('slow', duration)
        self.slow_factor = slow_factor


class FreezeEffect(StatusEffect):
    """
    Full movement stop for freeze_duration.
    When it expires, Enemy.update() reads thawed=False and queues a SlowEffect.
    thawed is flipped to True immediately so the slow is only queued once.
    Re-freezing extends duration by base / 2^n (geometric decay) rather than resetting.
    extension_count tracks how many times this freeze has been extended.
    """
    def __init__(self, freeze_duration: float, slow_duration: float, slow_factor: float):
        super().__init__('freeze', freeze_duration)
        self.freeze_duration   = freeze_duration
        self.slow_duration     = slow_duration
        self.slow_factor       = slow_factor
        self.thawed            = False
        self.extension_count   = 0


class BurnEffect(StatusEffect):
    """
    Deals damage_per_tick every tick_interval seconds for 'duration' seconds.
    Damage application is handled by Enemy.update() via consume_tick().
    """
    def __init__(self, duration: float, damage_per_tick: float, tick_interval: float):
        super().__init__('burn', duration)
        self.damage_per_tick = damage_per_tick
        self.tick_interval   = tick_interval
        self.tick_timer      = 0.0

    def update(self, dt: float):
        super().update(dt)
        self.tick_timer += dt

    def consume_tick(self) -> bool:
        """Returns True and resets accumulator when a damage tick is due."""
        if self.tick_timer >= self.tick_interval:
            self.tick_timer -= self.tick_interval
            return True
        return False


class WetEffect(StatusEffect):
    """
    Applied by water towers (TideLauncher, Kraken). Lasts 0.3 s.
    Provides a minor speed reduction; enables Conductor's 1.1x damage bonus
    and lightning burn ignition at 5 stacks.
    Refreshes on re-application; takes the stronger (lower) slow_factor if refreshed.
    """
    def __init__(self, slow_factor: float):
        super().__init__('wet', 0.3)
        self.slow_factor = slow_factor
