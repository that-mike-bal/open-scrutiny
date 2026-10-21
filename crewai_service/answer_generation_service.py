# ==========================================================================
# CUSTOMIZE: The generation half: routes each question/field to a handler (entity / selection / substantive). Adapt the handlers and field mapping to your output schema.
# This platform is a domain-agnostic evaluate-then-generate engine; the
# gTLD/ICANN ruleset is just the bundled example. Grep for 'CUSTOMIZE:'
# to find every retargeting point. See the README's Customize section.
# ==========================================================================

"""
Answer Generation Service — 3-Tier Handler
=============================================
Replaces the CrewAI multi-agent + RAG pipeline with a direct, fast approach:

  1. EntityFieldHandler     — DB lookup, zero AI overhead
  2. SelectionFieldHandler  — Options + contextual tips
  3. SubstantiveAnswerGenerator — Single Gemini call with evaluation context

"Less is more" — concise, factual answers that don't invite ICANN scrutiny.
"""

import os
import re
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

import google.generativeai as genai

from crewai_service.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt — core of "less is more"
# ---------------------------------------------------------------------------

SUBSTANTIVE_SYSTEM_PROMPT = """You are drafting a response for an ICANN new gTLD application.

RULES:
1. Be CONCISE. Every extra word invites scrutiny. Shorter is better.
2. State facts only. Do not volunteer information beyond what is asked.
3. No superlatives (world-class, cutting-edge, unparalleled).
4. Do not explain ICANN requirements back to ICANN.
5. If you lack specifics, say "To be provided" — do not fabricate.
6. Professional, straightforward, factual tone.
7. Use plain text only — no markdown formatting, no bullet points unless the question specifically calls for a list.
8. Do not include headers or labels in the answer — just the response content.
"""


# ---------------------------------------------------------------------------
# Entity Field Handler
# ---------------------------------------------------------------------------

class EntityFieldHandler:
    """Maps entity-field questions to applicant DB columns. Zero AI overhead."""

    def __init__(self, supabase):
        self.supabase = supabase

    async def generate(self, question: Dict, applicant: Optional[Dict]) -> Dict[str, Any]:
        """Return the applicant field value directly."""
        mapping = question.get('applicant_field_mapping')
        qnum = question.get('question_number', '')

        if not applicant:
            return {
                'success': False,
                'response': '',
                'data_source': 'applicant_database',
                'confidence': 0.0,
                'tip': 'No applicant selected. Create or select an applicant first.',
            }

        value = None
        if mapping:
            value = applicant.get(mapping)

            # Handle JSONB address fields — flatten to readable string
            if isinstance(value, dict):
                parts = [
                    value.get('line1', ''),
                    value.get('line2', ''),
                    value.get('city', ''),
                    value.get('state', ''),
                    value.get('postal_code', ''),
                    value.get('country', ''),
                ]
                value = ', '.join(p for p in parts if p) or None

            # Handle key_personnel specially — flatten to readable text
            if mapping == 'key_personnel' and isinstance(value, list):
                lines = []
                for p in value:
                    name = p.get('name', 'N/A')
                    title = p.get('title', '')
                    role = p.get('role', '')
                    parts = [name]
                    if title:
                        parts.append(title)
                    if role:
                        parts.append(role)
                    lines.append(' — '.join(parts))
                value = '\n'.join(lines) if lines else None

            # Array fields
            if isinstance(value, list) and not isinstance(value, str):
                value = ', '.join(str(v) for v in value)

        if value:
            return {
                'success': True,
                'response': str(value),
                'data_source': 'applicant_database',
                'confidence': 1.0,
            }
        else:
            return {
                'success': False,
                'response': '',
                'data_source': 'applicant_database',
                'confidence': 0.0,
                'tip': f'Missing data — update the applicant profile (field: {mapping or "unknown"}).',
            }


# ---------------------------------------------------------------------------
# Selection Field Handler
# ---------------------------------------------------------------------------

class SelectionFieldHandler:
    """Returns available options and contextual tips for selection fields."""

    # Default recommendations keyed by question patterns
    SELECTION_TIPS = {
        'existing registry': "Select 'No' unless you currently operate a gTLD registry.",
        'community-based': "Select 'No' for standard gTLD applications.",
        'geographic': "Select 'No' unless the string represents a geographic name.",
        'idn': "Select 'No' unless the string uses non-ASCII characters.",
    }

    async def generate(self, question: Dict, applicant: Optional[Dict]) -> Dict[str, Any]:
        """Return options with contextual tip."""
        question_text = (question.get('question_text') or '').lower()

        # Try to find a relevant tip
        tip = None
        for pattern, t in self.SELECTION_TIPS.items():
            if pattern in question_text:
                tip = t
                break

        return {
            'success': True,
            'response': '',
            'data_source': 'question_metadata',
            'confidence': 0.5,
            'tip': tip or 'Review the options and select the most appropriate value.',
        }


