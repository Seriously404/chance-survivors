# V1.0 True: pass 03 evidence, integration and next decisions

This pass continues [V1_TRUE_NEXT_PASS.md](V1_TRUE_NEXT_PASS.md). The system
contract remains [V1_TRUE_SYSTEMS.md](V1_TRUE_SYSTEMS.md). This is a record of
verified changes and open decisions, not a release certificate or a claim that
an automated policy is equivalent to a human player.

## 1. Work completed

### Catalog behavior is now tested from actual definitions

The content audit exposed a distinction between synthetic combination tests and
actual content. Most real elemental damage abilities did not carry the tags
that activate hybrid rules. Nature Seed and other damage definitions now declare
those tags, and tests acquire their real catalog records, combine them and hit
resistant targets in both directions. The same path verifies that damage
components are not multiplied twice.

Inferno Core now transfers finite fire trails. Flame Blaster leaves the fire
aftermath its description promises. The relic compatibility factory reads the
canonical asset definitions instead of maintaining a second, contradictory
catalog. Descriptions no longer promise random penalties, extra attacks or
summons where no runtime handler exists. The per-definition audit remains
explicit about numeric-only items and mechanics still absent from the game.

### Dormant combat stats have real consumers

- Critical chance is a percent, capped at 100%. Each direct target hit can deal
  twice its resolved damage once. It applies to weapon, ability, area,
  explosion and summon hits. Trails and lingering damage do not repeatedly
  roll criticals. Orange CRIT feedback distinguishes surviving critical hits.
- Elemental damage effectiveness applies only to nonphysical components,
  before each component's resistance. The same creation-time snapshot reaches
  projectiles, summons, secondary explosions, trails and core lingering.
- Healing effectiveness applies to actual health restoration, including
  damage-to-health effects, with a cap at missing health. It does not silently
  strengthen shields. Actual damage, rather than nominal overkill, drives
  damage-derived healing and elemental quest attribution.
- Owned relic passive stats count globally once, including while assigned to
  a base. Active combined gear excludes those same relic contribution traces
  from local passive totals. Special tags and nonpassive effects such as area
  radius still transfer. This retains weapon-supplement luck and critical
  bonuses without granting them a second time.

These rules are exercised with deterministic RNG, mixed damage components,
resistant enemies, summons, healing, extreme values and real inventory records.
They do not establish that every item, rarity or combination has been balanced.

### Complete codex inspection

Crate inspection no longer stops at eight rewards. Reward pages expose every
entry and its probability; hover uses the full item metadata supplied by the
main loop. The title-screen preview keeps its luck-one context visible. It is
not presented as a guarantee about the odds for a player's live build.

Descriptions for items, recipes and guide pages wrap and paginate at 800×450.
Width measurement accounts for inline currency icons, and both mouse-wheel and
button paths are tested. Selection changes reset the detail page. The Bazaar
item-details area is independently scrollable and cannot draw through the
reserved cost/action controls.

### Integration and player feedback

A real headless main-loop test now starts a run, opens the Bazaar, purchases a
crate, skips its already-committed animation, selects a combination base, drags
the acquired item into a slot, takes damage through the collision system and
loads the saved result. It checks item ownership, exact charging, combination
state and damaged health. It is stronger than an isolated drawing smoke test,
but is not a complete end-to-end test of every purchase type and fusion.

Defeated enemies emit short, bounded world-space pulses, so a finishing hit has
feedback even after the enemy is removed. Player shields have a visible ring;
health loss produces a brief border cue. None of these visuals changes damage,
collisions or RNG.

The opening guide is now safe practice: controls work, but the active run clock
and hostile spawning begin only when the optional guide completes or is
skipped. This is an action-driven onboarding phase, not a timed access gate.
The regression waits through many practice frames and confirms that enemies
and the run timer remain unchanged, then skips and observes live progression.

## 2. Economy defect discovered and corrected

The earlier values admitted a positive loop: buying a cheap Copper crate,
selling the resulting common item for Gold, then exchanging the Gold back into
Copper could produce more value than the original purchase. Arbitrarily high
trader bonuses made this worse. This was a real duplication route, not a matter
of whether the player enjoyed frequent shopping.

Purchased instances now retain the canonical Gold value invested in their
acquisition. Liquidation returns at most half of that budget, or three quarters
with the maximum bounded trader bonus, subject to the item's nominal quote.
Fractional Gold preserves a nonzero refund for cheap Copper items. Paid level
and rarity investments add only the value actually spent; fusion inherits its
source budgets rather than laundering them into the output's nominal rarity.
Earned and legacy items retain their prior nominal resale behavior.

Tests use actual purchase, sale and exchange services over repeated cycles,
all defined crate costs, extreme trader bonuses, paid upgrades and fusion.
Invalid bonuses and invalid transactions do not partially mutate the state.
Duplicate aliases of the same currency are aggregated before checking and
spending a rarity pool, closing an adjacent partial-spend issue.

