"""Combat-ready contract loans, isolated from normal market and crate loot."""

from copy import deepcopy

from game.systems.game_definitions import load_json_asset
from game.systems.inventory import _item
from game.systems.items import effective_ability, item_stat


def role_value(item, role):
    """Compare a role's real scaled throughput instead of its script name."""
    script = item.get('stats', {}).get('script')
    cooldown = max(.05, item_stat(item, 'cooldown', 8))
    if role == 'primary' and script in {'projectile', 'ember', 'frost'}:
        return item_stat(item, 'cast_damage', 0) / cooldown
    if role == 'area' and script in {'nova', 'void', 'siphon'}:
        radius = max(item_stat(item, 'cast_radius', .5), item_stat(item, 'area_radius', 0))
        return item_stat(item, 'cast_damage', 0) * radius ** 2 / cooldown
    if role == 'healing' and script in {'heal', 'mend_ward'}:
        return item_stat(item, 'heal_amount', 0) / cooldown
    if ((role == 'mobile_sentry' and script == 'sentinel')
            or (role == 'fixed_turret' and script == 'turret')):
        return (item_stat(item, 'summon_damage', 0)
                * min(1., item_stat(item, 'summon_duration', 0) / cooldown))
    return 0.


def contract_starter_items(mode, inventory):
    """Return only roles the active build cannot already perform adequately."""
    definitions = load_json_asset('quest_starters.json')
    identities = definitions['packages'].get(mode)
    if identities is None:
        return None
    active = [effective_ability(inventory, inventory.get(identity))
              for identity in inventory.active_slots['abilities'] if identity]
    by_id = {definition['id']: definition for definition in definitions['items']}
    result = []
    for identity in identities:
        definition = by_id[identity]
        item = _item(identity, definition['name'], 'ability', 'common', 1,
                     deepcopy(definition['stats']))
        role = definition['role']
        item['contract_role'] = role
        item['description'] = definition['description']
        item['tags'] = list(definition.get('tags', []))
        if any(role_value(existing, role) >= role_value(item, role) for existing in active):
            continue
        result.append(item)
    return result


def displaced_contract_abilities(inventory, grants):
    """Identify weaker active replacements while retaining them in inventory."""
    displaced = []
    for identity in inventory.active_slots['abilities']:
        if not identity:
            continue
        item = effective_ability(inventory, inventory.get(identity))
        if any(0 < role_value(item, grant.get('contract_role'))
               < role_value(grant, grant.get('contract_role')) for grant in grants):
            displaced.append(identity)
    return displaced
