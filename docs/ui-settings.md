# Configuració de la interfície

El botó de controls de la capçalera obre un panell lateral de preferències. Els canvis s'apliquen immediatament i es desen a `localStorage` amb la clau `gm-ai-ui-preferences-v1`.

## Visibilitat

Es poden mostrar o ocultar independentment Eines de taula, Món, Pantalla de jugadors, Coneixement, Hexcrawl, Combat, Faccions, Biblioteca, Catàleg SRD, Taules custom, Encounter Engine i Reward Engine.

La vista **Sessió** sempre es manté activa perquè el DM no es pugui quedar sense navegació. Si s'oculta el mòdul que estava obert, l'aplicació torna automàticament a Sessió. Ocultar un mòdul no elimina cap dada ni desactiva els seus endpoints.

Les accions ràpides disponibles són:

- `Mostrar-ho tot`, que recupera el menú complet;
- `Mode essencial`, que conserva Sessió, Món, Hexcrawl i Combat;
- `Restaurar configuració inicial`, que restableix totes les preferències.

## Aparença i accessibilitat

- **Interfície compacta**: redueix marges i espais del dashboard.
- **Panell de context**: mostra o amaga la columna d'ubicació, grup, rumors i eines ràpides.
- **Text ampliat**: augmenta la mida base del text.
- **Reduir animacions**: minimitza transicions i moviment.

Aquestes preferències pertanyen al navegador i al dispositiu, no a una campanya. Per això no entren als exports JSON ni es comparteixen amb la pantalla dels jugadors.
