# Chance Survivors: V1.0 True systems and implementation guide

This is a working design and verification document, not a claim that every
feature below is already implemented. The latest player instructions take
precedence over earlier design notes. In particular, access to power is based on
player progress and choices, not a required number of minutes; real-time crate
rotation is a refresh mechanism and must not prevent progression.

## 1. Experience and creative direction

The player survives an escalating arena, earns currencies and experience,
chooses a build, and turns modest components into surprising abilities. The
aspiration is a sustained run approaching the finite score milestone of
1.7976931348623157e308. A run should keep its identity as numbers become large:
exponential progress is meaningful only when attacks, opponents, decisions and
feedback remain understandable.

The opening prioritizes learning to move, dash, fire and cast. The starter rifle
and a simple single-target fireball are dependable, comprehensible baselines.
The middle game makes a player choose an approach: abilities, weapons, armor,
summons and relic interactions should invite experimentation. The late game
should combine effects and score multipliers without becoming a lottery in
which the player cannot understand why they won or lost.

No game can guarantee a player is never overwhelmed by every possible input,
performance setting or build. The implementable requirement is that pressure
has readable warnings, reasonable counters, bounded computational costs and a
recovery path; difficulty changes should be measured in reproducible scenarios
and human playtests rather than asserted by formula.

## 2. Run lifecycle and controls

- Name entry belongs to the title screen. Movement and text input must never
  corrupt each other or survive a state transition as stuck keys.
- Explain controls and the first meaningful decisions before a run. Preserve a
  way to review the tutorial later, and make each step brief and skippable.
- WASD moves; space performs a directional dash. If no movement key is held,
  use the aim direction. A single equipped dash ability replaces the default
  dash and shares its cooldown between Space and its numbered key.
- Mouse aims; the two mouse buttons fire their respective equipped weapons.
  Holding a numbered ability key previews its trajectory, range or destination;
  releasing it casts if it is ready.
- Opening a gameplay menu pauses simulation and the active run timer. Menu
  navigation and animations must not advance enemy movement, rewards or quest
  timers. Escape/save and resume must behave consistently.
- A result screen explains the score and lets the player explicitly choose to
  upload it. Offline or disabled services are reported clearly and must not
  break local play.

## 3. Item model, identity and inspection

An item instance is a weapon, ability, armor piece or relic. Armor has boots,
pants, chestplate, headpiece and accessory positions. Preserve stable definition
and instance identifiers, original/base rarity, current rarity, level,
ultimate subtier, tags, script, description, combinations and fusion provenance
through acquisition, upgrades, saves and leaderboard submissions.

Every item needs a truthful description of what its base form does, an icon
that makes its category recognizable without reading, and accessible detail
and hover views. A preview should identify base stats, scaled stats, cooldowns,
element, added effects, source items and limitations. Show meaningful action
prompts, costs and available balances before committing. Do not expose internal
script names to players as though they were effects.

The starter and low-base-rarity items should retain useful growth potential.
A high-base-rarity item offers convenient immediate strength, while investment
in an ordinary item can produce a competitive build. Original rarity must not
be silently overwritten on upgrade. Compare equivalent builds with actual
combat tests, not rarity labels alone.

## 4. Ability system and combat effects

Ability definitions live in JSON and name their behavior implementation.
Scripts must produce real gameplay effects, not merely labels in a preview.
A cast validates the equipped item, target, cooldown and resources before it
mutates the world; invalid casts report why and do not consume a cooldown.
More powerful effects generally deserve longer cooldowns, subject to deliberate
synergies that accelerate recovery. The Sandevistan is an endgame fusion: a
dash with short-lived slowed world time, accelerated movement and quicker
ability recovery; the effect and cooldown must be clear to the player.

Projectile, area, heal, ward, teleport and summon effects each need visible
telegraphs and a clear point of impact. Telegraphs must match actual target
coordinates and work with a smoothly following camera. The player, enemies,
projectiles, summons and world-space effects must share the same coordinate
transform. Movement and hostile projectiles remain readable during slowdown.

Tags describe reusable mechanics. An elemental `trail:fire` contribution should
cause a moving compatible projectile or summon to leave a temporary fire
hazard; the hazard has bounded lifetime and count, damages enemies at a known
rate, honors resistance, awards kills once and does not consume unbounded
memory. Other mechanics such as homing, explosion, piercing, healing-on-damage,
ricochet and teleport trails should be carried by tags or behavior definitions
and actually execute for every supported base type. Avoid advertising an
interaction when no runtime implementation exists. Clearly define whether an
interaction stacks, refreshes, replaces or conflicts with another.

