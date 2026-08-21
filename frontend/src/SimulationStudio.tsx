import { useMemo, useState } from 'react'
import { Bot, CalendarClock, Check, Pause, Play, Save, Sparkles, X } from 'lucide-react'
import { api } from './api'
import type { Dashboard, EventProposal, NPCActionResult } from './types'

function ActionProposal({event,done}:{event:EventProposal;done:()=>void}){
  const [draft,setDraft]=useState(event);const [busy,setBusy]=useState(false)
  const save=async()=>{setBusy(true);try{setDraft(await api.updateEvent(event.id,{title:draft.title,severity:draft.severity}))}finally{setBusy(false)}}
  const resolve=async(action:'apply'|'ignore')=>{setBusy(true);try{if(action==='apply')await api.applyEvent(event.id);else await api.ignoreEvent(event.id);done()}finally{setBusy(false)}}
  return <article className="downtime-proposal">
    <header><span>Proposta pendent</span><em>Severitat {draft.severity}/10</em></header>
    <input className="title-input" value={draft.title} onChange={e=>setDraft({...draft,title:e.target.value})}/>
    <p>{draft.description}</p>
    <label><span>Impacte</span><input type="range" min="1" max="10" value={draft.severity} onChange={e=>setDraft({...draft,severity:Number(e.target.value)})}/></label>
    <small>{draft.consequences.map(item=>item.text||`${item.field} ${item.delta}`).join(' · ')}</small>
    <footer><button disabled={busy} onClick={()=>void resolve('ignore')}><X size={14}/> Ignorar</button><button disabled={busy} onClick={()=>void save()}><Save size={14}/> Desar</button><button className="primary" disabled={busy} onClick={()=>void resolve('apply')}><Check size={14}/> Aplicar</button></footer>
  </article>
}

export function SimulationStudio({data,changed}:{data:Dashboard;changed:()=>void}){
  const activeIds=useMemo(()=>data.npcs.filter(npc=>npc.active).map(npc=>npc.id),[data.npcs])
  const [selected,setSelected]=useState<string[]>(activeIds);const [days,setDays]=useState(1);const [advance,setAdvance]=useState(true)
  const [result,setResult]=useState<NPCActionResult|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('')
  const toggleNpc=async(id:string,active:boolean)=>{await api.updateNpc(id,{active});setSelected(items=>active?[...new Set([...items,id])]:items.filter(item=>item!==id));changed()}
  const setAutonomy=async(id:string,autonomy:number)=>{await api.updateNpc(id,{autonomy});changed()}
  const generate=async()=>{setBusy(true);setError('');try{const value=await api.generateNpcActions(data.campaign.id,{days,npc_ids:selected,advance_calendar:advance});setResult(value);changed()}catch(e){setError(e instanceof Error?e.message:'No s’han pogut generar les accions')}finally{setBusy(false)}}
  const pending=(result?.proposals??[]).filter(item=>item.status==='pending')
  return <div className="studio-page simulation-studio">
    <div className="studio-heading"><div><span className="eyebrow">Motor local entre sessions</span><h1>NPCs actius</h1><p>Avança les seves agendes en forma de propostes. Res modifica el món fins que ho aprovis.</p></div><Bot/></div>
    <div className="simulation-layout"><section className="studio-card"><div className="section-head"><div><h2>Qui pot actuar?</h2><p>{activeIds.length} NPC actius de {data.npcs.length}</p></div></div>
      <div className="active-npc-list">{data.npcs.map(npc=><article className={npc.active?'enabled':''} key={npc.id}><button className="npc-active-toggle" title={npc.active?'Fer passiu':'Fer actiu'} onClick={()=>void toggleNpc(npc.id,!npc.active)}>{npc.active?<Play size={14}/>:<Pause size={14}/>}</button><button className="npc-action-choice" disabled={!npc.active} onClick={()=>setSelected(items=>items.includes(npc.id)?items.filter(id=>id!==npc.id):[...items,npc.id])}><i className={selected.includes(npc.id)&&npc.active?'selected':''}/><span><strong>{npc.name}</strong><small>{npc.goals[0]||'Sense objectiu definit'}</small></span></button><label>Autonomia<select value={npc.autonomy} disabled={!npc.active} onChange={e=>void setAutonomy(npc.id,Number(e.target.value))}><option value="0">Pausa</option><option value="1">Baixa</option><option value="2">Mitjana</option><option value="3">Alta</option></select></label></article>)}</div>
    </section><aside className="studio-card simulation-control"><CalendarClock/><h2>Avanç de temps</h2><label className="range-label"><span>Període <b>{days} {days===1?'dia':'dies'}</b></span><input type="range" min="1" max="30" value={days} onChange={e=>setDays(Number(e.target.value))}/><div><small>1 dia</small><small>30 dies</small></div></label><label className="toggle-inline"><input type="checkbox" checked={advance} onChange={e=>setAdvance(e.target.checked)}/> Avançar també el calendari</label><p>Es crearà com a màxim una proposta per NPC seleccionat. Les conseqüències quedaran pendents.</p><button className="primary full" disabled={busy||selected.length===0} onClick={()=>void generate()}><Sparkles size={15}/>{busy?'Calculant agendes…':`Proposar accions (${selected.length})`}</button>{error&&<div className="alert">{error}</div>}{result&&<div className="simulation-result"><strong>Dia {result.previous_day} → {result.current_day}</strong><span>{result.proposals.length} propostes · {result.skipped.length} omesos</span></div>}</aside></div>
    {result&&<section><div className="section-head"><div><h2>Revisió del DM</h2><p>Edita, aplica o ignora cada proposta individualment.</p></div></div><div className="downtime-grid">{pending.map(event=><ActionProposal event={event} key={event.id} done={()=>{setResult({...result,proposals:result.proposals.filter(item=>item.id!==event.id)});changed()}}/>)}{pending.length===0&&<div className="empty"><Check/><p>No queden propostes d’aquest avanç de temps.</p></div>}</div>{result.skipped.length>0&&<details className="studio-card skipped-actions"><summary>NPC omesos ({result.skipped.length})</summary>{result.skipped.map(item=><p key={item}>{item}</p>)}</details>}</section>}
  </div>
}
