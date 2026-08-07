# Encounter i Reward Engine

## Escales

La dificultat utilitza una escala simple i configurable:

1. Fàcil
2. Moderada
3. Mitjana
4. Difícil
5. Mortal

No substitueix el càlcul complet de CR/XP de D&D 5e. El core conserva nivell, mida del grup, terreny, tipus i una DC orientativa perquè les taules futures puguin implementar un perfil de regles més exacte.

## Filtratge de taules

```text
Campanya + kind
→ terreny
→ rang de nivell
→ rang de dificultat
→ tipus sol·licitat
→ selecció ponderada
```

Terrenys inicials: `urban`, `forest`, `jungle`, `dungeon`, `ruins`, `coast`, `river`, `swamp`, `mountain`, `desert` i `other`.

## Catàleg SRD integrat

El motor consulta localment `backend/app/data/srd5e_2014.json`, sense fer peticions durant la partida:

- un encounter de combat o mixt rep una proposta de monstre SRD filtrada per CR orientatiu, mida del grup, dificultat i família de criatura coherent amb el terreny;
- una recompensa que contingui el marcador `Consumible apropiat al nivell` es concreta amb un objecte màgic SRD d'una raresa adequada al nivell i la dificultat;
- cada proposta conserva `reference_id`, font i llicència;
- qualsevol fitxa del catàleg es pot afegir manualment a una taula custom des de la UI.

Aquest suport amplia les opcions inicials, però no substitueix un balanceig exhaustiu de CR/XP ni incorpora contingut fora de l'SRD.

## Entrada custom d'example

```json
{
  "terrains": ["jungle", "swamp"],
  "min_level": 3,
  "max_level": 8,
  "min_difficulty": 2,
  "max_difficulty": 5,
  "weight": 4,
  "title": "Santuari cobert per la vegetació",
  "payload": {
    "type": "exploration",
    "description": "Un santuari parcialment enfonsat conserva pistes i un perill latent.",
    "objectives": ["Interpretar les inscripcions"],
    "complications": ["Una facció també busca el lloc"]
  },
  "tags": ["homebrew", "lore"]
}
```

Per a recompenses, `payload` accepta `items` i `narrative`. Els objectes poden portar camps custom addicionals; el motor conserva el JSON sense imposar un catàleg tancat.

## Fortuna

En mode neutral no s'aplica cap modificador. En mode fortuna, una tirada d20 opcional ajusta quantitats i pot afegir una recompensa narrativa. Una tirada baixa redueix el valor dins d'un interval coherent, però mai buida arbitràriament la recompensa.
