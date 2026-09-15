# Authentication practice in Tiny RPG

## Registration

The first authentication stage is account registration:

```http
POST /users HTTP/1.1
Content-Type: application/json

{
  "email": "ada@example.com",
  "display_name": "Ada",
  "password": "correct-horse-battery-staple"
}
```

FastAPI validates the request, normalizes the email, rejects duplicates, hashes
the password, and stores the user. Success returns `201 Created` with safe fields:

```json
{
  "id": 1,
  "email": "ada@example.com",
  "display_name": "Ada",
  "created_at": "2026-09-14T18:30:00Z"
}
```

Neither the password nor its hash is returned. The server stores only an Argon2
password hash produced by `pwdlib`'s recommended configuration. Hashing is
one-way and salted; login will verify a submitted password against this hash.

Registration is not login. It creates an account but this endpoint does not yet
issue a bearer token.

## Login and token issuance

The client exchanges credentials for an access token:

```http
POST /auth/token HTTP/1.1
Content-Type: application/json

{
  "email": "ada@example.com",
  "password": "correct-horse-battery-staple"
}
```

The server looks up the normalized email and verifies the submitted password
against the stored Argon2 hash. A successful response is:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

The signed JWT contains a user ID in `sub`, an issue time in `iat`, and an
expiration time in `exp`. It expires after 30 minutes by default. The JWT payload
is readable, so passwords and other secrets never belong in it.

Unknown emails, wrong passwords, and disabled users all receive the same `401`
response. This reveals less account information than separate errors. The
`WWW-Authenticate: Bearer` response header identifies the authentication scheme.

The local default signing secret exists only to make development easy. Set a
long random `JWT_SECRET_KEY` environment variable anywhere beyond local practice.
The next stage will validate this token when a protected endpoint receives it in
the `Authorization: Bearer <token>` request header.
