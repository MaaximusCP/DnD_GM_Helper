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
    archived: bool = False


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
    archived: bool | None = None


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


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    terrain: str | None = Field(default=None, max_length=40)


class Faction(BaseModel):
    id: str
    campaign_id: str
    name: str
    description: str = ""


class FactionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)


class FactionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class PartySettings(BaseModel):
    campaign_id: str
    name: str = "Grup d'aventurers"
    level: int = Field(default=3, ge=1, le=20)
    size: int = Field(default=4, ge=1, le=12)
    notes: str = Field(default="", max_length=3000)


class PartySettingsUpdate(BaseModel):
    name: str = Field(default="Grup d'aventurers", min_length=2, max_length=120)
    level: int = Field(default=3, ge=1, le=20)
    size: int = Field(default=4, ge=1, le=12)
    notes: str = Field(default="", max_length=3000)


class WorldStateUpdate(BaseModel):
    value: int | str


class LoreEntry(BaseModel):
    id: str
    campaign_id: str
    layer: Literal["dm", "players", "world"]
    category: Literal["lore", "npc", "location", "quest", "rule", "other"] = "lore"
    title: str
    content: str
    source_id: str | None = None
    location_id: str | None = None
    created_at: str = Field(default_factory=utc_now)


class LoreEntryCreate(BaseModel):
    campaign_id: str = "demo"
    layer: Literal["dm", "players", "world"] = "dm"
    category: Literal["lore", "npc", "location", "quest", "rule", "other"] = "lore"
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=10000)
    source_id: str | None = None
    location_id: str | None = None


class LoreEntryUpdate(BaseModel):
    layer: Literal["dm", "players", "world"] | None = None
    category: Literal["lore", "npc", "location", "quest", "rule", "other"] | None = None
    title: str | None = Field(default=None, min_length=2, max_length=200)
    content: str | None = Field(default=None, min_length=2, max_length=10000)
    source_id: str | None = None
    location_id: str | None = None


class HexCell(BaseModel):
    id: str
    campaign_id: str
    q: int = Field(ge=-100, le=100)
    r: int = Field(ge=-100, le=100)
    terrain: str = "jungle"
    title: str = "Hex desconegut"
    discovery: Literal["hidden", "discovered", "explored"] = "hidden"
    travel_cost: int = Field(default=1, ge=1, le=10)
    encounter_chance: int = Field(default=20, ge=0, le=100)
    player_notes: str = ""
    dm_notes: str = ""
    location_id: str | None = None
    source_id: str | None = None


class HexCellCreate(BaseModel):
    campaign_id: str = "demo"
    q: int = Field(ge=-100, le=100)
    r: int = Field(ge=-100, le=100)
    terrain: str = Field(default="jungle", max_length=40)
    title: str = Field(default="Hex desconegut", min_length=2, max_length=160)
    discovery: Literal["hidden", "discovered", "explored"] = "hidden"
    travel_cost: int = Field(default=1, ge=1, le=10)
    encounter_chance: int = Field(default=20, ge=0, le=100)
    player_notes: str = Field(default="", max_length=5000)
    dm_notes: str = Field(default="", max_length=5000)
    location_id: str | None = None
    source_id: str | None = None


class HexCellUpdate(BaseModel):
    terrain: str | None = Field(default=None, max_length=40)
    title: str | None = Field(default=None, min_length=2, max_length=160)
    discovery: Literal["hidden", "discovered", "explored"] | None = None
    travel_cost: int | None = Field(default=None, ge=1, le=10)
    encounter_chance: int | None = Field(default=None, ge=0, le=100)
    player_notes: str | None = Field(default=None, max_length=5000)
    dm_notes: str | None = Field(default=None, max_length=5000)
    location_id: str | None = None
    source_id: str | None = None


class HexcrawlSettings(BaseModel):
    campaign_id: str
    track_weather: bool = True
    track_navigation: bool = True
    track_food: bool = True
    track_water: bool = True
    track_fatigue: bool = True
    track_encounters: bool = True
    track_foraging: bool = True
    auto_discover: bool = True
    default_pace: Literal["slow", "normal", "fast"] = "normal"
    hex_distance: float = Field(default=10, gt=0, le=1000)
    distance_unit: Literal["km", "miles"] = "km"


