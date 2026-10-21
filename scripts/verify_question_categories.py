#!/usr/bin/env python3
"""
Verify question_category for Q8, Q9, Q11, Q17, Q25 in Supabase.
Expected after fixes:
  - Q8, Q9 → file_upload (were entity_field; they're uploads)
  - Q11, Q17, Q25 → selection_field (were entity_field; they're dropdowns)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.supabase_client import get_supabase

QUESTIONS_TO_CHECK = ['8', '9', '11', '17', '25']
EXPECTED = {
    '8': 'file_upload',
    '9': 'file_upload',
    '11': 'selection_field',
    '17': 'selection_field',
    '25': 'selection_field',
}

def main():
    db = get_supabase()
    tbl = db.table('application_questions_enhanced')
    # question_number can be stored as string "8", "9", etc.
    response = tbl.select('id, question_number, input_type, question_category').in_(
        'question_number', QUESTIONS_TO_CHECK
    ).order('question_number').execute()

    if not response.data:
        print("No rows returned. Check that question_number values match (e.g. '8' not 'Q8').")
        return 1

    print("question_number | input_type   | question_category | expected    | OK")
    print("-" * 75)
    all_ok = True
    for row in response.data:
        qnum = row.get('question_number', '')
        inp = (row.get('input_type') or '')[:12]
        cat = row.get('question_category') or ''
        exp = EXPECTED.get(qnum, '?')
        ok = (cat == exp)
        if not ok:
            all_ok = False
        print(f" {qnum:14} | {inp:12} | {cat:18} | {exp:11} | {'✓' if ok else 'MISMATCH'}")
    print()
    if all_ok:
        print("All verified: Q8,Q9 = file_upload; Q11,Q17,Q25 = selection_field.")
    else:
        print("Some categories do not match expected. Re-run categorize_questions.py to fix.")
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
