"""Finite elemental trails attached to tagged moving objects."""
from dataclasses import dataclass
import math
from game.systems.elements import apply_elemental_damage
from game.utils.large_number import LargeNumber


@dataclass
class Trail:
    x: float
    y: float
    element: str
    damage: object
    remaining: float = 2.0


class TrailSystem:
    MAX_TRAILS = 150
    INTERVAL = .18

    def __init__(self):
        self.trails = []

    def reset(self):
        self.trails.clear()

    def emit(self, source, dt):
        element = getattr(source, 'trail_element', None)
        if not element:
            return
        previous = getattr(source, '_trail_previous', None)
        source._trail_previous = (source.x, source.y)
        if previous is not None and math.hypot(source.x - previous[0], source.y - previous[1]) < .001:
            return
        timer = getattr(source, '_trail_timer', 0) - dt
        if timer <= 0:
            damage = LargeNumber(getattr(source, 'damage', 1)) * .2
            self.trails.append(Trail(source.x, source.y, element, damage))
            self.trails = self.trails[-self.MAX_TRAILS:]
            timer = self.INTERVAL
        source._trail_timer = timer

    def update(self, enemies, enemy_types, dt):
        killed = []
        for trail in self.trails:
            active = min(max(dt, 0), trail.remaining)
            for enemy in enemies[:]:
                if math.hypot(enemy.x - trail.x, enemy.y - trail.y) <= .22:
                    amount = apply_elemental_damage(trail.damage * active, trail.element,
                                                    enemy_types[enemy.type].get('resistances', {}))
                    enemy.take_damage(amount)
                    if enemy.is_dead():
                        enemies.remove(enemy)
                        killed.append(enemy)
            trail.remaining -= active
        self.trails = [trail for trail in self.trails if trail.remaining > 0]
        return killed
