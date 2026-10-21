#!/usr/bin/env python3
# ==========================================================================
# CUSTOMIZE: Defines the question categories/sets and field mappings for the example (ICANN) domain. Replace with your own item schema and categorization rules.
# This platform is a domain-agnostic evaluate-then-generate engine; the
# gTLD/ICANN ruleset is just the bundled example. Grep for 'CUSTOMIZE:'
# to find every retargeting point. See the README's Customize section.
# ==========================================================================

"""
Question Categorization Script — 2026 Guidebook Alignment
===========================================================
Classifies all application_questions_enhanced rows with:
  - question_category:      entity_field | selection_field | substantive_field | file_upload
  - applicant_field_mapping: DB column on applicants table (for entity_field questions)
  - question_set / question_set_name: ICANN Question Set (1-23)
  - applicability:          which application types must answer (default: ALL)
  - entity_scope:           what entity the question is about
  - relevant_task_names:    evaluation tasks that provide context for AI generation
  - generation_hint:        per-question LLM guidance

Usage:
    python scripts/categorize_questions.py [--dry-run] [--verbose]
"""

import sys
import re
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
# ENTITY FIELD MAPPINGS (Q1-48 → applicants table columns)
# Maps question numbers to their corresponding column in the applicants table.
# None = this question has an entity scope but no direct column mapping
#        (e.g., selection fields within the entity range).
# ---------------------------------------------------------------------------

ENTITY_FIELD_MAPPINGS = {
    '1': 'legal_name',
    '2': 'business_name',            # DBA / trade name
    '3': 'entity_type',
    '4': 'jurisdiction',
    '5': 'tax_id',
    '6': 'tax_id_issuing_authority',
    '7': 'lei',
    # '8' and '9' are file upload overrides — not mapped here
    '8': None,   # proof of establishment (file upload)
    '9': None,   # proof of good standing (file upload)
    '10': 'website',
    '11': None,  # selection: existing registry operator?
    '12': 'registry_relationship_explanation',
    '13': None,  # selection: RSP/provider?
    '14': 'rsp_affiliate_explanation',
    '15': 'stock_symbol',
    '16': 'stock_exchange',
    '17': 'phone',                   # phone country code
    '18': 'phone',                   # phone number
    '19': 'email',
    '20': 'address_line1',             # primary address — discrete columns
    '21': 'address_line2',
    '22': 'city',
    '23': 'state_province',
    '24': 'postal_code',
    '25': 'country_code',
    '26': 'parent_company_name',
    '27': 'parent_company_dba',
    '28': 'parent_company_entity_type',
    '29': 'parent_company_jurisdiction',
    '30': 'parent_company_address.line1',       # JSONB subfields
    '31': 'parent_company_address.line2',
    '32': 'parent_company_address.city',
    '33': 'parent_company_address.state',
    '34': 'parent_company_address.postal_code',
    '35': 'parent_company_address.country',
    '36': 'ultimate_parent_name',
    '37': 'ultimate_parent_dba',
    '38': 'ultimate_parent_entity_type',
    '39': 'ultimate_parent_jurisdiction',
    '40': 'ultimate_parent_address.line1',      # JSONB subfields
    '41': 'ultimate_parent_address.line2',
    '42': 'ultimate_parent_address.city',
    '43': 'ultimate_parent_address.state',
    '44': 'ultimate_parent_address.postal_code',
    '45': 'ultimate_parent_address.country',
    '46': None,  # org chart upload (file upload override)
    '47': None,  # has_unique_legal_issues (boolean)
    '48': None,  # legal_issues_explanation (narrative — substantive override)
}

# Questions in the entity range that are file uploads
# (proof of establishment, proof of good standing, org chart)
ENTITY_FILE_UPLOAD_OVERRIDES = {'8', '9', '46'}

# Questions in the entity range that should be classified as selection_field
# despite being in Q1-48 (dropdowns, radios, yes/no toggles)
ENTITY_SELECTION_OVERRIDES = {'11', '13', '47'}

