"""
ICANN DNS Magnitude Collision Analysis Tool

Analyzes name collision risks using ICANN DNS Magnitude data from the Name Collision Analysis Project (NCAP).
Only flags risks when actual ICANN magnitude data exists for a TLD string.
If no magnitude data exists, returns CLEAR status as no collision risk has been identified by ICANN.

Similarity analysis is handled by the dedicated SimilarityAnalyzer tool.
"""

from crewai.tools import BaseTool
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from ..utils.enhanced_data_loader import get_data_loader
from ..utils.enhanced_data_loader import enhanced_collision_data_loader

class MagnitudeCollisionTool(BaseTool):
    name: str = "Magnitude Collision Analyzer"
    description: str = "Analyzes name collision risks using ICANN magnitude data from the Name Collision Analysis Project (NCAP)"
    
    def __init__(self):
        super().__init__()
        self._iana_tlds = None  # Cache for IANA TLD data
        
    def _run(self, tld_string: str) -> str:
        """
        Analyze collision risk using ICANN magnitude data only.
        
        Args:
            tld_string: The TLD string to analyze
            
        Returns:
            JSON string with collision risk assessment based on ICANN magnitude data
        """
        tld_string = tld_string.lower().strip()
        
        # First check if this is already a delegated TLD in IANA database
        if self._is_delegated_tld(tld_string):
            return json.dumps(self._create_delegated_tld_result(tld_string), indent=2)
        
        try:
            # Load comprehensive collision data (real ICANN + critical cases)
            collision_records = enhanced_collision_data_loader.load_comprehensive_collision_data()
            
            if not collision_records:
                logging.warning("No collision data loaded, using fallback")
                collision_records = self._get_fallback_collision_data()
                
        except Exception as e:
            logging.error(f"Failed to load enhanced collision data: {e}")
            collision_records = self._get_fallback_collision_data()
        
        # Check for exact match in collision data (only source of collision risk)
        exact_match = self._find_exact_match(tld_string, collision_records)
        if exact_match:
            return json.dumps(exact_match, indent=2)
        
        # No magnitude data found = No collision risk identified
        result = {
            "string": tld_string,
            "risk_level": "CLEAR",
            "risk_score": 1.0,
            "magnitude_score": None,
            "status": "no_collision_data_found",
            "collision_evidence": ["No collision risk identified in ICANN magnitude data"],
            "recommendation": "PROCEED - No magnitude collision risk detected",
            "confidence": 1.0,
            "expert_review_required": False,
            "data_source": "ICANN Name Collision Analysis Project (NCAP)",
            "note": "Magnitude collision analysis complete - no ICANN collision data found for this string"
        }
        
        logging.info(f"Magnitude collision analysis for '{tld_string}': {result['risk_level']}")
        return json.dumps(result, indent=2)
    
    def _find_exact_match(self, tld_string: str, collision_records: List[Dict]) -> Optional[Dict]:
        """Find exact match in comprehensive collision data."""
        for record in collision_records:
            if record.get("tld", "").lower() == tld_string:
                return self._format_collision_result(record, "exact_match")
        return None

    def _format_collision_result(self, record: Dict, match_type: str) -> Dict:
        """Enhanced assessment using real ICANN data patterns."""
        return self._assess_exact_match(record.get("tld", ""), record, self._get_collision_thresholds())
    
    def _assess_exact_match(self, tld_string: str, match_data: Dict, collision_thresholds: Dict) -> Dict:
        """Enhanced assessment using real ICANN data."""
        
        magnitude = match_data.get("magnitude_score", 0)
        status = match_data.get("status", "").lower()
        unique_sources = match_data.get("unique_sources", 0)
        coverage = match_data.get("coverage", 0)
        data_source = match_data.get("data_source", "unknown")
        
        # Enhanced risk determination based on real data patterns
        if status == "delegated":
            risk_level = "BLOCKED"
            recommendation = "HALT - String already delegated in DNS root"
            confidence = 1.0
            
        elif "blocked" in status:
            risk_level = "BLOCKED" 
            recommendation = "HALT - String blocked due to collision risk (2012 precedent)"
            confidence = 1.0
            
        elif status in ["special-use"]:
            risk_level = "HIGH_RISK"
            recommendation = "EXPERT REVIEW - Special-use domain with collision implications"
            confidence = 0.95
            
        elif status == "pattern_risk":
            risk_level = self._categorize_magnitude_risk(magnitude, collision_thresholds)
            recommendation = f"CAUTION - Pattern matches high-risk cases (magnitude {magnitude:.2f})"
            confidence = 0.85
            
        else:
            # Unknown status - apply magnitude-based assessment
            risk_level = self._categorize_magnitude_risk(magnitude, collision_thresholds)
            recommendation = self._get_risk_recommendation(risk_level)
            confidence = 0.8
        
        # Build evidence from real data
        evidence = [f"Exact match found with magnitude {magnitude:.2f}"]
        
        if unique_sources:
            evidence.append(f"Unique sources: {unique_sources:,}")
        if coverage:
            evidence.append(f"Coverage: {coverage:.2f}%")
        if data_source == "magnitude_full_dataset":
            evidence.append("Source: Real ICANN magnitude database (full dataset)")
        elif data_source == "magnitude_comprehensive_dataset":
            evidence.append("Source: Real ICANN magnitude database (comprehensive)")
        elif data_source == "historical_precedent":
            evidence.append("Source: 2012 round precedent analysis")
        elif data_source == "rfc_standard":
            evidence.append("Source: RFC technical standards")
        elif data_source == "pattern_analysis":
            evidence.append("Source: Pattern-based risk analysis")
        
        # Add reason if available
        if match_data.get("reason"):
            evidence.append(f"Reason: {match_data.get('reason')}")
        if match_data.get("precedent"):
            evidence.append(f"Precedent: {match_data.get('precedent')}")
        
        return {
            "string": tld_string,
            "risk_level": risk_level,
            "risk_score": self._risk_level_to_score(risk_level),
            "magnitude_score": magnitude,
            "delegation_status": status,
            "unique_sources": unique_sources,
            "coverage": coverage,
            "collision_evidence": evidence,
            "data_source": data_source,
            "recommendation": recommendation,
            "confidence": confidence,
            "expert_review_required": risk_level in ["BLOCKED", "HIGH_RISK"],
            "real_icann_data": data_source in ["magnitude_full_dataset", "magnitude_comprehensive_dataset"],
            "match_type": "exact_match"
        }
    
    def _get_collision_thresholds(self) -> Dict:
        """Get collision risk thresholds for magnitude scoring based on ICANN data patterns."""
        return {
            "blocked": 9.0,      # Immediate blocking threshold (delegated TLDs like .com)
            "high_risk": 7.0,    # High collision risk requiring expert review  
            "medium_risk": 5.0,  # Medium risk requiring monitoring (includes .old at 5.483)
            "low_risk": 3.0      # Low risk threshold
        }
    
    def _categorize_magnitude_risk(self, magnitude: float, thresholds: Dict) -> str:
        """Categorize risk level based on magnitude score."""
        if magnitude >= thresholds["blocked"]:
            return "BLOCKED"
        elif magnitude >= thresholds["high_risk"]:
            return "HIGH_RISK"
        elif magnitude >= thresholds["medium_risk"]:
            return "MEDIUM_RISK"
        elif magnitude >= thresholds["low_risk"]:
            return "LOW_RISK"
        else:
            return "CLEAR"
    
    def _get_risk_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on risk level."""
        recommendations = {
            "BLOCKED": "HALT - Unacceptable collision risk",
            "HIGH_RISK": "EXPERT REVIEW - High collision risk requires mitigation",
            "MEDIUM_RISK": "PROCEED WITH CAUTION - Implement collision monitoring",
            "LOW_RISK": "PROCEED - Monitor for collision indicators",
            "CLEAR": "PROCEED - No significant collision risk detected"
        }
        return recommendations.get(risk_level, "REVIEW REQUIRED - Unknown risk level")
    
    def _risk_level_to_score(self, risk_level: str) -> float:
        """Convert risk level to numeric score."""
        scores = {
            "BLOCKED": 5.0,
            "HIGH_RISK": 4.0,
            "MEDIUM_RISK": 3.0,
            "LOW_RISK": 2.0,
            "CLEAR": 1.0
        }
        return scores.get(risk_level, 2.5)
    
    def _get_fallback_collision_data(self) -> List[Dict]:
        """Minimal fallback collision data in case of loading issues."""
        return [
            {"tld": "com", "status": "delegated", "magnitude_score": 9.696, "data_source": "fallback"},
            {"tld": "corp", "status": "blocked_2012", "magnitude_score": 9.8, "reason": "Corporate network usage", "data_source": "fallback"},
            {"tld": "home", "status": "blocked_2012", "magnitude_score": 9.6, "reason": "Home network usage", "data_source": "fallback"},
            {"tld": "mail", "status": "blocked_2012", "magnitude_score": 9.4, "reason": "Email server conflicts", "data_source": "fallback"},
            {"tld": "local", "status": "special-use", "magnitude_score": 8.681, "reason": "RFC 6761 special-use", "data_source": "fallback"}
        ]
    
    def _load_iana_tlds(self) -> List[str]:
        """Load IANA TLD database to identify already delegated TLDs."""
        if self._iana_tlds is not None:
            return self._iana_tlds
        
        try:
            # Path to IANA Root DB JSON file
            iana_file = Path(__file__).parent.parent.parent / "client" / "public" / "data" / "Iana Root DB.json"
            
            if not iana_file.exists():
                logging.warning(f"IANA Root DB file not found: {iana_file}")
                self._iana_tlds = []
                return self._iana_tlds
            
            with open(iana_file, 'r', encoding='utf-8') as f:
                iana_data = json.load(f)
            
            # Extract TLD strings (remove leading dots)
            iana_tlds = []
            for entry in iana_data:
                tld = entry.get('tld', '').lower()
                if tld.startswith('.'):
                    tld = tld[1:]  # Remove leading dot
                if tld:
                    iana_tlds.append(tld)
            
            self._iana_tlds = iana_tlds
            logging.info(f"Loaded {len(iana_tlds)} delegated TLDs from IANA database")
            return self._iana_tlds
            
        except Exception as e:
            logging.error(f"Failed to load IANA TLD data: {e}")
            self._iana_tlds = []
            return self._iana_tlds
    
    def _is_delegated_tld(self, tld_string: str) -> bool:
        """Check if the TLD string is already delegated according to IANA."""
        iana_tlds = self._load_iana_tlds()
        return tld_string.lower() in iana_tlds
    
    def _create_delegated_tld_result(self, tld_string: str) -> Dict:
        """Create result for already delegated TLD."""
        return {
            "string": tld_string,
            "risk_level": "BLOCKED",
            "risk_score": 5.0,
            "magnitude_score": None,
            "status": "already_delegated",
            "collision_evidence": [
                f"TLD '{tld_string}' is already delegated in the DNS root zone",
                "Cannot delegate same TLD twice - represents absolute blocking condition"
            ],
            "recommendation": "HALT - TLD already exists in DNS root",
            "confidence": 1.0,
            "expert_review_required": True,
            "data_source": "IANA Root Zone Database",
            "note": f"TLD '.{tld_string}' is already delegated and operational in the DNS root zone",
            "delegated_tld": True,
            "blocking_reason": "already_delegated"
        } 