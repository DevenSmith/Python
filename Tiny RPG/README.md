# TinyRPG

TinyRPG is a small learning project that combines:

- A Python command-line RPG
- A FastAPI backend
- A React and TypeScript frontend
- Automated backend tests with pytest and frontend tests with Vitest and React Testing Library

The frontend loads character classes from the Python API and can create a character through the API.

## Requirements

- Python 3.12 or newer
- Node.js 20.19 or newer (Node.js 24 LTS is recommended)
- npm

## Project structure

```text
Tiny RPG/
├── frontend/          React and TypeScript frontend
├── docs/              Learning guides tied to the working API
├── tests/             Python tests
├── tinyrpg/           Python package, models, storage, UI, and API
├── main.py            Command-line application
├── pyproject.toml     Python project and tool configuration
└── requirements.txt   Complete Python environment dependencies
```

## Python setup

Run the Python commands below from the `Tiny RPG` project directory, which contains `main.py` and `requirements.txt`. If your checkout contains several projects, enter `Tiny RPG` first.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux, activate it with:

```bash
source .venv/bin/activate
```

Install the Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run the command-line game

With the Python virtual environment activated, run:

```powershell
python main.py
```

The CLI asks for character information, applies simple game actions, and writes character data to `character.txt` and `character.json`.

## Run the API

From the `Tiny RPG` project directory, with the virtual environment activated:

```powershell
python -m alembic upgrade head
python -m uvicorn tinyrpg.api:app --reload
```

Run the Alembic command whenever you pull or create database schema changes. It
applies only revisions that the current database has not recorded yet.

The API is available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | API welcome message |
| `POST` | `/users` | Register a user with a securely hashed password |
| `POST` | `/auth/token` | Verify credentials and issue a JWT bearer token |
| `POST` | `/auth/refresh` | Rotate the refresh cookie and issue a new access token |
| `POST` | `/auth/logout` | Revoke the refresh token and clear its cookie |
| `POST` | `/auth/verify-email` | Consume a single-use email verification token |
| `POST` | `/auth/verify-email/request` | Replace an unverified account's verification token |
| `POST` | `/auth/password-reset/request` | Create password-reset instructions without revealing account existence |
| `POST` | `/auth/password-reset/confirm` | Consume a reset token and replace the password |
| `GET` | `/users/me` | Return the account identified by a valid bearer token |
| `GET` | `/users/me/security-events` | List recent security activity for the account |
| `PATCH` | `/users/me` | Update the authenticated user's display name |
| `POST` | `/users/me/password` | Change the password and revoke all refresh sessions |
| `POST` | `/users/me/logout-all` | Revoke every refresh session for the account |
| `DELETE` | `/users/me` | Soft-disable the authenticated account |
| `GET` | `/admin/users` | List users when the authenticated account has the admin role |
| `GET` | `/classes` | List character classes and starting health |
| `GET` | `/classes/{character_class}` | Get one class and its starting health |
| `POST` | `/characters` | Create a character |
| `GET` | `/characters?after_id=&limit=` | List characters with optional cursor pagination |
| `GET` | `/characters/{character_id}` | Retrieve a created character by ID |
| `PATCH` | `/characters/{character_id}` | Update a character's name or health |
| `DELETE` | `/characters/{character_id}` | Delete a character |
| `POST` | `/characters/{character_id}/level-up` | Increase a character's level |
| `POST` | `/characters/{character_id}/take-damage` | Reduce health without going below zero |
| `POST` | `/characters/{character_id}/revive` | Restore a defeated character to half health |
| `GET` | `/characters/{character_id}/inventory` | List a character's inventory |
| `POST` | `/characters/{character_id}/inventory` | Add an item or increase its quantity |
| `PUT` | `/characters/{character_id}/inventory/{item_id}` | Completely replace an inventory item |
| `DELETE` | `/characters/{character_id}/inventory/{item_id}` | Delete one inventory item |

Example request body for `POST /characters`:

```json
{
  "name": "Deven",
  "character_class": "Warrior"
}
```

Character and inventory data created through the API is stored in the local
`tiny_rpg.db` SQLite database.

Character and inventory endpoints require `Authorization: Bearer <token>` and
are scoped to the authenticated user's characters. Register with `POST /users`,
then obtain an access token from `POST /auth/token`.

For a guided explanation of requests, methods, parameters, headers, JSON, and
status codes using these endpoints, read [`docs/http-fundamentals.md`](docs/http-fundamentals.md).
For the schema migration workflow, read [`docs/database-migrations.md`](docs/database-migrations.md).
For development, testing, and production settings, read [`docs/configuration.md`](docs/configuration.md).
For cookie request protection, read [`docs/csrf-protection.md`](docs/csrf-protection.md).
For verification and password-reset email setup, read [`docs/email-delivery.md`](docs/email-delivery.md).

## Frontend setup

In a separate terminal, start from the `Tiny RPG` project directory and install the frontend dependencies:

```powershell
cd frontend
npm install
```

While still in `frontend`, create your local configuration in PowerShell:

```powershell
Copy-Item .env.example .env
```

On macOS or Linux, use `cp .env.example .env` instead. Copy the file only during initial setup; do not overwrite an existing customized `.env`.

The example configures the backend address:

```text
VITE_API_BASE_URL=http://localhost:8000
```

`.env` is ignored by Git; `.env.example` documents the setting for new checkouts. Restart Vite after changing `.env`. Frontend `VITE_` values are exposed to the browser, so never put passwords or secret API keys in them.

Start the React development server from `frontend`:

```powershell
npm run dev
```

Open the URL shown by Vite, normally:

```text
http://localhost:5173
```

The FastAPI server must also be running for the frontend to load classes and create characters. During development, keep the API and frontend running in separate terminals. `npm run dev` starts only the frontend; it does not start FastAPI.

The default CORS configuration permits `http://localhost:5173`. If Vite uses a different port or you open the frontend under a different hostname, update `FRONTEND_ORIGINS` to match and restart the backend.

## Environment variables

The API supports these optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `TinyRPG API` | Title shown in the generated API documentation |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Browser origin permitted by CORS |
| `JWT_SECRET_KEY` | Development-only value | Secret used to sign and verify JWTs; set outside local practice |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Lifetime of an issued access token |

PowerShell example:

```powershell
$env:APP_NAME = "TinyRPG Development API"
$env:FRONTEND_ORIGIN = "http://localhost:5173"
python -m uvicorn tinyrpg.api:app --reload
```

## Tests and code quality

Run all Python tests from the `Tiny RPG` project directory:

```powershell
python -m pytest -v
```

Run Python linting and type checking:

```powershell
python -m ruff check .
python -m mypy main.py tinyrpg tests
```

From the `frontend` directory, run the frontend checks:

```powershell
npm test
npm run lint
npm run build
```

`npm test` runs the frontend tests once. The component tests simulate a browser and mock the API functions, so neither development server needs to be running for these tests. To verify the real connection, run both servers and create a character in the browser.

The production frontend build is written to `frontend/dist/`.

## Stop the development servers

Press `Ctrl+C` in each terminal running Uvicorn or Vite.

To leave the Python virtual environment, run:

```powershell
deactivate
```

## Current status

TinyRPG is an educational work in progress. It currently demonstrates Python modules and models, JSON and file storage, a tested FastAPI API, React components and custom hooks, form validation, accessible error messages, API requests, loading/error UI, and automated frontend interaction tests.
