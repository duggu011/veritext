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
- definition: defined terms, meanings, source-stated role definitions, control definitions, endpoint definitions, and terminology.
- citation: source references, section references, exhibit/table/figure references, statute or regulation citations, standards clauses, and document cross-references.
- temporal: dates, deadlines, periods, or durations when time itself is the approved field target.
- quantity_with_unit: quantities whose unit or scope is part of the field meaning.

Rules:
- Enable only lenses needed to populate the approved schema.
- Include number when any approved field expects numeric, currency, percentage, rate, count, or measured values.
- Include event when approved fields describe dated actions, transactions, changes, obligations, or milestones.
- Include entity when approved fields require named participants or identifiers.
- Include claim when approved fields require source-backed assertions or summaries.
- Include definition when approved fields ask for a term, definition text, defined meaning, glossary entry, control definition, endpoint definition, or source-stated terminology.
- Include citation when approved fields ask for a section, clause, citation, authority, exhibit, table, figure, docket, policy reference, standard control, or cross-reference.
- Include temporal when approved fields ask for dates, deadlines, periods, durations, windows, effective times, review periods, or time-based source facts.
- Include quantity_with_unit when approved fields ask for a quantity whose unit, denominator, cadence, rate basis, dosage basis, capacity unit, or measurement scope is part of the field meaning.
- Avoid redundant lenses when one lens clearly covers all approved fields.
- enabled_lenses must be unique and contain only supported executable lenses: entity, event, claim, number, definition, citation, temporal, and quantity_with_unit.
- The rationale must explain lens coverage by category or field.

Selection examples:
- FinancialMetric.statement with percentages and periods usually needs claim and number.
- PaymentTerm.summary with dollar amounts and deadlines usually needs claim, number, and event only if the deadline/action is itself a field.
- Counterparty.name or Organization.name needs entity.
- TerminationEvent.summary or AcquisitionEvent.summary needs event; add entity only if participants are separate fields.
- PolicyRequirement.summary can often use claim only; add number when cadence or deadline values are fields.
- ContractDefinition.definition_text or GlossaryTerm.meaning needs definition.
- RegulationCitation.reference or StandardControl.clause needs citation.
- Deadline.date or PolicyPeriod.duration needs temporal.
- DosageInstruction.amount, CapacityMetric.measurement, or AvailabilityMetric.rate needs quantity_with_unit when the unit or denominator is part of the field meaning.

Anti-patterns:
- Do not enable all lenses by default.
- Do not enable number just because the document contains incidental page numbers or examples unrelated to approved fields.
- Do not enable entity for names explicitly marked as examples or non-parties unless the schema asks for examples.
- Do not enable citation merely because a document has numbered headings; the approved field must ask for the reference itself.
- Do not enable temporal merely because an event sentence contains a date when event extraction already covers the approved field.
- Do not enable quantity_with_unit for bare numbers when the approved field does not require unit or scope.

Call the required tool exactly once. Do not include prose outside the tool call.