# Questions in the entity range that should be classified as substantive_field
# (long narrative fields even though they're about the entity)
ENTITY_SUBSTANTIVE_OVERRIDES = {'48'}


# ---------------------------------------------------------------------------
# QUESTION SETS (derived from DB section_name boundaries, 237 questions)
# Maps (start, end) question number ranges to (set_number, set_name).
# ---------------------------------------------------------------------------

QUESTION_SETS = [
    ((1, 48),    (1, 'Applying Entity Information')),
    ((49, 64),   (2, 'Users')),
    ((65, 103),  (3, 'Payments')),
    ((104, 115), (4, 'Applicant Background and Organization')),
    ((116, 121), (5, 'Applied-for String')),
    ((122, 130), (6, 'Variant Strings')),
    ((131, 157), (7, 'Community gTLDs')),
    ((158, 161), (8, 'Geographic Names')),
    ((162, 163), (9, 'Reserved Names')),
    ((164, 171), (10, 'Safeguard Assessment')),
    ((172, 175), (11, 'Registry Voluntary Commitments')),
    ((176, 178), (12, 'Registry Services')),
    ((179, 188), (13, 'Brand TLD and Code of Conduct')),
    ((189, 191), (14, 'Financial Profile Determination')),
    ((192, 194), (15, 'Government Financial Profile')),
    ((195, 201), (16, 'Registry Operator Financial Profile')),
    ((202, 207), (17, 'Top 25 Financial Profile')),
    ((208, 219), (18, 'Standard Financial Profile')),
    ((220, 221), (19, 'Operational Questions')),
    ((222, 222), (20, 'Additional Information')),
    ((223, 224), (21, 'Bona Fide Intent')),
    ((225, 225), (22, 'Volume Refund')),
    ((226, 237), (23, 'Variant Strings (Supplementary)')),
]


# ---------------------------------------------------------------------------
# APPLICABILITY RULES
# Maps question numbers to the application types that must answer them.
# Default = ['ALL'] (every application type).
# Routing questions (dropdowns asking "is this a X?") are shown to ALL.
# ---------------------------------------------------------------------------

APPLICABILITY_RULES: dict[str, list[str]] = {
    # Variant Strings (Q122-130) — only if applying for variant
    **{str(q): ['variant'] for q in range(122, 131)},

    # Community gTLDs (Q131-157)
    # Q131 = routing question ("Is this a community TLD?") — ALL see it
    '131': ['ALL'],
    **{str(q): ['community'] for q in range(132, 158)},

    # Geographic Names (Q158-161)
    '158': ['ALL'],  # routing
    **{str(q): ['geographic'] for q in range(159, 162)},

    # Reserved Names (Q162-163)
    '162': ['ALL'],  # routing
    '163': ['reserved'],

    # Safeguard Assessment (Q164-171) — ALL (default)

    # RVC (Q172-175)
    '172': ['ALL'],  # routing
    **{str(q): ['rvc'] for q in range(173, 176)},

    # Registry Services (Q176-178) — ALL (default)

    # Brand TLD and Code of Conduct (Q179-188)
    '179': ['ALL'],  # routing: "Are you applying for a Brand TLD?"
    **{str(q): ['brand'] for q in range(180, 185)},
    '185': ['ALL'],  # routing: "Code of Conduct Exemption Requested?"
    **{str(q): ['code_of_conduct'] for q in range(186, 189)},

    # Financial Profile Determination (Q189-191) — ALL (default)

    # Financial profiles — mutually exclusive
    **{str(q): ['government_profile'] for q in range(192, 195)},
    **{str(q): ['registry_operator_profile'] for q in range(195, 202)},
    **{str(q): ['top25_profile'] for q in range(202, 208)},
    **{str(q): ['standard_profile'] for q in range(208, 220)},

    # Bona Fide Intent (Q223-224) — ALL (default)
    # Volume Refund (Q225) — ALL (default)

    # Supplementary Variant questions (Q226-237) — variant only
    **{str(q): ['variant'] for q in range(226, 238)},
}


