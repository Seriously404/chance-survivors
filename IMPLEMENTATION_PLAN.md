# Chance Survivors - Implementation Plan

## Executive Summary
This document outlines the comprehensive implementation plan to bring Chance Survivors as close as possible to the FINAL_DESIGN.md vision. The plan prioritizes the Bazaar system, content creation, and progressive polishing.

## Current State Analysis

### What's Working
- ✅ Basic game loop with pygame rendering
- ✅ Inventory system with item slots
- ✅ Enemy spawning and combat
- ✅ Basic item definitions in JSON
- ✅ Currency system (multiple currencies defined)
- ✅ Bazaar service layer (data logic)
- ✅ Combination system foundation
- ✅ Large number support

### Critical Gaps from FINAL_DESIGN.md

#### 1. Bazaar System (PRIORITY #1)
**Required by FINAL_DESIGN.md:**
- Fusion tab ✅ (partially implemented)
- Rarity Upgrader tab ❌ (not in UI)
- Level Upgrader tab ❌ (not in UI)
- Crates/Shop tab ✅ (partially implemented)
- Sell menu ❌ (not in UI)
- Additional creative features ❌ (casino, wizard, etc.)

**Current State:**
- Basic tab structure exists (Market, Crates, Fusion)
- Service layer has upgrade logic
- UI rendering is minimal/simplified
- Missing: Rarity upgrader UI, Level upgrader UI, Sell interface

#### 2. Content Creation (PRIORITY #2)
**Required by FINAL_DESIGN.md:**
- Hundreds of items with unique synergies
- Elemental system (damage types, resistances)
- Armor sets with playstyle-defining bonuses
- Ability combinations (base abilities + supplements)
- Relics with functionality over stats
- Fusion recipes

**Current State:**
- ~20 items in `build_extended_catalog()`
- Basic weapons, abilities, armor defined
- Missing: Full armor sets, many abilities, relics, fusion recipes
- Missing: Elemental interactions, set bonuses

#### 3. Quest System (PRIORITY #3)
**Required by FINAL_DESIGN.md:**
- Main quests (unlocked at level 5, can be locked)
- Side quests (progressive, cannot fail)
- Quest percentage bonuses on score
- Quest tracking UI

**Current State:**
- Quest JSON exists
- Quest system module exists
- UI for active quests exists (basic)
- Missing: Quest generation, main quest logic, locking mechanism

#### 4. Leaderboard API (PRIORITY #4)
**Required by FINAL_DESIGN.md:**
- FastAPI + Uvicorn server
- Score submission endpoint
- Leaderboard display (Place | Name | Score | Time)
- Detailed view on click
- Admin database clear (authenticated)

**Current State:**
- `game/leaderboard_api.py` exists
- `game/leaderboard_client.py` exists
- Missing: FastAPI server implementation, website UI

#### 5. Scaling Systems (PRIORITY #5)
**Required by FINAL_DESIGN.md:**
- Time-based scaling
- Player-controlled difficulty scaling (separate)
- Enemy composition changes
- Spawn rate control
- Reward scaling

**Current State:**
- Basic scaling exists
- Threat level buttons exist
- Missing: Modular scaling system, player-controlled modifiers

#### 6. UI Polish (PRIORITY #6)
**Required by FINAL_DESIGN.md:**
- Consistent visual language
- Green accent color
- Readability improvements
- Visual feedback
- Animations
- Glow effects for certain items
- Proper rarity presentation

**Current State:**
- Basic rendering exists
- Rarity icons exist
- Missing: Glow effects, animations, polished UI elements

---

## Implementation Phases

### Phase 1: Bazaar System Completion (Week 1-2)

#### 1.1 Rarity Upgrader Tab
**Files to modify:** `client/render.py`, `game/systems/bazaar.py`

**Features:**
- Select item to upgrade
- Display current rarity and tier
- Show currency options with favorability indicators
- Luck-based probability display
- Visual feedback on success/failure
- Ultimate tier progression (1-100)

