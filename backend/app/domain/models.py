from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Relationship(BaseModel):
    trust: int = Field(default=0, ge=-100, le=100)
    respect: int = Field(default=0, ge=-100, le=100)
    fear: int = Field(default=0, ge=-100, le=100)
    affection: int = Field(default=0, ge=-100, le=100)


class Campaign(BaseModel):
    id: str
    name: str
    system: str = "dnd5e"
    rules_profile: str = "campaign_default"
    current_day: int = 1
    current_location_id: str


class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    system: str = Field(default="dnd5e", max_length=40)
    rules_profile: str = Field(default="campaign_default", max_length=80)
    location_name: str = Field(default="Punt de partida", min_length=2, max_length=120)


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    current_day: int | None = Field(default=None, ge=1, le=100000)
    current_location_id: str | None = None
    rules_profile: str | None = Field(default=None, max_length=80)


class Location(BaseModel):
    id: str
    campaign_id: str
    name: str
    description: str = ""
    terrain: str = "urban"


class LocationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    terrain: str = Field(default="urban", max_length=40)


class Faction(BaseModel):
    id: str
    campaign_id: str
    name: str
    description: str = ""


class FactionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)


class Memory(BaseModel):
    id: str
    npc_id: str
    text: str
    importance: Literal["recent", "important", "summary"] = "recent"
    created_at: str = Field(default_factory=utc_now)


class NPC(BaseModel):
    id: str
    campaign_id: str
    name: str
    location_id: str
    faction_id: str | None = None
    traits: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    secrets: list[str] = Field(default_factory=list)
    relationship: Relationship = Field(default_factory=Relationship)
    memories: list[Memory] = Field(default_factory=list)


class NPCCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location_id: str
    faction_id: str | None = None
    traits: list[str] = Field(default_factory=list, max_length=12)
    goals: list[str] = Field(default_factory=list, max_length=12)
    values: list[str] = Field(default_factory=list, max_length=12)
    secrets: list[str] = Field(default_factory=list, max_length=12)
    relationship: Relationship = Field(default_factory=Relationship)


class NPCUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    location_id: str | None = None
    faction_id: str | None = None
    traits: list[str] | None = Field(default=None, max_length=12)
    goals: list[str] | None = Field(default=None, max_length=12)
    values: list[str] | None = Field(default=None, max_length=12)
    secrets: list[str] | None = Field(default=None, max_length=12)
    relationship: Relationship | None = None


class MemoryCreate(BaseModel):
    text: str = Field(min_length=2, max_length=2000)
    importance: Literal["recent", "important", "summary"] = "recent"


class Consequence(BaseModel):
    kind: Literal["relationship", "reputation", "wanted", "memory"]
    target_id: str
    field: str
    delta: int = Field(default=0, ge=-100, le=100)
    text: str = ""


class EventProposal(BaseModel):
    id: str
    campaign_id: str
    title: str
    description: str
    event_type: str
    severity: int = Field(ge=1, le=10)
    consequences: list[Consequence] = Field(default_factory=list)
    status: Literal["pending", "applied", "ignored"] = "pending"
    created_at: str = Field(default_factory=utc_now)
    location_id: str | None = None
    visibility: Literal["private", "witnessed", "public"] = "public"


class Session(BaseModel):
    id: str
    campaign_id: str
    started_at: str = Field(default_factory=utc_now)
    ended_at: str | None = None
    summary: str = ""


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class NPCChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    situation: str = Field(default="", max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class NPCChatResponse(BaseModel):
    npc_id: str
    reply: str
    context_reasons: list[str]
    provider: str


class EventAnalyzeRequest(BaseModel):
    campaign_id: str = "demo"
    description: str = Field(min_length=3, max_length=5000)
    npc_id: str | None = None
    location_id: str | None = None
    visibility: Literal["private", "witnessed", "public"] = "public"


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    event_type: str | None = Field(default=None, min_length=2, max_length=80)
    severity: int | None = Field(default=None, ge=1, le=10)
    consequences: list[Consequence] | None = None
    location_id: str | None = None
    visibility: Literal["private", "witnessed", "public"] | None = None


class SessionEndRequest(BaseModel):
    summary: str = Field(default="", max_length=10000)


class SearchResult(BaseModel):
    kind: Literal["npc", "event", "location", "faction", "memory"]
    id: str
    title: str
    excerpt: str = ""


class CampaignImport(BaseModel):
    format_version: int = 1
    campaign: Campaign
    locations: list[Location] = Field(default_factory=list)
    factions: list[Faction] = Field(default_factory=list)
    npcs: list[NPC] = Field(default_factory=list)
    events: list[EventProposal] = Field(default_factory=list)
    world_state: dict[str, int | str] = Field(default_factory=dict)


class RestoreBackupRequest(BaseModel):
    confirm: Literal["RESTORE"]


class ContentSource(BaseModel):
    id: str
    campaign_id: str
    title: str
    source_type: Literal["official", "homebrew", "notes"]
    file_name: str
    file_path: str
    mime_type: str
    checksum: str
    visibility: Literal["dm", "players"] = "dm"
    page_count: int = 0
    chunk_count: int = 0
    status: Literal["ready", "needs_ocr", "error"] = "ready"
    asset_kind: Literal["document", "map", "image"] = "document"
    created_at: str = Field(default_factory=utc_now)


class DocumentChunk(BaseModel):
    id: str
    source_id: str
    page: int | None = None
    section: str = ""
    text: str


class DocumentSearchResult(BaseModel):
    source_id: str
    source_title: str
    chunk_id: str
    page: int | None = None
    excerpt: str
    score: float = 0


class Knowledge(BaseModel):
    id: str
    npc_id: str
    subject: str
    content: str
    confidence: float = Field(default=0.5, ge=0, le=1)
    truth_status: Literal["fact", "belief", "false"] = "belief"
    source_type: Literal["event", "rumor", "document", "manual"] = "manual"
    source_id: str | None = None
    created_at: str = Field(default_factory=utc_now)


class KnowledgeCreate(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=3000)
    confidence: float = Field(default=0.5, ge=0, le=1)
    truth_status: Literal["fact", "belief", "false"] = "belief"
    source_type: Literal["event", "rumor", "document", "manual"] = "manual"
    source_id: str | None = None


class Rumor(BaseModel):
    id: str
    campaign_id: str
    origin_location_id: str | None = None
    subject: str
    content: str
    credibility: float = Field(default=0.6, ge=0, le=1)
    spread: float = Field(default=0.3, ge=0, le=1)
    status: Literal["active", "faded"] = "active"
    source_event_id: str | None = None
    created_at: str = Field(default_factory=utc_now)


class RumorCreate(BaseModel):
    campaign_id: str = "demo"
    origin_location_id: str | None = None
    subject: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=3000)
    credibility: float = Field(default=0.6, ge=0, le=1)
    spread: float = Field(default=0.3, ge=0, le=1)
    source_event_id: str | None = None


