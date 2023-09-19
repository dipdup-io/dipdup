CREATE MATERIALIZED VIEW
    quotes_1m
AS

SELECT
    time_bucket('1 minute'::INTERVAL, ts) AS bucket,
    token_id,
    candlestick_agg(
        ts,
        price,
        volume
    ) as candlestick
FROM token_price

GROUP BY
    bucket,
    token_id
ORDER BY
    bucket,
    token_id

WITH DATA;

CREATE INDEX quotes_1m_bucket ON quotes_1m(bucket);
CREATE INDEX quotes_1m_token_id ON quotes_1m(token_id);
