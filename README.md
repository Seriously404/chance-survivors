# Chance Survivors

A luck-based roguelike where the goal is to reach infinity points and compete for the fastest time.

## Overview

**Chance Survivors** is a luck-based roguelike game where you try to reach approximately 1.797e308 points (infinity) and compete for the fastest time. The game loop involves defeating enemies, collecting points, and gambling them on new weapons, abilities, or upgrades to current items.

## Goal

Reach approximately 1.797e308 points (infinity) and achieve the fastest time.

The game marks the practical infinity milestone at the largest finite IEEE-754
double value (`1.7976931348623157e308`). Reaching it is a finite score milestone,
not actual infinity or a floating-point overflow; the run can continue, and both
the gameplay HUD and results screen explicitly identify the milestone.

## Game Loop

1. Defeat enemies to earn points
2. Collect points from kills and achievements
3. Gamble points on new weapons, abilities, or upgrades
4. Combine items to create powerful combinations
5. Fuse items to lock their stats and use them in further combinations
6. Repeat until death or victory

## Features

### Combinations

The player can add any ability or weapon on to any other ability or weapon to either increase the current stats, add new functionality, or completely rework how the base item works. The game provides many basic parts and elements, and you must create combinations of them to build out your toolkit.

### Fusion

Fusion unlocks at player level 50, marking the beginning of the endgame. Before then, the Fusion panel displays the unlock requirement and fusion actions are rejected by the game loop. Once unlocked, recipes require the listed source types, minimum rarity, and minimum level. Only unequipped items that are not already used in combinations can be consumed; invalid attempts leave the inventory unchanged and report why. Fused results have stable unique IDs, record their source items, preserve output-weapon behavior/tags, and are marked fusion-only so they cannot be mistaken for ordinary drops or shop entries.

### Gambling

Lots of it. Nearly everything relies on gambling, and the strongest combinations would come from fusing things together and hoping whether you get the wanted outcome.

### Luck System

The game has a luck stat for the player, and the luckier the player is, the higher the chance of an event is. An event has difficulties. For example, a common sniper would have a fairly low difficulty, meaning that even with something like a luck stat of 10, you can hit a crit every time, but a legendary or even ultimate rarity sniper requires millions of luck to guarantee any chance of ever getting crits. Luck also changes your chances from loot crates, buyables, and other things. The whole game is structured around managing luck and trying to get lucky.

### Rarities and Levels

Any item has two separate things: a level and a rarity. Levels add the configured per-level stat contribution before rarity is applied; the default contribution is 10% of the base stat per level, configurable through `assets/item_level_scaling.json`. Cooldown levels instead subtract 2% of the base cooldown per level, with a 0.05-second minimum, so leveling does not make abilities or weapons slower. Rarity multiplies the resulting stats.

Mythical items can upgrade into Ultimate 1, then continue through Ultimate 100. Ultimate-tier upgrades cost more at higher tiers, use the rarity upgrader's luck-based success and payment rules, and stop at Ultimate 100. Inventory and run saves preserve the tier; icons progress from deep blue-purple toward white.

Combat and passive item stats use the shared calculation pipeline: base stat, additive level contributions, then rarity scaling from `assets/rarity_scaling.json`. Higher rarity increases effects and damage while reducing cooldowns; Ultimate tiers apply an additional configurable multiplier per tier.

Equipping two or four pieces from the same armor set activates its data-defined passive bonuses; threshold bonuses stack. The Bulwark set rewards durable builds with defense and health, while Windrunner favors speed and luck. Set pieces have dedicated boots, pants, chestplate, headpiece, or accessory slots and remain available through the Bazaar; equipped progress and bonuses are shown in the inventory equipment panel.

### Modifiers

Modifiers are special items that aren't used in combat, but rather are put in combinations to enhance the existing item. Examples include items that increase stats by ^1.05. A power in the equation is very powerful.

### Enemy Types

Enemies are different and have all kinds of resistances and types. This is to get the player to create actual element-based loadouts instead of just trying to make a super powerful gun that one-shots everything.

The live spawner retains the original enemy roster and now includes asset-defined fast, tank, shooter, swarm, stealth, boss, and six elemental enemy variants. Elemental variants use their configured resistances and currency/XP drops in combat and have distinct colors; bosses spawn much less often than common enemies. Swarm spawns create three nearby enemies, each scaled and rewarded individually. Necromancers summon up to three minions every six seconds; minions are excluded from normal spawning and award no score, currency, XP, or quest kills. Shooters fire visible, cooldown-based projectiles within their configured range; shots use swept collision checks and player defense.