# ---------------------------------------------------------------------------
# Substantive Answer Generator
# ---------------------------------------------------------------------------

class SubstantiveAnswerGenerator:
    """
    Single direct Gemini call with evaluation context.
    No CrewAI, no RAG — just structured context + focused prompt.
    """

    def __init__(self, supabase):
        self.supabase = supabase
        self.model_available = False
        self._setup_gemini()

    def _setup_gemini(self):
        """Initialise Gemini API."""
        try:
            api_key = os.getenv('GEMINI_API_KEY')

            if api_key:
                genai.configure(api_key=api_key)
                self.model_available = True
                logger.info('Gemini configured for SubstantiveAnswerGenerator')
            else:
                logger.error('Gemini API key not found')
        except Exception as e:
            logger.error(f'Failed to initialise Gemini: {e}')

    def _build_context(
        self,
        question: Dict,
        applicant: Optional[Dict],
        evaluation_data: Optional[Dict],
        tld_string: str,
        application_context: Optional[Dict] = None,
    ) -> tuple[str, list]:
        """Assemble structured context for the LLM.

        Returns (context_string, matched_tasks) so the caller can use
        matched_tasks for confidence scoring.
        """
        parts: list[str] = []
        matched_tasks: list[Dict] = []

        # Applicant summary
        if applicant:
            parts.append(
                f"APPLICANT: {applicant.get('legal_name', 'N/A')} "
                f"({applicant.get('entity_type', 'N/A')}, {applicant.get('jurisdiction', 'N/A')})"
            )
            if applicant.get('registry_experience_description'):
                parts.append(f"REGISTRY EXPERIENCE: {applicant['registry_experience_description'][:500]}")
            if applicant.get('current_tlds'):
                parts.append(f"CURRENT TLDs: {', '.join(applicant['current_tlds'])}")
            if applicant.get('website'):
                parts.append(f"WEBSITE: {applicant['website']}")

        # Application-level TLD context (string_meaning, rationale, intended_use)
        if application_context:
            if application_context.get('string_meaning'):
                parts.append(f"STRING MEANING: {application_context['string_meaning']}")
            if application_context.get('string_rationale'):
                parts.append(f"STRING RATIONALE: {application_context['string_rationale']}")
            if application_context.get('intended_use'):
                parts.append(f"INTENDED USE: {application_context['intended_use']}")

        # TLD evaluation data
        if evaluation_data:
            string_info = evaluation_data.get('string_info', {})
            if string_info:
                parts.append(f"TLD STRING: .{tld_string.upper()}")
                if string_info.get('use_case'):
                    parts.append(f"USE CASE: {string_info['use_case']}")
                if string_info.get('overall_status'):
                    parts.append(f"EVALUATION STATUS: {string_info['overall_status']}")

            # Filter tasks by question relevance
            tasks = evaluation_data.get('task_executions', [])
            relevant_names = question.get('relevant_task_names')
            if relevant_names and tasks:
                matched_tasks = [t for t in tasks if t.get('task_name') in relevant_names]
            else:
                matched_tasks = tasks[:15] if tasks else []

            if matched_tasks:
                parts.append(f"\nEVALUATION DATA ({len(matched_tasks)} relevant tasks):")
                for task in matched_tasks:
                    task_name = task.get('task_name', 'unknown')
                    result_status = task.get('result_status', '')

                    # Use user_friendly_summary (actual field), falling back to result_data
                    summary = task.get('user_friendly_summary', '') or ''
                    if not summary:
                        result_data = task.get('result_data')
                        if result_data:
                            summary = str(result_data)[:600]

                    if isinstance(summary, dict):
                        summary = str(summary)
                    if len(summary) > 600:
                        summary = summary[:600] + '...'

                    # Format: [task_name | STATUS]: summary
                    status_tag = f" | {result_status}" if result_status else ""
                    if summary:
                        parts.append(f"  [{task_name}{status_tag}]: {summary}")

        return '\n'.join(parts), matched_tasks

    async def generate(
        self,
        question: Dict,
        applicant: Optional[Dict],
        evaluation_data: Optional[Dict],
        tld_string: str = '',
        application_context: Optional[Dict] = None,
        user_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a substantive answer via a single Gemini call.

        If there is insufficient context (no matched tasks, no evaluation data,
        and no application context) and no user_prompt is provided, returns an
        ``insufficient_data`` result instead of calling Gemini.
        """
        if not self.model_available:
            return {
                'success': False,
                'response': 'AI model unavailable. Please check Gemini API key configuration.',
                'data_source': 'error',
                'confidence': 0.0,
            }

        char_limit = question.get('character_limit') or 4000
        question_text = question.get('question_text', '')
        qnum = question.get('question_number', '')

        context, matched_tasks = self._build_context(
            question, applicant, evaluation_data, tld_string, application_context
        )

        # --- Insufficient data check ---
        has_matched_tasks = bool(matched_tasks)
        has_eval_tasks = bool(
            evaluation_data and evaluation_data.get('task_executions')
        )
        has_app_context = bool(
            application_context
            and any(
                application_context.get(k)
                for k in ('string_meaning', 'string_rationale', 'intended_use')
            )
        )

        if not has_matched_tasks and not has_eval_tasks and not has_app_context:
            if not user_prompt:
                return {
                    'success': False,
                    'response': '',
                    'data_source': 'insufficient_data',
                    'confidence': 0.0,
                    'tip': (
                        'Not enough evaluation data to auto-generate this answer. '
                        'Run an evaluation for this TLD first, or provide a prompt with specific direction.'
                    ),
                }

        applicant_name = applicant.get('legal_name', 'the applicant') if applicant else 'the applicant'
        entity_type = applicant.get('entity_type', '') if applicant else ''
        jurisdiction = applicant.get('jurisdiction', '') if applicant else ''

        # Build generation hint section
        generation_hint = question.get('generation_hint', '')
        hint_section = f"\nQUESTION-SPECIFIC GUIDANCE: {generation_hint}" if generation_hint else ''

        # User direction section
        user_direction = f"\nUSER DIRECTION: {user_prompt}" if user_prompt else ''

        prompt = f"""{SUBSTANTIVE_SYSTEM_PROMPT}

CHARACTER LIMIT: {char_limit}. Target roughly 70% of the limit unless the question genuinely needs more.
APPLICANT: {applicant_name} ({entity_type}, {jurisdiction})
TLD STRING: .{tld_string.upper() if tld_string else 'N/A'}
{hint_section}{user_direction}

--- CONTEXT ---
{context}

--- QUESTION ---
Question {qnum}: {question_text}

{f"Notes/Instructions: {question.get('notes_instructions')}" if question.get('notes_instructions') else ''}

Provide a direct, professional answer. Plain text only.
"""

        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=min(char_limit * 2, 8192),
                ),
            )

            answer_text = response.text.strip() if response.text else ''

            # Post-processing: strip markdown formatting
            answer_text = self._strip_markdown(answer_text)

            # Character limit enforcement
            if len(answer_text) > char_limit:
                answer_text = answer_text[:char_limit - 3] + '...'

            # Confidence scoring based on matched evaluation tasks
            confidence = self._compute_confidence(
                matched_tasks, evaluation_data, application_context
            )

            return {
                'success': True,
                'response': answer_text,
                'data_source': 'ai_generated',
                'confidence': confidence,
                'character_count': len(answer_text),
                'character_limit': char_limit,
            }

        except Exception as e:
            logger.error(f'Gemini generation error for Q{qnum}: {e}')
            return {
                'success': False,
                'response': f'Error generating answer: {str(e)}',
                'data_source': 'error',
                'confidence': 0.0,
            }

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove markdown formatting for ICANN copy-paste."""
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # headers
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # italic
        text = re.sub(r'`(.+?)`', r'\1', text)  # inline code
        text = re.sub(r'^\s*[-*+]\s+', '- ', text, flags=re.MULTILINE)  # normalise bullets
        return text.strip()

    @staticmethod
    def _compute_confidence(
        matched_tasks: list,
        evaluation_data: Optional[Dict],
        application_context: Optional[Dict],
    ) -> float:
        """Compute confidence score based on available context quality."""
        if matched_tasks:
            # Average confidence from matched tasks (confidence_score is 0-100 in DB)
            scores = [t.get('confidence_score') or 50 for t in matched_tasks]
            avg_task_confidence = sum(scores) / len(scores) / 100
            confidence = min(0.95, 0.7 + (avg_task_confidence * 0.25))
        elif evaluation_data and evaluation_data.get('task_executions'):
            confidence = 0.7  # Has eval data but no specific matches
        else:
            confidence = 0.5  # No eval data at all

        # Small boost if application context (string_meaning, etc.) is available
        if application_context:
            has_context = any(
                application_context.get(k)
                for k in ('string_meaning', 'string_rationale', 'intended_use')
            )
            if has_context:
                confidence = min(0.95, confidence + 0.05)

        return round(confidence, 2)

    def _build_shared_context(
        self,
        questions: List[Dict],
        applicant: Optional[Dict],
        evaluation_data: Optional[Dict],
        tld_string: str,
        application_context: Optional[Dict] = None,
    ) -> tuple[str, list]:
        """Build shared context for a batch of questions.

        Merges all relevant_task_names from the question list to filter
        evaluation tasks, then builds a single context string.
        """
        parts: list[str] = []
        matched_tasks: list[Dict] = []

        # Applicant summary
        if applicant:
            parts.append(
                f"APPLICANT: {applicant.get('legal_name', 'N/A')} "
                f"({applicant.get('entity_type', 'N/A')}, {applicant.get('jurisdiction', 'N/A')})"
            )
            if applicant.get('registry_experience_description'):
                parts.append(f"REGISTRY EXPERIENCE: {applicant['registry_experience_description'][:500]}")
            if applicant.get('current_tlds'):
                parts.append(f"CURRENT TLDs: {', '.join(applicant['current_tlds'])}")
            if applicant.get('website'):
                parts.append(f"WEBSITE: {applicant['website']}")

        # Application-level TLD context
        if application_context:
            if application_context.get('string_meaning'):
                parts.append(f"STRING MEANING: {application_context['string_meaning']}")
            if application_context.get('string_rationale'):
                parts.append(f"STRING RATIONALE: {application_context['string_rationale']}")
            if application_context.get('intended_use'):
                parts.append(f"INTENDED USE: {application_context['intended_use']}")

        # Merge all relevant_task_names from the batch
        merged_task_names: set[str] = set()
        for q in questions:
            names = q.get('relevant_task_names')
            if names:
                merged_task_names.update(names)

        # TLD evaluation data
        if evaluation_data:
            string_info = evaluation_data.get('string_info', {})
            if string_info:
                parts.append(f"TLD STRING: .{tld_string.upper()}")
                if string_info.get('use_case'):
                    parts.append(f"USE CASE: {string_info['use_case']}")
                if string_info.get('overall_status'):
                    parts.append(f"EVALUATION STATUS: {string_info['overall_status']}")

            tasks = evaluation_data.get('task_executions', [])
            if merged_task_names and tasks:
                matched_tasks = [t for t in tasks if t.get('task_name') in merged_task_names]
            else:
                matched_tasks = tasks[:15] if tasks else []

            if matched_tasks:
                parts.append(f"\nEVALUATION DATA ({len(matched_tasks)} relevant tasks):")
                for task in matched_tasks:
                    task_name = task.get('task_name', 'unknown')
                    result_status = task.get('result_status', '')

                    summary = task.get('user_friendly_summary', '') or ''
                    if not summary:
                        result_data = task.get('result_data')
                        if result_data:
                            summary = str(result_data)[:600]

                    if isinstance(summary, dict):
                        summary = str(summary)
                    if len(summary) > 600:
                        summary = summary[:600] + '...'

                    status_tag = f" | {result_status}" if result_status else ""
                    if summary:
                        parts.append(f"  [{task_name}{status_tag}]: {summary}")

        return '\n'.join(parts), matched_tasks

    async def generate_batch(
        self,
        questions: List[Dict],
        applicant: Optional[Dict],
        evaluation_data: Optional[Dict],
        tld_string: str,
        application_context: Optional[Dict] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Generate answers for a batch of questions in a single Gemini call.

        Returns a dict keyed by question_number, each value being the answer
        result dict (same shape as generate() output).
        """
        if not self.model_available:
            return {
                q['question_number']: {
                    'success': False,
                    'response': 'AI model unavailable. Please check Gemini API key configuration.',
                    'data_source': 'error',
                    'confidence': 0.0,
                }
                for q in questions
            }

        # Check for insufficient data across the batch
        has_eval_tasks = bool(
            evaluation_data and evaluation_data.get('task_executions')
        )
        has_app_context = bool(
            application_context
            and any(
                application_context.get(k)
                for k in ('string_meaning', 'string_rationale', 'intended_use')
            )
        )

        if not has_eval_tasks and not has_app_context:
            return {
                q['question_number']: {
                    'success': False,
                    'response': '',
                    'data_source': 'insufficient_data',
                    'confidence': 0.0,
                    'tip': (
                        'Not enough evaluation data to auto-generate this answer. '
                        'Run an evaluation for this TLD first, or provide a prompt with specific direction.'
                    ),
                }
                for q in questions
            }

        # Build shared context once for the whole batch
        context, matched_tasks = self._build_shared_context(
            questions, applicant, evaluation_data, tld_string, application_context
        )

        applicant_name = applicant.get('legal_name', 'the applicant') if applicant else 'the applicant'
        entity_type = applicant.get('entity_type', '') if applicant else ''
        jurisdiction = applicant.get('jurisdiction', '') if applicant else ''

        # Build the questions template
        questions_json = {}
        for q in questions:
            qnum = q.get('question_number', '')
            entry = {
                'question_text': q.get('question_text', ''),
                'character_limit': q.get('character_limit') or 4000,
            }
            if q.get('generation_hint'):
                entry['guidance'] = q['generation_hint']
            if q.get('notes_instructions'):
                entry['notes'] = q['notes_instructions']
            questions_json[qnum] = entry

        questions_block = json.dumps(questions_json, indent=2)

        prompt = f"""{SUBSTANTIVE_SYSTEM_PROMPT}

CHARACTER LIMITS: Vary per question (see below). Target roughly 70% of each limit.
APPLICANT: {applicant_name} ({entity_type}, {jurisdiction})
TLD STRING: .{tld_string.upper() if tld_string else 'N/A'}

--- SHARED CONTEXT ---
{context}

--- QUESTIONS ---
Answer ALL of the following questions. Return a JSON object where each key is the
question number (e.g. "Q48") and the value is an object with "answer" (plain text
string, no markdown) and "confidence_note" (brief note on data quality).

{questions_block}

Return ONLY valid JSON. No markdown code fences. No extra text.
"""

        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=8192,
                    response_mime_type='application/json',
                ),
            )

            raw_text = response.text.strip() if response.text else ''
            batch_answers = json.loads(raw_text)

            # Build per-question results
            confidence = self._compute_confidence(
                matched_tasks, evaluation_data, application_context
            )
            results: Dict[str, Dict[str, Any]] = {}

            for q in questions:
                qnum = q.get('question_number', '')
                char_limit = q.get('character_limit') or 4000
                entry = batch_answers.get(qnum, {})
                answer_text = entry.get('answer', '') if isinstance(entry, dict) else ''

                # Post-processing
                answer_text = self._strip_markdown(answer_text)
                if len(answer_text) > char_limit:
                    answer_text = answer_text[:char_limit - 3] + '...'

                results[qnum] = {
                    'success': bool(answer_text),
                    'response': answer_text,
                    'data_source': 'ai_generated' if answer_text else 'insufficient_data',
                    'confidence': confidence if answer_text else 0.0,
                    'character_count': len(answer_text),
                    'character_limit': char_limit,
                }

            return results

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f'Batch generation failed ({e}), falling back to individual calls')
            # Fallback: generate each question individually
            results: Dict[str, Dict[str, Any]] = {}
            for q in questions:
                r = await self.generate(
                    q, applicant, evaluation_data, tld_string,
                    application_context=application_context,
                )
                results[q['question_number']] = r
            return results


# ---------------------------------------------------------------------------
# Main Answer Generation Service
# ---------------------------------------------------------------------------

class AnswerGenerationService:
    """
    Routes questions to the appropriate handler based on question_category.
    Replaces ApplicationGenerationService + ApplicationRAGAgent.
    """

    def __init__(self):
        self.supabase = get_supabase_client()
        self.entity_handler = EntityFieldHandler(self.supabase)
        self.selection_handler = SelectionFieldHandler()
        self.substantive_generator = SubstantiveAnswerGenerator(self.supabase)

    # ------------------------------------------------------------------
    # Public API: single question
    # ------------------------------------------------------------------

    async def generate_answer(
        self,
        question_id: str,
        question_text: str,
        tld_string: Optional[str] = None,
        applicant_id: Optional[str] = None,
        application_id: Optional[str] = None,
        question_category: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an answer for a single question, routing by category."""

        # Fetch question metadata if we don't have the category
        question = await self._get_question(question_id)
        if not question:
            # Fallback: create minimal question dict
            question = {
                'question_number': question_id,
                'question_text': question_text,
                'question_category': question_category or 'substantive_field',
            }

        category = question_category or question.get('question_category', 'substantive_field')

        # Fetch applicant data
        applicant = await self._get_applicant(applicant_id) if applicant_id else None

        # Resolve tld_string and application context from application if available
        application_context = None
        if application_id:
            app_data = await self._get_application(application_id)
            if app_data:
                if not tld_string:
                    tld_string = app_data.get('tld_string')
                application_context = {
                    'string_meaning': app_data.get('string_meaning'),
                    'string_rationale': app_data.get('string_rationale'),
                    'intended_use': app_data.get('intended_use'),
                }
        elif not tld_string:
            tld_string = None

        result = await self._route_to_handler(
            category, question, applicant, tld_string,
            application_context=application_context,
            user_prompt=user_prompt,
        )

        # Store user_prompt in the answer record if provided
        if user_prompt:
            result['generation_prompt'] = user_prompt

        # Add common metadata
        result['question_id'] = question_id
        result['question_category'] = category
        result['generated_at'] = datetime.utcnow().isoformat()

        return result

    # ------------------------------------------------------------------
    # Public API: batch generation
    # ------------------------------------------------------------------

    async def generate_multiple(
        self,
        application_id: str,
        question_ids: Optional[List[str]] = None,
        store_in_database: bool = True,
    ) -> Dict[str, Any]:
        """Generate answers for multiple questions with smart category routing."""

        # Get application details
        app_data = await self._get_application(application_id)
        if not app_data:
            return {'success': False, 'error': f'Application {application_id} not found'}

        tld_string = app_data.get('tld_string', '')
        applicant_id = app_data.get('applicant_id')
        tld_string_id = app_data.get('tld_string_id')

        applicant = await self._get_applicant(applicant_id) if applicant_id else None

        # Extract application-level TLD context
        application_context = {
            'string_meaning': app_data.get('string_meaning'),
            'string_rationale': app_data.get('string_rationale'),
            'intended_use': app_data.get('intended_use'),
        }

        # Fetch evaluation data once
        evaluation_data = None
        if tld_string_id:
            evaluation_data = await self._get_evaluation_data(tld_string_id)

        # Fetch questions, filtered by applicability for this application type
        app_type = app_data.get('application_type', 'standard')
        questions = await self._get_questions_for_type(question_ids, app_type)
        if not questions:
            return {'success': False, 'error': 'No questions found'}

        logger.info(f'Batch generating {len(questions)} answers for .{tld_string}')

        # Categorize questions
        entity_qs = [q for q in questions if q.get('question_category') == 'entity_field']
        selection_qs = [q for q in questions if q.get('question_category') == 'selection_field']
        upload_qs = [q for q in questions if q.get('question_category') == 'file_upload']
        substantive_qs = [q for q in questions if q.get('question_category', 'substantive_field') == 'substantive_field']

        total = len(questions)
        # Only entity + substantive questions can auto-generate; use this for progress %
        auto_total = len([q for q in questions if q.get('question_category') in ('entity_field', 'substantive_field', None)])
        results = []
        successful = 0

        # Phase 1: Instant — entity fields
        for q in entity_qs:
            r = await self.entity_handler.generate(q, applicant)
            r['question_id'] = q['question_number']
            r['question_category'] = 'entity_field'
            results.append(r)
            if r.get('success'):
                successful += 1
                if store_in_database:
                    await self._store_answer(application_id, q, r)

        # Incremental progress: entity phase complete
        if store_in_database and auto_total:
            await self._update_application_status(
                application_id, round(successful / auto_total * 100, 1)
            )

        # Phase 2: Instant — selection fields
        for q in selection_qs:
            r = await self.selection_handler.generate(q, applicant)
            r['question_id'] = q['question_number']
            r['question_category'] = 'selection_field'
            results.append(r)
            # Selection fields don't count as "successful" since they have no answer

        # Phase 3: Skip — file uploads
        for q in upload_qs:
            results.append({
                'question_id': q['question_number'],
                'question_category': 'file_upload',
                'success': False,
                'response': '',
                'data_source': 'file_upload',
                'confidence': 0.0,
                'tip': 'File upload required. See question requirements.',
            })

        # Phase 4: AI batch — substantive fields (batched by related context)
        if substantive_qs:
            question_groups = self._group_questions_for_batching(substantive_qs)
            logger.info(
                f'Batching {len(substantive_qs)} substantive Qs into {len(question_groups)} API calls'
            )

            for group in question_groups:
                batch_results = await self.substantive_generator.generate_batch(
                    group, applicant, evaluation_data, tld_string,
                    application_context=application_context,
                )

                for q in group:
                    qnum = q['question_number']
                    r = batch_results.get(qnum, {
                        'success': False,
                        'response': '',
                        'data_source': 'insufficient_data',
                        'confidence': 0.0,
                        'tip': 'Answer not returned from batch generation.',
                    })
                    r['question_id'] = qnum
                    r['question_category'] = 'substantive_field'
                    results.append(r)
                    if r.get('success'):
                        successful += 1
                        if store_in_database:
                            await self._store_answer(application_id, q, r)

                # Progress update after each batch
                if store_in_database and auto_total:
                    await self._update_application_status(
                        application_id, round(successful / auto_total * 100, 1)
                    )

        completion_pct = (successful / auto_total * 100) if auto_total else 0

        # Final status update
        if store_in_database:
            await self._update_application_status(application_id, round(completion_pct, 1))

        return {
            'success': True,
            'application_id': application_id,
            'tld_string': tld_string,
            'total_questions': total,
            'successful_answers': successful,
            'completion_percentage': round(completion_pct, 1),
            'results': results,
            'category_counts': {
                'entity_field': len(entity_qs),
                'selection_field': len(selection_qs),
                'file_upload': len(upload_qs),
                'substantive_field': len(substantive_qs),
            },
            'generated_at': datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------
    # Public API: question guidance (lightweight)
    # ------------------------------------------------------------------

    async def get_question_guidance(
        self, question_id: str, question_text: str
    ) -> Dict[str, Any]:
        """Return lightweight guidance for a question."""
        question = await self._get_question(question_id)
        category = question.get('question_category', 'substantive_field') if question else 'substantive_field'

        tips = {
            'entity_field': 'This field is auto-populated from your applicant profile. Update your applicant data to change it.',
            'selection_field': 'Select the appropriate option from the available choices.',
            'file_upload': f"Upload the required document. Accepted formats: {', '.join(question.get('acceptable_file_types', ['PDF']) if question else ['PDF'])}.",
            'substantive_field': 'Click "Generate Answer" to create an AI-drafted response based on your evaluation data.',
        }

        return {
            'success': True,
            'response': tips.get(category, 'Click Generate Answer to get started.'),
            'data_source': 'question_guidance',
            'confidence': 0.9,
            'question_id': question_id,
            'generated_at': datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _group_questions_for_batching(
        questions: List[Dict], max_batch_size: int = 12
    ) -> List[List[Dict]]:
        """Group substantive questions into batches by relevant_task_names.

        Questions sharing the same relevant_task_names set go together
        (they need the same evaluation context). Groups are capped at
        max_batch_size and split if larger.
        """
        from collections import defaultdict

        groups: dict[tuple, list[Dict]] = defaultdict(list)
        for q in questions:
            names = q.get('relevant_task_names')
            key = tuple(sorted(names)) if names else ()
            groups[key].append(q)

        batches: list[list[Dict]] = []
        for _key, group_qs in groups.items():
            # Split oversized groups into chunks
            for i in range(0, len(group_qs), max_batch_size):
                batches.append(group_qs[i : i + max_batch_size])

        return batches

    async def _route_to_handler(
        self,
        category: str,
        question: Dict,
        applicant: Optional[Dict],
        tld_string: Optional[str],
        application_context: Optional[Dict] = None,
        user_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route to the correct handler based on category."""
        if category == 'entity_field':
            return await self.entity_handler.generate(question, applicant)
        elif category == 'selection_field':
            return await self.selection_handler.generate(question, applicant)
        elif category == 'file_upload':
            return {
                'success': False,
                'response': '',
                'data_source': 'file_upload',
                'confidence': 0.0,
                'tip': 'File upload required.',
            }
        else:
            # Substantive — need evaluation data
            tld_string_id = None
            if tld_string:
                tld_string_id = await self._get_tld_string_id(tld_string)
            evaluation_data = await self._get_evaluation_data(tld_string_id) if tld_string_id else None
            return await self.substantive_generator.generate(
                question, applicant, evaluation_data, tld_string or '',
                application_context=application_context,
                user_prompt=user_prompt,
            )

    async def _get_question(self, question_id: str) -> Optional[Dict]:
        """Fetch question metadata by question_number."""
        try:
            response = self.supabase.table('application_questions_enhanced').select('*').eq(
                'question_number', question_id
            ).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f'Error fetching question {question_id}: {e}')
            return None

    async def _get_applicant(self, applicant_id: str) -> Optional[Dict]:
        """Fetch applicant data."""
        try:
            response = self.supabase.table('applicants').select('*').eq('id', applicant_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f'Error fetching applicant {applicant_id}: {e}')
            return None

    async def _get_application(self, application_id: str) -> Optional[Dict]:
        """Fetch application data."""
        try:
            response = self.supabase.table('tld_applications').select('*').eq('id', application_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f'Error fetching application {application_id}: {e}')
            return None

    async def _get_tld_string_from_application(self, application_id: str) -> Optional[str]:
        """Get tld_string from an application."""
        app = await self._get_application(application_id)
        return app.get('tld_string') if app else None

    async def _get_tld_string_id(self, tld_string: str) -> Optional[str]:
        """Look up tld_string_id from the string name."""
        try:
            response = self.supabase.table('tld_strings').select('id').eq(
                'tld_string', tld_string.lower()
            ).limit(1).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f'Error looking up tld_string {tld_string}: {e}')
            return None

    async def _get_evaluation_data(self, tld_string_id: str) -> Optional[Dict]:
        """Fetch evaluation data using existing TldApplicationStore pattern."""
        try:
            string_response = self.supabase.table('tld_strings').select('*').eq('id', tld_string_id).single().execute()
            string_data = string_response.data if string_response.data else {}

            # Accept CLEAR (current status) and VERIFIED (legacy) as completed tasks
            tasks_response = self.supabase.table('task_executions').select('*').eq(
                'tld_string_id', tld_string_id
            ).in_('result_status', ['CLEAR', 'VERIFIED']).execute()
            task_executions = tasks_response.data or []

            return {
                'string_info': string_data,
                'task_executions': task_executions,
                'total_tasks': len(task_executions),
            }
        except Exception as e:
            logger.error(f'Error fetching evaluation data for {tld_string_id}: {e}')
            return None

    async def _get_questions(self, question_ids: Optional[List[str]] = None) -> List[Dict]:
        """Fetch questions, optionally filtered by IDs."""
        try:
            query = self.supabase.table('application_questions_enhanced').select('*')
            if question_ids:
                query = query.in_('question_number', question_ids)
            response = query.order('question_number').execute()
            return response.data or []
        except Exception as e:
            logger.error(f'Error fetching questions: {e}')
            return []

    async def _get_questions_for_type(
        self, question_ids: Optional[List[str]], app_type: str
    ) -> List[Dict]:
        """Fetch questions filtered by applicability for the given application type.

        Keeps questions where the applicability array contains 'ALL' or the
        app_type (e.g. 'standard', 'community', 'brand', etc.).  If the
        applicability column hasn't been populated yet (None/empty), the
        question is included as a safe default.
        """
        questions = await self._get_questions(question_ids)
        applicable_tags = {'ALL', app_type}
        # Q65-103 (Payments) handled by financial partner — skip generation
        excluded = set(range(65, 104))
        results = []
        for q in questions:
            try:
                qnum = int(re.match(r'(\d+)', str(q.get('question_number', '0'))).group(1))
            except (AttributeError, ValueError):
                qnum = 0
            if qnum in excluded:
                continue
            applicability = q.get('applicability')
            if not applicability or set(applicability) & applicable_tags:
                results.append(q)
        return results

    async def _store_answer(self, application_id: str, question: Dict, result: Dict):
        """Store a generated answer in the database."""
        try:
            answer_text = result.get('response', '')
            answer_data = {
                'tld_application_id': application_id,
                'question_id': question['id'],
                'answer_text': answer_text,
                'word_count': len(answer_text.split()),
                'character_count': len(answer_text),
                'version': 1,
                'generation_method': 'ai_generated' if result.get('data_source') == 'ai_generated' else 'template_filled',
                'ai_model_used': 'gemini-2.5-flash' if result.get('data_source') == 'ai_generated' else 'database_lookup',
                'confidence_score': result.get('confidence', 0.0),
                'completeness_score': 0.9 if result.get('confidence', 0) > 0.7 else 0.5,
                'source_data_summary': f"Source: {result.get('data_source', 'unknown')}",
                'data_availability_score': result.get('confidence', 0.0),
                'validation_status': 'pending',
                'review_status': 'ai_reviewed',
                'generated_at': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            }

            if result.get('generation_prompt'):
                answer_data['generation_prompt'] = result['generation_prompt']

            self.supabase.table('application_answers_enhanced').upsert(
                answer_data, on_conflict='tld_application_id,question_id,version'
            ).execute()

        except Exception as e:
            logger.error(f"Error storing answer for Q{question.get('question_number')}: {e}")

    async def _update_application_status(self, application_id: str, completion_pct: float):
        """Update application completion status."""
        try:
            # Note: DB CHECK constraint only allows Draft/In_Progress/Ready_For_Review/Submitted/Under_Evaluation
            # Run db/migrations/update_application_statuses.sql to add Generating/Completed/Failed
            status = 'Ready_For_Review' if completion_pct >= 90 else 'In_Progress'
            self.supabase.table('tld_applications').update({
                'completion_percentage': min(completion_pct, 100),
                'status': status,
                'updated_at': datetime.utcnow().isoformat(),
            }).eq('id', application_id).execute()
        except Exception as e:
            logger.error(f'Error updating application status: {e}')


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------
answer_generation_service = AnswerGenerationService()
