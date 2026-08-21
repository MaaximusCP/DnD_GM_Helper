import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import get_backup_service, get_content_repository, get_repository, get_simulation_repository, router
from app.application.backup_service import BackupService
from app.config import Settings, get_settings
from app.infrastructure.database import Database
from app.infrastructure.content_repository import ContentRepository
from app.infrastructure.repository import SQLiteRepository
from app.infrastructure.simulation_repository import SimulationRepository


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Database(Path(self.temp_dir.name) / "api.db")
        database.initialize()
        self.repository = SQLiteRepository(database)
        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_repository] = lambda: self.repository
        app.dependency_overrides[get_content_repository] = lambda: ContentRepository(database)
        app.dependency_overrides[get_simulation_repository] = lambda: SimulationRepository(database)
        app.dependency_overrides[get_settings] = lambda: Settings(
            database_path=database.path, library_path=Path(self.temp_dir.name) / "library"
        )
        app.dependency_overrides[get_backup_service] = lambda: BackupService(database, Path(self.temp_dir.name) / "backups")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def test_dashboard_session_and_search(self):
        dashboard = self.client.get("/api/campaigns/demo")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(len(dashboard.json()["npcs"]), 3)
        session = self.client.post("/api/sessions?campaign_id=demo")
        self.assertEqual(session.status_code, 201)
        self.assertEqual(self.client.post("/api/sessions?campaign_id=demo").status_code, 409)
        ended = self.client.post(f"/api/sessions/{session.json()['id']}/end", json={"summary": "Final local"})
        self.assertEqual(ended.status_code, 200)
        self.assertIsNotNone(ended.json()["ended_at"])
        search = self.client.get("/api/search", params={"campaign_id": "demo", "q": "Kara"})
        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.json()[0]["kind"], "npc")

    def test_npc_event_undo_export_and_backup(self):
        npc = self.client.post("/api/npcs?campaign_id=demo", json={
            "name": "Iria", "location_id": "port_verd", "traits": ["pacient"],
            "goals": ["guiar el grup"], "values": [],
            "relationship": {"trust": 0, "respect": 0, "fear": 0, "affection": 0},
        })
        self.assertEqual(npc.status_code, 201)
        event = self.client.post("/api/events/analyze", json={
            "campaign_id": "demo", "description": "El grup ha ajudat Iria", "npc_id": npc.json()["id"],
        })
        self.assertEqual(event.status_code, 201)
        event_id = event.json()["id"]
        edited = self.client.patch(f"/api/events/{event_id}", json={"severity": 5})
        self.assertEqual(edited.json()["severity"], 5)
        self.assertEqual(self.client.post(f"/api/events/{event_id}/apply").status_code, 200)
        self.assertEqual(len(self.client.get("/api/rumors?campaign_id=demo").json()), 1)
        self.assertEqual(self.client.post(f"/api/events/{event_id}/undo").json()["status"], "pending")
        self.assertEqual(len(self.client.get("/api/rumors?campaign_id=demo").json()), 0)
        private_event = self.client.post("/api/events/analyze", json={
            "campaign_id":"demo", "description":"El grup parla en secret", "visibility":"private",
        }).json()
        self.assertEqual(self.client.post(f"/api/events/{private_event['id']}/apply").status_code, 200)
        self.assertEqual(len(self.client.get("/api/rumors?campaign_id=demo").json()), 0)
        self.assertEqual(self.client.get("/api/campaigns/demo/export").status_code, 200)
        backup = self.client.post("/api/backups")
        self.assertEqual(backup.status_code, 201)
        self.assertEqual(len(self.client.get("/api/backups").json()), 1)
        self.assertEqual(self.client.post(f"/api/backups/{backup.json()['name']}/restore").status_code, 422)
        restored = self.client.post(f"/api/backups/{backup.json()['name']}/restore", json={"confirm": "RESTORE"})
        self.assertEqual(restored.status_code, 200)
        self.assertIn("safety_backup", restored.json())

    def test_library_encounter_reward_and_knowledge_endpoints(self):
        uploaded = self.client.post("/api/library/upload", data={
            "campaign_id": "demo", "title": "Notes locals", "source_type": "notes", "visibility": "dm",
        }, files={"file": ("notes.md", b"La Kara coneix el mercat secret.", "text/markdown")})
        self.assertEqual(uploaded.status_code, 201)
        search = self.client.get("/api/library/search", params={"campaign_id":"demo", "q":"mercat secret"})
        self.assertEqual(search.status_code, 200)
        chunk_id = search.json()[0]["chunk_id"]
        lore = self.client.post("/api/campaigns/demo/library/lore", json={
            "chunk_id": chunk_id, "layer": "dm", "category": "location", "title": "Mercat secret",
        })
        self.assertEqual(lore.status_code, 201)
        self.assertEqual(lore.json()["source_id"], uploaded.json()["id"])
        patched = self.client.patch(f"/api/library/{uploaded.json()['id']}", json={"visibility":"players"})
        self.assertEqual(patched.json()["visibility"], "players")
        asset = self.client.get(f"/api/library/{uploaded.json()['id']}/asset")
        self.assertEqual(asset.status_code, 200)
        player_sources = self.client.get("/api/player-view/demo").json()["sources"]
        self.assertEqual(player_sources[0]["id"], uploaded.json()["id"])
        self.assertNotIn("file_path", player_sources[0])
        self.assertNotIn("checksum", player_sources[0])
        knowledge = self.client.post("/api/npcs/kara/knowledge", json={
            "subject":"Mercat", "content":"Coneix el mercat secret", "confidence":1,
            "truth_status":"fact", "source_type":"manual",
        })
        self.assertEqual(knowledge.status_code, 201)
        encounter = self.client.post("/api/encounters/generate", json={
            "campaign_id":"demo", "terrain":"jungle", "party_level":4, "party_size":4,
            "difficulty":3, "encounter_type":"auto",
        })
        self.assertEqual(encounter.status_code, 201)
        reward = self.client.post("/api/rewards/generate", json={
            "campaign_id":"demo", "terrain":"jungle", "party_level":4, "difficulty":3,
            "mode":"neutral", "encounter_id":encounter.json()["id"],
        })
        self.assertEqual(reward.status_code, 201)
        self.assertEqual(reward.json()["terrain"], "jungle")

    def test_knowledge_layers_hexcrawl_and_combat_assistant(self):
        dashboard = self.client.get("/api/campaigns/demo").json()
        self.assertEqual({item["layer"] for item in dashboard["lore_entries"]}, {"dm", "players", "world"})
        self.assertGreaterEqual(len(dashboard["hex_cells"]), 5)
        self.assertEqual(dashboard["combats"][0]["combatants"][0]["initiative"], 16)

        lore = self.client.post("/api/lore", json={
            "campaign_id": "demo", "layer": "players", "category": "location",
            "title": "Gual descobert", "content": "El grup ja coneix un pas segur pel riu.",
        })
        self.assertEqual(lore.status_code, 201)
        self.assertEqual(self.client.get("/api/lore", params={"campaign_id":"demo", "layer":"players"}).status_code, 200)

        hex_cell = self.client.post("/api/hexes", json={
            "campaign_id":"demo", "q":3, "r":2, "terrain":"jungle", "title":"Dosser espès",
            "discovery":"hidden", "travel_cost":3, "encounter_chance":35,
            "player_notes":"", "dm_notes":"Petjades al nord",
        })
        self.assertEqual(hex_cell.status_code, 201)
        revealed = self.client.patch(f"/api/hexes/{hex_cell.json()['id']}", json={"discovery":"discovered"})
        self.assertEqual(revealed.json()["discovery"], "discovered")
        self.assertEqual(self.client.post("/api/hexes", json={
            "campaign_id":"demo", "q":3, "r":2, "title":"Duplicat",
        }).status_code, 409)

        combat = self.client.post("/api/combats", json={"campaign_id":"demo", "name":"Prova de combat"})
        combat_id = combat.json()["id"]
        combatant = self.client.post(f"/api/combats/{combat_id}/combatants", json={
            "name":"Guerrer de prova", "kind":"enemy", "initiative":17,
            "armor_class":14, "max_hp":20, "actions":[{"name":"Llança", "description":"1d6"}],
        })
        self.assertEqual(combatant.json()["current_hp"], 20)
        reference_combatant = self.client.post(f"/api/combats/{combat_id}/combatants/from-reference", json={
            "reference_id":"srd51:monsters:goblin", "initiative":12,
        })
        self.assertEqual(reference_combatant.status_code, 201)
        self.assertEqual(reference_combatant.json()["reference_id"], "srd51:monsters:goblin")
        self.assertTrue(reference_combatant.json()["actions"])
        damaged = self.client.patch(f"/api/combatants/{combatant.json()['id']}", json={"current_hp":7, "conditions":["enverinat"]})
        self.assertEqual(damaged.json()["current_hp"], 7)
        next_turn = self.client.post(f"/api/combats/{combat_id}/next-turn").json()
        self.assertEqual(next_turn["turn_index"], 1)
        self.assertEqual(self.client.post(f"/api/combats/{combat_id}/next-turn").json()["round"], 2)
        exported = self.client.get("/api/campaigns/demo/export").json()
        self.assertIn("lore_entries", exported)
        self.assertIn("hex_cells", exported)
        self.assertIn("combats", exported)

    def test_modular_travel_player_projection_and_advanced_combat(self):
        dashboard = self.client.get("/api/campaigns/demo").json()
        self.assertTrue(dashboard["hexcrawl_settings"]["track_water"])
        self.assertEqual(dashboard["expedition_state"]["current_hex_id"], "hex_demo_0_0")

        disabled = self.client.patch("/api/campaigns/demo/hexcrawl-settings", json={
            "track_weather":False, "track_navigation":False, "track_food":False,
            "track_water":False, "track_fatigue":False, "track_encounters":False,
            "track_foraging":False,
        })
        self.assertEqual(disabled.status_code, 200)
        travel = self.client.post("/api/campaigns/demo/travel", json={
            "destination_hex_id":"hex_demo_1_0", "pace":"fast",
        })
        self.assertEqual(travel.status_code, 201)
        self.assertEqual(travel.json()["food_used"], 0)
        self.assertEqual(travel.json()["weather"], "ignored")
        self.assertTrue(travel.json()["reached_destination"])

        enabled = self.client.patch("/api/campaigns/demo/hexcrawl-settings", json={
            "track_weather":True, "track_navigation":True, "track_food":True,
            "track_water":True, "track_fatigue":True, "track_encounters":True,
            "track_foraging":True,
        })
        self.assertEqual(enabled.status_code, 200)
        encounter_travel = self.client.post("/api/campaigns/demo/travel", json={
            "destination_hex_id":"hex_demo_1_1", "pace":"normal", "navigation_roll":20,
            "encounter_roll":1, "foraging_roll":20, "manual_weather":"clear",
        })
        self.assertEqual(encounter_travel.status_code, 201)
        self.assertTrue(encounter_travel.json()["encounter_triggered"])
        self.assertIsNotNone(encounter_travel.json()["encounter_id"])

        player = self.client.get("/api/player-view/demo")
        self.assertEqual(player.status_code, 200)
        serialized = player.text
        self.assertNotIn("sabotatge", serialized.lower())
        self.assertNotIn("dm_notes", serialized)
        self.assertNotIn("petjades recents", serialized.lower())
        self.assertTrue(all(item["discovery"] != "hidden" for item in player.json()["hexes"]))
        self.assertEqual(self.client.patch("/api/campaigns/demo/player-view-settings", json={"enabled":False}).status_code, 200)
        self.assertEqual(self.client.get("/api/player-view/demo").status_code, 403)

        combat_id = "combat_demo"
        combatant_id = "combatant_demo_goblin"
        advanced = self.client.patch(f"/api/combatants/{combatant_id}", json={
            "temp_hp":5, "concentration":True, "reaction_available":False,
            "legendary_actions":1, "legendary_actions_max":2, "conditions":["enverinat"],
        })
        self.assertEqual(advanced.status_code, 200)
        self.assertEqual(advanced.json()["temp_hp"], 5)
        self.assertTrue(advanced.json()["concentration"])
        duplicated = self.client.post(f"/api/combatants/{combatant_id}/duplicate", json={"quantity":2})
        self.assertEqual(len(duplicated.json()), 2)
        initiative = self.client.post(f"/api/combats/{combat_id}/initiative", json={"automatic":True})
        self.assertEqual(initiative.status_code, 200)
        rolled = self.client.post(f"/api/combats/{combat_id}/roll", json={"notation":"2d6+3", "label":"Dany"})
        self.assertEqual(rolled.status_code, 200)
        self.assertGreaterEqual(rolled.json()["total"], 5)
        self.assertTrue(self.client.get(f"/api/combats/{combat_id}/log").json())

    def test_campaign_studio_world_party_and_custom_tables(self):
        created = self.client.post("/api/campaigns", json={
            "name": "Campanya pròpia", "system": "dnd5e",
            "rules_profile": "campaign_default", "location_name": "Vila inicial",
        })
        self.assertEqual(created.status_code, 201)
        campaign = created.json()
        campaign_id = campaign["id"]
        original_location = campaign["current_location_id"]

        dashboard = self.client.get(f"/api/campaigns/{campaign_id}")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["party"]["level"], 3)
        self.assertEqual(dashboard.json()["generation_tables"], [])

        party = self.client.put(f"/api/campaigns/{campaign_id}/party", json={
            "name": "Companyia del Sol", "level": 6, "size": 5, "notes": "Sense clergue",
        })
        self.assertEqual(party.json()["level"], 6)

        location = self.client.post(f"/api/campaigns/{campaign_id}/locations", json={
            "name": "Temple enfonsat", "description": "Ruïnes sota la selva", "terrain": "ruins",
        })
        location_id = location.json()["id"]
        edited = self.client.patch(f"/api/locations/{location_id}", json={"terrain": "dungeon"})
        self.assertEqual(edited.json()["terrain"], "dungeon")
        self.assertEqual(self.client.patch(f"/api/campaigns/{campaign_id}", json={
            "current_location_id": location_id, "current_day": 4,
        }).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/locations/{original_location}?confirm=true").status_code, 204)

        faction = self.client.post(f"/api/campaigns/{campaign_id}/factions", json={
            "name": "Cartògrafs", "description": "Exploren les ruïnes",
        })
        faction_id = faction.json()["id"]
        self.assertEqual(self.client.patch(f"/api/factions/{faction_id}", json={
            "description": "Exploren i protegeixen les ruïnes",
        }).status_code, 200)
        state = self.client.put(f"/api/campaigns/{campaign_id}/world-state/clima", json={"value": "tempesta"})
        self.assertEqual(state.json()["clima"], "tempesta")
        self.assertEqual(self.client.delete(f"/api/campaigns/{campaign_id}/world-state/clima?confirm=true").status_code, 204)

        table = self.client.post("/api/generation-tables", json={
            "campaign_id": campaign_id, "kind": "encounter", "name": "Ruïnes pròpies",
        })
        table_id = table.json()["id"]
        entry = self.client.post(f"/api/generation-tables/{table_id}/entries", json={
            "terrains": ["dungeon"], "min_level": 2, "max_level": 8,
            "min_difficulty": 2, "max_difficulty": 5, "weight": 3,
            "title": "Guardià adormit", "payload": {"type": "combat"}, "tags": ["homebrew"],
        })
        self.assertEqual(entry.status_code, 201)
        self.assertEqual(len(self.client.get(f"/api/generation-tables/{table_id}/entries").json()), 1)
        self.assertEqual(self.client.delete(f"/api/generation-tables/{table_id}?confirm=true").status_code, 204)
        self.assertEqual(self.client.patch(f"/api/campaigns/{campaign_id}", json={"archived": True}).json()["archived"], True)

    def test_hex_zone_rest_and_encounter_to_combat_flow(self):
        revealed = self.client.post("/api/campaigns/demo/hexes/reveal", json={
            "center_hex_id": "hex_demo_0_0", "radius": 1, "discovery": "explored",
        })
        self.assertEqual(revealed.status_code, 200)
        self.assertGreaterEqual(len(revealed.json()), 3)
        self.assertTrue(all(item["discovery"] == "explored" for item in revealed.json()))

        self.assertEqual(self.client.delete("/api/hexes/hex_demo_0_0?confirm=true").status_code, 409)
        disposable = self.client.post("/api/hexes", json={
            "campaign_id": "demo", "q": 9, "r": 9, "title": "Hex temporal",
        })
        self.assertEqual(disposable.status_code, 201)
        self.assertEqual(self.client.delete(f"/api/hexes/{disposable.json()['id']}?confirm=true").status_code, 204)

        self.client.patch("/api/campaigns/demo/expedition", json={
            "food": 20, "water": 40, "supplies": 5, "exhaustion": 2, "lost": True,
        })
        day_before = self.client.get("/api/campaigns/demo").json()["campaign"]["current_day"]
        rested = self.client.post("/api/campaigns/demo/rest", json={
            "rest_type": "long", "consume_resources": True, "safe_camp": True,
        })
        self.assertEqual(rested.status_code, 201)
        self.assertEqual(rested.json()["state"]["food"], 16)
        self.assertEqual(rested.json()["state"]["water"], 32)
        self.assertEqual(rested.json()["state"]["supplies"], 4)
        self.assertEqual(rested.json()["state"]["exhaustion"], 1)
        self.assertFalse(rested.json()["state"]["lost"])
        self.assertEqual(rested.json()["log"]["pace"], "rest_long")
        self.assertEqual(self.client.get("/api/campaigns/demo").json()["campaign"]["current_day"], day_before + 1)

        encounter = self.client.post("/api/encounters/generate", json={
            "campaign_id": "demo", "terrain": "jungle", "party_level": 4,
            "party_size": 4, "difficulty": 3, "encounter_type": "combat",
        })
        self.assertEqual(encounter.status_code, 201)
        prepared = self.client.post(f"/api/encounters/{encounter.json()['id']}/combat", json={
            "quantity": 2, "roll_initiative": True,
        })
        self.assertEqual(prepared.status_code, 201)
        self.assertEqual(prepared.json()["encounter_id"], encounter.json()["id"])
        self.assertEqual(len(prepared.json()["combatants"]), 2)
        self.assertTrue(all(item["reference_id"] for item in prepared.json()["combatants"]))
        self.assertEqual(self.client.post(f"/api/encounters/{encounter.json()['id']}/combat", json={}).status_code, 409)

        completed = self.client.patch(f"/api/combats/{prepared.json()['id']}", json={
            "status": "completed", "summary": "Victòria del grup",
        })
        self.assertEqual(completed.status_code, 200)
        encounters = self.client.get("/api/encounters", params={"campaign_id": "demo"}).json()
        resolved = next(item for item in encounters if item["id"] == encounter.json()["id"])
        self.assertEqual(resolved["status"], "resolved")

    def test_local_srd_reference_catalog(self):
        metadata = self.client.get("/api/reference/meta")
        self.assertEqual(metadata.status_code, 200)
        self.assertEqual(metadata.json()["license"], "CC-BY-4.0")
        self.assertEqual(metadata.json()["counts"]["magic-items"], 362)
        results = self.client.get("/api/reference", params={
            "category": "magic-items", "q": "Bag of Holding", "limit": 10,
        })
        self.assertEqual(results.status_code, 200)
        self.assertGreaterEqual(results.json()["total"], 1)
        item = results.json()["items"][0]
        detail = self.client.get(f"/api/reference/item/{item['id']}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["license"], "CC-BY-4.0")

    def test_party_inventory_treasury_reward_and_combat_sync(self):
        dashboard = self.client.get("/api/campaigns/demo").json()
        self.assertEqual(len(dashboard["characters"]), 3)
        character = self.client.post("/api/characters", json={
            "campaign_id": "demo", "name": "Test Hero", "class_name": "Bard",
            "level": 4, "armor_class": 15, "max_hp": 30,
            "resources": [{"name": "Inspiracio", "current": 0, "maximum": 1, "reset": "long"}],
        })
        self.assertEqual(character.status_code, 201)
        character_id = character.json()["id"]
        item = self.client.post("/api/inventory", json={
            "campaign_id": "demo", "owner_type": "character", "owner_id": character_id,
            "name": "Pocio de prova", "category": "consumable", "quantity": 2, "consumable": True,
        })
        self.assertEqual(item.status_code, 201)
        consumed = self.client.post(f"/api/inventory/{item.json()['id']}/consume", json={"quantity": 1})
        self.assertEqual(consumed.json()["item"]["quantity"], 1)
        adjusted = self.client.post("/api/campaigns/demo/treasury/adjust", json={
            "currency": "gp", "amount": 25, "description": "Venda",
        })
        self.assertEqual(adjusted.json()["gp"], 150)

        reward = self.client.post("/api/rewards/generate", json={
            "campaign_id": "demo", "terrain": "jungle", "party_level": 4, "difficulty": 3,
        }).json()
        claimed = self.client.post(f"/api/rewards/{reward['id']}/claim", json={"owner_type": "party"})
        self.assertEqual(claimed.status_code, 200)
        self.assertTrue(claimed.json()["reward"]["claimed"])
        self.assertEqual(self.client.post(f"/api/rewards/{reward['id']}/claim", json={}).status_code, 409)

        combat = self.client.post("/api/combats", json={"campaign_id": "demo", "name": "Prova"}).json()
        linked = self.client.post(f"/api/combats/{combat['id']}/characters", json={
            "character_ids": [character_id], "roll_initiative": False,
        })
        self.assertEqual(linked.status_code, 201)
        combatant = linked.json()["combatants"][0]
        self.assertEqual(combatant["character_id"], character_id)
        self.client.patch(f"/api/combatants/{combatant['id']}", json={"current_hp": 7, "conditions": ["poisoned"]})
        updated = next(x for x in self.client.get("/api/characters?campaign_id=demo").json() if x["id"] == character_id)
        self.assertEqual(updated["current_hp"], 7)
        self.assertEqual(updated["conditions"], ["poisoned"])
        rested = self.client.post("/api/campaigns/demo/rest", json={
            "rest_type": "long", "consume_resources": False, "safe_camp": True,
        })
        self.assertIn("Test Hero", rested.json()["characters_recovered"])
        refreshed = next(x for x in self.client.get("/api/characters?campaign_id=demo").json() if x["id"] == character_id)
        self.assertEqual(refreshed["current_hp"], 30)
        self.assertEqual(refreshed["resources"][0]["current"], 1)
        combat_after_rest = next(x for x in self.client.get("/api/combats?campaign_id=demo").json() if x["id"] == combat["id"])
        linked_after_rest = next(x for x in combat_after_rest["combatants"] if x["character_id"] == character_id)
        self.assertEqual(linked_after_rest["current_hp"], 30)
        player = self.client.get("/api/player-view/demo").json()
        self.assertTrue(any(x["id"] == character_id for x in player["characters"]))
        self.assertIsNotNone(player["treasury"])

    def test_v09_operations_session_resolution_and_hexcrawl_risk(self):
        session = self.client.post("/api/sessions?campaign_id=demo").json()
        quest = self.client.post("/api/campaign-records", json={
            "campaign_id": "demo", "kind": "quest", "title": "Trobar el temple",
            "visibility": "players", "due_day": 8, "data": {"objectives": ["Seguir el mapa"]},
        })
        clock = self.client.post("/api/campaign-records", json={
            "campaign_id": "demo", "kind": "clock", "title": "Alerta yuan-ti",
            "data": {"current": 0, "maximum": 4, "consequence": "Arriben reforcos"},
        })
        self.assertEqual(quest.status_code, 201)
        self.assertEqual(clock.status_code, 201)
        duplicated = self.client.post(f"/api/campaign-records/{quest.json()['id']}/duplicate")
        self.assertEqual(duplicated.status_code, 201)
        self.assertTrue(duplicated.json()["title"].startswith("Còpia de"))
        self.client.patch("/api/hexes/hex_demo_1_0", json={
            "risk_level": 4, "alert_level": 2, "risk_tags": ["malaltia", "patrulles"],
        })
        travelled = self.client.post("/api/campaigns/demo/travel", json={
            "destination_hex_id": "hex_demo_1_0", "pace": "fast",
            "navigation_roll": 20, "encounter_roll": 100, "foraging_roll": 20,
        })
        self.assertEqual(travelled.status_code, 201)
        destination = next(x for x in self.client.get("/api/campaigns/demo").json()["hex_cells"] if x["id"] == "hex_demo_1_0")
        self.assertEqual(destination["risk_level"], 4)
        self.assertEqual(destination["risk_tags"], ["malaltia", "patrulles"])
        self.assertGreaterEqual(destination["alert_level"], 3)

        encounter = self.client.post("/api/encounters/generate", json={
            "campaign_id": "demo", "terrain": "jungle", "party_level": 4,
            "party_size": 4, "difficulty": 3, "encounter_type": "combat",
        }).json()
        before_xp = sum(x["xp"] for x in self.client.get("/api/characters?campaign_id=demo").json())
        resolved = self.client.post(f"/api/encounters/{encounter['id']}/resolve", json={
            "outcome": "victory", "summary": "El grup supera l'emboscada", "xp": 900,
            "advance_clock_id": clock.json()["id"], "clock_steps": 2,
            "quest_id": quest.json()["id"], "quest_status": "completed", "generate_reward": True,
        })
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["clock"]["data"]["current"], 2)
        self.assertEqual(resolved.json()["quest"]["status"], "completed")
        self.assertIsNotNone(resolved.json()["reward"])
        after_xp = sum(x["xp"] for x in self.client.get("/api/characters?campaign_id=demo").json())
        self.assertGreater(after_xp, before_xp)
        player = self.client.get("/api/player-view/demo").json()
        self.assertTrue(any(x["id"] == quest.json()["id"] for x in player["quests"]))
        closed = self.client.post(f"/api/sessions/{session['id']}/close", json={"summary": "", "share_summary": True})
        self.assertEqual(closed.status_code, 200)
        self.assertIn("Resum autom", closed.json()["summary"])
        self.assertGreaterEqual(len(closed.json()["activities"]), 2)


    def test_v1_templates_and_reviewable_npc_downtime(self):
        templates = self.client.get("/api/campaign-templates")
        self.assertEqual(templates.status_code, 200)
        self.assertEqual(len(templates.json()), 4)
        created = self.client.post("/api/campaign-templates/create", json={
            "template_id": "urban_intrigue", "name": "Ombres de la ciutat",
        })
        self.assertEqual(created.status_code, 201)
        campaign_id = created.json()["id"]
        dashboard = self.client.get(f"/api/campaigns/{campaign_id}").json()
        self.assertGreaterEqual(len(dashboard["locations"]), 3)
        self.assertEqual(len([npc for npc in dashboard["npcs"] if npc["active"]]), 2)
        self.assertGreaterEqual(len(dashboard["hex_cells"]), 5)

        day_before = dashboard["campaign"]["current_day"]
        result = self.client.post(f"/api/campaigns/{campaign_id}/npc-actions", json={
            "days": 3, "advance_calendar": True,
        })
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()["current_day"], day_before + 3)
        self.assertEqual(len(result.json()["proposals"]), 2)
        self.assertTrue(all(item["status"] == "pending" for item in result.json()["proposals"]))
        npc = dashboard["npcs"][0]
        before_memories = len(npc["memories"])
        proposal = result.json()["proposals"][0]
        self.assertEqual(self.client.post(f"/api/events/{proposal['id']}/apply").status_code, 200)
        affected = self.client.get(f"/api/npcs/{proposal['consequences'][0]['target_id']}").json()
        self.assertGreaterEqual(len(affected["memories"]), before_memories)

    def test_v1_session_dice_tray_and_srd_conditions(self):
        rolled = self.client.post("/api/campaigns/demo/dice-rolls", json={
            "notation": "1d20+5", "label": "Percepció", "actor": "Aria",
            "mode": "advantage", "dc": 12,
        })
        self.assertEqual(rolled.status_code, 201)
        result = rolled.json()
        self.assertEqual(len(result["dice"]), 2)
        self.assertEqual(result["kept"], [max(result["dice"])])
        self.assertEqual(result["total"], result["kept"][0] + 5)
        self.assertEqual(result["success"], result["total"] >= 12)
        self.assertEqual(len(self.client.get("/api/campaigns/demo/dice-rolls").json()), 1)
        exported = self.client.get("/api/campaigns/demo/export")
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.json()["dice_rolls"][0]["id"], result["id"])
        invalid = self.client.post("/api/campaigns/demo/dice-rolls", json={
            "notation": "2d6", "label": "Dany", "mode": "advantage",
        })
        self.assertEqual(invalid.status_code, 422)
        cleared = self.client.delete("/api/campaigns/demo/dice-rolls?confirm=true")
        self.assertEqual(cleared.json()["deleted"], 1)

        conditions = self.client.get("/api/reference", params={"category": "conditions", "limit": 100})
        self.assertEqual(conditions.status_code, 200)
        self.assertGreaterEqual(conditions.json()["total"], 15)
        self.assertTrue(any(item["key"] == "poisoned" for item in conditions.json()["items"]))


if __name__ == "__main__":
    unittest.main()
