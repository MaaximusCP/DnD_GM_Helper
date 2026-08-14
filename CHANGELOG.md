# Registre de canvis

## 2026-08-14 14:53 — Continuïtat d'expedició i encounters

Hora: 14:53, Europe/Madrid.

Canvi fet:

- afegits revelat i exploració radial de zones del mapa;
- incorporada eliminació segura d'hexàgons, protegint sempre la posició actual;
- implementats descansos curts i llargs amb provisions, campament, esgotament, orientació i calendari;
- registrats els descansos dins del diari persistent de l'expedició;
- creat el flux automàtic d'encounter a combat amb adversaris SRD i iniciativa;
- sincronitzat l'estat resolt de l'encounter en finalitzar o reobrir el combat;
- reorganitzats els controls avançats en blocs plegables, resums visuals i accions contextuals;
- creat un menú de configuració per activar o ocultar tots els mòduls i generadors;
- afegits mode essencial, mode compacte, panell contextual opcional, text ampliat i reducció d'animacions;
- desades les preferències exclusivament al navegador, amb restauració dels valors inicials;
- ampliades API, proves i documentació, i actualitzada la versió a `0.7.0`.

Motiu: reduir feina repetitiva durant la sessió i mantenir còmodes les pantalles amb molta informació.

## 2026-08-14 14:26 — Player View, hexcrawl modular i combat avançat

Hora: 14:26, Europe/Madrid.

Canvi fet:

- creada una pantalla de jugadors independent amb endpoint filtrat i actualització automàtica;
- afegida configuració de mapa, rumors, recursos, clima, combat i PG enemics compartits;
- implementats clima, navegació, menjar, aigua, fatiga, foratge, encounters i descobriment com a regles activables;
- creat el motor de rutes axials i dies de viatge amb ritme, tirades manuals o automàtiques, consum i diari;
- connectada la generació automàtica d'encounters contextuals durant el viatge;
- ampliat el combat amb PG temporals, bonus d'iniciativa, concentració, reaccions, accions llegendàries i notes;
- afegits cercador de monstres SRD, quantitats, duplicació, tirades d'iniciativa, notació de daus i historial;
- ampliades migracions SQLite, exportació/importació, API, proves, responsive i documentació.

Motiu: permetre adaptar la complexitat a cada sessió, oferir una pantalla segura als jugadors i fer que exploració i combat funcionin com fluxos complets.

## 2026-08-14 13:59 — Coneixement, hexcrawl i combat

Hora: 13:59, Europe/Madrid.

Canvi fet:

- separada la informació canònica en capes `DM only`, coneixement dels jugadors i estat real del món;
- afegit CRUD persistent de lore amb procedència documental i ubicació opcionals;
- implementat un hexcrawl de Chult amb coordenades, descobriment, terreny, cost de viatge, probabilitat d'encounter i notes separades;
- preparat l'enllaç del mapa oficial carregat localment sense distribuir-lo al repositori;
- creat un assistent de combat amb iniciativa, rondes, PG, CA, condicions, accions i procedència;
- afegit un adaptador API que crea enemics amb estadístiques i accions del catàleg SRD local;
- incorporades dades de mostra per a les tres capes, cinc hexàgons i un combat;
- corregida la propagació de rumors perquè una probabilitat del 100% sigui realment garantida;
- ampliats dashboard, exportació/importació, API, frontend responsive, proves i documentació.

Motiu: disposar d'eines completes de preparació i sessió que mantinguin els secrets del DM i permetin incorporar en el futur dades revisades des dels documents locals.

## 2026-08-07 16:58 — Fortuna manual al Reward Engine

Hora: 16:58, Europe/Madrid.

Canvi fet:

- afegides les opcions sense fortuna, tirada d20 automàtica i resultat manual dels jugadors;
- connectada la tirada manual amb el camp `fortune_roll` ja validat i persistent del backend;
- incorporada validació visual de l'interval 1–20;
- mostrada la tirada utilitzada dins del resultat del botí;
- adaptat el nou control a pantalles petites i actualitzada la documentació.

