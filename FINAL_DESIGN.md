# Ok then, design time!
# Chance Survivors final design document

## K so the game is really quite simple, really.
the core of the game is to try and reach infinity points, also known as the 64-bit integer limit, or approximately 1.797e308
so basically, you must implement everything in the game in accordance to the fact that the game would scale up in magnitudes.
a single run for an average first time player should be aimed at a total of 2 hours of actual gameplay, however the core idea is to either reach the highest possible score, or get infinite score in the least amount of time.

the very most important thing is the luck factor. you should focus on making most things in the game revolve around luck. the luckier you are, the more powerful you are, simple.

## super duper important!!!!!
you must write a fastAPI and uvicorn api that allows me to start a server that has a leaderboard of the scores. you enter your name before a run, and at the end of it, you can choose to upload your score to the database. then the website accesses the database and you can see all the entries. also provide an additional path or an editing mode inside the website that allows me to clear the database of all scores.
### what info has to be saved?
your total score at the end of the run, your run time, and the informational player stats, specifically: inventory, level, active items at the end of the run. Other players should be able to recreate a specific build in their own games from looking at the top scorers. however, when you just open the basic website, it only shows a table with
|place| |name | |score| |time|, and allow you to click on each entry, to bring up a detailed, cleanly structured menu in the current style of the game, that shows the player's inventory and stats, especially luck and level, etc.

## little note: if you want an accent color, choose green.

## next topic.
the actual game state at the beginning. a working prototype where the core loop of the game has been created, and most menus have been made in their bare form.

## what is the end result gonna look like?
you MUST follow this section down to the last minute detail.
now this is quite complex so take each task carefully.
now the final game will have the following rarities
common - gray
uncommon - green
rare - blue
epic - purple
legendary - yellow
mythical - red
ultimate - rainbow
these have already been implemented for items.
when you open the game you are greeted with the name entry promt, play, exit and settings buttons. (already done)
the main game loop is simple. shoot your active weapons, use your abilities etc. to kill enemies, complete quests for a bigger percentage bonus on your score, and upgrade, upgrade, upgrade!
the whole game is gonna be centered around luck and synergies and upgrades.
## what sits in your inventory?
in general, things in your inventory are referred to as items. here are the types of items:
weapon: can sit actively in one of your weapon slots
ability: can sit actively in one of your ability slots.
armor: can sit actively in its respective armor slot. there are boots, pants, chestplate, headpiece and accessory slots.
relic: these items just sit in your inventory, and are meant to be combined with other items.


## suggestions for items that you can then go off of to make even more
Guns: 
    a regular all rounder rifle that fits any situation. bullets despawn when they damage an enemy, despawn together with the enemy.
    a powerful sniper whose bullets travel as long as their internal damage doesnt deplete.
    an alien gun that has bullets that have homing capabilities. 
    a machine gun that fires not too accurate, low damage rounds.
    a shotgun that shoots pellets, that deplete after just a short distance, but packs a punch

Armor:
    Specifically, sets.
    now, armor sets are gonna be one of the things steering your path. having a full set of 4 armor pieces gives even more bonuses towards the playstyle, and enables more synergies.
    just to give some examples:
    a set that focuses on increasing your damage the faster you are.
    a tank set that enables your dash to damage enemies and gives you invulnerability periods, but overall makes you slower.
    a ranged set, that enables you to do more damage the further from the opponent you are.
    a sneaky set, that synergizes with invisibility abilities and others and gives bonuses for attacking enemies that dont know your position.
    more simply, elemental sets that give bonuses to their respective elements, and nerf the usage of others.
    passive bonuses: armor sets should focus on giving you passive bonuses that can proc when certain events happen, such as casts of specific abilities, etc.
    here you can really go wild and design all kinds of freaky ideas and have fun making specific playstyles.
    what i want to see most is a sentry / minion playstyle, that basically turns you into a hyper engineer and builder, making synergies with anything that can build walls, place down minions etc. however the set debuff must be that instead of focusing on you, the enemies focus on something else that you now must defend instead. so basically, just the armor set you choose later on defines how you are going to be playing your entire rest of the game.

abilities:
    this is gonna be by far the most important part of the whole game, so heres a guide on general design.
    an ability, at its core without combinations, should be fairly incompetent, and you are expected to combine it to actually make some cool stuff.
    lets say, a fireball ability. at its base, it casts one fireball in a target direction, that hits one single enemy. so you are expected to make combinations to make a longer burn effect, turn it into an AoE, or maybe even have it home, or leave a trail that sets enemies on fire. the rules are yours to write.
    there should be many MANY abilities, each doing a little thing at once, and their power comes from combining them. to give an example, adding a healing spell (heals one minion) onto a fire spell that has already been combined with a grenade, makes your fireball ability that throws a fire grenade that does fire damage to enemies in a range, but also heals minions / sentries.

