-- SCRUM-9: Add city column to events table for city-based campaigns
ALTER TABLE events ADD COLUMN IF NOT EXISTS city VARCHAR(100);
CREATE INDEX IF NOT EXISTS idx_events_city ON events(city);
