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
2. Collect score, experience, and currencies from kills
3. Spend currencies on crates and upgrades
4. Combine items to create powerful combinations
5. Fuse items to lock their stats and use them in further combinations
6. Repeat until death or victory

## Features

### Combinations

The player can add any ability or weapon on to any other ability or weapon to either increase the current stats, add new functionality, or completely rework how the base item works. The game provides many basic parts and elements, and you must create combinations of them to build out your toolkit.

### Fusion

Fusion is available from the start, with stronger recipes unlocking at later levels. The Bazaar lists each recipe and its requirements. Only unequipped items that are not already used in combinations can be consumed; invalid attempts leave the inventory unchanged and report why. Fused results record their source items and are marked fusion-only so they cannot appear as ordinary drops or shop entries.

### Gambling

Lots of it. Nearly everything relies on gambling, and the strongest combinations would come from fusing things together and hoping whether you get the wanted outcome.

### Luck System

The game has a luck stat for the player, and the luckier the player is, the higher the chance of an event is. An event has difficulties. For example, a common sniper would have a fairly low difficulty, meaning that even with something like a luck stat of 10, you can hit a crit every time, but a legendary or even ultimate rarity sniper requires millions of luck to guarantee any chance of ever getting crits. Luck also changes your chances from loot crates, buyables, and other things. The whole game is structured around managing luck and trying to get lucky.

### Rarities and Levels

Any item has two separate things: a level and a rarity. Levels add the configured per-level stat contribution before rarity is applied; the default contribution is 10% of the base stat per level, configurable through `assets/item_level_scaling.json`. Cooldown levels instead subtract 2% of the base cooldown per level, with a 0.05-second minimum, so leveling does not make abilities or weapons slower. Rarity multiplies the resulting stats.

Mythical items can upgrade into Ultimate 1. Inventory and run saves preserve Ultimate subtiers, and icons progress from deep blue-purple toward white.

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

The Bazaar sells themed crates in different currencies and offers relics in the market. Use the fusion table and codex to craft special items, gamble currency pools on rarity, exchange currencies, upgrade item levels, or sell unequipped items. Crates rotate as active run time advances. Wheel scrolling exposes longer lists, and failed transactions display feedback.

### Missions

Select quests in the Quests panel. Side quests add percentage bonuses; at level 8, choose one of three restricted main quests or skip the main quest for the run. Completed main quests raise the score to the shown power. The choice and restrictions persist in run saves.

### Scaling

New enemies scale with active run time. Their health and rewards rise while spawn intervals shorten; time in menus and while paused does not advance scaling or the run timer.

### Active Abilities

Hold an equipped ability's number key (1–9, then 0 for slot 10) to aim, and release it to cast. Cooldowns appear on the ability bar. New runs begin with a basic fireball as well as a rifle.

### Run Uploads

When a run ends, the results screen offers an optional leaderboard upload. Nothing is submitted unless you choose **Upload Score**. The client sends the final score, active run time, level, luck, inventory, active equipment, and build stats to the API at `CHANCE_SURVIVORS_LEADERBOARD_URL` (default `http://127.0.0.1:8000`). Upload failures are shown on the results screen and can be retried.

### Run Saves

Active runs are atomically autosaved every 15 seconds and when leaving a run for the menu or closing the game. Choose **Resume Run** from the main menu to continue the saved run; transient enemies, projectiles, and cooldowns restart cleanly, while score, active gameplay time, player health, progression, inventory/equipment, currencies, quests, threat, and item IDs are preserved. Starting a new run replaces the previous save, and completed runs are removed from the resume slot. The versioned save defaults to `data/run_save.json`; set `CHANCE_SURVIVORS_RUN_SAVE` to use another path.

## Installation

Run these commands from the project root with Python 3.12. A virtual environment
is recommended:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Running the Game

```bash
python -m game.main
```

## Leaderboard API

The project includes a FastAPI + Uvicorn leaderboard server for persistent run submissions.

```bash
export CHANCE_SURVIVORS_ADMIN_TOKEN="replace-me-with-a-secret-token"
python -m game.leaderboard_api
```

Then open `http://localhost:8000/` to view the leaderboard. The page includes a ranked table, a per-entry detail panel, and a button to clear the database after supplying the admin token.

Open `http://127.0.0.1:8000/docs` for interactive API documentation, including run submission and leaderboard endpoints. The older `python -m api.main` server entry point also exposes these routes and its legacy player-stat endpoints.

## Controls

- **W, A, S, D** — Move the player
- **Space** — Dash
- **Mouse** — Aim; left and right click fire equipped weapons
- **Hold and release 1–9, 0** — Aim and cast ability slots 1–10
- **Enter** — Confirm
- **Escape** — Back, or save and return to the title during a run
- Use the on-screen buttons to open menus and pause.

## Tests

```bash
python -m unittest discover -s tests
```

For headless environments, set `SDL_VIDEODRIVER=dummy` and
`SDL_AUDIODRIVER=dummy` before running tests that initialize the renderer.

## Project Structure

```
chance-survivors/
├── requirements.txt          # Python dependencies
├── AGENTS.md                 # Codebase structure and rules
├── README.md                # This file
├── api/                     # Legacy API entry point
├── assets/                  # Item, enemy, and other game data
├── client/                  # Pygame rendering and input
├── game/                    # Game logic and leaderboard API
│   └── main.py              # Main game loop
├── scripts/                 # Development helpers
└── tests/                   # Automated tests
```

## Dependencies

- pygame
- autopep8
- pylint
- fastapi
- uvicorn
- httpx2

## License

This project is for educational purposes.
