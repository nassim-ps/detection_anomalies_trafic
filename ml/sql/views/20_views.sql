-- Vues de lecture sur les tables Umami (schéma vérifié sur Umami 3.5.0).
-- À appliquer APRÈS le premier démarrage d'Umami (ses tables doivent exister) :
--   docker compose exec -T postgres psql -U postgres umami -f /docker-entrypoint-initdb.d/views/20_views.sql
-- Le pipeline ne lit Umami QUE via ces vues.

GRANT USAGE ON SCHEMA public TO ml_reader;
GRANT SELECT ON public.website_event, public.session TO ml_reader;

SET ROLE ml_writer;

-- Pages vues (event_type = 1), une ligne par événement.
CREATE OR REPLACE VIEW ml.v_events AS
SELECT e.website_id,
       e.created_at        AS ts,
       e.url_path,
       e.referrer_domain,
       e.session_id,
       s.browser,
       s.os,
       s.device
FROM public.website_event e
JOIN public.session s USING (session_id)
WHERE e.event_type = 1;

-- Trafic par tranche de 5 min, une ligne par tranche même sans événement.
CREATE OR REPLACE VIEW ml.v_traffic_5m AS
WITH bornes AS (
    SELECT website_id,
           date_bin('5 minutes', min(created_at), timestamptz '2000-01-01') AS t0,
           date_bin('5 minutes', max(created_at), timestamptz '2000-01-01') AS t1
    FROM public.website_event
    WHERE event_type = 1
    GROUP BY website_id
),
grille AS (
    SELECT b.website_id, g.bucket
    FROM bornes b,
         generate_series(b.t0, b.t1, interval '5 minutes') AS g(bucket)
),
agg AS (
    SELECT website_id,
           date_bin('5 minutes', created_at, timestamptz '2000-01-01') AS bucket,
           count(*)                   AS pages_vues,
           count(DISTINCT session_id) AS visiteurs
    FROM public.website_event
    WHERE event_type = 1
    GROUP BY 1, 2
)
SELECT g.website_id,
       g.bucket,
       coalesce(a.pages_vues, 0)::int AS pages_vues,
       coalesce(a.visiteurs, 0)::int  AS visiteurs
FROM grille g
LEFT JOIN agg a USING (website_id, bucket);

RESET ROLE;
