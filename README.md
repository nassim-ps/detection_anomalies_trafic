# Detection d'anomalies de trafic à l'aide de scenarios simulés

Le simulateur joue des scénarios (normal, pic, bot, panne, changement de comportement). Plausible et ClickHouse collectent les événements. La couche ML détecte ces situations, et la couche MLOps entraîne, versionne, sert et surveille les modèles, puis les ré-entraîne quand le comportement change.