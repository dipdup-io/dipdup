CREATE OR REPLACE PROCEDURE trade_summary()
LANGUAGE 'plpgsql'
AS $$
    BEGIN

        DROP TABLE IF EXISTS trade_24h;
        DROP TABLE IF EXISTS trade_7d;
        DROP TABLE IF EXISTS trade_1m;

        CREATE TEMP TABLE trade_24h AS
            SELECT
                t.symbol_id AS symbol,
                sum(t.quantity) AS token_total_24h,
                sum(t.quantity * t.price) AS xtz_total_24h
            FROM trade t
            WHERE t.timestamp > NOW() - INTERVAL '24 hour'
            GROUP BY symbol;

        CREATE TEMP TABLE trade_7d AS
            SELECT
                t.symbol_id AS symbol,
                sum(t.quantity) AS token_total_7d,
                sum(t.quantity * t.price) AS xtz_total_7d
            FROM trade t
            WHERE t.timestamp > NOW() - INTERVAL '7 day'
            GROUP BY symbol;

        CREATE TEMP TABLE trade_1m AS
            SELECT
                t.symbol_id AS symbol,
                sum(t.quantity) AS token_total_1m,
                sum(t.quantity * t.price) AS xtz_total_1m
            FROM trade t
            WHERE t.timestamp > NOW() - INTERVAL '1 month'
            GROUP BY symbol;

        DROP TABLE IF EXISTS trade_total;
        CREATE TABLE trade_total AS
            SELECT
                trade_1m.symbol AS symbol,
                trade_24h.token_total_24h,
                trade_24h.xtz_total_24h,
                trade_7d.token_total_7d,
                trade_7d.xtz_total_7d,
                trade_1m.token_total_1m,
                trade_1m.xtz_total_1m,
                NOW() as updated_at
            FROM trade_1m
            JOIN trade_7d ON trade_1m.symbol = trade_7d.symbol
            JOIN trade_24h ON trade_24h.symbol = trade_1m.symbol;
    END;
$$;