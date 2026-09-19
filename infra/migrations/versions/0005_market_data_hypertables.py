"""Require the verified PG16/Timescale 2.28.1 observation storage profile."""

from alembic import op

revision = "0005_market_data_hypertables"
down_revision = "0004_market_data_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF current_setting('server_version_num')::integer NOT BETWEEN 160000 AND 169999 THEN
       RAISE EXCEPTION 'S4 requires PostgreSQL 16'; END IF;
      IF EXISTS(SELECT FROM price_daily) OR EXISTS(SELECT FROM macro_observations) THEN
       RAISE EXCEPTION 'S4 hypertable conversion requires empty observation tables; use an explicit data migration'; END IF;
    END $$;
    CREATE EXTENSION IF NOT EXISTS timescaledb;
    DO $$ BEGIN
      IF (SELECT extversion FROM pg_extension WHERE extname='timescaledb') IS DISTINCT FROM '2.28.1' THEN
       RAISE EXCEPTION 'S4 requires the verified TimescaleDB 2.28.1 runtime'; END IF;
    END $$;
    SELECT create_hypertable('price_daily',by_range('session_date',INTERVAL '1 year'),create_default_indexes=>false);
    SELECT create_hypertable('macro_observations',by_range('reference_date',INTERVAL '1 year'),create_default_indexes=>false);
    DO $$ BEGIN
      IF (SELECT count(*) FROM timescaledb_information.hypertables
          WHERE hypertable_schema='public' AND hypertable_name IN ('price_daily','macro_observations'))<>2 THEN
       RAISE EXCEPTION 'required S4 hypertables were not created'; END IF;
    END $$;
    """)


def downgrade() -> None:
    # Empty-only conversion: retain every column/constraint/index/grant/trigger.
    # Saved S4 evidence is never discarded to make an environment downgrade work.
    op.execute(r"""
    DO $$
    DECLARE tab text; old_name text; f record; constraints text[]; triggers text[]; definition text;
    BEGIN
      IF EXISTS(SELECT FROM price_daily) OR EXISTS(SELECT FROM macro_observations) THEN
       RAISE EXCEPTION 'refusing to discard S4 observations during downgrade' USING ERRCODE='55000'; END IF;
      FOREACH tab IN ARRAY ARRAY['price_daily','macro_observations'] LOOP
       old_name:=tab||'_s4_downgrade';
       SELECT array_agg(pg_get_constraintdef(oid)) INTO constraints FROM pg_constraint
        WHERE conrelid=tab::regclass AND contype='f';
       SELECT array_agg(pg_get_triggerdef(oid)) INTO triggers FROM pg_trigger
        WHERE tgrelid=tab::regclass AND NOT tgisinternal AND tgname<>'ts_insert_blocker';
       EXECUTE format('ALTER TABLE %I RENAME TO %I',tab,old_name);
       EXECUTE format('CREATE TABLE %I (LIKE %I INCLUDING ALL)',tab,old_name);
       -- No incoming production references exist at this migration boundary.
       EXECUTE format('DROP TABLE %I',old_name);
       FOREACH definition IN ARRAY coalesce(constraints,ARRAY[]::text[]) LOOP
        EXECUTE format('ALTER TABLE %I ADD %s',tab,definition);
       END LOOP;
       FOREACH definition IN ARRAY coalesce(triggers,ARRAY[]::text[]) LOOP EXECUTE definition; END LOOP;
       EXECUTE format('REVOKE ALL ON %I FROM PUBLIC,equity_runtime',tab);
       EXECUTE format('GRANT SELECT ON %I TO equity_runtime',tab);
      END LOOP;
    END $$;
    """)
