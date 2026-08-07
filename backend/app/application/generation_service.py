import random
import secrets
from uuid import uuid4

from app.domain.models import Encounter, EncounterRequest, Reward, RewardRequest
from app.infrastructure.repository import SQLiteRepository
from app.infrastructure.reference_catalog import ReferenceCatalog
from app.infrastructure.simulation_repository import SimulationRepository


class GenerationService:
    def __init__(self, repository: SimulationRepository, world_repository: SQLiteRepository):
        self.repository = repository
        self.world_repository = world_repository
        self.catalog = ReferenceCatalog()

    def _terrain(self, campaign_id: str, location_id: str | None, explicit: str | None) -> tuple[str, str | None, list[str]]:
        reasons: list[str] = []
        if explicit:
            reasons.append(f"Terreny forçat pel DM: {explicit}")
            return explicit, location_id, reasons
        if location_id:
            location = self.world_repository.get_location(location_id)
            if not location or location.campaign_id != campaign_id:
                raise ValueError("La localització no pertany a la campanya")
            reasons.append(f"Terreny heretat de {location.name}: {location.terrain}")
            return location.terrain, location_id, reasons
        campaign = self.world_repository.get_campaign(campaign_id)
        if not campaign:
            raise ValueError("Campanya no trobada")
        location = self.world_repository.get_location(campaign.current_location_id)
        terrain = location.terrain if location else "other"
        reasons.append(f"Terreny de la localització actual: {terrain}")
        return terrain, campaign.current_location_id, reasons

    @staticmethod
    def _choose(entries):
        if not entries:
            raise ValueError("No hi ha opcions compatibles. Afegeix una entrada a les taules")
        return random.SystemRandom().choices(entries, weights=[entry.weight for entry in entries], k=1)[0]

    def generate_encounter(self, request: EncounterRequest) -> Encounter:
        terrain, location_id, reasons = self._terrain(request.campaign_id, request.location_id, request.terrain)
        entries = self.repository.list_entries(request.campaign_id, "encounter", terrain, request.party_level, request.difficulty)
        selected_type = request.encounter_type
        if request.encounter_type != "auto":
            typed = [entry for entry in entries if entry.payload.get("type") == request.encounter_type]
            if typed:
                entries = typed
            else:
                reasons.append("No hi havia una plantilla exacta; s'ha adaptat una opció del terreny")
            reasons.append(f"Tipus sol·licitat: {request.encounter_type}")
        entry = self._choose(entries)
        if selected_type == "auto":
            selected_type = entry.payload.get("type", "mixed")
        world = self.world_repository.get_world_state(request.campaign_id)
        wanted = int(world.get("wanted_level", 0))
        if wanted:
            reasons.append(f"El grup té nivell de cerca {wanted}")
        reasons.extend([f"Dificultat {request.difficulty}/5", f"Grup de {request.party_size} personatges de nivell {request.party_level}"])
        complications = list(entry.payload.get("complications", []))
        if selected_type in {"combat", "mixed"}:
            creature = self.catalog.monster_for_level(request.party_level, request.party_size, request.difficulty, terrain)
            if creature:
                cr = creature["data"].get("challenge_rating", "?")
                complications.append(f"Adversari SRD suggerit: {creature['name']} (CR {cr})")
                reasons.append("Adversari seleccionat del catàleg local SRD 5.1")
        complications.append(f"DC orientativa principal: {10 + request.difficulty + request.party_level // 4}")
        if wanted >= 2 and terrain == "urban":
            complications.append("Una patrulla pot reconèixer el grup")
        active_rumors = [rumor for rumor in self.repository.list_rumors(request.campaign_id) if rumor.status == "active"]
        if active_rumors:
            reasons.append(f"Rumor actiu rellevant: {active_rumors[0].subject}")
            if selected_type == "social":
                complications.append("Els interlocutors poden haver sentit un rumor sobre el grup")
        negative_reputations = [key for key, value in world.items() if key.startswith("reputation:") and isinstance(value, int) and value < 0]
        if negative_reputations:
            reasons.append(f"Reputació negativa amb {len(negative_reputations)} grups")
        item = Encounter(
            id=f"encounter_{uuid4().hex[:12]}", campaign_id=request.campaign_id,
            location_id=location_id, terrain=terrain, party_level=request.party_level,
            party_size=request.party_size, difficulty=request.difficulty,
            encounter_type=selected_type, title=entry.title,
            description=entry.payload.get("description", entry.title), objectives=entry.payload.get("objectives", []),
            complications=complications, context_reasons=reasons,
        )
        return self.repository.save_encounter(item)

    def generate_reward(self, request: RewardRequest) -> Reward:
        encounter = self.repository.get_encounter(request.encounter_id) if request.encounter_id else None
        if request.encounter_id and (not encounter or encounter.campaign_id != request.campaign_id):
            raise ValueError("L'encounter no existeix dins d'aquesta campanya")
        location_id = request.location_id or (encounter.location_id if encounter else None)
        explicit_terrain = request.terrain or (encounter.terrain if encounter else None)
        terrain, location_id, reasons = self._terrain(request.campaign_id, location_id, explicit_terrain)
        entries = self.repository.list_entries(request.campaign_id, "reward", terrain, request.party_level, request.difficulty)
        entry = self._choose(entries)
        roll = request.fortune_roll
        if request.mode == "fortune" and roll is None:
            roll = secrets.randbelow(20) + 1
        tier = "neutral"
        multiplier = 1.0
        if request.mode == "fortune" and roll is not None:
            if roll <= 3: tier, multiplier = "inferior", 0.7
            elif roll <= 7: tier, multiplier = "lleugerament inferior", 0.85
            elif roll >= 20: tier, multiplier = "excepcional", 1.6
            elif roll >= 18: tier, multiplier = "molt bona", 1.4
            elif roll >= 14: tier, multiplier = "superior", 1.2
            reasons.append(f"Tirada de fortuna: {roll} → {tier}")
        reasons.extend([f"Terreny: {terrain}", f"Nivell {request.party_level}, dificultat {request.difficulty}/5"])
        if encounter:
            reasons.append(f"Recompensa vinculada a l'encounter: {encounter.title}")
        items = []
        for raw in entry.payload.get("items", []):
            item = dict(raw)
            if "apropiat al nivell" in str(item.get("name", "")).casefold():
                reference = self.catalog.reward_for_level(request.party_level, request.difficulty)
                if reference:
                    rarity = reference["data"].get("rarity", {}).get("name", "SRD")
                    item.update({"name": reference["name"], "category": "magic-item", "rarity": rarity,
                                 "reference_id": reference["id"], "source": reference["source"]})
                    reasons.append("Objecte concret seleccionat del catàleg local SRD 5.1")
            if isinstance(item.get("quantity"), (int, float)):
                item["quantity"] = max(1, round(item["quantity"] * multiplier))
            items.append(item)
        narrative = list(entry.payload.get("narrative", []))
        if tier in {"molt bona", "excepcional"}:
            narrative.append("Una pista addicional connectada amb una facció o objectiu actiu")
        item = Reward(
            id=f"reward_{uuid4().hex[:12]}", campaign_id=request.campaign_id,
            encounter_id=request.encounter_id, location_id=location_id, terrain=terrain,
            party_level=request.party_level, difficulty=request.difficulty, mode=request.mode,
            fortune_roll=roll, tier=tier, title=entry.title, items=items,
            narrative_rewards=narrative, context_reasons=reasons,
        )
        return self.repository.save_reward(item)
