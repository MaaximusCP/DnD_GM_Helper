# Projecte: Motor d'IA per a campanyes de D&D 5e

> **Estat:** document de disseny inicial  
> **Arquitectura recomanada per a l'MVP:** web local + FastAPI + SQLite + Ollama/LM Studio  
> **Cloud:** Azure opcional en fases posteriors  
> **Plataforma:** aplicació independent, sense dependència de VTT extern  
> **Campanya inicial:** Tomb of Annihilation; motor reutilitzable per altres campanyes D&D 5e  
> **Última actualització:** 7 d'agost de 2026

## Índex resumit

1. Visió general, objectius i principis
2. Arquitectura general i separació de capes
3. Campanyes modulars i estat del món
4. Esdeveniments, NPCs, memòria i relacions
5. Coneixement, rumors, reputació i faccions
6. Context dels agents i mecàniques D&D 5e
7. Game Master Agent i NPCs actius/passius
8. Encounter Engine
9. Reward Engine: mode neutral i mode amb tirada
10. Sessions, persistència i model de dades
11. Models locals i abstracció del proveïdor LLM
12. Interfície del DM i experiència d'ús
13. Arquitectura local-first i stack inicial
14. Azure com a extensió opcional
15. Desplegament, sincronització i backups
16. Perfil de regles configurable
17. Fluxos principals de sessió
18. Roadmap i MVP
19. Estructura de projecte proposada
20. Visió a llarg termini i següents passos

---

## 1. Visió general

L'objectiu del projecte és crear una eina modular per a **Dungeons & Dragons 5e** que ajudi el Dungeon Master a gestionar un món més reactiu i persistent mitjançant agents d'IA.

La primera campanya on s'utilitzaria seria **Tomb of Annihilation**, però l'arquitectura s'ha de dissenyar des del principi perquè la campanya sigui només una capa de dades substituïble. En el futur s'ha de poder carregar una altra aventura publicada, una campanya pròpia o un món completament homebrew sense haver de reescriure el motor.

El sistema no pretén substituir el DM ni delegar totes les regles a una IA. La idea és separar clarament:

- **Regles, estat del món i dades persistents**, controlades pel programa i pel DM.
- **Interpretació, diàleg, personalitat i propostes narratives**, gestionades pel model de llenguatge.

Això permet que el món recordi les accions dels jugadors i que els NPC reaccionin de manera coherent sense perdre el control mecànic de la partida.

---

## 2. Objectius principals

El projecte hauria de permetre:

- Crear NPCs amb personalitat, objectius, valors, límits i motivacions pròpies.
- Mantenir relacions persistents entre NPCs, jugadors, faccions i altres entitats.
- Fer que els NPC recordin interaccions significatives.
- Separar el que és cert al món del que cada NPC creu o coneix.
- Gestionar reputació per localització, facció i grup social.
- Propagar rumors i notícies de manera gradual.
- Fer que els esdeveniments de la partida tinguin conseqüències persistents.
- Permetre diàlegs contextuals amb NPCs mitjançant un LLM.
- Permetre que alguns NPCs importants actuïn entre sessions.
- Registrar i resumir sessions de campanya.
- Generar encounters contextuals.
- Generar recompenses coherents amb el lloc, els enemics, la dificultat i la situació narrativa.
- Oferir un mode de recompenses neutre i un mode opcional basat en tirades de fortuna/risc.
- Poder substituir la campanya activa sense modificar el motor principal.
- Poder funcionar gratuïtament o amb un cost molt baix utilitzant models locals.
- Oferir una interfície pròpia, senzilla i usable en directe pel DM.
- Funcionar sense dependre de cap VTT extern.
- Permetre una arquitectura local-first amb Azure com a extensió opcional.

---

# 3. Principis de disseny

## 3.1. La campanya és contingut, no motor

El motor no ha de tenir lògica específica de Tomb of Annihilation.

```text
AI RPG ENGINE
│
├── D&D 5e rules / adapters
├── NPC engine
├── memory engine
├── event engine
├── knowledge engine
├── rumor engine
├── reputation engine
├── faction engine
├── encounter engine
├── reward engine
│
└── campaigns/
     ├── tomb_of_annihilation/
     ├── future_campaign/
     └── homebrew_campaign/
```

Tomb of Annihilation seria la primera campanya carregada, però totes les dades específiques haurien d'estar fora del codi central.

---

## 3.2. El programa conserva la veritat; la IA la interpreta

La base de dades és la **font de veritat**.

Si els personatges són buscats en una ciutat, aquesta condició existeix a les dades independentment de què digui el model.

```text
WORLD STATE
    ↓
Regles / modificadors
    ↓
Context seleccionat
    ↓
LLM
    ↓
Diàleg, descripció o proposta d'acció
```

El model no hauria de poder modificar lliurement l'estat del món sense passar pel sistema o per l'aprovació del DM.

---

## 3.3. Context rellevant, no tota la campanya

No s'ha d'enviar tot l'historial de la campanya al model cada vegada.

Quan un NPC interactua amb els jugadors, el sistema selecciona únicament:

- personalitat;
- objectius actuals;
- relació amb els interlocutors;
- memòries rellevants;
- rumors coneguts;
- reputació aplicable;
- esdeveniments recents relacionats;
- estat actual de la localització;
- situació immediata.

Això redueix tokens, millora la coherència i facilita utilitzar models locals petits.

## 3.4. Eina independent i local-first

El projecte serà una **aplicació pròpia i independent** i no dependrà de cap VTT extern per funcionar.

La prioritat és que el DM pugui obrir l'eina, carregar la seva campanya i utilitzar-la durant una sessió encara que no tingui connexió a Internet.

Principis:

- la funcionalitat principal ha de funcionar en local;
- el model d'IA local ha de ser una opció de primera classe;
- la base de dades local ha de continuar sent usable sense Azure;
- els serveis cloud han de ser opcionals i afegir sincronització, backup o accés remot, no ser una dependència del joc;
- la UI no ha de mostrar complexitat tècnica innecessària al DM.

## 3.5. Separar UI, motor i infraestructura

La interfície no ha de contenir la lògica de campanya, i el motor no ha de dependre de SQLite, Cosmos DB, Ollama o cap proveïdor concret.

```text
DM INTERFACE
     │
     ▼
APPLICATION SERVICES
     │
     ▼
CAMPAIGN ENGINE
     │
     ├── NPC / Memory / Events
     ├── Knowledge / Rumors / Reputation
     ├── Encounters / Rewards
     └── Rules adapter
     │
     ▼
INFRASTRUCTURE ADAPTERS
     ├── SQLite
     ├── Cosmos DB (futur)
     ├── Ollama / LM Studio
     └── altres proveïdors futurs
```

Aquesta separació permet canviar la tecnologia sense reescriure les regles del projecte.

---

# 4. Arquitectura general

```text
                         ┌──────────────────┐
                         │        DM        │
                         │ input / control  │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  EVENT MANAGER   │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        WORLD STATE          REPUTATION          KNOWLEDGE
                                                   / RUMORS
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ CONTEXT BUILDER  │
                         └────────┬─────────┘
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
               NPC AGENTS                GM AGENT
                     │                         │
                     └────────────┬────────────┘
                                  ▼
                                LLM
                                  │
              ┌───────────────────┼────────────────────┐
              ▼                   ▼                    ▼
           DIÀLEG              ACCIONS             PROPOSTES
                                                    DE CANVI
```

