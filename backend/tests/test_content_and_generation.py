import tempfile
import unittest
from pathlib import Path

from app.application.document_service import DocumentService
from app.application.generation_service import GenerationService
from app.application.rumor_service import RumorService
from app.domain.models import EncounterRequest, RewardRequest, RumorCreate
from app.infrastructure.content_repository import ContentRepository
from app.infrastructure.database import Database
from app.infrastructure.repository import SQLiteRepository
from app.infrastructure.simulation_repository import SimulationRepository


class ContentAndGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.world = SQLiteRepository(self.database)
        self.simulation = SimulationRepository(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_document_ingestion_search_and_delete(self):
        repository = ContentRepository(self.database)
        service = DocumentService(repository, Path(self.temp_dir.name) / "library")
        source = service.ingest(
            "demo", "Guia del port", "homebrew", "dm", "guia.md",
            "# Port Verd\n\nLa Kara coneix una ruta secreta per sortir del mercat.".encode(),
        )
        self.assertEqual(source.chunk_count, 1)
        results = repository.search("demo", "ruta secreta")
        self.assertEqual(results[0].source_title, "Guia del port")
        with self.assertRaises(ValueError):
            service.ingest("demo", "Duplicat", "homebrew", "dm", "copia.md", "# Port Verd\n\nLa Kara coneix una ruta secreta per sortir del mercat.".encode())
        self.assertTrue(service.delete(source.id))
        self.assertEqual(repository.list_sources("demo"), [])
        image = service.ingest("demo", "Mapa del port", "homebrew", "dm", "mapa.png", b"not-a-real-image-but-local-asset")
        self.assertEqual(image.asset_kind, "map")
        self.assertEqual(image.chunk_count, 0)

    def test_encounter_and_reward_respect_terrain_and_parameters(self):
        engine = GenerationService(self.simulation, self.world)
        encounter = engine.generate_encounter(EncounterRequest(
            terrain="dungeon", party_level=5, party_size=4, difficulty=4,
        ))
        self.assertEqual(encounter.terrain, "dungeon")
        self.assertEqual(encounter.difficulty, 4)
        self.assertTrue(encounter.complications)
        forced = engine.generate_encounter(EncounterRequest(terrain="urban", encounter_type="combat", difficulty=2))
        self.assertEqual(forced.encounter_type, "combat")
        reward = engine.generate_reward(RewardRequest(
            terrain="dungeon", party_level=5, difficulty=4, mode="fortune", fortune_roll=20,
            encounter_id=encounter.id,
        ))
        self.assertEqual(reward.terrain, "dungeon")
        self.assertEqual(reward.tier, "excepcional")
        self.assertEqual(reward.fortune_roll, 20)
        self.assertTrue(reward.items)

    def test_rumor_creates_differentiated_npc_knowledge(self):
        rumor = self.simulation.create_rumor(RumorCreate(
            subject="Expedició desapareguda", content="Es diu que l'expedició no va tornar.",
            credibility=0.55, spread=1.0, origin_location_id="port_verd",
        ))
        learned = RumorService(self.simulation, self.world).propagate(rumor.id)
        self.assertEqual(set(learned), {"kara", "batu", "nyra"})
        kara = self.simulation.list_knowledge("kara")
        self.assertEqual(kara[0].truth_status, "belief")
        self.assertEqual(kara[0].confidence, 0.55)
        self.assertEqual(RumorService(self.simulation, self.world).propagate(rumor.id), [])


if __name__ == "__main__":
    unittest.main()