# ---------------------------------------------------------------------------
# ENTITY SCOPE
# Maps question number ranges to the entity the question is about.
# ---------------------------------------------------------------------------

ENTITY_SCOPE_RANGES = [
    ((1, 19),    'applying_entity'),
    ((20, 25),   'applying_entity'),
    ((26, 35),   'direct_parent_company'),
    ((36, 45),   'ultimate_parent_company'),
    ((46, 48),   'applying_entity'),
    ((49, 64),   'primary_user'),
    ((65, 74),   'payor'),
    ((75, 90),   'financial_institution'),
    ((91, 103),  'billing_contact'),
    ((104, 109), 'directors_officers_shareholders'),
    ((110, 115), 'applying_entity'),        # attestations (includes new Q114-115)
    ((116, 121), 'applied_for_string'),
    ((122, 130), 'variant_string'),
    ((131, 157), 'community_tld'),
    ((158, 161), 'geographic_name'),
    ((162, 163), 'reserved_name'),
    ((164, 171), 'safeguard'),
    ((172, 175), 'rvc'),
    ((176, 178), 'registry_services'),
    ((179, 188), 'brand_and_code_of_conduct'),
    ((189, 191), 'financial_profile'),
    ((192, 194), 'government_profile'),
    ((195, 201), 'registry_operator_profile'),
    ((202, 207), 'top25_profile'),
    ((208, 219), 'standard_profile'),
    ((220, 221), 'operational'),
    ((222, 222), 'additional_info'),
    ((223, 224), 'bona_fide_intent'),
    ((225, 225), 'volume_refund'),
    ((226, 237), 'variant_string'),  # supplementary variant questions
]


# ---------------------------------------------------------------------------
# GENERATION CONTEXT RULES
# Maps question ranges to evaluation task names and LLM hints.
# ---------------------------------------------------------------------------

