CREATE
OR REPLACE VIEW dipdup_heartbeat AS
SELECT
    name,
    CASE
        WHEN updated_at - interval '2 minutes' < NOW() THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM
    dipdup_head;