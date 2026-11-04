# Bug Fixes Summary - 2026-11-04

## Issues Fixed

### 1. Bazaar Crash (CRITICAL)
**Issue**: `TypeError: Renderer._text() got an unexpected keyword argument 'bold'`
**Location**: `client/render.py` line 1227
**Fix**: Removed `bold=True` parameter from `_text()` call. The `_text()` method doesn't support bold formatting.

### 2. Pylance Errors (50+ errors)
**Issue**: Undefined variables (`bazaar`, `crates`, `left`, `right`, `catalog`, `state`, `outer`, `owned_prices`, `shop_height`)
**Location**: `client/render.py` lines 1413-1524
**Fix**: Completely rewrote `_draw_bazaar_menu()` to be simple and clean, removing all the old broken code that referenced undefined variables.

### 3. Starting Gun Too Fast
**Issue**: `starter-rapid` had cooldown of 0.14 seconds, making it too powerful
**Location**: `assets/weapons.json`
**Fix**: Changed cooldown from 0.14 to 0.25 seconds and rarity from "uncommon" to "common" for better balance.

### 4. Leaderboard Server Setup
**Issue**: No leaderboard server structure existed
**Fix**: Created complete FastAPI leaderboard server:
- `api/main.py` - FastAPI application with endpoints:
  - `POST /scores` - Submit scores
  - `GET /scores/top` - Get top 10 scores
  - `GET /players/{name}/stats` - Get player stats (returns 404 if player not found)
- `api/db.py` - Database operations module
- `api/__init__.py` - Package marker
- SQLite database: `game.db` (added to `.gitignore`)

**Launch command**: `uvicorn api.main:app --reload`

## Files Modified

1. `client/render.py` - Fixed `_draw_bazaar_menu()` to remove crash-causing code
2. `assets/weapons.json` - Balanced starting weapon stats
3. `.gitignore` - Added `game.db` and `*.db` patterns
4. `api/main.py` - New file: FastAPI leaderboard server
5. `api/db.py` - New file: Database operations
6. `api/__init__.py` - New file: Package marker

## Testing

- All 152 tests pass ✅
- Game starts without crashing ✅
- No Pylance errors ✅

## Remaining Issues (Not Fixed)

The following issues were mentioned but not addressed in this session:
- Inventory showing random items (may need investigation of spawn logic)
- Right-click shooting white bullet (may need weapon slot logic check)
- Health bars not drawing on enemies (may need rendering fix)

These would require deeper investigation of the game loop and rendering logic.