En el futur s'hi afegirien dos motors més:

```text
ENCOUNTER ENGINE ───────► encounter contextual
REWARD ENGINE ──────────► recompensa contextual
```

---

# 5. Campanyes modulars

Una campanya podria tenir una estructura semblant a:

```text
campaigns/
└── tomb_of_annihilation/
    ├── campaign.json
    ├── locations/
    ├── factions/
    ├── npcs/
    ├── quests/
    ├── encounters/
    ├── rumors/
    ├── discoveries/
    └── campaign_state/
```

Manifest simplificat:

```json
{
  "id": "toa",
  "name": "Tomb of Annihilation",
  "system": "dnd5e",
  "modules": {
    "rumors": true,
    "factions": true,
    "travel": true,
    "reputation": true,
    "encounters": true,
    "rewards": true
  }
}
```

Una futura campanya podria utilitzar exactament el mateix motor:

```json
{
  "id": "campaign_02",
  "name": "Nova campanya",
  "system": "dnd5e"
}
```

---

# 6. Estat del món

El `World State` conté les condicions actuals i persistents.

Exemple conceptual:

```json
{
  "current_day": 37,
  "current_location": "city_01",
  "active_events": [],
  "global_conditions": [],
  "party": {
    "reputation": {},
    "wanted_status": {}
  }
}
```

Exemple d'una conseqüència activa:

```json
{
  "wanted_status": {
    "city_01": 3
  }
}
```

Aquesta dada no depèn del que recordi un NPC concret.

---

# 7. Sistema d'esdeveniments

Cada fet important de la partida es converteix en un `Event`.

Exemple:

```json
{
  "id": "event_0042",
  "type": "crime",
  "location": "city_01",
  "actors": ["party"],
  "targets": ["merchant_01"],
  "severity": 6,
  "visibility": "public",
  "witnesses": ["guard_04", "merchant_07"],
  "timestamp": "day_37"
}
```

El DM podria introduir una frase natural:

> Els jugadors han robat un comerciant al mercat. Dos guàrdies els han vist fugir.

El Game Master Agent podria proposar:

```text
Crear: CrimeEvent
Reputació comerciants: -15
Reputació guàrdies: -25
Wanted level: +1
Crear rumor públic: sí
Crear memòria als testimonis: sí
```

Inicialment és preferible que el DM pugui:

- acceptar;
- modificar;
- ignorar.

---

# 8. NPCs

Cada NPC ha de ser una entitat persistent independent del model d'IA.

Exemple simplificat:

```json
{
  "id": "npc_014",
  "name": "Kara",
  "location": "city_01",
  "personality": {
    "traits": [
      "pragmatic",
      "suspicious",
      "ambitious"
    ]
  },
  "goals": [
    "protect her business",
    "gain political influence"
  ],
  "values": [
    "wealth",
    "loyalty"
  ]
}
```

## 8.1. Personalitat

Els NPC poden tenir variables qualitatives o quantitatives com:

- amabilitat;
- ambició;
- impulsivitat;
- prudència;
- honestedat;
- lleialtat;
- cobdícia;
- tolerància al risc;
- predisposició a la violència;
- sentit de l'humor;
- espiritualitat;
- romanticisme;
- sociabilitat;
- inseguretats;
- prejudicis o preferències culturals coherents amb el món;
- límits personals;
- secrets.

No totes han de ser numèriques. Una combinació de descriptors i alguns valors funciona millor.

---

## 8.2. Relacions

Un NPC pot mantenir relacions independents amb individus, grups i faccions.

```json
{
  "relationships": {
    "party": {
      "trust": 25,
      "affection": 10,
      "fear": 5,
      "respect": 35,
      "attraction": 0
    }
  }
}
```

Aquests valors poden evolucionar amb les accions dels jugadors.

No cal que totes les dimensions apareguin per a tots els NPCs.

---

# 9. Memòria

La memòria no hauria de ser un log infinit de converses.

Es proposen tres nivells.

## 9.1. Memòria recent

Esdeveniments recents que poden desaparèixer o resumir-se amb el temps.

```text
Fa dos dies els aventurers van discutir amb ella pel preu.
```

## 9.2. Memòria important

Fets amb alta càrrega emocional o narrativa.

```text
Els aventurers li van salvar la vida.
```

## 9.3. Resum de relació

Resum compacte generat periòdicament.

```text
Considera el grup poc fiable, però els respecta perquè han complert dues promeses importants.
```

Aquesta estructura evita enviar centenars de missatges antics al model.

---

# 10. Realitat, coneixement i creences

Una de les peces centrals del projecte és separar:

```text
REALITAT DEL MÓN
        ≠
CONEIXEMENT DE L'NPC
        ≠
CREENÇA DE L'NPC
```

Exemple:

```text
REALITAT
Els aventurers van robar un artefacte.
No van matar ningú.
```

Però circula un rumor:

```text
"Els aventurers van matar el propietari i van robar l'artefacte."
```

Un NPC podria tenir:

```json
{
  "belief": "The adventurers are murderers",
  "confidence": 0.65,
  "source": "rumor_21"
}
```

Això permet que els NPC s'equivoquin de manera coherent.

---

# 11. Rumors i propagació d'informació

Un rumor podria tenir:

```json
{
  "id": "rumor_21",
  "origin": "city_01",
  "subject": "party",
  "credibility": 0.7,
  "spread": 0.4,
  "factions": [
    "merchants",
    "city_guards"
  ]
}
```

La propagació no necessita simular cada habitant individualment.

Es pot gestionar per grups:

```text
Dia 1

Guàrdies       100%
Comerciants     80%
Habitants       40%
Viatgers        10%

Dia 4

Guàrdies       100%
Comerciants     90%
Habitants       70%
Viatgers        30%
```

Els rumors també podrien degradar-se, exagerar-se o mutar a mesura que viatgen.

---

# 12. Reputació

No hauria d'existir una única reputació global.

Millor separar per:

- regió;
- ciutat;
- facció;
- professió;
- grup social;
- individu.

Exemple:

```text
Party reputation

City 01
    població            +10
    comerciants         -35
    criminals           +20
    guards              -60

City 02
    població              0
    comerciants           0
    guards                0
```

Això evita que un delicte local converteixi automàticament el grup en criminal conegut arreu del món.

---

# 13. Faccions

Les faccions poden tenir:

- objectius;
- recursos;
- territori o influència;
- enemics i aliats;
- reputació envers el grup;
- coneixement compartit;
- secrets;
- NPCs membres;
- agenda activa.

Exemple:

```json
{
  "id": "faction_01",
  "relations": {
    "party": -20
  },
  "knowledge": [
    "event_14",
    "event_21"
  ],
  "priorities": [
    "protect_trade",
    "increase_influence"
  ]
}
```

Un NPC membre pot combinar:

```text
Memòria personal
+
Coneixement de facció
+
Rumors locals
+
Informació pública
```

