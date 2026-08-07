"""Descarrega el catàleg SRD 5.1 obert i genera un artefacte local reproduïble.

Font de dades: dnd5eapi.co, que exposa el contingut de l'SRD en JSON.
El fitxer resultant conserva procedència i llicència a nivell global i per entrada.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = "https://www.dnd5eapi.co/api/2014"
CATEGORIES = ("magic-items", "equipment", "monsters", "spells")
ATTRIBUTION = (
    "This work includes material taken from the System Reference Document 5.1 "
    '(“SRD 5.1”) by Wizards of the Coast LLC and available at '
    "https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 "
    "is licensed under the Creative Commons Attribution 4.0 International License "
    "available at https://creativecommons.org/licenses/by/4.0/legalcode."
)


def fetch_json(url: str, retries: int = 3) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "GM-AI-SRD-Importer/0.4"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError("No s'ha pogut obtenir la font SRD")


def compact(category: str, raw: dict[str, Any]) -> dict[str, Any]:
    ignored = {"url", "updated_at", "image"}
    data = {key: value for key, value in raw.items() if key not in ignored}
    name = str(data.pop("name", raw.get("index", "Entrada SRD")))
    key = str(data.pop("index", raw.get("index", name.lower().replace(" ", "-"))))
    tags: list[str] = [category]
    for field in ("type", "size", "alignment", "weapon_category", "armor_category"):
        if data.get(field):
            tags.append(str(data[field]).lower())
    for field in ("rarity", "school", "equipment_category", "gear_category"):
        value = data.get(field)
        if isinstance(value, dict) and value.get("name"):
            tags.append(str(value["name"]).lower())
    summary_parts = data.get("desc") or []
    if isinstance(summary_parts, str):
        summary_parts = [summary_parts]
    summary = " ".join(str(item) for item in summary_parts[:2])[:1200]
    return {
        "id": f"srd51:{category}:{key}", "category": category, "key": key,
        "name": name, "summary": summary, "tags": sorted(set(tags)), "data": data,
        "source": "SRD 5.1 via dnd5eapi.co", "license": "CC-BY-4.0",
    }


def build_catalog() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for category in CATEGORIES:
        listing = fetch_json(f"{BASE_URL}/{category}")
        resources = listing.get("results", [])
        urls = [f"https://www.dnd5eapi.co{resource['url']}" for resource in resources]
        with ThreadPoolExecutor(max_workers=12) as executor:
            details = list(executor.map(fetch_json, urls))
        items.extend(compact(category, detail) for detail in details)
        print(f"{category}: {len(resources)}")
        counts[category] = len(resources)
    return {
        "format_version": 1,
        "dataset": "D&D 5e SRD 5.1 (2014 rules)",
        "source_url": "https://www.dnd5eapi.co/",
        "official_srd_url": "https://www.dndbeyond.com/srd",
        "license": "CC-BY-4.0",
        "attribution": ATTRIBUTION,
        "counts": counts,
        "items": sorted(items, key=lambda item: (item["category"], item["name"])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el catàleg local SRD de GM AI")
    parser.add_argument("--output", type=Path, default=Path("backend/app/data/srd5e_2014.json"))
    args = parser.parse_args()
    catalog = build_catalog()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(catalog["counts"], ensure_ascii=False))
    print(f"Desat: {args.output} ({args.output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
