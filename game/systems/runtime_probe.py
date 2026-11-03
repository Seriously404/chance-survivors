"""Small JSON control surface for exercising real game systems at runtime.

Run ``python -m game.systems.runtime_probe --interactive`` and send one JSON
command per line. This is a developer probe, not part of the shipped game UI.
"""

from __future__ import annotations

from copy import deepcopy
import json
import sys
from typing import Any

from game.config.settings import bullet_base_speed, enemy_types, player_max_health
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.bullets import load_bullet_types
from game.systems.collision import CollisionSystem
from game.systems.currency import CurrencyWallet
from game.systems.items import create_initial_inventory, player_bonuses, player_speed_multiplier, spawnable_items
from game.systems.progression import PlayerProgress, award_enemy_kill
from game.systems.scoring import RunScore
from game.systems.combinations import CombinationEngine
from game.systems.weapons import projectile_for_weapon
from game.utils.large_number import LargeNumber


class RuntimeProbe:
    """Inspectable and controllable instance built from the game's systems."""

    def __init__(self) -> None:
        self.player=Player(health=player_max_health,max_health=player_max_health)
        self.inventory=create_initial_inventory()
        self.combination_engine = CombinationEngine()
        self.player.max_health=LargeNumber(player_max_health)+player_bonuses(self.inventory)["health"]
        self.player.health=self.player.max_health
        self.bullet_types=load_bullet_types()
        self.collision=CollisionSystem(200)
        self.wallet=CurrencyWallet()
        self.progress=PlayerProgress()
        self.bullets=[]
        self.enemies=[]
        self.weapon_cooldowns=[0.0,0.0]
        self.score=RunScore()
        self.elapsed=0.0
        self._spawned=0
        self._catalog=spawnable_items()

    def status(self) -> dict[str, Any]:
        return {
            "player":{"x":self.player.x,"y":self.player.y,"health":str(self.player.health),
                      "max_health":str(self.player.max_health),"angle":self.player.angle},
            "inventory":{"count":len(self.inventory.items),"active_slots":self.inventory.active_slots,
                          "bonuses":{name: str(value) for name, value in player_bonuses(self.inventory).items()}},
            "bullets":[{"type":b.bullet_type,"damage":str(b.damage),"piercing":b.piercing} for b in self.bullets],
            "enemies":[{"type":e.type,"x":e.x,"y":e.y,"health":str(e.health)} for e in self.enemies],
            "currency":{name: str(amount) for name, amount in self.wallet.amounts.items()},
            "score":str(self.score.total_score),"level":self.progress.level,
            "experience":self.progress.current_exp,"elapsed":self.elapsed,
        }

    def execute(self, command: dict[str, Any]) -> dict[str, Any]:
        action=command.get("action")
        if action=="status": return self.status()
        if action=="spawn_enemy":
            kind=str(command.get("type","basic"))
            if kind not in enemy_types: raise ValueError(f"Unknown enemy type: {kind}")
            stats=enemy_types[kind]
            enemy=Enemy.create_from_type(kind,stats,float(command.get("x",0.08)),float(command.get("y",0)))
            if "health" in command:
                enemy.health=LargeNumber(max(1,int(command["health"]))); enemy.max_health=enemy.health
            self.enemies.append(enemy)
            return {"enemy_index":len(self.enemies)-1,"health":str(enemy.health)}
        if action=="fire":
            slot=int(command.get("slot",0))
            if slot not in (0,1): raise ValueError("weapon slot must be 0 or 1")
            if self.weapon_cooldowns[slot]>0: return {"fired":False,"cooldown":self.weapon_cooldowns[slot]}
            item_id=self.inventory.active_slots["weapons"][slot]
            item=next((i for i in self.inventory.items if i["id"]==item_id),None)
            combined_item = self.combination_engine.evaluate_inventory(self.inventory, item_id) if item else None
            projectile,cooldown,automatic=projectile_for_weapon(
                self.player,float(command.get("angle",0)),combined_item,slot,self.bullet_types,bullet_base_speed,
                player_bonuses(self.inventory)["damage_pct"])
            self.bullets.append(projectile); self.weapon_cooldowns[slot]=cooldown
            return {"fired":True,"type":projectile.bullet_type,"damage":str(projectile.damage),
                    "piercing":projectile.piercing,"cooldown":cooldown,"automatic":automatic}
        if action=="step":
            dt=float(command.get("dt",1/60))
            if not 0 < dt <= 10: raise ValueError("dt must be greater than 0 and at most 10 seconds")
            self.elapsed+=dt
            self.weapon_cooldowns=[max(0,v-dt) for v in self.weapon_cooldowns]
            for bullet in self.bullets:
                bullet.steer_towards(self.enemies, dt)
                bullet.move(dt)
            self.bullets,self.enemies=self.collision.check_bullet_enemy_collisions(
                self.bullets,self.enemies,enemy_types)
            killed=len(self.collision.killed_enemies)
            for enemy in self.collision.killed_enemies:
                self.score.award(LargeNumber(10) * enemy.reward_multiplier)
                self.wallet.reward_for_kill(
                    luck=player_bonuses(self.inventory)["luck"],
                    reward_multiplier=enemy.reward_multiplier,
                )
                award_enemy_kill(self.progress)
            return {"killed":killed,"state":self.status()}
        if action=="move_player":
            dt=float(command.get("dt",1/60))
            bonuses=player_bonuses(self.inventory)
            self.player.move(float(command.get("dx",0)),float(command.get("dy",0)),dt,
                             player_speed_multiplier(bonuses["speed_pct"]))
            return {"x":self.player.x,"y":self.player.y,"speed_multiplier":player_speed_multiplier(bonuses["speed_pct"])}
        if action=="enemy_attack":
            index=int(command.get("index",0))
            if not 0<=index<len(self.enemies): raise IndexError("enemy index out of range")
            self.enemies[index].x=self.player.x; self.enemies[index].y=self.player.y
            health_before=self.player.health
            self.player=self.collision.check_enemy_player_collisions(
                self.enemies,self.player,enemy_types,player_bonuses(self.inventory)["defense"])
            return {"damage_taken":str(health_before-self.player.health),"health":str(self.player.health)}
        if action=="spawn_item":
            template=next((i for i in self._catalog if i["id"]==command.get("item_id")),None)
            if template is None: raise ValueError("Unknown catalog item_id")
            item=deepcopy(template); self._spawned+=1; item["id"]=f"probe-{self._spawned}"
            self.inventory.add(item)
            return {"item_id":item["id"],"inventory_count":len(self.inventory.items)}
        if action=="equip":
            self.inventory.equip(str(command["item_id"]),str(command["slot"]),int(command["index"]))
            return self.status()["inventory"]
        if action=="combine":
            self.inventory.assign_combination(str(command["base_id"]),int(command["index"]),command.get("item_id"))
            return self.status()["inventory"]
        if action=="assert_invariants":
            self._assert_invariants()
            return {"ok":True,"items":len(self.inventory.items),"bullets":len(self.bullets),"enemies":len(self.enemies)}
        if action=="scenario": return self.run_scenario()
        raise ValueError("unknown runtime action; supported: status, spawn_enemy, fire, step, move_player, enemy_attack, spawn_item, equip, combine, assert_invariants, scenario")

    def _assert_invariants(self) -> None:
        ids=[item["id"] for item in self.inventory.items]
        assert len(ids)==len(set(ids)), "duplicate inventory ids"
        assert len(ids)<=self.inventory.CAPACITY, "inventory overflow"
        assert self.player.health<=self.player.max_health, "health exceeds max health"
        assert all(value>=0 for value in self.wallet.amounts.values()), "negative currency"
        assert all(bullet.damage>0 for bullet in self.bullets), "invalid projectile damage"

    def run_scenario(self) -> dict[str, Any]:
        """Exercise both equipped weapons, collision rewards, and item assignment."""
        target=Enemy.create_from_type("basic",enemy_types["basic"],0.07,0)
        self.enemies.append(target)
        rapid=self.execute({"action":"fire","slot":0})
        self.execute({"action":"step","dt":0.02})
        if self.enemies:
            self.execute({"action":"step","dt":0.2})
            self.execute({"action":"fire","slot":0})
            self.execute({"action":"step","dt":0.02})
        heavy=self.execute({"action":"fire","slot":1})
        self.execute({"action":"step","dt":0.8})
        self.execute({"action":"step","dt":0.02})
        assert rapid["type"]=="rapid_fire" and rapid["automatic"] and rapid["piercing"]==0
        assert heavy["type"]=="heavy_shot" and not heavy["automatic"] and heavy["piercing"]>0
        assert self.score.total_score==10 and self.progress.current_exp==1 and not self.enemies
        self._assert_invariants()
        return {"rapid_fire":rapid,"heavy_shot":heavy,"state":self.status(),"invariants":"passed"}


def main() -> None:
    probe=RuntimeProbe()
    if "--interactive" not in sys.argv:
        print(json.dumps(probe.execute({"action":"scenario"}),indent=2))
        return
    for line in sys.stdin:
        try:
            response=probe.execute(json.loads(line))
            print(json.dumps({"ok":True,"result":response}),flush=True)
        except Exception as exc:  # developer console should surface live failures
            print(json.dumps({"ok":False,"error":f"{type(exc).__name__}: {exc}"}),flush=True)


if __name__=="__main__":
    main()
