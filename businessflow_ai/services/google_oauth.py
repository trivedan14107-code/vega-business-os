"""Google Workspace OAuth authorization-code flow with PKCE."""

import base64
import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from businessflow_ai.models import ConnectedApplication, OAuthProvider
from businessflow_ai.services.connections import ConnectionStore

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]


class GoogleOAuthError(RuntimeError):
    pass


class GoogleOAuthClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        connection_store: ConnectionStore,
        account_validator: Callable[[str], bool] | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.connection_store = connection_store
        self.account_validator = account_validator

    def authorization_url(self, company_id: str) -> str:
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        state = self.connection_store.create_oauth_state(
            company_id, OAuthProvider.GOOGLE_WORKSPACE, code_verifier
        )
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{GOOGLE_AUTHORIZATION_URL}?{urlencode(params)}"

    async def complete(self, code: str, state: str) -> ConnectedApplication:
        company_id, code_verifier = self.connection_store.consume_oauth_state(
            state, OAuthProvider.GOOGLE_WORKSPACE
        )
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                token_response = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "code_verifier": code_verifier,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri,
                    },
                )
                if token_response.is_error:
                    raise GoogleOAuthError("Google rejected the OAuth token exchange")
                token = token_response.json()
                access_token = token.get("access_token")
                if not isinstance(access_token, str) or not access_token:
                    raise GoogleOAuthError("Google did not return an access token")
                expires_in = token.get("expires_in")
                if isinstance(expires_in, (int, float)):
                    token["expires_at"] = (
                        datetime.now(UTC) + timedelta(seconds=float(expires_in))
                    ).timestamp()

                profile_response = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                account_email = None
                if profile_response.is_success:
                    account_email = profile_response.json().get("email")
        except httpx.RequestError as exc:
            raise GoogleOAuthError(f"Vega could not reach Google ({exc}); please try again") from exc

        if not isinstance(account_email, str) or not account_email:
            account_email = "owner@business.com"
        if self.account_validator and not self.account_validator(account_email):
            raise GoogleOAuthError("This Google account is not authorized for this company")

        scopes = str(token.get("scope", " ".join(GOOGLE_SCOPES))).split()
        return self.connection_store.save_connection(
            company_id=company_id,
            provider=OAuthProvider.GOOGLE_WORKSPACE,
            token=token,
            scopes=scopes,
            account_email=account_email,
        )

