# Detection d'anomalies de trafic à l'aide de scenarios simulés

Le simulateur joue des scénarios (normal, pic, bot, panne, changement de comportement). Umami collecte les événements dans PostgreSQL. La couche ML détecte ces situations, et la couche MLOps entraîne, versionne, sert et surveille les modèles, puis les ré-entraîne quand le comportement change.

- Spécification : [cdr/spec.md](cdr/spec.md)
- Diagramme de flux : [cdr/diagramme_de_flux.excalidraw](cdr/diagramme_de_flux.excalidraw)