Players see the ordinary owned/cost and refund amounts. The budget is metadata
for integrity and persistence, not a new resource they must micromanage.

## 3. Measured balance evidence

The [balance report](V1_TRUE_BALANCE_REPORT.md) and
[JSON observations](reports/v1_true_balance.json) retain 33 versioned trials.
Earlier snapshots explicitly identify their concurrent-source limitations.
The final six trials have matching source and asset fingerprints and forward
the current elemental, healing and critical parameters into actual combat.
The report is the source of truth for reproduction commands and complete data.

Before changing prices, the investigation compared three policies:

1. A kiter that uses the starter rifle/fireball and buys nothing.
2. A shopper that equips empty slots but keeps buying until inventory fills.
3. A managed shopper that compares gear with a stated heuristic, sells spares
   and purchases levels using actual earned currency.

The unmodified kiter controls die after 269.5–499.33 active seconds across the
three seeds, with 240–420 kills. This simple policy lacks dash planning,
projectile prediction, combinations, quests and fusion; it is not a prediction
of the survival time for all human players.

After the refund fix, all three final managed shoppers survive 900 active
seconds. They achieve 1,043–1,415 kills, finish at 307–375 HP, and reach peak
live-enemy counts of 22–55. They make 90–147 paid level upgrades rather than
176–177 in the earlier exploitable-economy sample. Maximum health changes with
equipment, so these HP figures must not be interpreted as healing above the
maximum. The report includes individual seed values and upgrade transitions.

These experiments support two conclusions: gear decisions materially change
survival, and the old refund economy overfunded repeated upgrades. They do not
yet establish ideal prices, a two-hour fun curve, a reachable normal-play path
to e308, or the strongest/weakest possible build. Avoid substituting a narrow
simulation for human feedback.

## 4. Verification approach

At completion of this pass, all 352 discovered tests passed, the editor
reported no problems, `git diff --check` was clear, and a headless launch
exercised the title, introduction and gameplay event loop. The API tests still
emit the existing third-party startup/dependency deprecation warnings.

The full unittest suite checks real catalog interaction, combat effects,
probabilities, ownership graphs, economic atomicity, serialization, actual SDL
input, tutorial transitions, codex pagination and API behavior. Focused tests
also cover the simulator's deterministic replay, RNG-state isolation and
nonnegative balances. The editor diagnostics and a real headless game launch
are part of the integration check after shared code settles.

The current arithmetic is intentionally finite. Economy calculations retain
512 significant digits; combat has a separate large-number representation.
Small spends around the practical e308 objective are covered, but arbitrary
precision beyond every possible future magnitude is not proven. The existing
third-party API startup/dependency deprecation warnings remain visible and
should be handled as a separate compatibility task.

## 5. Next pass priorities

### A. Validate active build diversity

Extend the harness with deliberately earned summon, elemental-trail, melee-risk
and hybrid builds, including failed gambles and replacement choices. Compare
policies over more seeds. Do not gift late-rarity equipment and then claim the
economy enables it. Keep free-gear fixtures only as declared throughput controls.

Record actual effective HP, outgoing damage, incoming damage, death source,
upgrade value, purchases, liquidation and time spent deciding. Identify whether
a mechanic is dominant because of damage, mitigation, healing, mobility,
proc frequency or transaction economics. Change one connected balance surface
at a time and retain the previous measurement snapshot.

### B. Finish content-role validation

Many armor and relic entries remain numeric-only. Stealth is not implemented,
and combining a ward or summon does not automatically create a new hit trigger.
Prefer several clearly differentiated, executed mechanics over a large list of
synonyms. For every new behavior, specify trigger, compatible bases, stacking,
target, bounds, scaling, feedback and save meaning before implementing it.

Verify armor sets guide a playstyle with a tradeoff and do not merely add
unexplained global power. Audit local versus global passive stats, particularly
relics and critical chance, whenever the combination contribution pipeline
changes. Preview wording must continue to match that policy.

### C. Playtest the interfaces and feedback

Test hover, item comparison and long names at every supported resolution.
Review the practice guide with someone unfamiliar with the controls. Check that
its placement does not cover a target or prevent learning a panel. Confirm
that descriptions and the codex are discoverable without requiring the player
to infer internal tags. Assess whether critical and defeat effects remain
readable with many summons and trails.

### D. Exercise the complete late-run route

A mathematical score trajectory is not an economy or survival proof. Build a
reproducible route that uses earned items and survives through the target kill
count, then validate it through real sessions. Profile frame time and entity
counts in high-throughput combat. Keep failure recovery and enemy counterplay
visible; do not guarantee impossibility of overwhelm merely because a spawn
cap exists.

After those checks, run another description-to-runtime audit, keep tests that
found real defects, and create the next pass from observed failures rather
than calling this pass the finished game.