**UI Layout:**
```
┌─────────────────────────────────────┐
│ RARITY UPGRADER                     │
├─────────────────────────────────────┤
│ Selected: [Item Icon] Name          │
│ Current: Epic (tier 1)              │
│ Next: Legendary                     │
│                                     │
│ Currency Options:                   │
│ [Gold]  +15% chance (favored)       │
│ [Silver] 0% chance (neutral)        │
│ [Copper] -20% chance (unfavored)    │
│                                     │
│ Luck bonus: +8%                     │
│ Success chance: 42%                 │
│ Cost: 50 Gold                       │
│                                     │
│ [UPGRADE BUTTON]                    │
└─────────────────────────────────────┘
```

#### 1.2 Level Upgrader Tab
**Features:**
- Select item to upgrade
- Display current level and stats
- Show upgrade cost
- Preview stat increases
- Visual level indicator

**UI Layout:**
```
┌─────────────────────────────────────┐
│ LEVEL UPGRADER                      │
├─────────────────────────────────────┤
│ Selected: [Item Icon] Name          │
│ Current Level: 5                    │
│ Next Level: 6                       │
│                                     │
│ Stat Changes:                       │
│ +Damage: +3                         │
│ +Cooldown: -0.02s                   │
│                                     │
│ Cost: 120 Gold                      │
│                                     │
│ [UPGRADE BUTTON]                    │
└─────────────────────────────────────┘
```

#### 1.3 Sell Menu
**Features:**
- Browse inventory items
- Display sell value
- Quick sell all option
- Trader bonus display (if applicable)
- Confirmation dialog

**UI Layout:**
```
┌─────────────────────────────────────┐
│ SELL MARKET                         │
├─────────────────────────────────────┤
│ [Scrollable inventory list]         │
│ - Item name (Rarity)                │
│   Value: 45 Gold                    │
│   [SELL]                            │
│                                     │
│ Total: 1,250 Gold                   │
│ [SELL ALL] [CANCEL]                 │
└─────────────────────────────────────┘
```

#### 1.4 Additional Creative Features
**Suggestions from FINAL_DESIGN.md:**
- **Wizard NPC**: Sells combination slots for price
- **Casino**: Exchange currencies with risk/reward
- **Enchanter**: Add random modifiers to items
- **Appraiser**: Reveal hidden item properties

**Implementation Priority:**
1. Enchanter (simplest, fits design)
2. Appraiser (useful for players)
3. Casino (gambling theme)
4. Wizard (complex, later)

### Phase 2: Content Expansion (Week 2-3)

#### 2.1 Weapons (Add 30+ new weapons)
**Categories:**
- Rifles (rapid fire, balanced)
- Snipers (high damage, slow, piercing)
- Shotguns (pellets, short range, high damage)
- Machine guns (low accuracy, fast fire)
- Alien guns (homing bullets)
- Special weapons (elemental, unique mechanics)

**Example New Weapons:**
```json
{
  "id": "void-piercer",
  "name": "Void Piercer",
  "type": "weapon",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "bullet_type": "heavy_shot",
    "damage": 35,
    "cooldown": 0.8,
    "speed_modifier": 2.0,
    "piercing": 8,
    "element": "shadow"
  },
  "description": "A shadow-infused sniper that penetrates multiple enemies."
}
```

#### 2.2 Abilities (Add 40+ new abilities)
**Categories:**
- Elemental projectiles (fire, frost, shadow, light, arcane)
- AoE abilities (nova, grenade, area denial)
- Support abilities (heal, shield, buff)
- Utility abilities (teleport, invisibility, dash)
- Minion/sentry abilities (builder playstyle)

**Example New Abilities:**
```json
{
  "id": "sentinel-summon",
  "name": "Sentinel Summon",
  "type": "ability",
  "rarity": "legendary",
  "level": 1,
  "stats": {
    "cooldown": 30,
    "cast_type": "summon",
    "summon_count": 2,
    "summon_duration": 15,
    "summon_health": 50,
    "summon_damage": 15
  },
  "description": "Summons 2 sentinels that attack nearby enemies for 15 seconds."
}
```

