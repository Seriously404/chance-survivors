# Catalog-to-runtime audit: V1.0 True

This audit records the live merged catalog, rather than assuming every historical
asset definition is authoritative. It is an implementation inventory and a list
of remaining defects, not a release or balance certificate.

## Concrete corrections in this pass

- Real elemental damage abilities now declare `elemental` and their element tags.
  The hybrid rules previously worked in synthetic tests while silently failing
  for Nature Seed, Ember Wand and most other real catalog spells. Real Nature
  Seed/rifle combinations now deliver separately resisted nature and arcane
  damage in both combination directions.
- Inferno Core adds finite fire trails when combined with a compatible weapon,
  projectile ability, moving sentry or teleport. It remains a passive damage/luck
  relic when simply owned. Existing trail caps and two-second lifetimes apply.
- Flame Blaster now implements its promised fire aftermath with finite fire
  trails on each of its six pellets. It does not promise a separate enemy burn
  status or unlimited ground fire.
- The compatibility relic factory now reads the actual relic asset, preserves
  tags and descriptions, excludes the historical armor entry, and returns fresh
  instances. Its old descriptions promised randomized penalties, repeated hits
  and on-cast fortune that the live runtime did not execute.
- Relic summaries use live item level and rarity calculations instead of showing
  unscaled base stats.

## Runtime guarantees and remaining limits

1. Critical chance now executes for direct projectile and area hits, including
   summon projectiles and explosion targets. One roll per target hit can double
   every resolved damage component once; chance is clamped to 0–100 percent.
   Trails and lingering damage do not roll critical hits.
2. Owned `healing_pct` now changes actual health restoration from healing casts
   and damage-to-health conversion, including supported combined projectiles,
   summons and area siphons. It scales the actual damage-derived healing once,
   clamps to missing health, and deliberately does not change shields.
3. Equipped `elemental_dmg` now changes each nonphysical damage portion once,
   before resistance. It reaches weapon, spell, summon and secondary explosion
   hits, finite trails and Elemental Core lingering. Physical portions do not
   receive an elemental bonus. Active effects snapshot the bonuses at creation.
4. Sneaky armor names/descriptions imply stealth. There is no stealth mechanic.
   Do not label ordinary speed or luck bonuses as working enemy concealment.
5. Most armor and relics have only numeric identity. They do not yet satisfy
   the requested unique transferable behavior per item. Metadata is not an effect.
6. A summon ability used as a supplement does not automatically create a summon
   on a weapon hit. Likewise a ward supplement does not automatically add a
   shield trigger. Preview must describe only the runtime transfers implemented.
7. Owned relic passives now apply exactly once even while a relic is assigned
   as a supplement. Active combined abilities/armor exclude the relic's passive
   contribution traces before owned totals are added. Weapon local critical
   chance excludes those same traces before global chance is added. Weapon
   supplement luck and critical chance remain globally available. Tags and
   nonpassive delivery stats such as area radius still transfer to the base.
   Numeric-only relics do not gain a second passive simply through assignment.
   Mathematical combination traces retain all sources for inspection; previews
   must distinguish the globally owned passive scope from local special effects.
8. Primary ordinary ability damage rounds resistance results to integers while
   large-number hybrid components retain fractional damage. The real catalog
   regression captures the current distinction; unifying rounding is separate.
9. Elemental Core is a fusion product and is not in this raw catalog. Fusion
   generation, market filtering and save provenance need their own audit.
10. This is not a full validation of every rarity, combination direction, armor
    set threshold, save migration or controller/mouse path.

## Executable transfer rules and bounds

| Tag / source | Trigger and valid target | Current bounds / evidence |
| --- | --- | --- |
| `elemental` damage ability | Weapon supplement adds a separately resisted damage component; elemental ability base can inherit weapon damage | Real Nature Seed and rifle tested both directions |
| `trail:fire` | Moving projectile or sentry emits ground damage; teleport emits a path | Two seconds per patch, 150 global patches, 24 samples per teleport segment; source removal does not prolong patches |
| `ricochet` | Combination rule adds bounce count; projectile redirects to another unhit living target | Count finite; movement/collision and existing focused tests cover redirect |
| `homing` | Combination rule adds steering to projectiles | Steering rate bounded by projectile configuration; does not summon anything |
| `explosive` | Combination rule adds area radius | Projectile explosion handles nearby secondary targets; no infinite recursion |
| Healing supplement script | Successful supported combined damage can heal for actual damage dealt | Health clamped to player maximum; not a shield or universal regeneration |
| Owned relic numeric stats | Player passive aggregation | Level/rarity scaled; active modifiers use the consumers described above |

