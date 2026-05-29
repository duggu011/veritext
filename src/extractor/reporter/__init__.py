"""Output and audit reporting."""

from extractor.reporter.models import (
    CrossDocumentReport,
    ExtractionRefusalReport,
    ExtractionReport,
    ReportWriteResult,
)
from extractor.reporter.diff import (
    RunDiffWriteResult,
    diff_reports,
    render_run_diff_report_json,
    write_run_diff_report,
)
from extractor.reporter.service import (
    ReporterError,
    render_report_json,
    write_cross_document_report,
    write_refusal_report,
    write_report,
)
from extractor.reporter.signing import (
    ReportSigningError,
    canonical_json_bytes,
    canonical_json_sha256,
    config_sha256,
    file_sha256,
    sign_payload,
    verify_signed_report_manifest,
    verify_payload_signature,
    write_signed_report_manifest,
)
from extractor.reporter.static_provenance import build_static_provenance_artifact
from extractor.reporter.static_provenance_html import (
    StaticProvenanceHtmlError,
    StaticProvenanceHtmlWriteResult,
    render_static_provenance_html,
    write_static_provenance_html,
)

__all__ = [
    "CrossDocumentReport",
    "ExtractionRefusalReport",
    "ExtractionReport",
    "ReporterError",
    "ReportSigningError",
    "ReportWriteResult",
    "RunDiffWriteResult",
    "StaticProvenanceHtmlError",
    "StaticProvenanceHtmlWriteResult",
    "build_static_provenance_artifact",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "config_sha256",
    "diff_reports",
    "file_sha256",
    "render_run_diff_report_json",
    "render_report_json",
    "render_static_provenance_html",
    "sign_payload",
    "verify_signed_report_manifest",
    "verify_payload_signature",
    "write_signed_report_manifest",
    "write_cross_document_report",
    "write_refusal_report",
    "write_report",
    "write_run_diff_report",
    "write_static_provenance_html",
]
