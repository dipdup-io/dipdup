CREATE MATERIALIZED VIEW
    quotes_1d
AS

SELECT
    time_bucket('1 day'::INTERVAL, ts) AS bucket,
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

CREATE INDEX quotes_1d_bucket ON quotes_1d(bucket);
CREATE INDEX quotes_1d_token_id ON quotes_1d(token_id);
