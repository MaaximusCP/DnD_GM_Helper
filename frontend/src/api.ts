import type { Dashboard, DocumentResult, Encounter, EventProposal, Knowledge, NPC, NPCCreate, Reward, SearchResult, Session } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers)
  if (!(options?.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(body.detail ?? 'Error inesperat')
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  dashboard: () => request<Dashboard>('/campaigns/demo'),
  analyzeEvent: (description: string, npcId?: string, visibility: 'private'|'witnessed'|'public'='public') => request<EventProposal>('/events/analyze', {
    method: 'POST', body: JSON.stringify({ campaign_id: 'demo', description, npc_id: npcId || null, visibility }),
  }),
  applyEvent: (id: string) => request<EventProposal>(`/events/${id}/apply`, { method: 'POST' }),
  updateEvent: (id: string, payload: Partial<EventProposal>) => request<EventProposal>(`/events/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  ignoreEvent: (id: string) => request<EventProposal>(`/events/${id}/ignore`, { method: 'POST' }),
  undoEvent: (id: string) => request<EventProposal>(`/events/${id}/undo`, { method: 'POST' }),
  startSession: () => request<Session>('/sessions?campaign_id=demo', { method: 'POST' }),
  endSession: (id: string, summary: string) => request<Session>(`/sessions/${id}/end`, { method: 'POST', body: JSON.stringify({ summary }) }),
  createNpc: (payload: NPCCreate) => request<NPC>('/npcs?campaign_id=demo', { method: 'POST', body: JSON.stringify(payload) }),
  updateNpc: (id: string, payload: Partial<NPCCreate>) => request<NPC>(`/npcs/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteNpc: (id: string) => request<void>(`/npcs/${id}`, { method: 'DELETE' }),
  addMemory: (id: string, text: string) => request(`/npcs/${id}/memories`, { method: 'POST', body: JSON.stringify({ text, importance: 'important' }) }),
  search: (query: string) => request<SearchResult[]>(`/search?campaign_id=demo&q=${encodeURIComponent(query)}`),
  createBackup: () => request<{ name: string; size: number }>('/backups', { method: 'POST' }),
  listBackups: () => request<{ name: string; size: number; created_at: string }[]>('/backups'),
  exportCampaign: () => request<Record<string, unknown>>('/campaigns/demo/export'),
  uploadDocument: (form: FormData) => request('/library/upload', { method: 'POST', body: form }),
  searchLibrary: (query: string) => request<DocumentResult[]>(`/library/search?campaign_id=demo&q=${encodeURIComponent(query)}`),
  knowledge: (npcId: string) => request<Knowledge[]>(`/npcs/${npcId}/knowledge`),
  addKnowledge: (npcId: string, content: string) => request<Knowledge>(`/npcs/${npcId}/knowledge`, { method:'POST', body:JSON.stringify({subject:'Nota del DM',content,confidence:1,truth_status:'fact',source_type:'manual'}) }),
  generateEncounter: (payload: Record<string, unknown>) => request<Encounter>('/encounters/generate', { method:'POST', body:JSON.stringify({campaign_id:'demo',...payload}) }),
  generateReward: (payload: Record<string, unknown>) => request<Reward>('/rewards/generate', { method:'POST', body:JSON.stringify({campaign_id:'demo',...payload}) }),
  chat: (npcId: string, message: string) => request<{ reply: string; context_reasons: string[]; provider: string }>(
    `/npcs/${npcId}/chat`, { method: 'POST', body: JSON.stringify({ message, situation: 'Conversa durant la sessió', history: [] }) },
  ),
}
