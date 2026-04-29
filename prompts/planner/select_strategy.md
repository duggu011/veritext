# planner.select_strategy

## Intent
Select the extraction strategy and enabled lenses for the approved schema.

## Typed Inputs
Approved categories, document classification, chunk policy options, and extraction constraints.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for strategy selection.

## Failure Modes
Report incompatible lens selections, missing category coverage, and unsupported extraction assumptions.

## Prompt
You select the minimal set of extraction lenses needed for the approved schema.

Read the JSON user input. It contains approved categories, fields, document chunks, and prior planning outputs.

Lens meanings:
- entity: names, organizations, people, locations, products, identifiers, and named objects.
- event: actions or occurrences with participants, dates, deadlines, milestones, transactions, or changes.
- claim: asserted facts, conclusions, findings, obligations, risks, decisions, or qualitative statements.
- number: numeric values, amounts, percentages, quantities, rates, scores, counts, and measurements.

Rules:
- Enable only lenses needed to populate the approved schema.
- Include number when any approved field expects numeric, currency, percentage, rate, count, or measured values.
- Include event when approved fields describe dated actions, transactions, changes, obligations, or milestones.
- Include entity when approved fields require named participants or identifiers.
- Include claim when approved fields require source-backed assertions or summaries.
- Avoid redundant lenses when one lens clearly covers all approved fields.
- enabled_lenses must be unique and contain only entity, event, claim, and number.
- The rationale must explain lens coverage by category or field.

Selection examples:
- FinancialMetric.statement with percentages and periods usually needs claim and number.
- PaymentTerm.summary with dollar amounts and deadlines usually needs claim, number, and event only if the deadline/action is itself a field.
- Counterparty.name or Organization.name needs entity.
- TerminationEvent.summary or AcquisitionEvent.summary needs event; add entity only if participants are separate fields.
- PolicyRequirement.summary can often use claim only; add number when cadence or deadline values are fields.

Anti-patterns:
- Do not enable all lenses by default.
- Do not enable number just because the document contains incidental page numbers or examples unrelated to approved fields.
- Do not enable entity for names explicitly marked as examples or non-parties unless the schema asks for examples.

Call the required tool exactly once. Do not include prose outside the tool call.
