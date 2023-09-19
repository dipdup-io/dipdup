CREATE MATERIALIZED VIEW
    token_price
AS

(
    SELECT
        to_timestamp(timestamp) as ts,
        token0_id as token_id,
        abs(amount_usd/amount0) as price,
        amount_usd as volume
    FROM swap
    WHERE
        amount_usd!=0
    AND
        amount0!=0
) UNION (
    SELECT
        to_timestamp(timestamp) as ts,
        token1_id as token_id,
        abs(amount_usd/amount1) as price,
        amount_usd as volume
    FROM swap
    WHERE
        amount_usd!=0
    AND
        amount1!=0
)

WITH DATA;

CREATE INDEX token_price_ts ON token_price(ts);
CREATE INDEX token_price_token_id ON token_price(token_id);