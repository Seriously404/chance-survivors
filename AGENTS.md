# AGENTS.md

## Codebase Structure

This document describes the structure of the Chance Survivors codebase, what each file does, and the rules for working with it.

### Root Level

- `requirements.txt` — Python dependencies for the project.
- `AGENTS.md` — This file. Describes the codebase structure and rules.
- `REFACTOR.md` — Describes the planned refactoring steps and extras.
- `README.md` — Permanent documentation of the project.

### `game/` — Core Game Logic

This folder contains the main game loop and core functions. It is the root of the game logic and connects all other components together.

- `game/main.py` — The root script. Holds the main game loop and connects everything else together. This file is the entry point for the game. It imports and initializes all other components and runs the main loop.
- `game/core/` — Contains additional core scripts that support the main game loop.
  - `game/core/game.py` — Manages game state transitions (MENU, SETTINGS, PLAYING, GAME_OVER) and panel management.
  - `game/core/states.py` — Defines the `GameState` enum with all possible game states.

### `client/` — Rendering and Input

This folder contains all rendering data and anything that includes pygame. It is responsible for all visual output and input handling.

- `client/render.py` — The `Renderer` class. Handles all pygame operations: initialization, event processing, input handling, and all rendering functions (grid, player, enemies, bullets, health bars, timer, debug info).
- `client/__init__.py` — Package marker file (currently empty).

### `game/` Package

- `game/__init__.py` — Package marker file (currently empty).

## Rules for Working with the Codebase

### Rule 1: Never modify the `.venv` folder

The virtual environment folder (`.venv`) is managed by the Python environment and should never be modified directly. All dependency management should be done through `requirements.txt`.

### Rule 2: `game/main.py` is the root script

The file `game/main.py` is the entry point and holds the main game loop. It connects all other components together. All other modules are imported and initialized from this file.

### Rule 3: `game/main.py` must not use pygame directly

The file `game/main.py` is not allowed to use pygame at all. If a function is required that is only available through pygame, it must be imported from the `client/` folder instead. This keeps the separation of concerns clear: game logic in `game/`, rendering in `client/`.

### Rule 4: Pygame scripts must only be in `client/`

Scripts that use pygame can only be in the `client/` folder. No other folder can contain a script that imports pygame. This enforces the separation between game logic and rendering.

### Rule 5: Plan before implementing

When facing a major task, plan the implementation into smaller tasks first, then delegate sub-agents that implement, test, and report whether the implementation is successful or not. A sub-agent cannot create new sub-agents, and must first read `AGENTS.md` to understand what it is allowed to do.

### Rule 6: Import pygame through client

Any code in `game/` that needs pygame functionality must import it through the `client/` folder. For example, instead of `import pygame`, use `from client.render import Renderer` or similar.

### Rule 7: Maintain separation of concerns

The `game/` folder should contain pure game logic (math, state management, entity updates, collision detection). The `client/` folder should contain all rendering and input handling. This separation makes the codebase easier to understand, test, and extend.

## File Descriptions

### `game/main.py`

The main entry point and game loop. Responsibilities:
- Import and initialize all game components
- Run the main game loop
- Handle state transitions between game states
- Coordinate updates between all game systems
- Import pygame-related functionality from `client/`

### `game/core/game.py`

Manages game state and panels. Responsibilities:
- Track current game state (MENU, SETTINGS, PLAYING, GAME_OVER)
- Manage active panels (UI overlays during gameplay)
- Handle state transitions
- Store player name

### `game/core/states.py`

Defines game states. Responsibilities:
- Define the `GameState` enum
- List all possible game states: MENU, SETTINGS, PLAYING, GAME_OVER

### `client/render.py`

The renderer class. Responsibilities:
- Initialize pygame and display
- Process all pygame events (keyboard, mouse, quit)
- Handle input (movement, shooting, actions)
- Render all game elements (grid, player, enemies, bullets, health bars, timer, debug info)
- Manage the pygame display lifecycle

### `client/__init__.py`

Package marker file. Currently empty.

### `game/__init__.py`

Package marker file. Currently empty.

## Import Structure

The import structure enforces the separation of concerns:

```
game/
├── main.py          # Entry point, imports from client/
└── core/
    ├── game.py      # State management, imports from client/
    └── states.py    # GameState enum
client/
├── render.py        # All pygame code
└── __init__.py      # Package marker
```

## Testing Guidelines

- Test game logic in `game/` without pygame dependencies
- Test rendering in `client/` with pygame
- Keep tests separate from the main codebase
- Test collision detection, entity updates, and state transitions independently

## Extension Guidelines

When adding new features:

1. **New game logic**: Add to `game/` folder, keeping pure logic separate from rendering
2. **New rendering**: Add to `client/render.py` or create new files in `client/`
3. **New game states**: Add to `game/core/states.py` and `game/core/game.py`
4. **New input handling**: Add to `client/render.py`
5. **New entity types**: Add to `game/` (logic) and `client/` (rendering)

## Launch command
Python -m game.main
This command launches the entire project. if possible, run it once after implementing fixes, then analyze any problems that occur.

## NOTE
Python -m game.main is not a done deal test that your feature is implemented correctly, you NEED to correctly test your new features, by writing either helper scripts to call them manually, or by using a controllable headless mode, that allows you to analyze what it does.