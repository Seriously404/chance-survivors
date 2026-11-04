"""Headless checks of gameplay and menu failure paths."""
from game.utils.large_number import LargeNumber
from client.render import Renderer
import pygame
import os
import unittest
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')


class UIRegressionTests(unittest.TestCase):
    def setUp(self):
        self.renderer = Renderer(800, 450, 200)
        self.renderer.mode = 'PLAYING'
        self.renderer.panel = 'upgrades'
        self.renderer.menu_tab = 'upgrades'
        self.renderer.upgrade_tab = 'combination'

    def test_name_input_is_confined_to_focused_menu_field(self):
        r = self.renderer
        r.set_view('MENU')
        r.draw_menu()
        pygame.event.clear()
        for char, key in [('w', pygame.K_w), ('q', pygame.K_q), ('u', pygame.K_u)]:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
            pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=char))
            pygame.event.post(pygame.event.Event(pygame.KEYUP, key=key))
        _, _, actions = r.process_events()
        self.assertEqual(r.get_player_name(), 'wqu')
        self.assertNotIn('open_settings', actions)
        self.assertNotIn('upload_run', actions)
        self.assertEqual(r.get_movement(), (0, 0))
        r.set_view('PLAYING')
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text='w'))
        pygame.event.post(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_BACKSPACE))
        r.process_events()
        self.assertEqual(r.get_player_name(), 'wqu')
        self.assertEqual(r.get_movement(), (0, 1))
        r.set_view('GAME_OVER')
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text='a'))
        pygame.event.post(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_BACKSPACE))
        r.process_events()
        self.assertEqual(r.get_player_name(), 'wqu')
        r.set_view('MENU')
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(5, 5)))
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text='x'))
        r.process_events()
        self.assertEqual(r.get_player_name(), 'wqu')
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=r._name_entry.center))
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text='x'))
        r.process_events()
        self.assertEqual(r.get_player_name(), 'wqux')

    def test_released_key_after_state_change_does_not_move_player(self):
        r = self.renderer
        r.set_view('PLAYING')
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
        r.process_events()
        r.set_view('GAME_OVER')
        r.set_view('PLAYING')
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_w))
        r.process_events()
        self.assertEqual(r.get_movement(), (0, 0))

    def test_drag_item_onto_itself_does_not_crash(self):
        r = self.renderer
        item = {'id': 'rifle', 'name': 'Rifle', 'type': 'weapon',
                'rarity': 'common', 'level': 1, 'stats': {}, 'combinations': [None]}
        r._last_state = {'items': [item], 'active_slots': {}}
        r._item_rects = {'rifle': pygame.Rect(10, 10, 30, 30)}
        r._drop_targets = {'combo:rifle:0': pygame.Rect(100, 100, 30, 30)}
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(15, 15)))
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(
            110, 110), rel=(95, 95), buttons=(1, 0, 0)))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=(110, 110)))
        _, _, actions = r.process_events()
        # game logic rejects it safely
        self.assertIn('combine:rifle:0:rifle', actions)

    def test_menu_notifications_render(self):
        r = self.renderer
        r.draw({'items': [], 'notifications': [
               {'text': 'Not enough Gold', 'remaining': 3}]})

    def test_damage_does_not_invoke_debug_overlay(self):
        r = self.renderer
        r.panel = None
        r.draw_debug = lambda state: self.fail(
            'debug overlay should be removed')
        from game.entities.player import Player
        player = Player()
        player.health = LargeNumber(85)
        r.draw({'player': player, 'bullets': [], 'enemies': [],
               'enemy_types': {}, 'currency': {}})

    def test_summon_is_visible_in_gameplay(self):
        from game.entities.player import Player
        from game.ability_scripts.effects import Summon
        r = self.renderer
        r.panel = None
        player = Player()
        ally = Summon(player.x + 1, player.y, 10, 15, 'radiant', True)
        with patch('client.render.pygame.draw.circle', wraps=pygame.draw.circle) as circles:
            r.draw({'player': player, 'bullets': [], 'enemies': [], 'enemy_types': {},
                    'currency': {}, 'summons': [ally]})
        self.assertTrue(any(call.args[1] == (100, 220, 255)
                        for call in circles.call_args_list))

    def test_camera_follows_teleport_smoothly_and_aims_from_player(self):
        from game.entities.player import Player
        r = self.renderer
        r.panel = None
        player = Player()
        state = {'player': player, 'bullets': [],
                 'enemies': [], 'enemy_types': {}, 'currency': {}}
        r.draw(state)
        player.x = 2
        r.draw(state)
        self.assertGreater(r._camera[0], 0)
        self.assertLess(r._camera[0], 2)
        screen_pos = r.world_to_screen(player.x, player.y, *r._camera)
        self.assertAlmostEqual(r.aim_angle(
            (screen_pos[0]+10, screen_pos[1]), player.x, player.y), 0)

    def test_damage_feedback_appears_and_expires(self):
        from game.entities.enemy import Enemy
        r = self.renderer
        enemy = Enemy('basic', health=10, max_health=10)
        r._draw_damage_feedback([enemy], 0, 0)
        self.assertEqual(r._damage_feedback, [])
        enemy.health = 6
        r._draw_damage_feedback([enemy], 0, 0)
        self.assertEqual(len(r._damage_feedback), 1)
        self.assertEqual(r._damage_feedback[0]['amount'], LargeNumber(4))
        r._frame_dt = 1.0
        r._draw_damage_feedback([enemy], 0, 0)
        self.assertEqual(r._damage_feedback, [])

    def test_aim_telegraph_uses_combined_nova_radius(self):
        from game.systems.inventory import _item
        r = self.renderer
        base = _item('nova', 'Nova', 'ability', 'common', 1,
                     {'script': 'nova', 'cast_radius': .5})
        supplement = _item('blast', 'Blast', 'ability', 'common', 1,
                           {'area_radius': 1.5})
        base['combinations'] = ['blast']
        r.input_handler.held_abilities.add(pygame.K_1)
        with patch('client.render.pygame.draw.circle', wraps=pygame.draw.circle) as circles:
            r._draw_ability_aim({'items': [base, supplement],
                                 'active_slots': {'abilities': ['nova']}}, (400, 225))
        self.assertEqual(circles.call_args.args[3], 300)

    def test_new_run_equips_basic_fireball(self):
        from game.systems.items import create_initial_inventory
        inventory = create_initial_inventory()
        self.assertEqual(
            inventory.active_slots['abilities'][0], 'starter-fire-rune')
        self.assertEqual(inventory.get('starter-fire-rune')
                         ['stats']['script'], 'projectile')

    def test_codex_renders_items_fusions_and_crates(self):
        r = self.renderer
        r.set_view('MENU')
        r.draw_menu()
        self.assertIn('codex', r._buttons)
        catalog = [{'id': 'a', 'name': 'Item', 'type': 'ability',
                    'rarity': 'common', 'description': 'A test ability'}]
        recipes = [{'name': 'Fusion', 'description': 'Combine parts',
                    'required_types': ['weapon', 'armor']}]
        crates = [{'name': 'Box', 'description': 'A box',
                   'costs': {'Copper': 10}, 'rewards': [('Item', 1.0)]}]
        for tab in ('guide', 'items', 'fusions', 'crates'):
            r.codex_tab = tab
            r.codex_selected = 0
            r.draw_codex(catalog, recipes, crates)
            self.assertIn('back', r._buttons)

    def test_exchange_drag_and_slider(self):
        from game.systems.numbers import LargeNumber as Money
        r = self.renderer
        r.panel = r.menu_tab = 'bazaar'
        r._bazaar_tab = 'exchange'
        r.draw({'items': [], 'bazaar': {'wallet': {
               'Copper': Money(100), 'Silver': Money(0), 'Gold': Money(0)}}})
        start = r._currency_drag_rects['Gold'].center
        end = r._exchange_slots['destination'].center
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=start))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEMOTION, pos=end, rel=(0, 0), buttons=(1, 0, 0)))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=end))
        r.process_events()
        self.assertEqual(r._exchange_destination, 2)
        slider = r._sliders['exchange']
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=slider.midright))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=slider.midright))
        r.process_events()
        self.assertEqual(r._exchange_amount, 100)

    def test_rarity_slider_selects_a_halfway_target(self):
        from game.systems.numbers import LargeNumber as Money
        r = self.renderer
        r.panel = r.menu_tab = 'bazaar'
        r._bazaar_tab = 'rarity_upgrader'
        item = {'id': 'rifle', 'name': 'Rifle', 'type': 'weapon',
                'rarity': 'common', 'level': 1, 'stats': {}, 'combinations': []}
        r.selected_item_id = 'rifle'
        r.draw({'items': [item], 'bazaar': {'wallet': {'Copper': Money(100)}}})
        slider = r._sliders['target']
        halfway = (slider.left + round(slider.width / (2 * (len(__import__('game.systems.bazaar',
                   fromlist=['RARITY_ORDER']).RARITY_ORDER) - 2))), slider.centery)
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=halfway))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=halfway))
        r.process_events()
        self.assertAlmostEqual(r._rarity_target, 0.5, delta=0.03)

    def test_wheel_routes_to_hovered_crate_panel_and_interpolates(self):
        r = self.renderer
        r.panel = r.menu_tab = 'bazaar'
        r._bazaar_tab = 'crates'
        crates = [{'id': str(i), 'name': f'Crate {i}', 'cost': 1, 'rewards': [
            'Rifle'] * 20} for i in range(15)]
        state = {'items': [], 'bazaar': {'wallet': {}, 'crates': crates}}
        r.draw(state)
        left = r._scroll_regions['bazaar_crates_scroll_target']
        right = r._scroll_regions['bazaar_rewards_scroll']
        with patch('pygame.mouse.get_pos', return_value=left.center):
            pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, x=0))
            r.process_events()
        self.assertEqual(r.bazaar_crates_scroll_target, 1)
        self.assertEqual(getattr(r, 'bazaar_rewards_scroll', 0), 0)
        self.assertEqual(r.inventory_scroll_target, 0)
        r.draw(state)
        self.assertGreater(
            r._scroll_positions['bazaar_crates_scroll_target'], 0)
        self.assertLess(r._scroll_positions['bazaar_crates_scroll_target'], 1)
        with patch('pygame.mouse.get_pos', return_value=right.center):
            pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, x=0))
            r.process_events()
        self.assertEqual(r.bazaar_rewards_scroll, 1)
        self.assertEqual(r.bazaar_crates_scroll_target, 1)

    def test_wheel_over_inventory_does_not_scroll_fusion_codex(self):
        r = self.renderer
        r.panel = r.menu_tab = 'bazaar'
        r._bazaar_tab = 'fusion'
        r.fusion_codex = True
        state = {'items': [], 'bazaar': {}, 'fusion_recipes': []}
        r.draw(state)
        with patch('pygame.mouse.get_pos', return_value=r._scroll_regions['inventory'].center):
            pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, x=0))
            r.process_events()
        self.assertEqual(r.inventory_scroll_target, 2)
        self.assertEqual(r.fusion_catalog_scroll, 0)

    def test_quest_wheel_only_moves_hovered_column(self):
        r = self.renderer
        r.panel = r.menu_tab = 'quests'
        quests = [{'id': f'{kind}{i}', 'name': f'{kind}{i}', 'type': kind,
                   'status': 'available', 'description': ''}
                  for kind in ('main', 'side') for i in range(10)]
        state = {'items': [], 'quests': quests}
        r.draw(state)
        with patch('pygame.mouse.get_pos', return_value=r._scroll_regions['quest:side'].center):
            pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, x=0))
            r.process_events()
        r.draw(state)
        self.assertEqual(r.quest_offsets['main'], 0)
        self.assertEqual(r.quest_offsets['side'], 1)
        self.assertGreater(r.quest_scroll_positions['side'], 0)
        self.assertLess(r.quest_scroll_positions['side'], 1)
