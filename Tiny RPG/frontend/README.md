# TinyRPG frontend

This directory contains the React and TypeScript client for TinyRPG.

The interface supports account registration and authentication, character creation and management, tactical monster combat, XP progression, session management, and account-security actions. API calls are centralized in `src/api/tinyrpgApi.ts`, while the application uses typed responses and tested user interactions.

## Run locally

Start the FastAPI backend from the parent directory first. Then run:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Commands

```powershell
npm test       # Run Vitest and React Testing Library tests
npm run lint   # Run ESLint
npm run build  # Type-check and create the production Vite build
```

`VITE_API_BASE_URL` controls the backend address and defaults to `http://localhost:8000` in the example environment file.
