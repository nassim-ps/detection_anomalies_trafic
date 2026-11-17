# Socle données + simulateur (étape 1 de la feuille de route) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un `docker compose up` démarre PostgreSQL + Umami + une page web locale ; un simulateur rejoue des scénarios YAML versionnés vers Umami, journalise chaque scénario dans `ml.ground_truth`, et des vues SQL exposent le trafic agrégé par fenêtre.

**Architecture:** Un seul serveur PostgreSQL héberge la base Umami (lue en lecture seule via des vues) et le schéma `ml` (écrit par le pipeline). Le paquet Python `trafic_ml` contient des fonctions pures paramétrées par `start`, `end`, config ; `cli.py` n'est qu'une couche fine. Le simulateur envoie les événements à l'API de collecte d'Umami (`POST /api/send`), jamais directement en base.

**Tech Stack:** Python 3.12 (conteneur) · PostgreSQL 16 · Umami v2 (image `ghcr.io/umami-software/umami:postgresql-latest`, version figée au Task 2) · psycopg 3 · pydantic 2 · PyYAML · numpy · httpx · pytest · docker compose.

**Spec:** [cdr/spec.md](../../../cdr/spec.md)

**Hors périmètre de ce plan** (plans suivants) : plan 2 = features, modèles (référence naïve, statsforecast, Isolation Forest), protocole d'évaluation, MLflow ; plan 3 = conteneur supercronic + Makefile, Evidently, ré-entraînement, Grafana.

## Global Constraints

- Aucune écriture dans les tables d'Umami ; le pipeline lit Umami **uniquement** via les vues de `sql/` (rôle `ml_reader` en `SELECT` seul sur les tables Umami).
- Tout ce que produit le projet va dans le schéma `ml` (rôle `ml_writer`).
- Travailler au niveau session ou agrégat temporel, jamais utilisateur sur plusieurs périodes.
- Configuration externe (`.env` / YAML) : aucune URL, mot de passe, seuil ni identifiant en dur.
- Idempotence par fenêtre : réécrire une fenêtre = `DELETE` de la fenêtre puis `INSERT`, dans une même transaction.
- Scénarios en YAML dans `ml/scenarios/` avec une graine ; même YAML + même graine ⇒ même suite d'événements.
- Simulateur réaliste : cycles jour/nuit, user-agents et référents variés, délais aléatoires.
- Environnement Windows : tout ce qui tourne en continu tourne dans docker compose ; `make` n'est pas requis sur l'hôte.

## Review Focus

1. **Horodatage des événements** : si Umami ignore le champ `timestamp` du payload, tout l'historique simulé tombe « maintenant » et `ml.ground_truth` ne correspond plus aux données → vérifié en Task 6, Step 1 (bloquant).
2. **Sessions écrasées** : toutes les requêtes viennent de la même IP ; sans `X-Forwarded-For` variable, Umami fusionne les visiteurs par user-agent → test `test_visitors_have_distinct_ips` (Task 5).
3. **Bots filtrés par Umami** : Umami rejette les user-agents de robots par défaut ; sans `DISABLE_BOT_CHECK=1` le scénario « bot » disparaît → vérifié en Task 6, Step 1.
4. **Fenêtre rejouée deux fois** : relancer `simulate` sur le même scénario ne doit pas dupliquer `ml.ground_truth` → test `test_replace_window_is_idempotent` (Task 3).
5. **Panne = zéro événement** : une fenêtre vide doit apparaître comme 0 dans les vues, pas comme une ligne absente → test `test_view_fills_empty_buckets` (Task 7).

---

## Structure des fichiers

```
docker-compose.yml            # postgres, umami, web (nginx), sim (python)
.env.example                  # toutes les variables, sans secret réel
web/index.html                # page suivie (script Umami)
ml/
├── pyproject.toml
├── Dockerfile                # image python du simulateur / pipeline
├── cli.py                    # python cli.py <etape> --start --end | --last 1h
├── sql/
│   ├── 00_roles.sql          # rôles ml_reader / ml_writer, schéma ml
│   ├── 10_tables.sql         # ground_truth, runs
│   └── 20_views.sql          # vues sur les tables Umami
├── scenarios/
│   ├── base.yaml             # trafic normal (paramètres communs)
│   └── eval_v1.yaml          # jeu d'évaluation fixe : liste de scénarios + graines
├── src/trafic_ml/
│   ├── config.py             # Settings (.env)
│   ├── db.py                 # connexion, replace_window
│   ├── runs.py               # journal ml.runs
│   └── simulator/
│       ├── scenarios.py      # modèles pydantic + chargement YAML
│       ├── intensity.py      # taux d'événements attendu à l'instant t
│       ├── events.py         # génération déterministe des événements
│       └── umami.py          # envoi vers /api/send
└── tests/
```

