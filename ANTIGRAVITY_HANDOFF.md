# Vega Business OS — Antigravity Developer Handoff

Last updated: 2026-09-12  
Workspace: `C:\Users\M Trivedan\OneDrive\Documents\ChatGPT\Hackathon- 1`

## 1. Product intent

Vega is a **Business Second Brain / AI Operating System for non-technical business
owners**. The owner talks only to Vega, the Main Agent. Vega understands the requested
business outcome, creates or reuses narrowly permissioned specialist agents, coordinates
their work, requests human approval before external actions, executes through OAuth-connected
business applications, verifies the outcome, and records an audit trail.

Non-negotiable product rules:

1. Business users never copy API keys, client IDs, client secrets, MCP configuration, or
   OAuth tokens.
2. Platform developers configure provider credentials once on the server.
3. The user only clicks a familiar **Connect** button and approves the provider's OAuth
   consent screen.
4. LLM output may propose a plan but may never grant permissions or directly bypass policy.
5. External communications and meeting creation require explicit human approval.
6. Persistent agents are approved configurations, not generated executable code.
7. Every real external action must return a verifiable receipt.

The primary demonstration is:

> “Schedule a leadership meeting tomorrow at 10 AM and notify the team.”

Expected orchestration:

1. Vega identifies Meeting and Communication responsibilities.
2. Vega creates or reuses the Meeting Agent and Communication Agent.
3. Access control checks Google Workspace and Slack capabilities.
4. Vega presents one approval request; no external action occurs before approval.
5. Meeting Agent creates a Google Calendar event with a unique Google Meet link.
6. Communication Agent posts the verified link into the selected Slack channel.
7. Vega verifies the receipts, marks the task completed, and shows the result.

## 2. Technology and project shape

- Python 3.11+
- FastAPI + Uvicorn
- LangGraph 1.x
- LangChain Groq 1.x
- Pydantic 2.x
- SQLite for the hackathon database
- `cryptography.Fernet`-based encrypted OAuth token vault
- Plain HTML/CSS/JavaScript owner interface; no Node build step
- UV dependency management (`pyproject.toml` and `uv.lock`)

Important paths:

```text
businessflow_ai/api.py                    Secure web/API surface and runtime composition
businessflow_ai/agents/main_agent.py      LangGraph orchestration
businessflow_ai/agents/planner.py         Groq and deterministic planners
businessflow_ai/agents/templates.py       Approved specialist definitions
businessflow_ai/graph/state.py            LangGraph state contract
businessflow_ai/models/                   Pydantic domain models
businessflow_ai/services/registry.py      SQLite agent/task/audit persistence
businessflow_ai/services/connections.py   OAuth state and encrypted connection storage
businessflow_ai/services/token_vault.py   Token encryption
businessflow_ai/services/access.py        Capability gate
businessflow_ai/services/policy.py        Deterministic approval and safety policy
businessflow_ai/services/google_oauth.py  Google OAuth + PKCE
businessflow_ai/services/google_workspace.py Real Calendar/Meet execution and verification
businessflow_ai/services/slack_oauth.py   Slack OAuth v2
businessflow_ai/services/slack.py         Channel selection and message execution
businessflow_ai/web/                      Owner-facing interface
tests/                                    Unit/integration/security tests
data/                                     Normalized evaluation and business sample data
slack-app-manifest.yaml                   Slack app definition
```

## 3. What is implemented

### 3.1 Owner experience

- Responsive Vega dashboard at `/`.
- One Google button for identity and Google Workspace connection.
- Natural-language goal composer.
- Visible approval panel with Approve and Reject actions.
- Persistent specialist-agent overview.
- Connected-app overview.
- Slack channel selector.
- Recent task/status timeline.
- Business language throughout; no credentials are shown to the owner.

Frontend files:

- `businessflow_ai/web/index.html`
- `businessflow_ai/web/app.css`
- `businessflow_ai/web/app.js`

### 3.2 Main Agent and specialist lifecycle

`build_main_agent()` builds this graph:

```text
understand_goal
  -> resolve_specialists
  -> create_execution
  -> check_access
     -> report_access_required, or
     -> request_approval, or
     -> execute_specialists
  -> verify_results
  -> report_completion
```

