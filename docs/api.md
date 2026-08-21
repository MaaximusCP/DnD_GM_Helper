# API local 1.1

Base URL: `http://localhost:8000/api`. FastAPI publica l'especificació interactiva completa a `/docs`.

| Mètode | Ruta | Ús |
|---|---|---|
| `GET` | `/health` | Estat del backend i proveïdor LLM actiu |
| `GET` | `/campaigns` | Campanyes disponibles |
| `GET` | `/campaigns/{id}` | Dashboard agregat de la campanya |
| `POST` | `/campaigns` | Crea una campanya i la seva localització inicial |
| `GET` | `/campaign-templates` | Llista les plantilles locals disponibles |
| `POST` | `/campaign-templates/create` | Crea una campanya completa des d'una plantilla |
| `PATCH` | `/campaigns/{id}` | Edita nom, dia, regles o localització actual |
| `GET` | `/campaigns/{id}/export` | Exporta un paquet JSON portable |
| `POST` | `/campaigns/import` | Importa un paquet JSON; mai sobreescriu un ID existent |
| `POST` | `/campaigns/{id}/locations` | Crea una localització |
| `PATCH/DELETE` | `/locations/{id}` | Edita o elimina una localització no activa |
| `POST` | `/campaigns/{id}/factions` | Crea una facció |
| `PATCH/DELETE` | `/factions/{id}` | Edita o elimina una facció |
| `GET/PUT` | `/campaigns/{id}/party` | Consulta o configura nivell, mida i notes del grup |
| `PUT/DELETE` | `/campaigns/{id}/world-state/{key}` | Administra variables custom del món |
| `POST` | `/sessions?campaign_id=demo` | Comença una sessió |
| `GET` | `/sessions?campaign_id=demo` | Historial de sessions |
| `POST` | `/sessions/{id}/end` | Finalitza una sessió i en desa el resum |
| `GET` | `/npcs?campaign_id=demo` | Llista NPC |
| `POST` | `/npcs?campaign_id=demo` | Crea un NPC |
| `GET` | `/npcs/{id}` | Fitxa, relació i memòries d'un NPC |
| `PATCH` | `/npcs/{id}` | Edita un NPC i la relació |
| `DELETE` | `/npcs/{id}` | Elimina un NPC després de confirmació a la UI |
| `POST` | `/npcs/{id}/memories` | Afegeix una memòria manual |
| `POST` | `/npcs/{id}/chat` | Resposta contextual de l'NPC |
| `POST` | `/campaigns/{id}/npc-actions` | Genera accions de downtime pendents i pot avançar el calendari |
| `POST` | `/events/analyze` | Crea una proposta pendent |
| `PATCH` | `/events/{id}` | Edita una proposta pendent |
| `POST` | `/events/{id}/apply` | Aplica una proposta en transacció |
| `POST` | `/events/{id}/ignore` | Marca una proposta com ignorada |
| `POST` | `/events/{id}/undo` | Restaura els valors previs d'una proposta aplicada |
| `GET` | `/search?q=...` | Cerca global dins la campanya |
| `GET/POST` | `/backups` | Llista o crea backups consistents |
| `POST` | `/backups/{name}/restore` | Restaura només un backup validat del directori local |
| `GET` | `/settings` | Configuració pública no secreta |
| `GET` | `/library?campaign_id=demo` | Fonts locals de la campanya |
| `POST` | `/library/upload` | Carrega i indexa un document o mapa amb `multipart/form-data` |
| `GET` | `/library/search?q=...` | Cerca textual amb font i pàgina |
| `GET` | `/library/{id}/asset` | Obre el document o mapa des de la biblioteca local |
| `PATCH` | `/library/{id}` | Edita títol o visibilitat de la font |
| `GET` | `/library/{id}/chunks` | Consulta fragments paginats d'una font |
| `POST` | `/campaigns/{id}/library/lore` | Aprova un fragment i el converteix en lore amb procedència |
| `DELETE` | `/library/{id}?confirm=true` | Elimina metadades, fragments i fitxer local |
| `GET/POST` | `/npcs/{id}/knowledge` | Consulta o afegeix coneixement diferenciat |
| `GET/POST` | `/rumors` | Consulta o crea rumors |
| `POST` | `/rumors/{id}/propagate` | Propaga el rumor idempotentment als NPC |
| `GET/POST` | `/lore` | Consulta o crea informació separada per capa `dm`, `players` o `world` |
| `PATCH/DELETE` | `/lore/{id}` | Edita, mou de capa o elimina una entrada de coneixement |
| `GET/POST` | `/hexes` | Consulta o crea hexàgons de la campanya |
| `PATCH` | `/hexes/{id}` | Actualitza descobriment, viatge, encounter i notes de l'hex |
| `DELETE` | `/hexes/{id}?confirm=true` | Elimina un hex que no sigui la posició actual |
| `POST` | `/campaigns/{id}/hexes/reveal` | Revela o explora una zona per radi axial |
| `GET/PATCH` | `/campaigns/{id}/hexcrawl-settings` | Consulta o activa cada subsistema de l'hexcrawl |
| `GET/PATCH` | `/campaigns/{id}/expedition` | Estat de recursos, posició, clima, esgotament i diari |
| `POST` | `/campaigns/{id}/travel` | Resol una ruta amb ritme, regles actives i tirades opcionals |
| `POST` | `/campaigns/{id}/rest` | Resol descans curt o llarg, provisions, campament i esgotament |
| `GET/PATCH` | `/campaigns/{id}/player-view-settings` | Configura la informació compartida amb els jugadors |
| `GET` | `/player-view/{id}` | Projecció filtrada sense dades secretes del DM |
| `GET/POST` | `/combats` | Consulta o crea combats persistents |
| `PATCH` | `/combats/{id}` | Reanomena, finalitza o reobre un combat |
| `POST` | `/combats/{id}/combatants` | Afegeix un combatent amb estadístiques i accions |
| `POST` | `/combats/{id}/combatants/from-reference` | Crea un enemic amb CA, PG i accions del catàleg SRD |
| `PATCH/DELETE` | `/combatants/{id}` | Actualitza PG, condicions o dades del combatent, o l'elimina |
| `POST` | `/combats/{id}/next-turn` | Avança iniciativa i incrementa la ronda quan correspon |
| `POST` | `/combatants/{id}/duplicate` | Duplica un enemic o plantilla dins del combat |
| `POST` | `/combats/{id}/initiative` | Calcula iniciativa automàtica o aplica tirades manuals |
| `GET` | `/combats/{id}/log` | Historial persistent del combat |
| `POST` | `/combats/{id}/roll` | Resol una notació limitada com `2d6+3` i la registra |
| `GET` | `/campaigns/{id}/dice-rolls` | Consulta les darreres tirades de la campanya |
| `POST` | `/campaigns/{id}/dice-rolls` | Tira daus amb CD i mode normal, avantatge o desavantatge |
| `DELETE` | `/campaigns/{id}/dice-rolls?confirm=true` | Buida l'historial de tirades de la campanya |
| `GET/POST` | `/generation-tables` | Llista o crea taules homebrew |
| `PATCH/DELETE` | `/generation-tables/{id}` | Edita o elimina una taula i les entrades associades |
| `GET/POST` | `/generation-tables/{id}/entries` | Llista o afegeix opcions contextuals |
| `PUT/DELETE` | `/generation-entries/{id}` | Edita o elimina una opció custom |
| `GET` | `/encounters` | Historial d'encounters generats |
| `POST` | `/encounters/generate` | Genera i desa un encounter contextual |
| `POST` | `/encounters/{id}/combat` | Prepara un combat amb adversaris SRD a partir de l'encounter |
| `GET` | `/rewards` | Historial de recompenses |
| `POST` | `/rewards/generate` | Genera i desa una recompensa contextual |
| `POST` | `/rewards/{id}/claim` | Converteix una recompensa en inventari i tresoreria, una sola vegada |
| `GET/POST` | `/characters` | Llista o crea personatges jugadors persistents |
| `PATCH/DELETE` | `/characters/{id}` | Actualitza o elimina un personatge i reassigna el seu equip |
| `GET/POST` | `/inventory` | Llista o crea equip compartit, individual o vinculat a una ubicació |
| `PATCH/DELETE` | `/inventory/{id}` | Transfereix, edita o elimina un objecte |
| `POST` | `/inventory/{id}/consume` | Consumeix una quantitat i registra el moviment |
| `GET/PATCH` | `/campaigns/{id}/treasury` | Consulta o fixa la tresoreria multimoneda |
| `POST` | `/campaigns/{id}/treasury/adjust` | Registra un ingrés o una despesa auditada |
| `GET` | `/campaigns/{id}/inventory-transactions` | Historial d'inventari i tresoreria |
| `POST` | `/combats/{id}/characters` | Afegeix personatges al combat amb PG i condicions sincronitzats |
| `GET/POST` | `/campaign-records` | Llista o crea missions, calendari, clocks, escenes, mapes, marcadors i vincles |
| `PATCH/DELETE` | `/campaign-records/{id}` | Actualitza estat, visibilitat i dades d'un element d'operacions |
| `POST` | `/campaign-records/{id}/duplicate` | Duplica missions, escenes, clocks, mapes o altres plantilles |
| `GET/POST` | `/campaigns/{id}/activities` | Cronologia automàtica i notes de sessió |
| `POST` | `/sessions/{id}/close` | Tanca la sessió i genera un resum a partir de l'activitat |
| `POST` | `/encounters/{id}/resolve` | Resol l'encounter i aplica XP, missió, clock i recompensa |
| `GET` | `/library/{id}/asset` | Serveix localment una imatge o document de la biblioteca |
| `GET` | `/reference/meta` | Versió, llicència i recompte del catàleg SRD local |
| `GET` | `/reference?category=...&q=...` | Cerca paginada al catàleg SRD |
| `GET` | `/reference/item/{id}` | Fitxa estructurada completa d'una entrada SRD |

Exemple per analitzar un fet:

```json
{
  "campaign_id": "demo",
  "npc_id": "kara",
  "description": "El grup ha ajudat la Kara a recuperar la mercaderia."
}
```

Els paràmetres d'aquest exemple van al **cos JSON**. L'identificador d'una proposta va al **path** en aplicar-la o ignorar-la.

La càrrega documental utilitza `multipart/form-data`: `file` conté el fitxer; `campaign_id`, `title`, `source_type` i `visibility` són camps de formulari. No s'envia cap document al cos JSON.

La restauració és deliberadament explícita: el nom del backup va al **path** i la confirmació va al **cos JSON**. Abans de restaurar, el sistema genera automàticament un backup de seguretat de l'estat actual.

```json
{
  "confirm": "RESTORE"
}
```
