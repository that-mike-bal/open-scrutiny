"""
GAC Historical Precedent Analyzer using your comprehensive 242-case database.
"""

from crewai.tools import BaseTool
import json
import logging
from typing import Dict, List, Any, Optional
from ..utils.enhanced_data_loader import get_data_loader

class GACPrecedentTool(BaseTool):
    name: str = "GAC Precedent Analyzer"
    description: str = "Analyzes GAC objection risks using 242 historical precedent cases"
    
    def __init__(self):
        super().__init__()
    
    def _run(self, tld_string: str) -> str:
        """
        Analyze GAC objection risk using historical precedents.
        
        Args:
            tld_string: The TLD string to analyze
            
        Returns:
            JSON string with GAC risk assessment
        """
        tld_string = tld_string.lower().strip()
        
        # Load your comprehensive GAC data
        data_loader = get_data_loader()
        gac_data = data_loader.load_gac_precedents()
        
        # Analyze against precedent patterns
        precedent_matches = self._find_precedent_matches(tld_string, gac_data)
        risk_assessment = self._assess_gac_risk(tld_string, precedent_matches, gac_data)
        
        result = {
            "string": tld_string,
            "gac_risk_level": risk_assessment["risk_level"],
            "risk_score": risk_assessment["risk_score"],
            "precedent_matches": precedent_matches,
            "warning_likelihood": risk_assessment["warning_likelihood"],
            "outcome_prediction": risk_assessment["outcome_prediction"],
            "mitigation_strategies": risk_assessment["mitigation_strategies"],
            "government_concerns": risk_assessment["government_concerns"],
            "confidence": risk_assessment["confidence"],
            "expert_review_required": risk_assessment["expert_review_required"]
        }
        
        logging.info(f"GAC analysis for '{tld_string}': {result['gac_risk_level']}")
        return json.dumps(result, indent=2)
    
    def _find_precedent_matches(self, tld_string: str, gac_data: Dict) -> List[Dict]:
        """Find matching precedents in the 242-case database."""
        matches = []
        
        # Check each warning category
        for category_name, category_data in gac_data.get("warning_categories", {}).items():
            # Check subcategories
            for subcat_name, subcat_data in category_data.get("subcategories", {}).items():
                examples = subcat_data.get("examples", [])
                
                for example in examples:
                    if self._is_precedent_match(tld_string, example):
                        matches.append({
                            "category": category_name,
                            "subcategory": subcat_name,
                            "precedent_string": example.get("string"),
                            "warning_governments": example.get("warning_governments", []),
                            "outcome": example.get("outcome"),
                            "precedent_value": example.get("precedent_value"),
                            "rationale": example.get("rationale"),
                            "similarity_type": self._get_similarity_type(tld_string, example)
                        })
        
        return matches
    
    def _is_precedent_match(self, tld_string: str, precedent: Dict) -> bool:
        """Determine if precedent is relevant to current string."""
        precedent_string = precedent.get("string", "").lower()
        
        # Exact match
        if tld_string == precedent_string:
            return True
        
        # Similar strings (simple similarity for now)
        if tld_string in precedent_string or precedent_string in tld_string:
            return True
        
        # Category-based matching (e.g., all city names)
        # This could be enhanced with more sophisticated matching
        
        return False
    
    def _assess_gac_risk(self, tld_string: str, matches: List[Dict], gac_data: Dict) -> Dict:
        """Assess overall GAC risk using precedent analysis."""
        if not matches:
            return {
                "risk_level": "LOW_RISK",
                "risk_score": 1.5,
                "warning_likelihood": "Low",
                "outcome_prediction": "likely_success",
                "mitigation_strategies": ["Standard application process"],
                "government_concerns": [],
                "confidence": 0.8,
                "expert_review_required": False
            }
        
        # Analyze matches using your framework
        prediction_model = gac_data.get("outcome_prediction_model", {})
        factors = prediction_model.get("factors", [])
        
        # Calculate risk score based on precedents
        risk_score = self._calculate_risk_score(matches, factors)
        
        # Determine outcome using your thresholds
        thresholds = prediction_model.get("outcome_thresholds", {})
        outcome = self._determine_outcome(risk_score, thresholds)
        
        # Get mitigation strategies
        mitigation = self._get_mitigation_strategies(matches, gac_data)
        
        return {
            "risk_level": self._score_to_risk_level(risk_score),
            "risk_score": risk_score,
            "warning_likelihood": self._score_to_likelihood(risk_score),
            "outcome_prediction": outcome,
            "mitigation_strategies": mitigation,
            "government_concerns": self._extract_government_concerns(matches),
            "confidence": 0.85 if len(matches) > 0 else 0.7,
            "expert_review_required": risk_score > 3.0
        }
    
    def _calculate_risk_score(self, matches: List[Dict], factors: List[Dict]) -> float:
        """Calculate risk score using your prediction model."""
        base_score = 2.0
        
        # Number of precedents factor
        if len(matches) >= 3:
            base_score += 1.5
        elif len(matches) >= 2:
            base_score += 1.0
        elif len(matches) == 1:
            base_score += 0.5
        
        # Outcome analysis
        failed_outcomes = [m for m in matches if m.get("outcome") in ["withdrawn", "terminated"]]
        if len(failed_outcomes) > 0:
            base_score += len(failed_outcomes) * 0.5
        
        # Government sensitivity
        sensitive_govs = ["Australia", "France", "United Kingdom", "Germany"]
        for match in matches:
            gov_list = match.get("warning_governments", [])
            if any(gov in sensitive_govs for gov in gov_list):
                base_score += 0.3
        
        return min(base_score, 5.0)  # Cap at 5.0
    
    def _score_to_risk_level(self, score: float) -> str:
        """Convert numeric score to risk level."""
        if score >= 4.0:
            return "VERY_HIGH_RISK"
        elif score >= 3.5:
            return "HIGH_RISK"
        elif score >= 2.5:
            return "MEDIUM_RISK"
        else:
            return "LOW_RISK"
    
    def _score_to_likelihood(self, score: float) -> str:
        """Convert score to warning likelihood."""
        if score >= 4.0:
            return "Very High"
        elif score >= 3.0:
            return "High"
        elif score >= 2.0:
            return "Medium"
        else:
            return "Low"
    
    def _determine_outcome(self, score: float, thresholds: Dict) -> str:
        """Determine predicted outcome using your thresholds."""
        if score >= 4.0:
            return "likely_failure"
        elif score >= 3.5:
            return "high_risk"
        elif score >= 2.5:
            return "requires_mitigation"
        else:
            return "likely_success"
    
    def _get_similarity_type(self, tld_string: str, precedent: Dict) -> str:
        """Determine type of similarity with precedent."""
        precedent_string = precedent.get("string", "").lower()
        
        if tld_string == precedent_string:
            return "exact_match"
        elif tld_string in precedent_string or precedent_string in tld_string:
            return "substring_match"
        else:
            return "category_match"
    
    def _get_mitigation_strategies(self, matches: List[Dict], gac_data: Dict) -> List[str]:
        """Get mitigation strategies based on precedents."""
        strategies = set()
        
        # Add general strategies from your data
        general_strategies = gac_data.get("risk_assessment_framework", {}).get("mitigation_strategies", [])
        strategies.update(general_strategies)
        
        # Add specific strategies based on matches
        for match in matches:
            category = match.get("category", "")
            if "geographic" in category:
                strategies.add("Obtain government letter of support")
            elif "religious" in category:
                strategies.add("Demonstrate community endorsement")
            elif "cultural" in category:
                strategies.add("Provide cultural sensitivity documentation")
        
        return list(strategies)
    
    def _extract_government_concerns(self, matches: List[Dict]) -> List[str]:
        """Extract likely government concerns from precedents."""
        concerns = set()
        
        for match in matches:
            rationale = match.get("rationale", "")
            if rationale:
                concerns.add(rationale)
        
        return list(concerns) 