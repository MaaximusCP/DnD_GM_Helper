import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import router
from app.application.adventure_service import AdventureService, AdventureConflict
from app.config import Settings, get_settings
from app.domain.models import AdventureAdvance, CampaignBundle
from app.infrastructure.database import Database
from app.infrastructure.homebrew_catalog import HomebrewCatalog
from app.infrastructure.repository import SQLiteRepository


@pytest.fixture
def setup(tmp_path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_settings] = lambda: Settings(database_path=database.path, homebrew_path=tmp_path / "packs", library_path=tmp_path / "library")
    with TestClient(app) as client:
        yield client, database


def make(client, **changes):
    payload = {"title": "Les ombres del riu", "description": "SECRET-DM-TEST",
               "enemy_groups": [{"resource_id": "hb:jungle:enemy:glass-frond", "quantity": 2, "wave": 1},
                                {"resource_id": "hb:jungle:enemy:root-serpent", "quantity": 1, "wave": 2}]}
    response = client.post("/api/adventures", json={**payload, **changes})
    assert response.status_code == 201, response.text
    return response.json()


def action(client, item, name="advance", **extra):
    return client.post(f"/api/adventures/{item['id']}/{name}", json={"expected_revision": item["data"]["revision"], **extra})


def start(client, item):
    response = client.post(f"/api/adventures/{item['id']}/activate", json={})
    assert response.status_code == 200, response.text
    return response.json()


def test_templates_resources_and_budget(setup):
    client, _ = setup
    templates = client.get("/api/adventures/templates").json()
    assert len(templates) == 6
    for template in templates:
        make(client, **{k:v for k,v in template.items() if k not in {"id", "terrain", "level_hint"}})
    resources = client.get("/api/adventures/resources").json()
    assert {"monsters", "enemy", "minigame", "temple", "situation"} <= {r["category"] for r in resources}
    # Mixed SRD + homebrew use the exact same calculator and snapshots.
    monster = next(r for r in resources if r["category"] == "monsters" and r["data"].get("xp", 0) > 0)
    item = make(client, enemy_groups=[{"resource_id": monster["id"], "quantity": 1, "wave": 1},
                                    {"resource_id":"hb:jungle:enemy:glass-frond","quantity":1,"wave":1}])
    assert item["data"]["budget"]["waves"][0]["multiplier"] == 1.5


@pytest.mark.parametrize("size,multiplier", [(2,1.5),(4,1),(6,0.5)])
def test_party_size_multipliers(setup, size, multiplier):
    client, db = setup
    with db.connect() as conn:
        conn.execute("DELETE FROM characters WHERE campaign_id='demo'")
        conn.execute("INSERT OR REPLACE INTO party_settings(campaign_id,name,level,size,notes) VALUES ('demo','Grup',3,?,'')", (size,))
    response = client.post("/api/adventures/budget", json={"enemy_groups":[{"resource_id":"hb:jungle:enemy:root-serpent"}]})
    assert response.status_code == 200
    assert response.json()["waves"][0]["multiplier"] == multiplier
    assert response.json()["thresholds"][0] == 75 * size


def test_draft_has_no_effects_and_activation_is_once(setup):
    client, db = setup
    with db.connect() as conn:
        before = conn.execute("SELECT COUNT(*) FROM combats").fetchone()[0]
        hex_id = conn.execute("SELECT current_hex_id FROM expedition_state WHERE campaign_id='demo'").fetchone()[0]
        alert = conn.execute("SELECT alert_level FROM hex_cells WHERE id=?", (hex_id,)).fetchone()[0]
    item = make(client, hex_id=hex_id, alert_delta=2, visibility="players")
    assert item["visibility"] == "dm"
    assert item["status"] == "draft"
    start(client, item)
    start(client, item)
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM combats").fetchone()[0] == before
        assert conn.execute("SELECT alert_level FROM hex_cells WHERE id=?", (hex_id,)).fetchone()[0] == min(5, alert+2)
    assert "SECRET-DM-TEST" not in client.get("/api/player-view/demo").text
    assert "Les ombres del riu" not in client.get("/api/player-view/demo").text
    second = make(client)
    assert client.post(f"/api/adventures/{second['id']}/activate", json={}).status_code == 409


