CREATE
OR REPLACE VIEW dipdup_head_status AS
SELECT
    name,
    CASE
        WHEN timestamp < NOW() - interval '2 minutes' THEN 'OUTDATED'
        ELSE 'OK'
    END AS status
FROM
    dipdup_head;