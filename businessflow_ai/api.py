"""Secure owner-facing API and web application for Vega."""

import secrets
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from businessflow_ai.agents.main_agent import build_main_agent
from businessflow_ai.agents.planner import GroqGoalPlanner, RuleBasedGoalPlanner
from businessflow_ai.agents.templates import AGENT_TEMPLATES
from businessflow_ai.config import Settings, get_settings
from businessflow_ai.models import CompanyContact, OAuthProvider, ScheduledTask
from businessflow_ai.services import (
    AccessController,
    AgentRegistry,
    ConnectionStore,
    GmailExecutionEngine,
    GmailService,
    GoogleOAuthClient,
    GoogleOAuthError,
    GoogleSheetsExecutionEngine,
    GoogleSheetsService,
    GoogleWorkspaceExecutionEngine,
    GroqMeetingDetailsExtractor,
    OAuthStateError,
    SlackError,
    SlackExecutionEngine,
    SlackOAuthClient,
    SlackOAuthError,
    SlackService,
    TokenVault,
    VegaSchedulerService,
)
from businessflow_ai.services.playbooks import list_playbooks

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"


def database_path(settings: Settings) -> Path:
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        raise RuntimeError("Only sqlite:/// database URLs are supported in this release")
    return Path(settings.database_url.removeprefix(prefix))


class GoalRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)


class ApprovalRequest(BaseModel):
    approved: bool


class ChannelRequest(BaseModel):
    channel_id: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z0-9]+$")


class ContactCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)
    phone: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=120)
    category: str = Field(default="teammate")
    notes: str = Field(default="", max_length=300)


class ScheduleCreateRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    run_at: datetime
    schedule_type: str = Field(default="once")
    cron_expr: str | None = None
    preapproved: bool = False


def secure_connection_store(settings: Settings | None = None) -> ConnectionStore:
    settings = settings or get_settings()
    if settings.token_encryption_key is None:
        raise HTTPException(status_code=503, detail="Secure storage is not configured")
    return ConnectionStore(
        database_path(settings), TokenVault(settings.token_encryption_key.get_secret_value())
    )


