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
issue a bearer token. The next stage will add a login endpoint and JWT issuance.
