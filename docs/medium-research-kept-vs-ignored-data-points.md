# Medium Research Run: Kept vs Ignored Data Points

This report is local evidence for what the pipeline kept and what it ignored from `evals/fixtures/medium_research_brief/source.md`. It uses the evaluation fixture as the source-backed expectation list, the final JSON output, and the audit DB for stage-by-stage proof.

## Inputs

- Run ID: `medium-research-executor-check-20260502-044644`
- Source: `source.md` under `evals/fixtures/medium_research_brief/`
- Output: `outputs/medium-research-executor-check-20260502-044644.json`
- Output SHA-256: `7215ebe521316874e32bc6554c241c09a09659668b8d80542e50d360fa4c8d11`
- Audit DB: `.veritext/audit.sqlite3`
- Manifest: `completed`, completed at `2026-05-02T10:33:36.870980Z`

## Score Summary

| Metric | Value |
|---|---:|
| `expected_count` | 53 |
| `actual_count` | 58 |
| `true_positives` | 50 |
| `false_positives` | 8 |
| `false_negatives` | 3 |
| `precision` | 0.862 |
| `recall` | 0.943 |
| `f1` | 0.901 |
| `exact_provenance_matches` | 50 |
| `provenance_recall` | 0.943 |
| `invariant_violations` | 0 |

## Audit Artifact Counts

| Artifact | Count |
|---|---:|
| `plans` | 1 |
| `candidates` | 182 |
| `critic_reports` | 182 |
| `verifier_reports` | 171 |
| `data_points` | 58 |
| `rejections` | 124 |

| Rejection stage | Count |
|---|---:|
| `critic` | 8 |
| `dedup` | 111 |
| `verifier` | 5 |

## Ignored Expected Data Points

These are source-backed expected points from the original document that did not survive into a matching final data point.

### exp-000 — `CorporateEvent.asset_detail`

- Expected value: `Atacama-1 in Chile commenced operation January 22, 2026, contributing 312 gigawatt-hours.`
- Original source span: chars `549-638`, bytes `551-640`
- Original source text: `Atacama-1 in Chile commenced operation January 22, 2026, contributing 312 gigawatt-hours.`
- Exact executor candidate count: `1`
  - Candidate `candidate-7a0ab068482fbedff1242dbce88956d7`: lens `event`, confidence `0.82`, span chars `549-638`, span text `Atacama-1 in Chile commenced operation January 22, 2026, contributing 312 gigawatt-hours.`
    - Critic: accepted
    - Verifier: rejected: `schema_violation`: asset_detail field is for asset/facility details (e.g. Northwind); this span describes a CorporateEvent (commencement), not an asset detail of an acquisition target.
    - Rejection row `verifier`: `schema_violation`: asset_detail field is for asset/facility details (e.g. Northwind); this span describes a CorporateEvent (commencement), not an asset detail of an acquisition target.
- Pinpoint: the exact candidate is present and critic accepted it; verifier rejected a schema-approved, source-supported `asset_detail` span.

### exp-018 — `FinancialMetric.period`

- Expected value: `Q1 2026`
- Original source span: chars `173-180`, bytes `175-182`
- Original source text: `Q1 2026`
- Exact executor candidate count: `2`
  - Candidate `candidate-c1b1907b08dd969b5d43fd21743933db`: lens `entity`, confidence `0.98`, span chars `173-180`, span text `Q1 2026`
    - Critic: rejected: medium `critic_rejected`: period field requires a specific metric context; this span alone ('Q1 2026') is too vague without a metric_name to anchor the FinancialMetric record.
    - Rejection row `critic`: `critic_rejected`: medium issue critic_rejected: period field requires a specific metric context; this span alone ('Q1 2026') is too vague without a metric_name to anchor the FinancialMetric record.
  - Candidate `candidate-ea977cf1d7c9b115535c05cb19693448`: lens `claim`, confidence `0.99`, span chars `173-180`, span text `Q1 2026`
    - Dedup: merged into `candidate-c1b1907b08dd969b5d43fd21743933db`
    - Critic: rejected: medium `critic_rejected`: period field requires a specific metric context; this span alone ('Q1 2026') is too vague without a metric_name to anchor the FinancialMetric record.
- Pinpoint: exact period candidates are present, but critic rejected the atomic period field because the span alone lacks metric context. The pipeline stores fields atomically, so this is an over-rejection.

### exp-048 — `RegulatoryRisk.exposure_pct`

