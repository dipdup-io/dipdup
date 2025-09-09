-- Drops all user-defined objects (views, materialized views, tables, sequences, types, functions, TimescaleDB hypertables/chunks) 
-- in the specified schema. A complete schema wipe without dropping the schema itself. Afair this was implemented for compatibility
-- with some cloud providers.
CREATE OR REPLACE FUNCTION dipdup_wipe(schema_name VARCHAR) RETURNS void AS $$
DECLARE
    rec RECORD;
BEGIN
    -- Drop views
    FOR rec IN
        SELECT 'DROP VIEW IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(viewname) || ' CASCADE;'
        FROM pg_views
        WHERE schemaname = schema_name
    LOOP
        BEGIN
            EXECUTE rec."?column?";
        EXCEPTION WHEN others THEN END;
    END LOOP;

    -- Drop materialized views
    FOR rec IN
        SELECT 'DROP MATERIALIZED VIEW IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(matviewname) || ' CASCADE;'
        FROM pg_matviews
        WHERE schemaname = schema_name
    LOOP
        BEGIN
            EXECUTE rec."?column?";
        EXCEPTION WHEN others THEN END;
    END LOOP;

    -- Drop tables
    FOR rec IN
        SELECT 'DROP TABLE IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(tablename) || ' CASCADE;'
        FROM pg_tables
        WHERE schemaname = schema_name
    LOOP
        BEGIN
            EXECUTE rec."?column?";
        EXCEPTION WHEN others THEN END;
    END LOOP;

    -- Drop sequences
    FOR rec IN
        SELECT 'DROP SEQUENCE IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(sequencename) || ' CASCADE;'
        FROM pg_sequences
        WHERE schemaname = schema_name
    LOOP
        BEGIN
            EXECUTE rec."?column?";
        EXCEPTION WHEN others THEN END;
    END LOOP;

    -- Drop types
    FOR rec IN
        SELECT 'DROP TYPE IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(t.typname) || ' CASCADE;'
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = schema_name AND t.typtype = 'c'
    LOOP
        BEGIN
            EXECUTE rec."?column?";
        EXCEPTION WHEN others THEN END;
    END LOOP;

    -- Drop functions
    FOR rec IN
        SELECT 'DROP FUNCTION IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ') CASCADE;'
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = schema_name
    LOOP
        BEGIN
            EXECUTE rec."?column?";
        EXCEPTION WHEN others THEN END;
    END LOOP;

    -- Drop TimescaleDB hypertables and chunks (if any)
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'hypertable' AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'timescaledb_information')) THEN
        FOR rec IN
            -- Use a very large interval ('10000 years') to ensure all TimescaleDB chunks are dropped, regardless of their age.
            SELECT 'SELECT drop_chunks(interval ''10000 years'', ''' || quote_ident(schema_name) || '.' || quote_ident(table_name) || ''');'
            FROM timescaledb_information.hypertables
            WHERE table_schema = schema_name
        LOOP
            BEGIN
                EXECUTE rec."?column?";
            EXCEPTION WHEN others THEN END;
        END LOOP;
    END IF;

    -- Drop all remaining objects (extensions, etc.) if needed
    -- (Extensions are usually global, not per-schema, so not dropped here)

    RETURN;
END;
$$ LANGUAGE plpgsql;
