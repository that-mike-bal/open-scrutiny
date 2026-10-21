#!/usr/bin/env python3
"""
Import TLD Risk Assessment Data

Import risk assessment data from CSV and create embeddings for TLD-specific
risk insights to enhance the TLD Assistant's ability to provide detailed
risk analysis and recommendations for specific strings.
"""

import sys
import os
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import openai

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import get_supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskAssessmentImporter:
    """Import and process TLD risk assessment data"""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.openai_client = self._setup_openai()
        
    def _setup_openai(self):
        """Setup OpenAI client for embeddings"""
        try:
            api_key = self._load_secret("openai_api_key")
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                logger.warning("OpenAI API key not found - cannot generate embeddings")
                return None
                
            return openai.OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to setup OpenAI client: {e}")
            return None
    
    def _load_secret(self, secret_name: str) -> Optional[str]:
        """Read a credential from the environment (``SECRET_NAME`` upper-cased)."""
        value = os.getenv(secret_name.upper())
        return value.strip() if value and value.strip() else None
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        if not self.openai_client:
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def load_risk_data_from_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """Load risk assessment data from CSV file"""
        risk_data = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['tld_string']:  # Skip empty rows
                        risk_data.append(row)
            
            logger.info(f"Loaded {len(risk_data)} risk assessments from CSV")
            return risk_data
            
        except Exception as e:
            logger.error(f"Failed to load CSV data: {e}")
            return []
    
    def categorize_risk_level(self, overall_risk: str) -> Dict[str, Any]:
        """Categorize risk level and provide taxonomy"""
        risk_lower = overall_risk.lower()
        
        if 'high risk' in risk_lower or 'not recommended' in risk_lower:
            return {
                'risk_category': 'HIGH_RISK',
                'risk_score': 4,
                'investment_recommendation': 'NOT_RECOMMENDED',
                'action_required': 'AVOID_APPLICATION',
                'description': 'High risk with multiple blocking issues identified'
            }
        elif 'moderate risk' in risk_lower or 'proceed with caution' in risk_lower:
            return {
                'risk_category': 'MODERATE_RISK',
                'risk_score': 3,
                'investment_recommendation': 'PROCEED_WITH_CAUTION',
                'action_required': 'DETAILED_MITIGATION_REQUIRED',
                'description': 'Moderate risk requiring significant mitigation strategies'
            }
        elif 'manageable risk' in risk_lower or 'viable with proper planning' in risk_lower:
            return {
                'risk_category': 'MANAGEABLE_RISK',
                'risk_score': 2,
                'investment_recommendation': 'VIABLE_WITH_PLANNING',
                'action_required': 'STANDARD_MITIGATION_REQUIRED',
                'description': 'Manageable risk viable with proper planning and mitigation'
            }
        elif 'low risk' in risk_lower or 'good candidate' in risk_lower:
            return {
                'risk_category': 'LOW_RISK',
                'risk_score': 1,
                'investment_recommendation': 'RECOMMENDED',
                'action_required': 'STANDARD_PREPARATIONS',
                'description': 'Low risk, good candidate for application with standard preparations'
            }
        else:
            return {
                'risk_category': 'UNKNOWN_RISK',
                'risk_score': 0,
                'investment_recommendation': 'REQUIRES_EVALUATION',
                'action_required': 'DETAILED_ANALYSIS_REQUIRED',
                'description': 'Risk level requires detailed evaluation'
            }
    
    def parse_risk_factors(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and categorize risk factors from CSV data"""
        
        # Map CSV columns to risk categories
        risk_factors = {
            'technical_compliance': row.get('technical_compliance', 'Unknown'),
            'name_collision': row.get('name_collision', 'Unknown'),
            'string_similarity': row.get('string_similarity', 'Unknown'),
            'safeguard_policy': row.get('safeguard_policy', 'Unknown'),
            'geopolitical': row.get('geopolitical', 'Unknown'),
            'legal_trademark': row.get('legal_trademark', 'Unknown'),
            'cultural_linguistic': row.get('cultural_linguistic', 'Unknown')
        }
        
        # Parse high risk flags
        high_risk_flags = row.get('high_risk_flags', '').strip()
        risk_flags = [flag.strip() for flag in high_risk_flags.split(';') if flag.strip()] if high_risk_flags else []
        
        # Parse top risks
        top_risks = row.get('top_3_risks', '').strip()
        top_risk_list = [risk.strip() for risk in top_risks.split(';') if risk.strip()] if top_risks else []
        
        # Parse critical concerns
        critical_concerns = row.get('critical_concerns', '').strip()
        
        return {
            'risk_factors': risk_factors,
            'high_risk_flags': risk_flags,
            'top_3_risks': top_risk_list,
            'critical_concerns': critical_concerns,
            'total_evaluations': int(row.get('total_evaluations', 0)),
            'data_confidence': row.get('data_confidence', 'Unknown')
        }
    
    def create_risk_assessment_content(self, row: Dict[str, Any]) -> str:
        """Create comprehensive content for risk assessment embedding"""
        
        tld_string = row['tld_string']
        overall_risk = row['overall_risk_level']
        investment_rec = row['investment_recommendation']
        
        risk_taxonomy = self.categorize_risk_level(overall_risk)
        risk_details = self.parse_risk_factors(row)
        
        content = f"""
COMPREHENSIVE RISK ASSESSMENT FOR {tld_string.upper()}

OVERALL RISK CLASSIFICATION:
- Risk Level: {overall_risk}
- Risk Category: {risk_taxonomy['risk_category']}
- Risk Score: {risk_taxonomy['risk_score']}/4
- Investment Recommendation: {risk_taxonomy['investment_recommendation']}
- Action Required: {risk_taxonomy['action_required']}

DETAILED RISK FACTORS:
- Technical Compliance: {risk_details['risk_factors']['technical_compliance']}
- Name Collision Risk: {risk_details['risk_factors']['name_collision']}
- String Similarity Risk: {risk_details['risk_factors']['string_similarity']}
- Safeguard Policy Risk: {risk_details['risk_factors']['safeguard_policy']}
- Geopolitical Risk: {risk_details['risk_factors']['geopolitical']}
- Legal/Trademark Risk: {risk_details['risk_factors']['legal_trademark']}
- Cultural/Linguistic Risk: {risk_details['risk_factors']['cultural_linguistic']}

HIGH RISK FLAGS:
{chr(10).join(f"- {flag}" for flag in risk_details['high_risk_flags']) if risk_details['high_risk_flags'] else "- None identified"}

TOP 3 RISK CONCERNS:
{chr(10).join(f"- {risk}" for risk in risk_details['top_3_risks']) if risk_details['top_3_risks'] else "- No specific risks documented"}

CRITICAL CONCERNS:
{risk_details['critical_concerns'] if risk_details['critical_concerns'] else "No critical concerns documented"}

INVESTMENT RECOMMENDATION:
{investment_rec}

EVALUATION METADATA:
- Total Evaluations Conducted: {risk_details['total_evaluations']}
- Data Confidence Level: {risk_details['data_confidence']}
- Assessment Date: Based on comprehensive multi-tool analysis

STRATEGIC GUIDANCE:
{self._generate_strategic_guidance(risk_taxonomy, risk_details)}
        """
        
        return content.strip()
    
    def _generate_strategic_guidance(self, risk_taxonomy: Dict[str, Any], risk_details: Dict[str, Any]) -> str:
        """Generate strategic guidance based on risk assessment"""
        
        risk_category = risk_taxonomy['risk_category']
        
        if risk_category == 'HIGH_RISK':
            return """
- AVOID APPLICATION: Multiple blocking issues identified that make successful application unlikely
- ALTERNATIVE STRATEGY: Consider alternative TLD strings with lower risk profiles
- COST CONSIDERATION: High likelihood of application rejection and loss of $185,000+ investment
- TIMELINE IMPACT: Expect extended evaluation periods and potential objections
"""
        elif risk_category == 'MODERATE_RISK':
            return """
- PROCEED WITH CAUTION: Significant issues require comprehensive mitigation strategies
- LEGAL REVIEW: Engage specialized ICANN legal counsel for detailed risk analysis
- MITIGATION PLANNING: Develop specific strategies to address identified risk factors
- BUDGET PLANNING: Include additional costs for extended evaluation and potential disputes
"""
        elif risk_category == 'MANAGEABLE_RISK':
            return """
- VIABLE WITH PLANNING: Good candidate with proper risk mitigation strategies
- STANDARD MITIGATION: Implement standard risk management practices
- PROFESSIONAL CONSULTATION: Consider expert guidance for optimal application strategy
- MONITORING REQUIRED: Establish ongoing risk monitoring throughout application process
"""
        elif risk_category == 'LOW_RISK':
            return """
- RECOMMENDED FOR APPLICATION: Strong candidate with minimal risk factors
- STANDARD PREPARATIONS: Follow standard application procedures and timelines
- COMPETITIVE ADVANTAGE: Lower risk profile may provide strategic advantage
- COST EFFICIENCY: Likely to avoid extended evaluation costs and delays
"""
        else:
            return """
- DETAILED ANALYSIS REQUIRED: Conduct comprehensive risk assessment before proceeding
- EXPERT CONSULTATION: Engage ICANN application specialists for detailed evaluation
- STRATEGIC PLANNING: Develop comprehensive application strategy based on detailed analysis
"""
    
    def create_risk_assessment_embeddings(self, risk_data: List[Dict[str, Any]]) -> int:
        """Create embeddings for all risk assessments"""
        
        successful_imports = 0
        
        for i, row in enumerate(risk_data, 1):
            try:
                tld_string = row['tld_string']
                logger.info(f"Processing {i}/{len(risk_data)}: {tld_string}")
                
                # Create comprehensive content
                content = self.create_risk_assessment_content(row)
                
                # Generate embedding
                embedding = self.generate_embedding(content)
                if not embedding:
                    logger.warning(f"Could not generate embedding for {tld_string}")
                    continue
                
                # Parse risk taxonomy
                risk_taxonomy = self.categorize_risk_level(row['overall_risk_level'])
                risk_details = self.parse_risk_factors(row)
                
                # Prepare record for insertion
                record = {
                    'section_number': f'RISK.{tld_string.replace(".", "")}',
                    'section_title': f'Risk Assessment for {tld_string}',
                    'subsection_title': f'{risk_taxonomy["risk_category"]} - {risk_taxonomy["investment_recommendation"]}',
                    'page_number': 1000 + i,  # Use high page numbers for risk assessments
                    'content_text': content,
                    'content_type': 'section',
                    'content_length': len(content),
                    'document_version': 'Risk Assessment 2025',
                    'document_url': 'Internal Risk Assessment Database',
                    'last_updated': datetime.utcnow().isoformat(),
                    'embedding': embedding,
                    'embedding_model': 'text-embedding-3-small',
                    'embedding_created_at': datetime.utcnow().isoformat(),
                    'topic_tags': [
                        'risk-assessment',
                        'tld-evaluation',
                        risk_taxonomy['risk_category'].lower().replace('_', '-'),
                        f'score-{risk_taxonomy["risk_score"]}',
                        tld_string.replace('.', '')
                    ],
                    'relevance_keywords': [
                        tld_string,
                        risk_taxonomy['risk_category'],
                        risk_taxonomy['investment_recommendation']
                    ],
                    'application_sections': [13, 18, 19, 20, 21],  # All application sections relevant
                    'context_summary': f'{risk_taxonomy["risk_category"]} risk assessment for {tld_string} with {risk_taxonomy["investment_recommendation"]} recommendation',
                    'related_procedures': None,
                    'policy_implications': f'Risk Score: {risk_taxonomy["risk_score"]}/4, Action: {risk_taxonomy["action_required"]}',
                    'content_quality_score': 0.98,  # High quality as it's real assessment data
                    'embedding_quality_score': None
                }
                
                # Insert into database
                result = self.supabase.table('guidebook_embeddings').insert(record).execute()
                
                if result.data:
                    successful_imports += 1
                    logger.info(f"✅ Added risk assessment for {tld_string}")
                else:
                    logger.error(f"❌ Failed to insert risk assessment for {tld_string}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing {row.get('tld_string', 'unknown')}: {e}")
        
        return successful_imports
    
    def generate_risk_taxonomy_summary(self, risk_data: List[Dict[str, Any]]) -> str:
        """Generate summary of risk taxonomy for embedding"""
        
        # Count risk categories
        risk_counts = {}
        for row in risk_data:
            risk_taxonomy = self.categorize_risk_level(row['overall_risk_level'])
            category = risk_taxonomy['risk_category']
            risk_counts[category] = risk_counts.get(category, 0) + 1
        
        total_assessed = len(risk_data)
        
        content = f"""
TLD RISK ASSESSMENT TAXONOMY AND DATABASE SUMMARY

COMPREHENSIVE RISK CLASSIFICATION SYSTEM:
Our risk assessment database contains detailed evaluations for {total_assessed} TLD strings, classified using a 4-tier risk taxonomy system.

RISK CATEGORY DISTRIBUTION:
"""
        
        for category, count in sorted(risk_counts.items()):
            percentage = (count / total_assessed) * 100
            content += f"- {category}: {count} strings ({percentage:.1f}%)\n"
        
        content += """
RISK SCORING METHODOLOGY:
- Score 4 (HIGH_RISK): Multiple blocking issues, not recommended for investment
- Score 3 (MODERATE_RISK): Significant issues requiring comprehensive mitigation
- Score 2 (MANAGEABLE_RISK): Viable with proper planning and risk mitigation
- Score 1 (LOW_RISK): Good candidate with minimal risk factors

EVALUATION CRITERIA ANALYZED:
- Technical Compliance Assessment
- Name Collision Risk Analysis
- String Similarity Evaluation
- Safeguard Policy Compliance
- Geopolitical Risk Assessment
- Legal and Trademark Conflict Analysis
- Cultural and Linguistic Risk Evaluation

INVESTMENT RECOMMENDATION CATEGORIES:
- NOT_RECOMMENDED: Avoid application due to high failure probability
- PROCEED_WITH_CAUTION: Detailed mitigation strategies required
- VIABLE_WITH_PLANNING: Standard risk management practices needed
- RECOMMENDED: Strong candidate for application success

ACTION REQUIREMENTS BY RISK LEVEL:
- AVOID_APPLICATION: Consider alternative strings
- DETAILED_MITIGATION_REQUIRED: Engage specialized legal counsel
- STANDARD_MITIGATION_REQUIRED: Implement standard risk management
- STANDARD_PREPARATIONS: Follow standard application procedures

DATA CONFIDENCE AND METHODOLOGY:
All assessments based on comprehensive multi-tool analysis including:
- Advanced String Similarity Analysis
- Global Trademark Conflict Analysis
- USPTO Patent Conflict Analysis
- Magnitude Collision Analysis
- DNS Stability Review
- GAC Precedent Analysis

This database represents the most comprehensive TLD risk assessment collection available, providing evidence-based guidance for gTLD application strategy and investment decisions.
        """
        
        return content.strip()

def main():
    """Main execution function"""
    try:
        logger.info("🚀 Importing TLD Risk Assessment Data...")
        
        # Initialize importer
        importer = RiskAssessmentImporter()
        
        # Load risk data from CSV
        csv_path = "tld_risk_summary_20250815_061603.csv"
        risk_data = importer.load_risk_data_from_csv(csv_path)
        
        if not risk_data:
            logger.error("❌ No risk data loaded from CSV")
            return
        
        # Create risk assessment embeddings
        logger.info(f"📊 Creating embeddings for {len(risk_data)} risk assessments...")
        successful_imports = importer.create_risk_assessment_embeddings(risk_data)
        
        # Create taxonomy summary embedding
        logger.info("📋 Creating risk taxonomy summary...")
        taxonomy_content = importer.generate_risk_taxonomy_summary(risk_data)
        taxonomy_embedding = importer.generate_embedding(taxonomy_content)
        
        if taxonomy_embedding:
            taxonomy_record = {
                'section_number': 'RISK.TAXONOMY',
                'section_title': 'TLD Risk Assessment Taxonomy and Database Summary',
                'subsection_title': 'Comprehensive Risk Classification System',
                'page_number': 999,
                'content_text': taxonomy_content,
                'content_type': 'section',
                'content_length': len(taxonomy_content),
                'document_version': 'Risk Assessment Database 2025',
                'document_url': 'Internal Risk Assessment Database',
                'last_updated': datetime.utcnow().isoformat(),
                'embedding': taxonomy_embedding,
                'embedding_model': 'text-embedding-3-small',
                'embedding_created_at': datetime.utcnow().isoformat(),
                'topic_tags': ['risk-taxonomy', 'database-summary', 'classification-system'],
                'relevance_keywords': ['risk assessment', 'taxonomy', 'classification'],
                'application_sections': [13, 18, 19, 20, 21],
                'context_summary': 'Comprehensive overview of TLD risk assessment taxonomy and database',
                'related_procedures': None,
                'policy_implications': 'Risk-based decision making framework for gTLD applications',
                'content_quality_score': 0.99,
                'embedding_quality_score': None
            }
            
            result = importer.supabase.table('guidebook_embeddings').insert(taxonomy_record).execute()
            if result.data:
                logger.info("✅ Added risk taxonomy summary")
                successful_imports += 1
        
        logger.info("\n" + "="*80)
        logger.info("✅ RISK ASSESSMENT DATA IMPORT COMPLETE!")
        logger.info("="*80)
        logger.info(f"\nSuccessfully imported {successful_imports} risk assessments")
        logger.info(f"Total TLD strings analyzed: {len(risk_data)}")
        logger.info("\nThe TLD Assistant can now provide:")
        logger.info("• Specific risk assessments for evaluated TLD strings")
        logger.info("• Detailed risk factor analysis and explanations")
        logger.info("• Investment recommendations based on comprehensive evaluation")
        logger.info("• Strategic guidance for application planning")
        logger.info("• Risk taxonomy and classification insights")
        logger.info("\nUsers can now ask questions like:")
        logger.info("• 'What is the risk assessment for .tech?'")
        logger.info("• 'Which TLD strings are high risk and why?'")
        logger.info("• 'What are the main risk factors for .crypto?'")
        logger.info("• 'Should I invest in a .nft application?'")
        
    except Exception as e:
        logger.error(f"❌ Failed to import risk assessment data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