class GenerationTable(BaseModel):
    id: str
    campaign_id: str
    kind: Literal["encounter", "reward"]
    name: str
    description: str = ""
    created_at: str = Field(default_factory=utc_now)


class GenerationTableCreate(BaseModel):
    campaign_id: str = "demo"
    kind: Literal["encounter", "reward"]
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)


class GenerationEntry(BaseModel):
    id: str
    table_id: str
    terrains: list[str] = Field(default_factory=list)
    min_level: int = Field(default=1, ge=1, le=20)
    max_level: int = Field(default=20, ge=1, le=20)
    min_difficulty: int = Field(default=1, ge=1, le=5)
    max_difficulty: int = Field(default=5, ge=1, le=5)
    weight: int = Field(default=1, ge=1, le=1000)
    title: str
    payload: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class GenerationEntryCreate(BaseModel):
    terrains: list[str] = Field(default_factory=list)
    min_level: int = Field(default=1, ge=1, le=20)
    max_level: int = Field(default=20, ge=1, le=20)
    min_difficulty: int = Field(default=1, ge=1, le=5)
    max_difficulty: int = Field(default=5, ge=1, le=5)
    weight: int = Field(default=1, ge=1, le=1000)
    title: str = Field(min_length=2, max_length=200)
    payload: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class EncounterRequest(BaseModel):
    campaign_id: str = "demo"
    location_id: str | None = None
    terrain: str | None = None
    party_level: int = Field(default=3, ge=1, le=20)
    party_size: int = Field(default=4, ge=1, le=12)
    difficulty: int = Field(default=3, ge=1, le=5)
    encounter_type: Literal["auto", "combat", "social", "exploration", "hazard", "mixed"] = "auto"


class Encounter(BaseModel):
    id: str
    campaign_id: str
    location_id: str | None = None
    terrain: str
    party_level: int
    party_size: int
    difficulty: int
    encounter_type: str
    title: str
    description: str
    objectives: list[str] = Field(default_factory=list)
    complications: list[str] = Field(default_factory=list)
    context_reasons: list[str] = Field(default_factory=list)
    status: Literal["generated", "resolved"] = "generated"
    created_at: str = Field(default_factory=utc_now)


class RewardRequest(BaseModel):
    campaign_id: str = "demo"
    location_id: str | None = None
    encounter_id: str | None = None
    terrain: str | None = None
    party_level: int = Field(default=3, ge=1, le=20)
    difficulty: int = Field(default=3, ge=1, le=5)
    mode: Literal["neutral", "fortune"] = "neutral"
    fortune_roll: int | None = Field(default=None, ge=1, le=20)


class Reward(BaseModel):
    id: str
    campaign_id: str
    encounter_id: str | None = None
    location_id: str | None = None
    terrain: str
    party_level: int
    difficulty: int
    mode: str
    fortune_roll: int | None = None
    tier: str
    title: str
    items: list[dict] = Field(default_factory=list)
    narrative_rewards: list[str] = Field(default_factory=list)
    context_reasons: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class CampaignBundle(CampaignImport):
    knowledge: list[Knowledge] = Field(default_factory=list)
    rumors: list[Rumor] = Field(default_factory=list)
    generation_tables: list[GenerationTable] = Field(default_factory=list)
    generation_entries: list[GenerationEntry] = Field(default_factory=list)
    encounters: list[Encounter] = Field(default_factory=list)
    rewards: list[Reward] = Field(default_factory=list)
    excluded_content_notice: str = "Els fitxers de la biblioteca documental no s'inclouen en l'exportació."
