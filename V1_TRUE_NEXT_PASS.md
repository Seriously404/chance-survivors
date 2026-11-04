# V1.0 True: next implementation and investigation pass

This document follows [V1_TRUE_SYSTEMS.md](V1_TRUE_SYSTEMS.md). It records
findings from the first pass and is a working backlog, not a claim of release
readiness or a replacement for actual playtesting. Later player instructions
supersede older design assumptions.

## 1. Findings from the first pass

- Fixed-time gates were removed from rarity gambling, the relic market, fusion
  and crate reward selection. Currency, luck, inventory, ingredient and recipe
  level requirements remain. Rotating a daily offer is a refresh, not a
  requirement to wait before access to the economy.
- Eligible kills now increase the next eligible kill's score by a factor of
  1.05. The kill counter is saved, the multiplier is visible in the HUD and
  ordinary score remains separate from currency and XP rewards. A mathematical
  baseline calculation reaches the finite e308 milestone at roughly 14,440
  eligible kills. This is not a predicted or tested run duration; enemy
  availability, build damage, deaths and menus all affect real pacing.
- Enemy health scaling is now smooth instead of jumping tenfold at fixed
  intervals. A pressure director slows new spawns for low-health players and
  crowded screens, and a cap also applies to summoned enemies. This reduces
  pressure but does not prove that a player can never be overwhelmed. Crowd
  size, player mobility, ranged attacks and performance still require trials.
- A three-page, skippable introduction explains controls, Bazaar choices and
  building. It can be reviewed in the title codex. An optional in-run guide now
  tracks movement, dash, Bazaar browsing, inventory and choosing a combination
  base without requiring a purchase. It is transient and does not resume or
  replay in the middle of a saved run; assess whether persistence is needed.
- Hover information is available over visible item tiles in inventory,
  equipment, market, crate rewards and fusion views. Fusion tiles are no longer
  painted over their icons. Tooltips are clipped to the viewport and suppressed
  under the crate roll overlay. This needs actual mouse and resolution playtests
  across every panel and long translated description.
- Ricochet projectiles can find another target. Summons inherit combined damage,
  healing, explosion, homing, piercing and bounce effects. Elemental Core
  explosions apply the same resistance and lingering rules to secondary hits.
  Fire-tagged teleport combinations can leave finite damaging trails. Area
  supplements affect nova/siphon execution, telegraph and cast visual radius.
- Equipped abilities now contribute their advertised passive stats while
  equipped. A bounded, fading damage popup shows surviving enemies' health
  changes. Killed enemies are removed before the renderer observes them, so
  finishing-hit feedback still needs a combat-event pipeline.
- Large-number fixes cover rarity pool arithmetic, small spends at e308 and
  economy slider input with e309 balances. The economy uses finite 512-digit
  Decimal precision and the separate combat-number type uses different
  precision. Unbounded arithmetic, migration and consistent rounding remain
  open engineering work.
- Luck now increases the rarity-upgrade probability shown in the preview and
  used for the attempt. The same weighted probability is used for positions
  between rarity dots; the result is still a gamble, not a promised upgrade.
- Hybrid weapon/ability combinations now carry damage components through direct
  hits, explosions, area casts and summons, with individual elemental
  resistances. Quest progress records actual post-resistance elemental damage
  and successful purchases, combinations and fusions after acceptance.

## 2. Reproducible balance observations

A deterministic formula sample, not an automated player or a human playtest,
used 1,200 ms initial spawn delay, zero threat, 50 enemies and 10% player
health for the pressured case:

| Active minutes | Enemy health multiplier | Base delay | Pressured delay |
| ---: | ---: | ---: | ---: |
| 0 | 1 | 1,200 ms | 3,033 ms |
| 15 | 3.64 | 491 ms | 1,241 ms |
| 30 | 13.3 | 283 ms | 715 ms |
| 60 | 176 | 153 ms | 387 ms |
| 120 | 3.10e4 | 100 ms | 253 ms |

For one seeded daily crate selection the combined Epic/Legendary weight was
0% at luck 1, approximately 15.3% at luck 4, 21.6% at luck 10 and 23.9% at
luck 20. These figures describe that one crate pool, not the overall economy or
an observed player's acquisition rate. They were measured before later changes
to a separate rarity-upgrade luck formula; rerun them after future balancing.

The missing evidence is decisive: there is no validated build that survives to
14,440 kills, no measured average kills per second over an entire run, and no
human evidence that 15–120 minutes of play remain readable or enjoyable. Do not
claim that the milestone is practically reachable, fair or balanced yet.

## 3. Immediate integration and correctness checks

1. Test the real main loop through tutorial navigation, movement, dash, ability
   aim/release, a crate purchase and skip, equipment, combination, damage and
   save/resume. Use a temporary save and seed-controlled RNG; verify state and
   balances, not only that drawing completed.
2. Exercise a combined fire/teleport ability from input through effect emission,
   resistance-aware damage, expiry, death and one-time reward. Exercise the same
   trail tag on a moving summon and weapon projectile. Verify no additional
   damage occurs after a trail expires or the source is removed.
