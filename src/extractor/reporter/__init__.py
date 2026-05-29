"""Output and audit reporting."""

from extractor.reporter.models import (
    CrossDocumentReport,
    ExtractionRefusalReport,
    ExtractionReport,
    ReportWriteResult,
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
    verify_payload_signature,
)

__all__ = [
    "CrossDocumentReport",
    "ExtractionRefusalReport",
    "ExtractionReport",
    "ReporterError",
    "ReportSigningError",
    "ReportWriteResult",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "config_sha256",
    "file_sha256",
    "render_report_json",
    "sign_payload",
    "verify_payload_signature",
    "write_cross_document_report",
    "write_refusal_report",
    "write_report",
]
