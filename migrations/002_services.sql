-- Add service catalog and an optional service link for existing care schedules.
-- The application checks whether service_id already exists before applying the
-- ALTER TABLE statement, so existing schedule rows remain unchanged.
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price REAL NOT NULL CHECK (price >= 0),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive'))
);

ALTER TABLE care_schedules
    ADD COLUMN service_id INTEGER REFERENCES services(id) ON DELETE SET NULL;
