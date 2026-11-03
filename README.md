# Chance Survivors

A luck-based roguelike where the goal is to reach infinity points and compete for the fastest time.

## Overview

**Chance Survivors** is a luck-based roguelike game where you try to reach approximately 1.797e308 points (infinity) and compete for the fastest time. The game loop involves defeating enemies, collecting points, and gambling them on new weapons, abilities, or upgrades to current items.

## Goal

Reach approximately 1.797e308 points (infinity) and achieve the fastest time.

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

You can "fuse" a combined item, permanently locking its stats. This can then be used as one item in other combinations. The catch is that fusing it permanently decreases the total power of it, creating decreasing return, to ensure that you wouldn't just infinitely keep stacking item upon item.

### Gambling

Lots of it. Nearly everything relies on gambling, and the strongest combinations would come from fusing things together and hoping whether you get the wanted outcome.

### Luck System

The game has a luck stat for the player, and the luckier the player is, the higher the chance of an event is. An event has difficulties. For example, a common sniper would have a fairly low difficulty, meaning that even with something like a luck stat of 10, you can hit a crit every time, but a legendary or even ultimate rarity sniper requires millions of luck to guarantee any chance of ever getting crits. Luck also changes your chances from loot crates, buyables, and other things. The whole game is structured around managing luck and trying to get lucky.

### Rarities and Levels

Any item has two separate things: a level and a rarity. The level is a +based scaling, where increasing level increases a specific stat by adding a base value on it. A rarity is a multiplier that multiplies the stats by a certain amount.

### Modifiers

Modifiers are special items that aren't used in combat, but rather are put in combinations to enhance the existing item. Examples include items that increase stats by ^1.05. A power in the equation is very powerful.

### Enemy Types

Enemies are different and have all kinds of resistances and types. This is to get the player to create actual element-based loadouts instead of just trying to make a super powerful gun that one-shots everything.

### Missions

Once in-game and past a certain milestone, you choose a main quest. Having this quest complete grants you up to a +20% total score bonus. Smaller missions can be accepted and taken on for smaller +1% to +5% bonuses. These bonuses add a percentage to your base score. The total score needs to be ~1.797e308, not base score. Main quests can be something like using a specific combination, NOT using a specific item, or others, while side missions are something like shooting this many enemies with gun A, while the enemies are on fire, etc.

### Scaling

Enemies scale as you progress, but not by time, but rather progress. You can also take missions that make enemies harder, or use weapons and abilities with modifiers that increase spawn rate, difficulty, and others. This is so that if you are in a very comfortable spot, you can up the difficulty yourself to get a faster time to the end.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Game

```bash
python game/main.py
```

## Controls

- **W, A, S, D** — Move the player
- **Mouse Click** — Shoot
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
