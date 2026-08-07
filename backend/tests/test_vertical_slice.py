import tempfile
import unittest
from pathlib import Path

from app.application.context_builder import ContextBuilder
from app.application.event_service import EventService
from app.application.backup_service import BackupService
from app.domain.models import EventAnalyzeRequest, MemoryCreate, NPCCreate, NPCUpdate, Relationship
from app.infrastructure.database import Database
from app.infrastructure.repository import SQLiteRepository


class VerticalSliceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Database(Path(self.temp_dir.name) / "test.db")
        database.initialize()
        self.repository = SQLiteRepository(database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seed_contains_campaign_and_three_npcs(self):
        self.assertEqual(len(self.repository.list_campaigns()), 1)
        self.assertEqual(len(self.repository.list_npcs("demo")), 3)

    def test_event_is_proposed_before_it_changes_world(self):
        service = EventService(self.repository)
        proposal = service.analyze(EventAnalyzeRequest(description="El grup ha robat al mercat"))
        self.assertEqual(proposal.status, "pending")
        self.assertEqual(self.repository.get_world_state("demo")["wanted_level"], 0)
        applied = self.repository.apply_event(proposal)
        self.assertEqual(applied.status, "applied")
        self.assertEqual(self.repository.get_world_state("demo")["wanted_level"], 1)

    def test_context_contains_relationship_and_memory(self):
        npc = self.repository.get_npc("kara")
        assert npc is not None
        context, reasons = ContextBuilder(self.repository).build_for_npc(npc, "El grup entra a la botiga")
        self.assertIn("Kara", context)
        self.assertIn("El grup va ajudar", context)
        self.assertTrue(any("Relació" in reason for reason in reasons))

    def test_npc_crud_and_manual_memory(self):
        npc = self.repository.create_npc("demo", NPCCreate(
            name="Iria", location_id="port_verd", traits=["pacient"], goals=["trobar una ruta"],
            relationship=Relationship(trust=12),
        ))
        self.assertEqual(npc.relationship.trust, 12)
        updated = self.repository.update_npc(npc.id, NPCUpdate(name="Iria la Guia", traits=["pacient", "valenta"]))
        assert updated is not None
        self.assertEqual(updated.name, "Iria la Guia")
        self.repository.add_memory(npc.id, MemoryCreate(text="El grup va complir la seva paraula.", importance="important"))
        self.assertEqual(len(self.repository.get_npc(npc.id).memories), 1)  # type: ignore[union-attr]
        self.assertTrue(self.repository.delete_npc(npc.id))
        self.assertIsNone(self.repository.get_npc(npc.id))

    def test_applied_event_can_be_undone_exactly(self):
        proposal = EventService(self.repository).analyze(EventAnalyzeRequest(
            description="El grup ha ajudat la Kara", npc_id="kara"
        ))
        before = self.repository.get_npc("kara")
        self.repository.apply_event(proposal)
        after = self.repository.get_npc("kara")
        assert before is not None and after is not None
        self.assertEqual(after.relationship.trust, before.relationship.trust + 10)
        self.assertEqual(len(after.memories), len(before.memories) + 1)
        undone = self.repository.undo_event(proposal.id)
        restored = self.repository.get_npc("kara")
        assert restored is not None
        self.assertEqual(undone.status, "pending")
        self.assertEqual(restored.relationship.trust, before.relationship.trust)
        self.assertEqual(len(restored.memories), len(before.memories))

    def test_sessions_search_export_and_backup(self):
        session = self.repository.start_session("demo")
        ended = self.repository.end_session(session.id, "El grup prepara l'expedició.")
        assert ended is not None
        self.assertIsNotNone(ended.ended_at)
        self.assertEqual(ended.summary, "El grup prepara l'expedició.")
        self.assertTrue(any(item.id == "kara" for item in self.repository.search("demo", "Kara")))
        package = self.repository.export_campaign("demo")
        assert package is not None
        self.assertEqual(package.campaign.id, "demo")
        self.assertEqual(len(package.npcs), 3)
        backup = BackupService(self.repository.database, Path(self.temp_dir.name) / "backups")
        created = backup.create()
        self.assertTrue(created.is_file())
        self.assertEqual(len(backup.list()), 1)


if __name__ == "__main__":
    unittest.main()
