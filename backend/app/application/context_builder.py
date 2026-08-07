from app.domain.models import NPC
from app.infrastructure.repository import SQLiteRepository
from app.infrastructure.content_repository import ContentRepository
from app.infrastructure.simulation_repository import SimulationRepository


class ContextBuilder:
    def __init__(self, repository: SQLiteRepository):
        self.repository = repository

    def build_for_npc(self, npc: NPC, situation: str = "", query: str = "") -> tuple[str, list[str]]:
        campaign = self.repository.get_campaign(npc.campaign_id)
        location = self.repository.get_location(npc.location_id)
        world = self.repository.get_world_state(npc.campaign_id)
        knowledge = SimulationRepository(self.repository.database).list_knowledge(npc.id)[:8]
        documents = ContentRepository(self.repository.database).search(npc.campaign_id, query, 3) if query else []
        reasons = [
            f"Personalitat: {', '.join(npc.traits)}",
            f"Relació: confiança {npc.relationship.trust}, respecte {npc.relationship.respect}",
        ]
        if npc.memories:
            reasons.append(f"Memòries rellevants: {len(npc.memories)}")
        if world.get("wanted_level", 0):
            reasons.append(f"Nivell de cerca del grup: {world['wanted_level']}")
        if knowledge:
            reasons.append(f"Coneixement propi de l'NPC: {len(knowledge)} entrades")
        if documents:
            reasons.append(f"Fragments documentals consultats: {len(documents)}")

        memories = "\n".join(f"- {item.text}" for item in npc.memories[:5]) or "- Cap memòria rellevant"
        known = "\n".join(f"- [{item.truth_status}, confiança {item.confidence:.0%}] {item.content}" for item in knowledge) or "- Cap coneixement específic"
        sources = "\n".join(f"- {item.source_title}, pàgina {item.page or 'n/a'}: {item.excerpt}" for item in documents) or "- Cap fragment documental rellevant"
        context = f"""Interpreta {npc.name}, un NPC d'una campanya de D&D 5e.
No inventis fets que contradiguin el context. Respon breument en la llengua de l'usuari.

PERSONALITAT: {', '.join(npc.traits)}
VALORS: {', '.join(npc.values)}
OBJECTIUS: {', '.join(npc.goals)}
RELACIÓ AMB EL GRUP: confiança={npc.relationship.trust}, respecte={npc.relationship.respect}, por={npc.relationship.fear}, afecte={npc.relationship.affection}
CAMPANYA: {campaign.name if campaign else npc.campaign_id}
LOCALITZACIÓ: {location.name if location else npc.location_id}
ESTAT DEL MÓN: {world}
MEMÒRIES:
{memories}
CONEIXEMENT I CREENCES DE L'NPC (no assumeixis que les creences són certes):
{known}
FONTS DOCUMENTALS RECUPERADES:
{sources}
SITUACIÓ ACTUAL: {situation or 'Conversa ordinària durant la sessió'}
"""
        return context, reasons
