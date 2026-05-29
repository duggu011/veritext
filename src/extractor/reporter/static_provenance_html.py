from __future__ import annotations

import html

from extractor.contracts import StaticProvenanceArtifact, StaticProvenanceWarning


def render_static_provenance_html(artifact: StaticProvenanceArtifact) -> str:
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>Veritext Static Provenance - {_e(artifact.run_id)}</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:2rem;line-height:1.45;}",
        "table{border-collapse:collapse;width:100%;margin:1rem 0;}",
        "th,td{border:1px solid #bbb;padding:.4rem;text-align:left;vertical-align:top;}",
        "code,pre{font-family:ui-monospace,monospace;}",
        "mark{background:#fff2a8;padding:0 .1rem;}",
        ".warning{border-left:4px solid #a33;padding:.5rem;margin:.5rem 0;}",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Veritext Static Provenance Artifact</h1>",
        _summary_section(artifact),
        _warnings_section(artifact.warnings),
        _manifest_section(artifact),
        _document_section(artifact),
        _diff_section(artifact),
        _rejection_section(artifact),
        _data_points_section(artifact),
        "</body>",
        "</html>",
    ]
    return "\n".join(parts) + "\n"


def _summary_section(artifact: StaticProvenanceArtifact) -> str:
    rows = (
        ("artifact_schema_version", artifact.artifact_schema_version),
        ("report_schema_version", artifact.report_schema_version),
        ("run_id", artifact.run_id),
        ("doc_id", artifact.doc_id),
        ("generated_at", artifact.generated_at.isoformat()),
        ("schema_id", artifact.schema_id),
        ("schema_hash", artifact.schema_hash),
        ("schema_source_kind", artifact.schema_source_kind),
        ("data_point_count", str(len(artifact.data_point_views))),
    )
    return '<section id="summary"><h2>Summary</h2>' + _definition_table(rows) + "</section>"


def _warnings_section(warnings: tuple[StaticProvenanceWarning, ...]) -> str:
    if not warnings:
        return '<section id="warnings"><h2>Warnings</h2><p>None.</p></section>'
    items = []
    for warning in warnings:
        detail = f"{warning.warning_code} ({warning.severity}): {warning.message}"
        if warning.data_point_id is not None:
            detail = f"{detail} [data_point_id={warning.data_point_id}]"
        items.append(f'<li class="warning"><code>{_e(detail)}</code></li>')
    return '<section id="warnings"><h2>Warnings</h2><ul>' + "".join(items) + "</ul></section>"


def _manifest_section(artifact: StaticProvenanceArtifact) -> str:
    manifest = artifact.manifest_identity
    if manifest is None:
        return '<section id="manifest"><h2>Signed Manifest</h2><p>Not supplied.</p></section>'
    rows = (
        ("artifact_sha256", manifest.artifact.artifact_sha256),
        ("artifact_path", manifest.artifact.artifact_path),
        ("source_sha256s", ", ".join(manifest.source_sha256s)),
        ("text_sha256s", ", ".join(manifest.text_sha256s)),
        ("schema_hashes", ", ".join(manifest.schema_hashes)),
        ("prompt_sha256s", ", ".join(manifest.prompt_sha256s)),
        ("config_sha256", manifest.config_sha256),
        ("audit_digest_sha256", manifest.audit_digest_sha256),
        ("audit_chain_head_sha256", manifest.audit_chain_head_sha256),
        ("signature_key_id", manifest.signature_key_id),
    )
    return (
        '<section id="manifest"><h2>Signed Manifest</h2>'
        + _definition_table(rows)
        + "</section>"
    )


def _document_section(artifact: StaticProvenanceArtifact) -> str:
    document = artifact.document_summary
    if document is None:
        return '<section id="document"><h2>Document</h2><p>Not supplied.</p></section>'
    rows = (
        ("source_path", document.source_path),
        ("format", document.format),
        ("source_sha256", document.source_sha256),
        ("text_sha256", document.text_sha256),
        ("source_byte_length", str(document.source_byte_length)),
        ("text_byte_length", str(document.text_byte_length)),
        ("page_count", str(document.page_count)),
    )
    return '<section id="document"><h2>Document</h2>' + _definition_table(rows) + "</section>"