---

# 14. Construcció del context d'un NPC

Quan un jugador parla amb un NPC, el `Context Builder` prepara només la informació rellevant.

Exemple conceptual:

```text
CHARACTER
Kara

PERSONALITY
Pragmatic, suspicious and ambitious.

CURRENT GOAL
Discover why the party is asking about the merchant guild.

RELATIONSHIP WITH PARTY
Trust: 25
Respect: 35
Fear: 5

CURRENT LOCATION
City 01

RELEVANT WORLD STATE
The city guard is searching for the party.

NPC KNOWLEDGE
You have seen wanted posters matching some party members.

MEMORIES
The party helped one of your employees last week.

CURRENT SITUATION
Three members of the party enter your shop.
```

El model rep aquest context i interpreta el personatge.

---

# 15. D&D 5e i mecàniques

La IA no hauria de decidir arbitràriament les regles.

Exemple:

```text
NPC intenta detectar una mentida
        ↓
Sistema / DM determina que correspon Insight
        ↓
Tirada o comprovació
        ↓
Resultat
        ↓
LLM narra la reacció
```

També es poden calcular dificultats contextuals.

```text
Base DC                  12
Wanted by guards         +4
Saved her employee       -2
Good personal relation   -1
---------------------------
Final DC                 13
```

Aquest tipus de càlcul és més fiable si el fa el motor i no el model.

---

# 16. Game Master Agent

A més dels NPCs, hi hauria un agent especial que no interpreta cap personatge.

La seva funció seria analitzar els esdeveniments introduïts pel DM i proposar canvis estructurats.

Exemple:

```text
INPUT DEL DM

Els jugadors provoquen una baralla al mercat, fereixen un guàrdia i fugen.
```

Proposta:

```text
Crear event: Assault on city guard

Possible consequences:
- wanted_level +2
- guard_reputation -30
- public_reputation -10

Create rumor:
"They attacked the city guard."

Possible witnesses:
12

Propagation:
high
```

En les primeres versions, el DM valida el resultat abans d'aplicar-lo.

---

# 17. NPCs actius i passius

No té sentit que tots els NPCs facin inferència constantment.

## NPC passiu

La majoria del món.

Només utilitza IA quan:

- parla amb els jugadors;
- és afectat per un esdeveniment;
- cal actualitzar una memòria important.

## NPC actiu

Personatges importants:

- antagonistes;
- aliats importants;
- rivals;
- dirigents de facció;
- personatges amb una agenda pròpia.

Poden actuar quan avança el temps:

```text
Passa un dia
    ↓
NPC actiu revisa objectius
    ↓
Escull o proposa una acció
    ↓
Es crea un Event
    ↓
El món s'actualitza
```

---

# 18. Encounter Engine

En una fase posterior, el projecte incorporaria una eina per generar encounters coherents amb el context.

No hauria de ser un simple generador aleatori de monstres.

L'Encounter Engine hauria de tenir en compte:

- sistema: D&D 5e;
- nivell del grup;
- nombre de personatges;
- estat actual del grup si el DM vol considerar-lo;
- localització;
- bioma;
- hora del dia;
- perillositat de la regió;
- faccions presents;
- esdeveniments actius;
- reputació del grup;
- conseqüències de decisions prèvies;
- objectiu narratiu de l'escena;
- dificultat desitjada;
- freqüència recent de combats;
- tipus d'encontre: combat, social, exploració, hazard, puzzle, mixt, etc.

Exemple:

```text
Party level: 5
Location: jungle
Situation: travelling between two known locations
Recent events: local hunters distrust the party
Desired difficulty: medium
```

El sistema podria generar:

```text
Encounter type: social / exploration
Reason: hunting party has heard a negative rumor
Potential escalation: combat only if negotiations fail
Possible consequence: rumor spread or reputation change
```

Això és més interessant que generar enemics sense context.

---

# 19. Tipus d'encounters

El generador hauria de suportar almenys:

## Combat

- enemics contextuals;
- objectius diferents de "matar-ho tot";
- terreny;
- complicacions;
- reforços;
- vies de retirada;
- conseqüències.

## Social

- negociació;
- interrogatori;
- disputa;
- petició d'ajuda;
- suborn;
- rumor;
- conflicte entre faccions.

## Exploració

- descobriments;
- rastres;
- ruïnes;
- obstacles;
- vies alternatives;
- recursos;
- informació ambiental.

## Hazards

- clima;
- terreny;
- malalties;
- trampes;
- problemes logístics;
- riscos naturals.

## Mixt

Combinació de diversos tipus.

---

# 20. Reward Engine

El sistema de recompenses hauria de generar recompenses que **tinguin sentit**, en lloc de seleccionar objectes completament aleatoris.

Factors possibles:

- dificultat de l'encontre;
- tipus d'encontre;
- nivell dels personatges;
- enemics implicats;
- lloc on es troben;
- riquesa de la zona;
- facció propietària;
- context narratiu;
- recompensa ja obtinguda recentment;
- economia de la campanya;
- progressió màgica desitjada pel DM;
- raresa màxima autoritzada;
- consumibles vs objectes permanents;
- informació o favors com a recompensa no monetària.

---

# 21. Mode de recompensa neutre

Aquest seria el comportament **per defecte**.

L'objectiu és generar una recompensa raonable i equilibrada, sense premiar ni castigar especialment la fortuna.

```text
Encounter
    ↓
Dificultat
    ↓
Context
    ↓
Pressupost / tier de recompensa esperat
    ↓
Filtre temàtic
    ↓
Recompensa coherent
```

Exemple conceptual:

```text
Dificultat: mitjana
Context: bandits locals
Campanya: baixa disponibilitat d'objectes màgics

Possible reward:
- moneda moderada;
- provisions;
- un mapa parcial;
- informació sobre una ruta;
- un objecte mundà útil;
- petita probabilitat de consumible apropiat.
```

La recompensa no ha de ser sempre tresor físic.

---

# 22. Mode de recompensa amb tirada

Opcionalment el DM pot activar un mode de fortuna.

Es faria una tirada que modifiqui la qualitat de la recompensa al voltant del valor neutral.

Per exemple:

```text
1 ───────────── 10 ───────────── 20
pitjor           neutral          millor
```

Un possible comportament:

```text
1-3     recompensa clarament inferior a l'esperada
4-7     lleugerament inferior
8-13    recompensa neutral
14-17   lleugerament superior
18-19   molt bona recompensa
20      recompensa excepcional o especialment interessant
```

Aquests rangs haurien de ser configurables.

Important: una tirada baixa **no hauria de fer absurda la recompensa**.

Per exemple, derrotar un enemic important no hauria de donar literalment res només per haver tret un 1.

La tirada modifica la recompensa dins d'un interval coherent.

---

# 23. Fortuna no equival només a valor econòmic

Una tirada alta podria millorar diferents dimensions:

- quantitat;
- qualitat;
- raresa;
- utilitat;
- informació trobada;
- estat de conservació;
- connexió amb una quest;
- valor per a una facció;
- possibilitat de trobar una pista secreta.

Exemple:

