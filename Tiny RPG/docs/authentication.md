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
Protected endpoints validate this token when they receive it in the
`Authorization: Bearer <token>` request header.

## Authenticating a protected request

`GET /users/me` requires an access token:

```http
GET /users/me HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

FastAPI's bearer dependency extracts the scheme and token. Tiny RPG then verifies
the HS256 signature, requires `sub`, `iat`, and `exp`, rejects expired tokens,
converts `sub` to a positive user ID, and loads that user from the database. A
missing user or disabled account is also rejected.

Success returns the safe `UserResponse`. Missing, malformed, expired, or otherwise
invalid credentials receive the same response:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer

{"detail": "Could not validate credentials"}
```

The reusable `get_current_user` dependency can now protect another endpoint by
declaring a `CurrentUser` parameter. Authentication happens before the endpoint
body runs.

## Character authorization

Every character now has an `owner_id` foreign key to `users.id`. Character and
inventory endpoints require `CurrentUser`. Collection queries filter by that user:

```sql
SELECT * FROM characters
WHERE owner_id = :current_user_id;
```

An individual operation first loads the character and compares its `owner_id`
with the authenticated user's ID. A missing or invalid token returns `401`. A
validly authenticated user attempting to access another user's character returns
`403 Forbidden`.

This demonstrates the boundary:

```text
JWT validation identifies the user       → authentication
Comparing user.id with character.owner_id → authorization
```

The frontend never sends `owner_id` when creating a character. The backend takes
the owner from `CurrentUser`, which prevents a caller from assigning a new
character to an arbitrary account.