The player should see attack direction, effect radius, impact, cooldown, enemy
health changes and damage sources. Animations should make actions legible,
not hide the battlefield or misrepresent an already committed transaction.
Support reduced visual intensity where practical and preserve the distinction
between decorative particles and damaging areas.

## 5. Combinations

A combination has one base and ordered supplemental items. Rarity determines
capacity. Equipped items cannot be consumed as supplements; supplements cannot
be reused in multiple bases or themselves contain a combination. Armor may
combine with armor, subject to explicitly defined exceptions such as the
Elemental Core. Validate graphs before modifying them, and restore them without
silently corrupting ownership.

Changes are hot-swappable: assigning or removing a component immediately
updates preview and runtime effects. Base stats receive additive level growth,
then rarity multiplication. Supplements contribute through the same documented
pipeline. Generic contributions should remain logical when no special rule
applies. An elemental ability plus an explosive component should have a real
area effect; a healing ability combined with a damaging cast should heal based
on damage actually dealt, capped by missing health. Explicit behaviors need
integration tests for both application and removal.

## 6. Fusion

Fusion consumes a validated set of eligible, unequipped, uncombined instances
and creates a new item unavailable through normal purchases or crate drops.
Show recipes, output, ingredient types/tags/rarities/levels, progress-based
requirements and compatible inventory items in a codex. The crafting table
should accept deliberate ingredient choices, validate every slot, present
errors without partial consumption, and show the result after successful
creation. Save provenance for inspection and the leaderboard.

Early fusions should be accessible with a small build; more demanding outputs
require increasingly meaningful player progress and materials. The Elemental
Core uses one ability of each element, supplies elemental resistance to armor,
reduces target resistance on compatible attacks and can apply bounded lingering
elemental effects. Its rarity and level control probabilities and capacity.
Its use in later fusions must not make the core available from ordinary shops.

## 7. Rarity, level and mathematical growth

Rarity is a multiplier; item levels add configured contributions before the
rarity multiplier. Ultimate has subtiers and the same upgrade path must preserve
combinations and identity. A rarity pool accepts multiple currencies with
favorable, normal and unfavorable affinities. The player may select a
continuous mixture between adjacent targets; the displayed success probability
and outcome distribution must match the committed random draw. Funds are spent
once on an attempted gamble and never on validation failure.

Progression and unlocks are earned by levels, builds, quest milestones or
other player actions. Remove requirements that simply say “wait N minutes”.
Make the path through Mythical meaningful instead of letting a player skip
directly to Ultimate. A progress-gated target should explain what remains to
unlock. Difficulty, investment and expected rewards need measured relationships
so players can form a build without grinding an opaque wall.

Use the project's large-number representations consistently. Damage, health,
score, currencies, XP, rarity and level upgrades must be finite, ordered,
serializable and safe beyond ordinary float range. Exponential enemy and score
growth must not overflow via an accidental float or giant integer conversion.
Avoid a hidden cap that makes late progression stop while still displaying a
larger number. The finite infinity milestone is a milestone, not actual infinity.

## 8. Enemies, pressure and fairness

Enemy roles should be distinct: basic pursuers, faster turn-limited threats,
slow durable enemies, ranged shooters, stealth variants, elemental enemies,
swarms, summoners and bosses. Each major threat has identifiable visuals,
legible health and a counterplay opportunity. Spawn groups and delayed attacks
must not appear directly on top of the player without warning. Minions that do
not award rewards must be distinguishable if their presence affects decisions.

Start gently, then increase pressure with progress and build strength. A horde
can be dense without being unfair: protect minimum safe space, bound off-screen
spawns, avoid sudden damage spikes and keep performance stable. Dash and escape
should have predictable movement and cooldowns; no invisible invulnerability
or unavoidable overlapping attacks. Tune spawn rate and enemy strength against
realistic starter, mixed and endgame builds using seeded simulations, then
verify those conclusions through human playtests.

Fast projectiles use swept collision, resolved in travel order; no shot should
pass through a target just because its speed or the frame time increased.
Explosions and healing-on-hit use the true impact and actual damage. Prevent
projectile speed from scaling into unusable values while keeping its upgrade
feedback understandable.

## 9. Currency and Bazaar

Enemies have clear currency sources and the player can inspect each currency's
balance, worth and intended use. All cost displays show both owned and required
amounts with readable icons. No purchase can spend a negative amount, duplicate
funds, accept unavailable offers or add an item when inventory is full.