```text
Neutral:
100 gp + una carta incompleta

Bona tirada:
120 gp + carta completa + pista sobre un NPC

Molt bona tirada:
120 gp + carta completa + pista + objecte consumible contextual
```

Això evita convertir la fortuna en una simple multiplicació de monedes.

---

# 24. Recompenses narratives

El Reward Engine hauria de considerar recompenses no materials:

- favors;
- contactes;
- reputació;
- informació;
- accés a una zona;
- refugi;
- descomptes;
- suport d'una facció;
- transport;
- mapes;
- rumors fiables;
- drets o permisos;
- aliats temporals;
- pistes de quests.

A D&D aquestes recompenses poden ser més memorables que un objecte aleatori.

---

# 25. Encounters i conseqüències del món

L'Encounter Engine hauria d'estar connectat a la resta del sistema.

Exemple:

```text
Els jugadors roben una ciutat
        ↓
Wanted level augmenta
        ↓
Rumor es propaga
        ↓
Encounter Engine consulta l'estat
        ↓
Major probabilitat de:
- patrulles;
- controls;
- caçadors de recompenses;
- NPCs desconfiats;
- criminals interessats en contactar-los.
```

Així els encounters es converteixen en conseqüències naturals del món.

---

# 26. Sessions

Cada sessió hauria de tenir un registre propi.

```text
SESSION
├── data
├── participants
├── events
├── NPC interactions
├── discoveries
├── combat encounters
├── rewards
└── summary
```

Al final de la sessió, el sistema pot generar:

- resum per al DM;
- esdeveniments importants;
- memòries que cal conservar;
- canvis de reputació;
- rumors nous;
- quests afectades;
- estat de faccions;
- assumptes pendents per a la següent sessió.

---

# 27. Base de dades

Per a una primera versió, **SQLite** és una bona opció.

Avantatges:

- gratuït;
- local;
- un sol fitxer;
- fàcil de copiar i fer backup;
- suficient per a una campanya sencera;
- no requereix servidor.

Possible esquema inicial:

```text
CAMPAIGN
SESSION
WORLD_STATE
LOCATION
NPC
NPC_RELATIONSHIP
NPC_MEMORY
EVENT
RUMOR
FACTION
FACTION_RELATIONSHIP
KNOWLEDGE
QUEST
ENCOUNTER
REWARD
```

Els fitxers JSON poden seguir sent útils per a:

- importar campanyes;
- exportar campanyes;
- plantilles;
- configuració;
- backups llegibles.

---

# 28. Model d'IA local

Per mantenir el projecte gratuït, una opció interessant és utilitzar:

```text
Aplicació
    │
    ▼
LM Studio / Ollama
    │
    ▼
Model local
```

No cal tenir un model diferent per NPC.

```text
                 MATEIX LLM
                    ▲
        ┌───────────┼───────────┐
        │           │           │
      NPC A       NPC B       NPC C
```

El que diferencia els agents és:

- system prompt;
- personalitat;
- memòria;
- relacions;
- objectius;
- context actual.

Això permet tenir centenars de NPC registrats sense carregar centenars de models.

---

# 29. Funcionament gratuït i opcions de model

El projecte s'ha plantejat perquè pugui funcionar sense pagar per cada interacció.

## Opció recomanada: model local

```text
Aplicació
    ↓
LM Studio o Ollama
    ↓
Model local
```

Avantatges:

- sense cost per token;
- dades de campanya locals;
- útil per fer moltes interaccions amb NPCs;
- un sol model pot interpretar tots els agents;
- permet automatitzar les converses entre NPCs i el Game Master Agent.

El cost pràctic és el hardware disponible i el consum de l'ordinador. El model concret s'haurà d'escollir segons RAM, GPU i VRAM.

## ChatGPT Free com a prototip manual

També es pot provar el concepte manualment dins ChatGPT Free, mantenint fitxes de NPC, resums i estat del món en el mateix xat o en documents auxiliars.

És útil per validar prompts, personalitats i fluxos abans de programar res, però no s'ha de considerar equivalent a disposar d'una API gratuïta per automatitzar el projecte. Per a una aplicació amb agents que facin múltiples crides automàtiques, el model local és la via gratuïta més adequada.

---

## 29.1. Desplegament per fases

### Fase A — Desenvolupament local

```text
Developer machine
├── frontend dev server
├── FastAPI
├── SQLite
└── Ollama / LM Studio
```

### Fase B — Aplicació local usable

Un launcher arrenca automàticament els components necessaris i obre el navegador.

```text
[Open Campaign AI]
       ↓
launcher
├── inicia backend
├── comprova SQLite
├── comprova LLM local
└── obre UI
```

### Fase C — Desktop empaquetat

Si aporta valor, empaquetar la UI i el backend perquè l'experiència sigui similar a una aplicació nativa.

### Fase D — Cloud opcional

Afegir Azure només per funcions que requereixen realment infraestructura remota: sync, backup, compartir o accés des de diversos dispositius.

---

# 30. Perfil de regles D&D 5e

Com que D&D 5e té diferents revisions i moltes taules utilitzen regles opcionals o homebrew, el motor no hauria de codificar una única interpretació rígida de les regles.

Cada campanya podria seleccionar un `rules_profile`:

```json
{
  "system": "dnd5e",
  "rules_profile": "campaign_default",
  "house_rules": []
}
```

Això permetria conservar la mateixa campanya encara que el grup utilitzi una combinació concreta de regles, i facilitaria adaptar el motor a futures revisions sense afectar NPCs, memòries, rumors o reputació.

El mateix principi s'aplicaria al balanç dels encounters i a les recompenses: les taules, fórmules i criteris mecànics haurien de pertànyer al perfil de regles, no estar incrustats en els agents d'IA.

---

## 30.1. API local inicial

Sense convertir l'API en el centre del disseny, uns endpoints inicials podrien ser:

```text
GET    /campaigns
GET    /campaigns/{id}
POST   /sessions
POST   /events/analyze
POST   /events/{id}/apply
GET    /npcs
GET    /npcs/{id}
POST   /npcs/{id}/chat
GET    /timeline
POST   /encounters/generate
POST   /rewards/generate
```

Les respostes de la IA que poden modificar estat haurien de seguir esquemes estructurats i validables, no text lliure.

---

# 31. Interfície del DM

La interfície ha de ser **amigable, ràpida i pensada per utilitzar-se mentre hi ha una partida en curs**. No ha de semblar un panell d'administració ni obligar el DM a editar JSON, prompts o registres manualment.

La IA ha de quedar en segon pla. El DM interactua amb conceptes de joc: NPCs, esdeveniments, rumors, encounters, recompenses i sessions.

## 31.1. Dos modes principals

### Mode Preparació

Pensat per abans o després de la sessió. Pot oferir més profunditat:

- crear i editar NPCs;
- preparar localitzacions;
- revisar faccions;
- modificar reputacions;
- gestionar rumors;
- preparar encounters;
- configurar recompenses;
- revisar memòries;
- importar contingut de campanya;
- consultar el timeline;
- configurar regles i preferències.

### Mode Sessió

Ha de ser molt més minimalista. Les accions més importants haurien d'estar disponibles immediatament:

