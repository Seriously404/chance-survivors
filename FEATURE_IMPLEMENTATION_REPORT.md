# Feature Implementation Report

## 1. Features implemented

- Added a name-entry menu with Play, Exit, and Settings actions. Starting with an empty name displays feedback.
- Added settings for 800×450, 1280×720, 1600×900, and 1920×1080, plus windowed/fullscreen selection and Apply/Back actions. Windowed mode is resizable, and UI anchors are recalculated from the current window dimensions.
- Added shared in-game navigation for Inventory, Quests, Upgrades, and Bazaar, including while paused.
- Added a 200-slot adaptive inventory grid, eleven starter/test items, item details, active armor/weapon/ability slots, rarity-colored square icons, rarity-based combination slot icons, and drag-and-drop equipment/combination assignment. Supplement items cannot be equipped; armor cannot be used as a supplement. Active slots are reflected in the gameplay HUD.
- Replaced the UI-only sample gear with a starter catalog: equipped armor applies defense, health, and movement bonuses; passive misc items apply luck, health, speed, and damage bonuses; weapon items configure projectiles and cooldowns. Left click fires weapon slot 1 and right click fires slot 2.
- Added a Bazaar test spawner for catalog items. The pure game-side item catalog, stat aggregation, and weapon-to-projectile adapter are separate modules so new content can be added without placing balance data in the renderer.
- Updated the menu chrome to neutral grayscale, aligned the shared menu tabs to the top edge, and placed the upgrades sub-navigation immediately below them. Added item-to-slot connector lines and a cursor-following drag preview.
- Distinguished clicks from drags with an 8-pixel movement threshold: a click selects an item, while a drag preview and drop action start only after deliberate movement. Inventory wheel scrolling eases toward the target row. Armor and weapon loadout slots are larger squares.
- Added Quests and Bazaar placeholder screens and an Upgrades screen with Overview and Combination categories. Overview displays level/EXP, player stats, currencies, and active gear/abilities.
- Added an EXP progression model backed by 50 integer requirements totaling `10^200` in `assets/level_upgrade_req.json`. Enemy kills award 1 EXP and overflow carries to subsequent levels; the final requirement advances level 50 to level 51.
- Kept score independent of XP: each enemy kill adds 10 score and 1 EXP. Score is an unbounded Python integer and keeps increasing after level 51; XP stops at the level cap. `mission_score_bonus_pct` defaults to 0%.
- Added a top-center stack of timed currency notifications and Copper/Gold totals.
- Added per-slot weapon and ability cooldown indicators; abilities are still data/UI placeholders pending their individual activation implementations.
- Added rapid-fire and heavy-shot configuration and firing behavior. Tab cycles between the configured types. Rapid fire repeats while the mouse button is held; heavy shots require another press. Heavy shots pierce multiple targets.
- Added a reward on enemy death and score increment. Reward handling runs after collision resolution, when the collision system reports killed enemies.

## 2. Files created and modified

Created:

- `assets/bullet_types.json`
- `game/systems/bullets.py`
- `game/systems/currency.py`
- `game/systems/inventory.py`
- `game/systems/progression.py`
- `assets/level_upgrade_req.json`
- `FEATURE_IMPLEMENTATION_REPORT.md`

Modified:

- `client/input.py`
- `client/render.py`
- `game/config/settings.py`
- `game/entities/projectile.py`
- `game/main.py`
- `game/systems/collision.py`
- `client/input.py` (inventory drag-and-drop)
- `game/main.py` (menu navigation, inventory and EXP integration)
- `client/render.py` (inventory, upgrade, quest, and Bazaar menus)
- `game/systems/items.py` (starter catalog and player stat aggregation)
- `game/systems/weapons.py` (weapon item to projectile adapter)
- `game/systems/runtime_probe.py` and `scripts/runtime_probe.py` (JSON runtime control surface)

## 3. Bullet configuration

`assets/bullet_types.json` is loaded at startup by `load_bullet_types()`. Each entry provides `cooldown` in seconds, positive integer `damage`, positive `speed_modifier`, non-negative integer `piercing`, and boolean `automatic`. Invalid or missing files raise a `RuntimeError` naming the configuration path and the validation/read error. A projectile stores its selected type name and its damage/piercing values, so collision handling does not depend on the renderer.

