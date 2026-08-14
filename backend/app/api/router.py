from pathlib import Path
import re
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from app.application.context_builder import ContextBuilder
from app.application.event_service import EventService
from app.application.backup_service import BackupService
from app.application.document_service import DocumentService
from app.application.generation_service import GenerationService
from app.application.rumor_service import RumorService
from app.application.travel_service import TravelService
from app.config import Settings, get_settings
from app.domain.models import (
    CampaignBundle, CampaignCreate, CampaignUpdate, EventAnalyzeRequest, EventProposal,
    EventUpdate, FactionCreate, FactionUpdate, LocationCreate, LocationUpdate,
    MemoryCreate, NPCCreate, NPCChatRequest,
    NPCChatResponse, NPCUpdate, SessionEndRequest,
    RestoreBackupRequest, PartySettingsUpdate, WorldStateUpdate,
    EncounterRequest, GenerationEntryCreate, GenerationTableCreate,
    GenerationTableUpdate, KnowledgeCreate, RewardRequest, RumorCreate,
    CombatCreate, CombatUpdate, CombatantCreate, CombatantUpdate,
    ReferenceCombatantCreate,
    HexCellCreate, HexCellUpdate, LoreEntryCreate, LoreEntryUpdate,
    CombatantDuplicate, CombatRollRequest, InitiativeRequest,
    ExpeditionStateUpdate, HexcrawlSettingsUpdate, PlayerViewSettingsUpdate, TravelRequest,
)
from app.infrastructure.campaign_tools_repository import CampaignToolsRepository
from app.infrastructure.content_repository import ContentRepository
from app.infrastructure.database import Database
from app.infrastructure.llm import create_provider
from app.infrastructure.repository import SQLiteRepository
from app.infrastructure.reference_catalog import ReferenceCatalog
from app.infrastructure.simulation_repository import SimulationRepository


router = APIRouter()


def get_repository(settings: Settings = Depends(get_settings)) -> SQLiteRepository:
    return SQLiteRepository(Database(settings.database_path))


def get_content_repository(settings: Settings = Depends(get_settings)) -> ContentRepository:
    return ContentRepository(Database(settings.database_path))


def get_simulation_repository(settings: Settings = Depends(get_settings)) -> SimulationRepository:
    return SimulationRepository(Database(settings.database_path))


def get_campaign_tools_repository(settings: Settings = Depends(get_settings)) -> CampaignToolsRepository:
    return CampaignToolsRepository(Database(settings.database_path))


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "llm_provider": settings.llm_provider}


@router.get("/campaigns")
def list_campaigns(repository: SQLiteRepository = Depends(get_repository)):
    return repository.list_campaigns()


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, repository: SQLiteRepository = Depends(get_repository)):
    return repository.create_campaign(payload)