- Groq structured output can select only approved roles.
- Rule-based planning supports offline tests and demonstrations.
- The registry enforces one persistent specialist per company and role.
- Repeated goals reuse existing agent IDs.
- Meeting is deterministically ordered before Communication even if the LLM returns the
  roles in reverse order.
- Agent status changes to active during work and returns to idle afterward.
- Unknown roles fail closed.

Approved templates currently include:

- Meeting
- Communication
- Finance Collection
- Sales Follow-up
- Customer Support
- Inventory
- Procurement
- Sales Reporting

Only Meeting and Communication have real external adapters. The other roles currently use
safe deterministic mock execution and must not be marketed as production integrations.

### 3.3 Google Workspace

- OAuth authorization-code flow with PKCE and single-use state.
- User profile email is required.
- First local owner claims the configured company; production requires `OWNER_EMAIL`.
- OAuth access and refresh tokens are encrypted before SQLite persistence.
- Automatic token refresh.
- Real Calendar event creation with an idempotent event ID.
- Real Google Meet conference creation via Calendar conference data.
- Optional attendees are accepted only when explicit email addresses appear in the goal.
- Calendar event is read back and Meet URL format is validated.
- Current requested scopes are intentionally limited to identity/profile and
  `calendar.events`.

### 3.4 Slack

- Platform-owned Slack OAuth v2 flow with server-side state.
- Encrypted bot-token storage.
- Public/private channel discovery.
- Vega can select only a channel to which the bot has been invited.
- Approved communication posts the meeting title, time, and verified Meet URL.
- Slack API response channel ID and timestamp form the execution receipt.
- Least-privilege bot scopes:
  - `chat:write`
  - `channels:read`
  - `groups:read`

### 3.5 Security controls already present

- `.env.local` is gitignored.
- `.env.example` contains placeholders only; leaked example credentials were removed.
- Provider tokens are encrypted at rest.
- OAuth states expire after ten minutes and are single-use.
- Google uses PKCE.
- Signed, HTTP-only, SameSite=Lax owner sessions.
- CSRF token required for state-changing JSON endpoints.
- Trusted host middleware.
- Content Security Policy, anti-framing, MIME-sniff prevention, referrer policy, and
  restrictive browser permissions headers.
- Production startup fails if `SESSION_SECRET` or `OWNER_EMAIL` is absent.
- Company identity comes from the signed session, never from an owner-editable request field.
- Approval handles are random UUIDs and scoped to the authenticated company.
- LLM plans are validated with Pydantic and approved templates.
- Deterministic capability and policy layers sit between the model and adapters.
- Provider/network exceptions are converted into safe user-facing OAuth errors.

### 3.6 API routes

```text
GET  /                              Owner interface
GET  /health                        Health check
GET  /api/session                   Authentication state + CSRF token
POST /api/logout                    End signed session
GET  /api/oauth/google/start        Begin Google connection/login
GET  /api/oauth/google/callback     Complete Google connection/login
GET  /api/oauth/slack/start         Begin authenticated Slack connection
GET  /api/oauth/slack/callback      Complete Slack connection
GET  /api/providers                 Supported providers
GET  /api/dashboard                 Connections, agents, tasks, audit events
POST /api/goals                     Start a Vega goal
POST /api/approvals/{thread_id}     Approve or reject paused work
GET  /api/slack/channels            Discover accessible channels
PUT  /api/slack/default-channel     Select the allowed team channel
GET  /api/webhooks/whatsapp         Legacy verification endpoint only
```

WhatsApp message delivery is intentionally not implemented; Slack was selected for the
hackathon.

## 4. Current test status

At handoff, the complete suite passes:

```text
37 passed
ruff: all checks passed
```

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check businessflow_ai tests
```

The tests cover agent creation/reuse, policy controls, approval interrupts, rejection,
Google execution/verification, OAuth state, encrypted storage, Slack installation/channel
selection/messaging, dataset integrity, UI availability, session cookies, CSP headers,
authentication, and CSRF.

## 5. Current local state and known incident

- `.env.local` exists and contains platform credentials. Never print or paste its values.
- `TOKEN_ENCRYPTION_KEY` and `SESSION_SECRET` exist locally.
- Vega was last started on `http://127.0.0.1:8000`.
- The most recent Google OAuth callback returned HTTP 500 because the sandboxed development
  process could not make an outbound TCP connection to Google's token endpoint.
