CREATE TABLE IF NOT EXISTS market_day (
  id BIGSERIAL PRIMARY KEY,
  market TEXT NOT NULL CHECK (market IN ('DAM','GDAM','RTM')),
  trade_date DATE NOT NULL,
  UNIQUE (market, trade_date)
);

CREATE TABLE IF NOT EXISTS dam_price (
  id BIGSERIAL PRIMARY KEY,
  market_day_id BIGINT NOT NULL REFERENCES market_day(id) ON DELETE CASCADE,
  hour_block SMALLINT NOT NULL CHECK (hour_block BETWEEN 0 AND 23),
  mcp_rs_per_mwh NUMERIC(10,2) NOT NULL,
  CONSTRAINT dam_uniq UNIQUE (market_day_id, hour_block)
);

CREATE INDEX IF NOT EXISTS idx_dam_mday_hour ON dam_price(market_day_id, hour_block);

CREATE TABLE IF NOT EXISTS gdam_price (
  id BIGSERIAL PRIMARY KEY,
  market_day_id BIGINT NOT NULL REFERENCES market_day(id) ON DELETE CASCADE,
  quarter_index SMALLINT NOT NULL CHECK (quarter_index BETWEEN 0 AND 95),
  mcp_rs_per_mwh NUMERIC(10,2) NOT NULL,
  hydro_fsv_mw NUMERIC(12,2),
  scheduled_volume_mw NUMERIC(12,2),
  CONSTRAINT gdam_uniq UNIQUE (market_day_id, quarter_index)
);

CREATE INDEX IF NOT EXISTS idx_gdam_mday_q ON gdam_price(market_day_id, quarter_index);

CREATE TABLE IF NOT EXISTS rtm_price (
  id BIGSERIAL PRIMARY KEY,
  market_day_id BIGINT NOT NULL REFERENCES market_day(id) ON DELETE CASCADE,
  hour SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
  session_id SMALLINT,
  quarter_index SMALLINT NOT NULL CHECK (quarter_index BETWEEN 0 AND 95),
  mcv_mw NUMERIC(12,2),
  fsv_mw NUMERIC(12,2),
  mcp_rs_per_mwh NUMERIC(10,2) NOT NULL,
  CONSTRAINT rtm_uniq UNIQUE (market_day_id, quarter_index)
);

CREATE INDEX IF NOT EXISTS idx_rtm_mday_q ON rtm_price(market_day_id, quarter_index);

CREATE TABLE IF NOT EXISTS market_summary (
  id BIGSERIAL PRIMARY KEY,
  market_day_id BIGINT NOT NULL REFERENCES market_day(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  value NUMERIC(12,4) NOT NULL,
  UNIQUE (market_day_id, label)
);

CREATE ROLE IF NOT EXISTS power_reader LOGIN PASSWORD 'power_reader';
GRANT CONNECT ON DATABASE power_exchange TO power_reader;
GRANT USAGE ON SCHEMA public TO power_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO power_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO power_reader;
