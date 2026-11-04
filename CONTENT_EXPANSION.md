# Chance Survivors - Content Expansion

This file contains original content additions to bring the game closer to the FINAL_DESIGN.md vision.

## Weapons (30+ new weapons)

### Rapid Fire Rifles
```json
{
  "id": "arc-rifle",
  "name": "Arc Rifle",
  "type": "weapon",
  "rarity": "common",
  "level": 1,
  "stats": {
    "bullet_type": "rapid_fire",
    "damage": 7,
    "cooldown": 0.15,
    "speed_modifier": 3.2,
    "piercing": 0,
    "element": "arcane"
  },
  "description": "A basic arcane rifle for beginners."
}
```

### Snipers
```json
{
  "id": "lantern-sniper",
  "name": "Lantern Sniper",
  "type": "weapon",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "bullet_type": "heavy_shot",
    "damage": 22,
    "cooldown": 0.72,
    "speed_modifier": 2.6,
    "piercing": 4,
    "element": "light"
  },
  "description": "A light-infused sniper with high piercing capability."
}
```

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

### Shotguns
```json
{
  "id": "flame-blaster",
  "name": "Flame Blaster",
  "type": "weapon",
  "rarity": "uncommon",
  "level": 1,
  "stats": {
    "bullet_type": "shotgun",
    "damage": 12,
    "cooldown": 0.9,
    "speed_modifier": 2.0,
    "pellets": 6,
    "pellet_range": 8,
    "element": "fire"
  },
  "description": "A fire shotgun that fires 6 pellets with burn effects."
}
```

### Machine Guns
```json
{
  "id": "storm-spool",
  "name": "Storm Spool",
  "type": "weapon",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "bullet_type": "rapid_fire",
    "damage": 26,
    "cooldown": 0.11,
    "speed_modifier": 4.2,
    "piercing": 2,
    "element": "frost"
  },
  "description": "A frost-infused rapid-fire weapon with exceptional speed."
}
```

### Alien/Homing Weapons
```json
{
  "id": "homing-devastator",
  "name": "Homing Devastator",
  "type": "weapon",
  "rarity": "legendary",
  "level": 1,
  "stats": {
    "bullet_type": "homing",
    "damage": 28,
    "cooldown": 0.25,
    "speed_modifier": 3.8,
    "piercing": 1,
    "homing_speed": 5.0,
    "element": "arcane"
  },
  "description": "An alien weapon with homing bullets that track enemies."
}
```

## Abilities (40+ new abilities)

### Elemental Projectiles
```json
{
  "id": "ember-wand",
  "name": "Ember Wand",
  "type": "ability",
  "rarity": "uncommon",
  "level": 1,
  "stats": {
    "cooldown": 8,
    "damage_pct": 12,
    "burn": 2,
    "cast_type": "projectile",
    "cast_damage": 22,
    "cast_speed_modifier": 2.8,
    "element": "fire"
  },
  "description": "A wand that casts fire spells with burn effects."
}
```

```json
{
  "id": "frost-lantern",
  "name": "Frost Lantern",
  "type": "ability",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "cooldown": 9,
    "damage_pct": 14,
    "luck": 3,
    "cast_type": "nova",
    "cast_damage": 26,
    "cast_radius": 0.45,
    "element": "frost"
  },
  "description": "A frost nova that slows enemies in the area."
}
```

### AoE Abilities
```json
{
  "id": "void-bloom",
  "name": "Void Bloom",
  "type": "ability",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "cooldown": 12,
    "damage_pct": 18,
    "crit_chance": 4,
    "cast_type": "nova",
    "cast_damage": 32,
    "cast_radius": 0.6,
    "element": "shadow"
  },
  "description": "A void ability that increases critical chance."
}
```

### Support Abilities
```json
{
  "id": "warding-sigil",
  "name": "Warding Sigil",
  "type": "ability",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "cooldown": 10,
    "shield": 8,
    "luck": 1,
    "cast_type": "heal",
    "heal_amount": 18
  },
  "description": "A sigil that creates a protective ward."
}
```

### Minion/Sentry Abilities
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

```json
{
  "id": "turret-deploy",
  "name": "Turret Deploy",
  "type": "ability",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "cooldown": 25,
    "cast_type": "summon",
    "summon_count": 1,
    "summon_duration": 20,
    "summon_health": 30,
    "summon_damage": 12,
    "summon_fire_rate": 0.3
  },
  "description": "Deploys a turret that fires at nearby enemies for 20 seconds."
}
```