class VegaRuntime:
    """Long-lived graph and its authenticated approval handles."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry = AgentRegistry(database_path(settings))
        self.store = secure_connection_store(settings)
        planner = (
            GroqGoalPlanner(
                settings.groq_api_key.get_secret_value(), settings.groq_reasoning_model
            )
            if settings.groq_api_key is not None
            else RuleBasedGoalPlanner()
        )
        fallback = None
        if settings.slack_client_id and settings.slack_client_secret is not None:
            fallback = SlackExecutionEngine(
                SlackService(self.store), settings.slack_default_channel_id
            )
        executor = fallback
        if (
            settings.google_client_id
            and settings.google_client_secret is not None
        ):
            gmail_service = GmailService(
                self.store,
                settings.google_client_id,
                settings.google_client_secret.get_secret_value(),
                settings.business_timezone,
            )
            gmail_engine = GmailExecutionEngine(
                gmail_service, fallback=fallback
            )
            sheets_service = GoogleSheetsService(
                self.store,
                settings.google_client_id,
                settings.google_client_secret.get_secret_value(),
                settings.business_timezone,
            )
            sheets_engine = GoogleSheetsExecutionEngine(
                sheets_service, fallback=gmail_engine
            )
            executor = sheets_engine
            if settings.groq_api_key is not None:
                extractor = GroqMeetingDetailsExtractor(
                    settings.groq_api_key.get_secret_value(),
                    settings.groq_fast_model,
                    settings.business_timezone,
                    settings.default_meeting_duration_minutes,
                )
                executor = GoogleWorkspaceExecutionEngine(
                    self.store,
                    settings.google_client_id,
                    settings.google_client_secret.get_secret_value(),
                    extractor,
                    settings.business_timezone,
                    fallback=sheets_engine,
                )
        self.graph = build_main_agent(
            planner,
            self.registry,
            execution_engine=executor,
            access_controller=AccessController(self.store),
        )
        self.pending_threads: dict[str, str] = {}
        self.lock = RLock()
        self.scheduler = VegaSchedulerService(self.registry, self.start_goal, self.decide)

    @staticmethod
    def initial_state(company_id: str, goal: str) -> dict[str, Any]:
        return {
            "company_id": company_id,
            "owner_goal": goal,
            "plan": None,
            "resolved_agents": [],
            "task": None,
            "access_requests": [],
            "approval_decision": None,
            "execution_results": [],
            "verification_results": [],
            "final_response": "",
            "audit_events": [],
            "errors": [],
        }

    def start_goal(self, company_id: str, goal: str) -> dict[str, Any]:
        thread_id = str(uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        with self.lock:
            result = self.graph.invoke(self.initial_state(company_id, goal), config=config)
            if result.get("__interrupt__"):
                self.pending_threads[thread_id] = company_id
        return format_graph_result(result, thread_id)

    def decide(self, company_id: str, thread_id: str, approved: bool) -> dict[str, Any]:
        with self.lock:
            if self.pending_threads.get(thread_id) != company_id:
                raise KeyError("This approval request is unavailable or already resolved")
            result = self.graph.invoke(
                Command(resume=approved),
                config={"configurable": {"thread_id": thread_id}},
            )
            self.pending_threads.pop(thread_id, None)
        return format_graph_result(result, thread_id)


def format_graph_result(result: dict[str, Any], thread_id: str) -> dict[str, Any]:
    task = result.get("task")
    if result.get("__interrupt__"):
        status = "waiting_approval"
    elif result.get("access_requests"):
        status = "waiting_access"
    elif task is not None:
        status = task.status.value
    else:
        status = "failed"
    return jsonable_encoder(
        {
            "thread_id": thread_id,
            "status": status,
            "message": result.get("final_response") or "Vega has prepared this work.",
            "task": task,
            "plan": result.get("plan"),
            "agents": result.get("resolved_agents", []),
            "access_requests": result.get("access_requests", []),
        }
    )


def runtime(request: Request) -> VegaRuntime:
    return request.app.state.vega


def identity(request: Request) -> dict[str, str]:
    company_id = request.session.get("company_id")
    email = request.session.get("email")
    if not isinstance(company_id, str) or not isinstance(email, str):
        raise HTTPException(status_code=401, detail="Connect Google Workspace to continue")
    return {"company_id": company_id, "email": email}


def csrf_guard(request: Request) -> None:
    supplied = request.headers.get("x-csrf-token", "")
    expected = request.session.get("csrf_token", "")
    if not expected or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="Security token expired; refresh Vega")


Owner = Annotated[dict[str, str], Depends(identity)]
Runtime = Annotated[VegaRuntime, Depends(runtime)]
Csrf = Annotated[None, Depends(csrf_guard)]


def google_oauth_client(request: Request) -> GoogleOAuthClient:
    settings = get_settings()
    if not settings.google_client_id or settings.google_client_secret is None:
        raise HTTPException(status_code=503, detail="Google connection is not configured")
    registry = runtime(request).registry

    def validate_owner(email: str) -> bool:
        if settings.owner_email is not None and not secrets.compare_digest(
            email.lower(), settings.owner_email.lower()
        ):
            return False
        return registry.claim_company(settings.default_company_id, email)

    return GoogleOAuthClient(
        settings.google_client_id,
        settings.google_client_secret.get_secret_value(),
        f"{settings.app_base_url.rstrip('/')}/api/oauth/google/callback",
        secure_connection_store(settings),
        account_validator=validate_owner,
    )


def slack_oauth_client() -> SlackOAuthClient:
    settings = get_settings()
    if not settings.slack_client_id or settings.slack_client_secret is None:
        raise HTTPException(status_code=503, detail="Slack connection is not configured")
    redirect_uri = settings.slack_redirect_uri or (
        f"{settings.app_base_url.rstrip('/')}/api/oauth/slack/callback"
    )
    if not redirect_uri.startswith("https://"):
        raise HTTPException(
            status_code=503,
            detail="Slack needs Vega's public HTTPS callback URL",
        )
    return SlackOAuthClient(
        settings.slack_client_id,
        settings.slack_client_secret.get_secret_value(),
        redirect_uri,
        secure_connection_store(settings),
    )


settings = get_settings()
if settings.app_env == "production" and settings.session_secret is None:
    raise RuntimeError("SESSION_SECRET is required in production")
if settings.app_env == "production" and settings.owner_email is None:
    raise RuntimeError("OWNER_EMAIL is required in production")
session_secret = (
    settings.session_secret.get_secret_value()
    if settings.session_secret is not None
    else secrets.token_urlsafe(48)
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.vega.scheduler.start()
    yield
    await app.state.vega.scheduler.stop()


app = FastAPI(
    title="Vega Business Second Brain",
    version="0.2.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.state.vega = VegaRuntime(settings)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="vega_session",
    same_site="lax",
    https_only=settings.app_env == "production",
    max_age=60 * 60 * 12,
)
app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "media-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(
        WEB_ROOT / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "vega"}


@app.get("/api/session")
def session_status(request: Request) -> dict[str, Any]:
    csrf = request.session.setdefault("csrf_token", secrets.token_urlsafe(24))
    authenticated = "company_id" in request.session and "email" in request.session
    return {
        "authenticated": authenticated,
        "email": request.session.get("email"),
        "company_id": request.session.get("company_id"),
        "csrf_token": csrf,
        "google_connect_url": "/api/oauth/google/start",
    }


@app.post("/api/logout")
def logout(request: Request, _: Csrf) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@app.get("/api/oauth/google/start")
def start_google_oauth(request: Request) -> RedirectResponse:
    company_id = get_settings().default_company_id
    return RedirectResponse(google_oauth_client(request).authorization_url(company_id), 302)


@app.get("/api/oauth/google/callback")
async def complete_google_oauth(request: Request, code: str, state: str) -> RedirectResponse:
    try:
        connection = await google_oauth_client(request).complete(code, state)
    except (GoogleOAuthError, OAuthStateError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    request.session["company_id"] = connection.company_id
    request.session["email"] = connection.account_email
    request.session["csrf_token"] = secrets.token_urlsafe(24)
    return RedirectResponse("/?connected=google", 303)


@app.get("/api/oauth/slack/start")
def start_slack_oauth(owner: Owner) -> RedirectResponse:
    return RedirectResponse(slack_oauth_client().authorization_url(owner["company_id"]), 302)


@app.get("/api/oauth/slack/callback")
async def complete_slack_oauth(request: Request, code: str, state: str) -> RedirectResponse:
    owner_company_id = request.session.get("company_id")
    try:
        await slack_oauth_client().complete(
            code, state, expected_company_id=owner_company_id
        )
    except (SlackOAuthError, OAuthStateError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(f"{get_settings().app_base_url.rstrip('/')}/?connected=slack", 303)


@app.get("/api/providers")
def list_providers() -> list[dict[str, str]]:
    return [
        {"id": OAuthProvider.GOOGLE_WORKSPACE.value, "name": "Google Workspace"},
        {"id": OAuthProvider.SLACK.value, "name": "Slack"},
    ]


@app.get("/api/webhooks/whatsapp", response_class=PlainTextResponse)
def verify_whatsapp_webhook(
    mode: str = Query(alias="hub.mode"),
    verify_token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> PlainTextResponse:
    """Retain Meta's verification endpoint while WhatsApp delivery is disabled."""
    configured = get_settings().whatsapp_verify_token
    if configured is None:
        raise HTTPException(status_code=503, detail="WhatsApp webhook is not configured")
    if mode != "subscribe" or not secrets.compare_digest(
        verify_token, configured.get_secret_value()
    ):
        raise HTTPException(status_code=403, detail="WhatsApp webhook verification failed")
    return PlainTextResponse(challenge)


