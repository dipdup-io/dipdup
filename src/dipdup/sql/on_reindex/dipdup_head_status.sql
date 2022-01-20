CREATE
OR REPLACE VIEW dipdup_head_status AS
SELECT
    name,
    CASE
        WHEN timestamp - interval '2 minutes' < NOW() THEN 'OK'
        ELSE 'OUTDATED'
    END AS status
FROM
    dipdup_head;