#!/usr/bin/env python3
"""
Question Reconciliation Script — DB vs 2026 Applicant Guidebook PDF
=====================================================================
Reconciles the 233-question DB numbering (old draft) against the 225-question
final numbering from the 2026 Applicant Guidebook PDF, then inserts 4 new
questions to arrive at 237 total.

Changes:
  - Q1-103:   no change
  - Q104:     moves to Q225 (Volume Refund becomes supplementary)
  - Q105-114: shift to Q104-113 (Background fills the gap)
  - Q115-120: shift to Q116-121 (Applied-for String)
  - Q121-129: shift to Q122-130 (Variant Strings Original)
  - Q130-135: move to Q226-231 (Replacement String becomes supplementary)
  - Q136-141: move to Q232-237 (Variant of Replacement becomes supplementary)
  - Q142-233: shift -11 to Q131-222
  - NEW: Q114, Q115 (Background attestations)
  - NEW: Q223, Q224 (Bona Fide Intent)

Section renames:
  - Q226-237 (old Replacement/Variant of Replacement) → 'Variant Strings'
  - Q179-188 (old Brand + Code of Conduct) → 'Brand TLD and Code of Conduct'

The script is idempotent: it detects whether remapping was already applied
and skips if so. It handles the UNIQUE constraint on question_number with a
2-pass approach (rename to REMAP_xxx, then to final number).

Usage:
    python scripts/reconcile_questions.py [--dry-run] [--verbose]
"""

import sys
import argparse
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

try:
    from db.supabase_client import get_supabase
