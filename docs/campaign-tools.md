# Coneixement, hexcrawl i assistent de combat

## Tres capes d'informació

Les entrades de `lore_entries` tenen una capa obligatòria:

- `dm`: secrets, solucions, trampes i informació encara no revelada;
- `players`: informació que els jugadors ja poden consultar;
- `world`: estat objectiu del món, independentment de qui el conegui.

Moure una entrada entre capes és una decisió explícita del DM. Els camps `source_id` i `location_id` permeten conservar-ne la procedència documental i geogràfica. Aquesta separació complementa el coneixement subjectiu de cada NPC, que continua a `knowledge` amb confiança i estat de veritat propis.

## Hexcrawl

Cada hex desa coordenades axials `q,r`, terreny, estat de descobriment, cost de viatge, probabilitat d'encounter i dues notes separades:

- `player_notes`, visibles quan el DM decideixi compartir la informació;
- `dm_notes`, sempre reservades.

`source_id` permet vincular l'hex a un mapa o document carregat a la biblioteca. El projecte no distribueix el mapa comercial de Chult: l'usuari pot pujar localment una còpia que tingui dret a utilitzar. L'export conserva els hexàgons i els vincles, però no el fitxer original.

Cada campanya pot activar o desactivar independentment clima, navegació, menjar, aigua, fatiga, encounters, foratge i descobriment automàtic. Un viatge calcula una ruta contínua per coordenades axials, aplica el ritme, accepta tirades manuals o automàtiques, actualitza recursos i dia de campanya, revela el trajecte i pot generar un encounter contextual. Tots els resultats queden al diari de viatge.

Desactivar un subsistema no elimina les seves dades: simplement deixa d'aplicar-ne tirades, consum i penalitzacions. Això permet passar de supervivència completa a exploració narrativa en qualsevol moment.

## Pantalla dels jugadors

`GET /player-view/{campaign_id}` construeix una projecció segura amb només lore `players`, hexàgons descoberts, notes públiques, rumors permesos, recursos configurats i combat sanititzat. Els PG enemics són opcionals i les accions enemigues no s'exposen. Si la pantalla està desactivada, l'endpoint retorna `403`.

La URL del navegador és `?player=<campaign_id>` i s'actualitza automàticament. Aquesta separació evita filtracions accidentals en el payload, però no substitueix autenticació quan l'aplicació s'exposi a Internet.

## Assistent de combat

Un combat persistent conté ronda, índex del torn i combatents ordenats per iniciativa. Cada combatent desa:

- tipus, iniciativa, CA, PG màxims i actuals;
- condicions;
- accions estructurades;
- `reference_id` per al catàleg SRD i `source_id` per a documents locals.
- PG temporals, bonus d'iniciativa, concentració i disponibilitat de reacció;
- reserva d'accions llegendàries i notes operatives.

La interfície permet aplicar dany o curació, avançar el torn, consultar accions i afegir combatents manuals. Les dades de mostra demostren accions manuals i una referència SRD. Una ampliació posterior podrà crear combatents des d'un fragment documental revisat pel DM sense canviar l'esquema.

L'API ja permet crear un combatent complet des d'un monstre del catàleg local mitjançant `POST /combats/{id}/combatants/from-reference`. Aquest primer adaptador carrega nom, CA, PG i accions; és el patró de referència per al futur adaptador documental.

La UI permet cercar monstres SRD, afegir-ne múltiples còpies, duplicar combatents, tirar iniciativa, modificar l'ordre, aplicar condicions, gestionar concentració/reaccions, fer tirades amb notació de daus i conservar un historial del combat. Els combats poden quedar vinculats a l'encounter que els ha originat.

## Flux futur des de documents

La importació automàtica s'ha de mantenir darrere del límit d'aprovació del DM:

1. cercar fragments rellevants a la biblioteca local;
2. proposar una entrada de lore, un hex o un bloc de combat;
3. mostrar text, pàgina i `source_id` d'origen;
4. permetre editar la proposta;
5. persistir-la només després de l'aprovació explícita.

Això evita convertir una extracció imperfecta del PDF en estat canònic de la campanya.