### Utility Abilities
```json
{
  "id": "blink-step",
  "name": "Blink Step",
  "type": "ability",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "cooldown": 12,
    "cast_type": "teleport",
    "teleport_distance": 8,
    "leave_trail": true,
    "trail_element": "arcane"
  },
  "description": "Teleports a short distance, leaving an arcane trail."
}
```

## Armor Sets (5 complete sets)

### Speedster Set
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

```json
{
  "id": "speedster-pants",
  "name": "Speedster Pants",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "speed_pct": 10,
    "defense": 3
  },
  "armor_set": "speedster",
  "armor_slot": "pants"
}
```

```json
{
  "id": "speedster-vest",
  "name": "Speedster Vest",
  "type": "armor",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "speed_pct": 8,
    "defense": 4,
    "damage_pct": 5
  },
  "armor_set": "speedster",
  "armor_slot": "chest"
}
```

```json
{
  "id": "speedster-helmet",
  "name": "Speedster Helm",
  "type": "armor",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "speed_pct": 6,
    "defense": 5
  },
  "armor_set": "speedster",
  "armor_slot": "head"
}
```

```json
{
  "id": "speedster-amulet",
  "name": "Speedster Amulet",
  "type": "armor",
  "rarity": "legendary",
  "level": 1,
  "stats": {
    "speed_pct": 15,
    "damage_pct": 10
  },
  "armor_set": "speedster",
  "armor_slot": "accessory"
}
```

**Speedster Set Bonus:**
- 2 pieces: +5% movement speed
- 3 pieces: Damage increases by 1% per 1% movement speed above base
- 4 pieces: Dash leaves a speed trail that boosts allies
- 5 pieces: Movement speed capped at 200%, damage bonus capped at 50%

**Debuff:** Defense reduced by 20%

### Tank Set
```json
{
  "id": "titan-boots",
  "name": "Titan Boots",
  "type": "armor",
  "rarity": "uncommon",
  "level": 1,
  "stats": {
    "defense": 4,
    "health": 15
  },
  "armor_set": "titan",
  "armor_slot": "boots"
}
```

```json
{
  "id": "titan-pants",
  "name": "Titan Pants",
  "type": "armor",
  "rarity": "uncommon",
  "level": 1,
  "stats": {
    "defense": 5,
    "health": 20
  },
  "armor_set": "titan",
  "armor_slot": "pants"
}
```

```json
{
  "id": "titan-plate",
  "name": "Titan Plate",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "defense": 7,
    "health": 30
  },
  "armor_set": "titan",
  "armor_slot": "chest"
}
```

```json
{
  "id": "titan-helm",
  "name": "Titan Helm",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "defense": 6,
    "health": 25
  },
  "armor_set": "titan",
  "armor_slot": "head"
}
```

```json
{
  "id": "titan-shield",
  "name": "Titan Shield",
  "type": "armor",
  "rarity": "legendary",
  "level": 1,
  "stats": {
    "defense": 10,
    "health": 40,
    "dash_damage": 25
  },
  "armor_set": "titan",
  "armor_slot": "accessory"
}
```

**Tank Set Bonus:**
- 2 pieces: +10% health, dash damages nearby enemies
- 3 pieces: Gain 1 second of invulnerability after taking damage
- 4 pieces: Dash creates a shockwave that stuns enemies
- 5 pieces: Invulnerability frames increase to 2 seconds, dash damage doubles

**Debuff:** Movement speed reduced by 15%

### Ranged Set
```json
{
  "id": "archer-boots",
  "name": "Archer Boots",
  "type": "armor",
  "rarity": "uncommon",
  "level": 1,
  "stats": {
    "speed_pct": 5,
    "defense": 2
  },
  "armor_set": "ranged",
  "armor_slot": "boots"
}
```

```json
{
  "id": "archer-pants",
  "name": "Archer Pants",
  "type": "armor",
  "rarity": "uncommon",
  "level": 1,
  "stats": {
    "speed_pct": 4,
    "defense": 3
  },
  "armor_set": "ranged",
  "armor_slot": "pants"
}
```

```json
{
  "id": "archer-vest",
  "name": "Archer Vest",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "speed_pct": 3,
    "defense": 4,
    "range_bonus": 15
  },
  "armor_set": "ranged",
  "armor_slot": "chest"
}
```

```json
{
  "id": "archer-hood",
  "name": "Archer Hood",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "speed_pct": 2,
    "defense": 5
  },
  "armor_set": "ranged",
  "armor_slot": "head"
}
```

```json
{
  "id": "archer-bow-amulet",
  "name": "Archer's Bow Amulet",
  "type": "armor",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "range_bonus": 25,
    "damage_pct": 8
  },
  "armor_set": "ranged",
  "armor_slot": "accessory"
}
```

