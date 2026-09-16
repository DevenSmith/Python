# Environment configuration

Tiny RPG loads backend settings from environment variables and, for local
development, an optional `.env` file. Real `.env` files are ignored by Git;
the checked-in `.env.*.example` files contain templates without real secrets.

## Environments

`ENVIRONMENT` accepts `development`, `testing`, or `production`. Development is
the default so the existing local startup commands continue to work.

To customize local development:

```powershell
Copy-Item .env.example .env
```

The important settings are:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy and Alembic database connection |
| `FRONTEND_ORIGINS` | Comma-separated browser origins allowed by CORS |
| `JWT_SECRET_KEY` | Secret used to sign and verify access tokens |
| `COOKIE_SECURE` | Restricts refresh cookies to HTTPS |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token lifetime |

Environment variables supplied by the shell or deployment platform override
values from `.env`.

## Production safeguards

When `ENVIRONMENT=production`, startup validation requires:

- A unique `JWT_SECRET_KEY` with at least 32 characters.
- Secure refresh cookies.
- One or more explicit HTTPS frontend origins.
- No wildcard, HTTP, localhost, or loopback CORS origin.

Production secrets should come from the hosting platform's secret manager. Do
not commit a populated `.env` file. Generate a JWT secret with a cryptographically
secure tool, for example:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The production example uses a PostgreSQL URL as a preview of the later database
deployment step. PostgreSQL's Python driver will be added when that step is
implemented.

The React build reads `VITE_API_BASE_URL`. Copy
`frontend/.env.production.example` to `frontend/.env.production` and replace its
placeholder with the deployed HTTPS API address before a production build.