## Per-definition inventory

“Wired” means the handler exists, not that every item was individually playtested.
An entry without a unique tag/handler is deliberately listed as numeric-only.
The last column calls out known unsupported claims or dormant stats.

| Definition | Type | Runtime role / executable identity | Known gap |
| --- | --- | --- | --- |
| starter-rapid | weapon | Wired projectile: rapid_fire | Not individually playtested |
| starter-heavy | weapon | Wired projectile: heavy_shot | Not individually playtested |
| ember-lance | weapon | Wired projectile: rapid_fire | Not individually playtested |
| azar-saber | weapon | Wired projectile: heavy_shot | Not individually playtested |
| storm-spool | weapon | Wired projectile: rapid_fire | Not individually playtested |
| arc-rifle | weapon | Wired projectile: rapid_fire | Not individually playtested |
| lantern-sniper | weapon | Wired projectile: heavy_shot | Not individually playtested |
| plasma-cannon | weapon | Wired projectile: rapid_fire | Not individually playtested |
| storm-splitter | weapon | Wired projectile: rapid_fire | Not individually playtested |
| void-piercer | weapon | Wired projectile: heavy_shot | Not individually playtested |
| flame-blaster | weapon | Wired projectile: shotgun; transfer trail:fire | Not individually playtested |
| homing-devastator | weapon | Wired projectile: homing | Not individually playtested |
| starter-vest | armor | Equipped numeric passives | no distinct executable behavior |
| starter-boots | armor | Equipped numeric passives | no distinct executable behavior |
| starter-plate | armor | Equipped numeric passives | no distinct executable behavior |
| starter-hood | armor | Equipped numeric passives | no distinct executable behavior |
| starter-gloves | armor | Equipped numeric passives | no distinct executable behavior |
| titan-plate | armor | Equipped numeric passives | no distinct executable behavior |
| starlit-hood | armor | Equipped numeric passives | no distinct executable behavior |
| ghost-boots | armor | Equipped numeric passives | no distinct executable behavior |
| sunforge-plate | armor | Equipped numeric passives | no distinct executable behavior |
| gale-sandals | armor | Equipped numeric passives | no distinct executable behavior |
| sunspire-shield | armor | Equipped numeric passives | no distinct executable behavior |
| sentinel-heart | armor | Equipped numeric passives | no distinct executable behavior |
| bulwark-helm | armor | Equipped numeric passives; set bulwark | no distinct executable behavior |
| bulwark-chest | armor | Equipped numeric passives; set bulwark | no distinct executable behavior |
| bulwark-greaves | armor | Equipped numeric passives; set bulwark | no distinct executable behavior |
| bulwark-charm | armor | Equipped numeric passives; set bulwark | no distinct executable behavior |
| windrunner-hood | armor | Equipped numeric passives; set windrunner | no distinct executable behavior |
| windrunner-coat | armor | Equipped numeric passives; set windrunner | no distinct executable behavior |
| windrunner-boots | armor | Equipped numeric passives; set windrunner | no distinct executable behavior |
| windrunner-token | armor | Equipped numeric passives; set windrunner | critical hit chance active; no distinct executable behavior |
| speedster-helm | armor | Equipped numeric passives; set speedster | no distinct executable behavior |
| speedster-vest | armor | Equipped numeric passives; set speedster | no distinct executable behavior |
| speedster-boots | armor | Equipped numeric passives; set speedster | no distinct executable behavior |
| speedster-gloves | armor | Equipped numeric passives; set speedster | critical hit chance active; no distinct executable behavior |
| tank-helm | armor | Equipped numeric passives; set tank | no distinct executable behavior |
| tank-plate | armor | Equipped numeric passives; set tank | no distinct executable behavior |
| tank-leggings | armor | Equipped numeric passives; set tank | no distinct executable behavior |
| tank-amulet | armor | Equipped numeric passives; set tank | no distinct executable behavior |
| ranged-helm | armor | Equipped numeric passives; set ranged | no distinct executable behavior |
| ranged-vest | armor | Equipped numeric passives; set ranged | no distinct executable behavior |
| ranged-boots | armor | Equipped numeric passives; set ranged | critical hit chance active; no distinct executable behavior |
| ranged-ring | armor | Equipped numeric passives; set ranged | critical hit chance active; no distinct executable behavior |
| sneaky-hood | armor | Equipped numeric passives; set sneaky | critical hit chance active; stealth description unsupported; no distinct executable behavior |
| sneaky-robe | armor | Equipped numeric passives; set sneaky | critical hit chance active; no distinct executable behavior |
| sneaky-boots | armor | Equipped numeric passives; set sneaky | stealth description unsupported; no distinct executable behavior |
| sneaky-amulet | armor | Equipped numeric passives; set sneaky | critical hit chance active; no distinct executable behavior |
| elemental-helm | armor | Equipped numeric passives; set elemental | nonphysical damage effectiveness active; no distinct executable behavior |
| elemental-robe | armor | Equipped numeric passives; set elemental | nonphysical damage effectiveness active; no distinct executable behavior |
| elemental-boots | armor | Equipped numeric passives; set elemental | nonphysical damage effectiveness active; no distinct executable behavior |
| elemental-ring | armor | Equipped numeric passives; set elemental | nonphysical damage effectiveness active; no distinct executable behavior |
| dash-boots | ability | Wired cast: dash | Not individually playtested |
| starter-charm | ability | Wired cast: nova | Not individually playtested |
| starter-core | ability | Wired cast: heal | Not individually playtested |
| ember-wand | ability | Wired cast: ember; transfer trail:fire | Not individually playtested |
| warding-sigil | ability | Wired cast: ward | Not individually playtested |
| void-bloom | ability | Wired cast: void | critical hit chance active |
| glass-cascade | ability | Wired cast: projectile | Not individually playtested |
| cinder-ward | ability | Wired cast: nova | Not individually playtested |
| frost-lantern | ability | Wired cast: frost | Not individually playtested |
| nature-seed | ability | Wired cast: projectile | Not individually playtested |
| nova-blast | ability | Wired cast: nova | Not individually playtested |
| healing-light | ability | Wired cast: heal | Not individually playtested |
| sentinel-summon | ability | Wired cast: sentinel | Not individually playtested |
| turret-deploy | ability | Wired cast: turret | Not individually playtested |
| blink-step | ability | Wired cast: teleport | Not individually playtested |
| starter-fire-rune | ability | Wired cast: projectile | Not individually playtested |
| cinder-burst | ability | Wired cast: projectile | Not individually playtested |
| frost-needle | ability | Wired cast: frost | Not individually playtested |
| arcane-ricochet | ability | Wired cast: projectile | Not individually playtested |
| healing-spark | ability | Wired cast: heal | Not individually playtested |
| menders-ward | ability | Wired cast: mend_ward | Not individually playtested |
| shadow-siphon | ability | Wired cast: siphon | Not individually playtested |
| starter-teleport-sigil | ability | Wired cast: teleport | Not individually playtested |
| lucky-box | relic | Owned numeric passives | critical hit chance active; no distinct executable behavior |
| monkeys-paw | relic | Owned numeric passives | critical hit chance active; no distinct executable behavior |
| echo-prism | relic | Owned numeric passives | critical hit chance active; no distinct executable behavior |
| iron-nest | relic | Owned numeric passives | no distinct executable behavior |
| glass-heart | relic | Owned numeric passives | health restoration effectiveness active; no distinct executable behavior |
| void-bell | relic | Owned numeric passives | critical hit chance active; no distinct executable behavior |
| lucky-box-legendary | relic | Owned numeric passives | no distinct executable behavior |
| chaos-core | relic | Owned numeric passives | no distinct executable behavior |
| moon-sigil | relic | Owned numeric passives | no distinct executable behavior |
| inferno-core | relic | Owned numeric passives; transfer trail:fire | Not individually playtested |
| shimmer-petal | relic | Owned numeric passives | no distinct executable behavior |
| ricochet-amulet | relic | Owned numeric passives; transfer ricochet | Not individually playtested |
| sentinel-heart-relic | relic | Owned numeric passives | no distinct executable behavior |
| ember-gloves | armor | Equipped numeric passives | no distinct executable behavior |
| sentry-lattice | relic | Owned numeric passives | no distinct executable behavior |
| starter-relic | relic | Owned numeric passives | no distinct executable behavior |
| starter-token | relic | Owned numeric passives | no distinct executable behavior |
| starter-grenade | relic | Owned numeric passives; transfer explosive | Not individually playtested |
| starter-homing-lens | relic | Owned numeric passives; transfer homing | Not individually playtested |
| starter-ricochet-chip | relic | Owned numeric passives; transfer ricochet | Not individually playtested |

