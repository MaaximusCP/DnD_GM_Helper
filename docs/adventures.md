# Aventures connectades · v1.4.0

## Flux de joc

El constructor desa una aventura preparada (`draft`). La seqüència és: ganxo → situació opcional → temple opcional → combat opcional → minijoc opcional → resolució. Es pot jugar sense cap combat.

En activar-la passa a `active`. Només hi pot haver una aventura activa per campanya. El DM avança cada pas; en entrar al combat es creen la iniciativa, els enemics de la primera onada i, opcionalment, els personatges actius amb els PG actuals. No es tiren iniciatives automàticament: utilitza l'assistent de combat. Les onades següents conserven el torn en curs i requereixen una acció explícita. Si un enemic entra tard, el DM pot ajustar-li la iniciativa.

Per avançar després d'un combat cal haver activat totes les onades i haver-lo finalitzat a l'assistent. La resolució narrativa confirmada permet tancar-lo i descartar reforços pendents, per fugida, pacte o escena omesa. No concedeix PX ni botí.

Les proves del minijoc accepten d20 natural manual (1–20) o una tirada aleatòria local, modificador −20…+30 i la CD de la fitxa guardada. El resultat compara total i CD; no aplica èxit/fallada automàtics per 20/1 natural. No és un motor universal de minijocs: les rondes, els rols i els efectes particulars queden sota control del DM. Les tirades i notes es conserven dins l'aventura i a la cronologia privada.

## Dificultat de trobada

La implementació segueix les [Basic Rules 2014: Building Combat Encounters](https://www.dndbeyond.com/sources/dnd/basic-rules-2014/building-combat-encounters), consultades el 18-09-2026. Sumen llindars per nivell individual i apliquen el multiplicador de nombre d'enemics i mida del grup. Cada onada es valora separadament. El total de PX base es mostra sense repartir; els PX ajustats només serveixen per estimar dificultat.

Es fan servir les fitxes actives del grup. Si no n'hi ha, s'utilitzen nivell i mida de la configuració de campanya. El pressupost desat és una fotografia del moment de preparació, no canvia retroactivament si el grup puja de nivell. Tots els enemics es consideren rellevants per al multiplicador; el DM pot valorar diferent criatures de poc impacte. Solapar onades, terreny desfavorable o manca de recursos pot canviar molt el risc.

Les [Basic Rules 2014: Using Ability Scores](https://www.dndbeyond.com/sources/dnd/basic-rules-2014/using-ability-scores) sustenten la comparació d20 + modificador contra CD. La interfície no pretén reproduir tot el sistema de regles.

No es barregen llindars de 2014 amb regles de 2024. El [portal oficial SRD](https://www.dndbeyond.com/srd) publica les diferents revisions; el catàleg actual de GM AI continua basat en SRD 5.1. Atribució del catàleg: [NOTICE-SRD.md](../NOTICE-SRD.md). No es descarreguen manuals comercials ni s'extreu contingut restringit.

## Material original

`backend/app/data/adventure_templates.json` conté sis guions originals MIT: El deute de la pluja, L'alba prestada, El riu és testimoni, La processó sense noms, El tractat de l'ambre i El parlament sota les arrels. Inclouen pistes, dilemes, sortides pacífiques i recompenses suggerides. Recombinen recursos del pack original de selva, no aventures comercials. Els rangs de nivell són orientatius.

Els recursos seleccionats s'inclouen com a còpies dins l'aventura: eliminar o actualitzar un pack privat no destrueix la partida preparada. Les plantilles no es desen a la campanya fins que el DM prem «Desar aventura preparada».

## Hexcrawl i privacitat

La ubicació i l'hexàgon han de pertànyer a la campanya. El vincle amb la ubicació és informatiu. El vincle amb l'hex permet trobar l'aventura des del mapa i aplicar una alerta opcional (0 per defecte; límit 5) en activar-la. L'alerta s'aplica una sola vegada, fins i tot si es repeteix la petició. No mou l'expedició ni revela l'hex. Si el grup és en un altre hex, es requereix confirmació remota.

L'aventura, els guions, les tirades i les notes sempre són DM-only. Per compartir una pista, usa les eines existents de coneixement dels jugadors. Els combatents activats sí poden aparèixer segons la configuració de la pantalla pública: revisa els noms abans d'entrar a l'escena de combat.

## Persistència i API

Sense una base paral·lela ni migració destructiva: s'utilitza `campaign_records.kind=adventure`, dades JSON versionades (`schema_version=1`), combats i activitats existents. Creació i transicions fan servir transaccions SQLite `BEGIN IMMEDIATE`. Una fallada reverteix també els combatents i les activitats creats dins l'operació.

`expected_revision` és obligatori en avançar, activar una onada, desar una nota o tirar. Una revisió antiga retorna 409 sense efectes addicionals. La UI bloqueja controls durant l'enviament i recarrega l'estat després d'un conflicte. No es pot modificar ni duplicar una aventura pel CRUD genèric de registres; les actives tampoc es poden eliminar per aquell endpoint.

| Mètode | Ruta | Ús |
|---|---|---|
| GET | `/api/adventures/templates` | Sis guions originals |
| GET | `/api/adventures/resources` | Recursos homebrew i monstres SRD |
| POST | `/api/adventures/budget` | `campaign_id`, `enemy_groups` |
| POST | `/api/adventures` | Desa el pla sense activar-lo |
| GET | `/api/campaign-records?campaign_id=demo&kind=adventure` | Llista plans i estat |
| POST | `/api/adventures/{id}/activate` | `force=false`; repetir és segur |
| POST | `/api/adventures/{id}/advance` | `expected_revision`, `note`, `force` opcional |
| POST | `/api/adventures/{id}/wave` | `expected_revision` |
| POST | `/api/adventures/{id}/note` | `expected_revision`, `note` |
| POST | `/api/adventures/{id}/check` | `expected_revision`, `check_index`, `modifier`, `d20` opcional |

Màxim 12 grups, 20 criatures per grup, 60 per aventura i 5 onades. Exportació/importació conserva IDs, progrés, còpies dels recursos i vincles a combats. Cal importar en una base on no existeixin ja els identificadors, igual que amb la resta de la campanya.

## Validació i límits

`backend/tests/test_adventures.py` cobreix plantilles, pressupostos, activació repetida, privacitat, propietat dels hexàgons, progressió, conflictes, rollback, tirades, límits i exportació/importació. `scripts/check_adventure_ui.py` recorre la interfície real amb una base temporal i Edge ocult; pot regenerar captures amb `--screenshots`.

La v1.4 ofereix una seqüència lineal, sense editar o reordenar plans ja desats, branques condicionals ni repartiment automàtic de botí. Per corregir un pla preparat, crea'n un de nou. Les dades existents no es modifiquen en iniciar l'aplicació. L'app és una eina local sense autenticació multiusuari: no publiquis el servidor directament a Internet.
