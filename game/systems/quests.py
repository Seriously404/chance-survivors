"""Data-driven quest definitions and progress tracking for the run loop."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import math
from typing import Any

from .game_definitions import load_quests


@dataclass
class Quest:
    """Quest instance for a live run."""

    id: str
    name: str
    description: str
    quest_type: str
    unlock_level: int
    reward_pct: float
    condition: str
    target: float
    enemy_type: str | None = None
    restrictions: list[str] = field(default_factory=list)
    forbidden_item_tags: list[str] = field(default_factory=list)
    progress: float = 0.0
    completed: bool = False
    failed: bool = False
    lock_on_accept: bool = False

    def percent_complete(self) -> float:
        if self.target <= 0:
            return 1.0 if self.completed else 0.0
        return min(1.0, self.progress / self.target)

    def to_state(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.quest_type,
            "unlock_level": self.unlock_level,
            "reward_pct": float(self.reward_pct),
            "condition": self.condition,
            "target": float(self.target),
            "enemy_type": self.enemy_type,
            "restrictions": list(self.restrictions),
            "forbidden_item_tags": list(self.forbidden_item_tags),
            "progress": float(self.progress),
            "completed": bool(self.completed),
            "failed": bool(self.failed),
            "lock_on_accept": bool(self.lock_on_accept),
            "percent_complete": float(self.percent_complete()),
        }


QUEST_BLUEPRINTS: list[dict[str, Any]] = load_quests()


class QuestManager:
    """Track active, failed, and completed quests for a run."""

    def __init__(self, blueprints: list[dict[str, Any]] | None = None) -> None:
        self.blueprints = [deepcopy(item) for item in (blueprints or QUEST_BLUEPRINTS)]
        self.active_quests: list[Quest] = []
        self.completed_quests: list[Quest] = []
        self.failed_quests: list[Quest] = []
        self.level = 1
        self.kills_total = 0
        self.kills_by_enemy: dict[str, int] = {}
        self.time_survived = 0.0
        self.main_quest: Quest | None = None
        self._sync_unlocked_quests()

    def _quest_id_set(self, quests: list[Quest]) -> set[str]:
        return {quest.id for quest in quests}

    def _sync_unlocked_quests(self) -> None:
        existing = self._quest_id_set(self.active_quests + self.completed_quests + self.failed_quests)
        for blueprint in self.blueprints:
            quest_id = str(blueprint["id"])
            if quest_id in existing:
                continue
            if int(blueprint["unlock_level"]) > self.level:
                continue
            if blueprint["quest_type"] == "main":
                if self.main_quest is not None:
                    continue
                self.main_quest = self._build_quest(blueprint)
                self.active_quests.append(self.main_quest)
                continue
            if len([quest for quest in self.active_quests if quest.quest_type == "side"]) >= 3:
                continue
            self.active_quests.append(self._build_quest(blueprint))

    def _build_quest(self, blueprint: dict[str, Any]) -> Quest:
        return Quest(
            id=str(blueprint["id"]),
            name=str(blueprint["name"]),
            description=str(blueprint["description"]),
            quest_type=str(blueprint["quest_type"]),
            unlock_level=int(blueprint["unlock_level"]),
            reward_pct=float(blueprint["reward_pct"]),
            condition=str(blueprint["condition"]),
            target=float(blueprint["target"]),
            enemy_type=blueprint.get("enemy_type"),
            restrictions=list(blueprint.get("restrictions", [])),
            forbidden_item_tags=list(blueprint.get("forbidden_item_tags", [])),
        )

    def register_level(self, level: int) -> None:
        self.level = max(1, int(level))
        self._sync_unlocked_quests()
        for quest in self.active_quests:
            if quest.condition == "level_reached":
                quest.progress = float(self.level)
                self._advance_quest(quest)

    def register_kill(self, enemy_type: str | None = None) -> None:
        self.kills_total += 1
        if enemy_type is not None:
            self.kills_by_enemy[enemy_type] = self.kills_by_enemy.get(enemy_type, 0) + 1
        for quest in list(self.active_quests):
            if quest.condition == "kills_total":
                quest.progress = float(self.kills_total)
            elif quest.condition == "kills_enemy" and quest.enemy_type:
                quest.progress = float(self.kills_by_enemy.get(quest.enemy_type, 0))
            self._advance_quest(quest)

    def register_time(self, elapsed_seconds: float) -> None:
        self.time_survived = max(0.0, float(elapsed_seconds))
        for quest in list(self.active_quests):
            if quest.condition == "time_survived":
                quest.progress = self.time_survived
                self._advance_quest(quest)

    def _advance_quest(self, quest: Quest) -> None:
        if quest.completed or quest.failed:
            return
        if quest.condition == "kills_total":
            value = float(self.kills_total)
        elif quest.condition == "kills_enemy":
            value = float(self.kills_by_enemy.get(quest.enemy_type, 0))
        elif quest.condition == "level_reached":
            value = float(self.level)
        elif quest.condition == "time_survived":
            value = float(self.time_survived)
        else:
            value = float(quest.progress)
        quest.progress = max(float(quest.progress), value)
        if value >= quest.target:
            quest.completed = True
            quest.progress = float(quest.target)
            self.active_quests.remove(quest)
            self.completed_quests.append(quest)

    def total_bonus_pct(self) -> float:
        return float(sum(quest.reward_pct for quest in self.completed_quests))

    def to_state(self) -> list[dict[str, Any]]:
        quest_states = [quest.to_state() for quest in self.active_quests + self.completed_quests]
        for quest_state in quest_states:
            quest_state["status"] = "completed" if quest_state["completed"] else "active"
        return quest_states

    def to_save_state(self) -> dict[str, Any]:
        """Return the counters and quest outcomes needed to resume a run."""
        def compact(quests: list[Quest]) -> list[dict[str, Any]]:
            return [
                {
                    "id": quest.id,
                    "progress": quest.progress,
                    "lock_on_accept": quest.lock_on_accept,
                }
                for quest in quests
            ]

        return {
            "version": 1,
            "level": self.level,
            "kills_total": self.kills_total,
            "kills_by_enemy": dict(self.kills_by_enemy),
            "time_survived": self.time_survived,
            "active": compact(self.active_quests),
            "completed": compact(self.completed_quests),
            "failed": compact(self.failed_quests),
            "main_quest_id": self.main_quest.id if self.main_quest else None,
        }

    @classmethod
    def from_save_state(
        cls,
        state: dict[str, Any],
        blueprints: list[dict[str, Any]] | None = None,
    ) -> QuestManager:
        """Restore a validated quest snapshot without replaying progress events."""
        if (not isinstance(state, dict) or type(state.get("version")) is not int
                or state.get("version") != 1):
            raise ValueError("Unsupported quest-save version")
        level = state.get("level")
        kills_total = state.get("kills_total")
        time_survived = state.get("time_survived")
        if type(level) is not int or level < 1:
            raise ValueError("Quest save has an invalid level")
        if type(kills_total) is not int or kills_total < 0:
            raise ValueError("Quest save has an invalid total kill count")
        if (isinstance(time_survived, bool) or not isinstance(time_survived, (int, float))
                or not math.isfinite(time_survived) or time_survived < 0):
            raise ValueError("Quest save has invalid elapsed time")
        kills_by_enemy = state.get("kills_by_enemy")
        if (not isinstance(kills_by_enemy, dict)
                or any(not isinstance(key, str) or type(value) is not int or value < 0
                       for key, value in kills_by_enemy.items())):
            raise ValueError("Quest save has invalid enemy kill counts")

        manager = cls(blueprints)
        manager.active_quests = []
        manager.completed_quests = []
        manager.failed_quests = []
        manager.level = level
        manager.kills_total = kills_total
        manager.kills_by_enemy = dict(kills_by_enemy)
        manager.time_survived = float(time_survived)
        blueprints_by_id = {str(item["id"]): item for item in manager.blueprints}
        seen_ids: set[str] = set()

        for key, target in (
            ("active", manager.active_quests),
            ("completed", manager.completed_quests),
            ("failed", manager.failed_quests),
        ):
            entries = state.get(key)
            if not isinstance(entries, list):
                raise ValueError(f"Quest save has invalid {key} quests")
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError("Quest save entry must be an object")
                quest_id = entry.get("id")
                progress = entry.get("progress")
                if quest_id not in blueprints_by_id or quest_id in seen_ids:
                    raise ValueError("Quest save references an unknown or duplicate quest")
                if (isinstance(progress, bool) or not isinstance(progress, (int, float))
                        or not math.isfinite(progress) or progress < 0):
                    raise ValueError("Quest save has invalid quest progress")
                locked = entry.get("lock_on_accept", False)
                if not isinstance(locked, bool):
                    raise ValueError("Quest save has invalid restriction state")
                quest = manager._build_quest(blueprints_by_id[quest_id])
                quest.progress = float(progress)
                quest.completed = key == "completed"
                quest.failed = key == "failed"
                quest.lock_on_accept = locked
                target.append(quest)
                seen_ids.add(quest_id)

        main_quest_id = state.get("main_quest_id")
        manager.main_quest = next(
            (quest for quest in manager.active_quests + manager.completed_quests + manager.failed_quests
             if quest.id == main_quest_id and quest.quest_type == "main"),
            None,
        )
        if main_quest_id is not None and manager.main_quest is None:
            raise ValueError("Quest save references an invalid main quest")
        return manager

    def lock_main_quest(self, quest_id: str) -> bool:
        return self.set_main_quest_lock(quest_id, True)

    def set_main_quest_lock(
        self,
        quest_id: str,
        locked: bool,
        equipped_items: list[dict[str, Any]] | None = None,
    ) -> bool:
        if (self.main_quest is None or self.main_quest.id != quest_id
                or self.main_quest.completed or self.main_quest.failed):
            return False
        if locked and any(
            self._violates_main_quest_restrictions(item)
            for item in (equipped_items or [])
        ):
            return False
        self.main_quest.lock_on_accept = locked
        return True

    def can_equip(self, item: dict[str, Any]) -> bool:
        """Return whether an item respects an active locked main quest."""
        quest = self.main_quest
        if quest is None or not quest.lock_on_accept or quest.completed or quest.failed:
            return True
        return not self._violates_main_quest_restrictions(item)

    def _violates_main_quest_restrictions(self, item: dict[str, Any]) -> bool:
        quest = self.main_quest
        if quest is None or quest.completed or quest.failed:
            return False
        tags = item.get("tags", [])
        if not isinstance(tags, list):
            return False
        forbidden_tags = {tag.casefold() for tag in quest.forbidden_item_tags}
        return any(
            isinstance(tag, str) and tag.casefold() in forbidden_tags
            for tag in tags
        )