#### 2.3 Armor Sets (Implement set bonuses)
**Required Sets:**
1. **Speedster Set** (Boots, Pants, Chest, Head, Accessory)
   - Faster movement
   - Damage increases with speed
   - Debuff: Reduced defense

2. **Tank Set**
   - High defense
   - Dash damages enemies
   - Invulnerability frames
   - Debuff: Slower movement

3. **Ranged Set**
   - Damage increases with distance
   - Bullet speed bonus
   - Debuff: Reduced melee effectiveness

4. **Sneaky Set**
   - Bonuses against unaware enemies
   - Invisibility synergy
   - Debuff: Reduced direct combat

5. **Elemental Sets** (Fire, Frost, Shadow, Light, Arcane)
   - Elemental damage bonus
   - Elemental resistance
   - Debuff: Weakened other elements

**Example Set Definition:**
```json
{
  "id": "speedster-boots",
  "name": "Speedster Boots",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "speed_pct": 12,
    "defense": 2
  },
  "armor_set": "speedster",
  "armor_slot": "boots"
}
```

#### 2.4 Relics (Add 20+ relics)
**Required Relics:**
- Lucky Box (increases luck on cast)
- Monkey's Paw (random buffs/nerfs, rerollable)
- Enemy Spawner (increases spawn rate)
- Ricochet Amulet (bullet ricochet)
- Sentinel Heart (minion defense)
- Chaos Core (random stat boosts)
- Time Crystal (time manipulation)
- Infinity Shard (approaches infinity)

**Example Relic:**
```json
{
  "id": "lucky-box",
  "name": "Lucky Box",
  "type": "misc",
  "rarity": "legendary",
  "level": 1,
  "stats": {
    "luck": 8,
    "damage_pct": 6
  },
  "behavior": {
    "type": "on_cast",
    "effect": "permanent_luck_increase",
    "amount": 0.5
  },
  "description": "Attached to an ability, increases luck permanently on each cast."
}
```

#### 2.5 Currencies (Expand to 15+)
**Current:** Copper, Silver, Gold, Dark Matter, Holy Water, Essence, Arcane Dust, Chaos Fragment, Infinity Shard, Time Crystal

**Add:**
- Blood Orb (enemy kill currency)
- Star Dust (cosmic currency)
- Soul Fragment (boss drops)
- Mana Crystal (magic enemies)
- Iron Coin (common enemies)
- Platinum Nugget (rare enemies)
- Quantum Bit (endgame currency)

### Phase 3: Quest System (Week 3-4)

#### 3.1 Quest Generation System
**Files to modify:** `game/systems/quests.py`, `assets/quests.json`

**Features:**
- Main quest generation at level 5
- Side quest progression tree
- Quest failure conditions
- Quest locking mechanism

**Example Main Quest:**
```json
{
  "id": "main-no-snipers",
  "name": "Close Quarters Combat",
  "type": "main",
  "unlock_level": 5,
  "description": "Prove your skill without relying on long-range weapons.",
  "restriction": "no_snipers",
  "bonus_pct": 50,
  "conditions": {
    "kill_count": 100,
    "time_limit": null
  },
  "failure_condition": "equip_sniper"
}
```

**Example Side Quest:**
```json
{
  "id": "side-fire-kills-1",
  "name": "Pyromaniac",
  "type": "side",
  "unlock_level": 3,
  "description": "Kill 25 enemies with fire damage.",
  "bonus_pct": 10,
  "conditions": {
    "fire_damage_dealt": 25
  }
}
```

#### 3.2 Quest UI
**Files to modify:** `client/render.py`

**Features:**
- Quest log panel
- Active quests display
- Quest completion preview
- Lock/unlock main quest toggle

### Phase 4: Leaderboard API (Week 4-5)

#### 4.1 FastAPI Server
**Files to create:** `api/server.py`, `api/models.py`, `api/database.py`

**Endpoints:**
- `POST /api/run` - Submit run
- `GET /api/leaderboard` - Get leaderboard
- `GET /api/run/{id}` - Get run details
- `DELETE /api/database` - Clear database (admin)

