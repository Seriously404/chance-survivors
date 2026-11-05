"""Gold liquidation quotes bounded by the value actually invested in an item.

Purchase budgets survive upgrades and fusion. Sale proceeds return at most
50% of that budget, or 75% with the maximum trader bonus. Fractional Gold keeps
cheap Copper purchases worth selling without rounding them up into free money.
Legacy and earned items retain their previous nominal resale value.
"""

import math

from game.systems.currency import CURRENCY_DEFINITIONS, CURRENCY_NAMES
from game.systems.inventory import RARITY_COMBINATION_SLOTS
from game.systems.numbers import LargeNumber


BASIS_KEY = 'liquidation_basis_gold'
MAX_TRADER_BONUS = 0.5


def nominal_sell_gold(item):
    """Retain the existing rarity/level quote for free or legacy equipment."""
    rarities = tuple(RARITY_COMBINATION_SLOTS)
    rarity = str(item.get('rarity', 'common')).lower()
    if rarity not in rarities:
        raise ValueError('Unsupported item rarity.')
    level = item.get('level', 1)
    if type(level) is not int or level < 1:
        raise ValueError('Item level must be a positive integer.')
    return LargeNumber(5 + rarities.index(rarity) * 10 + level * 4)


def paid_value_gold(costs):
    """Value every paid currency using the same multipliers as exchange."""
    gold_value = LargeNumber(CURRENCY_DEFINITIONS['gold']['value_multiplier'])
    total = LargeNumber(0)
    for currency, amount in costs.items():
        name = CURRENCY_NAMES.get(str(currency).casefold())
        definition = next((value for value in CURRENCY_DEFINITIONS.values()
                           if value['name'] == name), None)
        amount = LargeNumber(amount)
        if definition is None or amount < 0:
            raise ValueError('Invalid purchase currency or amount.')
        total += amount * definition['value_multiplier'] / gold_value
    return total


def liquidation_basis(item):
    if BASIS_KEY not in item:
        # Free and old items keep their old resale quote. Once they undergo an
        # investment or fusion, this baseline becomes an explicit finite
        # budget.
        return nominal_sell_gold(item) * 2
    basis = LargeNumber(item[BASIS_KEY])
    if basis < 0:
        raise ValueError('Invalid item liquidation budget.')
    return basis


def record_investment(item, costs):
    """Add paid upgrades to the existing budget without minting item value."""
    item[BASIS_KEY] = str(liquidation_basis(item) + paid_value_gold(costs))


def sell_quote(item, trader_bonus=0.0):
    bonus = float(trader_bonus)
    if not math.isfinite(bonus):
        raise ValueError('Trader bonus must be finite.')
    multiplier = 1 + max(0.0, min(MAX_TRADER_BONUS, bonus))
    return min(nominal_sell_gold(item),
               liquidation_basis(item) * .5) * multiplier
