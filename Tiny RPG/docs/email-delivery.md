# Email delivery

Tiny RPG can send account-verification and password-reset links through any SMTP
provider. Token records are committed before delivery is queued, and FastAPI
runs the SMTP call as a background task after creating the response.

## Local development

Development keeps email disabled by default and exposes tokens in response
headers so the forms remain easy to practice. To test actual SMTP messages
without delivering mail to real addresses, run a local SMTP inbox such as
Mailpit, then copy its settings:

```powershell
Copy-Item .env.mailpit.example .env
```

The example expects SMTP on `localhost:1025` and its browser inbox on
`http://localhost:8025`. Restart FastAPI after changing `.env`. Registration and
password-reset requests will then appear in that inbox with clickable links.

## SMTP provider

For delivery to real inboxes, configure values supplied by an SMTP provider:

```text
EMAIL_DELIVERY_ENABLED=true
SMTP_HOST=smtp.provider.example
SMTP_PORT=587
SMTP_USERNAME=provider-username
SMTP_PASSWORD=provider-password
SMTP_FROM_EMAIL=no-reply@your-domain.example
SMTP_STARTTLS=true
FRONTEND_URL=https://tinyrpg.example
```

The sending domain normally needs DNS verification with the provider. Store the
SMTP password in the deployment platform's secret manager rather than Git.

Verification links use `?verify_token=...`; reset links use `?reset_token=...`.
The React app reads either query parameter, opens the correct form, and prefills
the token. It removes the token from the address bar after successful use.

Production configuration requires SMTP delivery and never returns verification
or reset tokens in development response headers.
