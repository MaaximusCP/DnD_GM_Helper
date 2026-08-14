import type {
  Campaign, Dashboard, DocumentResult, Encounter, EventProposal, Faction, GenerationEntry,
  GenerationTable, Knowledge, Location, NPC, NPCCreate, PartySettings, Reward, SearchResult, Session,
  ReferenceItem, ReferenceSearch,
  Combat, Combatant, CombatLog, ExpeditionState, HexCell, HexcrawlSettings, LoreEntry, LoreLayer,
  PlayerView, PlayerViewSettings, TravelLog,
} from './types'

const API_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://127.0.0.1:8000/api' : '/api')

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers)
  if (!(options?.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(body.detail ?? 'Error inesperat')
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  campaigns: () => request<Campaign[]>('/campaigns'),
  dashboard: (campaignId: string) => request<Dashboard>(`/campaigns/${campaignId}`),
  createCampaign: (payload: {name:string; system:string; rules_profile:string; location_name:string}) => request<Campaign>('/campaigns', {method:'POST', body:JSON.stringify(payload)}),
  updateCampaign: (campaignId:string, payload:Partial<Campaign>) => request<Campaign>(`/campaigns/${campaignId}`, {method:'PATCH', body:JSON.stringify(payload)}),
  importCampaign: (payload:unknown) => request<Campaign>('/campaigns/import', {method:'POST', body:JSON.stringify(payload)}),
  analyzeEvent: (campaignId:string, description: string, npcId?: string, visibility: 'private'|'witnessed'|'public'='public') => request<EventProposal>('/events/analyze', {
    method: 'POST', body: JSON.stringify({ campaign_id: campaignId, description, npc_id: npcId || null, visibility }),
  }),
  applyEvent: (id: string) => request<EventProposal>(`/events/${id}/apply`, { method: 'POST' }),
  updateEvent: (id: string, payload: Partial<EventProposal>) => request<EventProposal>(`/events/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  ignoreEvent: (id: string) => request<EventProposal>(`/events/${id}/ignore`, { method: 'POST' }),
  undoEvent: (id: string) => request<EventProposal>(`/events/${id}/undo`, { method: 'POST' }),
  startSession: (campaignId:string) => request<Session>(`/sessions?campaign_id=${campaignId}`, { method: 'POST' }),
  endSession: (id: string, summary: string) => request<Session>(`/sessions/${id}/end`, { method: 'POST', body: JSON.stringify({ summary }) }),
  createNpc: (campaignId:string, payload: NPCCreate) => request<NPC>(`/npcs?campaign_id=${campaignId}`, { method: 'POST', body: JSON.stringify(payload) }),
  updateNpc: (id: string, payload: Partial<NPCCreate>) => request<NPC>(`/npcs/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteNpc: (id: string) => request<void>(`/npcs/${id}`, { method: 'DELETE' }),
  addMemory: (id: string, text: string) => request(`/npcs/${id}/memories`, { method: 'POST', body: JSON.stringify({ text, importance: 'important' }) }),
  search: (campaignId:string, query: string) => request<SearchResult[]>(`/search?campaign_id=${campaignId}&q=${encodeURIComponent(query)}`),
  createBackup: () => request<{ name: string; size: number }>('/backups', { method: 'POST' }),
  exportCampaign: (campaignId:string) => request<Record<string, unknown>>(`/campaigns/${campaignId}/export`),
  uploadDocument: (form: FormData) => request('/library/upload', { method: 'POST', body: form }),
  deleteDocument: (id:string) => request<void>(`/library/${id}?confirm=true`, {method:'DELETE'}),
  searchLibrary: (campaignId:string, query: string) => request<DocumentResult[]>(`/library/search?campaign_id=${campaignId}&q=${encodeURIComponent(query)}`),
  knowledge: (npcId: string) => request<Knowledge[]>(`/npcs/${npcId}/knowledge`),
  addKnowledge: (npcId: string, content: string) => request<Knowledge>(`/npcs/${npcId}/knowledge`, { method:'POST', body:JSON.stringify({subject:'Nota del DM',content,confidence:1,truth_status:'fact',source_type:'manual'}) }),
  generateEncounter: (campaignId:string, payload: Record<string, unknown>) => request<Encounter>('/encounters/generate', { method:'POST', body:JSON.stringify({campaign_id:campaignId,...payload}) }),
  generateReward: (campaignId:string, payload: Record<string, unknown>) => request<Reward>('/rewards/generate', { method:'POST', body:JSON.stringify({campaign_id:campaignId,...payload}) }),
  chat: (npcId: string, message: string) => request<{ reply: string; context_reasons: string[]; provider: string }>(`/npcs/${npcId}/chat`, { method: 'POST', body: JSON.stringify({ message, situation: 'Conversa durant la sessió', history: [] }) }),
  createLocation: (campaignId:string,payload:{name:string;description:string;terrain:string}) => request<Location>(`/campaigns/${campaignId}/locations`,{method:'POST',body:JSON.stringify(payload)}),
  updateLocation: (id:string,payload:Partial<Location>) => request<Location>(`/locations/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  deleteLocation: (id:string) => request<void>(`/locations/${id}?confirm=true`,{method:'DELETE'}),
  createFaction: (campaignId:string,payload:{name:string;description:string}) => request<Faction>(`/campaigns/${campaignId}/factions`,{method:'POST',body:JSON.stringify(payload)}),
  updateFaction: (id:string,payload:Partial<Faction>) => request<Faction>(`/factions/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  deleteFaction: (id:string) => request<void>(`/factions/${id}?confirm=true`,{method:'DELETE'}),
  updateParty: (campaignId:string,payload:Omit<PartySettings,'campaign_id'>) => request<PartySettings>(`/campaigns/${campaignId}/party`,{method:'PUT',body:JSON.stringify(payload)}),
  setWorldState: (campaignId:string,key:string,value:string|number) => request<Record<string,string|number>>(`/campaigns/${campaignId}/world-state/${encodeURIComponent(key)}`,{method:'PUT',body:JSON.stringify({value})}),
  deleteWorldState: (campaignId:string,key:string) => request<void>(`/campaigns/${campaignId}/world-state/${encodeURIComponent(key)}?confirm=true`,{method:'DELETE'}),
  tables: (campaignId:string) => request<GenerationTable[]>(`/generation-tables?campaign_id=${campaignId}`),
  createTable: (campaignId:string,payload:{kind:'encounter'|'reward';name:string;description:string}) => request<GenerationTable>('/generation-tables',{method:'POST',body:JSON.stringify({campaign_id:campaignId,...payload})}),
  deleteTable: (id:string) => request<void>(`/generation-tables/${id}?confirm=true`,{method:'DELETE'}),
  entries: (tableId:string) => request<GenerationEntry[]>(`/generation-tables/${tableId}/entries`),
  createEntry: (tableId:string,payload:Omit<GenerationEntry,'id'|'table_id'>) => request<GenerationEntry>(`/generation-tables/${tableId}/entries`,{method:'POST',body:JSON.stringify(payload)}),
  updateEntry: (id:string,payload:Omit<GenerationEntry,'id'|'table_id'>) => request<GenerationEntry>(`/generation-entries/${id}`,{method:'PUT',body:JSON.stringify(payload)}),
  deleteEntry: (id:string) => request<void>(`/generation-entries/${id}?confirm=true`,{method:'DELETE'}),
  reference: (query:string,category:string,offset=0) => request<ReferenceSearch>(`/reference?q=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}&limit=50&offset=${offset}`),
  referenceItem: (id:string) => request<ReferenceItem>(`/reference/item/${encodeURIComponent(id)}`),
  referenceMeta: () => request<{counts:Record<string,number>;license:string;dataset:string}>('/reference/meta'),
  createLore: (campaignId:string,payload:{layer:LoreLayer;category:string;title:string;content:string;source_id?:string;location_id?:string}) => request<LoreEntry>('/lore',{method:'POST',body:JSON.stringify({campaign_id:campaignId,...payload})}),
  updateLore: (id:string,payload:Partial<LoreEntry>) => request<LoreEntry>(`/lore/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  deleteLore: (id:string) => request<void>(`/lore/${id}?confirm=true`,{method:'DELETE'}),
  createHex: (campaignId:string,payload:Omit<HexCell,'id'|'campaign_id'>) => request<HexCell>('/hexes',{method:'POST',body:JSON.stringify({campaign_id:campaignId,...payload})}),
  updateHex: (id:string,payload:Partial<HexCell>) => request<HexCell>(`/hexes/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  hexcrawlSettings: (campaignId:string) => request<HexcrawlSettings>(`/campaigns/${campaignId}/hexcrawl-settings`),
  updateHexcrawlSettings: (campaignId:string,payload:Partial<HexcrawlSettings>) => request<HexcrawlSettings>(`/campaigns/${campaignId}/hexcrawl-settings`,{method:'PATCH',body:JSON.stringify(payload)}),
  expedition: (campaignId:string) => request<{state:ExpeditionState;logs:TravelLog[]}>(`/campaigns/${campaignId}/expedition`),
  updateExpedition: (campaignId:string,payload:Partial<ExpeditionState>) => request<ExpeditionState>(`/campaigns/${campaignId}/expedition`,{method:'PATCH',body:JSON.stringify(payload)}),
  travel: (campaignId:string,payload:{destination_hex_id:string;pace?:string;navigation_roll?:number;encounter_roll?:number;foraging_roll?:number;manual_weather?:string}) => request<TravelLog>(`/campaigns/${campaignId}/travel`,{method:'POST',body:JSON.stringify(payload)}),
  playerView: (campaignId:string) => request<PlayerView>(`/player-view/${campaignId}`),
  updatePlayerViewSettings: (campaignId:string,payload:Partial<PlayerViewSettings>) => request<PlayerViewSettings>(`/campaigns/${campaignId}/player-view-settings`,{method:'PATCH',body:JSON.stringify(payload)}),
  createCombat: (campaignId:string,name:string,encounterId?:string) => request<Combat>('/combats',{method:'POST',body:JSON.stringify({campaign_id:campaignId,name,encounter_id:encounterId||null})}),
  updateCombat: (id:string,payload:Partial<Combat>) => request<Combat>(`/combats/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  nextTurn: (id:string) => request<Combat>(`/combats/${id}/next-turn`,{method:'POST'}),
  addCombatant: (combatId:string,payload:Record<string,unknown>) => request<Combatant>(`/combats/${combatId}/combatants`,{method:'POST',body:JSON.stringify(payload)}),
  addReferenceCombatant: (combatId:string,referenceId:string,initiative:number,quantity=1) => request<Combatant|Combatant[]>(`/combats/${combatId}/combatants/from-reference`,{method:'POST',body:JSON.stringify({reference_id:referenceId,initiative,quantity})}),
  updateCombatant: (id:string,payload:Partial<Combatant>) => request<Combatant>(`/combatants/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  deleteCombatant: (id:string) => request<void>(`/combatants/${id}?confirm=true`,{method:'DELETE'}),
  duplicateCombatant: (id:string,quantity:number) => request<Combatant[]>(`/combatants/${id}/duplicate`,{method:'POST',body:JSON.stringify({quantity})}),
  rollInitiative: (id:string,automatic=true,rolls:Record<string,number>={}) => request<Combat>(`/combats/${id}/initiative`,{method:'POST',body:JSON.stringify({automatic,rolls})}),
  combatLog: (id:string) => request<CombatLog[]>(`/combats/${id}/log`),
  combatRoll: (id:string,notation:string,label:string,combatantId?:string) => request<{notation:string;dice:number[];modifier:number;total:number;label:string}>(`/combats/${id}/roll`,{method:'POST',body:JSON.stringify({notation,label,combatant_id:combatantId||null})}),
}