```text
+ Event
+ NPC
⚔ Encounter
🎁 Reward
🎲 Roll
🔍 Search
```

La pregunta principal de la pantalla podria ser simplement:

> Què acaba de passar?

El sistema interpreta el text, proposa conseqüències i deixa l'última decisió al DM.

## 31.2. Session Dashboard

Primera pantalla prioritària del projecte:

```text
┌────────────────────────────────────────────────────────────────────┐
│ Tomb of Annihilation        Dia 37        Port Nyanzaru      ⚙    │
├───────────────┬─────────────────────────────────┬──────────────────┤
│ CAMPANYA      │          SESSIÓ ACTUAL          │ CONTEXT          │
│               │                                 │                  │
│ 🗺 Món         │  Què acaba de passar?           │ ⚠ Buscats        │
│ 👥 NPCs        │ ┌─────────────────────────────┐ │                  │
│ 🏰 Faccions    │ │ Els jugadors han entrat... │ │ Reputació       │
│ 📜 Events      │ └─────────────────────────────┘ │ Rumors actius    │
│ 💬 Rumors      │                                 │ Events rellevants│
│ ⚔ Encounters   │       [Registrar event]         │                  │
│ 🎁 Rewards     │                                 │                  │
│ 📖 Sessions    │                                 │                  │
├───────────────┴─────────────────────────────────┴──────────────────┤
│ NPCs presents: NPC A · NPC B · NPC C                  + Add NPC    │
└────────────────────────────────────────────────────────────────────┘
```

Objectiu: que registrar un esdeveniment normal requereixi **una entrada de text i una confirmació**, no navegar per múltiples formularis.

## 31.3. Flux de registre d'un esdeveniment

Exemple d'entrada del DM:

> Els jugadors han intentat subornar un guàrdia. El guàrdia s'hi ha negat però no els ha denunciat.

El sistema mostra una proposta compacta:

```text
EVENT DETECTAT

Intent de suborn

Guàrdia #14
  confiança party     -10
  sospita             +20

Propostes:
  ✓ crear memòria NPC
  ○ crear rumor
  ○ afectar reputació de la guàrdia

[Aplicar] [Modificar] [Ignorar]
```

Cap canvi sensible al món s'aplica de manera silenciosa en les primeres versions.

## 31.4. Vista d'NPC

```text
┌─────────────────────────────┐
│ KARA                        │
│                             │
│ 📍 Localització actual      │
│                             │
│ Relació amb el grup         │
│ Trust          ██████ 62    │
│ Respect        ███████ 71   │
│ Fear           ██ 14        │
│ Affection      ████ 38      │
│                             │
│ Objectiu actual             │
│ Protegir el seu negoci.     │
│                             │
│ Sap                          │
│ • rumor_14                  │
│ • event_31                  │
│                             │
│ Recorda                     │
│ • El grup la va ajudar...  │
│ • Discussió amb...         │
│                             │
│       [Parlar com NPC]      │
└─────────────────────────────┘
```

El DM ha de poder veure **per què** l'NPC està reaccionant d'una certa manera: memòria, reputació, rumor o relació. Això facilita detectar errors de context.

## 31.5. Conversa amb NPC

La conversa no ha de ser un xat desconnectat. Abans de cada resposta, el Context Builder prepara:

- personalitat;
- objectiu;
- situació actual;
- relació;
- memòries rellevants;
- informació coneguda;
- reputació aplicable;
- estat del món rellevant.

Després de la conversa, el sistema pot proposar:

- noves memòries;
- canvi de relació;
- event;
- rumor;
- nova intenció de l'NPC.

## 31.6. Encounter Generator

```text
⚔ CREATE ENCOUNTER

Party:             auto
Location:          auto
Context:           auto

Difficulty
○ Easy
● Medium
○ Hard
○ Deadly

Type
● Auto
○ Combat
○ Social
○ Exploration
○ Hazard
○ Mixed

✓ Respect current location
✓ Respect factions
✓ Respect current events
✓ Consider party reputation

[Generate]
```

El sistema ha d'omplir automàticament la informació que ja coneix. El DM només modifica allò que vulgui forçar.

## 31.7. Reward Generator

```text
🎁 GENERATE REWARD

Encounter: Current encounter

Reward mode
● Balanced / Neutral
○ Fortune roll 🎲
○ Manual

Context-aware: ✓
Campaign economy: default
Magic item frequency: campaign default

[Generate]
```

En mode fortuna:

```text
d20 → 17

Expected reward tier: Normal
Adjusted reward tier: Above average
```

La tirada modifica la recompensa dins d'un rang coherent; no substitueix les restriccions del perfil de campanya.

## 31.8. Timeline de campanya

```text
WORLD EVENTS

Day 32    Party enters city
Day 34    Merchant dispute
Day 36    Robbery
Day 36    Guards alerted
Day 37    Wanted posters appear
```

Ha de permetre filtrar per:

- sessió;
- localització;
- NPC;
- facció;
- tipus d'esdeveniment;
- importància.

## 31.9. Disseny visual i navegació

La UI hauria de prioritzar llegibilitat i velocitat per sobre d'efectes visuals. Proposta de criteris:

- navegació lateral fixa amb les àrees principals;
- zona central dedicada a la tasca actual;
- panell lateral dret opcional amb context rellevant;
- targetes compactes per NPCs, rumors i events;
- badges clars per estats com `Wanted`, `Rumor`, `Secret`, `Hostile` o `Pending`;
- mode fosc adequat per sessions llargues i mode clar opcional;
- tipografia molt llegible i densitat moderada;
- icones només quan acceleren el reconeixement;
- colors d'alerta reservats per informació realment important;
- accions primàries consistents: `Apply`, `Modify`, `Ignore`;
- dreceres de teclat opcionals per accions freqüents;
- responsive suficient per consultar la campanya des d'un portàtil o tablet, sense convertir el mòbil en objectiu principal de l'MVP.

La interfície ha d'evitar una aparença de "terminal d'IA". L'usuari està gestionant una campanya, no configurant un model de llenguatge.

### Patró de layout principal

```text
┌──────────────┬──────────────────────────────┬────────────────────┐
│ NAVIGATION   │ PRIMARY WORKSPACE            │ CONTEXT            │
│              │                              │                    │
│ Session      │ Event / NPC / Encounter      │ World state        │
│ NPCs         │                              │ Relevant rumors    │
│ World        │ Main interaction             │ Reputation         │
│ Factions     │                              │ Memories           │
│ Encounters   │                              │                    │
│ Rewards      │                              │                    │
└──────────────┴──────────────────────────────┴────────────────────┘
```

En pantalles petites, el panell de context es pot convertir en un drawer desplegable.

---

# 32. Arquitectura de l'aplicació: web local

Per al primer MVP, la proposta és una **web local**. El DM obre el navegador i accedeix a una adreça local, per exemple `http://localhost:xxxx`.

Això combina una UI moderna amb un backend i una base de dades que poden continuar sent completament locals.

```text
Browser
   │
   ▼
Frontend web local
   │
   ▼
Backend API local
   │
   ├────────► SQLite
   │
   └────────► Ollama / LM Studio
                   │
                   ▼
                Local LLM
```

