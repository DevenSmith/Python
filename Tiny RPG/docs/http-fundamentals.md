# HTTP fundamentals in Tiny RPG

HTTP is the protocol used by the frontend to send requests to the FastAPI server
and receive responses. Each exchange is independent: the request must contain
enough information for the server to understand what operation is requested.

## Anatomy of a request and response

This request partially updates character 7:

```http
PATCH /characters/7 HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
Accept: application/json

{
  "name": "Ada the Wise"
}
```

It contains:

- Method: `PATCH`, describing the operation.
- Path: `/characters/7`, identifying the resource. `7` is a path parameter.
- Headers: metadata about the request and expected representation.
- Body: JSON containing the requested change.

A successful response is:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 7,
  "name": "Ada the Wise",
  "character_class": "Mage",
  "health": 80,
  "level": 1
}
```

The response contains a status code, headers, and usually a body.

## Methods used by Tiny RPG

| Method | Meaning | Tiny RPG example |
| --- | --- | --- |
| `GET` | Retrieve without changing the resource | `GET /characters/7` |
| `POST` | Create a resource or trigger an action | `POST /characters`, `POST /characters/7/level-up` |
| `PATCH` | Change selected fields | `PATCH /characters/7` |
| `DELETE` | Remove a resource | `DELETE /characters/7` |

`PUT` normally replaces the complete resource. Tiny RPG uses `PATCH` because a
client can provide only `name`, only `health`, or both, while omitted fields stay
unchanged.

## Ways to send input

Path parameters identify a particular resource:

```http
GET /characters/7
```

Query parameters filter or control a request:

```http
GET /classes?minimum_health=100
```

JSON bodies carry structured input:

```http
POST /characters
Content-Type: application/json

{"name": "Ada", "character_class": "Mage"}
```

Headers carry request metadata. `Content-Type: application/json` describes the
body. A later authentication step will use an `Authorization` header.

## Status codes used by Tiny RPG

| Code | Meaning | Example |
| --- | --- | --- |
| `200 OK` | Retrieval, action, or update succeeded | Character retrieved or patched |
| `201 Created` | A new resource was stored | Character or inventory row created |
| `404 Not Found` | The addressed resource does not exist | Unknown character ID |
| `409 Conflict` | Input conflicts with current stored state | Same item name with different effects |
| `422 Unprocessable Entity` | JSON shape or field validation failed | Blank name or negative health |

`401 Unauthorized` means valid authentication is missing. `403 Forbidden` means
the server knows who the caller is, but that caller lacks permission. Tiny RPG
will exercise those codes when bearer-token authentication is added.

## Statelessness, persistence, and HTTPS

HTTP is stateless: one request does not automatically remember a previous one.
Tiny RPG persists character state in SQLite, so a later request can load it by
ID. Authentication will eventually attach identity to every protected request.

Local development uses `http://127.0.0.1:8000`. Production credentials and bearer
tokens must travel over HTTPS, which encrypts traffic between client and server.
TLS is commonly terminated by a reverse proxy or hosting platform in front of
FastAPI.

## Try it

Start the API and open `http://127.0.0.1:8000/docs`, or run:

```powershell
Invoke-RestMethod `
  -Method Patch `
  -Uri http://127.0.0.1:8000/characters/1 `
  -ContentType application/json `
  -Body '{"name":"Ada the Wise"}'
```