**Database Schema:**
```sql
CREATE TABLE runs (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(100),
    final_score BIGINT,
    run_time_seconds INTEGER,
    inventory JSONB,
    player_level INTEGER,
    luck FLOAT,
    submitted_at TIMESTAMP
);
```

#### 4.2 Website UI
**Files to create:** `website/index.html`, `website/styles.css`, `website/run_detail.html`

**Features:**
- Clean leaderboard table
- Clickable entries
- Detailed run view
- Responsive design

### Phase 5: Scaling Systems (Week 5-6)

#### 5.1 Modular Scaling
**Files to modify:** `game/systems/enemy_scaling.py`, `game/systems/spawner.py`

**Features:**
- Time-based scaling curve
- Player-controlled difficulty modifiers
- Separate reward scaling
- Enemy composition changes

**Scaling Parameters:**
```python
SCALING_CONFIG = {
    "time_based": {
        "health_scale": 1.05,  # 5% per minute
        "damage_scale": 1.03,
        "spawn_rate_scale": 1.02
    },
    "player_controlled": {
        "threat_levels": 10,
        "per_level_modifiers": {
            "health": 1.2,
            "damage": 1.15,
            "spawn_rate": 1.1
        }
    }
}
```

### Phase 6: UI Polish (Week 6-7)

#### 6.1 Visual Effects
**Files to modify:** `client/render.py`

**Features:**
- Glow effects for legendary+ items
- Ability VFX (particles, trails)
- Rarity gradient backgrounds
- Smooth animations
- Screen shake on damage
- Hit markers

#### 6.2 UI Improvements
**Files to modify:** `client/render.py`

**Features:**
- Consistent green accent color
- Better readability
- Tooltips for item stats
- Combination preview
- Currency display improvements
- Scroll indicators

### Phase 7: Testing & Bug Fixes (Week 7-8)

#### 7.1 Comprehensive Testing
- Run all existing tests
- Create new tests for implemented features
- Test edge cases (extreme values, corrupted data)
- Test UI interactions
- Test API endpoints

#### 7.2 Bug Fixes
- Fix all reported bugs
- Address performance issues
- Fix numerical precision problems
- Resolve UI glitches

---

## Implementation Order

1. **Bazaar UI Completion** (Rarity Upgrader, Level Upgrader, Sell)
2. **Content Creation** (Weapons, Abilities, Armor Sets, Relics)
3. **Quest System** (Generation, UI, Locking)
4. **Leaderboard API** (Server, Website)
5. **Scaling Systems** (Modular, Player-Controlled)
6. **UI Polish** (Effects, Animations, Readability)
7. **Testing & Bug Fixes**

---

## Success Criteria

### Bazaar System
- ✅ All 6 tabs implemented (Market, Crates, Fusion, Rarity Upgrader, Level Upgrader, Sell)
- ✅ Additional creative features (Enchanter, Casino, etc.)
- ✅ Proper currency handling
- ✅ Luck-based probability system

### Content
- ✅ 100+ unique items
- ✅ 20+ armor sets with bonuses
- ✅ 50+ abilities with combinations
- ✅ 30+ relics
- ✅ 15+ currencies

### Quests
- ✅ Main quest system with locking
- ✅ Side quest progression
- ✅ Quest UI and tracking

### Leaderboard
- ✅ FastAPI server running
- ✅ Score submission working
- ✅ Leaderboard display functional
- ✅ Admin controls secured

### Scaling
- ✅ Time-based scaling
- ✅ Player-controlled difficulty
- ✅ Separate reward scaling

### UI
- ✅ Green accent color
- ✅ Glow effects
- ✅ Animations
- ✅ Readable, clean interface

---

## Notes

- This plan assumes 2-week sprints with weekly reviews
- Content creation should be iterative (add, test, refine)
- UI polish should happen continuously, not just at the end
- Testing should be integrated throughout, not just at the end
- The Bazaar system is the highest priority as it's the core economy
- Multiplayer is explicitly out of scope for now (optional per FINAL_DESIGN.md)
