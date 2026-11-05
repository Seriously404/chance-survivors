# V1.0 True: reproducible balance observations

These are automated observations, not human playtests or a claim that the game
is finished. This report replaces formula-only estimates for the tested opening
policies. It does not establish a practical route to the e308 score milestone.
The reusable [JSON observations](reports/v1_true_balance.json) contain all 33
trials, minute checkpoints, currency balances and managed upgrade transitions.
Each trial is labeled before or after the liquidation correction described
below. The earlier tables are retained as measured pre-correction evidence.
The final six trials also forward all current elemental, healing, critical and
trader bonuses. Earlier trials omitted those explicit adapters and did not
record exact source fingerprints; their exact concurrent source snapshot is
unknown and they must not be represented as final integrated combat results.

## Reproduction

Run these commands from the project root with the project interpreter:

```bash
python -m scripts.balance_simulation --seconds 900 --seeds 7 23 101 --policy all
python -m scripts.balance_simulation --seconds 900 --seeds 7 23 101 --policy kite --loadout summoner
python -m scripts.balance_simulation --seconds 900 --seeds 7 23 101 --policy kite --loadout upgraded
python -m scripts.balance_simulation --seconds 900 --seeds 7 23 101 --policy managed-shopper
python -m unittest discover -s tests -p test_balance_simulation.py -v
```

The fixed step is 1/30 second. Runs stop at death or 900 active seconds. Menu
time is not simulated. Results include minute checkpoints, HP, kills, actual
HP lost, resolved damage, score, direct spawns, live enemy pressure, currencies,
item purchases, final equipped item IDs, progression milestones and death cause.
Random state is isolated and restored even if a probe fails. Fixed seeds are
reproducible for the same source and assets; future content or RNG changes
require rerunning the commands rather than treating this table as permanent.

## Policies and limits

- **Idle:** no movement, weapon use or ability use.
- **Stationary:** stands still and fires the starter rifle and fireball with
  perfect nearest-enemy aim whenever their cooldowns allow.
- **Kite:** uses the same combat policy and moves directly away from its
  nearest enemy. It does not predict incoming projectiles or plan escape routes.
- **Shopper:** kites, immediately buys an affordable starter crate using earned
  currency, and equips compatible ability/armor rewards in empty slots. It does
  not sell, compare replacement gear, exchange currencies, level items, combine
  items, accept quests or fuse. At inventory capacity it stops buying.
- **Managed shopper:** uses actual earned currency to buy the same starter
  crates, compares replacement gear with a declared stat heuristic, sells unused
  spares, equips up to four distinct ability scripts, and spends Gold on one
  lowest-level equipped item every five active seconds if affordable. These
  decision intervals are probe behavior, not game access gates. Its heuristic
  is not an exhaustive DPS or build search. It does not use dash/teleport, rarity
  gambling, currency exchange, combinations, quests or fusion.
- **Summoner fixture:** the kiting starter receives a free Legendary Sentinel
  Summon from the catalog. This compares an ability role; it is **not** evidence
  that the player could earn that summon at the beginning of a run.
- **Upgraded fixture:** the starter rifle and fireball are freely changed to
  level 10 Legendary. This is a throughput control, **not** an economy result.

The probe calls actual player/enemy movement, encounter scaling/director,
spawning, abilities, summons, projectiles, swept collision, elemental lingering,
finite trails, currency rewards, XP, score and crate transactions. It is a
separate system harness, not an event-driven execution of the shipped main
loop. It does not validate UI, aim/release inputs, manual dash, visual warnings,
tutorial comprehension, frames per second or readability. Damage dealt sums
resolved elemental damage events including overkill; damage taken counts actual
HP lost and does not count shield absorption. Direct spawn counts exclude
summoner-created enemies; live pressure includes them. Nearby means within 0.75
world units. Only three seeds were sampled, so the ranges below are observations,
not confidence intervals or population estimates.

## Results: opening 15 active minutes

| Policy / fixture | Seeds surviving to 900s | Lifetime seconds, range | Kills, range | Final HP, range | Peak enemies, range |
| --- | ---: | ---: | ---: | ---: | ---: |
| Idle / starter | 0/3 | 12.33–15.27 | 0 | 0 | 5–8 |
| Stationary / starter | 0/3 | 38.97–92.43 | 29–83 | 0 | 7–10 |
| Kite / starter | 0/3 | 269.50–499.33 | 240–420 | 0 | 23–38 |
| Shopper / starter | 3/3 | 900 | 550–1,097 | 163–183 | 60 |
| Managed shopper / starter | 3/3 | 900 | 1,232–1,432 | 368–415 | 21–41 |
| Kite / free summon | 3/3 | 900 | 1,388–1,458 | 27–64 | 10–14 |
| Kite / free upgraded items | 3/3 | 900 | 1,444–1,462 | 100 | 4–5 |

