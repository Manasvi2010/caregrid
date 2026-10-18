CREATE TABLE IF NOT EXISTS occupancy_snapshots (
  id SERIAL PRIMARY KEY,
  ward_id INT NOT NULL REFERENCES wards(id),
  taken_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  occupied_count INT NOT NULL,
  total INT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_ward_time
  ON occupancy_snapshots (ward_id, taken_at);