- Expected value: `Approximately 18%`
- Original source span: chars `1309-1326`, bytes `1311-1328`
- Original source text: `Approximately 18%`
- Exact executor candidate count: `3`
  - Candidate `candidate-9ca421047454fce6797e69ad1f0ab487`: lens `event`, confidence `0.99`, span chars `1309-1326`, span text `Approximately 18%`
    - Dedup: merged into `candidate-2870b8ef0a178a16b20d8aa5783678e8`
    - Critic: rejected: high `invalid_correction`: Critic correction failed invariant validation.
  - Candidate `candidate-2870b8ef0a178a16b20d8aa5783678e8`: lens `number`, confidence `0.99`, span chars `1309-1326`, span text `Approximately 18%`
    - Critic: rejected: high `invalid_correction`: Critic correction failed invariant validation.
    - Rejection row `critic`: `invented_span`: Corrected candidate span_text does not match the chunk slice at start_char 1325.
  - Candidate `candidate-ec345ce5f82a444b90c095e71532bb53`: lens `claim`, confidence `0.99`, span chars `1309-1326`, span text `Approximately 18%`
    - Dedup: merged into `candidate-2870b8ef0a178a16b20d8aa5783678e8`
    - Critic: rejected: high `invalid_correction`: Critic correction failed invariant validation.
- Pinpoint: exact qualified percentage candidates are present, but critic rejected after an invalid correction whose replacement span did not match the chunk. The valid original was not preserved.

## Kept Expected Data Points

These expected points from the original document survived into final data points. All 50 have exact provenance according to the scorer.

