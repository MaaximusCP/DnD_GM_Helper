import json
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "srd5e_2014.json"


class ReferenceCatalog:
    """Catàleg SRD de només lectura, local i sense dependències de xarxa."""

    def __init__(self, path: Path = CATALOG_PATH):
        self.path = path

    @staticmethod
    @lru_cache(maxsize=2)
    def _load(path: str) -> dict[str, Any]:
        if not Path(path).is_file():
            return {"items": [], "counts": {}, "license": "CC-BY-4.0"}
        return json.loads(Path(path).read_text(encoding="utf-8"))

    @property
    def data(self) -> dict[str, Any]:
        return self._load(str(self.path))

    def metadata(self) -> dict[str, Any]:
        return {key: value for key, value in self.data.items() if key != "items"}

    def get(self, item_id: str) -> dict[str, Any] | None:
        return next((item for item in self.data["items"] if item["id"] == item_id), None)

    def search(self, query: str = "", category: str | None = None, tag: str | None = None,
               limit: int = 50, offset: int = 0) -> dict[str, Any]:
        needle = query.strip().casefold()
        tag_needle = tag.strip().casefold() if tag else ""
        matches = []
        for item in self.data["items"]:
            if category and item["category"] != category:
                continue
            if tag_needle and tag_needle not in item["tags"]:
                continue
            haystack = f"{item['name']} {item['summary']} {' '.join(item['tags'])}".casefold()
            if needle and needle not in haystack:
                continue
            matches.append(item)
        return {"total": len(matches), "offset": offset, "limit": limit, "items": matches[offset:offset + limit]}

    @staticmethod
    def _choose(items: list[dict[str, Any]]) -> dict[str, Any] | None:
        return items[secrets.randbelow(len(items))] if items else None

    def reward_for_level(self, level: int, difficulty: int) -> dict[str, Any] | None:
        rarity_by_tier = {
            1: {"Common", "Uncommon"}, 2: {"Uncommon", "Rare"},
            3: {"Rare", "Very Rare"}, 4: {"Very Rare", "Legendary"},
        }
        tier = 1 if level <= 4 else 2 if level <= 10 else 3 if level <= 16 else 4
        if difficulty >= 5 and tier < 4:
            tier += 1
        allowed = rarity_by_tier[tier]
        candidates = [item for item in self.data["items"] if item["category"] == "magic-items"
                      and item.get("data", {}).get("rarity", {}).get("name") in allowed]
        return self._choose(candidates)

    def monster_for_level(self, level: int, party_size: int, difficulty: int,
                          terrain: str = "other") -> dict[str, Any] | None:
        multiplier = {1: 0.35, 2: 0.55, 3: 0.8, 4: 1.05, 5: 1.3}[difficulty]
        target = max(0.125, level * max(0.6, party_size / 4) * multiplier)
        candidates = []
        for item in self.data["items"]:
            if item["category"] != "monsters":
                continue
            cr = item.get("data", {}).get("challenge_rating")
            if isinstance(cr, (int, float)) and target * 0.65 <= float(cr) <= target * 1.35:
                candidates.append(item)
        terrain_types = {
            "urban": {"humanoid", "construct"},
            "forest": {"beast", "fey", "plant", "monstrosity"},
            "jungle": {"beast", "plant", "monstrosity", "dragon"},
            "swamp": {"beast", "plant", "monstrosity", "undead"},
            "dungeon": {"aberration", "construct", "fiend", "ooze", "undead"},
            "ruins": {"construct", "monstrosity", "undead"},
            "coast": {"beast", "elemental", "humanoid", "monstrosity"},
            "river": {"beast", "elemental", "monstrosity"},
            "mountain": {"beast", "dragon", "giant", "monstrosity"},
            "desert": {"beast", "elemental", "monstrosity", "undead"},
        }
        preferred = [item for item in candidates if str(item.get("data", {}).get("type", "")).lower()
                     in terrain_types.get(terrain, set())]
        if preferred:
            candidates = preferred
        return self._choose(candidates)