@app.get("/api/dashboard")
def dashboard(
    owner: Owner,
    vega: Runtime,
) -> dict[str, Any]:
    company = owner["company_id"]
    return jsonable_encoder(
        {
            "connections": vega.store.list_connections(company),
            "agents": vega.registry.list_agents(company),
            "tasks": vega.registry.list_tasks(company),
            "events": vega.registry.list_events(company),
            "contacts": vega.registry.list_contacts(company),
            "schedules": vega.registry.list_schedules(company),
            "metrics": vega.registry.get_business_metrics(company),
            "playbooks": list_playbooks(),
        }
    )


@app.get("/api/playbooks")
def get_playbooks(_owner: Owner) -> list[dict[str, Any]]:
    return list_playbooks()


@app.get("/api/metrics")
def get_metrics(
    owner: Owner,
    vega: Runtime,
) -> dict[str, Any]:
    return jsonable_encoder(vega.registry.get_business_metrics(owner["company_id"]))


@app.get("/api/workforce")
def get_workforce_templates(_owner: Owner) -> list[dict[str, Any]]:
    return [
        {
            "role": template.role,
            "responsibilities": list(template.responsibilities),
            "allowed_tools": list(template.allowed_tools),
            "forbidden_tools": list(template.forbidden_tools),
            "permissions": list(template.permissions),
            "business_rules": list(template.business_rules),
            "risk_level": template.risk_level.value,
        }
        for template in AGENT_TEMPLATES.values()
    ]