## Reproduction

Run the focused regressions with the configured project interpreter:

```sh
python -m unittest tests.test_live_catalog_interactions tests.test_trails tests.test_relic_system tests.test_hybrid_attacks -v
```

The seven new live-catalog cases verify tags, actual combined resisted hits in
both directions, the finite Inferno Core trail, Flame Blaster pellet tags,
factory detachment and scaled summaries. Existing trail and hybrid tests
bring this focused command to 14 passing cases. This number does not describe
a full-suite run or a human session.

## Follow-up effectiveness validation

The follow-up tests use the real Elemental Helm and Glass Heart catalog records
through inventory equipment and owned passives, then execute gun hits and healing
casts. Additional cases cover separately resisted physical/elemental hybrid
portions, explosion overkill healing, area siphon scaling, summon propagation,
shield exclusion, huge-number health clamping and invalid percentage rejection.

```sh
python -m unittest tests.test_combat_effectiveness tests.test_critical_hits -v
```

Health effectiveness is not a new healing source. A weapon without a healing
supplement still cannot heal; owning Glass Heart cannot create a shield or
healing cast. Elemental effectiveness does not magnify physical damage merely
because an item also has an elemental tag. Damage bonuses, elemental bonuses,
critical outcomes, resistance and actual health lost remain separate stages.

