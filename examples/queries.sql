-- Analysis over the long-format observation table:
--   observations(series_id, entity_id, observed_at, captured_at, metric,
--                value, unit, source_id, raw_ref, parser_version)
--
-- Every query starts from `latest`, which deduplicates. This source restates:
-- observed_at is the registry's own extract stamp, so a re-capture of an
-- unchanged month repeats the same observed_at with a newer captured_at.
-- Without the dedup you will count the same mine several times.

-- ---------------------------------------------------------------- current state
-- The developed fleet by commodity: what is running, what is idle.
-- Answers on a single capture; everything below needs two or more.
WITH latest AS (
  SELECT entity_id, metric, observed_at, value,
         ROW_NUMBER() OVER (PARTITION BY entity_id, metric, observed_at
                            ORDER BY captured_at DESC) AS rn
  FROM observations
),
site AS (
  SELECT observed_at, entity_id,
         MAX(CASE WHEN metric='stage'     THEN value END) AS stage,
         MAX(CASE WHEN metric='commodity' THEN value END) AS commodity,
         MAX(CASE WHEN metric='site_type' THEN value END) AS site_type
  FROM latest WHERE rn=1 AND entity_id LIKE 'site:%'
  GROUP BY observed_at, entity_id
)
SELECT commodity,
       SUM(CASE WHEN stage='Operating' THEN 1 ELSE 0 END)            AS operating,
       SUM(CASE WHEN stage='Care and Maintenance' THEN 1 ELSE 0 END) AS idle,
       SUM(CASE WHEN stage IN ('Proposed','Under Development') THEN 1 ELSE 0 END) AS pipeline
FROM site
WHERE site_type='Mine' AND observed_at=(SELECT MAX(observed_at) FROM site)
GROUP BY commodity
HAVING operating + idle >= 4
ORDER BY idle*1.0/NULLIF(operating+idle,0) DESC;

-- ---------------------------------------------------------------- transitions
-- Every mine that changed stage, and in which direction. This is the whole
-- point of the repository: the registry overwrites, so this row cannot be
-- reconstructed from any single download.
WITH latest AS (
  SELECT entity_id, metric, observed_at, value,
         ROW_NUMBER() OVER (PARTITION BY entity_id, metric, observed_at
                            ORDER BY captured_at DESC) AS rn
  FROM observations
),
stage AS (
  SELECT entity_id, observed_at, value AS stage
  FROM latest WHERE rn=1 AND metric='stage'
),
moves AS (
  SELECT entity_id, observed_at,
         LAG(stage)       OVER (PARTITION BY entity_id ORDER BY observed_at) AS was,
         stage                                                               AS now,
         LAG(observed_at) OVER (PARTITION BY entity_id ORDER BY observed_at) AS since
  FROM stage
)
SELECT since, observed_at, was, now, COUNT(*) AS mines
FROM moves
WHERE was IS NOT NULL AND was <> now
GROUP BY since, observed_at, was, now
ORDER BY observed_at DESC, mines DESC;

-- ---------------------------------------------------------------- supply response
-- Mothballs against restarts per period, by commodity. A restart is capacity
-- returning in months; a mothball is capacity leaving on the same timescale.
WITH latest AS (
  SELECT entity_id, metric, observed_at, value,
         ROW_NUMBER() OVER (PARTITION BY entity_id, metric, observed_at
                            ORDER BY captured_at DESC) AS rn
  FROM observations
),
s AS (SELECT entity_id, observed_at, value AS stage FROM latest WHERE rn=1 AND metric='stage'),
c AS (SELECT entity_id, observed_at, value AS commodity FROM latest WHERE rn=1 AND metric='commodity'),
moves AS (
  SELECT s.entity_id, s.observed_at, c.commodity,
         LAG(s.stage) OVER (PARTITION BY s.entity_id ORDER BY s.observed_at) AS was,
         s.stage AS now
  FROM s JOIN c ON c.entity_id=s.entity_id AND c.observed_at=s.observed_at
)
SELECT observed_at, commodity,
       SUM(CASE WHEN was='Operating' AND now='Care and Maintenance' THEN 1 ELSE 0 END) AS mothballed,
       SUM(CASE WHEN was='Care and Maintenance' AND now='Operating' THEN 1 ELSE 0 END) AS restarted,
       SUM(CASE WHEN was='Care and Maintenance' AND now='Shut'      THEN 1 ELSE 0 END) AS gave_up
