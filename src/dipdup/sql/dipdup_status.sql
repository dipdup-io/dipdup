DROP VIEW IF EXISTS dipdup_status;

CREATE VIEW dipdup_status AS

SELECT *
FROM (
    SELECT 'index' as type, name, level, 0 as size, updated_at
    FROM dipdup_index

    UNION ALL

    SELECT 'datasource' as type, name, level, 0 as size, updated_at
    FROM dipdup_head

    UNION ALL

    SELECT 
        'queue' as type, 
        json_each.key as name, 
        0 as level, 
        CAST(json_extract(json_each.value, '$.size') AS INTEGER) as size, 
        dipdup_meta.updated_at
    FROM dipdup_meta, json_each(json_extract(dipdup_meta.value, '$.queues'))
    WHERE dipdup_meta.key = 'dipdup_metrics'

    UNION ALL

    SELECT 
        'cache' as type, 
        json_each.key as name, 
        0 as level, 
        CAST(json_extract(json_each.value, '$.size') AS INTEGER) as size, 
        dipdup_meta.updated_at
    FROM dipdup_meta, json_each(json_extract(dipdup_meta.value, '$.caches'))
    WHERE dipdup_meta.key = 'dipdup_metrics'
) as combined_data;
