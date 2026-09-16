# CSRF protection

Browsers automatically attach matching cookies to requests. A malicious site
could try to make a signed-in browser submit a cookie-authenticated request even
though that site cannot read Tiny RPG's HTTP-only refresh token. Tiny RPG uses a
double-submit CSRF token on `/auth/refresh` and `/auth/logout` to prevent this.

After login, the backend sets two cookies:

- `refresh_token` is HTTP-only, so JavaScript cannot read it.
- `csrf_token` is readable by the Tiny RPG frontend.

Before refresh or logout, React reads `csrf_token` and copies it into the
`X-CSRF-Token` header. The browser also sends the CSRF cookie. The backend uses a
constant-time comparison and accepts the request only when both values exist and
match. A different website cannot normally read Tiny RPG's cookie and therefore
cannot construct the required custom header.

The refresh operation rotates both cookies. Logout, password changes, logging
out every device, and account disabling delete both cookies.

## Local hostname requirement

Cookies belong to hostnames. A cookie issued by `127.0.0.1` is not readable by a
page running on `localhost`, even when both names reach the same computer. Local
React configuration therefore uses:

```text
VITE_API_BASE_URL=http://localhost:8000
```

After changing this value, restart Vite. Existing sessions created through
`127.0.0.1` will not carry over; sign in once through the new `localhost` API
address.

CSRF protection is separate from CORS and authentication. CORS controls which
browser origins may read API responses, authentication identifies the user, and
CSRF verification proves a cookie-authenticated request originated from a page
that could read Tiny RPG's CSRF cookie.
