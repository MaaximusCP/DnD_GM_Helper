import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


BUNDLED_PACK = Path(__file__).resolve().parents[1] / "data" / "homebrew_jungle.json"
ALLOWED_CATEGORIES = {"enemy", "temple", "situation", "minigame"}
REQUIRED_ITEM_FIELDS = {
    "id", "category", "name", "summary", "terrains", "min_level",
    "max_level", "difficulty", "tags", "data",
}


class HomebrewPackError(ValueError):
    pass


class HomebrewCatalog:
    """Catàleg que combina el pack inclòs i packs JSON locals validats."""

    def __init__(self, custom_path: Path | None = None):
        self.custom_path = custom_path

    @staticmethod
    @lru_cache(maxsize=64)
    def _read(path: str, modified_ns: int) -> dict[str, Any]:
        del modified_ns
        return json.loads(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def _load(cls, path: Path) -> dict[str, Any]:
        return cls._read(str(path), path.stat().st_mtime_ns)

    def _paths(self) -> list[Path]:
        custom = [] if self.custom_path is None or not self.custom_path.is_dir() else sorted(self.custom_path.glob("*.json"))
        return [BUNDLED_PACK, *custom]

    @staticmethod
    def validate(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise HomebrewPackError("El pack ha de ser un objecte JSON")
        for field in ("format_version", "id", "name", "version", "license", "items"):
            if field not in payload:
                raise HomebrewPackError(f"Falta el camp obligatori '{field}'")
        if payload["format_version"] != 1:
            raise HomebrewPackError("Només s'admet format_version 1")
        if not isinstance(payload["id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", payload["id"]):
            raise HomebrewPackError("L'identificador del pack no és vàlid")
        if not isinstance(payload["items"], list) or not payload["items"]:
            raise HomebrewPackError("El pack ha de contenir almenys un recurs")
        seen: set[str] = set()
        counts = {category: 0 for category in sorted(ALLOWED_CATEGORIES)}
        for index, item in enumerate(payload["items"], start=1):
            if not isinstance(item, dict) or not REQUIRED_ITEM_FIELDS.issubset(item):
                raise HomebrewPackError(f"El recurs {index} no compleix el contracte base")
            if item["category"] not in ALLOWED_CATEGORIES:
                raise HomebrewPackError(f"Categoria no admesa al recurs {index}")
            if not isinstance(item["id"], str) or item["id"] in seen:
                raise HomebrewPackError(f"Identificador buit o duplicat al recurs {index}")
            if not isinstance(item["name"], str) or not item["name"].strip():
                raise HomebrewPackError(f"Nom buit al recurs {index}")
            if not isinstance(item["terrains"], list) or not all(isinstance(value, str) for value in item["terrains"]):
                raise HomebrewPackError(f"Terrenys no vàlids al recurs {index}")
            if not isinstance(item["tags"], list) or not all(isinstance(value, str) for value in item["tags"]):
                raise HomebrewPackError(f"Etiquetes no vàlides al recurs {index}")
            if not isinstance(item["data"], dict):
                raise HomebrewPackError(f"Data ha de ser un objecte al recurs {index}")
            if not isinstance(item["min_level"], int) or not isinstance(item["max_level"], int) or not 1 <= item["min_level"] <= item["max_level"] <= 20:
                raise HomebrewPackError(f"Rang de nivell no vàlid al recurs {index}")
            if not isinstance(item["difficulty"], int) or not 1 <= item["difficulty"] <= 5:
                raise HomebrewPackError(f"Dificultat no vàlida al recurs {index}")
            seen.add(item["id"])
            counts[item["category"]] += 1
        supplied_counts = payload.get("counts")
        if supplied_counts is not None and supplied_counts != counts:
            raise HomebrewPackError("El recompte declarat no coincideix amb els recursos")
        return {**payload, "counts": counts}

    def _valid_packs(self) -> list[tuple[Path, dict[str, Any]]]:
        packs: list[tuple[Path, dict[str, Any]]] = []
        pack_ids: set[str] = set()
        item_ids: set[str] = set()
        for path in self._paths():
            try:
                payload = self.validate(self._load(path))
            except (OSError, json.JSONDecodeError, HomebrewPackError):
                continue
            if payload["id"] in pack_ids:
                continue
            if any(item["id"] in item_ids for item in payload["items"]):
                continue
            pack_ids.add(payload["id"])
            item_ids.update(item["id"] for item in payload["items"])
            packs.append((path, payload))
        return packs

    def packs(self) -> list[dict[str, Any]]:
        valid_by_path = {path: payload for path, payload in self._valid_packs()}
        result: list[dict[str, Any]] = []
        for path in self._paths():
            payload = valid_by_path.get(path)
            if payload:
                result.append({
                    "id": payload["id"], "name": payload["name"], "version": payload["version"],
                    "license": payload["license"], "counts": payload["counts"],
                    "item_count": len(payload["items"]), "bundled": path == BUNDLED_PACK,
                    "status": "ready", "error": "",
                })
                continue
            try:
                self.validate(self._load(path))
                error = "Identificador de pack o recurs duplicat"
            except (OSError, json.JSONDecodeError, HomebrewPackError) as exc:
                error = str(exc)
            result.append({
                "id": path.stem, "name": path.stem, "version": "", "license": "",
                "counts": {}, "item_count": 0, "bundled": path == BUNDLED_PACK,
                "status": "invalid", "error": error,
            })
        return result

    def metadata(self) -> dict[str, Any]:
        packs = self._valid_packs()
        counts = {category: 0 for category in sorted(ALLOWED_CATEGORIES)}
        for _, pack in packs:
            for category, value in pack["counts"].items():
                counts[category] += value
        return {
            "id": "gm-ai-homebrew", "name": "Packs homebrew locals", "version": "1",
            "license": packs[0][1]["license"] if len(packs) == 1 else "Mixed; consulta cada pack", "counts": counts,
            "pack_count": len(packs), "packs": self.packs(),
        }

    def _items(self) -> list[dict[str, Any]]:
        return [
            {**item, "pack_id": pack["id"], "pack_name": pack["name"]}
            for _, pack in self._valid_packs() for item in pack["items"]
        ]

    def get(self, item_id: str) -> dict[str, Any] | None:
        return next((item for item in self._items() if item["id"] == item_id), None)

    def search(self, query: str = "", category: str | None = None, terrain: str | None = None,
               level: int | None = None, difficulty: int | None = None, pack_id: str | None = None,
               limit: int = 50, offset: int = 0) -> dict[str, Any]:
        needle = query.strip().casefold()
        matches: list[dict[str, Any]] = []
        for item in self._items():
            if category and item["category"] != category:
                continue
            if terrain and terrain not in item.get("terrains", []):
                continue
            if level is not None and not item["min_level"] <= level <= item["max_level"]:
                continue
            if difficulty is not None and item["difficulty"] != difficulty:
                continue
            if pack_id and item["pack_id"] != pack_id:
                continue
            haystack = f"{item['name']} {item['summary']} {' '.join(item.get('tags', []))}".casefold()
            if needle and needle not in haystack:
                continue
            matches.append(item)
        return {"total": len(matches), "offset": offset, "limit": limit,
                "items": matches[offset:offset + limit]}

    def import_pack(self, content: bytes) -> dict[str, Any]:
        if self.custom_path is None:
            raise HomebrewPackError("No hi ha cap directori de packs configurat")
        if not content or len(content) > 1_000_000:
            raise HomebrewPackError("El fitxer ha de tenir entre 1 byte i 1 MB")
        try:
            payload = self.validate(json.loads(content.decode("utf-8-sig")))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HomebrewPackError("El fitxer no és JSON UTF-8 vàlid") from exc
        existing_ids = {pack["id"] for _, pack in self._valid_packs()}
        if payload["id"] in existing_ids:
            raise HomebrewPackError("Ja existeix un pack amb aquest identificador")
        existing_items = {item["id"] for item in self._items()}
        if existing_items.intersection(item["id"] for item in payload["items"]):
            raise HomebrewPackError("El pack conté identificadors de recurs que ja existeixen")
        self.custom_path.mkdir(parents=True, exist_ok=True)
        target = self.custom_path / f"{payload['id']}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
        self._read.cache_clear()
        return next(pack for pack in self.packs() if pack["id"] == payload["id"])

    def delete_pack(self, pack_id: str) -> bool:
        for path, payload in self._valid_packs():
            if payload["id"] == pack_id:
                if path == BUNDLED_PACK:
                    raise HomebrewPackError("El pack inclòs no es pot eliminar")
                path.unlink()
                self._read.cache_clear()
                return True
        return False