**Ranged Set Bonus:**
- 2 pieces: +10% range, damage increases with distance
- 3 pieces: Damage bonus: +2% per unit distance from enemy (max 30%)
- 4 pieces: Bullets travel 20% faster
- 5 pieces: Distance bonus capped at 50%, melee attacks deal 50% less damage

**Debuff:** Melee damage reduced by 50%

### Sneaky Set
```json
{
  "id": "shadow-boots",
  "name": "Shadow Boots",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "speed_pct": 8,
    "defense": 2,
    "stealth": 5
  },
  "armor_set": "sneaky",
  "armor_slot": "boots"
}
```

```json
{
  "id": "shadow-pants",
  "name": "Shadow Pants",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "speed_pct": 6,
    "defense": 3,
    "stealth": 8
  },
  "armor_set": "sneaky",
  "armor_slot": "pants"
}
```

```json
{
  "id": "shadow-cloak",
  "name": "Shadow Cloak",
  "type": "armor",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "speed_pct": 4,
    "defense": 4,
    "stealth": 12,
    "invisibility_duration": 2
  },
  "armor_set": "sneaky",
  "armor_slot": "chest"
}
```

```json
{
  "id": "shadow-mask",
  "name": "Shadow Mask",
  "type": "armor",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "speed_pct": 3,
    "defense": 5,
    "stealth": 15
  },
  "armor_set": "sneaky",
  "armor_slot": "head"
}
```

```json
{
  "id": "shadow-amulet",
  "name": "Shadow Amulet",
  "type": "armor",
  "rarity": "legendary",
  "level": 1,
  "stats": {
    "stealth": 20,
    "crit_chance": 10,
    "backstab_damage": 50
  },
  "armor_set": "sneaky",
  "armor_slot": "accessory"
}
```

**Sneaky Set Bonus:**
- 2 pieces: +10% stealth, attacks on unaware enemies deal 25% more damage
- 3 pieces: Invisibility lasts 3 seconds, crit chance +5%
- 4 pieces: Backstab damage doubles, stealth regenerates 2/sec
- 5 pieces: Can attack while invisible, backstab damage triples

**Debuff:** Direct combat damage reduced by 20%

### Elemental Sets (Fire Example)
```json
{
  "id": "inferno-boots",
  "name": "Inferno Boots",
  "type": "armor",
  "rarity": "uncommon",
  "level": 1,
  "stats": {
    "speed_pct": 5,
    "defense": 2,
    "fire_damage": 10
  },
  "armor_set": "fire",
  "armor_slot": "boots"
}
```

```json
{
  "id": "inferno-pants",
  "name": "Inferno Pants",
  "type": "armor",
  "rarity": "uncommon",
  "level": 1,
  "stats": {
    "speed_pct": 4,
    "defense": 3,
    "fire_damage": 12
  },
  "armor_set": "fire",
  "armor_slot": "pants"
}
```

```json
{
  "id": "inferno-vest",
  "name": "Inferno Vest",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "speed_pct": 3,
    "defense": 4,
    "fire_damage": 15,
    "burn_duration": 3
  },
  "armor_set": "fire",
  "armor_slot": "chest"
}
```

```json
{
  "id": "inferno-helm",
  "name": "Inferno Helm",
  "type": "armor",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "speed_pct": 2,
    "defense": 5,
    "fire_damage": 18
  },
  "armor_set": "fire",
  "armor_slot": "head"
}
```

```json
{
  "id": "inferno-core",
  "name": "Inferno Core",
  "type": "armor",
  "rarity": "legendary",
  "level": 1,
  "stats": {
    "fire_damage": 25,
    "damage_pct": 15,
    "fire_resistance": 20
  },
  "armor_set": "fire",
  "armor_slot": "accessory"
}
```

**Fire Set Bonus:**
- 2 pieces: +15% fire damage, attacks apply burn
- 3 pieces: Burn damage increased by 50%, fire abilities cooldown -10%
- 4 pieces: Fire resistance 25%, ignite chance +10%
- 5 pieces: Fire damage capped at 200%, all damage types +10%

**Debuff:** Non-fire damage reduced by 25%

## Relics (20+ relics)

### Luck-Based Relics
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

```json
{
  "id": "monkeys-paw",
  "name": "Monkey's Paw",
  "type": "misc",
  "rarity": "legendary",
  "level": 1,
  "stats": {
    "luck": 6,
    "damage_pct": 8,
    "defense": -2
  },
  "behavior": {
    "type": "rerollable",
    "reroll_cost": 100,
    "max_rerolls": 3
  },
  "description": "Randomly buffs and nerfs stats. Rerollable for 100G."
}
```