GENERATION_CONTEXT_RULES: list[dict] = [
    {
        'range': (104, 115),
        'relevant_task_names': [
            'global_trademark_assessment',
            'patent_conflict_assessment',
            'legal_risk_validation',
        ],
        'generation_hint': 'Reference trademark search results. State findings, not opinions.',
    },
    {
        'range': (116, 121),
        'relevant_task_names': [
            'comprehensive_similarity_analysis',
            'dns_stability_review',
            'name_collision_assessment',
        ],
        'generation_hint': "Reference the applicant's stated string meaning and intended use.",
    },
    {
        'range': (122, 130),
        'relevant_task_names': [
            'comprehensive_similarity_analysis',
            'dns_stability_review',
        ],
        'generation_hint': 'Reference string similarity findings for variant strings.',
    },
    {
        'range': (131, 157),
        'relevant_task_names': [
            'cultural_linguistic_assessment',
            'gac_risk_analysis',
        ],
        'generation_hint': 'Reference community definitions and nexus. Be specific about eligibility criteria.',
    },
    {
        'range': (158, 161),
        'relevant_task_names': [
            'geographic_name_assessment',
            'gac_risk_analysis',
            'cultural_linguistic_assessment',
        ],
        'generation_hint': 'Reference geographic classification findings. State government support if available.',
    },
    {
        'range': (164, 171),
        'relevant_task_names': [
            'safeguard_assessment',
            'cultural_linguistic_assessment',
            'gac_risk_analysis',
        ],
        'generation_hint': 'Answer from a "reasonable person" perspective. Reference evaluation findings.',
    },
    {
        'range': (172, 175),
        'relevant_task_names': [
            'safeguard_assessment',
        ],
        'generation_hint': 'Describe specific voluntary commitments and enforcement mechanisms.',
    },
    {
        'range': (176, 178),
        'relevant_task_names': [
            'dns_stability_review',
            'technical_gut_check',
        ],
        'generation_hint': 'Focus on technical DNS compliance and RSP selection.',
    },
    {
        'range': (179, 188),
        'relevant_task_names': [
            'global_trademark_assessment',
            'safeguard_assessment',
        ],
        'generation_hint': 'Describe concrete protection mechanisms. Reference trademark findings.',
    },
    {
        'range': (189, 191),
        'relevant_task_names': [],
        'generation_hint': 'Select the appropriate financial profile based on applicant characteristics.',
    },
    {
        'range': (192, 219),
        'relevant_task_names': [],
        'generation_hint': 'State financial facts from applicant profile. No projections without data.',
    },
    {
        'range': (220, 221),
        'relevant_task_names': [
            'dns_stability_review',
            'technical_gut_check',
        ],
        'generation_hint': 'Describe operational procedures and technical readiness.',
    },
    {
        'range': (222, 222),
        'relevant_task_names': [],
        'generation_hint': 'Provide any additional relevant information not covered in previous sections.',
    },
    {
        'range': (226, 237),
        'relevant_task_names': [
            'comprehensive_similarity_analysis',
            'dns_stability_review',
        ],
        'generation_hint': 'Reference string similarity findings for replacement/variant strings.',
    },
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def parse_question_number(qnum_str: str) -> int | None:
    """Extract the leading integer from a question number string like '7', '18a', 'Q1.2-1'."""
    if not qnum_str:
        return None
    match = re.match(r'(\d+)', str(qnum_str))
    return int(match.group(1)) if match else None


def get_question_set(qnum_int: int) -> tuple[int | None, str | None]:
    """Return (set_number, set_name) for a question number."""
    for (lo, hi), (num, name) in QUESTION_SETS:
        if lo <= qnum_int <= hi:
            return num, name
    return None, None


def get_applicability(qnum_str: str) -> list[str]:
    """Return the applicability tags for a question number."""
    return APPLICABILITY_RULES.get(qnum_str, ['ALL'])


def get_entity_scope(qnum_int: int) -> str | None:
    """Return the entity scope for a question number."""
    for (lo, hi), scope in ENTITY_SCOPE_RANGES:
        if lo <= qnum_int <= hi:
            return scope
    return None


def get_generation_context(qnum_int: int) -> tuple[list[str] | None, str | None]:
    """Return (relevant_task_names, generation_hint) for a question number."""
    for rule in GENERATION_CONTEXT_RULES:
        lo, hi = rule['range']
        if lo <= qnum_int <= hi:
            task_names = rule['relevant_task_names'] or None
            hint = rule.get('generation_hint')
            return task_names, hint
    return None, None


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_question(q: dict) -> tuple[str, str | None]:
    """
    Classify a single question and return (category, applicant_field_mapping).

    Priority order:
      1. File uploads always win
      2. Selection fields (dropdown/radio/checkbox)
      3. Entity selection overrides (yes/no toggles in Q1-48)
      4. Entity substantive overrides (narrative fields in Q1-48)
      5. Explicit entity-field mappings with text-like input
      6. Short text/phone/email/url in entity range (Q1-48) → entity_field
      7. Short text/email/url/phone with char_limit <= 255 anywhere → entity_field
      8. Textarea with large limit → substantive
      9. Default → substantive
    """
    qnum = str(q.get('question_number', '')).strip()
    input_type = (q.get('input_type') or '').lower()
    char_limit = q.get('character_limit')
    qnum_int = parse_question_number(qnum)

    # 1. File uploads always take priority
    if input_type == 'upload':
        return 'file_upload', None

    # 1b. Entity file upload overrides (Q8=proof of establishment, Q9=good standing, Q46=org chart)
    if qnum in ENTITY_FILE_UPLOAD_OVERRIDES:
        return 'file_upload', None

    # 2. Selection fields (dropdown, radio, checkbox)
    if input_type in ('dropdown', 'radio', 'checkbox', 'select'):
        return 'selection_field', None

    # 3. Entity selection overrides (yes/no in Q1-48 that aren't dropdowns in DB)
    if qnum in ENTITY_SELECTION_OVERRIDES:
        return 'selection_field', None

    # 4. Entity substantive overrides (Q48 = narrative legal issues)
    if qnum in ENTITY_SUBSTANTIVE_OVERRIDES:
        return 'substantive_field', None

    # 5. Explicit entity-field mappings (text-like input types)
    if qnum in ENTITY_FIELD_MAPPINGS:
        mapping = ENTITY_FIELD_MAPPINGS[qnum]
        if mapping and input_type in ('text', 'email', 'url', 'phone', 'textarea', ''):
            return 'entity_field', mapping

    # 6. Other text fields in entity range (Q1-48)
    if qnum_int and 1 <= qnum_int <= 48:
        if input_type in ('text', 'email', 'url', 'phone'):
            return 'entity_field', None
        if input_type == 'textarea' and char_limit and char_limit <= 500:
            return 'entity_field', None

    # 7. Short text/email/url/phone outside Q1-48 → substantive (data about
    #    other entities or the string, not applicant profile fields)

    # 8. Textarea fields (large or no limit) → substantive
    if input_type == 'textarea':
        return 'substantive_field', None

    # 9. Default: substantive (safer — ensures review)
    return 'substantive_field', None


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(dry_run: bool = False, verbose: bool = False):
    """Run the categorization."""
    db = get_supabase()

    # Fetch all questions
    response = db.table('application_questions_enhanced').select(
        'id, question_number, section_name, sub_section, input_type, character_limit, question_text'
    ).order('question_number').execute()

    questions = response.data or []
    logger.info(f"Found {len(questions)} questions to categorize")

    counts = {'entity_field': 0, 'selection_field': 0, 'substantive_field': 0, 'file_upload': 0}

    for q in questions:
        qnum = str(q.get('question_number', '')).strip()
        qnum_int = parse_question_number(qnum)

        # Classification
        category, mapping = classify_question(q)
        counts[category] += 1

        # Question set
        set_num, set_name = get_question_set(qnum_int) if qnum_int else (None, None)

        # Applicability
        applicability = get_applicability(qnum)

        # Entity scope
        entity_scope = get_entity_scope(qnum_int) if qnum_int else None

        # Generation context
        task_names, hint = get_generation_context(qnum_int) if qnum_int else (None, None)

        if verbose:
            tasks_str = ','.join(task_names) if task_names else '-'
            appl_str = ','.join(applicability)
            logger.info(
                f"Q{qnum:>4s} | {category:20s} | mapping={mapping or '-':25s} "
                f"| set={set_num or '-'!s:>3s} | scope={entity_scope or '-':25s} "
                f"| appl={appl_str:20s} | tasks={tasks_str}"
            )

        if not dry_run:
            update_data: dict = {
                'question_category': category,
            }

            # Applicant field mapping
            if mapping:
                update_data['applicant_field_mapping'] = mapping

            # Question set
            if set_num is not None:
                update_data['question_set'] = set_num
            if set_name is not None:
                update_data['question_set_name'] = set_name

            # Applicability
            update_data['applicability'] = applicability

            # Entity scope
            if entity_scope is not None:
                update_data['entity_scope'] = entity_scope

            # Generation context
            if task_names is not None:
                update_data['relevant_task_names'] = task_names
            if hint is not None:
                update_data['generation_hint'] = hint

            db.table('application_questions_enhanced').update(update_data).eq('id', q['id']).execute()

    logger.info(f"\nCategorization complete:")
    for cat, count in sorted(counts.items()):
        logger.info(f"  {cat:20s}: {count}")

    if dry_run:
        logger.info("\n(Dry run — no database changes made)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Categorize ICANN application questions (2026 guidebook)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing to DB')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show per-question details')
    args = parser.parse_args()

    run(dry_run=args.dry_run, verbose=args.verbose)