Shopper HP can exceed 100 because its purchased equipped armor increases maximum
health. This is not overhealing above maximum health. Shopper peak nearby
enemies varied from 5 to 18; hitting the 60-enemy cap is not equivalent to having
60 enemies touching the player. The upgraded controls kept total enemy pressure
low by killing quickly, which shows that encounter pressure depends strongly on
damage throughput rather than active time alone.

### Starter policy by seed

| Policy | Seed | End second | Kills | Score | Purchases |
| --- | ---: | ---: | ---: | ---: | ---: |
| Idle | 7 | 12.33 | 0 | 0 | 0 |
| Idle | 23 | 15.27 | 0 | 0 | 0 |
| Idle | 101 | 13.17 | 0 | 0 | 0 |
| Stationary | 7 | 92.43 | 83 | 19,990.52 | 0 |
| Stationary | 23 | 74.27 | 59 | 4,504.37 | 0 |
| Stationary | 101 | 38.97 | 29 | 697.55 | 0 |
| Kite | 7 | 499.33 | 420 | 3.174e11 | 0 |
| Kite | 23 | 326.83 | 258 | 1.172e8 | 0 |
| Kite | 101 | 269.50 | 240 | 4.869e7 | 0 |
| Shopper | 7 | 900 | 550 | 2.542e14 | 198 |
| Shopper | 23 | 900 | 1,097 | 1.404e26 | 198 |
| Shopper | 101 | 900 | 906 | 1.195e22 | 198 |

Every shopper filled its 200-item inventory: two starters plus 198 purchases.
The probe did not sell surplus items. This provides evidence that opening
currency income can finance a large amount of low-cost loot. It does not by
itself prove what price should replace the current price: a human player spends
time in menus, can choose other currency sinks, and may make fewer kills.

The managed policy avoided the capacity problem: it finished with ten equipped
items, bought 892–975 crates, sold 884–967 unused items and made 176–177 real
level upgrades. Its equipped gear ended around levels 15–18, with Common to
Rare starting loot rather than injected Legendary gear. It survived all three
seeds and kept peak enemy pressure below the cap. This distinguishes poor
inventory policy from raw throughput: inventory saturation alone is not proof
that a crate is incorrectly priced. However, the large transaction count also
shows that repeatedly opening and disposing of cheap loot is an available
economic strategy, which needs a human usability and fun assessment.

| Managed shopper seed | Kills | Score | Purchases | Sales | Level upgrades | Inventory at end |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 1,432 | 1.765e33 | 975 | 967 | 176 | 10 |
| 23 | 1,260 | 4.003e29 | 905 | 897 | 177 | 10 |
| 101 | 1,232 | 1.032e29 | 892 | 884 | 177 | 10 |

Its first level upgrade occurred at 15.10–20.10 seconds, first armor at
14.63–35.30 seconds and level-8 threshold at 37.57–89.47 seconds. Gear and reward
choices can therefore change quest availability substantially. This still does
not demonstrate that a human can evaluate and execute hundreds of transactions
at the policy's speed; the model pauses no active time for buying and selling.

First shopper purchases occurred at 10.53–14.53 active seconds, and its first
armor reward occurred at 31.27–47.97 seconds. All moving starter policies reached
the level-8 main-quest threshold between 95.03 and 103.23 seconds. The harness
records reaching the threshold, not accepting or completing the quest. Rarity
upgrade and fusion availability have not yet been measured.

The free summon controls reached scores between 2.080e32 and 6.468e33; free
upgraded starters reached 3.215e33–7.774e33. These results show the current
kill-driven score grows far beyond thousands. Even the strongest tested result
is many orders of magnitude below e308. No estimate of a two-hour route should
be inferred from this short sample.

## What the evidence justifies next

1. Investigate starter-crate income, duplicate handling, meaningful spending
   choices and inventory capacity together. Price changes alone could delay
   the player's first build without solving later surplus.
2. Extend the earned-upgrade policy to declare a rarity-gamble, combination and
   fusion strategy, with exact spends and transition logs. The existing managed
   policy measures level upgrades only; the injected Legendary fixture remains
   a separate control rather than a progression result.
3. Add a fixed, declared unfavorable-loot sequence and more movement policies;
   three ordinary seeds do not cover bad luck, beginner aim or dash use.
4. Compare the managed buyer with a policy that invests in combinations rather
   than automatically using every equipped ability on cooldown. Both current
   shopper policies cast automatically and cannot establish whether deliberate
   ability timing feels rewarding to a person.
5. Run longer experiments separately and profile collision and Decimal costs.
   The probe's wall-clock runtime is not a rendering benchmark.