except ImportError:
    print("Error: Could not import supabase_client.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RENUMBER MAPPING: {old_question_number_str: new_question_number_str}
# Built from the exact spec in the task description.
# ---------------------------------------------------------------------------

def build_renumber_mapping() -> dict[str, str]:
    """
    Build the complete old→new mapping.

    Returns dict keyed by old question_number (str) with new question_number (str).
    Only includes entries where old != new.
    """
    mapping: dict[str, str] = {}

    # Q1-103: no change (omitted from mapping)

    # Q104 (Volume Refund) → Q225
    mapping['104'] = '225'

    # Q105-114 (Background) → Q104-113  (shift -1)
    for old in range(105, 115):
        mapping[str(old)] = str(old - 1)

    # Q115-120 (Applied-for String) → Q116-121  (shift +1)
    for old in range(115, 121):
        mapping[str(old)] = str(old + 1)

    # Q121-129 (Variant Strings Original) → Q122-130  (shift +1)
    for old in range(121, 130):
        mapping[str(old)] = str(old + 1)

    # Q130-135 (Replacement String) → Q226-231  (supplementary)
    for i, old in enumerate(range(130, 136)):
        mapping[str(old)] = str(226 + i)

    # Q136-141 (Variant of Replacement) → Q232-237  (supplementary)
    for i, old in enumerate(range(136, 142)):
        mapping[str(old)] = str(232 + i)

    # Q142-233: shift -11 → Q131-222
    for old in range(142, 234):
        mapping[str(old)] = str(old - 11)

    return mapping


# ---------------------------------------------------------------------------
# NEW QUESTIONS TO INSERT
# ---------------------------------------------------------------------------

NEW_QUESTIONS = [
    {
        'question_number': '114',
        'section_name': 'Applicant Background and Organization',
        'sub_section': 'Attestations',
        'question_text': 'Confirm No URS or PDDRP Involvement',
        'input_type': 'radio',
        'character_limit': None,
        'question_category': 'selection_field',
        'applicability': ['ALL'],
        'entity_scope': 'applying_entity',
    },
    {
        'question_number': '115',
        'section_name': 'Applicant Background and Organization',
        'sub_section': 'Attestations',
        'question_text': 'If No, Explain URS/PDDRP Issues',
        'input_type': 'textarea',
        'character_limit': 4000,
        'question_category': 'substantive_field',
        'applicability': ['ALL'],
        'entity_scope': 'applying_entity',
    },
    {
        'question_number': '223',
        'section_name': 'Bona Fide Intent',
        'sub_section': None,
        'question_text': 'Bona Fide Intent Confirmation',
        'input_type': 'checkbox',
        'character_limit': None,
        'question_category': 'selection_field',
        'applicability': ['ALL'],
        'entity_scope': None,
    },
    {
        'question_number': '224',
        'section_name': 'Bona Fide Intent',
        'sub_section': None,
        'question_text': 'Prohibited Communications Confirmation',
        'input_type': 'checkbox',
        'character_limit': None,
        'question_category': 'selection_field',
        'applicability': ['ALL'],
        'entity_scope': None,
    },
]


# ---------------------------------------------------------------------------
# SECTION RENAMES (applied after renumbering)
# keyed by new question_number (str) → new section_name
# ---------------------------------------------------------------------------

SECTION_RENAMES: dict[str, str] = {}

# Old Replacement String (Q130-135) → new Q226-231 — now under 'Variant Strings'
for q in range(226, 232):
    SECTION_RENAMES[str(q)] = 'Variant Strings'

# Old Variant of Replacement (Q136-141) → new Q232-237 — now under 'Variant Strings'
for q in range(232, 238):
    SECTION_RENAMES[str(q)] = 'Variant Strings'

# Old Brand TLD (Q190-195) → new Q179-184 — merge with Code of Conduct into
# 'Brand TLD and Code of Conduct'
for q in range(179, 185):
    SECTION_RENAMES[str(q)] = 'Brand TLD and Code of Conduct'

# Old Code of Conduct (Q196-199) → new Q185-188 — same merged section
for q in range(185, 189):
    SECTION_RENAMES[str(q)] = 'Brand TLD and Code of Conduct'


# ---------------------------------------------------------------------------
# Idempotency detection
# ---------------------------------------------------------------------------

def detect_state(db) -> str:
    """
    Detect the current state of question numbering.

    Returns one of:
      'old'       — DB still has old numbering (Q104 = Volume Refund section)
      'remapping' — partial state with REMAP_ prefixes present
      'new'       — DB already has new numbering (Q225 = Volume Refund)
      'unknown'   — cannot determine
    """
    response = db.table('application_questions_enhanced').select(
        'question_number, section_name'
    ).execute()
    questions = response.data or []

    qnums = {str(q['question_number']).strip() for q in questions}

    # Check for REMAP_ prefixes (interrupted previous run)
    has_remap = any(qn.startswith('REMAP_') for qn in qnums)
    if has_remap:
        return 'remapping'

    # Build a lookup of question_number → section_name
    qnum_to_section = {
        str(q['question_number']).strip(): (q.get('section_name') or '')
        for q in questions
    }

    # In OLD numbering: Q104 is Volume Refund, Q105 is Background
    # In NEW numbering: Q104 is Background, Q225 is Volume Refund
    if '104' in qnum_to_section:
        section_104 = qnum_to_section['104'].lower()
        if 'volume' in section_104 or 'refund' in section_104:
            return 'old'
        if 'background' in section_104:
            # Check additional signals to confirm new numbering
            if '225' in qnum_to_section:
                section_225 = qnum_to_section['225'].lower()
                if 'volume' in section_225 or 'refund' in section_225:
                    return 'new'
            # Q225 might not exist yet (before inserts), but Q104=Background is enough
            return 'new'

    # If Q104 doesn't exist at all, check for other signals
    if '225' in qnum_to_section:
        section_225 = qnum_to_section['225'].lower()
        if 'volume' in section_225 or 'refund' in section_225:
            return 'new'

    return 'unknown'


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(dry_run: bool = False, verbose: bool = False):
    """Run the question reconciliation."""
    db = get_supabase()

    # --- Detect current state ---
    state = detect_state(db)
    logger.info(f"Detected DB state: {state}")

    if state == 'new':
        logger.info("DB already has new (2026 guidebook) numbering. Nothing to do.")
        # Still check if the 4 new questions need inserting
        _insert_new_questions(db, dry_run, verbose)
        _apply_section_renames(db, dry_run, verbose)
        return

    if state == 'remapping':
        logger.warning(
            "Found REMAP_ prefixed question numbers — a previous run may have been "
            "interrupted. Will attempt to complete pass 2 (REMAP_ → final numbers) "
            "before proceeding."
        )
        _complete_remap_pass2(db, dry_run, verbose)
        # After completing pass 2, re-check state
        state = detect_state(db)
        if state == 'new':
            logger.info("Pass 2 recovery complete. DB now has new numbering.")
            _insert_new_questions(db, dry_run, verbose)
            _apply_section_renames(db, dry_run, verbose)
            return
        elif state != 'old':
            logger.error(f"Unexpected state after pass 2 recovery: {state}. Aborting.")
            sys.exit(1)

    if state == 'unknown':
        logger.error(
            "Could not determine DB numbering state. Check the section_name for Q104 "
            "manually. Aborting to be safe."
        )
        sys.exit(1)

    # --- State is 'old': proceed with remapping ---
    mapping = build_renumber_mapping()

    if verbose:
        logger.info(f"\nRenumber mapping ({len(mapping)} entries):")
        for old, new in sorted(mapping.items(), key=lambda x: int(x[0])):
            logger.info(f"  Q{old:>3s} → Q{new}")

    # Fetch all current questions to validate mapping
    response = db.table('application_questions_enhanced').select(
        'id, question_number'
    ).execute()
    existing = {str(q['question_number']).strip(): q['id'] for q in (response.data or [])}

    # Validate that all old numbers in the mapping actually exist
    missing_old = [old for old in mapping if old not in existing]
    if missing_old:
        logger.warning(f"Old question numbers not found in DB (will skip): {sorted(missing_old, key=int)}")

    # Filter mapping to only existing questions
    active_mapping = {old: new for old, new in mapping.items() if old in existing}
    logger.info(f"Will renumber {len(active_mapping)} questions")

    if dry_run:
        logger.info("\n--- DRY RUN: No changes will be applied ---\n")
        _print_mapping_summary(active_mapping)
        _print_new_questions_summary()
        _print_section_rename_summary()
        return

    # --- Pass 1: old → REMAP_{new} ---
    logger.info("\nPass 1: Renaming to temporary REMAP_ prefixes...")
    pass1_count = 0
    for old_num, new_num in sorted(active_mapping.items(), key=lambda x: int(x[0])):
        temp_num = f"REMAP_{new_num}"
        row_id = existing[old_num]
        try:
            db.table('application_questions_enhanced').update(
                {'question_number': temp_num}
            ).eq('id', row_id).execute()
            pass1_count += 1
            if verbose:
                logger.info(f"  Q{old_num} → {temp_num}")
        except Exception as e:
            logger.error(f"  FAILED Q{old_num} → {temp_num}: {e}")
            logger.error("Aborting. Run again to attempt recovery from REMAP_ state.")
            sys.exit(1)

    logger.info(f"Pass 1 complete: {pass1_count} questions renamed to REMAP_ prefix")

    # --- Pass 2: REMAP_{new} → {new} ---
    logger.info("\nPass 2: Renaming from REMAP_ prefix to final numbers...")
    pass2_count = 0
    for old_num, new_num in sorted(active_mapping.items(), key=lambda x: int(x[1])):
        temp_num = f"REMAP_{new_num}"
        row_id = existing[old_num]
        try:
            db.table('application_questions_enhanced').update(
                {'question_number': new_num}
            ).eq('id', row_id).execute()
            pass2_count += 1
            if verbose:
                logger.info(f"  {temp_num} → Q{new_num}")
        except Exception as e:
            logger.error(f"  FAILED {temp_num} → Q{new_num}: {e}")
            logger.error("Partial completion. Run again to attempt recovery.")
            sys.exit(1)

    logger.info(f"Pass 2 complete: {pass2_count} questions given final numbers")

    # --- Insert new questions ---
    _insert_new_questions(db, dry_run, verbose)

    # --- Apply section renames ---
    _apply_section_renames(db, dry_run, verbose)

    # --- Final summary ---
    _print_final_summary(db)


def _complete_remap_pass2(db, dry_run: bool, verbose: bool):
    """
    Complete an interrupted pass 2: rename REMAP_{n} → {n}.
    """
    response = db.table('application_questions_enhanced').select(
        'id, question_number'
    ).execute()

    remap_rows = [
        q for q in (response.data or [])
        if str(q['question_number']).startswith('REMAP_')
    ]

    if not remap_rows:
        logger.info("No REMAP_ rows found (false alarm or already cleaned up).")
        return

    logger.info(f"Found {len(remap_rows)} REMAP_ rows to finalize")

    if dry_run:
        for q in remap_rows:
            final_num = str(q['question_number']).replace('REMAP_', '')
            logger.info(f"  Would rename {q['question_number']} → Q{final_num}")
        return

    count = 0
    for q in remap_rows:
        final_num = str(q['question_number']).replace('REMAP_', '')
        try:
            db.table('application_questions_enhanced').update(
                {'question_number': final_num}
            ).eq('id', q['id']).execute()
            count += 1
            if verbose:
                logger.info(f"  {q['question_number']} → Q{final_num}")
        except Exception as e:
            logger.error(f"  FAILED {q['question_number']} → Q{final_num}: {e}")

    logger.info(f"Pass 2 recovery complete: {count} questions finalized")


def _insert_new_questions(db, dry_run: bool, verbose: bool):
    """Insert 4 new questions if they don't already exist."""
    logger.info("\nChecking for new questions to insert...")

    response = db.table('application_questions_enhanced').select(
        'question_number'
    ).execute()
    existing_nums = {str(q['question_number']).strip() for q in (response.data or [])}

    inserted = 0
    for nq in NEW_QUESTIONS:
        qnum = nq['question_number']
        if qnum in existing_nums:
            logger.info(f"  Q{qnum} already exists — skipping")
            continue

        if dry_run:
            logger.info(f"  Would insert Q{qnum}: {nq['question_text']}")
            inserted += 1
            continue

        insert_data = {
            'question_number': nq['question_number'],
            'section_name': nq['section_name'],
            'question_text': nq['question_text'],
            'input_type': nq['input_type'],
            'question_category': nq['question_category'],
            'applicability': nq['applicability'],
        }
        if nq.get('sub_section'):
            insert_data['sub_section'] = nq['sub_section']
        if nq.get('character_limit') is not None:
            insert_data['character_limit'] = nq['character_limit']
        if nq.get('entity_scope'):
            insert_data['entity_scope'] = nq['entity_scope']

        try:
            db.table('application_questions_enhanced').insert(insert_data).execute()
            inserted += 1
            if verbose:
                logger.info(f"  Inserted Q{qnum}: {nq['question_text']}")
        except Exception as e:
            logger.error(f"  FAILED to insert Q{qnum}: {e}")

    logger.info(f"New questions inserted: {inserted}")


def _apply_section_renames(db, dry_run: bool, verbose: bool):
    """Update section_name for merged/moved sections."""
    logger.info("\nApplying section renames...")

    response = db.table('application_questions_enhanced').select(
        'id, question_number, section_name'
    ).execute()
    qnum_to_row = {
        str(q['question_number']).strip(): q
        for q in (response.data or [])
    }

    renamed = 0
    for qnum, new_section in sorted(SECTION_RENAMES.items(), key=lambda x: int(x[0])):
        if qnum not in qnum_to_row:
            if verbose:
                logger.info(f"  Q{qnum}: not found in DB — skipping rename")
            continue

        row = qnum_to_row[qnum]
        current_section = row.get('section_name') or ''
        if current_section == new_section:
            if verbose:
                logger.info(f"  Q{qnum}: already '{new_section}' — skipping")
            continue

        if dry_run:
            logger.info(f"  Would rename Q{qnum} section: '{current_section}' → '{new_section}'")
            renamed += 1
            continue

        try:
            db.table('application_questions_enhanced').update(
                {'section_name': new_section}
            ).eq('id', row['id']).execute()
            renamed += 1
            if verbose:
                logger.info(f"  Q{qnum}: '{current_section}' → '{new_section}'")
        except Exception as e:
            logger.error(f"  FAILED section rename Q{qnum}: {e}")

    logger.info(f"Section renames applied: {renamed}")


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def _print_mapping_summary(mapping: dict[str, str]):
    """Print a human-readable summary of the mapping."""
    # Group by type of change
    shifts: dict[str, list[tuple[str, str]]] = {}
    for old, new in sorted(mapping.items(), key=lambda x: int(x[0])):
        diff = int(new) - int(old)
        key = f"shift {diff:+d}" if abs(diff) < 50 else f"move to Q{new}"
        shifts.setdefault(key, []).append((old, new))

    logger.info("\nMapping summary by shift:")
    for shift_desc, pairs in sorted(shifts.items()):
        old_range = f"Q{pairs[0][0]}-Q{pairs[-1][0]}" if len(pairs) > 1 else f"Q{pairs[0][0]}"
        new_range = f"Q{pairs[0][1]}-Q{pairs[-1][1]}" if len(pairs) > 1 else f"Q{pairs[0][1]}"
        logger.info(f"  {old_range:>12s} → {new_range:<12s}  ({shift_desc}, {len(pairs)} questions)")


def _print_new_questions_summary():
    """Print summary of new questions."""
    logger.info("\nNew questions to insert:")
    for nq in NEW_QUESTIONS:
        logger.info(f"  Q{nq['question_number']}: {nq['question_text']} ({nq['section_name']})")


def _print_section_rename_summary():
    """Print summary of section renames."""
    # Consolidate by target section
    sections: dict[str, list[str]] = {}
    for qnum, section in sorted(SECTION_RENAMES.items(), key=lambda x: int(x[0])):
        sections.setdefault(section, []).append(qnum)

    logger.info("\nSection renames:")
    for section, qnums in sections.items():
        q_range = f"Q{qnums[0]}-Q{qnums[-1]}" if len(qnums) > 1 else f"Q{qnums[0]}"
        logger.info(f"  {q_range} → '{section}'")


def _print_final_summary(db):
    """Print a final summary of the DB state after all changes."""
    response = db.table('application_questions_enhanced').select(
        'question_number, section_name'
    ).order('question_number').execute()
    questions = response.data or []

    logger.info(f"\n{'='*60}")
    logger.info(f"RECONCILIATION COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total questions in DB: {len(questions)}")

    # Count by section
    sections: dict[str, int] = {}
    for q in questions:
        sec = q.get('section_name') or '(none)'
        sections[sec] = sections.get(sec, 0) + 1

    logger.info(f"\nQuestions by section:")
    for sec, count in sorted(sections.items()):
        logger.info(f"  {sec:45s}: {count}")

    # Sanity checks
    qnums = [str(q['question_number']).strip() for q in questions]
    has_remap = [qn for qn in qnums if qn.startswith('REMAP_')]
    if has_remap:
        logger.warning(f"\nWARNING: {len(has_remap)} questions still have REMAP_ prefix!")

    numeric_qnums = []
    for qn in qnums:
        try:
            numeric_qnums.append(int(qn))
        except ValueError:
            pass
    if numeric_qnums:
        logger.info(f"Question number range: Q{min(numeric_qnums)} - Q{max(numeric_qnums)}")

    dupes = [qn for qn in qnums if qnums.count(qn) > 1]
    if dupes:
        logger.warning(f"\nWARNING: Duplicate question numbers found: {set(dupes)}")
    else:
        logger.info("No duplicate question numbers detected.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Reconcile DB question numbering against 2026 Applicant Guidebook PDF'
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing to DB')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show per-question details')
    args = parser.parse_args()

    run(dry_run=args.dry_run, verbose=args.verbose)
