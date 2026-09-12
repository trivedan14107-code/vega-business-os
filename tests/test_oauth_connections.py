"""OAuth state, encrypted token, and capability tests."""

import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from businessflow_ai.models import OAuthProvider
from businessflow_ai.services import ConnectionStore, GoogleOAuthClient, OAuthStateError, TokenVault


class OAuthConnectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "oauth.db"
        self.vault = TokenVault(TokenVault.generate_key())
        self.store = ConnectionStore(self.database, self.vault)
        self.client = GoogleOAuthClient(
            client_id="platform-client-id",
            client_secret="platform-client-secret",
            redirect_uri="http://localhost:8000/api/oauth/google/callback",
            connection_store=self.store,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_authorization_url_uses_pkce_and_server_state(self) -> None:
        url = self.client.authorization_url("company-001")
        query = parse_qs(urlparse(url).query)

        self.assertEqual(query["client_id"], ["platform-client-id"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertNotIn("platform-client-secret", url)
        self.assertTrue(query["state"][0])

    def test_oauth_state_is_single_use(self) -> None:
        url = self.client.authorization_url("company-001")
        state = parse_qs(urlparse(url).query)["state"][0]

        company_id, verifier = self.store.consume_oauth_state(
            state, OAuthProvider.GOOGLE_WORKSPACE
        )
        self.assertEqual(company_id, "company-001")
        self.assertGreater(len(verifier), 40)
        with self.assertRaises(OAuthStateError):
            self.store.consume_oauth_state(state, OAuthProvider.GOOGLE_WORKSPACE)

    def test_tokens_are_encrypted_and_capabilities_are_discovered(self) -> None:
        token = {"access_token": "secret-access-token", "refresh_token": "secret-refresh"}
        self.store.save_connection(
            company_id="company-001",
            provider=OAuthProvider.GOOGLE_WORKSPACE,
            token=token,
            scopes=[
                "openid",
                "email",
                "https://www.googleapis.com/auth/calendar.events",
            ],
            account_email="owner@example.test",
        )

        restored = self.store.get_token("company-001", OAuthProvider.GOOGLE_WORKSPACE)
        capabilities = self.store.available_capabilities("company-001")

        self.assertEqual(restored, token)
        self.assertIn("calendar.create", capabilities)
        self.assertNotIn("gmail.send", capabilities)
        self.assertNotIn("secret-access-token", self.database.read_bytes().decode(errors="ignore"))


if __name__ == "__main__":
    unittest.main()