Stealth enemies fade from 35% opacity at a distance to fully visible within 0.8 world units. This changes presentation only: stealth enemies remain targetable and continue to collide normally.

Enemy kill payouts are loaded from `assets/enemies.json`: each live enemy type maps to a configured currency amount and XP reward. Currency balances support the full currency catalog, and player luck can produce a bonus amount using each currency's drop-rate modifier.

### Bazaar and Content Expansion

The in-run Bazaar lets you buy luck-influenced crates or priced catalog items, upgrade owned-item rarity and levels, and sell un-equipped items. Higher-tier crates unlock as active run time advances; the offers rotate every five active minutes, and once per rotation the player can manually refresh the offers after alternatives have unlocked. The run seed and manual refresh state survive saves/resumes. Costs and sell values are shown in the Bazaar; wheel scrolling exposes the full market and inventory. Transactions validate Gold and inventory capacity before charging, and failed actions display feedback. Seeded runs support reproducible crate and rarity rolls in tests.

### Missions

Quest progress is shown in the gameplay HUD and the Quests panel, including progress bars and earned score bonuses. Main-quest restrictions can be locked from that panel; for the no-sniper quest, locking prevents equipping or combining sniper-tagged items and cannot be enabled while one is already equipped. The lock state is included in run saves.

### Scaling

New enemies scale with active run time and the player's threat tier. Their health and reward multiplier follow a 5%-per-active-minute and 25%-per-threat-tier curve; score, configured currency drops, and XP all use that multiplier. Damage and movement rise more gradually, while spawn intervals shorten with time and threat. The in-game `+` and `-` controls adjust threat from 0 to 20. Time in menus and while paused does not advance this scaling or the run timer.

### Active Abilities

Equipped abilities can be cast with their matching number key (1–9, then 0 for slot 10). Current effects include aimed elemental projectiles, close-range elemental novas, and healing; cooldowns are shown on the ability bar. Abilities are configured per item through cast type and effect stats.

### Run Uploads

When a run ends, the results screen offers an optional leaderboard upload. Nothing is submitted unless you choose **Upload Score**. The client sends the final score, active run time, level, luck, inventory, active equipment, and build stats to the API at `CHANCE_SURVIVORS_LEADERBOARD_URL` (default `http://127.0.0.1:8000`). Upload failures are shown on the results screen and can be retried.

### Run Saves

Active runs are atomically autosaved every 15 seconds and when leaving a run for the menu or closing the game. Choose **Resume Run** from the main menu to continue the saved run; transient enemies, projectiles, and cooldowns restart cleanly, while score, active gameplay time, player health, progression, inventory/equipment, currencies, quests, threat, and item IDs are preserved. Starting a new run replaces the previous save, and completed runs are removed from the resume slot. The versioned save defaults to `data/run_save.json`; set `CHANCE_SURVIVORS_RUN_SAVE` to use another path.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Game

```bash
python game/main.py
```

## Leaderboard API

The project includes a FastAPI + Uvicorn leaderboard server for persistent run submissions.

```bash
export CHANCE_SURVIVORS_ADMIN_TOKEN="replace-me-with-a-secret-token"
python -m game.leaderboard_api
```

Then open `http://localhost:8000/` to view the leaderboard. The page includes a ranked table, a per-entry detail panel, and a button to clear the database after supplying the admin token.

## Controls

- **W, A, S, D** — Move the player
- **Mouse Click** — Shoot
- **1–9, 0** — Cast ability slots 1–10
- **Enter** — Confirm
- **Escape** — Back
- **Q** — Open settings

## Project Structure

```
chance-survivors/
├── requirements.txt          # Python dependencies
├── AGENTS.md                 # Codebase structure and rules
├── REFACTOR.md              # Refactoring plan and extras
├── README.md                # This file
├── client/                  # Rendering and input
│   ├── __init__.py
│   └── render.py            # All pygame code
├── game/                    # Core game logic
│   ├── __init__.py
│   ├── main.py              # Main game loop
│   └── core/
│       ├── game.py          # State management
│       └── states.py        # Game states
└── .venv/                   # Virtual environment
```

## Dependencies

- pygame
- autopep8
- pylint
- fastapi
- uvicorn

## License

This project is for educational purposes.
