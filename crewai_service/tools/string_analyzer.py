"""
TLD String Analyzer Tool

Analyzes TLD strings for characteristics, compliance, and potential issues.
"""

import re
from typing import Dict, Any, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class StringAnalyzerInput(BaseModel):
    """Input schema for string analyzer tool."""
    tld_string: str = Field(description="The TLD string to analyze")
    use_case: str = Field(default="", description="The intended use case for context")


class StringAnalyzerTool(BaseTool):
    """Tool for analyzing TLD string characteristics and compliance."""
    
    name: str = "TLD String Analyzer"
    description: str = "Analyzes TLD strings for technical compliance, characteristics, and potential issues"
    args_schema: type[BaseModel] = StringAnalyzerInput
    
    def _run(self, tld_string: str, use_case: str = "") -> str:
        """Analyze TLD string characteristics."""
        try:
            # Clean the input
            tld_clean = tld_string.lower().strip().lstrip('.')
            
            # Perform comprehensive analysis
            analysis = {
                'basic_info': self._analyze_basic_characteristics(tld_clean),
                'technical_compliance': self._check_technical_compliance(tld_clean),
                'classification': self._classify_string(tld_clean, use_case),
                'risk_factors': self._identify_risk_factors(tld_clean),
                'recommendations': self._generate_recommendations(tld_clean, use_case)
            }
            
            # Format results
            return self._format_analysis_results(tld_clean, analysis)
            
        except Exception as e:
            return f"⚠️ ERROR: Could not analyze TLD '{tld_string}' - {str(e)}"
    
    def _analyze_basic_characteristics(self, tld_string: str) -> Dict[str, Any]:
        """Analyze basic string characteristics."""
        return {
            'length': len(tld_string),
            'character_types': self._get_character_types(tld_string),
            'is_ascii': tld_string.isascii(),
            'is_numeric': tld_string.isdigit(),
            'is_alphabetic': tld_string.isalpha(),
            'has_hyphens': '-' in tld_string,
            'starts_with_hyphen': tld_string.startswith('-'),
            'ends_with_hyphen': tld_string.endswith('-')
        }
    
    def _get_character_types(self, tld_string: str) -> List[str]:
        """Identify character types in the string."""
        types = []
        if any(c.isalpha() for c in tld_string):
            types.append('alphabetic')
        if any(c.isdigit() for c in tld_string):
            types.append('numeric')
        if '-' in tld_string:
            types.append('hyphen')
        if not tld_string.isascii():
            types.append('non-ascii')
        return types
    
    def _check_technical_compliance(self, tld_string: str) -> Dict[str, Any]:
        """Check technical compliance with DNS standards."""
        issues = []
        
        # Length checks
        if len(tld_string) < 2:
            issues.append("TLD too short (minimum 2 characters)")
        if len(tld_string) > 63:
            issues.append("TLD too long (maximum 63 characters)")
        
        # Character checks
        if not re.match(r'^[a-z0-9-]+$', tld_string):
            issues.append("Contains invalid characters (only a-z, 0-9, hyphen allowed)")
        
        # Hyphen checks
        if tld_string.startswith('-'):
            issues.append("Cannot start with hyphen")
        if tld_string.endswith('-'):
            issues.append("Cannot end with hyphen")
        if '--' in tld_string:
            issues.append("Cannot contain consecutive hyphens")
        
        # All numeric check
        if tld_string.isdigit():
            issues.append("Cannot be all numeric")
        
        return {
            'is_compliant': len(issues) == 0,
            'issues': issues
        }
    
    def _classify_string(self, tld_string: str, use_case: str) -> Dict[str, Any]:
        """Classify the TLD string type."""
        classification = {
            'primary_type': 'generic',
            'secondary_types': [],
            'complexity_level': 'low'
        }
        
        use_case_lower = use_case.lower()
        
        # Geographic classification
        geo_indicators = ['city', 'country', 'region', 'place', 'geographic']
        if any(indicator in use_case_lower for indicator in geo_indicators):
            classification['primary_type'] = 'geographic'
            classification['complexity_level'] = 'high'
        
        # Brand classification
        brand_indicators = ['brand', 'company', 'corporate', 'trademark']
        if any(indicator in use_case_lower for indicator in brand_indicators):
            classification['secondary_types'].append('brand')
            classification['complexity_level'] = 'medium'
        
        # Community classification
        community_indicators = ['community', 'organization', 'association', 'group']
        if any(indicator in use_case_lower for indicator in community_indicators):
            classification['secondary_types'].append('community')
            classification['complexity_level'] = 'high'
        
        # IDN classification
        if not tld_string.isascii():
            classification['secondary_types'].append('idn')
            classification['complexity_level'] = 'high'
        
        # Short string (premium/valuable)
        if len(tld_string) <= 4:
            classification['secondary_types'].append('premium')
        
        return classification
    
    def _identify_risk_factors(self, tld_string: str) -> List[str]:
        """Identify potential risk factors."""
        risks = []
        
        # Length-based risks
        if len(tld_string) <= 3:
            risks.append("Short strings may have high trademark conflict risk")
        
        # Common word risks
        common_words = ['app', 'web', 'site', 'online', 'digital', 'tech', 'data']
        if tld_string in common_words:
            risks.append("Common word may face trademark or similarity challenges")
        
        # Similarity risks (simplified)
        similar_existing = ['app', 'web', 'tech', 'online', 'digital']
        for existing in similar_existing:
            if self._calculate_similarity(tld_string, existing) > 0.7:
                risks.append(f"High similarity to existing TLD '.{existing}'")
        
        # Geographic risks
        if self._might_be_geographic(tld_string):
            risks.append("May be classified as geographic name requiring government support")
        
        return risks
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple similarity score between strings."""
        if str1 == str2:
            return 1.0
        
        # Simple Levenshtein-based similarity
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0
        
        # Count matching characters
        matches = sum(1 for a, b in zip(str1, str2) if a == b)
        return matches / max_len
    
    def _might_be_geographic(self, tld_string: str) -> bool:
        """Check if string might be geographic."""
        # Simple heuristics for geographic detection
        geo_patterns = [
            r'.*city$', r'.*town$', r'.*land$', r'.*burg$',
            r'.*shire$', r'.*state$', r'.*region$'
        ]
        
        return any(re.match(pattern, tld_string) for pattern in geo_patterns)
    
    def _generate_recommendations(self, tld_string: str, use_case: str) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Length recommendations
        if len(tld_string) <= 3:
            recommendations.append("Consider comprehensive trademark clearance due to short length")
        
        # Use case alignment
        if use_case:
            recommendations.append("Ensure string aligns with stated use case for ICANN evaluation")
        
        # Technical recommendations
        if not tld_string.isascii():
            recommendations.append("Prepare for IDN evaluation requirements")
        
        # Default recommendation
        if not recommendations:
            recommendations.append("Proceed with standard ICANN evaluation process")
        
        return recommendations
    
    def _format_analysis_results(self, tld_string: str, analysis: Dict[str, Any]) -> str:
        """Format analysis results into readable report."""
        basic = analysis['basic_info']
        compliance = analysis['technical_compliance']
        classification = analysis['classification']
        risks = analysis['risk_factors']
        recommendations = analysis['recommendations']
        
        report = f"""
🔍 TLD STRING ANALYSIS: .{tld_string}

📊 BASIC CHARACTERISTICS:
• Length: {basic['length']} characters
• Character types: {', '.join(basic['character_types'])}
• ASCII compliant: {'✅' if basic['is_ascii'] else '❌'}

⚙️ TECHNICAL COMPLIANCE:
• DNS compliant: {'✅' if compliance['is_compliant'] else '❌'}
{('• Issues: ' + ', '.join(compliance['issues'])) if compliance['issues'] else ''}

🏷️ CLASSIFICATION:
• Primary type: {classification['primary_type']}
• Secondary types: {', '.join(classification['secondary_types']) if classification['secondary_types'] else 'None'}
• Complexity level: {classification['complexity_level']}

⚠️ RISK FACTORS:
{chr(10).join(f'• {risk}' for risk in risks) if risks else '• No significant risks identified'}

💡 RECOMMENDATIONS:
{chr(10).join(f'• {rec}' for rec in recommendations)}
"""
        return report.strip() 