## 32.1. Per què web local

Avantatges:

- desenvolupament ràpid;
- UI molt més fàcil de fer amigable que una CLI;
- funciona a Windows, macOS i Linux amb pocs canvis;
- el navegador resol bona part del rendering i l'accessibilitat;
- pot funcionar sense Internet;
- facilita convertir-la més endavant en una aplicació desktop empaquetada;
- la mateixa UI es pot reutilitzar si algun dia es desplega una versió web remota.

## 32.2. Stack inicial proposat

Una opció pragmàtica:

```text
Frontend
  React + TypeScript + Vite

Backend
  Python + FastAPI

Persistència
  SQLite

LLM
  Ollama o LM Studio

Contracte UI ↔ backend
  REST/JSON inicialment
```

No és una decisió irreversible. El més important és mantenir el `Campaign Engine` independent del framework.

Python/FastAPI és especialment útil per a un prototip perquè facilita integrar SQLite, validació de dades i llibreries relacionades amb LLM. React/TypeScript és adequat per construir un dashboard interactiu.

## 32.3. Aplicació desktop futura

Si la web local funciona bé, es pot empaquetar posteriorment com una aplicació instal·lable:

```text
D&D Campaign AI
       │
       ├── UI web empaquetada
       ├── backend local
       ├── SQLite
       └── connexió a LLM local
```

L'objectiu seria que l'usuari no hagués d'obrir terminals ni iniciar serveis manualment.

---

# 33. Arquitectura interna per capes

```text
┌──────────────────────────────────────┐
│ Presentation                         │
│ Dashboard / NPC / Events / Rewards  │
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│ Application Services                 │
│ commands / queries / orchestration  │
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│ Domain / Campaign Engine             │
│ NPC, Memory, Event, Rumor, etc.     │
└───────────────┬───────────┬──────────┘
                │           │
        ┌───────▼──────┐ ┌──▼─────────────┐
        │ Storage      │ │ LLM Provider    │
        │ interface    │ │ interface       │
        └───────┬──────┘ └──┬─────────────┘
                │            │
       ┌────────┴──────┐ ┌───┴──────────────┐
       │ SQLite        │ │ Ollama            │
       │ Cosmos future │ │ LM Studio         │
       └───────────────┘ │ cloud future      │
                         └───────────────────┘
```

## 33.1. Storage interface

El motor no hauria de fer SQL directament.

Conceptualment:

```text
CampaignRepository
NPCRepository
EventRepository
MemoryRepository
...
        │
        ├── SQLite implementation
        └── Cosmos implementation (futur)
```

Això permet que SQLite sigui la base local sense impedir una futura sincronització amb Azure.

## 33.2. LLM Provider interface

Igualment:

```text
LLMProvider
    │
    ├── OllamaProvider
    ├── LMStudioProvider
    └── CloudProvider (opcional futur)
```

El motor demana una resposta estructurada; no necessita saber quin model concret l'ha produït.

---

# 34. Azure com a extensió opcional

Azure **no formarà part dels requisits de l'MVP**. La primera versió ha de funcionar íntegrament en local.

Azure pot ser útil més endavant per aportar:

- sincronització entre dispositius;
- còpia de seguretat remota;
- accés des d'un portàtil o tablet;
- compartir una campanya;
- APIs remotes;
- automatitzacions puntuals.

Arquitectura futura possible:

```text
                 LOCAL APP
                    │
          SQLite + Local LLM
                    │
              optional sync
                    │
                    ▼
                  AZURE
          ┌─────────┼─────────┐
          ▼         ▼         ▼
     Static Web   Functions  Cosmos DB
        Apps
```

## 34.1. Cosmos DB

Cosmos DB és interessant perquè moltes entitats del projecte tenen una representació natural com a documents JSON: NPCs, memòries, events, rumors, sessions, etc.

A data de **7 d'agost de 2026**, Microsoft documenta un Free Tier de Cosmos DB amb els primers **1.000 RU/s i 25 GB d'emmagatzematge** gratuïts durant la vida del compte. El Free Tier s'ha d'habilitar al compte i Microsoft indica que actualment no està disponible per a comptes serverless.

Per al projecte, Cosmos DB s'hauria d'introduir només quan existeixi una necessitat real de sincronització o accés remot.

Font oficial: [Azure Cosmos DB lifetime free tier](https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier)

## 34.2. Azure Functions

Functions podria allotjar operacions petites i independents, per exemple:

```text
sync-campaign()
save-event()
process-session()
refresh-rumors()
backup-campaign()
```

A data de **7 d'agost de 2026**, Microsoft publica per al pla Consumption una franquícia mensual de **1 milió de requests i 400.000 GB-s** de consum de recursos per subscripció pay-as-you-go, tot i que altres recursos associats poden generar cost.

