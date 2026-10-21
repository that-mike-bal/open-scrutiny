# Data sources

Every dataset shipped with the bundled gTLD example, where it came from, and what the project did to it. Datasets marked **project-authored** were written for this repository and are not copies of any external database. Datasets marked **derived** were compiled from the public source named; the compilation, categorisation, and any summaries are the project's own and may contain errors. Check the original before relying on a value.

ICANN and IANA publish the program materials below publicly. They remain the property of their publishers; if you redistribute this repository, keep these credits and check the publishers' site terms.

## Client-side gate datasets (`client/public/data/`)

| File | Source | Notes |
|---|---|---|
| `Iana Root DB.json` | **IANA Root Zone Database**, https://www.iana.org/domains/root/db | Snapshot of the delegated TLDs (1,571 entries) with type and manager. Used by the client gates and by the backend similarity and collision tools. Refresh from the source; IANA updates it continuously. |
| `reserved_names.json` | **Derived** from ICANN Registry Agreement Specification 5 (reserved names), RFC 2606 (reserved top-level names), RFC 6761 and the IANA Special-Use Domain Names registry, ISO 3166-1 country names and codes, GAC advice on geographic and IGO names, and ICANN's agreements covering Olympic, Paralympic, Red Cross and Red Crescent names | Grouped into categories with a policy reference and a project-assigned risk level per category. |
| `ICANN gTLD Blocked Domains.json` | **Derived** from ICANN's published protections for Red Cross and Red Crescent and Olympic names, plus the name-collision strings ICANN resolved not to delegate (`corp`, `home`, `mail`) | A flat list of strings the client rejects outright. |

## Backend reference datasets (`data/`)

| File | Source | Notes |
|---|---|---|
| `Magnitude Data.csv` | **ICANN DNS Magnitude research**, https://magnitude.research.icann.org/ | The top 2,000 labels by DNS magnitude observed at the ICANN Managed Root Server, snapshot dated 13 June 2025. See `data/README.md` for the metric and columns. |
| `magnitude_data.json`, `tld_strings_by_magnitude.csv` | **Derived** from the file above and ICANN's Name Collision Analysis Project (NCAP) publications | Processed subsets with project-assigned risk categories and thresholds used by the collision tool. |
| `gac_precedents.json` (also `crewai_service/data/gac_precedents.json`) | **Derived** from the GAC Early Warning notices of the 2012 New gTLD round, https://gac.icann.org/ | 242 warnings grouped by category with issuing government and summarised outcome. The outcome labels and statistics are the project's reading of public ICANN records. |
| `existing_tld_strings.json` | **Project-authored** | A short sample list used for development and tests. |
| `string_similarity.json`, `visual_confusion.json` | **Project-authored** | Heuristic tables: algorithm weights, confusable character pairs across scripts, and risk thresholds used by the similarity tool. Not an external dataset. |
| `uspto.json`, `euipo.json`, `wipo.json` | **Project-authored** reference notes about the USPTO, EUIPO, and WIPO Global Brand databases | Describe endpoints, Nice classes, and well-known marks for prompt context. They are not copies of those databases, and the current legal tool queries the live sources through Gemini Deep Research instead. |
| `application_questions.md`, `application_questions_reference.md`, `application_questions_parsing_spec.md` | **Derived** from the ICANN New gTLD Program 2026 Round Applicant Guidebook, V1-2025.12.16, Appendix 1 (application questions), https://newgtlds.icann.org/ | The questions restructured into a parseable format with the project's own scope, type, and applicability tags. The parsing spec is project-authored. |
| `example_registry_knowledgebase.md` | **Fictional, project-authored** | A made-up applicant, Example Registry Ltd., operator of the reserved `.example` TLD, used to demonstrate the generation pipeline. Every name, number, and fact in it is invented. |

## Not bundled

- **ICANN Applicant Guidebook (PDF).** The guidebook search tool indexes the full guidebook if you place the PDF where `db/README.md` says. It is large and user-supplied; the evaluation degrades gracefully without it.

## Standards referenced in prompts and tools

RFC 1035, RFC 1123, RFC 2181 (DNS syntax), RFC 2606 and RFC 6761 (reserved and special-use names), the Root Zone Label Generation Rules, and ISO 3166-1/2. These are referenced, not reproduced.
