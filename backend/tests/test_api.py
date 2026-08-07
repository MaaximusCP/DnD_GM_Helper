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
        self.assertEqual(self.client.get("/api/library/search", params={"campaign_id":"demo", "q":"mercat secret"}).status_code, 200)
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


if __name__ == "__main__":
    unittest.main()
