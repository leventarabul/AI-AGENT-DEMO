# Database Migrations

SQL migration files for the demo-domain campaign system.

## Naming Convention

```
SCRUM-{ticket_number}_{description}.sql
```

## How Migrations Run

Migrations are executed automatically on container startup
via `run_migrations.py`. Each migration runs only once
(tracked in the `schema_migrations` table).

## Example

```sql
-- SCRUM-9: Add city column to events table
ALTER TABLE events ADD COLUMN IF NOT EXISTS city VARCHAR(100);
```