relics:
    now relics are interesting in the sense that they should focus primarily on adding functionality over stat bonuses. such as ricochet, better explosions, add homing to things that dont have it yet, etc. a great example would be
        lucky box - added to abilities - every time you cast the ability, the box increases your luck stat permanently. must be attached to an ability for the increase to work.
        or perhaps
        monkey's paw - buffs random stats (determined when you first get it) and nerfs others. you can reroll it for currency, and the luckier you are, the less debuffs you get and the higher bonuses you get.
        or even - a relic that just simply increases enemy spawn rate.
        and so on, get creative

elements:
    now elements come in the form of: damage type and resistance. so you can do elemental damage, and enemies can have resistance to that type of damage.
    you can make as many different ones as you like, really, but dont try to climb over 10 different kinds.

enemies:
    enemies have different types, simple as that. one is faster, but has worse turning speed, the other is really, slow but has much more hp and resistances. you can also have shooting enemies, ones that are barely visible, aka have a stealth, ones that just summon more dummy minions (that do not give any xp) aka necromancers, etc. get relly creative, the enemies should be on par with the player the longer he goes, so you can safely also create enemies that can use certain abilities, etc. you can make them smarter, make them spawn in swarms, and most importantly, scale with the player, but also allow the player yo scale enemies himself, to make sure that he can get infinite points the fastest.

Currencies:
    add many, simple as that. different kinds of enemies drop different kinds of currencies, and there must be at least a few types that can only be obtained through killing enemies a certain way, such as a relic, that gives you the currency if you kill an enemy with whatever base item it is attached to, or a currency that you can get only by taking damage while a different relic is combined with your armor, etc. and also just basic currencies, like gold, copper, or fancy currencies, like dark matter.
   

# SCALING
make sure that things like enemy health always keep scaling appropriately, and so do the score and points you get when killing enemies.
this is an incremental process after all.
scaling is very important, and there must be abilities, relics and other things that let you control scaling separately of time based scaling. this is so that if you get a build that is too op, you can try to up the difficulty, get more points and reach infinity faster.


now rarities and levels affect this heavily.
a rarity is a multiplier, higher rarity multiplies all the stats, including those added in combinations.
a level for each item can be infinite, and adds to stats, not multiplies.
any item can be any rarity or level, just saying.

# so the big question
how do you implement this?
simple, for every gun, relic, element, when you define it in assets, give it a LOT of info, i mean a lot. like, for each stat that it could affect, tell how it affects it, etc.
abilities literally each have a custom script according to what they do.

# COMBINATIONS
this is SUPER important. like, very super duper mega important. this is the literal entire core of the game, you cannot make this be a bad implementation.
the way combinations work is that you can slap any item onto any other item, with the exception of armor, which can be combined onto only other armor.
there is a base item, and the others i call supplemental items, but that is not gonna be their name in game, its gonna be combined items.
the way it works is that you can literally just drag and drop supplemental items onto any base item, as long as the base item has free slots, (already defined by rarities) and the supplemental item isnt a base item for more combinations. each supplemental item can only supplement one base item at a time.
what do combinated items do? this is the beatiful part. i have no fucking clue. this is LITERALLy a case to case basis, there can be default cases, special cases, etc. as long as it plays well.
so here are some suggestions:
    the hot default of this system, obvious to anyone is using an element as a base, and a adding a grenade to it. this turns the elemental ability into an AoE wherever you aim it.
    now basically, make as many different kinds of interactions between stats as you can, but resort to this: when you feel like a combination doesnt really need custom behaviour, it just amplifies stats. so for instance, if you have a fireball ability, and add another one to it, it simply just makes it stronger. or when you add a gun to an ability. i mean, how does that combine? it doesnt, so just make the ability also do a regular damage type as well and slightly buff the stats.
    but for instance, if you add an ability to a gun, then that gun can then also do that new kind of ability damage, etc.
    if you have a teleportation ability, and add a fireball to it, then teleporting makes you leave a line from point a to point b that burns enemies, and if you also have a grenade, then on the exit you release a fire blast.
combinations are super important, you must make custom behaviours, default behaviours and everything in between to flesh the system out.


# FUSIONS
this is how those work. a fusion is when you permanently bind multiple different things together, not as a combination, but as a brand new item, that you cannot get through normal means (i will explain what normal means are later.)
again, get really creative here, this is just more items for you to define. just make sure that you can only get fusion items through fusion and not anyhow else.
fusions will be the main pathway to much more powerful things that do much more at the same time, and let you grow exponentially.


when designing new, any kind of ability, item etc. you are advised to get as creative as possible. the more different kinds of items, synergies, combinations and fusions exist, the better.

# MENU
so there is the game menu.
it has:
inventory
quests
upgrades
bazaar

inventory is mostly done, it simply must let you switch out active abilities, weapons armor, etc.

