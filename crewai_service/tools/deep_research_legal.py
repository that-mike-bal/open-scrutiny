"""
Deep Research Legal Tool — Gemini Deep Research API for comprehensive legal risk analysis.

Replaces EnhancedTrademarkCheckerTool + PatentCheckerTool with a single Gemini Deep Research
call that investigates trademarks, patents, and legal risks for a TLD string.

The Deep Research agent autonomously searches the web, synthesizes findings, and returns
a structured legal risk report with cited sources.
"""

import json
import logging
import time
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from crewai_service.utils.config import load_api_key
from crewai_service.utils.api_call_logger import log_api_call

logger = logging.getLogger(__name__)

# Polling configuration
POLL_INTERVAL_SECONDS = 15
MAX_POLL_SECONDS = 900  # 15 minutes max wait


class DeepResearchLegalSchema(BaseModel):
    """Input schema for Deep Research Legal Tool."""
    tld_string: str = Field(
        ...,
        description="The TLD string to research (without leading dot)"
    )


class DeepResearchLegalTool(BaseTool):
    """
    Comprehensive legal risk research using Gemini Deep Research API.

    Performs a single deep research call that covers:
    - Global trademark conflict analysis (USPTO, EUIPO, WIPO)
    - Patent conflict assessment (USPTO and web sources)
    - Related IP and legal risks
    - Rights protection considerations for ICANN gTLD applications

    Returns a structured report with cited sources.
    """

    name: str = "Deep Research Legal Analyzer"
    description: str = (
        "Conduct comprehensive legal risk research for a TLD string using Gemini Deep Research. "
        "Investigates trademarks (USPTO, EUIPO, WIPO), patents, and other IP conflicts "
        "with cited web sources. Use this for thorough legal due diligence on proposed TLD strings."
    )
    args_schema: Type[BaseModel] = DeepResearchLegalSchema

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_gemini_api_key', load_api_key("gemini") or "")

    def _run(self, **kwargs: Any) -> Any:
        """Execute deep research for legal risk analysis."""
        tld_string = kwargs.get("tld_string", "").strip().lstrip(".")

        if not tld_string:
            return json.dumps({"error": "No TLD string provided"})

        if not self._gemini_api_key:
            return self._model_knowledge_fallback(tld_string, "Gemini API key not configured")

        try:
            from google import genai

            client = genai.Client(api_key=self._gemini_api_key)
            return self._execute_deep_research(client, tld_string)

        except ImportError:
            logger.error("google-genai SDK not installed")
            return self._model_knowledge_fallback(tld_string, "google-genai SDK not installed")
        except Exception as e:
            logger.error(f"Deep research failed for '{tld_string}': {e}", exc_info=True)
            return self._model_knowledge_fallback(tld_string, str(e))

    def _build_research_prompt(self, tld_string: str) -> str:
        """Build the deep research prompt combining trademark + patent + legal risk analysis."""
        return f"""Conduct comprehensive legal and intellectual property risk research for the proposed
top-level domain (TLD) string ".{tld_string}" being applied for under ICANN's New gTLD Program.

RESEARCH OBJECTIVES:

1. TRADEMARK CONFLICT ANALYSIS
   Search for active trademark registrations and applications across these databases:
   - USPTO (United States Patent and Trademark Office) — search https://tsdr.uspto.gov and https://tmsearch.uspto.gov
   - EUIPO (European Union Intellectual Property Office) — search https://euipo.europa.eu/eSearch
   - WIPO Global Brand Database — search https://branddb.wipo.int

   For each jurisdiction, identify candidate marks that match or closely resemble "{tld_string}",
   then go beyond the textual match and perform a QUALITATIVE REALISTIC-HARM ASSESSMENT of each one.
   A word matching the string is NOT, by itself, a meaningful conflict — the question is whether
   the trademark holder would realistically succeed in (or even attempt) a Legal Rights Objection
   or cause brand/consumer confusion in a DNS context.

   For each candidate mark, investigate and report on:
   - Registration basics: owner, registration number, status (live/dead/abandoned), filing/registration date,
     Nice classification classes, and goods/services description
   - Holder viability: Is the trademark owner an ACTIVE, operating business today? (Check company
     website, recent news, corporate filings, LinkedIn presence.) A mark held by a defunct, dissolved,
     or non-operating entity is a much weaker threat.
   - Industry relevance: Does the holder operate in — or adjacent to — technology, internet
     infrastructure, domain names, DNS, software, digital services, or online commerce? A match
     held by, e.g., a regional plumbing company or a niche food product is far less likely to
     object to a gTLD than a tech company or internet-focused brand.
   - Class overlap with DNS/internet services: Nice classes 9 (software), 35 (online advertising/
     retail), 38 (telecommunications), 41 (online content), and 42 (SaaS, hosting, software
     services) are the most relevant to TLDs. Marks registered only in physically-distant classes
     (e.g., class 25 apparel, class 30 food) are typically weak threats.
   - Fame and commercial use: Is the mark famous or well-known (globally or in its industry), or
     is it an obscure registration with little or no commercial use? Is it actively used in commerce
     or appears to be defensively parked?
   - Enforcement history: Has the holder previously pursued trademark litigation, UDRP complaints,
     LROs, or opposition proceedings? Aggressive enforcers materially raise risk; holders with
     no enforcement track record are lower risk.
   - Identity vs similarity: Is the match IDENTICAL to "{tld_string}", or merely similar/contained?
     Identical famous marks are the highest risk; partial or phonetic similarities are usually weaker.

   Then classify each conflict using these refined levels — weighted toward REALISTIC objection risk,
   not textual matching alone:
   - STRONG: Active, operating holder; identical or near-identical mark; industry overlaps with
     tech/internet/DNS/software; famous or commercially used; prior enforcement history OR clear
     incentive to object. These should drive an overall HIGH or CRITICAL legal risk rating.
   - MEDIUM: Active holder with a plausible but not obvious reason to object — e.g., identical
     mark in an unrelated industry but commercially active, OR similar-but-not-identical mark in
     a relevant industry, OR a holder with no enforcement history but owning a live, well-used mark.
     These should still be flagged and contribute to a MEDIUM or HIGH overall rating when multiple
     MEDIUM matches exist or one MEDIUM match is particularly credible.
   - WEAK: Textual match only, but no realistic harm — dead/abandoned registration, defunct holder,
     clearly unrelated industry with no DNS/internet footprint, purely descriptive/generic use, or
     phonetic/partial match unlikely to sustain an objection. These should be documented for
     completeness but should NOT inflate the overall risk rating.

   Important: Still flag the overall legal risk as MEDIUM or HIGH when genuine active-business
   conflicts exist — the goal is to avoid over-flagging meaningless word matches, NOT to downplay
   real conflicts. When in doubt between two adjacent levels, choose the more conservative one
   and explain the rationale.

   For every candidate mark, explicitly state WHY you assigned its strength level, referencing the
   factors above. Then separately assess the realistic likelihood (LOW / MEDIUM / HIGH) that each
   holder would file a Legal Rights Objection under ICANN's dispute process, with reasoning.

2. PATENT CONFLICT ANALYSIS
   Search for patents related to "{tld_string}" that could pose IP conflicts:
   - Search USPTO patent database (https://ppubs.uspto.gov/pubwebapp/static/pages/landing.html) and Google Patents
   - Focus on internet/domain technology patents, DNS-related patents, and any patents on the concept "{tld_string}" represents
   - Identify any patent holders who might challenge a TLD registration
   - Assess enforcement risk for each relevant patent found

3. BROADER LEGAL RISK ASSESSMENT
   - Search for any pending or past litigation involving the term "{tld_string}" in domain name or intellectual property contexts
   - Check for UDRP (Uniform Domain-Name Dispute-Resolution Policy) cases involving "{tld_string}"
   - Identify any well-known brands, organizations, or entities strongly associated with "{tld_string}" that might object
   - Assess whether "{tld_string}" has geographic, cultural, or regulatory significance that could trigger government objections

4. ICANN-SPECIFIC CONSIDERATIONS
   - Evaluate risk of Legal Rights Objection (LRO) under ICANN's New gTLD Dispute Resolution procedures
   - Assess whether existing rights protection mechanisms (Sunrise Period, Trademark Claims) would be sufficient
   - Identify any ICANN precedents from previous gTLD rounds involving similar strings

OUTPUT FORMAT:
Provide a structured report with:
- Executive summary with overall legal risk level (LOW / MEDIUM / HIGH / CRITICAL)
- Trademark findings by jurisdiction with strength classifications
- Patent findings with relevance scores
- Legal precedent and litigation findings
- Specific risk factors and their severity
- Recommended mitigation strategies
- All sources cited with URLs

Be thorough and conservative — it is better to flag a potential risk than to miss it.
Cite every source you reference with its URL."""

    def _execute_deep_research(self, client: Any, tld_string: str) -> str:
        """Execute the deep research call and poll for results."""
        prompt = self._build_research_prompt(tld_string)

        start_time = time.monotonic()

        # Log the initial API call
        log_api_call(
            tool_name="DeepResearchLegalTool",
            endpoint="genai.interactions.create",
            method="POST",
            status_code=None,
            response_time_ms=0,
            success=True,
            error=None,
        )

        # Create background deep research interaction
        try:
            interaction = client.interactions.create(
                agent="deep-research-pro-preview-12-2025",
                input=prompt,
                background=True,
            )
        except Exception as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            log_api_call(
                tool_name="DeepResearchLegalTool",
                endpoint="genai.interactions.create",
                method="POST",
                status_code=None,
                response_time_ms=elapsed_ms,
                success=False,
                error=str(e),
            )
            raise

        interaction_id = interaction.id
        logger.info(
            f"Deep research started for '{tld_string}' — interaction {interaction_id}, "
            f"status: {interaction.status}"
        )

        # Poll for completion
        elapsed = 0.0
        poll_count = 0
        while elapsed < MAX_POLL_SECONDS:
            if interaction.status == "completed":
                break
            if interaction.status in ("failed", "cancelled", "incomplete"):
                elapsed_ms = (time.monotonic() - start_time) * 1000
                log_api_call(
                    tool_name="DeepResearchLegalTool",
                    endpoint="genai.interactions.get",
                    method="GET",
                    status_code=None,
                    response_time_ms=elapsed_ms,
                    success=False,
                    error=f"Research ended with status: {interaction.status}",
                )
                logger.warning(
                    f"Deep research for '{tld_string}' ended with status: {interaction.status}"
                )
                return self._model_knowledge_fallback(
                    tld_string,
                    f"Deep research ended with status: {interaction.status}",
                )

            time.sleep(POLL_INTERVAL_SECONDS)
            elapsed = time.monotonic() - start_time
            poll_count += 1

            try:
                interaction = client.interactions.get(interaction_id)
            except Exception as e:
                logger.warning(f"Poll {poll_count} failed for '{tld_string}': {e}")
                continue

            if poll_count % 4 == 0:
                logger.info(
                    f"Deep research for '{tld_string}' still running — "
                    f"status: {interaction.status}, elapsed: {elapsed:.0f}s"
                )

        # Check final status
        if interaction.status != "completed":
            elapsed_ms = (time.monotonic() - start_time) * 1000
            log_api_call(
                tool_name="DeepResearchLegalTool",
                endpoint="genai.interactions.get",
                method="GET",
                status_code=None,
                response_time_ms=elapsed_ms,
                success=False,
                error=f"Timed out after {MAX_POLL_SECONDS}s, status: {interaction.status}",
            )
            logger.warning(
                f"Deep research for '{tld_string}' timed out after {MAX_POLL_SECONDS}s"
            )
            return self._model_knowledge_fallback(
                tld_string,
                f"Deep research timed out after {MAX_POLL_SECONDS}s",
            )

        # Extract results
        elapsed_ms = (time.monotonic() - start_time) * 1000
        log_api_call(
            tool_name="DeepResearchLegalTool",
            endpoint="genai.interactions.create(deep-research)",
            method="POST",
            status_code=200,
            response_time_ms=elapsed_ms,
            success=True,
            error=None,
        )

        report_text = self._extract_report(interaction)
        sources = self._extract_sources(interaction)

        logger.info(
            f"Deep research completed for '{tld_string}' in {elapsed_ms / 1000:.0f}s, "
            f"{len(sources)} sources cited"
        )

        result = {
            "tld_string": tld_string,
            "research_status": "completed",
            "data_source": "gemini_deep_research",
            "search_bypassed": False,
            "model_knowledge_only": False,
            "research_duration_seconds": round(elapsed_ms / 1000, 1),
            "interaction_id": interaction_id,
            "report": report_text,
            "sources_cited": sources,
            "source_count": len(sources),
            "search_summary": {
                "deep_research_used": True,
                "brave_search_used": False,
                "firecrawl_used": False,
                "model_knowledge_only": False,
                "data_sources": ["gemini_deep_research"],
            },
        }
        return json.dumps(result, indent=2)

    def _extract_report(self, interaction: Any) -> str:
        """Extract the text report from the interaction outputs."""
        if not interaction.outputs:
            return "No research output was produced."

        text_parts = []
        for output in interaction.outputs:
            # TextContent has a .text attribute
            if hasattr(output, "text") and output.text:
                text_parts.append(output.text)

        return "\n\n".join(text_parts) if text_parts else "No text output in research results."

    def _extract_sources(self, interaction: Any) -> list:
        """Extract cited URLs from the report text via regex.

        Deep Research cites sources inline in the report prose, so we simply
        scan the report text for URLs rather than relying on SDK-specific
        output-type traversal (which has been brittle across versions).
        """
        import re

        report_text = self._extract_report(interaction)
        if not report_text:
            return []

        url_pattern = r'https?://[^\s\)\]>\"\']+'
        sources = []
        seen = set()
        for url in re.findall(url_pattern, report_text):
            url = url.rstrip(".,;:")
            if url and url not in seen:
                sources.append({"title": "", "url": url})
                seen.add(url)

        return sources

    def _model_knowledge_fallback(self, tld_string: str, reason: str) -> str:
        """Return a structured response indicating model-knowledge-only mode."""
        logger.warning(
            f"Deep research unavailable for '{tld_string}': {reason}. "
            "Agent will use model knowledge only."
        )

        result = {
            "tld_string": tld_string,
            "research_status": "fallback",
            "data_source": "model_knowledge",
            "search_bypassed": True,
            "model_knowledge_only": True,
            "bypass_reason": reason,
            "report": (
                f"Deep research was unavailable ({reason}). "
                f"The agent should use its training knowledge to assess legal risks for '.{tld_string}'. "
                "Flag that this analysis is NOT backed by live data and recommend the applicant "
                "conduct independent trademark and patent searches."
            ),
            "sources_cited": [],
            "source_count": 0,
            "search_summary": {
                "deep_research_used": False,
                "brave_search_used": False,
                "firecrawl_used": False,
                "model_knowledge_only": True,
                "search_bypass_reason": reason,
                "data_sources": [],
            },
        }
        return json.dumps(result, indent=2)
