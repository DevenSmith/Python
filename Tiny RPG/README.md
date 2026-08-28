# TinyRPG

TinyRPG is a small learning project that combines:

- A Python command-line RPG
- A FastAPI backend
- A React and TypeScript frontend
- Automated tests with pytest

The frontend loads character classes from the Python API and can create a character through the API.

## Requirements

- Python 3.12 or newer
- Node.js 20.19 or newer (Node.js 24 LTS is recommended)
- npm

## Project structure

```text
Tiny RPG/
├── frontend/          React and TypeScript frontend
├── tests/             Python tests
├── tinyrpg/           Python package, models, storage, UI, and API
├── main.py            Command-line application
├── pyproject.toml     Python project and tool configuration
└── requirements.txt   Complete Python environment dependencies
```

## Python setup

From the repository root, create a virtual environment:

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

From the repository root, with the virtual environment activated:

```powershell
python -m uvicorn tinyrpg.api:app --reload
```

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
| `GET` | `/classes` | List character classes and starting health |
| `GET` | `/classes/{character_class}` | Get one class and its starting health |
| `POST` | `/characters` | Create a character |
| `GET` | `/characters/{character_id}` | Retrieve a created character by ID |

Example request body for `POST /characters`:

```json
{
  "name": "Deven",
  "character_class": "Warrior"
}
```

Character data created through the API is currently stored in memory. Restarting the API clears all created characters and resets their IDs.

## Frontend setup

Install the frontend dependencies once:

```powershell
cd frontend
npm install
```

Start the React development server:

```powershell
npm run dev
```

Open the URL shown by Vite, normally:

```text
http://localhost:5173
```

The FastAPI server must also be running for the frontend to load classes and create characters. During development, keep the API and frontend running in separate terminals.

## Environment variables

The API supports these optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `TinyRPG API` | Title shown in the generated API documentation |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Browser origin permitted by CORS |

PowerShell example:

```powershell
$env:APP_NAME = "TinyRPG Development API"
$env:FRONTEND_ORIGIN = "http://localhost:5173"
python -m uvicorn tinyrpg.api:app --reload
```

## Tests and code quality

Run all Python tests from the repository root:

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
npm run lint
npm run build
```

The production frontend build is written to `frontend/dist/`.

## Stop the development servers

Press `Ctrl+C` in each terminal running Uvicorn or Vite.

To leave the Python virtual environment, run:

```powershell
deactivate
```

## Current status

TinyRPG is an educational work in progress. It currently demonstrates Python modules and models, JSON and file storage, a tested FastAPI API, React components and state, form handling, API requests, and loading/error UI.
