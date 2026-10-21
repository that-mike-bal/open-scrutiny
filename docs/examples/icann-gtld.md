# Worked example: evaluating gTLD strings against the ICANN rulebook

This is the walkthrough of the bundled example: how a public, hundreds-of-pages rulebook became three workflows, six agent roles, twelve task rubrics, and seven tools, and how `CrewBuilder` assembles them into crews. Everything here is read from the shipped configuration under [`crewai_service/evaluation/config/`](../../crewai_service/evaluation/config/); file paths are given so you can check each claim.

Nothing in this document is legal advice, and the example is not affiliated with ICANN. It uses public program materials as a demonstration domain.

## 1. The rulebook

ICANN's [New gTLD Program](https://newgtlds.icann.org/) lets an organisation apply to operate a new top-level domain. The rules are set out in the public **Applicant Guidebook** and its supporting policies. The part this example targets is the **string evaluation**: before anyone looks at the applicant's technical or financial plans, the applied-for string itself is judged. The main checks, in the Guidebook's own vocabulary, are:

| Guidebook concept | What it asks about the string |
|---|---|
| DNS stability review | Is the label syntactically valid and safe to put in the root zone (length, allowed characters, hyphen rules, RFC 1035/1123/2181 conformance, Root Zone Label Generation Rules for non-ASCII)? |
| String similarity review | Is it confusingly similar, visually or otherwise, to an existing TLD, a reserved name, or another applied-for string? |
| Name collision assessment | Do queries for this label already reach the root servers from private networks, so that delegating it would break things? ICANN publishes root-query "DNS magnitude" measurements for this. |
| Geographic names | Is it a country or territory name, a capital, a sub-national place, or a regional name that needs government support or non-objection? |
| Legal Rights Objection | Would a trademark holder have grounds to object, and in which jurisdictions? |
| GAC Early Warning and GAC Advice | Would governments, through the Governmental Advisory Committee, warn against or object to the string? The 2012 round produced 242 Early Warnings, which is the precedent set this example uses. |
| Safeguards | Does the string imply a regulated sector, consumer trust, government function, or potential for harassment, triggering mandatory safeguard commitments? The current application form asks six safeguard questions, numbered Q175 to Q180 in [`data/application_questions.md`](../../data/application_questions.md). |

Two properties make this a hard rulebook. Some checks are **binary gates** with authoritative data behind them (is this label already delegated? is it on the reserved list?). Others are **interpretive** (would France object to this string? does this word mean something offensive in Hindi?) and need precedent, web research, and judgement. The example separates the two: the binary gates run in the client in milliseconds, and the interpretive work goes to the crews.

### The client-side gates

Before any model call, [`client/src/lib/binaryCompliance.ts`](../../client/src/lib/binaryCompliance.ts) checks the string against four local datasets in [`client/public/data/`](../../client/public/data/): the IANA root database (1,571 delegated TLDs), ICANN's reserved names (Specification 5, RFC 2606 and RFC 6761 special-use names, ISO 3166 codes), the ICANN blocked-names list, and the user's own prior evaluations. A hit stops the submission. Sources are credited in [`data/SOURCES.md`](../../data/SOURCES.md).

## 2. From rulebook to workflows

[`workflows.yaml`](../../crewai_service/evaluation/config/workflows.yaml) defines three sequential crews that run one after another for every string:

| Workflow | Rulebook concepts covered | Tasks in order |
|---|---|---|
| `technical_risk_assessment` | DNS stability, string similarity, name collision | `dns_stability_review` → `comprehensive_similarity_analysis` → `name_collision_assessment` → `technical_gut_check` |
| `legal_risk_assessment` | Legal Rights Objection, trademark and patent conflicts | `deep_research_legal_assessment` → `legal_risk_validation` → `legal_gut_check` |
| `policy_safeguard_review` | Geographic names, safeguards, GAC precedent, cultural meaning | `geographic_name_assessment` → `safeguard_assessment` → `cultural_linguistic_assessment` → `gac_risk_analysis` → `policy_gut_check` |

