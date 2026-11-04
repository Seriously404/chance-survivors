"""Currency exchange and rarity gambling calculations, independent of the UI."""
from decimal import Decimal, ROUND_FLOOR
import math

from game.systems.bazaar import RARITY_ORDER
from game.systems.currency import CURRENCY_DEFINITIONS, CURRENCY_NAMES
from game.systems.inventory import RARITY_COMBINATION_SLOTS
from game.systems.numbers import LargeNumber


def currency_definition(name):
    canonical = CURRENCY_NAMES.get(str(name).casefold())
    return next((d for d in CURRENCY_DEFINITIONS.values() if d['name'] == canonical), None)


def currency_affinity(item, currency):
    """Explicit item affinities override sensible element/type defaults."""
    definition = currency_definition(currency)
    if not definition:
        raise ValueError('Unknown currency.')
    aliases = {definition['name'].casefold(), definition['id'].casefold()}
    favorable = {str(x).casefold()
                 for x in item.get('favorable_currencies', [])}
    unfavorable = {str(x).casefold()
                   for x in item.get('unfavorable_currencies', [])}
    if aliases & favorable:
        return 1.5
    if aliases & unfavorable:
        return 0.5
    element = str(item.get('stats', {}).get(
        'element', item.get('element', ''))).lower()
    affinities = {'fire': ('ember', 'holy_water'), 'frost': ('time_crystal', 'blood_orb'),
                  'shadow': ('dark_matter', 'holy_water'), 'light': ('holy_water', 'dark_matter'),
                  'nature': ('essence', 'dark_matter'), 'arcane': ('arcane_dust', 'iron_coin')}
    if element in affinities:
        positive, negative = affinities[element]
        if definition['id'] == positive:
            return 1.5
        if definition['id'] == negative:
            return 0.5
    defaults = {'weapon': ('iron_coin', 'mana_crystal'), 'armor': ('iron_coin', 'chaos_fragment'),
                'ability': ('mana_crystal', 'iron_coin'), 'relic': ('soul_fragment', 'copper')}
    positive, negative = defaults.get(item.get('type'), ('silver', 'copper'))
    return 1.5 if definition['id'] == positive else 0.5 if definition['id'] == negative else 1.0


def rarity_chance(item, target, pool, luck=0.0):
    if '~' in str(target):
        parts = str(target).split('~')
        if len(parts) not in (2, 3) or any(part not in RARITY_ORDER for part in parts[:2]) or RARITY_ORDER.index(parts[1]) != RARITY_ORDER.index(parts[0]) + 1:
            raise ValueError('Choose adjacent rarity targets.')
        try:
            upper_weight = float(parts[2]) / 100 if len(parts) == 3 else 0.5
        except ValueError as exc:
            raise ValueError('Invalid rarity distribution.') from exc
        if not math.isfinite(upper_weight) or not 0 <= upper_weight <= 1:
            raise ValueError('Invalid rarity distribution.')
        return (rarity_chance(item, parts[0], pool, luck) * (1 - upper_weight)
                + rarity_chance(item, parts[1], pool, luck) * upper_weight)
    current = str(item.get('rarity', 'common')).lower()
    target = str(target).lower()
    if current not in RARITY_ORDER or target not in RARITY_ORDER:
        raise ValueError('Unknown rarity.')
    steps = RARITY_ORDER.index(target) - RARITY_ORDER.index(current)
    if steps <= 0:
        raise ValueError('Choose a rarity above the current rarity.')
    luck = float(luck)
    if not math.isfinite(luck) or luck < 0:
        raise ValueError('Luck must be finite and non-negative.')
    # Use decimal arithmetic: a late-run wallet can exceed float's range.
    effective = Decimal(0)
    for name, amount in pool.items():
        definition = currency_definition(name)
        if not definition or type(amount) is not int or amount < 0:
            raise ValueError(
                'Currency pool amounts must be non-negative whole numbers.')
        effective += (Decimal(amount)
                      * Decimal(str(definition['value_multiplier']))
                      * Decimal(str(currency_affinity(item, name))))
    effective *= Decimal(str(1 + 0.1 * math.log1p(luck)))
    # Each skipped tier compounds the required investment by four.
    difficulty = Decimal(400 * (2 ** RARITY_ORDER.index(current))
                         * (4 ** (steps - 1)))
    return min(0.95, float(effective / (effective + difficulty))) if effective else 0.0


def gamble_rarity(item, target, pool, wallet, rng, *, elapsed_seconds=None, luck=None):
    selected = str(target).split('~')[:2]
    if 'ultimate' in selected and item.get('rarity') != 'mythical':
        raise ValueError('Reach mythical rarity before attempting ultimate.')
    if 'ultimate' in selected and luck is not None and luck < 20:
        raise ValueError('Ultimate upgrades require at least 20 luck.')
    chance = rarity_chance(item, target, pool, 0 if luck is None else luck)
    if chance <= 0:
        raise ValueError('Add currency to the pool first.')
    for currency, amount in pool.items():
        if wallet.get(currency) < amount:
            raise ValueError(f'Not enough {currency} for the pool.')
    for currency, amount in pool.items():
        if amount:
            wallet.spend(currency, LargeNumber(amount))
    success = rng.random() < chance
    if success:
        item.setdefault('base_rarity', item.get('rarity', 'common'))
        if '~' in target:
            parts = target.split('~')
            lower, upper = parts[:2]
            upper_weight = float(parts[2]) / 100 if len(parts) == 3 else 0.5
            target = lower if rng.random() < 1 - upper_weight else upper
        item['rarity'] = target
        if target == 'ultimate':
            item['ultimate_tier'] = 1
        combinations = item.get('combinations', [])
        count = RARITY_COMBINATION_SLOTS[target]
        item['combinations'] = combinations[:count] + \
            [None] * max(0, count - len(combinations))
    return success


def exchange_quote(source, destination, amount):
    src, dst = currency_definition(source), currency_definition(destination)
    if not src or not dst or src['id'] == dst['id']:
        raise ValueError('Choose two different currencies.')
    if type(amount) is not int or amount <= 0:
        raise ValueError('Exchange amount must be a positive whole number.')
    # Buying more valuable currency incurs a 20% fee; otherwise 10%.
    fee_factor = Decimal(
        '0.8') if src['value_multiplier'] < dst['value_multiplier'] else Decimal('0.9')
    result = (Decimal(amount) * Decimal(str(src['value_multiplier'])) * fee_factor / Decimal(
        str(dst['value_multiplier']))).to_integral_value(rounding=ROUND_FLOOR)
    return int(result)


def exchange_currency(wallet, source, destination, amount):
    received = exchange_quote(source, destination, amount)
    if received < 1:
        raise ValueError('Add more currency to receive at least one unit.')
    if wallet.get(source) < amount:
        raise ValueError(f'Not enough {source} to exchange.')
    wallet.spend(source, LargeNumber(amount))
    wallet.add(destination, LargeNumber(received))
    return received
