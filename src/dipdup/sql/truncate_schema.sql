-- TODO: Alias, remove in 8.0
CREATE OR REPLACE FUNCTION truncate_schema(schema_name VARCHAR) RETURNS void AS $$
BEGIN
    SELECT dipdup_wipe(schema_name);
    RETURN;
END;
$$ LANGUAGE plpgsql;
