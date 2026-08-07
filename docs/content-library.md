# Biblioteca de contingut

## Formats i comportament

| Format | Emmagatzematge | Extracció | Cerca |
|---|---|---|---|
| PDF amb text | Local | Per pàgina | Sí |
| PDF escanejat | Local | Marcat `needs_ocr` | Encara no |
| TXT / Markdown | Local | Per blocs | Sí |
| PNG / JPG / WebP | Local com a mapa/imatge | Sense OCR | No |

Cada fitxer té SHA-256 i no es pot carregar dues vegades dins la mateixa campanya. El nom físic es genera internament i no utilitza rutes proporcionades per l'usuari.

## Procedència

Cada fragment conserva `source_id` i pàgina. Quan un fragment entra al context d'un NPC, la resposta pot explicar quina font s'ha consultat. Els documents no modifiquen automàticament NPC, llocs o estat del món.

## Contingut oficial

`source_type=official` significa que el DM conserva el document per ús local. La carpeta queda fora de Git, Docker i exports JSON. El projecte no incorpora cap document comercial.

## Ampliacions previstes

- OCR local per pàgines escanejades;
- embeddings opcionals i índex semàntic;
- propostes d'entitats amb aprovació del DM;
- marcadors i coordenades sobre mapes;
- control de fragments visibles pels jugadors.