Every workflow sets `process: "sequential"`, `memory: false`, `allow_delegation: false`, and `max_iter: 2`. The legal workflow allows 15 minutes because deep research is slow; the others allow five. The order matters: `app.py` runs them technical first, so a string that is unusable in DNS fails cheaply before any paid research happens.

## 3. The agents

[`agents.yaml`](../../crewai_service/evaluation/config/agents.yaml) declares eight roles. Six carry the three workflows; two are synthesisers kept for reuse.

| Config key | Role | Tools loaded | Ownership | Produces → consumes |
|---|---|---|---|---|
| `string_analyst` | String Technical Analysis Specialist | `string_analyzer`, `similarity_analyzer` | `primary` | `technical_analysis_results` → nothing |
| `collision_analyst` | Collision Risk Analyst | `magnitude_collision_checker` | `exclusive`, `decision_authority: HIGH_RISK/PROCEED`, `collision_threshold: 8.0` | `binary_gate_results` → nothing |
| `trademark_specialist` | Global Legal & IP Risk Analyst | `deep_research_legal_analyzer` | `exclusive`, 10-minute budget | `trademark_conflicts`, `legal_risk_assessment` → `technical_analysis_results` |
| `gac_advisor` | GAC Safeguard Risk Analyst | `brave_web_search`, `similarity_analyzer`, `gac_precedent_analyzer`, `guidebook_search` | `enhanced` | geographic, safeguard, GAC, and cultural risk factors → technical and similarity results |
| `evaluation_validator` | Data Validation & Fact-Checking Specialist | `similarity_analyzer` | `validation`, `validation_mode: true`, `contradiction_detection: true` | `validation_results` → gate and technical results |
| `icann_compliance_specialist` | ICANN Compliance Gatekeeper | none (the binary gates moved to the client) | `exclusive`, `decision_authority: BLOCK/PROCEED` | `binary_gate_results` |
| `risk_assessor` | Risk Synthesis Specialist | none | `none` | `risk_synthesis_results` → every specialist output |
| `report_synthesizer` | Executive Report Compiler | none | `none` | `executive_report` → every specialist output |

Every agent sets `memory: false` and `conservative_bias: true`, and each has its own `max_rpm` and `max_execution_time`. The `backstory` text is the persona prompt; for example the validator's reads, in part, "You validate agent findings against authoritative data sources to catch hallucinations, contradictions, and false claims."

Two things to notice. First, the `tools` list is what the builder loads; `tools.yaml` also names `secondary_agents` for some tools, but that is documentation of intended sharing, not a grant. Second, the compliance gatekeeper and the two synthesisers are declared but not on any workflow roster: the gates run client-side, and report synthesis is done by a prompt after all three crews finish (section 7).

## 4. The tasks and their rubrics

[`tasks.yaml`](../../crewai_service/evaluation/config/tasks.yaml) is the ruleset. Each task has a `description` (the instruction) and an `expected_output` (the rubric-shaped template the agent must fill). Only `{tld_string}` and `{use_case}` are substituted at build time. The excerpts below are short quotes from that file.

### Technical risk assessment

**`dns_stability_review`** (`string_analyst`). A two-tier check. Tier 1 is the fast syntax pass:

> 1. **Character Length Check**: Verify 3-63 characters
> 2. **ASCII Validation**: Ensure only valid ASCII characters (a-z, 0-9, hyphen)
> 3. **Hyphen Position Rules**: No hyphens in 3rd/4th positions, no start/end hyphens
> 4. **Numeric Check**: Cannot be all numeric

Tier 2 runs only if Tier 1 passes and covers Root Zone Label Generation Rules, RFC 1035/1123/2181 conformance, resolver compatibility, and Unicode normalisation, with the rule "For non-ASCII strings: Flag for expert IDN review rather than attempting complex validation." The rubric opens with a status line and reports each tier separately:

