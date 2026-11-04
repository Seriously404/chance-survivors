# Bazaar UI Fixes - Implementation Notes

## Date: 2026-11-04

## Issues Fixed

### 1. Fusion Tab - No Inventory Display ✅
**Problem:** The fusion tab didn't show the player's inventory, making it impossible to select items for fusion.

**Solution:** Added inventory grid rendering at the bottom of the fusion tab using `_draw_inventory_grid()`.

**Files Modified:**
- `client/render.py` - Added inventory grid to `_draw_bazaar_fusion()`

### 2. Rarity Upgrader Tab - No Inventory Display ✅
**Problem:** The rarity upgrader tab didn't show the player's inventory, making it impossible to select items to upgrade.

**Solution:** Added inventory grid rendering at the bottom of the rarity upgrader tab.

**Files Modified:**
- `client/render.py` - Added inventory grid to `_draw_bazaar_rarity_upgrader()`

### 3. Level Upgrader Tab - No Inventory Display ✅
**Problem:** The level upgrader tab didn't show the player's inventory, making it impossible to select items to level up.

**Solution:** Added inventory grid rendering at the bottom of the level upgrader tab.

**Files Modified:**
- `client/render.py` - Added inventory grid to `_draw_bazaar_level_upgrader()`

### 4. Sell Buttons Not Working ✅
**Problem:** Sell buttons used action format `bazaar_sell_{id}_{index}` which didn't match the game loop handler expecting `bazaar_sell:{id}`.

**Solution:** Changed button action format from `bazaar_sell_{id}_{index}` to `bazaar_sell:{id}` to match the game loop handler.

**Files Modified:**
- `client/render.py` - Fixed button action format in `_draw_bazaar_sell()`

### 5. Can't Return to Main Menu from Bazaar ✅
**Problem:** The "Close" button in the bazaar menu didn't trigger any action to close the panel.

**Solution:** Added `bazaar_close` to the list of actions that trigger `close_panel()`.

**Files Modified:**
- `game/main.py` - Added `bazaar_close` to close panel handler

### 6. Fusion Button Gold Check ✅
**Problem:** The fusion button didn't check if the player had enough gold before allowing fusion.

**Solution:** Added gold check to fusion button color (green if affordable, red if not).

**Files Modified:**
- `client/render.py` - Added gold check in `_draw_bazaar_fusion()`

## Implementation Details

### Inventory Grid Rendering
All tabs that need item selection now use the existing `_draw_inventory_grid()` method:

```python
# Draw inventory grid below
inv_y = rect.bottom - 120
inv_rect = pygame.Rect(rect.left + 10, inv_y, rect.width - 20, 100)
pygame.draw.rect(self.screen, (40, 40, 40), inv_rect, border_radius=6)
pygame.draw.rect(self.screen, (100, 100, 100), inv_rect, 1, border_radius=6)
self._text("Inventory:", (inv_rect.left + 10, inv_rect.top + 5))
self._draw_inventory_grid(items, inv_rect)
```

### Button Action Format
The sell button action format was changed from:
```python
self._buttons[f"bazaar_sell_{item.get('id', '')}_{start_idx + i}"] = sell_btn
```
to:
```python
self._buttons[f"bazaar_sell:{item.get('id', '')}"] = sell_btn
```

This matches the game loop handler:
```python
elif action.startswith("bazaar_sell:"):
    item_id = action.split(":", 1)[1]
    # ... handle sell
```

### Close Panel Handler
The close panel handler now includes `bazaar_close`:
```python
if "close_panel" in actions or "bazaar_close" in actions:
    if game_state.active_panel:
        game_state.close_panel()
    else:
        paused = False
```

## Testing Results

All 150 tests pass, including:
- 14 bazaar system tests
- All other existing tests

## Next Steps

1. **Fusion System Integration** - The fusion tab needs to actually trigger the fusion recipe system when the FUSE button is clicked
2. **Rarity Upgrade Integration** - The rarity upgrader tab needs to trigger the actual upgrade when clicked
3. **Level Upgrade Integration** - The level upgrader tab needs to trigger the actual level up when clicked
4. **Item Selection** - Add click handlers to select items from the inventory grid for fusion/rarity/level tabs

## Known Limitations

- Fusion tab currently shows "Fusion requires selecting items from inventory first" message but doesn't actually perform fusion
- Rarity and level upgrade buttons don't have actual functionality yet
- Item selection from inventory grid is not implemented

These limitations are expected as they require additional integration work with the fusion and upgrade systems.
