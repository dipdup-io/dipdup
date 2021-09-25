-- source of inspiration: https://stackoverflow.com/a/11462481
CREATE OR REPLACE FUNCTION truncate_schema(schema_name VARCHAR) RETURNS void AS $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT
            'DROP SEQUENCE ' || quote_ident(n.nspname) || '.'
                || quote_ident(c.relname) || ' CASCADE;' AS name
        FROM
            pg_catalog.pg_class AS c
        LEFT JOIN
            pg_catalog.pg_namespace AS n
        ON
            n.oid = c.relnamespace
        WHERE
            relkind = 'S' AND
            n.nspname = schema_name AND
            pg_catalog.pg_table_is_visible(c.oid)
    LOOP
        BEGIN
            EXECUTE rec.name;
        EXCEPTION
            WHEN others THEN END;
    END LOOP;

    FOR rec IN SELECT
            'DROP TABLE ' || quote_ident(n.nspname) || '.'
                || quote_ident(c.relname) || ' CASCADE;' AS name
        FROM
            pg_catalog.pg_class AS c
        LEFT JOIN
            pg_catalog.pg_namespace AS n
        ON
            n.oid = c.relnamespace WHERE relkind = 'r' AND
            n.nspname = schema_name AND
            pg_catalog.pg_table_is_visible(c.oid)
    LOOP
        BEGIN
            EXECUTE rec.name;
        EXCEPTION
            WHEN others THEN END;
    END LOOP;

    FOR rec IN SELECT
            'DROP FUNCTION ' || quote_ident(ns.nspname) || '.'
                || quote_ident(proname) || '(' || oidvectortypes(proargtypes)
                || ');' AS name
        FROM
            pg_proc
        INNER JOIN
            pg_namespace ns
        ON
            (pg_proc.pronamespace = ns.oid)
        WHERE
            ns.nspname = schema_name AND
            pg_catalog.pg_function_is_visible(pg_proc.oid)
        ORDER BY
            proname
    LOOP
        BEGIN
            EXECUTE rec.name;
        EXCEPTION
            WHEN others THEN END;
    END LOOP;

    -- BEGIN
    --     CREATE EXTENSION IF NOT EXISTS pgcrypto;
    --     CREATE EXTENSION IF NOT EXISTS timescaledb;
    -- EXCEPTION
    --     WHEN OTHERS THEN
    --         NULL;
    -- END;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;
