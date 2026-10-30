# Local email delivery (QQ Mail SMTP)

Runbook for the email messages the backend sends: the registration verification code and the password reset link. Delivery uses the project lead's QQ Mail account over SMTP with an authorization code. The backend runs locally in the current demo mode, so this is a local procedure; TACC jobs do not send email.

## Why not a mail service

A transactional email provider needs a paid or verified domain and one more third-party credential for a course project. A personal mailbox with SMTP and an authorization code is enough for a handful of users and keeps the credential local.

## QQ Mail setup

1. Sign in to the QQ Mail web client with the account that will send the messages.
2. Open Settings, then Account, and enable the IMAP/SMTP service (the page labels it POP3/IMAP/SMTP 服务).
3. Generate an authorization code (授权码). QQ Mail asks for an SMS verification; the code is shown once and can be regenerated.
4. Copy the code. It is the SMTP password; the QQ account password is never used by the application.

## Configuration

Values live in the ignored `.env`; [../.env.example](../.env.example) carries empty placeholders. The Chinese settings from the QQ Mail help page map as follows.

| Setting | Value |
|---|---|
| SMTP host | `smtp.qq.com` |
| Port and security | `465` with SSL (implicit TLS), or `587` with STARTTLS |
| Username | The full QQ Mail address, for example `123456789@qq.com` |
| Password | The authorization code, not the QQ account password |
| From address | The full QQ Mail address, so it matches the authenticated user |

```bash
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=123456789@qq.com
SMTP_PASSWORD=<authorization code>
SMTP_FROM=123456789@qq.com
```

## Flows the application sends

| Message | Timing | Content |
|---|---|---|
| Registration code | Sent on sign-up | Six digit code, valid for 10 minutes, one active code per account |
| Password reset | Sent on request | One-time link with a signed token, valid for 30 minutes, invalidated after use |

## Development fallback

When `SMTP_HOST` or `SMTP_PASSWORD` is empty, the backend runs in development mode: it does not connect to QQ Mail, it writes the code or the reset link to the backend log, and the API response marks that email delivery is disabled. This keeps local tests and offline demos independent of a mailbox.

## Limits and risks

- A personal QQ mailbox has undocumented daily sending limits and may flag automated traffic. This is acceptable for a course project with a few users; a real deployment needs a transactional provider.
- The authorization code grants access to the mailbox, not only to SMTP. It belongs only in `.env`, never in Git, a screenshot, or a message. Regenerate it in the QQ Mail settings if it leaks.
- Register the sending address as a contact or whitelist it in the receiving account to reduce spam filtering.
- The current host may rate-limit or reject outbound SMTP; if the network blocks port 465, try 587 with STARTTLS.
- TACC jobs do not send email. The backend runs locally and no TACC-hosted backend is planned ([ADR-0010](adr/0010-tacc-as-offline-compute.md)), so SMTP stays a local-only concern.

## Troubleshooting

- Authentication error 535: the authorization code is wrong, expired, or replaced by the account password. Regenerate it.
- Connection timeout: the selected port or security mode is wrong; try the other pair (465 with SSL, 587 with STARTTLS).
- Messages arrive in spam: whitelist the sender and keep the subject and body short, without links other than the reset link.
- A smoke check from the project environment: send one message with `smtplib.SMTP_SSL("smtp.qq.com", 465)` and the authorization code, then read it in the receiving mailbox.