Crates show possible rewards and actual probabilities for the current luck and
progress, including an explanation of unavailable outcomes. Base legendary
items should be rare, but an unlucky player should still have a path forward.
The selected reward and payment are committed atomically when purchasing;
opening animation is cosmetic and skippable, with the same final item either
way. Seeded tests must reproduce outcomes.

The room groups elemental crates and other box types. A daily box may refresh
its randomized selection every active minute, but its availability is not a
mandatory timing gate. Display refresh timing, offer identity and remaining
costs. If offers rotate during an open selection, invalidate or refresh the
selection safely. Make each currency useful in a deliberate purchase, exchange,
upgrade or mechanic, and avoid creating currencies that never enter the run.

The relic market sells relics only, excludes fusion-only outputs and clearly
explains passive and combination effects. Currency exchange has a visible
source, destination, relative value, fee, amount and quote. Rarity and level
upgrades show a preview, target, chance, total spending and wallet balances.

## 10. Quests and player agency

Side quests are offered, not automatically accepted; track progress only after
acceptance, show a bar and retain the card's position. Main quest choice offers
three mutually exclusive build paths or the explicit choice to skip. A completed
main quest applies its score exponent; side quests provide percentage bonuses.
Restriction checks cover equipped bases and supplements, survive save/load and
cannot be circumvented after acceptance. Never offer an impossible objective:
all progress conditions must be connected to actual game events.

## 11. Tutorial, menus and accessibility

The first-run introduction teaches movement, dash, shooting, aiming and ability
casting. Introduce the Bazaar through an actionable, skippable sequence: earn a
small currency amount, open the shop, inspect a crate and understand costs,
select or purchase one when affordable, equip an item and preview a
combination. The tutorial must never require gambling success, consume the
player's items without consent or block experienced players. Explain how to
revisit these instructions in the codex.

Hovering an item shows a concise tooltip anchored on-screen with rarity, type,
level, effect and current status. It must work on equipment, inventory,
combination, fusion, market and crate-reward views where an item is visible.
Keep selected details accessible independently of hover, and make the hover
hitbox match the clipped visual item after scrolling.

Use consistent typography, contrast and spacing. Keep currency icons next to
balances and costs without depending on color-emoji availability. Ensure text
wraps within its panel, supports the minimum resolution and remains legible
at larger resolutions. Interaction feedback must be visually distinct from
combat. Prefer wheel/keyboard scrolling with visible progress, bounded lists,
clipped hitboxes and frame-rate-independent interpolation.

## 12. Save, API and integrity

Autosave a damaged player and large-number values without losing precision.
Validate versions, ownership graphs and all restored values before replacing a
live run. Preserve permanent progress and choices; describe transient world
state that intentionally does not persist. A failed save must remain visible.

Leaderboard submissions are explicit. Store enough item and build detail to
reconstruct a run, including tags and combinations. Handle disabled/unreachable
servers gracefully. The local API should present the leaderboard at `/` and
interactive API documentation at `/docs`; administrative deletion requires a
configured secret and must never be anonymously available.

## 13. Verification and acceptance

For every feature, include tests of the player-visible path, invalid inputs,
transactions and save round trips where relevant. Test pygame UI with a dummy
video/audio driver and real events, not just imports. Exercise a controllable
run that moves, dashes, fires, casts, opens the Bazaar, buys a crate, equips an
item, makes a combination, upgrades it and resumes a damaged save.

Use fixed RNG seeds to validate crate probabilities, progression gates and
upgrade distributions. Record actual elapsed gameplay, enemy count, damage,
items, resources and deaths over starter and later-build simulations; report
assumptions and distinguish simulated estimates from real-player feedback.
Check both small and extreme values and guard against runaway entity counts.
Run the complete unittest suite, editor diagnostics, and a headless launch.

## 14. Pass sequence and open work

1. Audit existing implementation against this guide and record verified gaps.
2. Replace time-only gates with progress checks; expose their requirements.
3. Make the ability and combination runtime obey advertised tags and effects.
4. Add hover inspection and contextual feedback across item-bearing interfaces.
5. Teach the first Bazaar loop without forcing a gamble; add replay/skip.
6. Measure progression, enemy pressure, economy and performance with seeded
   scripted scenarios, then adjust using those observations.
7. Run an integration and regression pass. Record actual limitations and create
   the next detailed pass document from findings, rather than labeling
   unfinished work as complete.
