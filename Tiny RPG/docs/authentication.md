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
  "created_at": "2026-09-14T18:30:00Z",
  "role": "player",
  "email_verified": false
}
```

Neither the password nor its hash is returned. The server stores only an Argon2
password hash produced by `pwdlib`'s recommended configuration. Hashing is
one-way and salted; login will verify a submitted password against this hash.

Registration is not login. It creates an account and a single-use verification
token, but does not issue a bearer token. In development, the verification token
is returned in `X-Verification-Token` to stand in for a link sent by email.

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

## Refresh tokens and logout

Login now also sets a random refresh token in an `HttpOnly` cookie. JavaScript
cannot read an `HttpOnly` cookie. The browser sends it to `POST /auth/refresh`,
which consumes it, creates a replacement refresh token, and returns a fresh
access token. Consuming the old record prevents token replay.

The access token stays only in frontend memory. A page reload loses it, so the
frontend uses the refresh cookie to restore the session. If a protected request
returns `401`, it refreshes and retries the request once. A second rejection
returns the player to sign in.

`POST /auth/logout` revokes the current refresh token and deletes its cookie.
Resetting a password revokes every outstanding refresh token for that user.

The cookie uses `Secure=false` only for local HTTP development. A deployed HTTPS
application must set `Secure=true`.

## Email verification and password reset

`POST /auth/verify-email` consumes the token created during registration. Tokens
are stored as SHA-256 hashes, expire after 24 hours, and can be used only once.

`POST /auth/password-reset/request` always returns the same `202 Accepted`
message whether an account exists or not. This prevents email enumeration. In
development, a valid account's token appears in `X-Password-Reset-Token`; an
email provider would normally deliver it. `POST /auth/password-reset/confirm`
consumes that token and stores a new Argon2 password hash.

## Roles and rate limiting

New accounts receive the `player` role. `/admin/users` uses a second dependency
after authentication to require the `admin` role. No credentials produces
`401`; valid player credentials produce `403`.

Login permits five failed attempts per client-address and email pair in five
minutes. The next attempt receives `429 Too Many Requests` and a `Retry-After`
header. This in-memory limiter is appropriate for this single-process exercise;
a multi-server application would keep the counters in Redis.
