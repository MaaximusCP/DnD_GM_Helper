import { useEffect, useState } from 'react'
import { BookOpen, Check, Dices, History, ShieldCheck, Trash2, X } from 'lucide-react'
import { api } from './api'
import type { Dashboard, DiceRoll, ReferenceItem } from './types'

type RollMode = DiceRoll['mode']

const modeLabels:Record<RollMode,string>={normal:'Normal',advantage:'Avantatge',disadvantage:'Desavantatge'}

export function SessionToolkit({data}:{data:Dashboard}){
  const [notation,setNotation]=useState('1d20')
  const [label,setLabel]=useState('Tirada del DM')
  const [actor,setActor]=useState('')
  const [mode,setMode]=useState<RollMode>('normal')
  const [dc,setDc]=useState('')
  const [history,setHistory]=useState<DiceRoll[]>([])
  const [result,setResult]=useState<DiceRoll|null>(null)
  const [conditions,setConditions]=useState<ReferenceItem[]>([])
  const [selectedCondition,setSelectedCondition]=useState<ReferenceItem|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')

  useEffect(()=>{void api.diceRolls(data.campaign.id).then(setHistory);void api.reference('','conditions').then(response=>{setConditions(response.items);setSelectedCondition(response.items[0]??null)})},[data.campaign.id])

  const execute=async(nextNotation=notation,nextMode=mode)=>{
    setBusy(true);setError('')
    try{
      const item=await api.rollDice(data.campaign.id,{notation:nextNotation,label,actor,mode:nextMode,...(dc?{dc:Number(dc)}:{})})
      setResult(item);setNotation(nextNotation);setMode(nextMode);setHistory(previous=>[item,...previous].slice(0,50))
    }catch(exception){setError(exception instanceof Error?exception.message:'No s’ha pogut fer la tirada')}finally{setBusy(false)}
  }
  const clear=async()=>{if(!confirm('Buidar tot l’historial de tirades d’aquesta campanya?'))return;await api.clearDiceRolls(data.campaign.id);setHistory([]);setResult(null)}
  const description=selectedCondition?.data.desc
  const conditionLines=Array.isArray(description)?description.map(String):description?[String(description)]:[]

  return <div className="studio-page session-toolkit">
    <div className="studio-heading"><div><span className="eyebrow">Utilitats de taula</span><h1>Safata de daus i regles ràpides</h1><p>Tirades persistents, CD, avantatge i condicions SRD disponibles sense connexió.</p></div><Dices/></div>
    <div className="dice-layout">
      <section className="studio-card dice-tray">
        <div className="dice-quick">{[4,6,8,10,12,20,100].map(sides=><button key={sides} onClick={()=>void execute(`1d${sides}`,sides===20?mode:'normal')}><span>d{sides}</span></button>)}</div>
        <div className="dice-fields"><label>Notació<input value={notation} onChange={event=>setNotation(event.target.value)} onKeyDown={event=>{if(event.key==='Enter')void execute()}} placeholder="2d6+3"/></label><label>Etiqueta<input value={label} onChange={event=>setLabel(event.target.value)} placeholder="Percepció, dany..."/></label><label>Personatge o origen<input value={actor} onChange={event=>setActor(event.target.value)} placeholder="Opcional"/></label><label>CD<input type="number" min="1" max="40" value={dc} onChange={event=>setDc(event.target.value)} placeholder="Sense CD"/></label></div>
        <div className="roll-modes">{(Object.keys(modeLabels) as RollMode[]).map(item=><button className={mode===item?'active':''} key={item} onClick={()=>{setMode(item);if(item!=='normal')setNotation('1d20')}}>{modeLabels[item]}</button>)}</div>
        <button className="primary roll-main" disabled={busy} onClick={()=>void execute()}><Dices/>{busy?'Tirant…':'Tirar els daus'}</button>
        {error&&<div className="alert dismissible" onClick={()=>setError('')}>{error}<X/></div>}
        {result&&<article className={`roll-result ${result.success===true?'success':result.success===false?'failure':''}`}><div><span>{result.actor||'DM'} · {result.label}</span><strong>{result.total}</strong><small>{result.notation} · {modeLabels[result.mode]}{result.modifier?` · ${result.modifier>0?'+':''}${result.modifier}`:''}</small></div><div className="rolled-dice">{result.dice.map((die,index)=><i key={`${die}-${index}`}>{die}</i>)}<span>Conservat: {result.kept.join(', ')}</span></div>{result.dc!=null&&<div className="roll-verdict">{result.success?<Check/>:<X/>}<span><b>{result.success?'Èxit':'Fallada'}</b>CD {result.dc}</span></div>}{result.critical&&<em className={`critical ${result.critical}`}>{result.critical==='success'?'20 natural':'1 natural'}</em>}</article>}
        <details className="dice-history" open><summary><History/> Historial de la campanya <b>{history.length}</b></summary><div className="history-head"><span>Les darreres 50 tirades queden desades a SQLite.</span>{history.length>0&&<button className="danger" onClick={()=>void clear()}><Trash2/> Buidar</button>}</div>{history.map(item=><article key={item.id}><strong>{item.total}</strong><span><b>{item.label}</b><small>{item.actor||'DM'} · {item.notation} · {modeLabels[item.mode]}{item.dc?` · CD ${item.dc}`:''}</small></span>{item.success!=null&&<em className={item.success?'success':'failure'}>{item.success?'Èxit':'Fallada'}</em>}<time>{new Date(item.created_at).toLocaleTimeString('ca-ES',{hour:'2-digit',minute:'2-digit'})}</time></article>)}{!history.length&&<p className="empty-search">Encara no hi ha cap tirada desada.</p>}</details>
      </section>
      <aside className="studio-card conditions-reference"><div className="conditions-title"><ShieldCheck/><div><span className="eyebrow">SRD 5.1</span><h2>Condicions</h2></div></div><div className="condition-pills">{conditions.map(item=><button className={selectedCondition?.id===item.id?'active':''} key={item.id} onClick={()=>setSelectedCondition(item)}>{item.name}</button>)}</div>{selectedCondition&&<article><span>Condició de regles</span><h3>{selectedCondition.name}</h3>{conditionLines.map((line,index)=><p key={index}>{line}</p>)}<small><BookOpen/> {selectedCondition.source} · CC-BY-4.0</small></article>}</aside>
    </div>
  </div>
}
