"""Tests for zero-dependency executive PDF report generator."""

from pathlib import Path

from starlette.testclient import TestClient

from businessflow_ai.api import app
from businessflow_ai.services.pdf_generator import ExecutivePDFReportGenerator


def test_pdf_generator_builds_valid_pdf(tmp_path: Path):
    generator = ExecutivePDFReportGenerator(output_dir=tmp_path)
    pdf_bytes = generator.build_pdf_bytes(
        title="Weekly Sprint Brief",
        subtitle="Sprint 42 Chat Synthesis",
        channel_or_source="#product-engineering",
        summary_text="Team closed 14 tickets. Staging database migration completed successfully.",
        action_items=["Deploy v2.4 to production", "Review QA metrics"],
    )

    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_bytes
    assert len(pdf_bytes) > 1000


def test_pdf_generator_creates_file_and_url(tmp_path: Path):
    generator = ExecutivePDFReportGenerator(output_dir=tmp_path)
    file_path, download_url = generator.generate_slack_summary_pdf(
        task_id="test-task-12345",
        channel_name="#general",
        summary_text="Discussion covered quarterly revenue targets and new enterprise leads.",
    )

    assert file_path.is_file()
    assert file_path.stat().st_size > 500
    assert download_url.startswith("/api/reports/vega_slack_summary_")
    assert download_url.endswith(".pdf")


def test_api_serves_pdf_report(tmp_path: Path):
    generator = ExecutivePDFReportGenerator(output_dir=Path("output/reports"))
    _file_path, download_url = generator.generate_slack_summary_pdf(
        task_id="api-test-pdf-999",
        channel_name="#general",
        summary_text="API verification report for PDF download endpoint.",
    )

    client = TestClient(app)
    response = client.get(download_url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-1.4")


def test_api_rejects_malicious_pdf_paths():
    client = TestClient(app)
    response = client.get("/api/reports/../../../etc/passwd")
    assert response.status_code == 400 or response.status_code == 404