- The Google authorization code in that callback URL is temporary and single-use. Do not
  copy or reuse the callback URL. Start a completely new OAuth attempt after running Vega
  in a normal network-enabled terminal.
- The consent response showed historical Gmail and Calendar-readonly scopes because the
  Google account had previously granted them. Current source code no longer requests Gmail
  or redundant Calendar-readonly access. Revoke the old Google grant and reconnect if strict
  scope cleanup is required.
- A Groq API key was visible in a screenshot and had also existed in the example file. It
  must be revoked and replaced before further real testing.
- Slack credentials also appeared in an earlier local example file during development.
  Rotate the Slack client secret as a precaution.
- Almost the entire workspace is currently untracked (`git status --short` shows `??`). There
  is no reliable commit history for this implementation. Review secret exclusions, then make
  a clean baseline commit before further changes.

## 6. How Antigravity should start

Do not delete or regenerate `.env.local`, `businessflow.db`, or the token-encryption key.
Changing the encryption key makes existing OAuth tokens unreadable.

```powershell
cd "C:\Users\M Trivedan\OneDrive\Documents\ChatGPT\Hackathon- 1"
$env:UV_CACHE_DIR=".uv-cache"
uv sync --extra dev
.\.venv\Scripts\python.exe -m businessflow_ai.bootstrap
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check businessflow_ai tests
.\.venv\Scripts\python.exe -m uvicorn businessflow_ai.api:app --host 127.0.0.1 --port 8000
```

Then open `http://localhost:8000`.

Run the server from a normal network-enabled terminal for OAuth. Do not use `--reload` while
diagnosing provider connectivity; file watchers previously reloaded on changes inside the
virtual environment.

## 7. Platform configuration contract

Never place real values in `.env.example`.

Required local/production environment names:

```text
APP_ENV=development|test|production
APP_BASE_URL=http://localhost:8000 or production HTTPS origin
DATABASE_URL=sqlite:///businessflow.db
GROQ_API_KEY=secret
GROQ_FAST_MODEL=openai/gpt-oss-20b
GROQ_REASONING_MODEL=openai/gpt-oss-120b
GOOGLE_CLIENT_ID=secret identifier
GOOGLE_CLIENT_SECRET=secret
TOKEN_ENCRYPTION_KEY=secret; do not rotate without a migration
SESSION_SECRET=secret
OWNER_EMAIL=authorized production owner email
DEFAULT_COMPANY_ID=demo-company
ALLOWED_HOSTS=comma-separated hostnames
BUSINESS_TIMEZONE=Asia/Kolkata
DEFAULT_MEETING_DURATION_MINUTES=45
SLACK_CLIENT_ID=secret identifier
SLACK_CLIENT_SECRET=secret
SLACK_REDIRECT_URI=https://public-host/api/oauth/slack/callback
SLACK_DEFAULT_CHANNEL_ID=optional fallback
```

## 8. Remaining work, in priority order

### P0 — required for the hackathon demo

1. **Rotate exposed credentials.** Revoke and replace Groq key and Slack client secret.
   Confirm no real secret is tracked with a secret scanner before committing.
2. **Run with outbound network access.** Restart Vega outside the restricted sandbox and
   repeat Google login from `/`; do not revisit the failed callback URL.
3. **Complete Google end-to-end test.** Ask only for a meeting, approve it, then verify the
   exact date/time, Calendar event, and Meet URL in the connected account.
4. **Give Vega a public HTTPS origin.** Slack's server-side OAuth redirect requires HTTPS.
   Use a deployment or an approved tunnel. Do not expose SQLite or development docs publicly.
5. **Align Slack callback exactly.** The same URL must appear in `.env.local`, the Slack app
   OAuth & Permissions page, and `slack-app-manifest.yaml`.
6. **Complete Slack OAuth.** Connect from Vega, invite the Vega bot to the desired channel,
   choose that channel in the dashboard, and verify one approved test message.
7. **Run the combined golden-path test.** “Schedule a leadership meeting tomorrow at 10 AM
   and notify the team in Slack.” Verify Calendar, Meet, Slack, final task status, and agent
   reuse on a second request.
