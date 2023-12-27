CREATE OR REPLACE FUNCTION dipdup_approve(schema_name VARCHAR) RETURNS void AS $$
BEGIN
    UPDATE dipdup_index SET config_hash = null;
    UPDATE dipdup_schema SET reindex = null, hash = null;
    UPDATE dipdup_head SET hash = null;
    RETURN;
END;
$$ LANGUAGE plpgsql;