class HexcrawlSettingsUpdate(BaseModel):
    track_weather: bool | None = None
    track_navigation: bool | None = None
    track_food: bool | None = None
    track_water: bool | None = None
    track_fatigue: bool | None = None
    track_encounters: bool | None = None
    track_foraging: bool | None = None
    auto_discover: bool | None = None
    default_pace: Literal["slow", "normal", "fast"] | None = None
    hex_distance: float | None = Field(default=None, gt=0, le=1000)
    distance_unit: Literal["km", "miles"] | None = None


class ExpeditionState(BaseModel):
    campaign_id: str
    current_hex_id: str | None = None
    food: float = Field(default=40, ge=0, le=100000)
    water: float = Field(default=80, ge=0, le=100000)
    supplies: float = Field(default=10, ge=0, le=100000)
    exhaustion: int = Field(default=0, ge=0, le=6)
    lost: bool = False
    weather: str = "clear"
    updated_at: str = Field(default_factory=utc_now)


class ExpeditionStateUpdate(BaseModel):
    current_hex_id: str | None = None
    food: float | None = Field(default=None, ge=0, le=100000)
    water: float | None = Field(default=None, ge=0, le=100000)
    supplies: float | None = Field(default=None, ge=0, le=100000)
    exhaustion: int | None = Field(default=None, ge=0, le=6)
    lost: bool | None = None
    weather: str | None = Field(default=None, max_length=80)


class TravelRequest(BaseModel):
    destination_hex_id: str
    pace: Literal["slow", "normal", "fast"] | None = None
    navigation_roll: int | None = Field(default=None, ge=1, le=40)
    encounter_roll: int | None = Field(default=None, ge=1, le=100)
    foraging_roll: int | None = Field(default=None, ge=1, le=40)
    manual_weather: str | None = Field(default=None, max_length=80)


class TravelLog(BaseModel):
    id: str
    campaign_id: str
    origin_hex_id: str | None = None
    destination_hex_id: str
    route: list[str] = Field(default_factory=list)
    pace: str
    days: int = 1
    distance: float = 0
    distance_unit: str = "km"
    weather: str = "clear"
    navigation_roll: int | None = None
    encounter_roll: int | None = None
    food_used: float = 0
    water_used: float = 0
    exhaustion_delta: int = 0
    encounter_triggered: bool = False
    encounter_id: str | None = None
    reached_destination: bool = True
    notes: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class PlayerViewSettings(BaseModel):
    campaign_id: str
    enabled: bool = True
    show_map: bool = True
    show_rumors: bool = True
    show_resources: bool = True
    show_weather: bool = True
    show_combat: bool = True
    show_enemy_hp: bool = False


class PlayerViewSettingsUpdate(BaseModel):
    enabled: bool | None = None
    show_map: bool | None = None
    show_rumors: bool | None = None
    show_resources: bool | None = None
    show_weather: bool | None = None
    show_combat: bool | None = None
    show_enemy_hp: bool | None = None


class Combatant(BaseModel):
    id: str
    combat_id: str
    name: str
    kind: Literal["player", "enemy", "ally", "neutral"] = "enemy"
    initiative: int = Field(default=10, ge=-10, le=50)
    armor_class: int = Field(default=10, ge=0, le=40)
    max_hp: int = Field(default=1, ge=1, le=10000)
    current_hp: int = Field(default=1, ge=0, le=10000)
    temp_hp: int = Field(default=0, ge=0, le=10000)
    initiative_bonus: int = Field(default=0, ge=-20, le=30)
    concentration: bool = False
    reaction_available: bool = True
    legendary_actions: int = Field(default=0, ge=0, le=10)
    legendary_actions_max: int = Field(default=0, ge=0, le=10)
    notes: str = ""
    conditions: list[str] = Field(default_factory=list)
    actions: list[dict] = Field(default_factory=list)
    source_id: str | None = None
    reference_id: str | None = None


class CombatantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    kind: Literal["player", "enemy", "ally", "neutral"] = "enemy"
    initiative: int = Field(default=10, ge=-10, le=50)
    armor_class: int = Field(default=10, ge=0, le=40)
    max_hp: int = Field(default=1, ge=1, le=10000)
    current_hp: int | None = Field(default=None, ge=0, le=10000)
    temp_hp: int = Field(default=0, ge=0, le=10000)
    initiative_bonus: int = Field(default=0, ge=-20, le=30)
    concentration: bool = False
    reaction_available: bool = True
    legendary_actions: int = Field(default=0, ge=0, le=10)
    legendary_actions_max: int = Field(default=0, ge=0, le=10)
    notes: str = Field(default="", max_length=3000)
    conditions: list[str] = Field(default_factory=list, max_length=20)
    actions: list[dict] = Field(default_factory=list, max_length=30)
    source_id: str | None = None
    reference_id: str | None = None


class CombatantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    kind: Literal["player", "enemy", "ally", "neutral"] | None = None
    initiative: int | None = Field(default=None, ge=-10, le=50)
    armor_class: int | None = Field(default=None, ge=0, le=40)
    max_hp: int | None = Field(default=None, ge=1, le=10000)
    current_hp: int | None = Field(default=None, ge=0, le=10000)
    temp_hp: int | None = Field(default=None, ge=0, le=10000)
    initiative_bonus: int | None = Field(default=None, ge=-20, le=30)
    concentration: bool | None = None
    reaction_available: bool | None = None
    legendary_actions: int | None = Field(default=None, ge=0, le=10)
    legendary_actions_max: int | None = Field(default=None, ge=0, le=10)
    notes: str | None = Field(default=None, max_length=3000)
    conditions: list[str] | None = Field(default=None, max_length=20)
    actions: list[dict] | None = Field(default=None, max_length=30)


class ReferenceCombatantCreate(BaseModel):
    reference_id: str = Field(min_length=3, max_length=300)
    initiative: int = Field(default=10, ge=-10, le=50)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    quantity: int = Field(default=1, ge=1, le=20)


class CombatantDuplicate(BaseModel):
    quantity: int = Field(default=1, ge=1, le=20)


class CombatRollRequest(BaseModel):
    notation: str = Field(default="1d20", min_length=3, max_length=30)
    label: str = Field(default="Tirada", min_length=2, max_length=160)
    combatant_id: str | None = None


class InitiativeRequest(BaseModel):
    automatic: bool = True
    rolls: dict[str, int] = Field(default_factory=dict)


class Combat(BaseModel):
    id: str
    campaign_id: str
    name: str
    status: Literal["active", "completed"] = "active"
    round: int = Field(default=1, ge=1)
    turn_index: int = Field(default=0, ge=0)
    encounter_id: str | None = None
    summary: str = ""
    created_at: str = Field(default_factory=utc_now)
    combatants: list[Combatant] = Field(default_factory=list)


class CombatCreate(BaseModel):
    campaign_id: str = "demo"
    name: str = Field(min_length=2, max_length=160)
    encounter_id: str | None = None


class CombatUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    status: Literal["active", "completed"] | None = None
    summary: str | None = Field(default=None, max_length=10000)


class CombatLog(BaseModel):
    id: str
    combat_id: str
    message: str
    kind: Literal["system", "damage", "healing", "roll", "condition", "turn"] = "system"
    created_at: str = Field(default_factory=utc_now)


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


class GenerationTableUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)


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
    party: PartySettings | None = None
    knowledge: list[Knowledge] = Field(default_factory=list)
    rumors: list[Rumor] = Field(default_factory=list)
    generation_tables: list[GenerationTable] = Field(default_factory=list)
    generation_entries: list[GenerationEntry] = Field(default_factory=list)
    encounters: list[Encounter] = Field(default_factory=list)
    rewards: list[Reward] = Field(default_factory=list)
    lore_entries: list[LoreEntry] = Field(default_factory=list)
    hex_cells: list[HexCell] = Field(default_factory=list)
    combats: list[Combat] = Field(default_factory=list)
    hexcrawl_settings: HexcrawlSettings | None = None
    expedition_state: ExpeditionState | None = None
    travel_logs: list[TravelLog] = Field(default_factory=list)
    player_view_settings: PlayerViewSettings | None = None
    excluded_content_notice: str = "Els fitxers de la biblioteca documental no s'inclouen en l'exportació."