8. **Create a clean Git baseline.** Confirm `.env.local`, database, virtual environment,
   caches, and generated artifacts are excluded; then commit the reviewed source.

### P1 — required before a real customer pilot

1. Replace `InMemorySaver` with a durable LangGraph checkpointer. Pending approvals are
   currently lost on process restart.
2. Replace the in-memory `pending_threads` dictionary with a durable approval record that
   expires, records approver identity, and is safe across multiple server workers.
3. Move SQLite to managed PostgreSQL with migrations, transactions, backups, tenant-aware
   constraints, and connection pooling.
4. Add a job queue for external work, retries with backoff, idempotency keys, deadlines, and
   dead-letter handling.
5. Add disconnect/revoke controls for Google and Slack, token revocation, connection health,
   and reauthorization status.
6. Add structured logs, tracing, error monitoring, metrics, provider latency, and alerting.
   Never log OAuth codes, tokens, goal content containing private data, or full callback URLs.
7. Add server-side rate limiting and abuse protection at the reverse proxy/API gateway.
8. Add proper organization onboarding, invited users, owner/admin/member roles, and tenant
   isolation tests. Current release is intentionally one company + one owner.
9. Add privacy controls: data retention, audit export, deletion, consent records, and legal
   terms appropriate to the target region.
10. Replace Slack receipt-only verification with an optional read-back check where permitted.
11. Add accessibility, cross-browser, responsive visual regression, and failure-state tests.
12. Run dependency and secret scanners in CI; protect the main branch.

### P2 — product expansion

1. Implement real adapters for finance, sales follow-up, customer support, inventory,
   procurement, and sales reporting. Until then, label them demo/simulation only.
2. Add proactive triggers and schedules: overdue invoices, quiet leads, inventory thresholds,
   daily briefs, and webhook events.
3. Add a governed business memory layer with source citations, per-company retention, and
   deletion controls.
4. Add inbound Slack events only if the product needs Vega conversations inside Slack.
   Current Slack integration is outbound notification only.
5. Voice calling is intentionally out of scope and must not be reintroduced.
6. Add evaluation datasets for tool selection, date resolution, prompt injection, privilege
   escalation, accidental broadcasts, and cross-tenant leakage.

## 9. Known architectural limits

- This is a secure hackathon MVP, not a finished multi-tenant SaaS deployment.
- Approval graph checkpoints and thread mappings are process-local.
- SQLite limits safe horizontal scaling.
- Only Google Meet/Calendar and outbound Slack are real integrations.
- Slack needs a public HTTPS callback; local HTTP alone cannot complete server OAuth.
- Google and Groq network calls are synchronous from the task execution path, so long provider
  latency occupies an API worker.
- Provider failures do not yet have queued retries.
- Agent audit events inside graph state are richer than the small subset currently persisted
  in the audit table; persist every state transition before pilot use.
- The legacy WhatsApp verification GET route remains, but message signatures and delivery are
  intentionally not implemented.
- `businessflow_ai.egg-info` and development artifacts should be removed or ignored before the
  baseline commit.

## 10. Demo acceptance checklist

The hackathon demo is ready only when all boxes pass:

- [ ] Fresh Google connection returns to the Vega dashboard without an error.
- [ ] Dashboard shows the authenticated owner and Google as connected.
- [ ] Slack connection returns to Vega and never exposes credentials to the owner.
- [ ] Bot is invited and the default channel can be selected.
- [ ] Meeting request pauses before any external action.
- [ ] Reject produces no Calendar event and no Slack message.
- [ ] Approve creates exactly one Calendar event with the correct local time.
- [ ] Event contains a valid unique Google Meet link.
- [ ] Slack receives the same verified link after the Calendar result exists.
- [ ] Vega reports completion only after both receipts verify.
- [ ] Repeating the workflow reuses the same Meeting and Communication agent definitions.
- [ ] Restart, failure, and expired-token limitations are stated honestly during the demo.
- [ ] No secret appears in source, Git history, screenshots, terminal output, or logs.

## 11. Definition of “done” for the next developer

For the immediate handoff, “done” means P0 is complete, the golden path succeeds twice,
credentials are rotated, the source is committed safely, and the exact demo steps are written
down. Do not claim the wider product is production-ready until the P1 security, persistence,
multi-tenancy, operations, and compliance work is complete.
