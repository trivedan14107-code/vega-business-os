"""Slack workspace OAuth installation for Vega."""

from urllib.parse import urlencode

import httpx

from businessflow_ai.models import ConnectedApplication, OAuthProvider
from businessflow_ai.services.connections import ConnectionStore, OAuthStateError

SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
SLACK_SCOPES = ["chat:write", "channels:read", "groups:read"]


class SlackOAuthError(RuntimeError):
    pass


class SlackOAuthClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        connection_store: ConnectionStore,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.connection_store = connection_store
        self.http = http_client

    def authorization_url(self, company_id: str) -> str:
        state = self.connection_store.create_oauth_state(
            company_id, OAuthProvider.SLACK, "not-used-by-slack"
        )
        params = {
            "client_id": self.client_id,
            "scope": ",".join(SLACK_SCOPES),
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return f"{SLACK_AUTHORIZE_URL}?{urlencode(params)}"

    async def complete(
        self, code: str, state: str, expected_company_id: str | None = None
    ) -> ConnectedApplication:
        company_id, _ = self.connection_store.consume_oauth_state(
            state, OAuthProvider.SLACK
        )
        if expected_company_id is not None and company_id != expected_company_id:
            raise OAuthStateError("Slack authorization belongs to another company")
        try:
            if self.http is not None:
                response = await self.http.post(
                    SLACK_TOKEN_URL,
                    auth=(self.client_id, self.client_secret),
                    data={"code": code, "redirect_uri": self.redirect_uri},
                )
            else:
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.post(
                        SLACK_TOKEN_URL,
                        auth=(self.client_id, self.client_secret),
                        data={"code": code, "redirect_uri": self.redirect_uri},
                    )
        except httpx.RequestError as exc:
            raise SlackOAuthError("Vega could not reach Slack; please try again") from exc
        payload = response.json() if response.is_success else {}
        if response.is_error or payload.get("ok") is not True:
            raise SlackOAuthError("Slack rejected the workspace connection")
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise SlackOAuthError("Slack did not return a bot access token")
        scopes = str(payload.get("scope", "")).split(",")
        token = {
            "access_token": access_token,
            "token_type": payload.get("token_type", "bot"),
            "bot_user_id": payload.get("bot_user_id"),
            "app_id": payload.get("app_id"),
            "team": payload.get("team", {}),
        }
        return self.connection_store.save_connection(
            company_id=company_id,
            provider=OAuthProvider.SLACK,
            token=token,
            scopes=[scope for scope in scopes if scope],
            account_email=None,
        )