| Expected ID | Field | Final Data Point | Value | Source Span |
|---|---|---|---|---|
| `exp-001` | `CorporateEvent.asset_detail` | `datapoint-9c403b74cb21462acda2485f611f9c94` | `1.85 gigawatt-hours across seven U.S. states` | `1.85 gigawatt-hours across seven U.S. states` |
| `exp-002` | `CorporateEvent.conditions` | `datapoint-a8281339d464aac312f18f665bf6ea0d` | `subject to FERC and CFIUS review` | `subject to FERC and CFIUS review` |
| `exp-003` | `CorporateEvent.event_date` | `datapoint-adeaec76b9e3de16eb592341c273eb3e` | `March 28, 2026` | `March 28, 2026` |
| `exp-004` | `CorporateEvent.event_type` | `datapoint-8bc7ac86249e1a5a4cbf476c0d7c3032` | `Facility commencement` | `commenced operation` |
| `exp-005` | `CorporateEvent.event_type` | `datapoint-836b472accaf6cc6f2e2cc228148bf56` | `Acquisition approval` | `approved acquiring` |
| `exp-006` | `CorporateEvent.expected_close_date` | `datapoint-da8683b99c05dc8b075363be4be268fa` | `September 30, 2026` | `September 30, 2026` |
| `exp-007` | `CorporateEvent.parties` | `datapoint-6597ca46d0bd0916184090113cd823e3` | `Northwind Storage` | `Northwind Storage` |
| `exp-008` | `CorporateEvent.summary` | `datapoint-ef05cb95265b03d509e7bed49990bfae` | `Atacama-1 in Chile commenced operation January 22, 2026, contributing 312 gigawatt-hours.` | `Atacama-1 in Chile commenced operation January 22, 2026, contributing 312 gigawatt-hours.` |
| `exp-009` | `CorporateEvent.summary` | `datapoint-d8522587e2da79812d939dfce8afb4b7` | `On March 28, 2026, the board approved acquiring Northwind Storage, a Reno, Nevada battery operator, for $1.24 billion.` | `On March 28, 2026, the board approved acquiring Northwind Storage, a Reno, Nevada battery operator, for $1.24 billion.` |
| `exp-010` | `CorporateEvent.transaction_value` | `datapoint-2657fe44349c27c0eb974161f6ed2612` | `$1.24 billion` | `$1.24 billion` |
| `exp-011` | `FinancialMetric.change_pct` | `datapoint-f0aeb3db952f63405c7eafde111742b2` | `up 17.4%` | `up 17.4%` |
| `exp-012` | `FinancialMetric.forecast_value` | `datapoint-65afcd531b6cdea2f6114badb20a36b4` | `$88.0 million` | `$88.0 million` |
| `exp-013` | `FinancialMetric.margin` | `datapoint-8ff1a0d7ff41a6946350c574f9eb1e99` | `19.5%` | `19.5%` |
| `exp-014` | `FinancialMetric.metric_name` | `datapoint-a8a824a431a6d1dec32931ef64597194` | `Revenue` | `revenue` |
| `exp-015` | `FinancialMetric.metric_name` | `datapoint-3be0f1fdc3eb8eb8eb164930fdebccb9` | `Adjusted EBITDA` | `Adjusted EBITDA` |
| `exp-016` | `FinancialMetric.metric_name` | `datapoint-97b406b7e067e61e9b84506a5cd57873` | `Free cash flow` | `Free cash flow` |
| `exp-017` | `FinancialMetric.notable_qualifier` | `datapoint-8592b0686d35698d672ca9a87aec1d61` | `for the first time in eight quarters` | `for the first time in eight quarters` |
| `exp-019` | `FinancialMetric.prior_period_value` | `datapoint-794488b59c43c1f3b96f5634fd0696a4` | `$410.8 million in Q1 2025` | `$410.8 million in Q1 2025` |
| `exp-020` | `FinancialMetric.value` | `datapoint-782fb447e1b57830ba9a0b860be71182` | `$482.3 million` | `$482.3 million` |
| `exp-021` | `FinancialMetric.value` | `datapoint-445ae7d068e29aa478a4709a0169e3b5` | `$94.1 million` | `$94.1 million` |
| `exp-022` | `FinancialMetric.value` | `datapoint-aeb44839fff812967eecf5031e7af38e` | `$12.6 million` | `$12.6 million` |
| `exp-023` | `ForwardGuidance.condition` | `datapoint-683c61b06084717148f38bc7e779960b` | `at least 60% under long-term offtake at signing` | `at least 60% under long-term offtake at signing` |
| `exp-024` | `ForwardGuidance.guidance_date` | `datapoint-044eb7144a5d20860a762a30975f7946` | `April 9, 2026` | `April 9, 2026` |
| `exp-025` | `ForwardGuidance.guidance_value` | `datapoint-d5d72f395b8fb5130ff829470983a251` | `at least 4.2 gigawatts` | `at least 4.2 gigawatts` |
| `exp-026` | `ForwardGuidance.guidance_value` | `datapoint-e4f9acd8b89229c52ab9758193026332` | `$2.10 to $2.25 billion` | `$2.10 to $2.25 billion` |
| `exp-027` | `ForwardGuidance.metric_name` | `datapoint-d7cfd4f67ef6ba65cd86aedcacdc3962` | `Full-year 2026 revenue` | `Full-year 2026 revenue` |
| `exp-028` | `ForwardGuidance.speaker` | `datapoint-b6b5b911dc3912e6116519a734f8ee5d` | `Marcus Bell` | `Marcus Bell` |
| `exp-029` | `ForwardGuidance.target_date` | `datapoint-bc528ed567c10112af00fde2cd8c02be` | `December 31, 2027` | `December 31, 2027` |
| `exp-030` | `OperationalMetric.change_pct` | `datapoint-0535e5c6ce6d2d2c9ea211f37405ed1d` | `up 11.2%` | `up 11.2%` |
| `exp-031` | `OperationalMetric.facility` | `datapoint-5fe1571dfc2b51ee12b6734ed6067fe1` | `Atacama-1` | `Atacama-1` |
| `exp-032` | `OperationalMetric.metric_name` | `datapoint-7a0d0575e25bcbc064bfb43ea40a8ba4` | `Fleet generation` | `Fleet generation` |
| `exp-033` | `OperationalMetric.metric_name` | `datapoint-96689a81f36507fbb45db31b75afa2a9` | `Solar capacity factor` | `Solar capacity factor` |
| `exp-034` | `OperationalMetric.prior_period_value` | `datapoint-d28a0165973d2ebf4d0eaf8d7f2eec8e` | `6,581 in Q1 2025` | `6,581 in Q1 2025` |
| `exp-035` | `OperationalMetric.target_value` | `datapoint-46721b4ef8392b63883adb69753d7589` | `29.0%` | `29.0%` |
| `exp-036` | `OperationalMetric.value` | `datapoint-671fe3ab9881353ebb320d72170c98f5` | `7,318 gigawatt-hours` | `7,318 gigawatt-hours` |
| `exp-037` | `OperationalMetric.value` | `datapoint-da64e048ddc0fcf0df1964dca39b6469` | `28.4%` | `28.4%` |
| `exp-038` | `OperationalMetric.value` | `datapoint-1712808fce9bf97f54417f56b2a77c6a` | `312 gigawatt-hours` | `312 gigawatt-hours` |
| `exp-039` | `PersonnelChange.change_type` | `datapoint-a875ba771009ce4616d5942de309910a` | `Appointment` | `appointed` |
| `exp-040` | `PersonnelChange.change_type` | `datapoint-2fb38ac288d0cca4f0c8d454028cd67b` | `Retirement` | `retirement` |
| `exp-041` | `PersonnelChange.effective_date` | `datapoint-36ec4c1d084eab412c1160a38bd88f20` | `February 2, 2026` | `February 2, 2026` |
| `exp-042` | `PersonnelChange.effective_date` | `datapoint-b909ad016e5983cfe19149e1a944cf5d` | `June 18, 2026 Annual Meeting` | `June 18, 2026 Annual Meeting` |
| `exp-043` | `PersonnelChange.person` | `datapoint-fb6e52da67614dc83d81d8b4095b4561` | `Dr. Anya Kowalski` | `Dr. Anya Kowalski` |
| `exp-044` | `PersonnelChange.person` | `datapoint-9ea3d64a6d32fc0006c34cde1a48d06b` | `Hiroshi Tanaka` | `Hiroshi Tanaka` |
| `exp-045` | `PersonnelChange.role` | `datapoint-a77b0567bef1781995a33a0045c37a12` | `Chief Sustainability Officer` | `Chief Sustainability Officer` |
| `exp-046` | `PersonnelChange.role` | `datapoint-bf7c6f6441544f0477fa9c164aeaec5d` | `Director` | `Director` |
| `exp-047` | `RegulatoryRisk.effective_date` | `datapoint-d8553429fb83f3dfecc88dd35b77d640` | `March 6, 2026` | `March 6, 2026` |
| `exp-049` | `RegulatoryRisk.issuing_authority` | `datapoint-1cbe1a50dea7bbc82dd280350812a39f` | `U.S. Department of Commerce` | `U.S. Department of Commerce` |
| `exp-050` | `RegulatoryRisk.new_rate` | `datapoint-af7f24ce21f0a02eb74643bc907bfc9c` | `26.5%` | `26.5%` |
| `exp-051` | `RegulatoryRisk.prior_rate` | `datapoint-df90d2b2c947415a9fbc73c640fe1375` | `15.0%` | `15.0%` |
| `exp-052` | `RegulatoryRisk.summary` | `datapoint-41587fa9aa7d7e681e7cb53f91baf4bd` | `The U.S. Department of Commerce raised module countervailing duties from 15.0% to 26.5% on March 6, 2026.` | `The U.S. Department of Commerce raised module countervailing duties from 15.0% to 26.5% on March 6, 2026.` |