### Functionality Relics
```json
{
  "id": "ricochet-amulet",
  "name": "Ricochet Amulet",
  "type": "misc",
  "rarity": "rare",
  "level": 1,
  "stats": {
    "damage_pct": 10,
    "luck": 2
  },
  "behavior": {
    "type": "bullet_modifier",
    "effect": "ricochet",
    "ricochet_count": 2,
    "ricochet_damage_reduction": 0.3
  },
  "description": "Bullets ricochet 2 times, losing 30% damage per ricochet."
}
```

```json
{
  "id": "sentinel-heart",
  "name": "Sentinel Heart",
  "type": "misc",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "luck": 5,
    "health": 18,
    "damage_pct": 7
  },
  "behavior": {
    "type": "minion_boost",
    "effect": "minion_defense",
    "defense_bonus": 50
  },
  "description": "Summons and minions gain 50% additional defense."
}
```

```json
{
  "id": "chaos-core",
  "name": "Chaos Core",
  "type": "misc",
  "rarity": "mythical",
  "level": 1,
  "stats": {
    "luck": 12,
    "damage_pct": 12,
    "speed_pct": 8
  },
  "behavior": {
    "type": "random_stat_boost",
    "roll_on_equip": true,
    "stats_to_modify": ["damage_pct", "speed_pct", "health", "luck"]
  },
  "description": "Randomly boosts stats when equipped. Unpredictable power."
}
```

### Enemy Control Relics
```json
{
  "id": "spawn-controller",
  "name": "Spawn Controller",
  "type": "misc",
  "rarity": "epic",
  "level": 1,
  "stats": {
    "luck": 4,
    "enemy_scale": 1.5
  },
  "behavior": {
    "type": "spawn_modifier",
    "effect": "increase_spawn_rate",
    "multiplier": 2.0,
    "reward_multiplier": 1.5
  },
  "description": "Doubles enemy spawn rate but increases rewards by 50%."
}
```

## Currencies (15+ currencies)

Already defined in `assets/currencies.json`. Add these:

```json
{
  "id": "blood_orb",
  "name": "Blood Orb",
  "symbol": "BO",
  "color": [180, 0, 0],
  "description": "A cursed orb dripping with blood. Dropped by melee kills.",
  "rarity": "rare",
  "drop_rate_modifier": 0.2,
  "value_multiplier": 30.0
}
```

```json
{
  "id": "star_dust",
  "name": "Star Dust",
  "symbol": "SD",
  "color": [200, 200, 255],
  "description": "Cosmic particles from celestial enemies.",
  "rarity": "epic",
  "drop_rate_modifier": 0.1,
  "value_multiplier": 80.0
}
```

```json
{
  "id": "soul_fragment",
  "name": "Soul Fragment",
  "symbol": "SF",
  "color": [100, 50, 150],
  "description": "A fragment of a defeated enemy's soul.",
  "rarity": "legendary",
  "drop_rate_modifier": 0.05,
  "value_multiplier": 400.0
}
```

```json
{
  "id": "mana_crystal",
  "name": "Mana Crystal",
  "symbol": "MC",
  "color": [100, 150, 255],
  "description": "Crystallized magical energy.",
  "rarity": "rare",
  "drop_rate_modifier": 0.15,
  "value_multiplier": 45.0
}
```

```json
{
  "id": "iron_coin",
  "name": "Iron Coin",
  "symbol": "IC",
  "color": [128, 128, 128],
  "description": "Common currency from basic enemies.",
  "rarity": "common",
  "drop_rate_modifier": 1.0,
  "value_multiplier": 0.5
}
```

```json
{
  "id": "platinum_nugget",
  "name": "Platinum Nugget",
  "symbol": "PN",
  "color": [225, 225, 225],
  "description": "A rare nugget from elite enemies.",
  "rarity": "epic",
  "drop_rate_modifier": 0.1,
  "value_multiplier": 120.0
}
```

```json
{
  "id": "quantum_bit",
  "name": "Quantum Bit",
  "symbol": "QB",
  "color": [255, 50, 255],
  "description": "A bit of reality itself. Endgame currency.",
  "rarity": "mythical",
  "drop_rate_modifier": 0.01,
  "value_multiplier": 10000.0
}
```

## Implementation Notes

1. All new items should be added to `game/systems/bazaar.py` in the `build_extended_catalog()` function
2. Armor sets need set bonus logic in `game/systems/armor_sets.py`
3. Relic behaviors need implementation in `game/systems/relics.py`
4. New currencies should be added to `assets/currencies.json`
5. Test all new content with deterministic seeds
