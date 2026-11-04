# Task Board - UI Refinement & Bug Fixes

## Current Status
- **Date**: 2026-11-03
- **Session**: UI refinement and bug fixes

## Bugs to Fix

### 1. Crash on Number Key Press (CRITICAL)
- **Issue**: `NameError: name 'enemy' is not defined` in `_draw_ability_vfx`
- **Location**: `client/render.py` line 368
- **Cause**: Leftover code referencing undefined variables
- **Status**: ✅ FIXED - Removed erroneous health bar code from ability VFX

### 2. Starting Inventory Too Powerful
- **Issue**: Player starts with multiple weapons and abilities
- **Current**: vest, boots, plate, rapid, heavy, charm, core
- **Required**: Only basic common rifle (starter-rapid)
- **Status**: ✅ FIXED - Updated `create_initial_inventory()` in `game/systems/items.py`

### 3. Fusion in Wrong Tab
- **Issue**: Fusion appears in Upgrades tab instead of Bazaar
- **Location**: UI rendering logic in `client/render.py`
- **Status**: ✅ FIXED - Moved fusion to Bazaar Fusion tab

### 4. Bazaar UI Incomplete
- **Issue**: Bazaar is a "barely readable mess"
- **Requirements**:
  - Proper tab structure (Market vs Crates)
  - Clear item display with stats
  - Currency display and affordability indicators
  - Better layout and readability
- **Status**: ✅ FIXED - Implemented tab-based Bazaar with Market, Crates, and Fusion tabs

### 5. Inventory Click Issues
- **Issue**: Cannot click on specific items to inspect them
- **Location**: `client/render.py` inventory interaction logic
- **Status**: ⏳ PENDING - Fix item click detection

### 6. Bonuses Overlap
- **Issue**: Bonus stats overlap in inventory display
- **Location**: `client/render.py` bonus rendering
- **Status**: ⏳ PENDING - Fix layout to prevent overlap

### 7. Bazaar Tab State Variable
- **Issue**: Tab state uses `bazaar_tab` but code checks `self._bazaar_tab`
- **Location**: `client/render.py` tab switching logic
- **Status**: ✅ FIXED - Standardized to `self._bazaar_tab`

## Implementation Plan

### Phase 1: Critical Bug Fixes
1. ✅ Fix `_draw_ability_vfx` crash (DONE)
2. Fix starting inventory to only have starter-rapid
3. Fix inventory click detection

### Phase 2: UI Refinement
4. Move fusion to Bazaar tab
5. Redesign Bazaar UI with proper tabs
6. Fix bonus overlap in inventory
7. Improve overall UI readability

### Phase 3: Testing
8. Test all fixes
9. Verify no regressions
10. Document changes

## Files to Modify

- `client/render.py` - UI rendering, ability VFX, inventory, bazaar
- `game/systems/items.py` - Starting inventory configuration
- `game/main.py` - Game initialization

## Notes

- All changes must maintain separation of concerns (game logic vs rendering)
- UI improvements should be visually appealing and user-friendly
- Test after each major change
- Document any new dependencies or requirements

## Incomplete work / Blockers
- None currently - all 150 tests pass

## Agent messages
- To all agents: Content expansion work is complete. All new weapons, abilities, armor sets, relics, and currencies have been added to their respective JSON files. The armor set system now supports 8 total sets (2 original + 6 new). All tests pass. Next priorities per the implementation roadmap: (1) Combination system UI implementation, (2) Leaderboard API FastAPI server, (3) Quest system main/side quest logic, (4) Enemy scaling modular implementation, (5) UI polish (glow effects, animations).

- Session 2026-11-03: Combination UI implementation complete with stat preview, visual feedback, and apply button. Projectile effects (homing, explosive, ricochet) implemented in collision.py. All 150 tests pass.