Add a new JSON object entry with those five fields to add another type. The current selector cycles over loaded types in JSON insertion order.

## 4. Currency rewards and notifications

`CurrencyWallet.reward_for_kill()` awards 3–7 Copper by default, or 1 Gold with an 8% probability. `CollisionSystem` records each enemy that transitions to dead while processing collisions; the main loop awards a reward for each recorded kill once, then the dead enemy is removed. `CurrencyNotifications` stores text and remaining lifetime. The game loop reduces lifetimes using delta time, removes expired entries, and the renderer places the remaining list consecutively with alpha based on remaining lifetime.

Add currencies by extending the wallet's initial amounts and reward selection. Notifications already accept arbitrary currency names and amounts.

## 5. Items, weapons, and runtime probe

Starter and Bazaar items are defined by `create_item_catalog()` in `game/systems/items.py`. Add a catalog record there with an item type and stat dictionary. Armor bonuses are aggregated from active armor; misc bonuses are passive while owned. Weapon records use `bullet_type`, `damage`, `cooldown`, `speed_modifier`, and `piercing`; `game/systems/weapons.py` applies these to the validated projectile definition. Equipped weapon slot 1 fires on left click and slot 2 on right click. Ability activation effects are intentionally not implemented because each ability will need its own behavior; active ability slots show readiness/cooldown state.

Run `python -m game.systems.runtime_probe` for an integration scenario. For interactive inspection and control, run `python -m game.systems.runtime_probe --interactive` and send one JSON object per line, for example `{"action":"spawn_enemy","health":3}`, `{"action":"fire","slot":0}`, `{"action":"step","dt":0.02}`, `{"action":"move_player","dx":1,"dt":0.1}`, or `{"action":"status"}`. The probe exercises the actual inventory, projectile, collision, reward, and progression modules without requiring a display. It reports runtime exceptions as JSON and supports `assert_invariants`.

## 6. Tests and checks performed

- Python bytecode compilation of `game/` and `client/`: passed.
- Direct system check: loaded both bullet types and checked automatic/piercing configuration, updated a wallet from one reward, displayed two simultaneous notifications, and verified notification expiry: passed.
- Direct UI/data check using SDL's dummy video driver: rendered Inventory, Upgrades/Overview, Upgrades/Combination, Quests, and Bazaar; simulated drag-to-equip, drag-to-combination, and drag-to-remove-combination actions: passed.
- XP check: confirmed 50 positive integer requirements sum to `10^200`, XP overflow advances through multiple levels, and the final requirement advances from level 50 to level 51: passed.
- Dummy SDL launch (`python -m game.main`) under a 3-second timeout: initialized without startup errors and remained running until timeout.
- Latest UI changes: Python compilation passed; SDL dummy rendering passed at 800×450 and 1920×1080 for Inventory and Combination views. `pytest` could not run because pytest is not installed in the project environment.
- Current milestone: runtime probe scenario fired both configured weapon types, killed an enemy through the collision system, awarded score/currency/EXP once, and passed inventory/projectile invariants. SDL dummy interaction checks verified selecting a combination base on click, attaching a supplement by drag without changing that base, and activating a Bazaar spawn icon. Python compilation passed.
- Not manually verified: desktop mouse navigation, fullscreen/display behavior, visual layout at all supported resolutions, or a complete live gameplay session with enemy kills and rewards.

## 7. Known limitations and recommended next steps

- The bullet selector is currently the Tab key; a future loadout UI can replace it without changing projectile data or collision rules.
- Total score is integer-truncated after applying the configurable percentage. There is no mission system, by design.
- Quest and Bazaar content remains placeholder content.
- Combination assignments update inventory relationships and visuals but do not change item stats or gameplay behavior.
- Ability effects and ability activation inputs remain unimplemented; current ability slots display ready state and are prepared for cooldown data.
- Inventory, active equipment, combinations, and progression are in-memory only and reset when the game process exits.
- Score has no finite in-game completion target yet; it remains unbounded and progresses independently after XP reaches its cap.
- Player luck and speed in the Overview are placeholder values; active gear does not affect player stats yet.
- Add automated tests for menu transitions, inventory assignment and invalid drops, progression boundaries, collision reward uniqueness, and desktop display transitions.