def test_wave_progression_conflicts_and_notes(setup):
    client, db = setup
    item = start(client, make(client, include_characters=False))
    response = action(client, item)
    assert response.status_code == 200, response.text
    combat_step = response.json()
    combat_id = combat_step["data"]["combat_id"]
    assert action(client, item).status_code == 409  # A duplicate advance cannot skip a scene.
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM combatants WHERE combat_id=?", (combat_id,)).fetchone()[0] == 2
        conn.execute("UPDATE combats SET turn_index=1 WHERE id=?", (combat_id,))
        active_id = conn.execute("SELECT id FROM combatants WHERE combat_id=? ORDER BY initiative DESC,name", (combat_id,)).fetchall()[1][0]
    assert action(client, combat_step).status_code == 409
    wave = action(client, combat_step, "wave")
    assert wave.status_code == 200, wave.text
    logs = client.get(f"/api/combats/{combat_id}/log")
    assert logs.status_code == 200, logs.text
    assert len(logs.json()) == 2
    assert client.get("/api/campaigns/demo").status_code == 200
    assert action(client, combat_step, "wave").status_code == 409
    with db.connect() as conn:
        ordered = conn.execute("SELECT id FROM combatants WHERE combat_id=? ORDER BY initiative DESC,name", (combat_id,)).fetchall()
        turn = conn.execute("SELECT turn_index FROM combats WHERE id=?", (combat_id,)).fetchone()[0]
        assert len(ordered) == 3 and ordered[turn][0] == active_id
    note = action(client, wave.json(), "note", note="Negociació secreta amb el guardià").json()
    assert note["data"]["notes"][-1]["text"] == "Negociació secreta amb el guardià"
    assert "Negociació secreta" not in client.get("/api/player-view/demo").text
    resolved = action(client, note, force=True).json()
    final = action(client, resolved).json()
    assert final["status"] == "completed"
    assert action(client, final).status_code == 409


def test_ownership_invalid_resource_and_limits(setup):
    client, _ = setup
    other = client.post("/api/campaigns", json={"name":"Altra campanya"}).json()
    for payload in [
        {"campaign_id": other["id"], "hex_id":"hex_demo_1_0"},
        {"campaign_id": other["id"], "location_id":"port_verd"},
        {"situation_id":"hb:jungle:enemy:glass-frond"},
        {"campaign_id":"does-not-exist"},
        {"enemy_groups":[{"resource_id":"missing"}]},
        {"enemy_groups":[{"resource_id":"hb:jungle:enemy:glass-frond","quantity":21}]},
        {"enemy_groups":[{"resource_id":"hb:jungle:enemy:glass-frond","quantity":20}]*4},
    ]:
        assert client.post("/api/adventures", json={"title":"Invalid", **payload}).status_code == 422


def test_atomic_rollback_when_entering_combat_fails(setup):
    client, db = setup
    item = start(client, make(client))
    with db.connect() as conn:
        before = conn.execute("SELECT COUNT(*) FROM combats").fetchone()[0]
    with patch("app.application.adventure_service.AdventureService.release", side_effect=ValueError("Bad pack")):
        assert action(client, item).status_code == 422
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM combats").fetchone()[0] == before
        persisted = json.loads(conn.execute("SELECT data FROM campaign_records WHERE id=?", (item["id"],)).fetchone()[0])
        assert persisted["revision"] == item["data"]["revision"]
        assert "combat_id" not in persisted


def test_generic_record_endpoints_cannot_bypass_runner(setup):
    client, _ = setup
    item = start(client, make(client))
    assert client.post("/api/campaign-records", json={"kind":"adventure","title":"Bypass"}).status_code == 409
    assert client.patch(f"/api/campaign-records/{item['id']}", json={"status":"draft"}).status_code == 409
    assert client.post(f"/api/campaign-records/{item['id']}/duplicate").status_code == 409
    assert client.delete(f"/api/campaign-records/{item['id']}?confirm=true").status_code == 409