---

### Task 1: Paquet Python et configuration

**Files:**
- Create: `ml/pyproject.toml`, `ml/src/trafic_ml/__init__.py`, `ml/src/trafic_ml/config.py`, `.env.example`
- Modify: `.gitignore` (ajouter `.env`, `__pycache__/`, `.venv/`)
- Test: `ml/tests/test_config.py`

**Interfaces:**
- Produces: `Settings` (pydantic-settings) avec `pg_dsn_reader: str`, `pg_dsn_writer: str`, `umami_url: str`, `umami_website_id: str`, `scenarios_dir: Path`; `get_settings() -> Settings`.

- [ ] **Step 1: Write the failing test**

```python
def test_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("PG_DSN_READER", "postgresql://r@h/db")
    monkeypatch.setenv("PG_DSN_WRITER", "postgresql://w@h/db")
    monkeypatch.setenv("UMAMI_URL", "http://umami:3000")
    monkeypatch.setenv("UMAMI_WEBSITE_ID", "00000000-0000-0000-0000-000000000000")
    s = get_settings()
    assert s.pg_dsn_writer == "postgresql://w@h/db"
    assert s.scenarios_dir.name == "scenarios"

def test_settings_missing_var_fails(monkeypatch):
    monkeypatch.delenv("PG_DSN_WRITER", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
```

