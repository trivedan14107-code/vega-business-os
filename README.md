# Vega — Business Second Brain

Vega is an AI operating system for business owners. The owner uses one simple web
conversation. Vega plans the work, creates or reuses permission-limited specialist agents,
asks for approval, operates connected business apps, verifies the result, and records it.

## Business-owner experience

1. Open Vega.
2. Click **Continue with Google** once.
3. Optionally click **Connect Slack** and choose a team channel.
4. Ask for an outcome in ordinary language.
5. Review and approve the proposed external action.

Owners never copy API keys, client IDs, secrets, or tokens. Those are configured once by
the platform developer and OAuth tokens are encrypted at rest.

## Included in the hackathon MVP

- Owner-focused responsive web interface
- Google account authentication and single-company ownership protection
- LangGraph Main Agent with persistent specialist creation and reuse
- Groq structured planning with a deterministic offline fallback
- Meeting and Communication specialist coordination
- Real Google Calendar event and unique Google Meet link creation
- Slack OAuth, channel selection, and approved team notification
- Access gates, human approval, execution verification, and audit history
- Signed HTTP-only sessions, CSRF protection, CSP and security headers
- Encrypted OAuth tokens and secret-safe configuration
- Least-privilege Google and Slack scopes

Other approved specialist templates currently demonstrate planning and safe mock execution.
They require provider adapters before production use.

## Run Vega locally

From this project folder:

```powershell
.\.venv\Scripts\python.exe -m businessflow_ai.bootstrap
.\.venv\Scripts\python.exe -m uvicorn businessflow_ai.api:app --host 127.0.0.1 --port 8000
```

Then open [http://localhost:8000](http://localhost:8000).

## Platform developer setup

Copy `.env.example` to `.env.local`. Keep `.env.local` private and never commit it.

Required configuration:

```text
GROQ_API_KEY=platform-owned-key
GOOGLE_CLIENT_ID=platform-owned-client-id
GOOGLE_CLIENT_SECRET=platform-owned-client-secret
OWNER_EMAIL=owner@company.com
```

Run `python -m businessflow_ai.bootstrap` to generate token-encryption and session-signing
secrets without printing them.

Google OAuth callback:

```text
http://localhost:8000/api/oauth/google/callback
```

### Slack

Slack requires a public HTTPS callback for a server-side bot installation. Deploy Vega or
use an approved development tunnel, then set the identical URL in all three locations:

```text
.env.local:
SLACK_REDIRECT_URI=https://YOUR-PUBLIC-DOMAIN/api/oauth/slack/callback

Slack app → OAuth & Permissions → Redirect URLs:
https://YOUR-PUBLIC-DOMAIN/api/oauth/slack/callback

slack-app-manifest.yaml:
https://YOUR-PUBLIC-DOMAIN/api/oauth/slack/callback
```

The platform developer stores `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` in `.env.local`.
The owner only clicks **Connect Slack**. Invite Vega to the chosen channel before selecting
it; Vega intentionally cannot post to channels it has not joined.

## Production checklist

- Serve only through HTTPS and set `APP_ENV=production`.
- Set `APP_BASE_URL`, `SLACK_REDIRECT_URI`, `OWNER_EMAIL`, and `ALLOWED_HOSTS` exactly.
- Use a managed secret store and managed database instead of local files.
- Rotate the Groq key that appeared in development screenshots.
- Complete Google OAuth verification before onboarding external customers.
- Add monitoring, backups, retention rules, and provider-specific failure alerts.

For the prepared Render release, follow [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md).

## Quality checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check businessflow_ai tests
```

See `PLAN.md` for architecture and future adapter phases.