> **STATUS:** ✅ PASS / ⚠️ FLAGGED / ❌ BLOCKED
> …
> - **Tier 1 (Basic Compliance)**: ✅ PASS / ❌ FAIL
> - **Tier 2 (Stability Analysis)**: ✅ PASS / ⚠️ FLAGGED / ❌ FAIL / ➡️ SKIPPED
> - **Expert Review Required**: Yes/No

**`comprehensive_similarity_analysis`** (`string_analyst`). Characterises the string (meaning, type, industry), then runs the similarity tool against the IANA database. The description is strict about provenance:

> 1. MUST call "Advanced String Similarity Analyzer" tool with tld_string parameter: '{tld_string}'
> 2. MUST use ONLY the tool output - do NOT generate your own analysis
> 3. MUST report the EXACT similarity scores from the tool output

The rubric fixes the review threshold and the decision vocabulary:

> - **Overall Similarity Risk**: ✅ CLEAR / ⚠️ LOW RISK / 🔶 MEDIUM RISK / 🔴 HIGH RISK / ❌ CRITICAL
> - **Highest Similarity Score**: [0.XX] (Professional Review Threshold: ≥0.6)
> …
> **PROCEED / PROCEED WITH CAUTION / EXPERT REVIEW REQUIRED / BLOCKED**

**`name_collision_assessment`** (`collision_analyst`). Calls the magnitude tool and reports which existing labels carry collision risk. The rubric encodes the thresholds the analyst must apply:

> - **Magnitude Risk Score**: [X.X] (Critical Threshold: ≥8.0)
> …
> ### **High Magnitude Score Trigger**
> - **Triggered**: [Yes/No] (Threshold: ≥6.0)
> ### **Multiple Collision TLDs Trigger**
> - **Triggered**: [Yes/No] (Threshold: ≥3 flagged TLDs)

**`technical_gut_check`** (`string_analyst`). The closing sanity pass, with a deliberately small rubric so it cannot drift into new analysis:

> OUTPUTS REVIEWED: DNS Stability, Similarity Analysis, Collision Assessment
> LOGIC CHECK: [Pass/Fail] - Do the findings make logical sense?
> CONSISTENCY CHECK: [Pass/Fail] - Are the conclusions consistent with evidence?
> COMPLETENESS CHECK: [Pass/Fail] - Are all required elements present?

### Legal risk assessment

**`deep_research_legal_assessment`** (`trademark_specialist`). One deep-research call covers trademarks, patents, and broader IP risk with cited sources. The description is where the rulebook's judgement lives. A textual match is explicitly not a conflict:

> A word matching the TLD string is NOT, by itself, a meaningful conflict. When analyzing each trademark hit, evaluate the REALISTIC likelihood that it would actually pose a problem for the gTLD application, not just whether the text matches. For every match, weigh:
> - Is the holder an active, operating business (not defunct or dissolved)?
> - Does the holder operate in technology, internet, DNS, software, digital services, or online commerce …
> - Do the Nice classes overlap with DNS/internet-relevant ones (9, 35, 38, 41, 42)?

Matches are graded STRONG, MEDIUM, or WEAK, and WEAK matches are excluded from the overall rating. The rubric asks for each conflict's jurisdiction, class, and status, an ICANN-specific block ("Legal Rights Objection Risk", "Rights Protection Adequacy"), and a "CITED SOURCES" section.

**`legal_risk_validation`** (`trademark_specialist`). Re-reads the research as a validator: spot-checks findings, confirms the multi-jurisdiction coverage, and records discrepancies.

> - **Legal Analysis Status**: ✅ VALIDATED / ⚠️ DISCREPANCIES / ❌ ISSUES FOUND
> …
> ## **⚠️ VALIDATION DISCREPANCIES**
> [List any discrepancies between agent findings and validation, or "None identified"]

**`legal_gut_check`** (`trademark_specialist`). Same four-line sanity rubric as the technical gut check.

### Policy safeguard review

