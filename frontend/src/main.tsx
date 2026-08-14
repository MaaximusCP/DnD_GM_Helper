import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { PlayerScreenApp } from './CampaignTools'
import './styles.css'

const playerCampaign=new URLSearchParams(window.location.search).get('player')
createRoot(document.getElementById('root')!).render(<StrictMode>{playerCampaign?<PlayerScreenApp campaignId={playerCampaign}/>:<App/>}</StrictMode>)
