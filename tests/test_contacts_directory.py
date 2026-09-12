"""Tests for the company contact directory."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from businessflow_ai.api import app
from businessflow_ai.models import CompanyContact
from businessflow_ai.services.registry import AgentRegistry


class ContactDirectoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_contacts.db"
        self.registry = AgentRegistry(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_contact_directory_starts_empty(self) -> None:
        contacts = self.registry.list_contacts("test-company")
        self.assertEqual(contacts, [])

    def test_create_custom_contact(self) -> None:
        new_contact = CompanyContact(
            company_id="test-company",
            name="Priya Sharma",
            role="Head of Product",
            phone="+91 9876543210",
            email="priya@company.com",
            category="teammate",
            notes="Sprint Manager",
        )
        saved = self.registry.create_contact(new_contact)
        self.assertEqual(saved.name, "Priya Sharma")

        found = self.registry.find_contact("test-company", "Priya")
        self.assertIsNotNone(found)
        self.assertEqual(found.phone, "+91 9876543210")

def test_api_contacts_endpoints() -> None:
    client = TestClient(app)
    res = client.get("/api/contacts")
    assert res.status_code == 401
