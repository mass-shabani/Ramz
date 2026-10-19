# Database Scripts — Ramz

Versioned SQL scripts for the Ramz database.

## Naming convention
- `create_db.vX.Y.sql` — full schema, idempotent
- `migration_XXX_description.vX.Y.sql` — one-shot migrations
- `seed_XXX.vX.Y.sql` — seed data (idempotent)

## Current version
`create_db.v6.0.sql` is the latest schema.

## How to use

Fresh database:
``` bash
sqlite3 data/rmz_data.db < db_scripts/create_db.v6.0.sql 
```

``` powershell
Get-Content db_scripts/create_db.v6.0.sql | sqlite3 data/rmz_data.db
```                             
Do NOT copy scripts into `data/` — keep them here.