## Owned passive scope regression

```sh
python -m unittest tests.test_relic_passive_scope -v
```

These cases compare active abilities before and after relic assignment at
Common, Legendary and Ultimate rarity; verify the weapon still receives the
owned relic's luck and critical chance exactly once; preserve a weapon's own
critical chance and relic explosion radius; and verify non-relic ability
supplement passives still transfer. Reading the local effective stat must not
mutate the preview or its contribution traces.

## Engineering defense and finite support restoration

The Engineer main quest introduces a separate relay objective. Enemies direct
movement and aimed attacks toward the relay; intact walls intercept approaches
that cross their footprint. Contact attackers remain alive and strike on a
cooldown. Friendly repair projectiles never damage enemies, including through
transferred trail tags. A repaired target cannot exceed maximum health or be
revived after destruction.

Deployments share a six-structure cap and must be placed on clear ground within
3.5 world units of the player. Walls absorb attacks but never fire. Relay Turret
provides ordinary shots; Arc Relay bounces, Furnace Sentry explodes and Cryo
Ballista pierces. Their structure health and finite service lifetime preserve a
need to repair, replace and reposition defenses. Fire trails, healing budgets,
critical chance and hybrid damage propagate through supported sentry shots.

Overclock doubles nearby turret firing rate for four seconds. Field Repair
restores 15% maximum health to nearby structures and the relay, affected by
health-restoration bonuses. These casts require valid targets. Architect Protocol
is an Ultimate fusion earned with high-level Mythical ingredients and an
Elemental Core; it doubles nearby structures' firing rate and shot damage for
eight seconds, with at least 60 seconds of recovery. It does not create immortal
defenses or resurrect a failed relay. This is implemented behavior, not a proof
that the mode's pacing is balanced.

Engineer waves advance through eligible kills, beginning with 12 kills and
adding five per subsequent wave. The relay increases maximum health by 12% per
completed wave while preserving its current health fraction. No elapsed-time
upgrade unlock is involved. Damage, active buffs, structures, wave progress and
remaining shared healing budgets survive the defense snapshot round trip.

Healing supplements now provide one finite restoration pool derived from the
combined item's scaled, investment-weighted heal amount. Projectiles share this
pool across hits, bounces and explosion targets; shotgun pellets share a volley
pool; summon projectiles share their source cast's pool. Area spells share a
pool across targets. Actual health lost limits on-damage restoration; healing
effectiveness scales restoration once. Standalone healing casts and the native
Shadow Siphon behavior retain their own effects. A synthetic low-level projectile
with an explicit healing flag but no budget remains compatible with the helper
API; inventory-generated combined attacks always receive their finite pool.

```sh
python -m unittest tests.test_engineering tests.test_healing_budget tests.test_supplement_progression -v
```
