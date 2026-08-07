import { useEffect, useState } from 'react'
import { Archive, BookOpen, Bot, ChevronRight, CircleAlert, Clock3, Database, Dices, Download, FileText, Gift, LayoutDashboard, Map, Menu, MessageSquare, Save, Search, Shield, Sparkles, Swords, Trash2, Undo2, UserPlus, Users, X } from 'lucide-react'
import { api } from './api'
import type { Dashboard, DocumentResult, Encounter, EventProposal, Knowledge, NPC, NPCCreate, Reward, SearchResult } from './types'

const nav = [
  [LayoutDashboard, 'Sessió'], [Users, 'NPCs'], [Map, 'Món'], [Shield, 'Faccions'],
  [BookOpen, 'Esdeveniments'], [Archive, 'Biblioteca'], [MessageSquare, 'Rumors'], [Swords, 'Encounters'], [Gift, 'Recompenses'],
] as const

function RelationBar({ label, value }: { label: string; value: number }) {
  const width = Math.max(3, Math.abs(value))
  return <div className="relation"><span>{label}</span><div className="bar"><i style={{ width: `${width}%` }} className={value < 0 ? 'negative' : ''} /></div><b>{value}</b></div>
}

function Proposal({ event, onDone }: { event: EventProposal; onDone: () => void }) {
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(event)
  const act = async (action: 'apply' | 'ignore') => {
    setBusy(true)
    try {
      if (action === 'apply' && editing) await api.updateEvent(event.id, { title: draft.title, severity: draft.severity, consequences: draft.consequences, visibility:draft.visibility })
      if (action === 'apply') await api.applyEvent(event.id)
      else await api.ignoreEvent(event.id)
      onDone()
    }
    finally { setBusy(false) }
  }
  return <section className="proposal">
    <div className="proposal-head"><span>Proposta pendent · {event.visibility==='public'?'públic':event.visibility==='witnessed'?'amb testimonis':'privat'}</span><em>Severitat {event.severity}/10</em></div>
    {editing ? <div className="proposal-editor"><label>Títol<input value={draft.title} onChange={e => setDraft({...draft, title:e.target.value})}/></label><label>Severitat<input type="number" min="1" max="10" value={draft.severity} onChange={e => setDraft({...draft, severity:Number(e.target.value)})}/></label><label>Visibilitat<select value={draft.visibility} onChange={e=>setDraft({...draft,visibility:e.target.value as EventProposal['visibility']})}><option value="public">Públic</option><option value="witnessed">Testimonis</option><option value="private">Privat</option></select></label></div> : <><h3>{event.title}</h3><p>{event.description}</p></>}
    <div className="changes">{draft.consequences.length ? draft.consequences.map((item, i) =>
      <div key={i}><ChevronRight size={15}/><span>{item.kind === 'memory' ? `Crear memòria: ${item.text}` : `${item.field}: ${item.delta > 0 ? '+' : ''}${item.delta}`}</span>{editing && item.kind !== 'memory' && <input className="delta-input" type="number" value={item.delta} onChange={e => { const consequences=[...draft.consequences]; consequences[i]={...item,delta:Number(e.target.value)}; setDraft({...draft,consequences}) }}/>} {editing && <button className="mini danger" onClick={() => setDraft({...draft, consequences:draft.consequences.filter((_,index)=>index!==i)})}>×</button>}</div>
    ) : <small>No s'han detectat canvis automàtics. El fet es conservarà al timeline.</small>}</div>
    <div className="actions"><button disabled={busy} onClick={() => setEditing(!editing)}>{editing ? 'Cancel·lar edició' : 'Modificar'}</button><button className="primary" disabled={busy} onClick={() => act('apply')}>{editing ? 'Desar i aplicar' : 'Aplicar canvis'}</button><button disabled={busy} onClick={() => act('ignore')}>Ignorar</button></div>
  </section>
}

function NPCPanel({ npc, close, changed }: { npc: NPC; close: () => void; changed: () => void }) {
  const [message, setMessage] = useState('')
  const [reply, setReply] = useState('')
  const [reasons, setReasons] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [memory, setMemory] = useState('')
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(npc.name)
  const [traits, setTraits] = useState(npc.traits.join(', '))
  const [goal, setGoal] = useState(npc.goals.join(', '))
  const [knowledge,setKnowledge]=useState<Knowledge[]>([])
  const [newKnowledge,setNewKnowledge]=useState('')
  useEffect(()=>{void api.knowledge(npc.id).then(setKnowledge)},[npc.id])
  const send = async () => {
    if (!message.trim()) return
    setBusy(true)
    try { const result = await api.chat(npc.id, message); setReply(result.reply); setReasons(result.context_reasons); setMessage('') }
    catch (error) { setReply(error instanceof Error ? error.message : 'No s’ha pogut contactar amb el model.') }
    finally { setBusy(false) }
  }
  const saveNpc = async () => {
    setBusy(true)
    try { await api.updateNpc(npc.id, { name, traits: traits.split(',').map(x=>x.trim()).filter(Boolean), goals: goal.split(',').map(x=>x.trim()).filter(Boolean) }); setEditing(false); changed() }
    finally { setBusy(false) }
  }
  const addMemory = async () => { if (!memory.trim()) return; setBusy(true); try { await api.addMemory(npc.id, memory); setMemory(''); changed() } finally { setBusy(false) } }
  const remove = async () => { if (!confirm(`Vols eliminar definitivament ${npc.name}?`)) return; await api.deleteNpc(npc.id); changed(); close() }
  const addKnowledge=async()=>{if(!newKnowledge.trim())return;const item=await api.addKnowledge(npc.id,newKnowledge);setKnowledge([item,...knowledge]);setNewKnowledge('')}
  return <div className="drawer-overlay" onMouseDown={close}><aside className="npc-drawer" onMouseDown={e => e.stopPropagation()}>
    <button className="icon-button close" onClick={close} aria-label="Tancar"><X /></button>
    <span className="eyebrow">NPC persistent</span>{editing ? <div className="edit-fields"><label>Nom<input value={name} onChange={e=>setName(e.target.value)}/></label><label>Trets, separats per comes<input value={traits} onChange={e=>setTraits(e.target.value)}/></label><label>Objectius<input value={goal} onChange={e=>setGoal(e.target.value)}/></label><button className="primary" onClick={saveNpc} disabled={busy}><Save size={15}/> Desar</button></div> : <><h2>{npc.name}</h2><p className="traits">{npc.traits.join(' · ')}</p></>}
    <div className="inline-actions"><button onClick={()=>setEditing(!editing)}>{editing?'Cancel·lar':'Editar fitxa'}</button><button className="danger" onClick={remove}><Trash2 size={14}/> Eliminar</button></div>
    <h4>Relació amb el grup</h4>
    <RelationBar label="Confiança" value={npc.relationship.trust}/><RelationBar label="Respecte" value={npc.relationship.respect}/>
    <RelationBar label="Por" value={npc.relationship.fear}/><RelationBar label="Afecte" value={npc.relationship.affection}/>
    <h4>Objectiu actual</h4><p>{npc.goals[0]}</p>
    <h4>Memòries</h4><div className="memory-list">{npc.memories.map(m => <p key={m.id}>{m.text}</p>)}{!npc.memories.length && <p>Encara no té memòries rellevants.</p>}</div><div className="chat-input"><input value={memory} onChange={e=>setMemory(e.target.value)} placeholder="Afegir una memòria manual..."/><button onClick={addMemory} disabled={busy}>Afegir</button></div>
    <details className="knowledge"><summary>Coneixement i creences ({knowledge.length})</summary>{knowledge.map(item=><div key={item.id}><span>{item.truth_status} · {Math.round(item.confidence*100)}%</span><p>{item.content}</p></div>)}<div className="chat-input"><input value={newKnowledge} onChange={e=>setNewKnowledge(e.target.value)} placeholder="Afegir un fet que coneix..."/><button onClick={addKnowledge}>Afegir</button></div></details>
    <div className="chat"><h4><Bot size={18}/> Parlar com {npc.name}</h4>{reply && <div className="reply">{reply}</div>}
      {reasons.length > 0 && <details><summary>Per què respon així?</summary>{reasons.map(r => <p key={r}>{r}</p>)}</details>}
      <div className="chat-input"><input value={message} onChange={e => setMessage(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Escriu què diu el personatge..."/><button className="primary" onClick={send} disabled={busy}>{busy ? 'Pensant…' : 'Enviar'}</button></div>
    </div>
  </aside></div>
}

function CreateNPC({ data, close, done }: { data: Dashboard; close:()=>void; done:()=>void }) {
  const [form,setForm]=useState<NPCCreate>({name:'',location_id:data.location.id,faction_id:data.factions[0]?.id,traits:[],goals:[],values:[],relationship:{trust:0,respect:0,fear:0,affection:0}})
  const [traits,setTraits]=useState(''); const [goals,setGoals]=useState(''); const [busy,setBusy]=useState(false)
  const submit=async()=>{if(form.name.trim().length<2)return;setBusy(true);try{await api.createNpc({...form,traits:traits.split(',').map(x=>x.trim()).filter(Boolean),goals:goals.split(',').map(x=>x.trim()).filter(Boolean)});done()}finally{setBusy(false)}}
  return <div className="drawer-overlay" onMouseDown={close}><div className="modal" onMouseDown={e=>e.stopPropagation()}><button className="icon-button close" onClick={close}><X/></button><span className="eyebrow">Nou personatge</span><h2>Crear NPC</h2><label>Nom<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Localització<select value={form.location_id} onChange={e=>setForm({...form,location_id:e.target.value})}>{data.locations.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Facció<select value={form.faction_id??''} onChange={e=>setForm({...form,faction_id:e.target.value||undefined})}><option value="">Sense facció</option>{data.factions.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Trets, separats per comes<input value={traits} onChange={e=>setTraits(e.target.value)} placeholder="prudent, curiosa, lleial"/></label><label>Objectius<input value={goals} onChange={e=>setGoals(e.target.value)} placeholder="protegir el negoci"/></label><button className="primary full" disabled={busy||form.name.trim().length<2} onClick={submit}><UserPlus size={16}/> Crear NPC</button></div></div>
}

function SearchPanel({ close, openNpc }: { close:()=>void; openNpc:(id:string)=>void }) {
  const [query,setQuery]=useState(''); const [results,setResults]=useState<SearchResult[]>([])
  useEffect(()=>{const timer=setTimeout(()=>{if(query.trim().length>=2)api.search(query).then(setResults);else setResults([])},250);return()=>clearTimeout(timer)},[query])
  return <div className="drawer-overlay" onMouseDown={close}><div className="search-modal" onMouseDown={e=>e.stopPropagation()}><div className="search-box"><Search/><input autoFocus value={query} onChange={e=>setQuery(e.target.value)} placeholder="Cerca NPC, memòries, llocs, faccions..."/><button className="icon-button" onClick={close}><X/></button></div>{results.map(r=><button className="search-result" key={`${r.kind}-${r.id}`} onClick={()=>{if(r.kind==='npc')openNpc(r.id)}}><span>{r.kind}</span><div><strong>{r.title}</strong><p>{r.excerpt}</p></div><ChevronRight/></button>)}{query.length>=2&&!results.length&&<p className="empty-search">Cap resultat.</p>}</div></div>
}

const terrains = ['urban','forest','jungle','dungeon','ruins','coast','river','swamp','mountain','desert','other']
const terrainNames:Record<string,string>={urban:'Ciutat',forest:'Bosc',jungle:'Selva',dungeon:'Dungeon',ruins:'Ruïnes',coast:'Costa',river:'Riu',swamp:'Pantà',mountain:'Muntanya',desert:'Desert',other:'Altres'}
const difficultyNames=['','Fàcil','Moderada','Mitjana','Difícil','Mortal']

function LibraryPanel({data,close,changed}:{data:Dashboard;close:()=>void;changed:()=>void}){
  const [file,setFile]=useState<File|null>(null);const [title,setTitle]=useState('');const [sourceType,setSourceType]=useState('official');const [busy,setBusy]=useState(false);const [query,setQuery]=useState('');const [results,setResults]=useState<DocumentResult[]>([]);const [error,setError]=useState('')
  const upload=async()=>{if(!file)return;setBusy(true);setError('');const form=new FormData();form.append('file',file);form.append('campaign_id',data.campaign.id);form.append('title',title||file.name);form.append('source_type',sourceType);form.append('visibility','dm');try{await api.uploadDocument(form);changed();setFile(null);setTitle('')}catch(e){setError(e instanceof Error?e.message:'No s’ha pogut carregar')}finally{setBusy(false)}}
  const search=async()=>{if(query.trim().length<2)return;setResults(await api.searchLibrary(query))}
  return <div className="drawer-overlay" onMouseDown={close}><div className="modal wide" onMouseDown={e=>e.stopPropagation()}><button className="icon-button close" onClick={close}><X/></button><span className="eyebrow">Biblioteca local</span><h2>Documents de campanya</h2><p className="modal-intro">PDF, Markdown i text. Els originals queden al teu ordinador i no entren a Git.</p>
    <div className="upload-zone"><FileText/><input type="file" accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp" onChange={e=>setFile(e.target.files?.[0]??null)}/><input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Títol opcional"/><select value={sourceType} onChange={e=>setSourceType(e.target.value)}><option value="official">Font oficial pròpia</option><option value="homebrew">Homebrew</option><option value="notes">Notes del DM</option></select><button className="primary" disabled={!file||busy} onClick={upload}>{busy?'Processant…':'Pujar i indexar'}</button></div>{error&&<div className="alert">{error}</div>}
    <div className="source-list">{data.sources.map(source=><div key={source.id}><Archive/><div><strong>{source.title}</strong><p>{source.asset_kind} · {source.source_type} · {source.page_count} pàgines · {source.chunk_count} fragments</p></div><span className={source.status==='ready'?'ready':'warning-text'}>{source.status==='ready'?'Preparat':'Necessita OCR'}</span></div>)}{!data.sources.length&&<p className="empty-search">Encara no hi ha documents o mapes.</p>}</div>
    <div className="library-search"><input value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==='Enter'&&search()} placeholder="Cerca dins dels documents..."/><button onClick={search}><Search size={16}/> Cercar</button></div>{results.map(result=><div className="document-result" key={result.chunk_id}><strong>{result.source_title} · pàgina {result.page??'—'}</strong><p>{result.excerpt}</p></div>)}
  </div></div>
}

function GeneratorPanel({kind,data,close,done}:{kind:'encounter'|'reward';data:Dashboard;close:()=>void;done:()=>void}){
  const [terrain,setTerrain]=useState(data.location.terrain||'urban');const [difficulty,setDifficulty]=useState(3);const [level,setLevel]=useState(3);const [partySize,setPartySize]=useState(4);const [type,setType]=useState('auto');const [mode,setMode]=useState('neutral');const [encounterId,setEncounterId]=useState(data.encounters[0]?.id??'');const [result,setResult]=useState<Encounter|Reward|null>(kind==='encounter'?(data.encounters[0]??null):(data.rewards[0]??null));const [busy,setBusy]=useState(false);const [error,setError]=useState('')
  const selectEncounter=(id:string)=>{setEncounterId(id);const encounter=data.encounters.find(item=>item.id===id);if(encounter){setTerrain(encounter.terrain);setDifficulty(encounter.difficulty);setLevel(encounter.party_level)}}
  const generate=async()=>{setBusy(true);setError('');try{if(kind==='encounter')setResult(await api.generateEncounter({location_id:data.location.id,terrain,party_level:level,party_size:partySize,difficulty,encounter_type:type}));else setResult(await api.generateReward({location_id:data.location.id,encounter_id:encounterId||null,terrain,party_level:level,difficulty,mode}));done()}catch(e){setError(e instanceof Error?e.message:'No s’ha pogut generar')}finally{setBusy(false)}}
  return <div className="drawer-overlay" onMouseDown={close}><div className="modal generator-modal" onMouseDown={e=>e.stopPropagation()}><button className="icon-button close" onClick={close}><X/></button><span className="eyebrow">{kind==='encounter'?'Encounter Engine':'Reward Engine'}</span><h2>{kind==='encounter'?'Crear encounter':'Generar recompensa'}</h2>
    {kind==='reward'&&<label>Encounter relacionat<select value={encounterId} onChange={e=>selectEncounter(e.target.value)}><option value="">Cap encounter concret</option>{data.encounters.map(item=><option value={item.id} key={item.id}>{item.title} · {terrainNames[item.terrain]??item.terrain}</option>)}</select></label>}<div className="generator-grid"><label>Terreny<select value={terrain} onChange={e=>setTerrain(e.target.value)}>{terrains.map(item=><option value={item} key={item}>{terrainNames[item]}</option>)}</select></label><label>Nivell del grup<input type="number" min="1" max="20" value={level} onChange={e=>setLevel(Number(e.target.value))}/></label>{kind==='encounter'&&<label>Mida del grup<input type="number" min="1" max="12" value={partySize} onChange={e=>setPartySize(Number(e.target.value))}/></label>}{kind==='encounter'?<label>Tipus<select value={type} onChange={e=>setType(e.target.value)}><option value="auto">Automàtic</option><option value="combat">Combat</option><option value="social">Social</option><option value="exploration">Exploració</option><option value="hazard">Perill</option><option value="mixed">Mixt</option></select></label>:<label>Mode<select value={mode} onChange={e=>setMode(e.target.value)}><option value="neutral">Neutral</option><option value="fortune">Fortuna d20</option></select></label>}</div>
    <label className="range-label"><span>Dificultat <b>{difficultyNames[difficulty]}</b></span><input type="range" min="1" max="5" step="1" value={difficulty} onChange={e=>setDifficulty(Number(e.target.value))}/><div><small>Fàcil</small><small>Mortal</small></div></label><button className="primary full" onClick={generate} disabled={busy}>{busy?'Generant…':kind==='encounter'?'Generar encounter':'Generar recompensa'}</button>{error&&<div className="alert">{error}</div>}
    {result&&<div className="generated-result"><span>{result.terrain} · dificultat {result.difficulty}/5</span><h3>{result.title}</h3>{'description'in result&&<p>{result.description}</p>}{'objectives'in result&&result.objectives.map(item=><p key={item}>Objectiu: {item}</p>)}{'complications'in result&&result.complications.map(item=><p key={item}>⚠ {item}</p>)}{'items'in result&&result.items.map((item,index)=><p key={index}>🎁 {item.quantity??1} × {item.name}</p>)}{'narrative_rewards'in result&&result.narrative_rewards.map(item=><p key={item}>◆ {item}</p>)}{'fortune_roll'in result&&result.fortune_roll&&<strong>Tirada: {result.fortune_roll} · {result.tier}</strong>}<details><summary>Per què aquesta opció?</summary>{result.context_reasons.map(reason=><p key={reason}>{reason}</p>)}</details></div>}
  </div></div>
}

export default function App() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [error, setError] = useState('')
  const [eventText, setEventText] = useState('')
  const [npcId, setNpcId] = useState('')
  const [visibility,setVisibility]=useState<'private'|'witnessed'|'public'>('public')
  const [proposal, setProposal] = useState<EventProposal | null>(null)
  const [selectedNpc, setSelectedNpc] = useState<NPC | null>(null)
  const [busy, setBusy] = useState(false)
  const [creatingNpc, setCreatingNpc] = useState(false)
  const [searching, setSearching] = useState(false)
  const [notice, setNotice] = useState('')
  const [panel,setPanel]=useState<'library'|'encounter'|'reward'|null>(null)
  const load = () => api.dashboard().then(setData).catch(e => setError(e.message))
  useEffect(() => { void load() }, [])
  const analyze = async () => {
    if (eventText.trim().length < 3) return
    setBusy(true); setError('')
    try { setProposal(await api.analyzeEvent(eventText, npcId || undefined, visibility)) }
    catch (e) { setError(e instanceof Error ? e.message : 'No s’ha pogut analitzar el fet.') }
    finally { setBusy(false) }
  }
  const complete = () => { setProposal(null); setEventText(''); load() }
  const activeSession = data?.sessions.find(session => !session.ended_at)
  const toggleSession = async () => {
    setBusy(true)
    try {
      if (activeSession) {
        const summary = prompt('Resum de la sessió (opcional):', '') ?? ''
        await api.endSession(activeSession.id, summary); setNotice('Sessió finalitzada i desada.')
      } else { await api.startSession(); setNotice('Sessió iniciada.') }
      await load()
    } finally { setBusy(false) }
  }
  const createBackup = async () => { const result=await api.createBackup(); setNotice(`Backup creat: ${result.name}`) }
  const exportCampaign = async () => { const result=await api.exportCampaign(); const blob=new Blob([JSON.stringify(result,null,2)],{type:'application/json'}); const url=URL.createObjectURL(blob); const anchor=document.createElement('a'); anchor.href=url; anchor.download='gm-ai-campaign-demo.json'; anchor.click(); URL.revokeObjectURL(url); setNotice('Campanya exportada.') }
  const undo = async (id:string) => { if(!confirm('Vols desfer els canvis d’aquest esdeveniment?'))return; await api.undoEvent(id); setNotice('Canvis desfets; la proposta torna a estar pendent.'); load() }
  const openNpcById=(id:string)=>{const npc=data?.npcs.find(x=>x.id===id);if(npc)setSelectedNpc(npc);setSearching(false)}
  const handleNav=(label:string)=>{if(label==='Biblioteca')return setPanel('library');if(label==='Encounters')return setPanel('encounter');if(label==='Recompenses')return setPanel('reward');const targets:Record<string,string>={Sessió:'session',NPCs:'npcs',Món:'context',Faccions:'context',Esdeveniments:'events',Rumors:'rumors'};document.getElementById(targets[label]??'session')?.scrollIntoView({behavior:'smooth'})}

  if (error && !data) return <main className="offline"><CircleAlert/><h1>El backend no està disponible</h1><p>{error}</p><code>cd backend<br/>python -m uvicorn app.main:app --reload</code><button onClick={load}>Tornar-ho a provar</button></main>
  if (!data) return <main className="loading"><Sparkles/><span>Carregant el món…</span></main>

  return <div className="app-shell">
    <header><button className="icon-button mobile-menu"><Menu/></button><div className="brand-mark">GM</div><div><span>Campaign Engine</span><strong>{data.campaign.name}</strong></div><div className="header-meta"><span>Dia {data.campaign.current_day}</span><span>{data.location.name}</span><button className="icon-button" onClick={()=>setSearching(true)} aria-label="Cerca"><Search/></button></div></header>
    <nav><p>TAULA DEL DM</p>{nav.map(([Icon, label], i) => <button key={label} className={i === 0 ? 'active' : ''} onClick={()=>handleNav(label)}><Icon size={19}/><span>{label}</span>{label==='Rumors'&&data.rumors.length>0&&<small>{data.rumors.length}</small>}</button>)}<div className="nav-foot"><span className="status-dot"/>Local · dades privades</div></nav>
    <main className="workspace" id="session">
      <div className="page-title"><div><span className="eyebrow">Mode sessió</span><h1>Taula de campanya</h1></div><button className={`session-button ${activeSession?'active':''}`} disabled={busy} onClick={toggleSession}><span className="pulse"/>{activeSession?'Finalitzar sessió':'Començar sessió'}</button></div>
      {notice&&<div className="notice" onClick={()=>setNotice('')}>{notice}<X size={14}/></div>}
      <section className="event-composer"><div className="composer-title"><Sparkles size={19}/><div><h2>Què acaba de passar?</h2><p>Descriu el fet. Revisaràs tots els canvis abans d’aplicar-los.</p></div></div>
        <textarea value={eventText} onChange={e => setEventText(e.target.value)} placeholder="Ex.: El grup ha ajudat la Kara a recuperar la mercaderia robada..."/>
        <div className="composer-actions"><select value={visibility} onChange={e=>setVisibility(e.target.value as typeof visibility)}><option value="public">Públic · pot generar rumor</option><option value="witnessed">Amb testimonis</option><option value="private">Privat</option></select><select value={npcId} onChange={e => setNpcId(e.target.value)}><option value="">Cap NPC concret</option>{data.npcs.map(n => <option value={n.id} key={n.id}>{n.name}</option>)}</select><button className="primary" onClick={analyze} disabled={busy || eventText.trim().length < 3}>{busy ? 'Analitzant…' : 'Analitzar fet'}</button></div>
      </section>
      {error && <div className="alert">{error}</div>}{proposal && <Proposal event={proposal} onDone={complete}/>} 
      <section id="npcs"><div className="section-head"><div><h2>NPCs presents</h2><p>Context i memòria preparats per conversar</p></div><button onClick={()=>setCreatingNpc(true)}>+ Afegir NPC</button></div>
        <div className="npc-grid">{data.npcs.map(npc => <button className="npc-card" key={npc.id} onClick={() => setSelectedNpc(npc)}><div className="avatar">{npc.name.slice(0, 1)}</div><div><h3>{npc.name}</h3><p>{npc.traits.slice(0, 2).join(' · ')}</p><span>Confiança {npc.relationship.trust}</span></div><ChevronRight/></button>)}</div>
      </section>
      <section className="timeline" id="events"><div className="section-head"><div><h2>Activitat recent</h2><p>El timeline conserva les decisions del món</p></div><Clock3/></div>
        {data.events.length ? data.events.slice(0, 8).map(e => <div className="timeline-row" key={e.id}><span className={`event-dot ${e.status}`}/><div><h4>{e.title}</h4><p>{e.description}</p></div><div className="timeline-state"><em>{e.status === 'applied' ? 'Aplicat' : e.status === 'ignored' ? 'Ignorat' : 'Pendent'}</em>{e.status==='applied'&&<button className="mini" onClick={()=>undo(e.id)} title="Desfer"><Undo2 size={14}/></button>}</div></div>) : <div className="empty"><Dices/><p>Encara no hi ha esdeveniments. El primer fet de la sessió apareixerà aquí.</p></div>}
      </section>
    </main>
    <aside className="context-panel" id="context"><span className="eyebrow">Context actual</span><h2>{data.location.name}</h2><p>{data.location.description}</p><span className="terrain-badge">{terrainNames[data.location.terrain]??data.location.terrain}</span><div className="metric warning"><CircleAlert/><div><span>Nivell de cerca</span><strong>{data.world_state.wanted_level ?? 0}</strong></div></div><div className="metric"><Shield/><div><span>Reputació del gremi</span><strong>{data.world_state['reputation:gremi_exploradors'] ?? 0}</strong></div></div><h3>Eines de sessió</h3><button className="quick enabled" onClick={()=>setPanel('library')}><Archive/>Biblioteca <span>{data.sources.length}</span></button><button className="quick enabled" onClick={()=>setPanel('encounter')}><Swords/>Generar encounter <span>{data.encounters.length}</span></button><button className="quick enabled" onClick={()=>setPanel('reward')}><Gift/>Generar recompensa <span>{data.rewards.length}</span></button><div id="rumors" className="rumor-summary"><h3>Rumors actius</h3>{data.rumors.slice(0,2).map(rumor=><div key={rumor.id}><MessageSquare/><p>{rumor.content}</p></div>)}{!data.rumors.length&&<p>Cap rumor actiu.</p>}</div><h3>Dades locals</h3><button className="quick enabled" onClick={createBackup}><Database/>Crear backup</button><button className="quick enabled" onClick={exportCampaign}><Download/>Exportar campanya</button>
    </aside>
    {selectedNpc && <NPCPanel npc={data.npcs.find(n => n.id === selectedNpc.id) ?? selectedNpc} close={() => setSelectedNpc(null)} changed={load}/>} 
    {creatingNpc&&<CreateNPC data={data} close={()=>setCreatingNpc(false)} done={()=>{setCreatingNpc(false);load();setNotice('NPC creat correctament.')}}/>}
    {searching&&<SearchPanel close={()=>setSearching(false)} openNpc={openNpcById}/>} 
    {panel==='library'&&<LibraryPanel data={data} close={()=>setPanel(null)} changed={()=>{load();setNotice('Document indexat correctament.')}}/>}
    {(panel==='encounter'||panel==='reward')&&<GeneratorPanel kind={panel} data={data} close={()=>setPanel(null)} done={()=>{load();setNotice(panel==='encounter'?'Encounter desat al timeline.':'Recompensa desada.')}}/>}
  </div>
}