@app.get("/api/export")
def export_business_records(
    owner: Owner,
    vega: Runtime,
) -> dict[str, Any]:
    return jsonable_encoder(vega.registry.export_business_records(owner["company_id"]))



@app.get("/api/contacts")
def list_contacts(
    owner: Owner,
    vega: Runtime,
) -> list[dict[str, Any]]:
    return jsonable_encoder(vega.registry.list_contacts(owner["company_id"]))


@app.post("/api/contacts")
def create_contact(
    payload: ContactCreateRequest,
    _: Csrf,
    owner: Owner,
    vega: Runtime,
) -> dict[str, Any]:
    contact = CompanyContact(
        company_id=owner["company_id"],
        name=payload.name,
        role=payload.role,
        phone=payload.phone,
        email=payload.email,
        category=payload.category,
        notes=payload.notes,
    )
    saved = vega.registry.create_contact(contact)
    return jsonable_encoder(saved)


@app.get("/api/schedules")
def list_schedules(
    owner: Owner,
    vega: Runtime,
) -> list[dict[str, Any]]:
    return jsonable_encoder(vega.registry.list_schedules(owner["company_id"]))


@app.post("/api/schedules")
def create_schedule(
    payload: ScheduleCreateRequest,
    _: Csrf,
    owner: Owner,
    vega: Runtime,
) -> dict[str, Any]:
    if not payload.preapproved:
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirm pre-authorization before scheduling. Vega may perform the "
                "external actions described in this workflow at the scheduled time."
            ),
        )
    scheduled = ScheduledTask(
        company_id=owner["company_id"],
        goal=payload.goal,
        run_at=payload.run_at,
        schedule_type=payload.schedule_type,
        cron_expr=payload.cron_expr,
        preapproved=True,
        approved_at=datetime.now(UTC),
    )
    saved = vega.registry.create_schedule(scheduled)
    return jsonable_encoder(saved)


@app.post("/api/schedules/{schedule_id}/run")
def run_schedule_now(
    schedule_id: str,
    _: Csrf,
    owner: Owner,
    vega: Runtime,
) -> dict[str, Any]:
    try:
        schedule = vega.registry.get_schedule(UUID(schedule_id))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid schedule ID") from exc
    if not schedule or schedule.company_id != owner["company_id"]:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    claimed = vega.registry.claim_schedule(schedule.schedule_id, owner["company_id"])
    if claimed is None:
        raise HTTPException(status_code=409, detail="Scheduled task is not pending")
    res = vega.scheduler._execute_scheduled_task(claimed)
    return jsonable_encoder(res)


@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    _: Csrf,
    owner: Owner,
    vega: Runtime,
) -> dict[str, bool]:
    try:
        deleted = vega.registry.delete_schedule(UUID(schedule_id), owner["company_id"])
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid schedule ID") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return {"ok": True}




@app.post("/api/goals")
def create_goal(
    payload: GoalRequest,
    _: Csrf,
    owner: Owner,
    vega: Runtime,
) -> dict[str, Any]:
    try:
        return vega.start_goal(owner["company_id"], payload.goal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Vega could not complete the plan") from exc


@app.post("/api/approvals/{thread_id}")
def decide_approval(
    thread_id: str,
    payload: ApprovalRequest,
    _: Csrf,
    owner: Owner,
    vega: Runtime,
) -> dict[str, Any]:
    try:
        return vega.decide(owner["company_id"], thread_id, payload.approved)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The approved action could not be completed") from exc


@app.get("/api/slack/channels")
def list_slack_channels(
    owner: Owner,
    vega: Runtime,
) -> list[dict[str, object]]:
    try:
        return SlackService(vega.store).list_channels(owner["company_id"])
    except (KeyError, SlackError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/slack/default-channel")
def select_slack_channel(
    payload: ChannelRequest,
    _: Csrf,
    owner: Owner,
    vega: Runtime,
) -> dict[str, object]:
    try:
        return SlackService(vega.store).select_channel(
            owner["company_id"], payload.channel_id
        )
    except (KeyError, SlackError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
