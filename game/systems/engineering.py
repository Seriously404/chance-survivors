"""Pure wave-defense objective, structures, repairs and active engineering.

Enemies attack the relay, while placed walls intercept their route. Structures
have finite health and lifetime. Positioning, repairs and short buffs matter;
placing a turret never switches off incoming pressure.
"""

from dataclasses import dataclass, field
import math

from game.ability_scripts.effects import Summon
from game.systems.combat_bonuses import effect_multiplier, HealingBudget
from game.systems.items import item_stat
from game.utils.large_number import LargeNumber


ENGINEER_DEPLOY_SCRIPTS = frozenset({
    'wall', 'arc_turret', 'flame_turret', 'frost_turret', 'turret', 'sentinel',
})
ENGINEER_SUPPORT_SCRIPTS = frozenset({
    'repair_pulse', 'overclock', 'architect_protocol',
})
ENGINEER_STARTER_IDS = (
    'engineer-repair-gun', 'engineer-turret', 'engineer-wall',
    'engineer-overclock', 'engineer-repair-pulse',
)


def engineer_starter_items():
    """Return detached starter records for atomic quest selection."""
    from game.systems.items import create_item_catalog
    catalog = {item['id']: item for item in create_item_catalog()}
    return [catalog[item_id] for item_id in ENGINEER_STARTER_IDS]


def _distance_to_segment(x, y, start_x, start_y, end_x, end_y):
    dx, dy = end_x - start_x, end_y - start_y
    length = dx * dx + dy * dy
    fraction = max(0.0, min(1.0, ((x - start_x) * dx + (y - start_y) * dy)
                            / length)) if length else 0.0
    return math.hypot(x - start_x - fraction * dx,
                      y - start_y - fraction * dy), fraction


@dataclass
class DefenseObjective:
    x: float
    y: float
    max_health: object = field(default_factory=lambda: LargeNumber(1200))
    health: object = field(default_factory=lambda: LargeNumber(1200))
    structure_kind: str = 'relay'
    radius: float = .55

    def take_damage(self, amount):
        self.health = max(LargeNumber(0), LargeNumber(self.health) - amount)

    def repair(self, amount):
        if self.health <= 0:
            return LargeNumber(0)
        actual = min(max(LargeNumber(0), self.max_health - self.health),
                     max(LargeNumber(0), LargeNumber(amount)))
        self.health += actual
        return actual