def test_export_import_keeps_progress_and_snapshots(setup, tmp_path):
    client, _ = setup
    campaign = client.post("/api/campaigns", json={"name":"Campanya transportable"}).json()
    item = action(client, start(client, make(client, campaign_id=campaign["id"]))).json()
    package = CampaignBundle.model_validate(client.get(f"/api/campaigns/{campaign['id']}/export").json())
    target = Database(Path(tmp_path) / "restored.db")
    target.initialize()
    SQLiteRepository(target).import_campaign(package)
    with target.connect() as conn:
        restored = json.loads(conn.execute("SELECT data FROM campaign_records WHERE id=?", (item["id"],)).fetchone()[0])
        assert restored == item["data"]
        assert conn.execute("SELECT 1 FROM combats WHERE id=?", (restored["combat_id"],)).fetchone()


def test_remote_activation_requires_confirmation(setup):
    client, _ = setup
    item = make(client, hex_id="hex_demo_1_0", alert_delta=1)
    response = client.post(f"/api/adventures/{item['id']}/activate", json={})
    assert response.status_code == 409
    assert client.post(f"/api/adventures/{item['id']}/activate", json={"force":True}).status_code == 200


def test_manual_and_automatic_checks_are_persistent_and_conflict_safe(setup):
    client, _ = setup
    item = start(client, make(client, enemy_groups=[], minigame_id="hb:jungle:minigame:rapids"))
    item = action(client, item).json()
    assert item["data"]["steps"][item["data"]["current_step"]]["kind"] == "minigame"
    checked = action(client, item, "check", d20=20, modifier=-20)
    assert checked.status_code == 200, checked.text
    result = checked.json()["data"]["steps"][1]["check_results"][0]
    assert result["total"] == 0 and result["manual"] and not result["success"]
    assert action(client, item, "check", d20=20).status_code == 409
    assert action(client, checked.json(), "check", d20=21).status_code == 422
    with patch("app.application.adventure_service.secrets.randbelow", return_value=15):
        auto = action(client, checked.json(), "check", modifier=3).json()
    result = auto["data"]["steps"][1]["check_results"][-1]
    assert result["total"] == 19 and not result["manual"]
    assert auto["data"]["current_step"] == 1  # DM decides progress, not a generic success counter.


def test_deleted_combatant_returns_404_not_server_error(setup):
    client, _ = setup
    response = client.patch("/api/combatants/missing", json={"current_hp":1})
    assert response.status_code == 404


def test_simultaneous_wave_requests_apply_only_once(setup):
    client, db = setup
    item = action(client, start(client, make(client, include_characters=False))).json()
    service = AdventureService(db, HomebrewCatalog())
    payload = AdventureAdvance(expected_revision=item["data"]["revision"])

    def release():
        try:
            service.transition(item["id"], payload, "wave")
            return "applied"
        except AdventureConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: release(), range(2)))
    assert sorted(outcomes) == ["applied", "conflict"]
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM combatants WHERE combat_id=?", (item["data"]["combat_id"],)).fetchone()[0] == 3


def test_malformed_private_enemy_fails_before_saving(setup):
    client, db = setup
    resource = {"id":"hb:invalid", "name":"Enemic incomplet", "category":"enemy", "data":{}}
    for stats in [{"xp":"invalid"}, {"hit_points":-2}, {"armor_class":["invalid"]}, {"actions":"invalid"}, {"dexterity":[]}]:
        with patch.object(AdventureService, "resource", return_value={**resource, "data":stats}):
            response = client.post("/api/adventures", json={"title":"Invalid", "enemy_groups":[{"resource_id":"hb:invalid"}]})
        assert response.status_code == 422, response.text
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM campaign_records WHERE kind='adventure'").fetchone()[0] == 0
