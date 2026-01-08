-- Drops all user-defined objects in the specified schema. A complete schema wipe without dropping the schema itself.
-- Affects views, materialized views, tables (including hypertables), sequences, composite types, functions, and procedures. 
-- This functionality was implemented for compatibility with some cloud provider I can't remember, who doesn't allow dropping schemas directly.
CREATE OR REPLACE FUNCTION dipdup_wipe(schema_name VARCHAR) RETURNS void AS $$
DECLARE
    rec RECORD;
BEGIN
    -- Drop views
    FOR rec IN
        SELECT format('DROP VIEW IF EXISTS %I.%I CASCADE', schema_name, viewname) AS stmt
        FROM pg_views WHERE schemaname = schema_name
    LOOP
        EXECUTE rec.stmt;
    END LOOP;

    -- Drop materialized views
    FOR rec IN
        SELECT format('DROP MATERIALIZED VIEW IF EXISTS %I.%I CASCADE', schema_name, matviewname) AS stmt
        FROM pg_matviews WHERE schemaname = schema_name
    LOOP
        EXECUTE rec.stmt;
    END LOOP;

    -- Drop tables (includes hypertables; CASCADE handles chunks automatically)
    FOR rec IN
        SELECT format('DROP TABLE IF EXISTS %I.%I CASCADE', schema_name, tablename) AS stmt
        FROM pg_tables WHERE schemaname = schema_name
    LOOP
        EXECUTE rec.stmt;
    END LOOP;

    -- Drop sequences
    FOR rec IN
        SELECT format('DROP SEQUENCE IF EXISTS %I.%I CASCADE', schema_name, sequencename) AS stmt
        FROM pg_sequences WHERE schemaname = schema_name
    LOOP
        EXECUTE rec.stmt;
    END LOOP;

    -- Drop composite types (excluding extension-owned)
    FOR rec IN
        SELECT format('DROP TYPE IF EXISTS %I.%I CASCADE', schema_name, t.typname) AS stmt
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = schema_name 
        AND t.typtype = 'c'
        AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            WHERE d.classid = 'pg_type'::regclass
            AND d.objid = t.oid
            AND d.deptype = 'e'
        )
    LOOP
        EXECUTE rec.stmt;
    END LOOP;


    -- Drop functions and procedures (excluding extension-owned)
    FOR rec IN
        SELECT format('DROP ROUTINE IF EXISTS %I.%I(%s) CASCADE', 
                    schema_name, p.proname, pg_get_function_identity_arguments(p.oid)) AS stmt
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = schema_name
        AND p.prokind IN ('f', 'p')
        AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            WHERE d.classid = 'pg_proc'::regclass
            AND d.objid = p.oid
            AND d.deptype = 'e'
        )
    LOOP
        EXECUTE rec.stmt;
    END LOOP;


END;
$$ LANGUAGE plpgsql;