**`geographic_name_assessment`** (`gac_advisor`). Classifies the string against the Guidebook's geographic categories (country and territory names, capitals, city names where the use case is city-related, sub-national and regional names) including translations and permutations, then works out which governments would need to consent. The rubric ends in a structured classification:

> - **Geographic Status**: [NON_GEOGRAPHIC/GEOGRAPHIC_SIMPLE/GEOGRAPHIC_COMPLEX/GEOGRAPHIC_CRITICAL]
> - **Recommendation**: [PROCEED/CONDITIONAL/EXPERT_REVIEW/BLOCKED]

**`safeguard_assessment`** (`gac_advisor`). Answers the six safeguard questions one by one, with the instruction "when in doubt, answer YES and require safeguards":

> - `## Q175: Consumer Trust` (with Yes/No and rationale)
> - `## Q176: Consumer Risk` (with Yes/No and rationale)
> - `## Q177: Licensing Requirements` (with Yes/No and rationale)
> - `## Q178: Government Oversight` (with Yes/No and rationale)
> - `## Q179: Harassment Potential` (with Yes/No and rationale)
> - `## Q180: Government Functions` (with Yes/No and rationale)
> - `## Required Safeguard Groups` (list which groups apply)

**`cultural_linguistic_assessment`** (`gac_advisor`). Etymology, meanings across ten major languages, religious and political sensitivity, historical context, script confusables, and false friends. Its own example: "kind" in English has a totally different meaning in German. The rubric scores cultural and language-conflict risk separately and lists regions to avoid.

**`gac_risk_analysis`** (`gac_advisor`). Focuses on government-function conflicts and the precedent set, and asks for an objection likelihood and a diplomatic strategy:

> OVERALL GAC RISK: [LOW/MEDIUM/HIGH/CRITICAL]
> PRECEDENT ANALYSIS: [Brief summary of relevant precedents or "No relevant precedents"]
> …
> GAC OBJECTION LIKELIHOOD: [Low/Medium/High]

**`policy_gut_check`** (`gac_advisor`). The closing sanity pass over all four policy outputs.

### What the rubrics have in common

