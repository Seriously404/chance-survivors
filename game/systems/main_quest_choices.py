"""Persistent main-quest offers and safe, transactional build transitions."""

from copy import deepcopy
import math
import random

from game.systems.inventory import Inventory, RARITY_COMBINATION_SLOTS


POWER_MIN = 1.05
POWER_MAX = 2.0
ENGINEER_ID = 'main-engineer'


def quest_challenge_modifiers(power):
    """Shared slider preview and runtime challenge multipliers."""
    if isinstance(power, bool) or not isinstance(power, (int, float)):
        raise ValueError('Choose a finite score power.')
    if not math.isfinite(power) or not 1 <= power <= POWER_MAX:
        raise ValueError('Invalid quest score power.')
    intensity = float(power) - 1
    return {'health': 1 + intensity * 3,
            'damage': 1 + intensity * 1.5,
            'spawn': 1 + intensity}


def _components(items):
    """Return whole combination groups; a base cannot itself be a supplement."""
    by_id = {item['id']: item for item in items}
    supplements = {
        sid for item in items for sid in item['combinations'] if sid}
    return [[item, *(by_id[sid] for sid in item['combinations'] if sid)]
            for item in items if item['id'] not in supplements]


class MainQuestChoices:
    """QuestManager mixin; rendering and pausing remain in the client/main loop."""

    def _init_main_choices(self, rng=None):
        self.main_offer_seed = (rng or random.SystemRandom()).getrandbits(63)
        self.main_offer_ids = []
        self.main_reroll_used = False
        self.quest_storage = []

    @property
    def pending_main_choice(self):
        engineer = next((bp for bp in self.blueprints
                         if bp['id'] == ENGINEER_ID), None)
        return bool(engineer and self.level >= int(engineer['unlock_level'])
                    and self.main_quest is None and not self.main_quest_declined)

    def _ensure_main_offers(self):
        if not self.pending_main_choice or self.main_offer_ids:
            return
        alternatives = [bp['id'] for bp in self.blueprints
                        if bp['quest_type'] == 'main' and bp['id'] != ENGINEER_ID
                        and int(bp['unlock_level']) <= self.level]
        rng = random.Random(self.main_offer_seed)
        self.main_offer_ids = [
            ENGINEER_ID, *rng.sample(alternatives, min(2, len(alternatives)))]

    def reroll_main_offers(self):
        if not self.pending_main_choice or self.main_reroll_used:
            return False
        self._ensure_main_offers()
        alternatives = [bp['id'] for bp in self.blueprints
                        if bp['quest_type'] == 'main'
                        and bp['id'] not in self.main_offer_ids
                        and int(bp['unlock_level']) <= self.level]
        if len(alternatives) < 2:
            return False
        rng = random.Random(self.main_offer_seed + 1)
        self.main_offer_ids = [ENGINEER_ID, *rng.sample(alternatives, 2)]
        self.main_reroll_used = True
        return True

    def main_choice_state(self):
        self._ensure_main_offers()
        by_id = {bp['id']: bp for bp in self.blueprints}
        offers = []
        for quest_id in self.main_offer_ids:
            quest = self._build_quest(by_id[quest_id])
            selectable = quest_id != ENGINEER_ID
            offers.append({**quest.to_state(), 'power_selectable': selectable,
                           'power_min': POWER_MIN, 'power_max': POWER_MAX,
                           'default_power': quest.reward_power,
                           'challenge_preview': self._power_modifiers(quest.reward_power)
                           if selectable else {'health': 1., 'damage': 1., 'spawn': 1.}})
        return {'pending': self.pending_main_choice, 'offers': offers,
                'rerolls_remaining': int(not self.main_reroll_used),
                'stored_item_count': len(self.quest_storage),
                'stored_item_names': [item.get('name', 'Item') for item in self.quest_storage]}

    @staticmethod
    def _power_modifiers(power):
        return quest_challenge_modifiers(power)

    def challenge_modifiers(self):
        quest = self.main_quest
        if quest is None or quest.failed or quest.restriction_mode == 'engineer':
            return {'health': 1., 'damage': 1., 'spawn': 1.}
        return self._power_modifiers(quest.reward_power)

    def choose_main_quest(self, quest_id, inventory, *, score_power=None,
                          starter_items=None):
        """Commit a visible offer and a usable build, or change nothing on error.

        Full inventories safely reserve complete unequipped combination groups;
        they return automatically when a group fits in the ordinary inventory.
        """
        self._ensure_main_offers()
        if not self.pending_main_choice or quest_id not in self.main_offer_ids:
            raise ValueError('Choose one of the current main quest offers.')
        staged = deepcopy(self)
        gear = deepcopy(inventory)
        blueprint = next(
            bp for bp in staged.blueprints if bp['id'] == quest_id)
        quest = staged._build_quest(blueprint)
        power = quest.reward_power if score_power is None else score_power
        if isinstance(power, bool) or not isinstance(
                power, (int, float)) or not math.isfinite(power):
            raise ValueError('Choose a finite score power.')
        if quest_id == ENGINEER_ID:
            if float(power) != quest.reward_power:
                raise ValueError('The Engineer has a fixed score power.')
        elif not POWER_MIN <= power <= POWER_MAX:
            raise ValueError('Choose a score power from 1.05 to 2.0.')
        quest.reward_power = float(power)
        quest.lock_on_accept = True
        if quest.condition == 'level_reached':
            if staged.level >= 51:
                quest.condition, quest.target = 'kills_total', 200.
                quest.description = 'Defeat 200 enemies after accepting. ' + '; '.join(quest.restrictions)
            else:
                old_target = int(quest.target)
                quest.target = min(51., max(quest.target, staged.level + 3.))
                quest.description = quest.description.replace(
                    f'level {old_target}', f'level {int(quest.target)}', 1)
        staged.main_quest = quest
        unequipped = []
        for category, slots in gear.active_slots.items():
            for index, item_id in enumerate(slots[:]):
                if item_id and not staged.can_activate(
                        gear.get(item_id), gear):
                    gear.unequip(category, index)
                    unequipped.append(item_id)
        grants = staged._starter_loadout(
            gear) if starter_items is None else deepcopy(starter_items)
        from game.systems.quest_loadouts import displaced_contract_abilities
        replacements = set(displaced_contract_abilities(gear, grants))
        for index, item_id in enumerate(gear.active_slots['abilities'][:]):
            if item_id in replacements:
                gear.unequip('abilities', index)
                unequipped.append(item_id)
        for category, kind in (('weapons', 'weapon'),
                               ('abilities', 'ability')):
            needed = sum(item['type'] == kind for item in grants)
            slots = gear.active_slots[category]
            for index in reversed(range(len(slots))):
                if slots.count(None) >= needed:
                    break
                if slots[index] is not None:
                    unequipped.append(slots[index])
                    gear.unequip(category, index)
        stored_before = len(staged.quest_storage)
        staged._reserve_space(gear, len(grants))
        granted_ids = []
        for template in grants:
            item = deepcopy(template)
            identity = f'quest-{quest_id}-{item["id"]}'
            suffix = 0
            existing = {entry['id']
                        for entry in gear.items + staged.quest_storage}
            while identity in existing:
                suffix += 1
                identity = f'quest-{quest_id}-{template["id"]}-{suffix}'
            item['id'] = identity
            item['quest_grant'] = quest_id
            # Loaned starter gear cannot be converted into free currency.
            item['liquidation_basis_gold'] = '0'
            gear.add(item)
            granted_ids.append(identity)
            category = 'weapons' if item['type'] == 'weapon' else 'abilities'
            slots = gear.active_slots[category]
            index = next(
                (i for i, value in enumerate(slots) if value is None), None)
            if index is None:
                raise ValueError(
                    'No active slot is available for the quest starter.')
            gear.equip(identity, category, index)
        if not any(item_id for category in ('weapons', 'abilities')
                   for item_id in gear.active_slots[category]):
            raise ValueError(
                'The selected quest must leave a usable combat item.')
        staged.active_quests.append(quest)
        if quest.condition == 'level_reached':
            quest.progress = float(staged.level)
        inventory.__dict__.update(gear.__dict__)
        self.__dict__.update(staged.__dict__)
        return {'quest_id': quest_id, 'unequipped': unequipped,
                'granted': granted_ids, 'stored': len(staged.quest_storage) - stored_before}

    def _starter_loadout(self, inventory):
        from game.systems.items import create_item_catalog
        mode = self.main_quest.restriction_mode
        if mode == 'engineer':
            from game.systems.engineering import engineer_starter_items
            return engineer_starter_items()
        from game.systems.quest_loadouts import contract_starter_items
        contract = contract_starter_items(mode, inventory)
        if contract is not None:
            return contract
        catalog = {item['id']: item for item in create_item_catalog()}
        desired = {'sentry_only': ('sentinel-summon', 'turret-deploy'),
                   'ability_only': ('starter-fire-rune',),
                   'weapon_only': ('starter-rapid',),
                   'fire_only': ('starter-fire-rune',)}.get(mode, ())
        active = [inventory.get(item_id)
                  for slots in inventory.active_slots.values() for item_id in slots if item_id]
        if not desired and not any(
                item['type'] == 'weapon' or any(item.get('stats', {}).get(key, 0) > 0
                                                for key in ('cast_damage', 'summon_damage'))
                for item in active):
            desired = ('starter-fire-rune',)
        result = []
        for identity in desired:
            template = deepcopy(catalog[identity])
            if any(item.get('stats', {}).get('script') == template.get('stats', {}).get('script')
                   and item['type'] == template['type'] for item in active):
                continue
            template['rarity'] = 'common'
            template['base_rarity'] = 'common'
            template['level'] = 1
            template['combinations'] = [None] * \
                RARITY_COMBINATION_SLOTS['common']
            result.append(template)
        return result

    def _reserve_space(self, inventory, required):
        active = {item_id for slots in inventory.active_slots.values()
                  for item_id in slots if item_id}
        for group in _components(inventory.items):
            if len(inventory.items) + required <= inventory.CAPACITY:
                break
            ids = {item['id'] for item in group}
            if ids & active:
                continue
            self.quest_storage.extend(deepcopy(group))
            inventory.items = [
                item for item in inventory.items if item['id'] not in ids]
        if len(inventory.items) + required > inventory.CAPACITY:
            raise ValueError(
                'Not enough safe reserve space for the quest loadout.')
        inventory._refresh_statuses()

    def recover_stored_items(self, inventory):
        """Restore whole reserved combinations only when every item will fit."""
        restored = []
        for group in _components(self.quest_storage):
            if len(inventory.items) + len(group) > inventory.CAPACITY:
                continue
            staged_items = inventory.items + deepcopy(group)
            Inventory._validate_combination_records(staged_items)
            ids = {item['id'] for item in group}
            if len({item['id'] for item in staged_items}) != len(staged_items):
                raise ValueError('Reserved item duplicates an inventory item.')
            inventory.items = staged_items
            self.quest_storage = [
                item for item in self.quest_storage if item['id'] not in ids]
            restored.extend(ids)
        inventory._refresh_statuses()
        return restored

    def can_use_supplement(self, item):
        return bool(self.main_quest and self.main_quest.restriction_mode ==
                    'engineer') or self.can_equip(item)

    def can_activate(self, item, inventory):
        return self.can_equip(item) and all(
            self.can_use_supplement(inventory.get(sid))
            for sid in item.get('combinations', []) if sid)

    def register_defense_wave(self, completed_waves):
        if type(completed_waves) is not int or completed_waves < 0:
            raise ValueError('Completed waves must be a nonnegative integer.')
        for quest in self.active_quests[:]:
            if quest.condition == 'defense_waves':
                quest.progress = min(
                    quest.target, max(
                        quest.progress, completed_waves))
                self._advance_quest(quest)

    def _main_choice_save_state(self):
        self._ensure_main_offers()
        return {'main_offer_seed': self.main_offer_seed,
                'main_offer_ids': list(self.main_offer_ids),
                'main_reroll_used': self.main_reroll_used,
                'quest_storage': deepcopy(self.quest_storage)}

    def _restore_main_choices(self, state):
        seed = state.get('main_offer_seed', self.main_offer_seed)
        offers = state.get('main_offer_ids', [])
        rerolled = state.get('main_reroll_used', False)
        storage = state.get('quest_storage', [])
        if type(seed) is not int or seed < 0 or not isinstance(rerolled, bool):
            raise ValueError('Invalid main quest offer state.')
        eligible = {bp['id'] for bp in self.blueprints if bp['quest_type'] == 'main'
                    and int(bp['unlock_level']) <= self.level}
        if (not isinstance(offers, list) or any(not isinstance(identity, str) for identity in offers)
                or len(set(offers)) != len(offers)
                or (offers and (len(offers) != 3 or offers[0] != ENGINEER_ID
                                or not set(offers) <= eligible))):
            raise ValueError('Invalid saved main quest offers.')
        if not isinstance(storage, list):
            raise ValueError('Invalid quest reserve.')
        Inventory(deepcopy(storage))
        self.main_offer_seed = seed
        self.main_offer_ids = list(offers)
        self.main_reroll_used = rerolled
        self.quest_storage = deepcopy(storage)
        self._ensure_main_offers()