- [ ] **Step 2: Run** `cd ml && pip install -e .[dev] && pytest tests/test_config.py -v` — Expected: FAIL (import error).
- [ ] **Step 3: Implement** `Settings` / `get_settings()` (pas de cache, pour que les tests lisent l'env). `pyproject.toml` : dépendances de la stack ci-dessus + extra `dev` (pytest). `.env.example` liste les 4 variables + `POSTGRES_PASSWORD`, `UMAMI_APP_SECRET`.
- [ ] **Step 4: Run** `pytest tests/test_config.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(ml): paquet trafic_ml et configuration externe"`

---

### Task 2: docker compose — PostgreSQL, Umami, page web

**Files:**
- Create: `docker-compose.yml`, `web/index.html`, `ml/sql/00_roles.sql`, `ml/Dockerfile`

**Interfaces:**
- Produces: services `postgres` (port hôte 5432), `umami` (3000), `web` (8080), `sim` (image `ml/Dockerfile`, profil `tools`) ; base `umami` ; schéma `ml` ; rôles `ml_reader`, `ml_writer`.

- [ ] **Step 1:** `docker-compose.yml` : `postgres:16` (volume nommé, `ml/sql/` monté sur `/docker-entrypoint-initdb.d`), `umami` avec `DATABASE_URL`, `APP_SECRET`, **`DISABLE_BOT_CHECK=1`**, healthcheck sur `/api/heartbeat`, version d'image figée par tag après le premier `pull` ; `web` = `nginx:alpine` servant `web/`.
- [ ] **Step 2:** `00_roles.sql` crée `ml_reader` / `ml_writer` et `CREATE SCHEMA ml AUTHORIZATION ml_writer`. Les `GRANT SELECT` sur les tables Umami se font dans `20_views.sql` (Task 7), car les tables n'existent qu'après la première migration d'Umami.
- [ ] **Step 3: Run** `docker compose up -d && docker compose ps` — Expected: `postgres`, `umami` et `web` sont `healthy` / `running` ; `http://localhost:3000` affiche la connexion Umami.
- [ ] **Step 4:** Créer le site dans l'interface Umami (domaine `localhost`), reporter son identifiant dans `.env` (`UMAMI_WEBSITE_ID`) et dans le snippet de `web/index.html`. Noter dans le README la version d'Umami utilisée.
- [ ] **Step 5: Commit** `git commit -m "feat(infra): docker compose postgres + umami + page web"`

---

### Task 3: Schéma `ml` et écriture idempotente

**Files:**
- Create: `ml/sql/10_tables.sql`, `ml/src/trafic_ml/db.py`
- Test: `ml/tests/test_db.py` (marqueur `@pytest.mark.db`, nécessite le service `postgres`)

**Interfaces:**
- Consumes: `Settings.pg_dsn_writer`
- Produces:
  - tables `ml.ground_truth(id bigserial, scenario text, seed int, debut timestamptz, fin timestamptz, parametres jsonb)` et `ml.runs(id bigserial, etape text, fenetre_debut timestamptz, fenetre_fin timestamptz, statut text, nb_lignes int, mlflow_run_id text null, horodatage timestamptz default now())`
  - `connect(dsn: str) -> psycopg.Connection`
  - `replace_window(conn, table: str, time_col: str, start: datetime, end: datetime, rows: list[dict]) -> int` : supprime `start <= time_col < end` puis insère `rows`, dans une transaction ; retourne le nombre de lignes insérées.

- [ ] **Step 1: Write the failing tests**

```python
def test_replace_window_is_idempotent(conn):
    rows = [{"scenario": "pic", "seed": 1, "debut": T0, "fin": T0 + H, "parametres": "{}"}]
    replace_window(conn, "ml.ground_truth", "debut", T0, T0 + DAY, rows)
    replace_window(conn, "ml.ground_truth", "debut", T0, T0 + DAY, rows)
    assert count(conn, "ml.ground_truth") == 1

def test_replace_window_keeps_other_windows(conn):
    replace_window(conn, "ml.ground_truth", "debut", T0, T0 + DAY, [row_at(T0)])
    replace_window(conn, "ml.ground_truth", "debut", T0 + DAY, T0 + 2*DAY, [row_at(T0 + DAY)])
    assert count(conn, "ml.ground_truth") == 2

def test_replace_window_rejects_unknown_table(conn):
    with pytest.raises(ValueError):
        replace_window(conn, "public.website_event", "created_at", T0, T0 + DAY, [])
```

- [ ] **Step 2: Run** `pytest -m db tests/test_db.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement.** `replace_window` n'accepte que des tables `ml.*` (liste blanche) — garde-fou contre toute écriture côté Umami ; identifiants via `psycopg.sql.Identifier`. Appliquer `10_tables.sql` (monté dans l'initdb) ; pour un volume existant : `docker compose exec postgres psql -f /docker-entrypoint-initdb.d/10_tables.sql`.
- [ ] **Step 4: Run** `pytest -m db tests/test_db.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(ml): schéma ml et écriture idempotente par fenêtre"`

---

### Task 4: Scénarios YAML et intensité du trafic

**Files:**
- Create: `ml/src/trafic_ml/simulator/scenarios.py`, `ml/src/trafic_ml/simulator/intensity.py`, `ml/scenarios/base.yaml`, `ml/scenarios/eval_v1.yaml`
- Test: `ml/tests/test_scenarios.py`, `ml/tests/test_intensity.py`

**Interfaces:**
- Produces:
  - `Base(volume_moyen: float /h, amplitude_jour_nuit: float 0..1, bruit: float, pages: list[str], referents: list[str])`
  - `Scenario` = union discriminée sur `type` ∈ {`pic`, `bot`, `panne`, `changement`} avec `debut: datetime`, `duree: timedelta` (sauf `changement`, durable) et : `pic.facteur` (3..10), `pic.duree` (15 min..2 h), `bot.part` (0.10..0.50), `panne.duree` (10 min..3 h), `changement.ampleur` + `changement.pages`
  - `Plan(base: Base, seed: int, debut: datetime, fin: datetime, scenarios: list[Scenario])`, `load_plan(path: Path) -> Plan`
  - `intensity(t: datetime, plan: Plan) -> tuple[float, float]` : (taux humain, taux bot) en événements/heure.

- [ ] **Step 1: Write the failing tests**

```python
def test_out_of_range_pic_rejected():
    with pytest.raises(ValidationError):
        load_plan_from_dict({..., "scenarios": [{"type": "pic", "facteur": 20, ...}]})

def test_night_lower_than_day():
    assert intensity(at("03:00"), plan)[0] < intensity(at("15:00"), plan)[0]

def test_pic_multiplies_rate():
    assert intensity(in_pic, plan)[0] == pytest.approx(3 * intensity(same_hour_no_pic, plan_no_pic)[0])

def test_panne_near_zero():
    assert sum(intensity(in_panne, plan)) < 0.05 * intensity(same_hour_no_panne, plan_no_panne)[0]

def test_bot_share():
    h, b = intensity(in_bot, plan)
    assert b / (h + b) == pytest.approx(0.3)

def test_changement_persists_after_end_of_plan_window():
    assert intensity(debut_changement + 10*DAY, plan) != intensity(debut_changement - HOUR, plan)

def test_eval_v1_loads():
    plan = load_plan(SCENARIOS / "eval_v1.yaml")
    assert {s.type for s in plan.scenarios} == {"pic", "bot", "panne", "changement"}
```

- [ ] **Step 2: Run** `pytest tests/test_scenarios.py tests/test_intensity.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement.** Bornes de §4 de la spec dans les validateurs pydantic. Cycle jour/nuit : sinusoïde sur 24 h (minimum vers 4 h) + modulation semaine/week-end. `intensity` ne contient pas d'aléa (le bruit est appliqué en Task 5). `eval_v1.yaml` : 14 jours, un scénario de chaque type, graine fixée.
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(sim): scénarios YAML et modèle d'intensité"`

---

### Task 5: Génération déterministe des événements

**Files:**
- Create: `ml/src/trafic_ml/simulator/events.py`
- Test: `ml/tests/test_events.py`

**Interfaces:**
- Consumes: `Plan`, `intensity`
- Produces: `Event(ts: datetime, url: str, referrer: str, user_agent: str, ip: str, language: str, screen: str, is_bot: bool)` ; `generate(plan: Plan, start: datetime, end: datetime) -> Iterator[Event]` (trié par `ts`).

- [ ] **Step 1: Write the failing tests**

```python
def test_same_seed_same_events():
    assert list(generate(plan, A, B)) == list(generate(plan, A, B))

def test_different_seed_different_events():
    assert list(generate(plan, A, B)) != list(generate(plan.model_copy(update={"seed": 2}), A, B))

def test_counts_follow_intensity():   # sur 7 jours, ±10 %
    ...

def test_visitors_have_distinct_ips():
    humans = [e for e in generate(plan, A, B) if not e.is_bot]
    assert len({e.ip for e in humans}) > 0.5 * len({(e.ip, e.user_agent) for e in humans})

def test_bots_homogeneous_and_regular():
    bots = [e for e in generate(plan_bot, A, B) if e.is_bot]
    assert len({e.user_agent for e in bots}) <= 2
    gaps = np.diff([e.ts.timestamp() for e in bots[:50]])
    assert gaps.std() < 0.2 * gaps.mean()

def test_humans_varied():
    humans = [e for e in generate(plan, A, B) if not e.is_bot]
    assert len({e.user_agent for e in humans}) >= 5 and len({e.referrer for e in humans}) >= 3
```

- [ ] **Step 2: Run** `pytest tests/test_events.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement.** `numpy.random.default_rng(plan.seed)` ; processus de Poisson par pas de 1 min avec taux = `intensity` × bruit log-normal ; un visiteur humain = IP aléatoire (plage privée) + UA tiré d'une liste ≥ 10 + 1 à 6 pages avec délais exponentiels ; bot = 1–2 UA fixes, intervalles quasi constants, pages séquentielles, sans référent.
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(sim): génération déterministe des événements"`

---

### Task 6: Envoi vers Umami, `ml.ground_truth` et commande `simulate`

**Files:**
- Create: `ml/src/trafic_ml/simulator/umami.py`, `ml/cli.py`
- Test: `ml/tests/test_umami.py` (unitaire, httpx mocké) ; `ml/tests/test_simulate_e2e.py` (`@pytest.mark.db`, services lancés)

**Interfaces:**
- Consumes: `Settings`, `generate`, `replace_window`, `Plan`
- Produces:
  - `to_payload(e: Event, website_id: str, hostname: str) -> tuple[dict, dict]` (json, headers : `User-Agent`, `X-Forwarded-For`)
  - `send(events: Iterable[Event], settings: Settings, client: httpx.Client) -> int`
  - `simulate(plan_path: Path, start: datetime, end: datetime, settings: Settings) -> int` : envoie les événements puis `replace_window("ml.ground_truth", "debut", start, end, …)` pour les scénarios dont `debut` ∈ [start, end[
  - CLI : `python cli.py simulate --plan scenarios/eval_v1.yaml --start ... --end ...`

- [ ] **Step 1 (bloquant): vérifier l'horodatage et les bots.** Envoyer à la main un événement avec `payload.timestamp` = il y a 3 jours et un UA `Googlebot`, puis `SELECT created_at, session_id FROM website_event ORDER BY created_at DESC LIMIT 5`. Expected : `created_at` = il y a 3 jours et l'événement Googlebot présent. **Si le timestamp est ignoré, s'arrêter et remonter le problème** : l'historique ne peut alors être produit qu'en temps réel, ce qui change la feuille de route.
- [ ] **Step 2: Write the failing tests**

```python
def test_payload_shape():
    body, headers = to_payload(EVENT, "wid", "localhost")
    assert body["type"] == "event"
    assert body["payload"]["website"] == "wid"
    assert body["payload"]["timestamp"] == int(EVENT.ts.timestamp())
    assert headers["X-Forwarded-For"] == EVENT.ip

def test_send_counts_only_successes(httpx_mock): ...

@pytest.mark.db
def test_simulate_writes_ground_truth_and_events(services):
    simulate(EVAL_V1, D0, D0 + 2*DAY, settings)
    simulate(EVAL_V1, D0, D0 + 2*DAY, settings)   # rejoué
    assert ground_truth_rows(D0, D0 + 2*DAY) == expected_scenarios_in_window
```

- [ ] **Step 3: Run** `pytest tests/test_umami.py -v` — Expected: FAIL.
- [ ] **Step 4: Implement.** `cli.py` : `argparse`, sous-commande `simulate`, `--last 1h` accepté comme alternative à `--start/--end` (helper `parse_window(args) -> tuple[datetime, datetime]`, réutilisé par les étapes des plans suivants). Les événements Umami d'une fenêtre rejouée ne peuvent pas être supprimés (lecture seule) : le README le signale ; on rejoue sur une base neuve (`docker compose down -v`).
- [ ] **Step 5: Run** `pytest tests/test_umami.py -v && pytest -m db tests/test_simulate_e2e.py -v` — Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "feat(sim): envoi vers Umami et journal ml.ground_truth"`

---

### Task 7: Vues de lecture sur Umami

**Files:**
- Create: `ml/sql/20_views.sql`
- Test: `ml/tests/test_views.py` (`@pytest.mark.db`)

**Interfaces:**
- Consumes: tables Umami (noms et colonnes confirmés au Step 1)
- Produces: `ml.v_events` (ts, url_path, referrer_domain, session_id, browser, os, device) et `ml.v_traffic_5m` (bucket timestamptz, pages_vues int, visiteurs int), avec un bucket par 5 min même sans événement.

- [ ] **Step 1:** `docker compose exec postgres psql -U postgres umami -c "\d website_event" -c "\d session"` ; reporter les colonnes réelles dans `20_views.sql` et la version d'Umami en commentaire en tête du fichier.
- [ ] **Step 2: Write the failing tests**

```python
def test_reader_cannot_write_umami(reader_conn):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        reader_conn.execute("DELETE FROM website_event")

def test_view_counts_match_simulation(services):   # après simulate sur 1 jour
    assert sum_pageviews(D0, D0 + DAY) == events_sent_humans_and_bots

def test_view_fills_empty_buckets(services):        # pendant la panne
    assert min_pageviews_during(panne) == 0 and bucket_count(panne) == panne.duree / FIVE_MIN
```

- [ ] **Step 3: Run** `pytest -m db tests/test_views.py -v` — Expected: FAIL.
- [ ] **Step 4: Implement** `20_views.sql` : `GRANT SELECT` sur les tables Umami à `ml_reader` (aucun autre droit), `ml.v_events`, `ml.v_traffic_5m` via `generate_series` + `LEFT JOIN` ; visiteurs = `count(DISTINCT session_id)`.
- [ ] **Step 5: Run** — Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "feat(sql): vues de lecture du trafic Umami"`

---

### Task 8: Journal `ml.runs` et README

**Files:**
- Create: `ml/src/trafic_ml/runs.py`
- Modify: `ml/cli.py`, `README.md`
- Test: `ml/tests/test_runs.py` (`@pytest.mark.db`)

**Interfaces:**
- Consumes: `connect`, `ml.runs`
- Produces: context manager `track_run(conn, etape: str, start: datetime, end: datetime)` qui écrit `statut = 'succes'` + `nb_lignes` (via `run.nb_lignes = …`) ou `statut = 'echec'` si une exception remonte (puis la relance). Utilisé par `simulate` et par toutes les étapes des plans suivants.

- [ ] **Step 1: Write the failing tests**

```python
def test_track_run_success(conn):
    with track_run(conn, "simulate", A, B) as run:
        run.nb_lignes = 42
    assert last_run(conn) == ("simulate", "succes", 42)

def test_track_run_failure_recorded_and_reraised(conn):
    with pytest.raises(RuntimeError):
        with track_run(conn, "simulate", A, B):
            raise RuntimeError("boom")
    assert last_run(conn)[1] == "echec"
```

- [ ] **Step 2: Run** `pytest -m db tests/test_runs.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement** `track_run` et l'utiliser dans la commande `simulate`. README : démarrage (`cp .env.example .env`, `docker compose up -d`, créer le site Umami, `docker compose run --rm sim python cli.py simulate --plan scenarios/eval_v1.yaml --start … --end …`), version d'Umami, rejouer = base neuve.
- [ ] **Step 4: Run** `pytest -v && pytest -m db -v` — Expected: tout PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(ml): journal ml.runs et documentation de démarrage"`