@router.get("/campaigns/{campaign_id}")
def get_dashboard(campaign_id: str, repository: SQLiteRepository = Depends(get_repository), tools: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    campaign = repository.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    return {
        "campaign": campaign,
        "location": repository.get_location(campaign.current_location_id),
        "locations": repository.list_locations(campaign_id),
        "world_state": repository.get_world_state(campaign_id),
        "party": repository.get_party_settings(campaign_id),
        "npcs": repository.list_npcs(campaign_id),
        "factions": repository.list_factions(campaign_id),
        "events": repository.list_events(campaign_id),
        "sessions": repository.list_sessions(campaign_id),
        "sources": ContentRepository(repository.database).list_sources(campaign_id),
        "rumors": SimulationRepository(repository.database).list_rumors(campaign_id),
        "encounters": SimulationRepository(repository.database).list_encounters(campaign_id),
        "rewards": SimulationRepository(repository.database).list_rewards(campaign_id),
        "generation_tables": SimulationRepository(repository.database).list_tables(campaign_id),
        "lore_entries": tools.list_lore(campaign_id),
        "hex_cells": tools.list_hexes(campaign_id),
        "combats": tools.list_combats(campaign_id),
        "hexcrawl_settings": tools.get_hexcrawl_settings(campaign_id),
        "expedition_state": tools.get_expedition_state(campaign_id),
        "travel_logs": tools.list_travel_logs(campaign_id),
        "player_view_settings": tools.get_player_view_settings(campaign_id),
    }


@router.patch("/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, payload: CampaignUpdate, repository: SQLiteRepository = Depends(get_repository)):
    try:
        campaign = repository.update_campaign(campaign_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    return campaign


@router.post("/campaigns/{campaign_id}/locations", status_code=status.HTTP_201_CREATED)
def create_location(campaign_id: str, payload: LocationCreate, repository: SQLiteRepository = Depends(get_repository)):
    if not repository.get_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    return repository.create_location(campaign_id, payload)


@router.patch("/locations/{location_id}")
def update_location(location_id: str, payload: LocationUpdate, repository: SQLiteRepository = Depends(get_repository)):
    item = repository.update_location(location_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Localització no trobada")
    return item


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: str, confirm: bool = False, repository: SQLiteRepository = Depends(get_repository)):
    if not confirm:
        raise HTTPException(status_code=409, detail="Cal confirm=true per eliminar la localització")
    try:
        deleted = repository.delete_location(location_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Localització no trobada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/campaigns/{campaign_id}/factions", status_code=status.HTTP_201_CREATED)
def create_faction(campaign_id: str, payload: FactionCreate, repository: SQLiteRepository = Depends(get_repository)):
    if not repository.get_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    return repository.create_faction(campaign_id, payload)


@router.patch("/factions/{faction_id}")
def update_faction(faction_id: str, payload: FactionUpdate, repository: SQLiteRepository = Depends(get_repository)):
    item = repository.update_faction(faction_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Facció no trobada")
    return item


@router.delete("/factions/{faction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faction(faction_id: str, confirm: bool = False, repository: SQLiteRepository = Depends(get_repository)):
    if not confirm:
        raise HTTPException(status_code=409, detail="Cal confirm=true per eliminar la facció")
    if not repository.delete_faction(faction_id):
        raise HTTPException(status_code=404, detail="Facció no trobada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/campaigns/{campaign_id}/party")
def get_party(campaign_id: str, repository: SQLiteRepository = Depends(get_repository)):
    if not repository.get_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    return repository.get_party_settings(campaign_id)


@router.put("/campaigns/{campaign_id}/party")
def update_party(campaign_id: str, payload: PartySettingsUpdate, repository: SQLiteRepository = Depends(get_repository)):
    if not repository.get_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    return repository.update_party_settings(campaign_id, payload)


@router.put("/campaigns/{campaign_id}/world-state/{key}")
def set_world_state(campaign_id: str, key: str, payload: WorldStateUpdate, repository: SQLiteRepository = Depends(get_repository)):
    if not repository.get_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    try:
        return repository.set_world_state(campaign_id, key, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/campaigns/{campaign_id}/world-state/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_world_state(campaign_id: str, key: str, confirm: bool = False, repository: SQLiteRepository = Depends(get_repository)):
    if not confirm:
        raise HTTPException(status_code=409, detail="Cal confirm=true per eliminar la variable")
    try:
        deleted = repository.delete_world_state(campaign_id, key)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Variable no trobada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/campaigns/{campaign_id}/export")
def export_campaign(campaign_id: str, repository: SQLiteRepository = Depends(get_repository)):
    package = repository.export_campaign(campaign_id)
    if not package:
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    return package


@router.post("/campaigns/import", status_code=status.HTTP_201_CREATED)
def import_campaign(payload: CampaignBundle, repository: SQLiteRepository = Depends(get_repository)):
    try:
        return repository.import_campaign(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def start_session(campaign_id: str = "demo", repository: SQLiteRepository = Depends(get_repository)):
    if not repository.get_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    try:
        return repository.start_session(campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/sessions")
def list_sessions(campaign_id: str = "demo", repository: SQLiteRepository = Depends(get_repository)):
    return repository.list_sessions(campaign_id)


@router.post("/sessions/{session_id}/end")
def end_session(session_id: str, payload: SessionEndRequest, repository: SQLiteRepository = Depends(get_repository)):
    session = repository.end_session(session_id, payload.summary)
    if not session:
        raise HTTPException(status_code=404, detail="Sessió no trobada")
    return session


@router.get("/npcs")
def list_npcs(campaign_id: str = "demo", repository: SQLiteRepository = Depends(get_repository)):
    return repository.list_npcs(campaign_id)


@router.post("/npcs", status_code=status.HTTP_201_CREATED)
def create_npc(campaign_id: str, payload: NPCCreate, repository: SQLiteRepository = Depends(get_repository)):
    if not repository.get_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    location = repository.get_location(payload.location_id)
    if not location or location.campaign_id != campaign_id:
        raise HTTPException(status_code=422, detail="La localització no pertany a aquesta campanya")
    if payload.faction_id:
        faction = repository.get_faction(payload.faction_id)
        if not faction or faction.campaign_id != campaign_id:
            raise HTTPException(status_code=422, detail="La facció no pertany a aquesta campanya")
    return repository.create_npc(campaign_id, payload)


@router.get("/npcs/{npc_id}")
def get_npc(npc_id: str, repository: SQLiteRepository = Depends(get_repository)):
    npc = repository.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail="NPC no trobat")
    return npc


@router.patch("/npcs/{npc_id}")
def update_npc(npc_id: str, payload: NPCUpdate, repository: SQLiteRepository = Depends(get_repository)):
    current = repository.get_npc(npc_id)
    if not current:
        raise HTTPException(status_code=404, detail="NPC no trobat")
    if payload.location_id:
        location = repository.get_location(payload.location_id)
        if not location or location.campaign_id != current.campaign_id:
            raise HTTPException(status_code=422, detail="La localització no pertany a aquesta campanya")
    if payload.faction_id:
        faction = repository.get_faction(payload.faction_id)
        if not faction or faction.campaign_id != current.campaign_id:
            raise HTTPException(status_code=422, detail="La facció no pertany a aquesta campanya")
    npc = repository.update_npc(npc_id, payload)
    if not npc:
        raise HTTPException(status_code=404, detail="NPC no trobat")
    return npc


@router.delete("/npcs/{npc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_npc(npc_id: str, repository: SQLiteRepository = Depends(get_repository)) -> Response:
    if not repository.delete_npc(npc_id):
        raise HTTPException(status_code=404, detail="NPC no trobat")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/npcs/{npc_id}/memories", status_code=status.HTTP_201_CREATED)
def add_memory(npc_id: str, payload: MemoryCreate, repository: SQLiteRepository = Depends(get_repository)):
    if not repository.get_npc(npc_id):
        raise HTTPException(status_code=404, detail="NPC no trobat")
    return repository.add_memory(npc_id, payload)


@router.post("/npcs/{npc_id}/chat", response_model=NPCChatResponse)
async def chat_with_npc(
    npc_id: str,
    payload: NPCChatRequest,
    repository: SQLiteRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
):
    npc = repository.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail="NPC no trobat")
    prompt, reasons = ContextBuilder(repository).build_for_npc(npc, payload.situation, payload.message)
    provider = create_provider(settings.llm_provider, settings.llm_base_url, settings.llm_model, npc)
    try:
        reply = await provider.chat(prompt, payload.message, payload.history)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"El LLM local no respon: {exc}") from exc
    return NPCChatResponse(npc_id=npc_id, reply=reply, context_reasons=reasons, provider=provider.name)


@router.post("/events/analyze", response_model=EventProposal, status_code=status.HTTP_201_CREATED)
def analyze_event(payload: EventAnalyzeRequest, repository: SQLiteRepository = Depends(get_repository)):
    if not repository.get_campaign(payload.campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    if payload.npc_id and not repository.get_npc(payload.npc_id):
        raise HTTPException(status_code=404, detail="NPC no trobat")
    return EventService(repository).analyze(payload)


@router.patch("/events/{event_id}", response_model=EventProposal)
def update_event(event_id: str, payload: EventUpdate, repository: SQLiteRepository = Depends(get_repository)):
    try:
        event = repository.update_event(event_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not event:
        raise HTTPException(status_code=404, detail="Esdeveniment no trobat")
    return event


@router.post("/events/{event_id}/apply", response_model=EventProposal)
def apply_event(event_id: str, repository: SQLiteRepository = Depends(get_repository)):
    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Esdeveniment no trobat")
    try:
        applied = repository.apply_event(event)
        rumor_service = RumorService(SimulationRepository(repository.database), repository)
        rumor = rumor_service.generate_from_event(applied)
        if rumor:
            rumor_service.propagate(rumor.id)
        return applied
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/events/{event_id}/ignore", response_model=EventProposal)
def ignore_event(event_id: str, repository: SQLiteRepository = Depends(get_repository)):
    try:
        event = repository.ignore_event(event_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not event:
        raise HTTPException(status_code=404, detail="Esdeveniment no trobat")
    return event


@router.post("/events/{event_id}/undo", response_model=EventProposal)
def undo_event(event_id: str, repository: SQLiteRepository = Depends(get_repository)):
    try:
        undone = repository.undo_event(event_id)
        SimulationRepository(repository.database).remove_rumors_for_event(event_id)
        return undone
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/search")
def search(q: str, campaign_id: str = "demo", repository: SQLiteRepository = Depends(get_repository)):
    if len(q.strip()) < 2:
        raise HTTPException(status_code=422, detail="La cerca ha de tenir almenys dos caràcters")
    return repository.search(campaign_id, q)


def get_backup_service(settings: Settings = Depends(get_settings)) -> BackupService:
    return BackupService(Database(settings.database_path), Path(settings.database_path).resolve().parent.parent / "backups")


@router.get("/backups")
def list_backups(service: BackupService = Depends(get_backup_service)):
    return service.list()


@router.post("/backups", status_code=status.HTTP_201_CREATED)
def create_backup(service: BackupService = Depends(get_backup_service)):
    path = service.create()
    return {"name": path.name, "size": path.stat().st_size}


@router.post("/backups/{name}/restore")
def restore_backup(name: str, payload: RestoreBackupRequest, service: BackupService = Depends(get_backup_service)):
    try:
        safety_backup = service.restore(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Backup no trobat") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"restored": name, "safety_backup": safety_backup.name}


@router.get("/settings")
def public_settings(settings: Settings = Depends(get_settings)):
    return {"llm_provider": settings.llm_provider, "llm_base_url": settings.llm_base_url, "llm_model": settings.llm_model, "database_file": Path(settings.database_path).name}


@router.get("/reference")
def search_reference(q: str = "", category: str | None = None, tag: str | None = None,
                     limit: int = 50, offset: int = 0):
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(status_code=422, detail="Paginació no vàlida")
    return ReferenceCatalog().search(q, category, tag, limit, offset)


@router.get("/reference/meta")
def reference_metadata():
    return ReferenceCatalog().metadata()


@router.get("/reference/item/{item_id:path}")
def get_reference_item(item_id: str):
    item = ReferenceCatalog().get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Entrada SRD no trobada")
    return item


@router.get("/library")
def list_library(campaign_id: str = "demo", repository: ContentRepository = Depends(get_content_repository)):
    return repository.list_sources(campaign_id)


@router.get("/library/search")
def search_library(q: str, campaign_id: str = "demo", repository: ContentRepository = Depends(get_content_repository)):
    if len(q.strip()) < 2:
        raise HTTPException(status_code=422, detail="La consulta ha de tenir almenys dos caràcters")
    return repository.search(campaign_id, q)


@router.post("/library/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...), campaign_id: str = Form("demo"), title: str = Form(""),
    source_type: str = Form("notes"), visibility: str = Form("dm"),
    settings: Settings = Depends(get_settings), world: SQLiteRepository = Depends(get_repository),
    repository: ContentRepository = Depends(get_content_repository),
):
    if not world.get_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    if source_type not in {"official", "homebrew", "notes"} or visibility not in {"dm", "players"}:
        raise HTTPException(status_code=422, detail="Tipus de font o visibilitat no vàlids")
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    try:
        return DocumentService(repository, settings.library_path, settings.max_upload_mb).ingest(
            campaign_id, title or file.filename or "Document", source_type, visibility,
            file.filename or "document", data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/library/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(source_id: str, confirm: bool = False, settings: Settings = Depends(get_settings), repository: ContentRepository = Depends(get_content_repository)):
    if not confirm:
        raise HTTPException(status_code=409, detail="Cal confirm=true per eliminar el document local")
    if not DocumentService(repository, settings.library_path, settings.max_upload_mb).delete(source_id):
        raise HTTPException(status_code=404, detail="Document no trobat")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/npcs/{npc_id}/knowledge")
def list_knowledge(npc_id: str, world: SQLiteRepository = Depends(get_repository), repository: SimulationRepository = Depends(get_simulation_repository)):
    if not world.get_npc(npc_id):
        raise HTTPException(status_code=404, detail="NPC no trobat")
    return repository.list_knowledge(npc_id)


@router.post("/npcs/{npc_id}/knowledge", status_code=status.HTTP_201_CREATED)
def add_knowledge(npc_id: str, payload: KnowledgeCreate, world: SQLiteRepository = Depends(get_repository), repository: SimulationRepository = Depends(get_simulation_repository)):
    if not world.get_npc(npc_id):
        raise HTTPException(status_code=404, detail="NPC no trobat")
    return repository.add_knowledge(npc_id, payload)


@router.get("/rumors")
def list_rumors(campaign_id: str = "demo", repository: SimulationRepository = Depends(get_simulation_repository)):
    return repository.list_rumors(campaign_id)


@router.post("/rumors", status_code=status.HTTP_201_CREATED)
def create_rumor(payload: RumorCreate, repository: SimulationRepository = Depends(get_simulation_repository)):
    return repository.create_rumor(payload)


@router.post("/rumors/{rumor_id}/propagate")
def propagate_rumor(rumor_id: str, repository: SimulationRepository = Depends(get_simulation_repository), world: SQLiteRepository = Depends(get_repository)):
    try:
        learned = RumorService(repository, world).propagate(rumor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rumor_id": rumor_id, "learned_by": learned}


@router.get("/lore")
def list_lore(campaign_id: str = "demo", layer: str | None = None, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    if layer and layer not in {"dm", "players", "world"}:
        raise HTTPException(status_code=422, detail="Capa de coneixement no vàlida")
    return repository.list_lore(campaign_id, layer)


@router.post("/lore", status_code=status.HTTP_201_CREATED)
def create_lore(payload: LoreEntryCreate, world: SQLiteRepository = Depends(get_repository), repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    if not world.get_campaign(payload.campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    return repository.create_lore(payload)


@router.patch("/lore/{item_id}")
def update_lore(item_id: str, payload: LoreEntryUpdate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    item = repository.update_lore(item_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Entrada de coneixement no trobada")
    return item


@router.delete("/lore/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lore(item_id: str, confirm: bool = False, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    if not confirm:
        raise HTTPException(status_code=409, detail="Cal confirm=true per eliminar l'entrada")
    if not repository.delete_lore(item_id):
        raise HTTPException(status_code=404, detail="Entrada de coneixement no trobada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/hexes")
def list_hexes(campaign_id: str = "demo", repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    return repository.list_hexes(campaign_id)


@router.post("/hexes", status_code=status.HTTP_201_CREATED)
def create_hex(payload: HexCellCreate, world: SQLiteRepository = Depends(get_repository), repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    if not world.get_campaign(payload.campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    try:
        return repository.create_hex(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/hexes/{item_id}")
def update_hex(item_id: str, payload: HexCellUpdate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    item = repository.update_hex(item_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Hex no trobat")
    return item


@router.get("/campaigns/{campaign_id}/hexcrawl-settings")
def get_hexcrawl_settings(campaign_id: str, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    return repository.get_hexcrawl_settings(campaign_id)


@router.patch("/campaigns/{campaign_id}/hexcrawl-settings")
def update_hexcrawl_settings(campaign_id: str, payload: HexcrawlSettingsUpdate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    return repository.update_hexcrawl_settings(campaign_id, payload)


@router.get("/campaigns/{campaign_id}/expedition")
def get_expedition(campaign_id: str, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    return {"state": repository.get_expedition_state(campaign_id), "logs": repository.list_travel_logs(campaign_id)}


@router.patch("/campaigns/{campaign_id}/expedition")
def update_expedition(campaign_id: str, payload: ExpeditionStateUpdate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    return repository.update_expedition_state(campaign_id, payload)


@router.post("/campaigns/{campaign_id}/travel", status_code=status.HTTP_201_CREATED)
def travel(campaign_id: str, payload: TravelRequest, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository), world: SQLiteRepository = Depends(get_repository), simulation: SimulationRepository = Depends(get_simulation_repository)):
    try:
        return TravelService(repository, world, simulation).travel(campaign_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/campaigns/{campaign_id}/player-view-settings")
def get_player_view_settings(campaign_id: str, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    return repository.get_player_view_settings(campaign_id)


@router.patch("/campaigns/{campaign_id}/player-view-settings")
def update_player_view_settings(campaign_id: str, payload: PlayerViewSettingsUpdate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    return repository.update_player_view_settings(campaign_id, payload)


@router.get("/player-view/{campaign_id}")
def player_view(campaign_id: str, world: SQLiteRepository = Depends(get_repository), repository: CampaignToolsRepository = Depends(get_campaign_tools_repository), simulation: SimulationRepository = Depends(get_simulation_repository)):
    campaign = world.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    settings = repository.get_player_view_settings(campaign_id)
    if not settings.enabled:
        raise HTTPException(status_code=403, detail="La pantalla de jugadors està desactivada")
    expedition = repository.get_expedition_state(campaign_id)
    visible_hexes = []
    if settings.show_map:
        for item in repository.list_hexes(campaign_id):
            if item.discovery == "hidden":
                continue
            visible_hexes.append({
                "id": item.id, "q": item.q, "r": item.r, "terrain": item.terrain,
                "title": item.title, "discovery": item.discovery, "player_notes": item.player_notes,
            })
    combats = []
    if settings.show_combat:
        for combat in repository.list_combats(campaign_id):
            if combat.status != "active":
                continue
            combatants = []
            for item in combat.combatants:
                hp_status = "down" if item.current_hp == 0 else "bloodied" if item.current_hp <= item.max_hp / 2 else "standing"
                visible_hp = item.kind in {"player", "ally"} or settings.show_enemy_hp
                combatants.append({
                    "id": item.id, "name": item.name, "kind": item.kind, "initiative": item.initiative,
                    "conditions": item.conditions, "concentration": item.concentration, "hp_status": hp_status,
                    "current_hp": item.current_hp if visible_hp else None,
                    "max_hp": item.max_hp if visible_hp else None,
                })
            combats.append({"id": combat.id, "name": combat.name, "round": combat.round, "turn_index": combat.turn_index, "combatants": combatants})
    return {
        "campaign": {"id": campaign.id, "name": campaign.name, "current_day": campaign.current_day},
        "party": {"name": world.get_party_settings(campaign_id).name},
        "lore": [item.model_dump() for item in repository.list_lore(campaign_id, "players")],
        "hexes": visible_hexes,
        "rumors": [item.model_dump() for item in simulation.list_rumors(campaign_id) if item.status == "active"] if settings.show_rumors else [],
        "expedition": {"food": expedition.food, "water": expedition.water, "supplies": expedition.supplies,
                       "exhaustion": expedition.exhaustion, "lost": expedition.lost,
                       "weather": expedition.weather if settings.show_weather else None} if settings.show_resources else None,
        "combats": combats, "settings": settings,
    }


@router.get("/combats")
def list_combats(campaign_id: str = "demo", repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    return repository.list_combats(campaign_id)


@router.post("/combats", status_code=status.HTTP_201_CREATED)
def create_combat(payload: CombatCreate, world: SQLiteRepository = Depends(get_repository), repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    if not world.get_campaign(payload.campaign_id):
        raise HTTPException(status_code=404, detail="Campanya no trobada")
    return repository.create_combat(payload)


@router.patch("/combats/{combat_id}")
def update_combat(combat_id: str, payload: CombatUpdate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    item = repository.update_combat(combat_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Combat no trobat")
    return item


@router.post("/combats/{combat_id}/combatants", status_code=status.HTTP_201_CREATED)
def add_combatant(combat_id: str, payload: CombatantCreate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    try:
        return repository.add_combatant(combat_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/combats/{combat_id}/combatants/from-reference", status_code=status.HTTP_201_CREATED)
def add_reference_combatant(combat_id: str, payload: ReferenceCombatantCreate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    reference = ReferenceCatalog().get(payload.reference_id)
    if not reference or reference.get("category") != "monsters":
        raise HTTPException(status_code=404, detail="Monstre no trobat al catàleg SRD")
    data = reference.get("data", {})
    raw_ac = data.get("armor_class", 10)
    armor_class = raw_ac[0].get("value", 10) if isinstance(raw_ac, list) and raw_ac else raw_ac if isinstance(raw_ac, int) else 10
    actions = [{"name": action.get("name", "Acció"), "description": action.get("desc", ""), "source": "SRD 5.1"}
               for action in data.get("actions", [])[:20]]
    try:
        created = [repository.add_combatant(combat_id, CombatantCreate(
            name=(payload.name or reference["name"]) + (f" {index + 1}" if payload.quantity > 1 else ""),
            kind="enemy", initiative=payload.initiative - index,
            armor_class=armor_class, max_hp=max(1, int(data.get("hit_points", 1))), actions=actions,
            reference_id=payload.reference_id,
        )) for index in range(payload.quantity)]
        return created[0] if payload.quantity == 1 else created
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/combatants/{item_id}")
def update_combatant(item_id: str, payload: CombatantUpdate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    item = repository.update_combatant(item_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Combatent no trobat")
    return item


@router.delete("/combatants/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_combatant(item_id: str, confirm: bool = False, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    if not confirm:
        raise HTTPException(status_code=409, detail="Cal confirm=true per eliminar el combatent")
    if not repository.delete_combatant(item_id):
        raise HTTPException(status_code=404, detail="Combatent no trobat")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/combatants/{item_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_combatant(item_id: str, payload: CombatantDuplicate, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    try:
        return repository.duplicate_combatant(item_id, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/combats/{combat_id}/next-turn")
def next_combat_turn(combat_id: str, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    item = repository.next_turn(combat_id)
    if not item:
        raise HTTPException(status_code=404, detail="Combat no trobat")
    return item


@router.post("/combats/{combat_id}/initiative")
def roll_combat_initiative(combat_id: str, payload: InitiativeRequest, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    combat = repository.get_combat(combat_id)
    if not combat:
        raise HTTPException(status_code=404, detail="Combat no trobat")
    rolls = {item.id: secrets.randbelow(20) + 1 for item in combat.combatants} if payload.automatic else payload.rolls
    item = repository.roll_initiative(combat_id, rolls)
    return item


@router.get("/combats/{combat_id}/log")
def get_combat_log(combat_id: str, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    if not repository.get_combat(combat_id):
        raise HTTPException(status_code=404, detail="Combat no trobat")
    return repository.list_combat_logs(combat_id)


@router.post("/combats/{combat_id}/roll")
def combat_roll(combat_id: str, payload: CombatRollRequest, repository: CampaignToolsRepository = Depends(get_campaign_tools_repository)):
    if not repository.get_combat(combat_id):
        raise HTTPException(status_code=404, detail="Combat no trobat")
    match = re.fullmatch(r"(\d{1,2})d(\d{1,3})([+-]\d{1,4})?", payload.notation.replace(" ", "").lower())
    if not match:
        raise HTTPException(status_code=422, detail="Notació no vàlida; utilitza per exemple 1d20+5")
    count, sides, modifier = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
    if count > 20 or sides > 100 or sides < 2:
        raise HTTPException(status_code=422, detail="La tirada supera els límits permesos")
    dice = [secrets.randbelow(sides) + 1 for _ in range(count)]
    total = sum(dice) + modifier
    message = f"{payload.label}: {payload.notation} = {total} ({dice}{modifier:+d})"
    repository.add_combat_log(combat_id, message, "roll")
    return {"notation": payload.notation, "dice": dice, "modifier": modifier, "total": total, "label": payload.label}


@router.get("/generation-tables")
def list_generation_tables(campaign_id: str = "demo", kind: str | None = None, repository: SimulationRepository = Depends(get_simulation_repository)):
    return repository.list_tables(campaign_id, kind)


@router.post("/generation-tables", status_code=status.HTTP_201_CREATED)
def create_generation_table(payload: GenerationTableCreate, repository: SimulationRepository = Depends(get_simulation_repository)):
    return repository.create_table(payload)


@router.patch("/generation-tables/{table_id}")
def update_generation_table(table_id: str, payload: GenerationTableUpdate, repository: SimulationRepository = Depends(get_simulation_repository)):
    item = repository.update_table(table_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Taula no trobada")
    return item


@router.delete("/generation-tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_generation_table(table_id: str, confirm: bool = False, repository: SimulationRepository = Depends(get_simulation_repository)):
    if not confirm:
        raise HTTPException(status_code=409, detail="Cal confirm=true per eliminar la taula")
    if not repository.delete_table(table_id):
        raise HTTPException(status_code=404, detail="Taula no trobada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/generation-tables/{table_id}/entries", status_code=status.HTTP_201_CREATED)
def add_generation_entry(table_id: str, payload: GenerationEntryCreate, repository: SimulationRepository = Depends(get_simulation_repository)):
    try:
        return repository.add_entry(table_id, payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Taula no trobada o entrada no vàlida") from exc


@router.get("/generation-tables/{table_id}/entries")
def list_generation_entries(table_id: str, repository: SimulationRepository = Depends(get_simulation_repository)):
    return repository.list_table_entries(table_id)


@router.put("/generation-entries/{entry_id}")
def update_generation_entry(entry_id: str, payload: GenerationEntryCreate, repository: SimulationRepository = Depends(get_simulation_repository)):
    item = repository.update_entry(entry_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Entrada no trobada")
    return item


@router.delete("/generation-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_generation_entry(entry_id: str, confirm: bool = False, repository: SimulationRepository = Depends(get_simulation_repository)):
    if not confirm:
        raise HTTPException(status_code=409, detail="Cal confirm=true per eliminar l'entrada")
    if not repository.delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Entrada no trobada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/encounters")
def list_encounters(campaign_id: str = "demo", repository: SimulationRepository = Depends(get_simulation_repository)):
    return repository.list_encounters(campaign_id)


@router.post("/encounters/generate", status_code=status.HTTP_201_CREATED)
def generate_encounter(payload: EncounterRequest, repository: SimulationRepository = Depends(get_simulation_repository), world: SQLiteRepository = Depends(get_repository)):
    try:
        return GenerationService(repository, world).generate_encounter(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/rewards")
def list_rewards(campaign_id: str = "demo", repository: SimulationRepository = Depends(get_simulation_repository)):
    return repository.list_rewards(campaign_id)


@router.post("/rewards/generate", status_code=status.HTTP_201_CREATED)
def generate_reward(payload: RewardRequest, repository: SimulationRepository = Depends(get_simulation_repository), world: SQLiteRepository = Depends(get_repository)):
    try:
        return GenerationService(repository, world).generate_reward(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
