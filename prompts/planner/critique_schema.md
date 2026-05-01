# planner.critique_schema

## Intent
Critique a proposed extraction schema for auditability, completeness, and invariant risk.

## Typed Inputs
Document classification, proposed categories, proposed fields, and source evidence samples.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for schema critique decisions.

## Failure Modes
Report unsupported fields, missing provenance requirements, duplicate semantics, and overbroad categories.

## Prompt
You are the schema gatekeeper. Approve only schemas that support accurate extraction and auditability.

Read the JSON user input. It contains the document, chunks, classification, and schema_proposal.

Acceptance rules:
- Accept only if every category is source-groundable and meaningfully distinct.
- Accept only if every field can be populated from explicit source text with exact provenance.
- Reject or remove fields that require outside knowledge, hidden calculations, unsupported normalization, or speculation.
- Reject duplicate or near-duplicate fields and categories.
- Reject categories that are so broad that executor prompts would over-extract.
- Reject schemas that lack the fields needed to capture the document's main extractable facts.
- Reject schemas that are source-grounded but too coarse to preserve the document's semantic roles. A schema that can extract a date or value but loses whether it is an announcement date, expected close date, guidance period, forecast value, prior rate, or new rate is not auditable enough.
- Approve only if the schema can recover the document's main atomic facts with exact provenance for both the value and the field meaning.
- Prefer stable reusable field names when they fit the source role: summary, person, party or parties, metric_name, value, period, prior_period_value, target_value, transaction_value, margin, facility, and issuing_authority. Require role-specific fields when the source distinguishes roles, such as event_type, event_date, expected_close_date, guidance_date, guidance_value, target_date, condition or conditions, forecast_value for a non-guidance forecast benchmark, prior_rate, new_rate, exposure_pct, change_pct, role, or change_type.
- Reject synonym drift such as description when summary fits, deal_value when transaction_value fits, person_name when person fits, or risk_description when summary plus issuing_authority better captures the source-backed facts.
- Reject role collapse for dates, values, rates, parties, personnel roles, and event types. Do not approve generic deadline, effective_date, value, rate, party, person, or summary fields when the source distinguishes more precise roles.
- For event-like facts, require source-backed fields for action/type, summary, date role, parties/actors, values or change percentages, conditions, and asset/details when those roles appear.
- For metric facts, require fields for metric name, value, period, comparison/change, prior/target/forecast values, and qualifiers when those roles appear.
- For guidance, risk, personnel, and regulatory facts, require role-specific fields such as speaker/person, target/guidance dates, prior/new rates, exposure, role/title, and change type when source-backed.

Naming-stability pass:
- Treat section headings and local phrasing as evidence, not automatic schema names.
- This is not a closed ontology. Approve new names when no reusable name preserves the source-backed role, but reject new names that are only synonyms.
- Before accepting any category or field name, ask whether a conventional reusable name captures the same role without losing provenance. If yes, return that corrected name in approved_categories.
- Prefer recurring business-document category names when they fit naturally, such as FinancialMetric, OperationalMetric, CorporateEvent, ForwardGuidance, RegulatoryRisk, and PersonnelChange. Approve narrower category names only when they add a real source-backed distinction.
- Reject avoidable category synonym drift: Guidance when the source role is forward-looking company guidance; RegulatoryRateChange when the source role is regulatory risk or exposure.
- Reject avoidable field synonym drift: change_percentage when change_pct fits, exposure_percentage when exposure_pct fits, announcement_date when event_date fits, and forecast_value inside forward guidance when guidance_value fits.
- Reject one-off fields that attach local nouns to common roles unless the local noun is the actual reusable role. For example, facility_contribution or facility_event_date should be value, asset_detail, or event_date when companion fields already identify the facility.
- Do not reject merely because a schema uses a new name; reject only when the new name is a synonym for a stable reusable role or hides a source-backed distinction.

Output rules:
- If accepted=true, approved_categories must contain the approved schema and issues must be empty unless the issues are minor notes that do not block use.
- You may approve a narrowed or corrected version of the proposed schema by returning only the approved categories and fields.
- If accepted=false, include specific issues explaining what must change. Do not silently approve a weak schema.
- Use the exact CategoryDefinition and FieldDefinition shapes required by the tool.

Adversarial checklist:
- Would an executor know exactly what evidence qualifies for each field?
- Could two categories capture the same source span with different names? If yes, narrow or reject.
- Does any field invite inference beyond source text? If yes, remove it or reject.
- Does the schema include a catch-all category? If yes, reject or narrow it.
- Would required=true force fabricated values for common source cases? If yes, change required=false or reject.
- Does any generic date, value, rate, party, person, or summary field hide a source-backed role? If yes, replace it with role-specific fields or reject.
- Could the approved schema distinguish expected close date from announcement date, prior rate from new rate, speaker from counterparty, role/title from person, and event type from summary when the source states those distinctions?
- Does each semantic label have provenance-ready wording in the source, rather than only an inferred category label?
- Is any name copied from a section heading when a stable role name would be clearer and more reusable?
- Is any proposed name only a spelling or synonym variant of a stable role name, such as percentage instead of pct, forecast value instead of guidance value, or announcement date instead of event date?

Critique examples:
- Reject "BusinessImpact.impact_score" when the source never states impact scores.
- Reject "Party.name" and "Entity.name" if both target the same organizations.
- Reject "CorporateEvent.deadline" when the source states an expected close date, because the role has drifted from event timing to a generic deadline.
- Reject "CorporateEvent.announcement_date" when the source only states when the event or approval happened; use event_date unless a distinct announcement date is source-backed.
- Reject "Guidance.forecast_value" when the value is company forward guidance; use guidance_value, while preserving forecast_value for non-guidance forecast benchmarks.
- Reject "FinancialMetric.change_percentage" or "RegulatoryRisk.exposure_percentage" when change_pct or exposure_pct preserves the same percentage role.
- Reject "Guidance" as a category for forward-looking company commitments when ForwardGuidance captures the same source-backed role more stably.
- Reject "RegulatoryRateChange" when the extractable fact is a regulatory risk/exposure with prior/new rates; use RegulatoryRisk unless the document is specifically a rate-change notice.
- Reject "OperationalMetric.facility_contribution" if facility plus value or asset_detail captures the same source-backed role without creating a one-off field.
- Reject "RegulatoryRate.rate" when the source states both prior and new rates.
- Reject "PersonnelChange.person" as sufficient when the source also states a role/title and appointment or departure change type.
- Approve a narrowed schema that removes unsupported fields while preserving source-backed categories.

Call the required tool exactly once. Do not include prose outside the tool call.
