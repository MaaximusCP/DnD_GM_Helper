# Packs homebrew locals

## Què incorpora el pack de selva

`backend/app/data/homebrew_jungle.json` conté 34 recursos originals i funciona completament offline:

| Categoria | Quantitat | Aplicació a la campanya |
|---|---:|---|
| Enemics | 8 | Crea combatents amb PG, CA, iniciativa i accions |
| Temples | 8 | Crea una escena planificada amb sales, secrets i recompensa |
| Situacions | 12 | Crea una escena amb opcions, proves i conseqüències |
| Minijocs | 6 | Crea una escena i un clock actiu amb progrés i perill |

La pantalla permet cercar i filtrar per terreny, nivell i dificultat. `Sorprèn-me` utilitza aleatorietat del navegador només sobre els resultats visibles.

## Eines de la versió 1.3

- **Compondre expedició** escull una peça compatible de cada categoria. El DM pot regenerar el conjunt o desar-lo com una escena del planificador.
- **Pressupost XP** calcula XP ajustats per quantitat d'enemics i adapta el multiplicador si el grup té menys de 3 o almenys 6 personatges.
- **Favorits** es desen al navegador per campanya i es poden usar com a filtre.
- **URLs profundes** conserven categoria i recurs, per exemple `?view=homebrew&brew=temple&item=hb:jungle:temple:seven-drips`.
- **Packs locals** permet importar i eliminar col·leccions JSON sense reiniciar el backend.

## Minijocs

Cada minijoc defineix:

- `target`: èxits necessaris per completar-lo;
- `danger_max`: fallades abans d'un desenllaç negatiu;
- `round_limit`: pressió temporal màxima;
- `checks`: proves alternatives amb habilitat i CD;
- `twists`, `success` i `failure`: eines narratives per al DM.

En preparar-lo, l'aplicació crea un `clock` actiu i una `scene` vinculada. Cada tirada usa la safata persistent, suma progrés o perill i deixa una entrada a l'activitat de campanya. El DM conserva el control del modificador i de la prova escollida.

## Fonts de calibratge

Les CD segueixen l'escala general de les Basic Rules (de molt fàcil a gairebé impossible). El terreny difícil, el ritme, les tirades de navegació i l'ajust d'encontres segueixen els principis públics de les regles bàsiques:

- https://www.dndbeyond.com/sources/dnd/basic-rules-2014/using-ability-scores
- https://www.dndbeyond.com/sources/dnd/basic-rules-2014/adventuring
- https://www.dndbeyond.com/sources/dnd/basic-rules-2014/building-combat-encounters
- https://www.dndbeyond.com/sources/dnd/basic-rules-2014/running-the-game

Les xifres dels enemics són orientatives: abans d'una sessió real convé contrastar-les amb la composició i els recursos actuals del grup.

L'estimador aplica els quatre llindars XP per nivell, suma el pressupost del grup i ajusta l'XP dels monstres amb el multiplicador per nombre d'enemics. És una ajuda de preparació, no una garantia: terreny, sorpresa, recursos gastats i sinergies poden canviar molt la dificultat real.

## Afegir recursos

Cada entrada comparteix aquesta base:

```json
{
  "id": "hb:biome:category:slug",
  "category": "enemy",
  "name": "Nom únic",
  "summary": "Descripció curta",
  "terrains": ["jungle", "ruins"],
  "min_level": 1,
  "max_level": 5,
  "difficulty": 2,
  "tags": ["plant", "ambush"],
  "data": {}
}
```

Els identificadors han de ser únics, els nivells han d'estar entre 1 i 20 i la dificultat entre 1 i 5. `data` depèn de la categoria; les entrades actuals són exemples complets del contracte.

## Importar un pack privat

1. Crea un JSON amb `format_version`, `id`, `name`, `version`, `license` i `items`.
2. Obre `Gestionar packs locals` al Laboratori.
3. Selecciona el fitxer i prem `Validar i importar`.

El backend rebutja fitxers de més d'1 MB, JSON mal formatat, IDs de pack o recurs duplicats, categories desconegudes, nivells fora d'1–20, dificultats fora d'1–5 i recomptes incorrectes. L'escriptura és atòmica i el pack inclòs no es pot eliminar.

Els packs privats es desen a `data/homebrew_packs/`, una ruta ignorada per Git. Les escenes, clocks o combatents que ja hagis aplicat a la campanya continuen existint encara que eliminis el pack d'origen.

Estructura superior mínima:

```json
{
  "format_version": 1,
  "id": "el-meu-pack",
  "name": "El meu pack",
  "version": "1.0.0",
  "license": "Ús privat",
  "items": []
}
```

Substitueix `items` per una o més entrades amb el contracte de l'apartat anterior; un pack buit es rebutja expressament.
