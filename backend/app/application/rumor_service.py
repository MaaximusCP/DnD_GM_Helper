import hashlib
import random

from app.domain.models import EventProposal, KnowledgeCreate, Rumor, RumorCreate
from app.infrastructure.repository import SQLiteRepository
from app.infrastructure.simulation_repository import SimulationRepository


class RumorService:
    def __init__(self, repository: SimulationRepository, world_repository: SQLiteRepository):
        self.repository = repository
        self.world_repository = world_repository

    def generate_from_event(self, event: EventProposal) -> Rumor | None:
        if event.visibility == "private" or event.severity < 3:
            return None
        existing = self.repository.get_rumor_by_event(event.id)
        if existing:
            return existing
        prefix = "Corre la veu que" if event.visibility == "public" else "Alguns testimonis afirmen que"
        return self.repository.create_rumor(RumorCreate(
            campaign_id=event.campaign_id, origin_location_id=event.location_id,
            subject=event.title, content=f"{prefix} {event.description.rstrip('.').lower()}.",
            credibility=0.8 if event.visibility == "public" else 0.6,
            spread=min(0.9, 0.15 + event.severity * 0.07), source_event_id=event.id,
        ))

    def propagate(self, rumor_id: str) -> list[str]:
        rumor = self.repository.get_rumor(rumor_id)
        if not rumor or rumor.status != "active":
            raise ValueError("Rumor no trobat o inactiu")
        learned: list[str] = []
        for npc in self.world_repository.list_npcs(rumor.campaign_id):
            if self.repository.has_knowledge_source(npc.id, rumor.id):
                continue
            seed = int(hashlib.sha256(f"{rumor.id}:{npc.id}".encode()).hexdigest()[:16], 16)
            chance = rumor.spread + (0.2 if npc.location_id == rumor.origin_location_id else 0)
            if random.Random(seed).random() <= min(chance, 0.98):
                self.repository.add_knowledge(npc.id, KnowledgeCreate(
                    subject=rumor.subject, content=rumor.content, confidence=rumor.credibility,
                    truth_status="belief", source_type="rumor", source_id=rumor.id,
                ))
                learned.append(npc.id)
        return learned

