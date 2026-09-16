# Database migrations with Alembic

SQLAlchemy models describe the schema expected by the Python application.
Alembic records the ordered operations that move an existing database to that
schema without deleting its data.

## Apply migrations

Run this before starting the API after receiving schema changes:

```powershell
python -m alembic upgrade head
```

`head` means the newest available revision. Alembic reads the current revision
from the database's `alembic_version` table and applies only newer migrations.

Useful inspection commands are:

```powershell
python -m alembic current
python -m alembic history
python -m alembic check
```

`current` shows the database revision, `history` shows the ordered migration
files, and `check` compares SQLAlchemy metadata with the migrated database.

## Create the next migration

After intentionally changing a class in `tinyrpg/database_models.py`, generate a
candidate revision:

```powershell
python -m alembic revision --autogenerate -m "describe the schema change"
```

Review the new file under `migrations/versions` before applying it. Autogenerate
detects many table, column, index, and constraint changes, but it cannot infer
every data transformation or rename safely.

Then apply and verify it:

```powershell
python -m alembic upgrade head
python -m alembic check
```

Each revision contains `upgrade()` for moving forward and `downgrade()` for
reversing that specific step. Downgrades that remove tables or columns can delete
data, so inspect them before running `python -m alembic downgrade -1`.

## Tiny RPG baseline

`0001_current_schema` is the baseline revision. It creates `users`,
`auth_tokens`, `characters`, and `inventory_items` for a fresh database. The
existing development database was stamped at this revision because it already
contained that schema. Stamping records a revision without rerunning its table
creation operations.

The API no longer calls `Base.metadata.create_all()` at startup. Database schema
changes must be explicit Alembic migrations, which prevents application startup
from silently creating an incomplete or unexpected schema.