Every substantive rubric opens with a status line drawn from a fixed vocabulary, names the tools and data it used, separates findings from recommendations, and ends with a confidence block and an "Agent Reasoning Summary". That shape is what the classifier in `app.py` reads (see [ARCHITECTURE.md](../ARCHITECTURE.md#result-classification)): the status words are what `_classify_result_status` keys on, and the fixed layout is what makes a gut check meaningful.

## 5. The tools

[`tools.yaml`](../../crewai_service/evaluation/config/tools.yaml) declares seven tools. All live in [`crewai_service/tools/`](../../crewai_service/tools/).

| Tool key | Class | Backed by | What it returns |
|---|---|---|---|
| `string_analyzer` | `StringAnalyzerTool` | Pure Python | Length, character classes, hyphen rules, DNS compliance issues, a coarse classification, and risk factors for the string |
| `similarity_analyzer` | `SimilarityAnalyzerTool` | IANA root database (`client/public/data/Iana Root DB.json`), `data/string_similarity.json`, `data/visual_confusion.json`, plus one model call | Two-phase result: a model shortlists semantically or visually close TLDs from the full list, then edit-distance, prefix, visual, and phonetic scores are computed for the shortlist |
| `magnitude_collision_checker` | `MagnitudeCollisionTool` | ICANN DNS magnitude data (`data/magnitude_data.json`, `data/Magnitude Data.csv`) and the IANA list | Whether the label is already delegated, its magnitude score if ICANN observed root queries for it, and a risk level against the 8.0 critical threshold; `CLEAR` when no collision data exists |
| `deep_research_legal_analyzer` | `DeepResearchLegalTool` | Gemini Deep Research (needs `GEMINI_API_KEY`) | A structured legal report with cited sources covering USPTO, EUIPO, and WIPO marks, patents, UDRP history, and ICANN-specific objection risk; falls back to model knowledge and says so when the API is unavailable |
| `gac_precedent_analyzer` | `GACPrecedentTool` | `data/gac_precedents.json` (242 GAC Early Warning cases from the 2012 round, by category and outcome) | Matching precedents, a warning likelihood, an outcome prediction, and mitigation strategies |
| `brave_web_search` | `BraveWebSearchTool` | Brave Search API (needs `BRAVE_API_KEY`) | Recent news on political, cultural, and regulatory developments related to the string |
| `guidebook_search` | `GuidebookRAGSearchTool` | pgvector index over the Applicant Guidebook PDF (user-supplied; see `db/README.md`) | Semantic search hits with section references; a "not available" result when the corpus is not loaded |

Each entry also carries `primary_agent`, `access_pattern`, and `data_sources` so a reader can see at a glance who owns the tool and what it reads. External calls go through logged request wrappers, which is how the audit trail attributes API calls to tasks.

## 6. How a crew is assembled

Take `technical_risk_assessment`. When `app.py` calls `build_crew_for_workflow("technical_risk_assessment", {"tld_string": "example", "use_case": "..."}, config_dir=...)`:

1. `CrewBuilder` loads the four YAML files and the shared `environment.yaml`, whose `current_environment` block sets `memory.enabled: false` and `max_rpm_default`.
2. The roster `[string_analyst, collision_analyst, string_analyst, evaluation_validator]` is instantiated entry by entry. Each agent gets its LLM from `get_model_for_agent` (Gemini 2.5 Flash for all of these), its tools imported by `module` and `class` from `tools.yaml`, `memory=False`, and its own `max_rpm`. Repeating a name in the roster is a readability convention; tasks bind to the first instance of a role.
3. `_validate_agent_tools` confirms every agent with a `tools` list loaded at least one tool. If `similarity_analyzer` failed to import, the build would raise rather than run a crippled analyst.
4. The four tasks are built in order. `{tld_string}` becomes `example` in each description and rubric; the JSON examples inside the prompts are untouched because only the passed input keys are substituted. Each task binds to its `agent` by config key.
5. `Crew(agents, tasks, process=sequential, memory=False, share_crew, max_rpm=10)` is returned.

`app.py` then clears the API-call log, kicks the crew off, and for each task output runs `_classify_result_status`, slices the call log per task, computes a confidence score, and inserts a `task_executions` row. The legal and policy crews follow in the same way.

## 7. Report synthesis

After the third crew, `generate_automatic_report` hands every task output to Gemini with [`crewai_service/prompts/gemini_report_prompt.txt`](../../crewai_service/prompts/gemini_report_prompt.txt). The prompt forbids an overall score and requires one qualitative level per category:

> • Do not compute or present an overall risk score or success probability.
> • Use only qualitative levels per category: Minimal, Low, Moderate, Concerning, High.
> • Surface flags that are considered high risk or concerning prominently in the Executive Summary …

The seven categories (Technical Compliance, String Similarity, Safeguard Policy, Geopolitical, Legal/Trademark, Cultural & Linguistic, Name Collision) map one-to-one onto the task outputs above. The report is stored on the item row and rendered in the client next to the audit log.

## 8. Running it

```bash
curl -X POST http://localhost:8000/api/evaluations/auto-submit \
  -H 'Content-Type: application/json' \
  -d '{"tld_string": "example", "use_case": "A general-purpose registry"}'
```

Progress: `GET /evaluations/{id}/workflows`. Task results and the report: `GET /evaluations/{tld_string}`. Narrative audit log: `GET /api/evaluations/{id}/audit/markdown`. A full run takes a few minutes, most of it in the legal workflow.

## Public sources used by the example

- ICANN New gTLD Program and Applicant Guidebook: https://newgtlds.icann.org/
- IANA Root Zone Database: https://www.iana.org/domains/root/db
- ICANN DNS Magnitude research: https://magnitude.research.icann.org/
- GAC Early Warnings (2012 round): https://gac.icann.org/
- RFC 2606 and RFC 6761 (reserved and special-use names)

Dataset-by-dataset credits are in [`data/SOURCES.md`](../../data/SOURCES.md).