Motiu: permetre que els jugadors facin físicament la tirada de fortuna i que el DM introdueixi el resultat sense perdre el càlcul contextual ni l'historial de la recompensa.

## 2026-08-07 16:36 — Versió 0.4.0-local

Hora: 16:36, Europe/Madrid.

Canvi fet:

- eliminades totes les dependències rígides de la campanya `demo` al frontend;
- incorporats selector, creació, importació i arxiu de múltiples campanyes;
- afegits editors persistents de campanya, grup, localitzacions, faccions i variables del món;
- completat el CRUD backend de localitzacions, faccions, estat del món i taules custom;
- creada una interfície visual per administrar taules homebrew i filtres contextuals;
- descarregat i incorporat un catàleg local de 1.252 entrades de l'SRD 5.1 sota CC-BY-4.0;
- afegida cerca local de 362 objectes màgics, 237 equipaments, 334 monstres i 319 encanteris;
- integrat el catàleg SRD amb els generadors d'encounters i recompenses;
- afegida conversió d'entrades SRD a opcions de taules custom;
- documentada l'atribució a `NOTICE-SRD.md` i creat un importador reproduïble;
- ampliada la suite a 14 proves, amb lint, compilació Python i build TypeScript validats.

Motiu: convertir la vertical slice en una eina multicampanya operable i oferir un corpus ampli de regles i contingut legalment redistribuïble sense dependre d'Internet ni de serveis externs.

## 2026-08-07 14:33 — Versió 0.3.0-local

Hora: 14:33, Europe/Madrid.

Canvi fet:

- incorporada una biblioteca local per PDF, text, Markdown, imatges i mapes;
- afegides extracció per pàgina, fragmentació, checksum, cerca i procedència;
- incorporat coneixement diferenciat amb fets, creences, confiança i font;
- afegida generació automàtica de rumors i propagació idempotent als NPC;
- implementats Encounter Engine i Reward Engine contextuals per terreny, nivell i dificultat;
- afegits controls de terreny, nivell, mida, tipus i slider de dificultat al frontend;
- incorporades taules i entrades custom persistents, editables i exportables;
- ampliats exports amb rumors, coneixement, taules, encounters i recompenses, excloent documents originals.

Motiu: deixar preparat el core de simulació i contingut perquè les taules, regles, mapes i fonts es puguin ampliar sense redissenyar la persistència.

## 2026-08-07 14:03 — Versió 0.2.0-local

Hora: 14:03, Europe/Madrid.

Canvi fet:

- ampliats el domini i l'API amb CRUD de campanyes, localitzacions, faccions i NPC;
- afegides memòries manuals, cerca global i gestió completa de sessions;
- afegida edició de propostes i operació transaccional per desfer canvis;
- implementats exportació/importació JSON, backups SQLite i restauració validada;
- connectades aquestes operacions principals al dashboard sense sobrecarregar-lo;
- afegits launcher de Windows, Docker, lockfile npm i captura real del dashboard;
- compilat el frontend de producció i ampliada la suite a proves d'API.

Motiu: portar el prototip fins a una aplicació local verificable i fàcil de provar abans de connectar cap LLM real o publicar-la.

## 2026-08-07  —  Versió 0.1.0

Hora: Europe/Madrid, sessió de creació inicial.

Canvi fet:

- creada la vertical slice local amb FastAPI, SQLite i React/TypeScript;
- afegides campanya demo, localització, facció, tres NPC, relacions i memòria;
- implementat el flux de proposta, aprovació o descart d'esdeveniments;
- implementada la conversa contextual mitjançant `LLMProvider` amb Mock, Ollama i LM Studio;
- afegits documentació, proves, llicència, `.gitignore` i CI per a GitHub.

Motiu: convertir el document de disseny en un primer projecte executable que validi el flux central abans d'ampliar rumors, encounters, recompenses o serveis cloud.
