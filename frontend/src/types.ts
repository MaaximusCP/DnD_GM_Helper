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
  active:boolean; autonomy:number
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
export type DocumentChunk = {id:string;source_id:string;page?:number;section:string;text:string}
export type CampaignTemplate = {id:'blank'|'jungle_expedition'|'urban_intrigue'|'dungeon_delve';name:string;description:string;terrain:string}
export type NPCActionResult = {previous_day:number;current_day:number;proposals:EventProposal[];skipped:string[]}
export type Knowledge = { id:string; subject:string; content:string; confidence:number; truth_status:string; source_type:string }
export type Rumor = { id:string; subject:string; content:string; credibility:number; spread:number; status:string; origin_location_id?:string }
export type Encounter = { id:string; campaign_id:string; title:string; description:string; terrain:string; party_level:number; party_size:number; difficulty:number; encounter_type:string; objectives:string[]; complications:string[]; context_reasons:string[]; status:'generated'|'resolved' }
export type Reward = { id:string; title:string; terrain:string; difficulty:number; mode:string; fortune_roll?:number; tier:string; items:{name:string;quantity?:number;category?:string}[]; narrative_rewards:string[]; context_reasons:string[]; claimed:boolean; claimed_at?:string }
export type CharacterResource = { name:string; current:number; maximum:number; reset:'short'|'long'|'manual' }
export type Character = { id:string;campaign_id:string;name:string;player_name:string;class_name:string;ancestry:string;level:number;armor_class:number;max_hp:number;current_hp:number;temp_hp:number;speed:number;ability_scores:Record<string,number>;saving_throws:string[];skills:string[];passive_perception:number;exhaustion:number;conditions:string[];spell_slots:Record<string,number>;spell_slots_max:Record<string,number>;resources:CharacterResource[];notes:string;share_with_players:boolean;active:boolean;created_at:string;xp:number;milestone:number;inspiration:boolean;hit_dice_current:number;hit_dice_max:number;death_saves_success:number;death_saves_failure:number }
export type InventoryItem = { id:string;campaign_id:string;owner_type:'party'|'character'|'location';owner_id?:string;name:string;category:string;quantity:number;weight:number;value:number;currency_unit:'cp'|'sp'|'ep'|'gp'|'pp';description:string;equipped:boolean;attuned:boolean;consumable:boolean;reference_id?:string;source_id?:string;reward_id?:string;created_at:string }
export type Treasury = {campaign_id:string;cp:number;sp:number;ep:number;gp:number;pp:number;updated_at:string}
export type InventoryTransaction = {id:string;campaign_id:string;kind:string;description:string;item_id?:string;character_id?:string;currency?:string;currency_delta:number;quantity_delta:number;created_at:string}
export type LoreLayer = 'dm'|'players'|'world'
export type LoreEntry = { id:string; campaign_id:string; layer:LoreLayer; category:string; title:string; content:string; source_id?:string; source_page?:number; location_id?:string; created_at:string }
export type HexCell = { id:string; campaign_id:string; q:number; r:number; terrain:string; title:string; discovery:'hidden'|'discovered'|'explored'; travel_cost:number; encounter_chance:number; player_notes:string; dm_notes:string; location_id?:string; source_id?:string; risk_level:number; alert_level:number; risk_tags:string[] }
export type CombatAction = { name:string; description?:string; source?:string }
export type Combatant = { id:string; combat_id:string; name:string; kind:'player'|'enemy'|'ally'|'neutral'; initiative:number; initiative_bonus:number; armor_class:number; max_hp:number; current_hp:number; temp_hp:number; concentration:boolean; reaction_available:boolean; legendary_actions:number; legendary_actions_max:number; notes:string; conditions:string[]; actions:CombatAction[]; source_id?:string; reference_id?:string; character_id?:string }
export type Combat = { id:string; campaign_id:string; name:string; status:'active'|'completed'; round:number; turn_index:number; encounter_id?:string; summary:string; created_at:string; combatants:Combatant[] }
export type HexcrawlSettings = { campaign_id:string; track_weather:boolean; track_navigation:boolean; track_food:boolean; track_water:boolean; track_fatigue:boolean; track_encounters:boolean; track_foraging:boolean; auto_discover:boolean; default_pace:'slow'|'normal'|'fast'; hex_distance:number; distance_unit:'km'|'miles';track_risk:boolean;track_alert:boolean;alert_decay:boolean }
export type CampaignRecord = {id:string;campaign_id:string;kind:'quest'|'calendar'|'clock'|'scene'|'map'|'marker'|'library_link';title:string;status:string;visibility:'dm'|'players'|'world';due_day?:number;linked_id?:string;data:Record<string,unknown>;created_at:string;updated_at:string}
export type CampaignActivity = {id:string;campaign_id:string;session_id?:string;kind:string;title:string;details:string;visibility:'dm'|'players';linked_id?:string;created_at:string}
export type ExpeditionState = { campaign_id:string; current_hex_id?:string; food:number; water:number; supplies:number; exhaustion:number; lost:boolean; weather:string; updated_at:string }
export type TravelLog = { id:string; campaign_id:string; origin_hex_id?:string; destination_hex_id:string; route:string[]; pace:string; days:number; distance:number; distance_unit:string; weather:string; navigation_roll?:number; encounter_roll?:number; food_used:number; water_used:number; exhaustion_delta:number; encounter_triggered:boolean; encounter_id?:string; reached_destination:boolean; notes:string[]; created_at:string }
export type ExpeditionRestResult = { state:ExpeditionState; log:TravelLog; food_used:number; water_used:number; supplies_used:number; exhaustion_delta:number; day_advanced:number; notes:string[] }
export type PlayerViewSettings = { campaign_id:string; enabled:boolean; show_map:boolean; show_rumors:boolean; show_resources:boolean; show_weather:boolean; show_combat:boolean; show_enemy_hp:boolean; show_characters:boolean; show_inventory:boolean; show_library:boolean }
export type CombatLog = { id:string; combat_id:string; message:string; kind:string; created_at:string }
export type DiceRoll = {id:string;campaign_id:string;notation:string;label:string;actor:string;mode:'normal'|'advantage'|'disadvantage';dice:number[];kept:number[];modifier:number;total:number;dc?:number;success?:boolean;critical?:'success'|'failure';created_at:string}
export type PlayerView = { campaign:{id:string;name:string;current_day:number};party:{name:string};lore:LoreEntry[];hexes:Array<Pick<HexCell,'id'|'q'|'r'|'terrain'|'title'|'discovery'|'player_notes'>>;rumors:Rumor[];expedition:null|{food:number;water:number;supplies:number;exhaustion:number;lost:boolean;weather?:string};characters:Character[];inventory:InventoryItem[];treasury:Treasury|null;sources:ContentSource[];quests:CampaignRecord[];calendar:CampaignRecord[];maps:CampaignRecord[];markers:CampaignRecord[];timeline:CampaignActivity[];combats:Array<{id:string;name:string;round:number;turn_index:number;combatants:Array<{id:string;name:string;kind:string;initiative:number;conditions:string[];concentration:boolean;hp_status:string;current_hp?:number;max_hp?:number}>}>;settings:PlayerViewSettings }
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
  lore_entries: LoreEntry[]; hex_cells: HexCell[]; combats: Combat[]
  hexcrawl_settings: HexcrawlSettings; expedition_state: ExpeditionState; travel_logs: TravelLog[]
  player_view_settings: PlayerViewSettings
  characters: Character[]; inventory: InventoryItem[]; treasury: Treasury; inventory_transactions: InventoryTransaction[]
  campaign_records:CampaignRecord[];campaign_activities:CampaignActivity[]
}
export type SearchResult = { kind: 'npc' | 'event' | 'location' | 'faction' | 'memory' | 'record' | 'activity'; id: string; title: string; excerpt: string }
export type NPCCreate = {
  name: string; location_id: string; faction_id?: string; traits: string[]; goals: string[]
  values: string[]; secrets?: string[]; active?:boolean; autonomy?:number; relationship: Relationship
}
export type DocumentResult = { source_id:string; source_title:string; chunk_id:string; page?:number; excerpt:string; content:string; score:number }
export type ReferenceItem = {
  id:string; category:'magic-items'|'equipment'|'monsters'|'spells'|'conditions'; key:string; name:string
  summary:string; tags:string[]; data:Record<string, unknown>; source:string; license:string
}
export type ReferenceSearch = { total:number; offset:number; limit:number; items:ReferenceItem[] }
export type HomebrewCategory = 'enemy'|'temple'|'situation'|'minigame'
export type HomebrewPack = {id:string;name:string;version:string;license:string;counts:Partial<Record<HomebrewCategory,number>>;item_count:number;bundled:boolean;status:'ready'|'invalid';error:string}
export type HomebrewItem = {id:string;category:HomebrewCategory;name:string;summary:string;terrains:string[];min_level:number;max_level:number;difficulty:number;tags:string[];data:Record<string,unknown>;pack_id:string;pack_name:string}
export type HomebrewSearch = {total:number;offset:number;limit:number;items:HomebrewItem[]}