FROM moves WHERE was IS NOT NULL AND was <> now
GROUP BY observed_at, commodity
ORDER BY observed_at DESC, mothballed DESC;

-- ---------------------------------------------------------------- ownership
-- Concentration of live ground over time. Rising top-10 share means
-- consolidation; falling means ground is dispersing.
WITH latest AS (
  SELECT entity_id, metric, observed_at, value,
         ROW_NUMBER() OVER (PARTITION BY entity_id, metric, observed_at
                            ORDER BY captured_at DESC) AS rn
  FROM observations
),
t AS (
  SELECT observed_at, entity_id,
         MAX(CASE WHEN metric='holder' THEN value END) AS holder,
         MAX(CASE WHEN metric='area'   THEN CAST(value AS DOUBLE) END) AS ha
  FROM latest WHERE rn=1 AND entity_id LIKE 'tenement:%'
  GROUP BY observed_at, entity_id
),
by_holder AS (
  SELECT observed_at, holder, SUM(ha) AS ha,
         ROW_NUMBER() OVER (PARTITION BY observed_at ORDER BY SUM(ha) DESC) AS rank
  FROM t WHERE holder IS NOT NULL AND holder <> 'MINISTERIAL'
  GROUP BY observed_at, holder
)
SELECT observed_at,
       COUNT(*)                                                AS holders,
       ROUND(SUM(ha)/1e6, 2)                                   AS million_ha,
       ROUND(100.0*SUM(CASE WHEN rank<=10 THEN ha ELSE 0 END)/SUM(ha), 1) AS top10_pct
FROM by_holder GROUP BY observed_at ORDER BY observed_at;

-- ---------------------------------------------------------------- ground churn
-- Tenements that changed hands. Ownership is overwritten in place, so a
-- transfer leaves no trace in the registry itself.
WITH latest AS (
  SELECT entity_id, metric, observed_at, value,
         ROW_NUMBER() OVER (PARTITION BY entity_id, metric, observed_at
                            ORDER BY captured_at DESC) AS rn
  FROM observations
),
h AS (SELECT entity_id, observed_at, value AS holder FROM latest WHERE rn=1 AND metric='holder'),
moves AS (
  SELECT entity_id, observed_at, holder AS now,
         LAG(holder) OVER (PARTITION BY entity_id ORDER BY observed_at) AS was
  FROM h
)
SELECT observed_at, was, now, COUNT(*) AS tenements
FROM moves WHERE was IS NOT NULL AND was <> now
GROUP BY observed_at, was, now
ORDER BY tenements DESC LIMIT 40;

-- ---------------------------------------------------------------- cadence check
-- Does the registry change often enough to justify the cadence? If most
-- captures show near-zero movement, widen the interval; if many mines move
-- every period, narrow it.
WITH latest AS (
  SELECT entity_id, metric, observed_at, value,
         ROW_NUMBER() OVER (PARTITION BY entity_id, metric, observed_at
                            ORDER BY captured_at DESC) AS rn
  FROM observations
),
v AS (
  SELECT entity_id, metric, observed_at, value,
         LAG(value) OVER (PARTITION BY entity_id, metric ORDER BY observed_at) AS prev
  FROM latest WHERE rn=1
)
SELECT observed_at, metric,
       COUNT(*)                                              AS entities,
       SUM(CASE WHEN prev IS NOT NULL AND prev<>value THEN 1 ELSE 0 END) AS changed
FROM v GROUP BY observed_at, metric ORDER BY observed_at, metric;
