# Seguretat

## Dades locals

Per defecte, GM AI només escolta a `127.0.0.1`, utilitza SQLite local i funciona amb el proveïdor LLM simulat. No publiquis `.env`, `data/*.db` ni `backups/`; ja estan exclosos per `.gitignore`.

La carpeta `library/` també està exclosa de Git i de la imatge Docker. Els exports JSON no inclouen PDF, imatges ni mapes originals. Abans de compartir un backup complet, comprova els drets de distribució del seu contingut.

Les respostes del LLM no modifiquen directament l'estat. Els canvis passen per una proposta estructurada i una confirmació explícita del DM.

## Restauracions

La restauració només accepta fitxers amb el patró intern de backup, rebutja rutes arbitràries, exigeix `{"confirm":"RESTORE"}` al cos JSON i crea una còpia de seguretat prèvia.

## Informar d'una vulnerabilitat

No obris una incidència pública amb secrets o dades reals de campanya. Contacta privadament amb el mantenidor del repositori i inclou passos mínims de reproducció, impacte i versió afectada.