class EngineeringDefense:
    """An objective-driven run with bounded deployments and kill-based waves."""

    MAX_STRUCTURES = 6
    PLACEMENT_RANGE = 3.5

    def __init__(self, x=0.0, y=0.0):
        self.objective = DefenseObjective(x, y)
        self.structures = []
        self.wave = 1
        self.completed_waves = 0
        self.wave_kills = 0
        self.protocol_remaining = 0.0
        self.last_error = ''

    @classmethod
    def create(cls, x=0.0, y=0.0):
        return cls(x, y)

    def to_dict(self):
        """Return JSON-safe active defense state, including damaged buildings."""
        def safe(value):
            if isinstance(value, HealingBudget):
                return {"remaining": str(value.remaining)}
            if isinstance(value, LargeNumber):
                return str(value)
            if isinstance(value, dict):
                return {key: safe(item) for key, item in value.items()}
            if isinstance(value, (tuple, list)):
                return [safe(item) for item in value]
            return value

        structures = []
        for ally in self.living_structures():
            record = dict(vars(ally))
            record.pop('_trail_previous', None)
            record.pop('_trail_timer', None)
            structures.append(safe(record))
        return {
            'version': 1, 'objective': safe(vars(self.objective)),
            'wave': self.wave, 'completed_waves': self.completed_waves,
            'wave_kills': self.wave_kills, 'protocol_remaining': self.protocol_remaining,
            'structures': structures,
        }

    @classmethod
    def from_dict(cls, data):
        """Validate and rebuild the objective and live structure snapshots."""
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('Unsupported engineering save version')

        def finite(value, minimum=None):
            if isinstance(value, bool):
                raise ValueError('Invalid engineering numeric value')
            result = float(value)
            if not math.isfinite(result) or (minimum is not None and result < minimum):
                raise ValueError('Invalid engineering numeric value')
            return result

        objective = data.get('objective', {})
        defense = cls(finite(objective['x']), finite(objective['y']))
        defense.objective.max_health = LargeNumber(objective['max_health'])
        defense.objective.health = LargeNumber(objective['health'])
        if (defense.objective.max_health <= 0 or defense.objective.health < 0
                or defense.objective.health > defense.objective.max_health):
            raise ValueError('Invalid relay health')
        for field_name in ('wave', 'completed_waves', 'wave_kills'):
            value = data[field_name]
            if type(value) is not int or value < (1 if field_name == 'wave' else 0):
                raise ValueError('Invalid defense wave')
            setattr(defense, field_name, value)
        if defense.wave != defense.completed_waves + 1 or defense.wave_kills >= defense.wave_target:
            raise ValueError('Inconsistent defense wave progress')
        defense.protocol_remaining = finite(data.get('protocol_remaining', 0), 0)
        records = data.get('structures', [])
        if not isinstance(records, list) or len(records) > cls.MAX_STRUCTURES:
            raise ValueError('Invalid saved structure count')
        for record in records:
            kind = record.get('structure_kind')
            if kind not in ENGINEER_DEPLOY_SCRIPTS:
                raise ValueError('Invalid saved structure type')
            ally = Summon(
                finite(record['x']), finite(record['y']),
                finite(record['remaining'], 0), LargeNumber(record['damage']),
                str(record['element']), bool(record.get('mobile', False)),
            )
            ally.structure_kind = kind
            ally.health = LargeNumber(record['health'])
            ally.max_health = LargeNumber(record['max_health'])
            if (ally.max_health <= 0 or ally.health <= 0 or ally.damage < 0
                    or ally.health > ally.max_health):
                raise ValueError('Invalid saved structure health')
            for name in ('attack_timer', 'attack_interval', 'overclock_remaining',
                         'protocol_remaining', 'explosion_radius', 'homing_strength',
                         'elemental_bonus_pct', 'healing_bonus_pct', 'critical_chance'):
                value = record.get(name, getattr(ally, name))
                setattr(ally, name, finite(value))
            if ally.attack_interval < .15 or ally.remaining > 180:
                raise ValueError('Invalid structure timing')
            for name in ('piercing', 'bounces'):
                value = record.get(name, 0)
                if type(value) is not int or value < 0:
                    raise ValueError('Invalid structure projectile count')
                setattr(ally, name, value)
            ally.elemental_core = record.get('elemental_core')
            ally.heal_on_damage = bool(record.get('heal_on_damage', False))
            budget = record.get('healing_budget')
            ally.healing_budget = (HealingBudget(budget['remaining'])
                                   if budget is not None else None)
            ally.trail_element = record.get('trail_element')
            ally.damage_components = [
                {'element': part['element'], 'damage': LargeNumber(part['damage'])}
                for part in record.get('damage_components', [])
            ]
            defense.structures.append(ally)
        return defense

    @property
    def failed(self):
        return self.objective.health <= 0

    @property
    def wave_target(self):
        return 12 + (self.wave - 1) * 5

    def register_kills(self, count):
        """Advance only through defeated enemies, never a waiting timer."""
        self.wave_kills += max(0, int(count))
        while self.wave_kills >= self.wave_target:
            self.wave_kills -= self.wave_target
            self.completed_waves += 1
            self.wave += 1
            # The relay scales with player-earned progress and keeps its health
            # fraction. This is not a free heal or a hidden enemy-level gate.
            ratio = LargeNumber(self.objective.health) / self.objective.max_health
            self.objective.max_health *= LargeNumber('1.12')
            self.objective.health = self.objective.max_health * ratio
        return self.completed_waves

    def living_structures(self):
        return [s for s in self.structures
                if s.health > 0 and s.remaining > 0]

    def deploy(self, item, player, angle, cursor_position=None):
        """Place a finite structure near the cursor, rejecting blocked slots."""
        self.structures[:] = self.living_structures()
        if len(self.structures) >= self.MAX_STRUCTURES:
            self.last_error = 'Structure limit reached. Protect or replace existing defenses.'
            return None
        if cursor_position is None:
            x = player.x + math.cos(angle) * 1.3
            y = player.y + math.sin(angle) * 1.3
        else:
            x, y = map(float, cursor_position)
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError('Structure position must be finite')
            distance = math.hypot(x - player.x, y - player.y)
            if distance > self.PLACEMENT_RANGE:
                x = player.x + (x - player.x) / distance * self.PLACEMENT_RANGE
                y = player.y + (y - player.y) / distance * self.PLACEMENT_RANGE
        if math.hypot(x - self.objective.x, y - self.objective.y) < .85 or any(
                math.hypot(x - s.x, y - s.y) < .65 for s in self.structures):
            self.last_error = 'Choose clear ground outside the relay and existing structures.'
            return None
        stats = item['stats']
        script = stats.get('script', 'turret')
        wall = script == 'wall'
        health = max(LargeNumber(1), LargeNumber(item_stat(
            item, 'structure_health', 180 if wall else 100)))
        ally = Summon(
            x, y, min(180.0, max(5.0, item_stat(item, 'summon_duration', 60))),
            0 if wall else max(1, int(item_stat(item, 'summon_damage', 12))),
            str(stats.get('element', 'arcane')), mobile=script == 'sentinel',
        )
        ally.health = health
        ally.max_health = health
        ally.structure_kind = script
        ally.attack_interval = max(.15, min(3.0, float(
            stats.get('attack_interval', 1.0))))
        if script == 'flame_turret':
            ally.explosion_radius = .4
        elif script == 'frost_turret':
            ally.piercing = 2
        elif script == 'arc_turret':
            ally.bounces = 2
        self.structures.append(ally)
        self.last_error = ''
        return ally

    def support(self, script, player, healing_bonus_pct=0.0):
        nearby = [s for s in self.living_structures()
                  if math.hypot(s.x - player.x, s.y - player.y) <= 4]
        if script == 'repair_pulse':
            targets = [*nearby]
            if math.hypot(self.objective.x - player.x,
                          self.objective.y - player.y) <= 4:
                targets.append(self.objective)
            restored = LargeNumber(0)
            for target in targets:
                amount = target.max_health * .15 * effect_multiplier(healing_bonus_pct)
                if isinstance(target, DefenseObjective):
                    restored += target.repair(amount)
                else:
                    actual = min(target.max_health - target.health, amount)
                    target.health += actual
                    restored += actual
            return restored > 0
        if script == 'overclock':
            turrets = [s for s in nearby if s.structure_kind != 'wall']
            for turret in turrets:
                turret.overclock_remaining = max(turret.overclock_remaining, 4.0)
            return bool(turrets)
        if script == 'architect_protocol':
            if not nearby:
                return False
            self.protocol_remaining = max(self.protocol_remaining, 8.0)
            for turret in nearby:
                turret.overclock_remaining = max(turret.overclock_remaining, 8.0)
                turret.protocol_remaining = max(turret.protocol_remaining, 8.0)
            return True
        return False

    def target_for(self, enemy):
        """Aim at the relay unless an intact wall intercepts its approach."""
        walls = []
        for wall in self.living_structures():
            if wall.structure_kind != 'wall':
                continue
            distance, fraction = _distance_to_segment(
                wall.x, wall.y, enemy.x, enemy.y,
                self.objective.x, self.objective.y)
            if distance <= .45 and 0 <= fraction < 1:
                walls.append(wall)
        return min(walls, key=lambda s: math.hypot(s.x - enemy.x, s.y - enemy.y),
                   default=self.objective)

    def update(self, enemies, enemy_projectiles, dt):
        """Apply enemy contact/ranged pressure and return unconsumed shots.

        Attack cooldowns cannot bank a burst while the game is paused. Enemies
        remain alive after striking, so camping does not erase incoming waves.
        """
        if not math.isfinite(dt) or dt < 0:
            raise ValueError('dt must be finite and non-negative')
        self.protocol_remaining = max(0.0, self.protocol_remaining - dt)
        for enemy in enemies:
            if enemy.is_dead():
                continue
            timer = max(0.0, getattr(enemy, '_defense_attack_timer', 0.0) - dt)
            target = self.target_for(enemy)
            distance = math.hypot(enemy.x - target.x, enemy.y - target.y)
            if distance <= (.8 if target is self.objective else .5) and timer <= 0 and dt > 0:
                amount = LargeNumber(enemy.damage)
                if target is self.objective:
                    target.take_damage(amount)
                else:
                    target.health = max(LargeNumber(0), target.health - amount)
                timer = 1.0
            enemy._defense_attack_timer = timer
        remaining = []
        for shot in enemy_projectiles:
            targets = [self.objective, *self.living_structures()]
            hit = self._first_hit(shot, targets)
            if hit is None:
                remaining.append(shot)
            elif isinstance(hit, DefenseObjective):
                hit.take_damage(LargeNumber(shot.damage))
            else:
                hit.health = max(LargeNumber(0), hit.health - LargeNumber(shot.damage))
        for structure in self.structures:
            if structure.health <= 0:
                structure.remaining = 0
        self.structures[:] = self.living_structures()
        return remaining

    @staticmethod
    def _first_hit(shot, targets):
        start_x = shot.previous_x if shot.previous_x is not None else shot.x
        start_y = shot.previous_y if shot.previous_y is not None else shot.y
        candidates = []
        for target in targets:
            if target.health <= 0:
                continue
            distance, fraction = _distance_to_segment(
                target.x, target.y, start_x, start_y, shot.x, shot.y)
            if distance <= getattr(target, 'radius', .4):
                candidates.append((fraction, target))
        return min(candidates, key=lambda entry: entry[0])[1] if candidates else None

    def process_repair_shots(self, shots):
        """Consume repairs on the first friendly building along a swept shot."""
        remaining = []
        for shot in shots:
            if not getattr(shot, 'friendly_repair', False):
                remaining.append(shot)
                continue
            target = self._first_hit(shot, [self.objective, *self.living_structures()])
            if target is None:
                remaining.append(shot)
                continue
            fraction = min(.08, max(0.0, shot.repair_fraction))
            amount = target.max_health * fraction * effect_multiplier(shot.healing_bonus_pct)
            if isinstance(target, DefenseObjective):
                target.repair(amount)
            else:
                target.health += min(target.max_health - target.health, amount)
        return remaining
