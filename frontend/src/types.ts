export type Relationship = { trust: number; respect: number; fear: number; affection: number }
export type Memory = { id: string; npc_id: string; text: string; importance: string; created_at: string }
export type Campaign = {
  id: string; name: string; system: string; rules_profile: string; current_day: number
  current_location_id: string; archived: boolean
}
export type Location = { id: string; campaign_id: string; name: string; description: string; terrain: string }
export type Faction = { id: string; campaign_id: string; name: string; description: string }
export type PartySettings = { campaign_id: string; name: string; level: number; size: number; notes: string }
export type NPC = {
  id: string; campaign_id: string; name: string; location_id: string; faction_id?: string
  traits: string[]; goals: string[]; values: string[]; secrets: string[]
  relationship: Relationship; memories: Memory[]
}
export type Consequence = { kind: string; target_id: string; field: string; delta: number; text: string }
export type EventProposal = {
  id: string; campaign_id: string; title: string; description: string; event_type: string
  severity: number; consequences: Consequence[]; status: 'pending' | 'applied' | 'ignored'; created_at: string
  location_id?: string; visibility: 'private'|'witnessed'|'public'
}
export type Session = { id: string; campaign_id: string; started_at: string; ended_at?: string; summary: string }
export type ContentSource = {
  id:string; campaign_id:string; title:string; source_type:string; file_name:string; page_count:number
  chunk_count:number; status:string; visibility:string; asset_kind:string
}
export type Knowledge = { id:string; subject:string; content:string; confidence:number; truth_status:string; source_type:string }
export type Rumor = { id:string; subject:string; content:string; credibility:number; spread:number; status:string; origin_location_id?:string }
export type Encounter = { id:string; title:string; description:string; terrain:string; party_level:number; party_size:number; difficulty:number; encounter_type:string; objectives:string[]; complications:string[]; context_reasons:string[] }
export type Reward = { id:string; title:string; terrain:string; difficulty:number; mode:string; fortune_roll?:number; tier:string; items:{name:string;quantity?:number;category?:string}[]; narrative_rewards:string[]; context_reasons:string[] }
export type GenerationTable = { id:string; campaign_id:string; kind:'encounter'|'reward'; name:string; description:string; created_at:string }
export type GenerationEntry = {
  id:string; table_id:string; terrains:string[]; min_level:number; max_level:number
  min_difficulty:number; max_difficulty:number; weight:number; title:string
  payload:Record<string, unknown>; tags:string[]
}
export type Dashboard = {
  campaign: Campaign; location: Location; locations: Location[]; party: PartySettings
  world_state: Record<string, number | string>; npcs: NPC[]; factions: Faction[]
  events: EventProposal[]; sessions: Session[]; sources: ContentSource[]; rumors: Rumor[]
  encounters: Encounter[]; rewards: Reward[]; generation_tables: GenerationTable[]
}
export type SearchResult = { kind: 'npc' | 'event' | 'location' | 'faction' | 'memory'; id: string; title: string; excerpt: string }
export type NPCCreate = {
  name: string; location_id: string; faction_id?: string; traits: string[]; goals: string[]
  values: string[]; secrets?: string[]; relationship: Relationship
}
export type DocumentResult = { source_id:string; source_title:string; chunk_id:string; page?:number; excerpt:string; score:number }
export type ReferenceItem = {
  id:string; category:'magic-items'|'equipment'|'monsters'|'spells'; key:string; name:string
  summary:string; tags:string[]; data:Record<string, unknown>; source:string; license:string
}
export type ReferenceSearch = { total:number; offset:number; limit:number; items:ReferenceItem[] }
