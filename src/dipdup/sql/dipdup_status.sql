DROP VIEW IF EXISTS dipdup_head_status;

CREATE OR REPLACE VIEW dipdup_status AS
SELECT *
FROM (
    SELECT 'index' as type, name, level, 0 as size, updated_at
    FROM dipdup_index

    UNION ALL

    SELECT 'datasource' as type, name, level, 0 as size, updated_at
    FROM dipdup_head

    UNION ALL

    SELECT 'queue' as type, queue_key as name, 0 as level, queue_size as size, updated_at
    FROM (
        SELECT
            queue_key,
            (value::jsonb -> 'queues' -> queue_key ->> 'size')::numeric as queue_size,
            updated_at
        FROM dipdup_meta,
        jsonb_object_keys(value::jsonb -> 'queues') as queue_key
        WHERE dipdup_meta.key = 'dipdup_metrics'
    ) as queue_subquery

    UNION ALL

    SELECT 'cache' as type, cache_key as name, 0 as level, cache_size as size, updated_at
    FROM (
        SELECT
            cache_key,
            (value::jsonb -> 'caches' -> cache_key ->> 'size')::numeric as cache_size,
            updated_at
        FROM dipdup_meta,
        jsonb_object_keys(value::jsonb -> 'caches') as cache_key
        WHERE dipdup_meta.key = 'dipdup_metrics'
    ) as cache_subquery
) as combined_data;