Font oficial: [Azure Functions pricing](https://azure.microsoft.com/en-us/pricing/details/functions/)

## 34.3. Azure Static Web Apps

Si en el futur es vol accés web remot, Azure Static Web Apps disposa d'un pla **Free** i pot allotjar el frontend. També pot integrar APIs basades en Functions.

Font oficial: [Azure Static Web Apps hosting plans](https://learn.microsoft.com/en-us/azure/static-web-apps/plans)

## 34.4. Per què no començar amb Azure

Fer l'MVP directament al cloud afegiria complexitat abans de validar el nucli del projecte:

- autenticació;
- configuració de recursos;
- networking;
- costos i quotes;
- sincronització;
- dependència de connexió;
- més punts de fallada durant una sessió.

El risc és invertir temps en infraestructura abans de demostrar que el sistema de context, memòria i reacció dels NPCs funciona bé.

---

# 35. Sincronització i còpies de seguretat

En la primera versió:

```text
campaign.db
```

és la font principal de dades.

S'haurien d'oferir accions senzilles:

```text
[Export campaign]
[Import campaign]
[Create backup]
[Restore backup]
```

Un export podria generar un paquet amb:

```text
campaign-export/
├── campaign.json
├── campaign.db
├── configuration.json
└── attachments/
```

En una fase cloud:

```text
LOCAL SQLITE
     │
     ▼
SYNC ENGINE
     │
     ▼
COSMOS DB
```

La sincronització ha de tenir resolució de conflictes i no pot assumir que sempre hi ha connexió.

---

# 36. Requisits d'experiència d'ús

L'eina hauria de complir aquests principis:

1. **Cap terminal durant la partida.**
2. **No editar JSON manualment per operacions normals.**
3. **El context existent s'omple automàticament.**
4. **Les accions destructives o importants són reversibles o confirmables.**
5. **El DM pot veure per què la IA proposa una conseqüència.**
6. **Cerca global ràpida per NPC, lloc, rumor, event o facció.**
7. **La UI ha de continuar sent usable si el LLM està desconnectat.**
8. **El DM sempre té l'última paraula.**
9. **La latència ha de ser acceptable durant una conversa en directe.**
10. **La campanya ha de poder exportar-se sense quedar atrapada en un servei cloud.**

---

# 37. Flux durant una sessió

```text
SESSION START
        ↓
Carregar campanya
        ↓
Carregar World State
        ↓
DM introdueix o selecciona situació
        ↓
Jugador interactua amb NPC
        ↓
Context Builder
        ↓
NPC Agent / LLM
        ↓
Diàleg o decisió
        ↓
Succeeix alguna cosa important
        ↓
GM Agent proposa Event
        ↓
DM valida
        ↓
Actualitzar:
- World State
- reputació
- memòries
- rumors
- faccions
        ↓
Opcionalment generar encounter
        ↓
Resoldre encounter
        ↓
Reward Engine
        ↓
Registrar resultats
```

---

# 38. Roadmap proposat

## Versió 0.1 — Vertical slice utilitzable

Objectiu: validar l'experiència real del DM des del primer moment.

- web local;
- Session Dashboard mínim;
- una campanya;
- SQLite;
- connexió amb Ollama o LM Studio;
- crear/editar NPC;
- personalitat i objectius;
- seleccionar NPC i conversar-hi;
- registrar un event des de text natural;
- memòria manual o proposada;
- confirmació abans d'aplicar canvis.

## Versió 0.2 — Persistència del món

- World State;
- relationships;
- reputació;
- historial de sessions;
- timeline;
- cerca bàsica;
- export/import local.

## Versió 0.3 — Game Master Agent

- interpretació estructurada d'esdeveniments;
- proposta automàtica de conseqüències;
- creació de memòries;
- resum de sessions;
- aprovació/modificació/ignoració des de la UI.

## Versió 0.4 — Coneixement i rumors

- knowledge per NPC;
- informació pública/privada;
- rumors;
- propagació;
- creences incorrectes;
- faccions.

## Versió 0.5 — NPCs actius

- objectius persistents;
- accions entre sessions;
- evolució de relacions;
- agendas de facció;
- revisió/aprovació pel DM.

## Versió 0.6 — Encounter Engine

- encounters contextuals;
- combat/social/exploració/hazard/mixt;
- dificultat D&D 5e;
- integració amb localització, reputació, events i faccions;
- registre de conseqüències.

## Versió 0.7 — Reward Engine

- recompensa contextual;
- mode neutral per defecte;
- mode opcional amb tirada;
- recompenses narratives;
- control de disponibilitat d'objectes màgics;
- coherència amb economia i progressió.

## Versió 0.8 — Party Core i poliment local

- personatges jugadors persistents amb PG, CA, atributs, estats, recursos i visibilitat;
- inventari compartit, individual i per ubicació;
- tresoreria multimoneda i historial de moviments;
- botí reclamable sense duplicats;
- sincronització amb descansos, combat i pantalla de jugadors;
- launcher, dashboard refinat, backups i gestió de configuració;
- importació/exportació robusta de tot el Party Core.

## Versió 0.9 — Campaign Operations

- missions i objectius amb visibilitat diferenciada;
- calendari, venciments i cronologia;
- clocks, amenaces i conseqüències;
- Session Planner, registre automàtic i resum validable;
- resolució d'encounters connectada a XP, botí, missions i clocks;
- progressió de personatges i descansos ampliats;
- mapes d'imatge amb marcadors i vincles documentals;
- hexcrawl amb risc, etiquetes de perill i alerta dinàmica;
- projecció filtrada de missions, calendari i cronologia als jugadors.

## Versió 1.0 — Motor de campanyes

- múltiples campanyes;
- plantilles locals en blanc, expedició selvàtica, intriga urbana i dungeon;
- Tomb of Annihilation com a primera campanya funcional;
- suport senzill per afegir una altra campanya D&D 5e;
- experiència local estable;
- cloud completament opcional.
- NPC actius amb autonomia configurable i accions entre sessions pendents d'aprovació;
- flux documental revisable que converteix fragments amb font i pàgina en coneixement canònic.

---

# 39. Prioritats tècniques

Ordre recomanat:

1. **Contractes del domini i model de dades mínim.**
2. **Web local amb Session Dashboard mínim.**
3. **SQLite i repositoris.**
4. **Abstracció `LLMProvider`.**
5. **Un NPC persistent funcional.**
6. **Context Builder.**
7. **Registrar Events des de la UI.**
8. **Memòria i relacions.**
9. **World State i reputació.**
10. **Game Master Agent.**
11. **Rumors, knowledge i faccions.**
12. **Encounters.**
13. **Recompenses.**
14. **Packaging desktop / launcher.**
15. **Azure opcional i sincronització.**

El primer criteri d'èxit no és tenir moltes funcionalitats. És poder fer aquesta seqüència còmodament:

```text
Obrir aplicació
    ↓
Carregar campanya
    ↓
Registrar un fet
    ↓
Veure una conseqüència proposada
    ↓
Acceptar-la
    ↓
Parlar amb un NPC afectat
    ↓
Comprovar que recorda i reacciona coherentment
```

Si això funciona bé, el nucli del projecte està validat.

---

# 40. Decisions que convé mantenir configurables

Perquè el sistema sigui útil en diferents taules i campanyes, convé no codificar aquestes decisions de manera rígida:

- freqüència d'objectes màgics;
- severitat de reputació;
- velocitat de propagació de rumors;
- mortalitat dels encounters;
- importància del realisme econòmic;
- freqüència d'encounters aleatoris;
- granularitat de memòria;
- autonomia dels NPCs actius;
- quantitat de decisions que requereixen aprovació del DM;
- escala de les relacions;
- ús de regles estrictes vs interpretació narrativa;
- sistema de fortuna per recompenses;
- probabilitat que un rumor es deformi;
- quantitat de context enviada al model.
- proveïdor LLM;
- model concret;
- backend d'emmagatzematge;
- ús o no de sincronització cloud;
- freqüència de backups;
- nivell d'automatització del GM Agent.

---

# 41. Filosofia del Reward Engine

El generador de recompenses no hauria de respondre només a:

> Què ha sortit a la taula de loot?

Sinó a:

> Quina recompensa és coherent amb el que acaba de passar, amb aquesta campanya i amb la progressió actual del grup?

El mode neutral respon aquesta pregunta sense afegir un biaix de fortuna.

El mode amb tirada afegeix una capa opcional de sorpresa:

```text
RECOMPENSA ESPERADA
       │
       ├── mala tirada  → variant inferior però coherent
       │
       ├── tirada mitjana → valor esperat
       │
       └── bona tirada → variant superior o més interessant
```

Això permet conservar l'emoció de "veure què trobem" sense perdre coherència narrativa.

---

# 42. Filosofia de l'Encounter Engine

De manera similar, un encounter no hauria de ser només:

> 2d6 monstres apareixen.

Sinó una conseqüència possible de:

```text
LOCALITZACIÓ
+
ESTAT DEL MÓN
+
REPUTACIÓ
+
FACCIÓ
+
RUMORS
+
NIVELL DEL GRUP
+
RITME DE LA SESSIÓ
+
OBJECTIU NARRATIU
```

Això permet que dues visites al mateix lloc no siguin iguals si les accions dels jugadors han canviat el món.

---

# 42.1. Estructura de projecte proposada

```text
project/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── features/
│   │   └── api/
│   └── ...
│
├── backend/
│   ├── api/
│   ├── application/
│   ├── domain/
│   │   ├── campaign/
│   │   ├── npc/
│   │   ├── events/
│   │   ├── memory/
│   │   ├── rumors/
│   │   ├── encounters/
│   │   └── rewards/
│   ├── infrastructure/
│   │   ├── sqlite/
│   │   ├── llm/
│   │   └── azure/
│   └── main.py
│
├── campaigns/
│   └── tomb_of_annihilation/
│       ├── campaign.json
│       ├── locations/
│       ├── factions/
│       ├── npcs/
│       └── imports/
│
├── data/
│   └── campaign.db
│
├── backups/
└── docs/
```

La carpeta `azure/` pot existir buida o no existir durant l'MVP; no és una dependència del motor.

---

# 43. Visió a llarg termini

La versió madura del projecte seria una **aplicació independent de suport al DM** amb un `Campaign Simulation Layer` persistent.

```text
                         DM
                          │
                          ▼
                  FRIENDLY LOCAL UI
                          │
                          ▼
                  CAMPAIGN ENGINE
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
      WORLD             EVENTS          FACTIONS
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                 KNOWLEDGE / RUMORS
                          │
                   NPC RELATIONSHIPS
                          │
                      NPC MEMORY
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
      NPC AI         ENCOUNTERS         REWARDS
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                     LLM PROVIDER
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
          LOCAL MODEL            CLOUD MODEL
          recommended              optional

Persistence:

          SQLite local
              │
              └── optional sync ──► Azure / Cosmos DB
```

El DM continua tenint l'última paraula. La IA manté context, proposa i interpreta; el motor conserva l'estat i les regles.

El projecte no dependrà de cap VTT extern: tota la funcionalitat definida en aquest document formarà part de l'aplicació pròpia.

---

# 44. Resum del concepte

```text
                    D&D 5e CAMPAIGN APP
                            │
                    Session Dashboard
                            │
                    Campaign Engine
                            │
     ┌──────────────────────┼──────────────────────┐
     │                      │                      │
  WORLD / EVENTS       NPC SIMULATION       TOOLS FOR DM
     │                      │                      │
     ├─ Locations           ├─ Personality        ├─ Encounters
     ├─ Factions            ├─ Memory             ├─ Rewards
     ├─ Reputation          ├─ Relationships      ├─ Session summary
     ├─ Knowledge           ├─ Goals              └─ Timeline
     └─ Rumors              └─ Dialogue
                            │
                       LLM Provider
                            │
                  Ollama / LM Studio
                            │
                      Local model

Storage default: SQLite
Cloud extension: Azure optional
Campaign format: modular and replaceable
Platform: independent application, no VTT dependency
```

**Tomb of Annihilation és la primera campanya, no el projecte.**

**SQLite + model local + web local és la primera arquitectura, no una limitació futura.**

El projecte és el motor persistent, modular i reutilitzable que permet que una campanya de D&D 5e tingui NPCs amb memòria, reputació, rumors, conseqüències, encounters contextuals i recompenses coherents des d'una interfície pensada per al DM.

---

# 45. Següent pas recomanat

El següent pas és definir una **Vertical Slice 0.1** en lloc d'intentar modelar tota la campanya.

Ha de contenir exactament el necessari per provar el concepte en una situació real:

```text
1 Campaign
1 Location
1 Party
3-4 NPCs
1 Faction
Relationship + Memory
World State mínim
Events
Session Dashboard
SQLite
Local LLM
```

Flux que s'ha de poder completar:

```text
DM obre la web local
        ↓
Selecciona la campanya
        ↓
Comença sessió
        ↓
Escriu què ha passat
        ↓
GM Agent proposa Event + conseqüències
        ↓
DM accepta/modifica
        ↓
World State s'actualitza
        ↓
DM obre NPC afectat
        ↓
Context Builder recupera memòria + reputació + knowledge
        ↓
NPC respon coherentment
        ↓
Sistema proposa nova memòria/relació
        ↓
DM valida
```

Les primeres entitats que cal concretar són:

```text
Campaign
RulesProfile
Session
Location
Party
NPC
Relationship
Memory
Event
WorldState
Faction
Reputation
Knowledge
Rumor
Encounter
Reward
```

I les primeres interfícies tècniques:

```text
StorageRepository
LLMProvider
ContextBuilder
EventProcessor
```

Una vegada aquesta vertical slice sigui usable durant una sessió, es pot ampliar gradualment amb rumors, NPCs actius, encounters, rewards i finalment sincronització opcional amb Azure.

---

# 46. Estat implementat: versió 1.1 local-first

La vertical slice i els mòduls locals previstos fins a la versió 1.1 ja estan implementats. A més dels motors de campanya, biblioteca, hexcrawl, combat, operacions, NPC actius i pantalla de jugadors, la versió 1.1 incorpora:

- safata de daus persistent per campanya;
- notació limitada i validada, modificadors i CD;
- avantatge i desavantatge per a tirades d'un d20;
- historial SQLite independent del registre de combat;
- 15 condicions de l'SRD 5.1 integrades al catàleg local;
- panell de consulta de condicions pensat per a l'ús durant la sessió.

La sincronització cloud, l'OCR i la cerca semàntica continuen sent extensions opcionals. El nucli 1.1 no les necessita.

---

# 47. Estat implementat: versió 1.2, Laboratori d'aventures

La versió 1.2 amplia el nucli local amb un paquet homebrew original orientat a expedicions de selva, sense reproduir cap aventura o bestiari comercial:

- 8 enemics amb CA, PG, CR orientatiu, accions, tàctica i recursos recuperables;
- 8 temples modulars amb ganxo, aproximació, sales, guardià, secret, recompensa i escalada;
- 12 situacions amb decisions, proves, CD, èxit, fallada i continuació;
- 6 minijocs amb objectiu, límit de perill, rondes, proves i desenllaç;
- cerca i filtres per categoria, terreny, nivell i dificultat;
- integració d'enemics amb Combat Assistant;
- conversió de temples i situacions en escenes persistents;
- conversió de minijocs en clocks persistents amb tirades i activitat auditable.

El pack és dades substituïbles i queda separat del catàleg SRD i dels documents privats del DM. Això permet afegir en el futur nous biomes o aventures pròpies sense canviar el motor.

---

# 48. Estat implementat: versió 1.3, composició i packs privats

La versió 1.3 converteix el Laboratori en una eina de preparació de sessió ampliable:

- compositor d'expedicions amb enemic, temple, situació i minijoc compatibles;
- desament del conjunt com una escena persistent i activitat de planificació;
- estimació de dificultat amb llindars XP, multiplicadors de grups d'enemics i mida del grup;
- favorits locals per campanya i filtre dedicat;
- deep links per obrir directament una categoria i un recurs;
- descoberta i selecció de diversos packs;
- importació JSON privada amb validació, escriptura atòmica i límit d'1 MB;
- protecció del pack inclòs i eliminació explícita només de packs privats;
- origen i llicència visibles a cada recurs.

Els packs privats continuen fora del repositori, mentre que qualsevol escena, clock o combatent aplicat passa a formar part de l'estat SQLite de la campanya.
