# API local 0.3

Base URL: `http://localhost:8000/api`. FastAPI publica l'especificació interactiva completa a `/docs`.

| Mètode | Ruta | Ús |
|---|---|---|
| `GET` | `/health` | Estat del backend i proveïdor LLM actiu |
| `GET` | `/campaigns` | Campanyes disponibles |
| `GET` | `/campaigns/{id}` | Dashboard agregat de la campanya |
| `POST` | `/campaigns` | Crea una campanya i la seva localització inicial |
| `PATCH` | `/campaigns/{id}` | Edita nom, dia, regles o localització actual |
| `GET` | `/campaigns/{id}/export` | Exporta un paquet JSON portable |
| `POST` | `/campaigns/import` | Importa un paquet JSON; mai sobreescriu un ID existent |
| `POST` | `/campaigns/{id}/locations` | Crea una localització |
| `POST` | `/campaigns/{id}/factions` | Crea una facció |
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
| `DELETE` | `/library/{id}?confirm=true` | Elimina metadades, fragments i fitxer local |
| `GET/POST` | `/npcs/{id}/knowledge` | Consulta o afegeix coneixement diferenciat |
| `GET/POST` | `/rumors` | Consulta o crea rumors |
| `POST` | `/rumors/{id}/propagate` | Propaga el rumor idempotentment als NPC |
| `GET/POST` | `/generation-tables` | Llista o crea taules homebrew |
| `GET/POST` | `/generation-tables/{id}/entries` | Llista o afegeix opcions contextuals |
| `PUT/DELETE` | `/generation-entries/{id}` | Edita o elimina una opció custom |
| `GET` | `/encounters` | Historial d'encounters generats |
| `POST` | `/encounters/generate` | Genera i desa un encounter contextual |
| `GET` | `/rewards` | Historial de recompenses |
| `POST` | `/rewards/generate` | Genera i desa una recompensa contextual |

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