## Extra Kept Data Points Not In Expected Set

These are final data points kept by the pipeline but counted as false positives by the eval fixture.

| Data Point | Field | Value | Source Span | Contributors |
|---|---|---|---|---|
| `datapoint-c540038c7abafb35a44433d6ccf52a6f` | `CorporateEvent.event_date` | `January 22, 2026` | `January 22, 2026` | `candidate-06e6fe85d39761a3cd2b6624b428c597`, `candidate-3d95490301b2a46e44de34c934ad2088`, `candidate-6b944c163a351d2a9f4d8f334031aeec` |
| `datapoint-c8598c79bc2a105cf1df5c5e688f275f` | `ForwardGuidance.change_type` | `reaffirmed` | `reaffirmed` | `candidate-e8ff16053c610b423318ba8e3e37115e`, `candidate-76944da36a876e1a4bde355d104f3c7b`, `candidate-d5cccf74c9d9c647060f08a137669172` |
| `datapoint-cd5142b429b85e4762ad35a7fb4834ce` | `ForwardGuidance.metric_name` | `new solar capacity` | `new solar capacity` | `candidate-a07908d0ee437e88efe52e3edb48695e`, `candidate-3346b4814ddd3cd2463a4698637f5b19`, `candidate-8bb615d2f8d9b99dc8d7004997dcab70` |
| `datapoint-15e1651d667edc16c0a053a3e6630418` | `ForwardGuidance.period` | `Full-year 2026` | `Full-year 2026` | `candidate-fb867b495d9d820975586fe83c249edc`, `candidate-b769366c0188f7999c63d25b3882c1b5` |
| `datapoint-b70dddcfe71fd0a7aebead3c756e1c32` | `OperationalMetric.period` | `Q1 2026` | `Q1 2026` | `candidate-593c7e57c55b125ef956bafffdea1974` |
| `datapoint-976cced940e7af9335acd2bbef45296d` | `RegulatoryRisk.exposure_pct` | `18%` | `18%` | `candidate-ea75656aef828d78da428b651444da61` |
| `datapoint-c97b3516822a6bea8dd8bd40ce98b52f` | `RegulatoryRisk.period` | `2026 module pipeline` | `2026 module pipeline` | `candidate-4e37b0812489a47d76f5cf01dfa06249`, `candidate-ec44d35316bb645c9f3084307522ef7e` |
| `datapoint-e4c403bf03e95446afc01837ec43f6fd` | `RegulatoryRisk.period` | `2026 module pipeline` | `2026 module pipeline` | `candidate-f876f0e3b7159fb7d9f522d3c6405d71` |

## Bottom Line

- The pipeline is not failing to produce candidates for the ignored data points; exact candidates exist for all 3 ignored expected IDs.
- Two losses are critic-stage over-rejections (`exp-018`, `exp-048`).
- One loss is verifier-stage over-rejection (`exp-000`).
- The next code phase should target those downstream guardrails only, without changing planner or executor behavior.
