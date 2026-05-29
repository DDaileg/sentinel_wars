"""
Currency management. All monetary transactions are routed here so balance
tuning only requires changing constants.py, not hunting through game logic.
"""

from constants import STARTING_MONEY, WAVE_BONUS, SELL_PERCENTAGE


class Economy:
    def __init__(self):
        self.money        = STARTING_MONEY
        self.total_earned = STARTING_MONEY  # lifetime earnings (useful for future stats screen)

    def can_afford(self, amount: int) -> bool:
        return self.money >= amount

    def spend(self, amount: int) -> bool:
        if self.can_afford(amount):
            self.money -= amount
            return True
        return False

    def earn(self, amount: int):
        self.money        += amount
        self.total_earned += amount

    def wave_bonus(self):
        """Called once per completed wave."""
        self.earn(WAVE_BONUS)

    def sell_tower(self, tower) -> int:
        """Refund 60% of total_spent; returns the refund amount."""
        refund = tower.sell_value
        self.earn(refund)
        return refund
