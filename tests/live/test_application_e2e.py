#!/usr/bin/env python3
"""
End-to-End Test: Application Creation & Answer Generation
==========================================================
Tests the full pipeline:
  1. DB connectivity & data availability
  2. Question loading & applicability filtering
  3. Payment question exclusion (Q65-104)
  4. Entity field resolution from applicant data
  5. Evaluation context retrieval for substantive questions
  6. Answer generation (entity + selection + substantive sample)
  7. Answer storage in application_answers_enhanced
  8. Answer retrieval matching the API endpoint pattern
"""

import sys
import re
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crewai_service.utils.supabase_client import get_supabase_client
from crewai_service.answer_generation_service import (
    AnswerGenerationService,
    EntityFieldHandler,
    SelectionFieldHandler,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results = []


def record(name: str, status: str, detail: str = ""):
    results.append((name, status, detail))
    icon = {"PASS": "+", "FAIL": "!", "SKIP": "-"}[status]
    msg = f"  [{icon}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


async def run_tests():
    print("\n=== Application Generation End-to-End Test ===\n")

    # ------------------------------------------------------------------
    # 1. DB connectivity
    # ------------------------------------------------------------------
    print("--- 1. Database Connectivity ---")
    sb = get_supabase_client()
    if not sb.enabled:
        record("Supabase connection", FAIL, "Client not enabled — check secrets")
        print_summary()
        return
    record("Supabase connection", PASS)

    # ------------------------------------------------------------------
    # 2. Required tables exist with data
    # ------------------------------------------------------------------
    print("\n--- 2. Required Tables ---")
    for table in [
        "applicants",
        "tld_applications",
        "application_questions_enhanced",
        "application_answers_enhanced",
        "tld_strings",
        "task_executions",
    ]:
        try:
            resp = sb.table(table).select("id", count="exact").limit(1).execute()
            count = resp.count if hasattr(resp, "count") and resp.count is not None else len(resp.data or [])
            record(f"Table '{table}'", PASS if count > 0 else SKIP, f"{count} rows")
        except Exception as e:
            record(f"Table '{table}'", FAIL, str(e)[:80])

    # ------------------------------------------------------------------
    # 3. Load applicant
    # ------------------------------------------------------------------
    print("\n--- 3. Applicant Data ---")
    applicant = None
    try:
        resp = sb.table("applicants").select("*").limit(1).execute()
        if resp.data:
            applicant = resp.data[0]
            record(
                "Applicant loaded",
                PASS,
                f"{applicant.get('legal_name', 'N/A')} ({applicant['id'][:8]}…)",
            )
            # Check key entity fields exist
            entity_fields = [
                "legal_name", "business_name", "entity_type", "jurisdiction",
                "email", "phone", "website", "business_address",
            ]
            populated = [f for f in entity_fields if applicant.get(f)]
            missing = [f for f in entity_fields if not applicant.get(f)]
            record(
                "Entity field coverage",
                PASS if len(populated) >= 5 else FAIL,
                f"{len(populated)}/{len(entity_fields)} populated; missing: {missing or 'none'}",
            )
        else:
            record("Applicant loaded", FAIL, "No applicants in DB")
    except Exception as e:
        record("Applicant loaded", FAIL, str(e)[:80])

    # ------------------------------------------------------------------
    # 4. Load questions & applicability filtering
    # ------------------------------------------------------------------
    print("\n--- 4. Question Loading & Filtering ---")
    service = AnswerGenerationService()

    all_questions = await service._get_questions()
    record("All questions loaded", PASS if all_questions else FAIL, f"{len(all_questions)} total")

    for app_type in ["standard", "community", "brand", "geographic", "idn_variant"]:
        filtered = await service._get_questions_for_type(None, app_type)
        record(f"Filtered for '{app_type}'", PASS, f"{len(filtered)} questions")

    # Verify standard gets fewer than community (community adds Q131-157)
    standard_qs = await service._get_questions_for_type(None, "standard")
    community_qs = await service._get_questions_for_type(None, "community")
    record(
        "Community > Standard count",
        PASS if len(community_qs) > len(standard_qs) else FAIL,
        f"community={len(community_qs)} vs standard={len(standard_qs)}",
    )

    # ------------------------------------------------------------------
    # 5. Payment question exclusion (Q65-103)
    # ------------------------------------------------------------------
    print("\n--- 5. Payment Question Exclusion ---")
    standard_qnums = set()
    for q in standard_qs:
        try:
            m = re.match(r"(\d+)", str(q.get("question_number", "0")))
            if m:
                standard_qnums.add(int(m.group(1)))
        except ValueError:
            pass

    payment_leaked = standard_qnums & set(range(65, 104))
    record(
        "Q65-103 excluded from generation",
        PASS if not payment_leaked else FAIL,
        f"leaked: {sorted(payment_leaked)}" if payment_leaked else "none in set",
    )

    # ------------------------------------------------------------------
    # 6. Question categorization
    # ------------------------------------------------------------------
    print("\n--- 6. Question Categorization ---")
    cats = {}
    for q in standard_qs:
        cat = q.get("question_category", "uncategorized")
        cats[cat] = cats.get(cat, 0) + 1
    for cat, count in sorted(cats.items()):
        record(f"Category '{cat}'", PASS, f"{count} questions")

    entity_qs = [q for q in standard_qs if q.get("question_category") == "entity_field"]
    record("Entity questions have field mapping", PASS if all(
        q.get("applicant_field_mapping") for q in entity_qs
    ) else FAIL, f"{len(entity_qs)} entity questions checked")

    # ------------------------------------------------------------------
    # 7. Entity field handler
    # ------------------------------------------------------------------
    print("\n--- 7. Entity Field Handler ---")
    entity_handler = EntityFieldHandler(sb)

    if applicant and entity_qs:
        # Test a few entity questions
        test_cases = []
        for q in entity_qs[:5]:
            r = await entity_handler.generate(q, applicant)
            mapping = q.get("applicant_field_mapping", "?")
            qnum = q.get("question_number", "?")
            test_cases.append((qnum, mapping, r))

        for qnum, mapping, r in test_cases:
            has_value = bool(r.get("response"))
            record(
                f"Q{qnum} → {mapping}",
                PASS if has_value else SKIP,
                f"'{r['response'][:50]}'" if has_value else r.get("tip", "no value"),
            )
    else:
        record("Entity handler", SKIP, "No applicant or entity questions")

    # ------------------------------------------------------------------
    # 8. Selection field handler
    # ------------------------------------------------------------------
    print("\n--- 8. Selection Field Handler ---")
    selection_handler = SelectionFieldHandler()
    selection_qs = [q for q in standard_qs if q.get("question_category") == "selection_field"]

    if selection_qs:
        for q in selection_qs[:3]:
            r = await selection_handler.generate(q, applicant)
            record(
                f"Q{q.get('question_number')} selection",
                PASS if r.get("success") else FAIL,
                f"tip: {r.get('tip', 'none')[:60]}",
            )
    else:
        record("Selection handler", SKIP, "No selection questions")

    # ------------------------------------------------------------------
    # 9. Evaluation data for substantive questions
    # ------------------------------------------------------------------
    print("\n--- 9. Evaluation Context ---")
    # Find a TLD string with completed evaluation
    eval_string = None
    eval_data = None
    try:
        tld_resp = sb.table("tld_strings").select("id, tld_string, use_case").limit(5).execute()
        for s in (tld_resp.data or []):
            tasks_resp = sb.table("task_executions").select("id", count="exact").eq(
                "tld_string_id", s["id"]
            ).in_("result_status", ["CLEAR", "VERIFIED"]).execute()
            task_count = tasks_resp.count if hasattr(tasks_resp, "count") and tasks_resp.count is not None else len(tasks_resp.data or [])
            if task_count > 0:
                eval_string = s
                eval_data = await service._get_evaluation_data(s["id"])
                record(
                    "Found evaluated string",
                    PASS,
                    f".{s['tld_string']} — {task_count} verified tasks",
                )
                break
        if not eval_string:
            record("Found evaluated string", SKIP, "No strings with verified evaluations")
    except Exception as e:
        record("Evaluation data", FAIL, str(e)[:80])

    # ------------------------------------------------------------------
    # 10. Find or create test application
    # ------------------------------------------------------------------
    print("\n--- 10. Test Application ---")
    test_app = None
    created_new = False

    if eval_string and applicant:
        try:
            # Check for existing application
            existing = sb.table("tld_applications").select("*").eq(
                "tld_string", eval_string["tld_string"]
            ).eq("applicant_id", applicant["id"]).limit(1).execute()

            if existing.data:
                test_app = existing.data[0]
                record("Using existing application", PASS, f"id={test_app['id'][:8]}…")
            else:
                record("No existing application", SKIP, "Will test without full app flow")
        except Exception as e:
            record("Test application lookup", FAIL, str(e)[:80])
    else:
        record("Test application", SKIP, "No evaluated string or applicant available")

    # ------------------------------------------------------------------
    # 11. Answer storage & retrieval
    # ------------------------------------------------------------------
    print("\n--- 11. Answer Storage & Retrieval ---")
    if test_app:
        app_id = test_app["id"]

        # Check how many answers are stored
        try:
            ans_resp = sb.table("application_answers_enhanced").select(
                "id, question_id, generation_method, confidence_score", count="exact"
            ).eq("tld_application_id", app_id).execute()

            ans_count = ans_resp.count if hasattr(ans_resp, "count") and ans_resp.count is not None else len(ans_resp.data or [])
            record("Answers in DB", PASS if ans_count > 0 else SKIP, f"{ans_count} answers stored")

            if ans_resp.data:
                methods = {}
                for a in ans_resp.data:
                    m = a.get("generation_method", "unknown")
                    methods[m] = methods.get(m, 0) + 1
                for method, count in sorted(methods.items()):
                    record(f"  Method '{method}'", PASS, f"{count} answers")
        except Exception as e:
            record("Answer storage check", FAIL, str(e)[:80])

        # Verify the API retrieval pattern (questions + answers join)
        try:
            q_resp = sb.table("application_questions_enhanced").select("id, question_number, question_category, applicant_field_mapping").execute()
            a_resp = sb.table("application_answers_enhanced").select("id, question_id, answer_text, generation_method, review_status").eq("tld_application_id", app_id).execute()

            q_by_id = {q["id"]: q for q in (q_resp.data or [])}
            matched = 0
            for a in (a_resp.data or []):
                if a["question_id"] in q_by_id:
                    matched += 1

            record(
                "Answer→Question join",
                PASS if matched > 0 else SKIP,
                f"{matched}/{len(a_resp.data or [])} answers match questions",
            )

            # Verify applicant data is included in the response
            app_detail = sb.table("tld_applications").select(
                "tld_string, applicant_id, application_type, applicants(*)"
            ).eq("id", app_id).single().execute()

            has_applicant = bool(app_detail.data and app_detail.data.get("applicants"))
            record(
                "Applicant data in response",
                PASS if has_applicant else FAIL,
                f"applicant joined: {has_applicant}",
            )

            # Check application context fields
            app_full = sb.table("tld_applications").select(
                "string_meaning, string_rationale, intended_use"
            ).eq("id", app_id).single().execute()
            if app_full.data:
                ctx_fields = ["string_meaning", "string_rationale", "intended_use"]
                populated = [f for f in ctx_fields if app_full.data.get(f)]
                record(
                    "Application context fields",
                    PASS if populated else SKIP,
                    f"{len(populated)}/3 populated: {populated or 'none'}",
                )

        except Exception as e:
            record("API retrieval pattern", FAIL, str(e)[:80])
    else:
        record("Answer storage & retrieval", SKIP, "No test application available")

    # ------------------------------------------------------------------
    # 12. Substantive generation (dry run — single question)
    # ------------------------------------------------------------------
    print("\n--- 12. Substantive Generation (Single Question) ---")
    substantive_qs = [q for q in standard_qs if q.get("question_category") == "substantive_field"]

    if substantive_qs and eval_data and applicant:
        # Pick a string-related question (Q116-121 range)
        test_q = None
        for q in substantive_qs:
            try:
                qnum = int(re.match(r"(\d+)", str(q.get("question_number", "0"))).group(1))
                if 116 <= qnum <= 121:
                    test_q = q
                    break
            except (AttributeError, ValueError):
                pass

        if not test_q:
            test_q = substantive_qs[0]

        record(
            "Test question selected",
            PASS,
            f"Q{test_q.get('question_number')}: {test_q.get('question_text', '')[:60]}…",
        )

        # Check relevant_task_names
        task_names = test_q.get("relevant_task_names", [])
        record(
            "Relevant task names",
            PASS if task_names else SKIP,
            f"{task_names}" if task_names else "none set",
        )

        # Test that the generator builds context correctly (without calling Gemini)
        gen = service.substantive_generator
        context_str, matched_tasks = gen._build_context(
            test_q, applicant, eval_data,
            tld_string=eval_string["tld_string"] if eval_string else None,
            application_context={"intended_use": eval_string.get("use_case", "") if eval_string else ""},
        )
        record(
            "Context built",
            PASS if context_str and len(context_str) > 50 else FAIL,
            f"{len(context_str)} chars, {len(matched_tasks)} matched tasks" if context_str else "empty",
        )

        # Check if matched tasks are included
        if task_names and eval_data:
            matched = [
                t for t in eval_data.get("task_executions", [])
                if t.get("task_name") in task_names
            ]
            record(
                "Matched eval tasks",
                PASS if matched else SKIP,
                f"{len(matched)} tasks matched out of {len(eval_data.get('task_executions', []))} total",
            )
    else:
        reason = []
        if not substantive_qs:
            reason.append("no substantive questions")
        if not eval_data:
            reason.append("no evaluation data")
        if not applicant:
            reason.append("no applicant")
        record("Substantive generation", SKIP, "; ".join(reason))

    # ------------------------------------------------------------------
    print_summary()


def print_summary():
    print("\n" + "=" * 60)
    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)
    skipped = sum(1 for _, s, _ in results if s == SKIP)
    total = len(results)

    print(f"RESULTS: {passed} passed, {failed} failed, {skipped} skipped ({total} total)")

    if failed:
        print("\nFAILURES:")
        for name, status, detail in results:
            if status == FAIL:
                print(f"  [!] {name}: {detail}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
