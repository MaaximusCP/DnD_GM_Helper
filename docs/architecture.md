# Arquitectura de la vertical slice

## Principis

1. SQLite conserva la veritat del món.
2. El LLM interpreta un NPC, però no pot escriure directament a la base de dades.
3. Qualsevol conseqüència sensible comença en estat `pending`.
4. La campanya és contingut substituïble; el motor no codifica cap aventura publicada.
5. La UI continua sent navegable si no hi ha un LLM actiu.
6. Els documents originals no es confonen amb l'estat viu de la campanya.
7. Encounters i recompenses es generen des de taules filtrades, no des de text lliure del LLM.
8. Els NPC actius només creen propostes; el DM continua sent l'únic que pot aplicar conseqüències.
9. Un fragment documental no esdevé canònic fins que el DM el revisa i l'aprova.
10. Les utilitats deterministes de sessió, com els daus, no depenen del LLM i en conserven l'historial per campanya.
11. El catàleg SRD, els documents privats i els packs homebrew són capes separades amb origen i llicència visibles.
12. Cap pack importat entra al catàleg fins que supera validació estructural, rangs, recomptes i unicitat d'identificadors.

## Flux d'un esdeveniment

```text
Text del DM
   │
   ▼
EventService.analyze
   │
   ├── desa EventProposal(status=pending)
   └── no modifica el món
            │
            ▼
       Revisió del DM
       │           │
    aplicar      ignorar
       │           │
       ▼           ▼
transacció SQL   conserva registre
```

L'analitzador 0.1 és deliberadament conservador i determinista. Reconeix patrons bàsics (ajuda, robatori, conflicte i suborn); la integració del GM Agent amb sortida estructurada pertany a la fase 0.3.

## Flux d'una conversa

`ContextBuilder` combina personalitat, objectius, relació, localització, estat del món i un màxim de cinc memòries. `LLMProvider` envia aquest context al proveïdor escollit. Els adapters d'Ollama i LM Studio queden a infraestructura; el domini no en depèn.

## Persistència

La inicialització és idempotent: crea les taules que falten i només insereix les dades demo quan no existeix cap campanya. Les operacions d'aplicació utilitzen una transacció SQLite i limiten les relacions a l'interval `[-100, 100]`.

## Capes de coneixement

```text
Biblioteca immutable → fragments amb font i pàgina
Dades canòniques     → NPC, llocs, faccions i taules aprovades
Estat viu            → sessions, esdeveniments i reputació
Coneixement NPC      → fets, creences i rumors amb confiança pròpia
```

Un rumor mai es converteix automàticament en una veritat del món. En propagar-lo es crea una entrada `belief` independent per a cada NPC que l'ha après.

## Motors de generació

`GenerationService` resol el terreny a partir del valor forçat pel DM o de la localització. Després filtra les entrades per campanya, tipus de taula, terreny, nivell i dificultat, i aplica el pes configurat. La selecció i els motius queden persistits per poder auditar el resultat.

## Aventures i trobades mixtes (1.4)

`AdventureService` conserva plans versionats dins `campaign_records` amb tipus `adventure`. Valida els vincles de campanya i desa còpies dels recursos seleccionats. Cada transició, activitat i canvi de combat s'executa en una sola transacció `BEGIN IMMEDIATE`; una revisió esperada evita executar dues vegades la mateixa acció. Els combats es creen quan s'arriba a l'escena, no en preparar el pla. Les onades s'activen separadament sense canviar qui té el torn actual.

El pressupost es calcula al servidor amb llindars 2014 i nivells individuals. `AdventureStudio` separa preparació i direcció de sessió, amb controls avançats plegables. El tipus `adventure` no s'exporta a la vista dels jugadors. Les aventures sí viatgen dins l'exportació privada de campanya, amb el seu progrés i els vincles a combats. Vegeu [el contracte i els límits](adventures.md).
