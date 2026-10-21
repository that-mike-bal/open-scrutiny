"""
Brand Guideline Lookup — the one local-data tool in the brand-name-check example.

Reads data/brand_guideline.json and checks a proposed product name against the
mechanical rules in it (length, characters, prohibited terms, conflicts with
existing or reserved names). Returns JSON the agent must report verbatim; the
interpretive judgement (tone, distinctiveness) is left to the tasks.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

DEFAULT_GUIDELINE = Path(__file__).resolve().parent.parent / "data" / "brand_guideline.json"


class GuidelineLookupInput(BaseModel):
    product_name: str = Field(description="The proposed product name to check")


class BrandGuidelineLookupTool(BaseTool):
    name: str = "Brand Guideline Lookup"
    description: str = (
        "Checks a proposed product name against the brand naming guideline: length, "
        "characters, prohibited terms, forbidden suffixes, and conflicts with existing "
        "or reserved product names. Call with product_name."
    )
    args_schema: type[BaseModel] = GuidelineLookupInput
    guideline_path: Optional[str] = None

    def _load_guideline(self) -> Dict[str, Any]:
        path = Path(self.guideline_path) if self.guideline_path else DEFAULT_GUIDELINE
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _run(self, product_name: str) -> str:
        guideline = self._load_guideline()
        rules = guideline["naming_rules"]
        name = product_name.strip()
        lowered = name.lower()
        checks: List[Dict[str, Any]] = []

        def check(rule: str, passed: bool, detail: str, blocking: bool = False) -> None:
            checks.append({"rule": rule, "result": "PASS" if passed else "FAIL", "detail": detail, "blocking": blocking})

        check("length", rules["min_length"] <= len(name) <= rules["max_length"],
              f"{len(name)} characters (allowed {rules['min_length']}-{rules['max_length']})", blocking=True)
        check("letters_only", name.isalpha() or not rules.get("letters_only", False),
              "letters only" if name.isalpha() else "contains digits, spaces, or punctuation", blocking=True)
        check("single_word", " " not in name or not rules.get("single_word", False),
              "single word" if " " not in name else "contains a space", blocking=True)

        bad_start = [p for p in rules.get("must_not_start_with", []) if lowered.startswith(p)]
        check("must_not_start_with", not bad_start,
              f"starts with '{bad_start[0]}'" if bad_start else "allowed initial letter")

        bad_suffix = [s for s in rules.get("forbidden_suffixes", []) if lowered.endswith(s)]
        check("forbidden_suffixes", not bad_suffix,
              f"ends with '-{bad_suffix[0]}'" if bad_suffix else "no forbidden suffix")

        hits = [t for t in rules.get("prohibited_terms", []) if t in lowered]
        check("prohibited_terms", not hits,
              f"contains prohibited term(s): {', '.join(hits)}" if hits else "no prohibited terms", blocking=True)

        existing = [p for p in guideline.get("existing_products", []) if p.lower() == lowered]
        contained = [p for p in guideline.get("existing_products", [])
                     if p.lower() != lowered and (p.lower() in lowered or lowered in p.lower())]
        check("existing_products", not existing,
              f"identical to existing product '{existing[0]}'" if existing else
              (f"overlaps existing product(s): {', '.join(contained)}" if contained else "no conflict with existing products"),
              blocking=bool(existing))

        reserved = [r for r in guideline.get("reserved_names", []) if r.lower() in lowered]
        check("reserved_names", not reserved,
              f"uses reserved name '{reserved[0]}'" if reserved else "no reserved name used", blocking=True)

        blocking_failures = [c for c in checks if c["result"] == "FAIL" and c["blocking"]]
        soft_failures = [c for c in checks if c["result"] == "FAIL" and not c["blocking"]]
        if blocking_failures:
            status = "BLOCKED"
        elif soft_failures or contained:
            status = "FLAGGED"
        else:
            status = "PASS"

        return json.dumps({
            "product_name": name,
            "guideline": guideline["brand"],
            "guideline_version": guideline.get("version"),
            "status": status,
            "checks": checks,
            "related_existing_products": contained,
            "tone_guidance": rules.get("tone", ""),
        }, indent=2)
