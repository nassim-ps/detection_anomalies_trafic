-- Vues de lecture sur les tables Umami (schéma vérifié sur Umami 3.5.0).
-- Appliquées par sql/init.sh après le démarrage d'Umami (ses tables doivent exister).
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

-- Trafic par tranche de 5 min sur [debut, fin[ : une ligne par tranche, même sans événement
-- (y compris avant le premier et après le dernier événement : une panne en cours apparaît à 0).
DROP VIEW IF EXISTS ml.v_traffic_5m;
CREATE OR REPLACE FUNCTION ml.traffic_5m(site uuid, debut timestamptz, fin timestamptz)
RETURNS TABLE (bucket timestamptz, pages_vues int, visiteurs int)
LANGUAGE sql STABLE AS $$
    WITH grille AS (
        SELECT g AS bucket
        FROM generate_series(date_bin('5 minutes', debut, timestamptz '2000-01-01'),
                             fin - interval '1 microsecond', interval '5 minutes') g
    ),
    agg AS (
        SELECT date_bin('5 minutes', created_at, timestamptz '2000-01-01') AS bucket,
               count(*) AS n, count(DISTINCT session_id) AS v
        FROM public.website_event
        WHERE website_id = site AND event_type = 1
          AND created_at >= debut AND created_at < fin
        GROUP BY 1
    )
    SELECT g.bucket, coalesce(a.n, 0)::int, coalesce(a.v, 0)::int
    FROM grille g LEFT JOIN agg a USING (bucket)
    ORDER BY g.bucket
$$;
GRANT EXECUTE ON FUNCTION ml.traffic_5m(uuid, timestamptz, timestamptz) TO ml_reader;

RESET ROLE;