6. Validate the real main loop through input, pauses, purchases, effects and
   save/resume, then conduct human playtests. A fair pressure director requires
   recovery opportunities and understandable counterplay, not only a count cap.

## Liquidation correction and measured follow-up

The experiments exposed a separate economic defect: a 35-Copper crate produced
an item worth at least 9 Gold when sold. With 25 Copper per Gold and the 10%
exchange fee, 9 Gold returned 202 Copper. Repeated buying, selling and exchanging
could mint currency without any combat or luck. An unbounded trader bonus made
the problem worse. The earlier managed policy did not exchange Gold back to
Copper, so its high volume was evidence worth investigating rather than proof
that it used this full arbitrage loop.

The correction keeps catalog prices and all loot odds unchanged. Each new
purchase records its real acquisition value in Gold units, including every
currency in a multi-currency cost. Its resale quote is capped at 50% of that
investment, rising to 75% with the bounded maximum trader bonus. A common
35-Copper purchase now quotes 0.70 Gold by default or 1.05 Gold at maximum bonus,
rather than being rounded up to at least one whole Gold. Fractional proceeds
accumulate in the existing Decimal-backed wallet. Market purchases use the same
budget, so their liquidation cannot exceed the amount spent either.

Paid item levels and rarity gambles add their actual spend to this budget.
Fusion inherits the sum of its ingredients' budgets, preventing cheap equipment
from being fused simply to erase its resale cap. Free/legacy items retain their
previous nominal value; their finite existing inventory is not a source of
unlimited new cheap items. Sale value still respects the nominal rarity/level
quote when that is lower than the investment cap. The tradeoff is deliberate:
a rare lucky find in a cheap crate can be powerful equipment without also
guaranteeing a huge cash payout. This partial-refund policy needs player feedback.

A related rarity-pool defect was fixed: aliases such as `Copper` and `copper`
are aggregated before checking and spending, so the same wallet balance cannot
be counted twice. Nonfinite trader bonuses are rejected before a sale changes
the wallet or inventory. Focused tests exercise all crate definitions, repeated
real purchases/sales/exchanges, inheritance through fusion, upgrade refunds and
failed transaction integrity.

The same managed policy and three seeds were rerun for 900 seconds after the
correction, along with the three basic kiting controls:

| Managed shopper seed | Survives 900s | Kills | Final HP | Peak enemies | Purchases | Level upgrades |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 7 | Yes | 1,366 | 332 | 29 | 947 | 119 |
| 23 | Yes | 978 | 299 | 55 | 680 | 76 |
| 101 | Yes | 1,410 | 364 | 23 | 1,033 | 141 |

All three still finished with ten equipped items. Paid level upgrades fell from
176–177 before the fix to 76–141 afterward. The kiting controls reproduced their
earlier lifetimes and kill totals exactly, showing the correction did not change
the unpurchased starter's combat. Per-seed outcomes do not all move in one
direction: changed spending changes kills, rewards, random draws, future gear and
survival pressure. Three seeds are insufficient to claim a general win-rate or
kill-rate improvement. The managed policy's continued large purchase count also
shows that this correctness fix is not a full economy or menu usability rebalance.

No enemy, crate cost or reward-odds constants were tuned to make these runs
succeed. The report records the contrast between unbuilt starter play, purchasing
and strong injected controls, then measures a necessary transaction correction
separately so future tuning can be evaluated against evidence.

## Final integrated adapter measurements and source attribution

The simulator was updated to forward the same equipped elemental damage,
healing and critical bonuses as the main loop, and the same luck-based trader
bonus. Six further trials use the integrated liquidation correction and these
adapters. All six recorded the same SHA256 before and after execution:

```text
27cc09a248ab5ec77e5f43114b14049a5571fe5d004a7f8b3baf0aeaaae92c01
```

The fingerprint covers sorted relative paths and contents for game Python
modules, JSON assets and the simulator itself. Every final trial reports
`source_changed_during_trial: false`. It is a source snapshot identifier, not a
claim that a human or the rendered main loop played these runs. Earlier trials
are retained with null fingerprints and explicit unknown-source annotations.

| Final managed seed | Survives 900s | Kills | Final HP | Peak enemies | Purchases | Level upgrades |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 7 | Yes | 1,323 | 335 | 40 | 921 | 123 |
| 23 | Yes | 1,043 | 307 | 55 | 631 | 90 |
| 101 | Yes | 1,415 | 375 | 22 | 1,065 | 147 |

The final basic kiter controls again reproduce 420/258/240 kills and death at
499.33/326.83/269.50 seconds, respectively. The final managed runs all finish
with ten equipped items and survive the entire 900-second window. The change
from the original managed observations includes both the resale correction and
newly forwarded passive bonuses, so their combined difference cannot be
attributed to liquidation alone. The intermediate post-liquidation table above
is retained to make that distinction inspectable.