# QUESTS
the questing system is simple. when you reach level-up milestones, you can get new quests, that you can take on, to get a percentage score bonus.
the right side of the screen while you play has an active quests menu, this shows you incomplete quests.
you can, in fact, fail quests.
there are 2 quest types. side quest and main quest. main quest you get at level 5. it gives a large percentage bonus, but sets you on a specific path, such as never using snipers (after selecting the quest) or being able to only use a specific ability etc.
again, get creative. there must also be an option specificaly to lock the main quest, which in essence, doesnt allow you to do things that would invalidate your main quest, such as using a sniper, if you arent allowed to use snipers, etc. this is an optional toggle.
for side quests, you unlock more and harder side quests, that give a relatively smaller bonus, as you also level up, and after reaching the maximum level, you get new quests when you complete enough of the previous side quests. side quests cannot be failed. they are simply "kill x enemy with y" or "kill y enemies in x seconds" and so on.

# UPGRADES
straigtforward. one menu is an overview, where you can view your stats, the other one is the menu where you can actively customize combinations.

# BAZAAR
by FAR the most important menu in the tabs.
this has to have many many tabs. currently it has a test item spawner, remove it in the final version.
so the menus, you might be asking.
as follows: FUSION. the menu where you can fuse items together to form key items. unlocked after reaching a level milestone.
RARITY UPGRADER: a gambling system that lets you upgrade the rarity of an item. basically, you can throw currency at it, any currency works, however each item has favourable currencies and non-favourable currencies. you need less of a favourable currency to increase your chances, and you need more of a non-favourable currency. default currencies are just default, no penalty or bonus. upgrading also depends on your luck stat obviously. you cannot upgrade a currency past ULTIMATE rarity, however the ULTIMATE rarity can have sub-tiers, ranging from ULTIMATE 1 - ULTIMATE 100, and basically make the icon of it be a gradient that starts out something like super dark blue to super dark purple, and ends at pure white for ULTIMATE 100, or something like that. this is also to preserve the incremental nature of the game.
LEVEL UPGRADER: here you can throw specific kinds of currencies into an item to upgrade its level, increasing its power additively. its kind of simple, but it works
SHOPS: it has crates. you can spend money on a crate, the more money you spend the higher chance of a good item coming out is. each item has a base rarity that it starts at, the basic rifle for example is common, basic spells are common too, but certain relics start at legendary, and since it only goes up to legendary (you must upgrade rarity for mythinc and beyond) they are the rarest to get.
more specifics on crates: each crate in the shop has random items, along with random chances. when you select a crate, you can either buy it as is, and hope for the rare drop, or spend more money to rig it and have a higher chance of getting the item you would want. more crates spawn in as you play more, and you can refresh the entire crate menu, and they also periodically refresh. basically, crates are the main way to get more items, you must create a system that is intuitive to use, but still lets the player have some control over the outcomes. however in the end it is still all a gamble. so yeah, the bazaar is full of gambling features.

SELL - a separate menu in the bazaar that lets you sell items you dont want.
thing is - i will be nice. and i will allow you to ADD YOUR OWN menus, inst that crazy? you are completely allowed to add more menus as you see fit, each serving an interesting purpose here, if you see it fit. this is your chance to prove that you can not only make new weapons, armor and abilities, but also entire game features. maybe add a wizard that can give you more combination slots for a price? maybe add a casino where you can gamble to exchange a currency to a different type? this is all up to you after these main 5 menus.

this covers what i want the final state of the game to be
i want the endgame to be utter chaos, where you can choose ridiculous paths to take and compete for the fastest time to reach infinity. there must be hundreds, if not thousands of cool items, synergies, combinations, armours, and everything in between.

you must also on the side delegate to polish the game, to make features easier to use, to make them look and function better, to add cool special effects to abilities, maybe even add a glow effect to certain things, this is up to you, but the rule is: the game is finished not when all the core features are implemented and you can play for 15 minutes, it must be a polished masterpiece that has near infinite replay value, long runs, and potentially, even multiplayer?
## MULTIPLAYER (SUPER OPTIONAL)
one player hosts the game server, the other player can connect to it, even through the internet,and they can play together. allow up to 5 players at once. game scales accordingly, making more and harder enemies, every player gets fair amount of curency, they are allowed to trade and exchange with each other, and this time, instead of protecting their skin like in singleplayer (except if you play a class or main quest that makes you protect an object) they are required to cumulatively protect an object that the enemies try to attack, while still staying alive because they can still take damage. a player respawns in 60 seconds after death, if at least one teammate remains alive
this is entirely optional, add it only after the game is already in a very polished state.


oh and by the way, when you are in a menu, the main timer doesnt tick, so only your active gameplay is added to the running total.
always look out to make the actual best looking result, make sure that UI scales properly with different resolutions, and let your creativity shine! do not EVER stop at my examples, add as much as you can possibly think of. make lists first, of ideas you have, and add more and more, as much as you can.
final notes: make sure that player level holds actual value, and properly gates new features, not only to not overwhelm the player, but to also ensure normal scaling. reaching level 50 is when the real game truly can begin.
