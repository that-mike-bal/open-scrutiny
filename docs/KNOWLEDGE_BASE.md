# The knowledge base: giving agents a rulebook to look up

Agents reason from their prompts, their tools, and whatever earlier tasks produced. For a rulebook that runs to hundreds of pages, none of that is enough: the agent needs to **look things up**. OpenScrutiny does this with a pgvector index in Postgres that two things read from: the `guidebook_search` tool the evaluation agents call, and the retrieval used by the generation half and the chat panel.

This page explains what is in the index, who reads it, how to load it, how to check it works, and how to replace it with your own corpus.

## What is in the index

Everything lives in one table, `rag_content`, keyed by `content_type`. A Postgres function, `similarity_search`, does the nearest-neighbour query with an optional `content_type` filter.

| `content_type` | What | Written by | Embedding model | Read by |
|---|---|---|---|---|
| `guidebook_section` | The ICANN Applicant Guidebook, chunked by section (about 800 tokens per chunk, 200-character overlap) with page numbers and topic tags | `db/populate_guidebook_embeddings.py` | `text-embedding-3-small` | `guidebook_search` tool (evaluation agents) |
| `applicant_data` | The applicant knowledge base (`data/example_registry_knowledgebase.md` by default) | `scripts/setup_rag_database.py` | `text-embedding-ada-002` | Generation half, chat |
| `question_guidance` | Per-question guidance derived from the application questions | `scripts/setup_rag_database.py` | `text-embedding-ada-002` | Generation half, chat |
| `answer_templates` | Example answer shapes | `scripts/setup_rag_database.py` | `text-embedding-ada-002` | Generation half, chat |

Both models produce 1,536-dimension vectors, so they share a table, but **a query must use the same model as the rows it searches**. The guidebook tool embeds queries with `text-embedding-3-small` and filters to `guidebook_section`; the generation retrieval (`crewai_service/rag_search_tool.py`) embeds with `text-embedding-ada-002` and searches the other three types. Keep that pairing if you change either side.

The chat panel in the client (`POST /api/chat`) is a thin wrapper over the same retrieval through `crewai_service/rag_chat_agent.py`. It is a convenience for browsing the corpus, not part of the evaluation.

## Who reads the guidebook during an evaluation

The `guidebook_search` tool (`GuidebookRAGSearchTool`, named "ICANN Guidebook Search" to the agents) is loaded for every evaluation agent whose task prompts cite it:

| Agent | Tasks that cite the guidebook |
|---|---|
| `string_analyst` | DNS stability review ("Root Zone Label Generation Rules", "Technical Requirements") |
| `trademark_specialist` | Deep research legal assessment and validation ("Rights Protection", "Trademark Clearinghouse", "Objection Procedures") |
| `gac_advisor` | Geographic names, safeguard questions Q175–Q180, cultural sensitivity |
| `evaluation_validator` | Legal risk validation and the three gut checks |

Each prompt tells the agent which sections to search for, and most rubrics have a guidebook-references block where the agent records the sections it consulted. That block is how a reader checks whether a finding rests on the rulebook or on the model's memory. The tool declaration in `tools.yaml` marks it `access_pattern: shared_reference` with the validator as `primary_agent`.

The tool is optional at runtime. Without the index it returns a clear "no sections found" or configuration error string, the agent notes it, and the evaluation continues. The result classifier does not treat that as a failure on its own, so if you care about guidebook-grounded findings, check the audit log for the tool's calls.

## Loading it

You need `OPENAI_API_KEY` (embeddings), `SUPABASE_URL`, and `SUPABASE_SERVICE_KEY` in the environment, and the schema from `db/schema.sql` already deployed.

**1. Create the index and seed the generation content.**

```bash
python scripts/setup_rag_database.py
```

This enables the `vector` extension, creates `rag_content` and `similarity_search`, embeds the applicant knowledge base, question guidance, and answer templates, and runs a verification query. It is idempotent: rows are upserted on `(source_id, content_type)`.

**2. Get the Applicant Guidebook.** ICANN publishes it as a PDF at https://newgtlds.icann.org/. It is not bundled because it is large and ICANN's. Put it anywhere; the path is passed on the command line.

**3. Chunk, embed, and load it.**

```bash
python db/populate_guidebook_embeddings.py \
  --pdf-path /path/to/applicant-guidebook.pdf \
  --clear-existing \
  --document-version 2026
```

The script extracts text with `pdfplumber`, detects section headings, splits long sections into overlapping chunks, tags each chunk by topic (geographic, safeguard, trademark, and so on), embeds it, and inserts it as a `guidebook_section` row. `--clear-existing` deletes the previous guidebook rows first so a re-run does not duplicate them. `--test-mode` loads a few sample chunks without a PDF, which is enough to see the tool return results.

A full guidebook is several hundred chunks and a few minutes of embedding calls.

## Checking it works

From a Python shell with the same environment:

```python
from crewai_service.tools.guidebook_rag_search import GuidebookRAGSearchTool
print(GuidebookRAGSearchTool()._run("geographic names requiring government support"))
```

You should see numbered results with a section title, a page number, and a relevance percentage. "No guidebook sections found" means the rows are missing or were embedded with a different model; a configuration error names the missing variable.

In SQL:

```sql
select content_type, count(*) from rag_content group by content_type;
```

After an evaluation, the per-task audit log (`GET /api/evaluations/{id}/audit/markdown`) and each rubric's "ICANN Guidebook References" section show whether the agent actually consulted it.

## Replacing it with your own corpus

For a different rulebook, keep the table and the function and change what you load:

1. **Pick a `content_type`** for your corpus, for example `policy_section`, and write a loader modelled on `db/populate_guidebook_embeddings.py`: extract, chunk with overlap, embed with one model, insert with `source_id`, `title`, `content`, `metadata` (page or clause numbers help agents cite), and `embedding`.
2. **Copy the tool.** Subclass or copy `GuidebookRAGSearchTool`, set `name` and `description` to what your prompts will call it, use the same embedding model as your loader, and filter `similarity_search` to your `content_type`.
3. **Declare it** in your tree's `tools.yaml` and add it to the `tools` list of each agent whose prompts should cite it. The [adapting tutorial](ADAPTING.md) covers the declarations.
4. **Make the rubric ask for citations.** Add a "References consulted" block to `expected_output` so the audit trail shows when a finding came from the corpus.

Scope the corpus to what the agents are allowed to decide. A narrow, well-chunked rulebook beats a large one: agents search with short queries, and the top five hits are all they see.

## Related but separate

- `crewai_service/rag_embedder.py` and the `/api/rag/*` endpoints write evaluation outputs into a `rag_embeddings` table for the chat panel. They are independent of the guidebook index.
- The populate script's `--target-table guidebook_embeddings` option writes to a legacy table layout that nothing reads any more; leave the default, `rag_content`.