def _diff_section(artifact: StaticProvenanceArtifact) -> str:
    diff = artifact.diff_summary
    if diff is None:
        return '<section id="diff"><h2>Run Diff</h2><p>Not supplied.</p></section>'
    rows = [("diff_run_id", diff.diff_run_id)]
    rows.extend((kind, str(count)) for kind, count in sorted(diff.summary_counts.items()))
    return '<section id="diff"><h2>Run Diff</h2>' + _definition_table(tuple(rows)) + "</section>"


def _rejection_section(artifact: StaticProvenanceArtifact) -> str:
    if not artifact.rejection_summaries:
        return '<section id="rejections"><h2>Rejections</h2><p>None supplied.</p></section>'
    rows = []
    for summary in artifact.rejection_summaries:
        rows.append(
            "<tr>"
            f"<td>{_e(summary.stage)}</td>"
            f"<td>{_e(summary.reason_code)}</td>"
            f"<td>{summary.count}</td>"
            f"<td>{_e(', '.join(summary.candidate_ids))}</td>"
            "</tr>"
        )
    return (
        '<section id="rejections"><h2>Rejections</h2>'
        "<table><thead><tr><th>stage</th><th>reason_code</th><th>count</th>"
        "<th>candidate_ids</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></section>"
    )


def _data_points_section(artifact: StaticProvenanceArtifact) -> str:
    articles = []
    for view in artifact.data_point_views:
        rows = (
            ("data_point_id", view.data_point_id),
            ("category", view.category),
            ("field_name", view.field_name),
            ("value", view.value),
            ("value_canonical", view.value_canonical or ""),
            ("value_kind", view.value_kind),
            ("confidence", str(view.confidence)),
            ("confidence_bucket", view.confidence_bucket or ""),
            ("conflict_status", view.conflict_status),
            ("conflict_group_id", view.conflict_group_id or ""),
            ("conflict_reason", view.conflict_reason or ""),
            ("contributing_candidate_ids", ", ".join(view.contributing_candidate_ids)),
            ("critic_report_ids", ", ".join(view.critic_report_ids)),
            ("verifier_report_ids", ", ".join(view.verifier_report_ids)),
            ("reconciliation_decision_id", view.reconciliation_decision_id),
        )
        articles.append(
            f'<article id="{_attr("data-point-" + view.data_point_id)}">'
            f"<h3>{_e(view.data_point_id)}</h3>"
            + _definition_table(rows)
            + _source_context_section(view.source_context)
            + _warnings_section(view.warnings)
            + "</article>"
        )
    return '<section id="data-points"><h2>Data Points</h2>' + "".join(articles) + "</section>"


def _source_context_section(context) -> str:
    span = context.source_span
    rows = (
        ("offset_status", context.offset_status),
        ("start_char", str(span.start_char)),
        ("end_char", str(span.end_char)),
        ("start_byte", str(span.start_byte)),
        ("end_byte", str(span.end_byte)),
        ("chunk_id", span.chunk_id),
        ("source_span_text", span.text),
        ("mismatch_expected_text", context.mismatch_expected_text or ""),
        ("mismatch_actual_text", context.mismatch_actual_text or ""),
    )
    source = (
        '<pre class="source-context">'
        f'<span class="prefix">{_e(context.prefix_text)}</span>'
        f"<mark>{_e(context.highlighted_text)}</mark>"
        f'<span class="suffix">{_e(context.suffix_text)}</span>'
        "</pre>"
    )
    return "<section><h4>Source Context</h4>" + _definition_table(rows) + source + "</section>"


def _definition_table(rows: tuple[tuple[str, str], ...]) -> str:
    body = "".join(f"<tr><th>{_e(key)}</th><td>{_e(value)}</td></tr>" for key, value in rows)
    return f"<table><tbody>{body}</tbody></table>"


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _attr(value: object) -> str:
    return _e(value)


__all__ = ["render_static_provenance_html"]