3. Exercise a sentry with healing, explosion, homing and piercing supplements
   through actual projectile movement and collision. Ensure cooldown, player
   bonuses and additive stats do not scale twice.
4. Check targeting of multiple enemies along a projectile's swept segment,
   collision ordering for piercing and ricochet, explosion impact position,
   lingering resistance and exact-once kill accounting.
5. Validate that held ability telegraphs, final cast radii and visuals agree
   for an uncombined and combined item at non-common rarity and item level.
   Verify UI previews do not mutate the live inventory graph.
6. Verify that running over the enemy cap cannot bypass it via group spawns or
   summoners, and that delayed spawning does not accumulate a hidden burst.
   Explore combinations of low health, ranged enemies, high movement speed and
   a crowded viewport instead of treating a cap alone as a fairness guarantee.
7. Confirm every failed purchase, fusion, exchange and gamble leaves the wallet
   and inventory unchanged. A successful gamble consumes funds exactly once;
   animated crate openings never reroll the purchased reward.
8. Check local saves and leaderboard payloads at damaged health and high score,
   with the counter that drives the score multiplier preserved. Test old save
   versions or explicitly report unsupported versions.

## 4. Interactive learning and player-facing information

Extend the optional, event-driven first-run guide.
Teach a movement input and dash without placing an unavoidable threat nearby.
Point to the Bazaar and show the cost/balance explanation. Highlight how to
inspect a crate; do not require opening one or consume currency automatically.
Explain that odds are probabilistic, the chosen reward is committed at click,
and animation can be skipped. Finally demonstrate equipment and a
combination preview. Each prompt needs Back, Skip and a way to reopen the guide.
The guide must pause while menus are paused and must not become impossible
when the player starts with a previous save.

A tooltip should show name, type, base/current rarity, level, computed stats,
relevant cooldown, description, combination status and an actionable reason for
an invalid drop. Show additive and multiplicative contributions separately.
Prevent long item or quest text from being truncated without a way to read it.
Audit the codex crate preview: it currently does not expose every reward when a
crate has more than eight; add scroll or pagination and show the same odds as
the active shop context. Ensure labels explain that a title-screen odds sample
is not necessarily the odds for a live build.

## 5. Effects and content model

Create an inventory of every definition and its promised effect. Classify each
as executable, descriptive-only, conflicting, duplicate or unreachable. Do not
create fake “unique” effects that only change metadata. For each tag, specify
eligible base types, trigger, target, chance, duration, stacking, damage source,
interactions, visual/audio feedback, serialization and computational bounds.
Add one integration case per distinct behavior rather than one superficial test
per copy of the same template.

Expand the tag handlers for projectiles, moving summons, area casts, teleports,
armor and relics. Explicitly describe unsupported combinations in preview
rather than promising an effect that the runtime drops. Give new or existing
items distinct roles and tradeoffs, with longer cooldowns where strength
warrants them. Compare a manually upgraded common item with naturally rarer
items at the same final rarity and level; check both opening power and long-run
investment. Preserve original rarity and provenance through crate purchase,
fusion, save/load and leaderboard serialization.

## 6. Economy, progression and pressure experiments

Build a headless automated player harness, separate from the shipped loop,
that records active time, kills, damage dealt and taken, enemy counts,
currencies, loot/upgrade choices, items and causes of death. Start with fixed
seeds and a handful of policies: basic rifle/fireball, careful movement,
ability/summon build and an upgraded build. Include deliberate bad luck and an
idle player. Repeat enough seeds to report distributions, not a single
anecdote. Profiles should cover at least the first 15 minutes and separately
stress extreme numbers and entity counts.

Measure when the first equipment, rarity upgrades, main quest and fusion become
available under those policies. Tune costs, loot weights and pressure in concert;
never reintroduce “wait until minute N” as an upgrade gate. Test 1–2 hour targets
as hypotheses only. A readable run can still end when the player makes mistakes;
use warning, recovery and counterplay instead of claiming mathematical
invulnerability. Assess whether the 60-enemy cap unfairly suppresses score or
summon play, and scale by proximity/visibility if a simple global cap is too
blunt.

At two hours, the sampled enemy health multiplier was approximately 3.1e4;
the score multiplier follows kill count instead. These curves serve different
purposes. Check damage throughput against enemy effective health before tuning
either. Guard large integers in spawn, score, inventory, chance and UI paths;
profile the cost of 512-digit arithmetic, sorting swept collisions and rendering
large crowds at supported resolutions.

## 7. Validation and completion criteria

A pass is complete only after the entire headless unittest suite, editor
problems, a real event-driven game launch and relevant focused regressions pass.
Run API checks independently. Use temporary save/database paths and never delete
player data as a test fixture. Document reproducible commands and note any
third-party deprecation warnings.

An eventual release decision also needs a documented balance report, real
human sessions, accessibility/readability checks at supported resolutions,
performance measurements, integrity checks of saves and all economy actions,
and a description-to-runtime audit. Report defects and unverified assumptions
as such. After this pass, repeat the audit and write the next plan from evidence.
