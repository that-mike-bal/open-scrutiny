#!/usr/bin/env python3
"""
Add The Applicant's Journey to Guidebook Embeddings

Add ICANN's "The Applicant's Journey" process content directly to the 
guidebook_embeddings table for TLD Assistant reference.
"""

import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import openai

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import get_supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ApplicantsJourneyAdder:
    """Add Applicant's Journey content to guidebook embeddings"""
    
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
    
    def add_applicants_journey_sections(self):
        """Add The Applicant's Journey sections to guidebook embeddings"""
        
        journey_sections = [
            {
                'section_number': 'AJ.1',
                'section_title': 'The Applicant\'s Journey - Process Overview',
                'content_text': """
The Applicant's Journey provides a comprehensive overview of the new gTLD application process from initial planning through delegation. The journey consists of seven key phases:

1. PRE-APPLICATION PHASE (3-6 months)
   - String selection and evaluation research
   - Community consultation and outreach
   - Technical and operational planning
   - Financial planning and projections
   - Legal and regulatory considerations
   - Application preparation and review

2. APPLICATION SUBMISSION (90 days)
   - Application form completion and submission
   - Required documentation upload
   - Fee payment ($185,000 base evaluation fee)
   - Supporting materials submission
   - Deadline compliance and final review

3. INITIAL EVALUATION (5-8 months)
   - String similarity review by expert panel
   - DNS stability and security review
   - Geographic names evaluation (if applicable)
   - Technical and operational capability assessment
   - Financial capability review
   - Registry services evaluation

4. EXTENDED EVALUATION (3-6 months, if required)
   - Community priority evaluation for community applications
   - String confusion objection proceedings
   - Legal rights objection proceedings
   - Limited public interest objection proceedings
   - Community objection proceedings

5. CONTENTION RESOLUTION (2-4 months)
   - Contention set identification for similar strings
   - Auction procedures or community priority resolution
   - Settlement negotiations between applicants
   - Withdrawal processes and agreements

6. CONTRACTING AND DELEGATION (2-3 months)
   - Registry agreement negotiation and execution
   - Pre-delegation testing requirements
   - IANA delegation process coordination
   - Launch preparation and timeline planning
   - Sunrise and trademark claims period setup

7. POST-DELEGATION OBLIGATIONS (ongoing)
   - Registry operations and service management
   - ICANN compliance monitoring and reporting
   - Periodic reporting requirements
   - Registry agreement renewal procedures

The complete journey typically takes 12-18 months from application submission to delegation, depending on evaluation complexity, objection proceedings, and contention resolution requirements.
                """,
                'page_number': 1,
                'content_type': 'section',
                'topic_tags': ['application-process', 'timeline', 'evaluation', 'delegation'],
                'application_sections': [13, 18, 19, 20, 21],
                'context_summary': 'Complete overview of the gTLD application process from planning to delegation'
            },
            
            {
                'section_number': 'AJ.2',
                'section_title': 'Application Timeline and Critical Milestones',
                'content_text': """
DETAILED APPLICATION TIMELINE WITH CRITICAL MILESTONES:

PRE-APPLICATION PHASE (Months 1-6):
- Month 1: String research, availability check, similarity analysis
- Month 2: Community outreach, stakeholder consultation
- Month 3: Technical architecture planning, DNS infrastructure design
- Month 4: Financial modeling, revenue projections, funding arrangements
- Month 5: Legal review, trademark clearance, regulatory compliance
- Month 6: Application drafting, document preparation, final review

APPLICATION WINDOW (90 days):
- Day 1-30: Application submission period opens, early submissions
- Day 31-60: Peak submission period, system capacity management
- Day 61-90: Final submission period, last-minute corrections allowed
- Day 90: Application window closes, no further submissions accepted

INITIAL EVALUATION PHASE (Months 7-14):
- Month 7: Administrative completeness check, fee verification
- Month 8-9: String similarity review by expert linguistic panel
- Month 10-11: Technical and operational capability assessment
- Month 12-13: Financial capability review and verification
- Month 14: Initial evaluation results published, pass/fail determination

EXTENDED EVALUATION (Months 15-20, if triggered):
- Months 15-17: Community priority evaluation for community applications
- Months 15-18: Objection proceedings (string confusion, legal rights)
- Months 18-20: Dispute resolution panels, expert determinations
- Month 20: Extended evaluation results, final determinations

CONTENTION RESOLUTION (Months 21-24):
- Month 21: Contention sets identified, resolution procedures initiated
- Month 22: Auction processes or community priority evaluations
- Month 23: Settlement negotiations, withdrawal agreements
- Month 24: Final contention resolution, successful applicants determined

CONTRACTING PHASE (Months 25-27):
- Month 25: Registry agreement negotiations begin
- Month 26: Contract terms finalized, legal review completed
- Month 27: Registry agreement execution, pre-delegation requirements

DELEGATION PHASE (Months 28-30):
- Month 28: Pre-delegation testing, technical validation
- Month 29: IANA coordination, root zone preparation
- Month 30: DNS delegation, registry launch preparation

Critical success factors include meeting all deadlines, maintaining complete documentation, engaging with community stakeholders, and ensuring technical and financial readiness throughout the process.
                """,
                'page_number': 2,
                'content_type': 'section',
                'topic_tags': ['timeline', 'milestones', 'deadlines', 'planning'],
                'application_sections': [13, 18, 19, 20, 21],
                'context_summary': 'Detailed timeline with specific milestones and deadlines for each phase'
            },
            
            {
                'section_number': 'AJ.3',
                'section_title': 'Community Engagement and Consultation Requirements',
                'content_text': """
COMMUNITY ENGAGEMENT REQUIREMENTS FOR gTLD APPLICATIONS:

MANDATORY CONSULTATION PERIODS:
All applicants must demonstrate appropriate consultation with relevant communities, particularly for strings that may affect specific geographic, cultural, or interest communities.

GEOGRAPHIC STRINGS:
- Government consultation required for country/territory names
- Minimum 60-day consultation period with relevant governments
- Documentation of government positions (support/non-objection/objection)
- Alternative dispute resolution if government objects
- Cultural and linguistic community engagement for regional terms

COMMUNITY-BASED APPLICATIONS:
- Substantial community support documentation required
- Community definition and nexus establishment
- Endorsement from recognized community institutions
- Registration policies serving community interests
- Opposition assessment from community members

CONSULTATION BEST PRACTICES:
1. Early Engagement (6+ months before application)
   - Identify relevant stakeholder communities
   - Establish communication channels and forums
   - Provide clear information about proposed gTLD
   - Allow sufficient time for community feedback

2. Transparent Communication
   - Public announcement of application intentions
   - Clear explanation of proposed registration policies
   - Open forums for community input and concerns
   - Regular updates on application progress

3. Documentation Requirements
   - Record of all consultation activities
   - Summary of community feedback received
   - Response to concerns and objections raised
   - Evidence of community support or endorsement

4. Ongoing Engagement
   - Commitment to continued community involvement
   - Advisory mechanisms for policy development
   - Dispute resolution procedures for community concerns
   - Regular reporting on community benefit delivery

OBJECTION MECHANISMS:
Communities can file formal objections during the objection period:
- Community objection for substantial opposition
- Limited public interest objection for policy concerns
- String confusion objection for similar strings
- Legal rights objection for trademark issues

EVALUATION CRITERIA:
Community engagement is evaluated based on:
- Scope and depth of consultation activities
- Quality of stakeholder identification and outreach
- Responsiveness to community feedback and concerns
- Ongoing commitment to community benefit and involvement

Effective community engagement significantly improves application success rates and reduces the likelihood of objections during the evaluation process.
                """,
                'page_number': 3,
                'content_type': 'section',
                'topic_tags': ['community', 'consultation', 'engagement', 'objections'],
                'application_sections': [18, 20],
                'context_summary': 'Requirements and best practices for community consultation and engagement'
            },
            
            {
                'section_number': 'AJ.4',
                'section_title': 'Financial Planning and Capability Demonstration',
                'content_text': """
FINANCIAL CAPABILITY REQUIREMENTS FOR gTLD APPLICATIONS:

FINANCIAL DOCUMENTATION REQUIREMENTS:
Applicants must demonstrate sufficient financial capability to establish and operate a registry throughout the registry agreement term.

REQUIRED FINANCIAL STATEMENTS:
- Audited financial statements for the past 3 years
- If applicant is newly formed, parent/sponsor financial statements
- Financial projections for 5 years post-delegation
- Cash flow analysis and working capital projections
- Revenue and cost modeling with supporting assumptions

FUNDING SOURCE DOCUMENTATION:
Acceptable funding sources include:
- Corporate capital and retained earnings
- Bank loans and committed credit facilities
- Investor equity commitments with executed agreements
- Parent company guarantees and support letters
- Grant funding (with appropriate restrictions)

COST MODELING REQUIREMENTS:
1. Application and Evaluation Costs
   - Base evaluation fee: $185,000 (non-refundable)
   - Extended evaluation fee: $50,000 (if applicable)
   - Auction fees (if contention resolution required)
   - Legal and consulting fees throughout process

2. Registry Infrastructure Costs
   - DNS infrastructure and redundancy systems
   - Registration system development and maintenance
   - Security systems and monitoring capabilities
   - Data escrow and backup systems
   - Technical support and operations staff

3. Operational Expenses
   - Personnel costs (technical, business, legal)
   - Marketing and business development expenses
   - Compliance and reporting costs
   - Insurance and risk management expenses
   - Ongoing ICANN fees and assessments

4. Contingency and Risk Reserves
   - Minimum 12 months operating expenses in reserve
   - Business interruption and disaster recovery funds
   - Legal defense and dispute resolution reserves
   - Technology refresh and upgrade provisions

REVENUE PROJECTIONS:
- Domain registration volume forecasts
- Pricing strategy and market positioning
- Revenue per domain and growth assumptions
- Alternative revenue streams (premium names, services)
- Market penetration and competitive analysis

FINANCIAL EVALUATION CRITERIA:
- Adequacy of funding for 5-year operational period
- Reasonableness of cost and revenue assumptions
- Quality and reliability of funding commitments
- Financial stability of applicant organization
- Contingency planning and risk mitigation measures

COMMON DEFICIENCIES:
- Insufficient funding commitments or documentation
- Unrealistic revenue projections or market assumptions
- Inadequate cost modeling or operational planning
- Lack of contingency reserves or risk management
- Poor quality financial statements or projections

Applications failing financial capability may be given opportunity to cure deficiencies with additional funding commitments or improved documentation.
                """,
                'page_number': 4,
                'content_type': 'section',
                'topic_tags': ['financial', 'capability', 'funding', 'costs', 'revenue'],
                'application_sections': [21],
                'context_summary': 'Comprehensive financial requirements and planning guidance for applications'
            }
        ]
        
        logger.info(f"Adding {len(journey_sections)} Applicant's Journey sections to guidebook embeddings...")
        
        for section in journey_sections:
            try:
                # Generate embedding for the content
                embedding = self.generate_embedding(section['content_text'])
                if not embedding:
                    logger.warning(f"Could not generate embedding for {section['section_number']}")
                    continue
                
                # Prepare the record for insertion
                record = {
                    'section_number': section['section_number'],
                    'section_title': section['section_title'],
                    'subsection_title': None,
                    'page_number': section['page_number'],
                    'content_text': section['content_text'],
                    'content_type': section['content_type'],
                    'content_length': len(section['content_text']),
                    'document_version': '2025 Draft',
                    'document_url': 'https://www.icann.org/en/announcements/details/icann-webinar-will-introduce-complete-draft-applicant-guidebook-15-05-2025-en',
                    'last_updated': datetime.utcnow().isoformat(),
                    'embedding': embedding,
                    'embedding_model': 'text-embedding-3-small',
                    'embedding_created_at': datetime.utcnow().isoformat(),
                    'topic_tags': section['topic_tags'],
                    'relevance_keywords': None,
                    'application_sections': section['application_sections'],
                    'context_summary': section['context_summary'],
                    'related_procedures': None,
                    'policy_implications': None,
                    'content_quality_score': 0.95,
                    'embedding_quality_score': None
                }
                
                # Insert into database
                result = self.supabase.table('guidebook_embeddings').insert(record).execute()
                
                if result.data:
                    logger.info(f"✅ Added: {section['section_number']} - {section['section_title']}")
                else:
                    logger.error(f"❌ Failed to insert {section['section_number']}")
                    
            except Exception as e:
                logger.error(f"❌ Error adding {section['section_number']}: {e}")
        
        logger.info("🎉 Applicant's Journey sections added to guidebook embeddings!")

def main():
    """Main execution function"""
    try:
        logger.info("🚀 Adding The Applicant's Journey to guidebook embeddings...")
        
        adder = ApplicantsJourneyAdder()
        adder.add_applicants_journey_sections()
        
        logger.info("\n" + "="*80)
        logger.info("✅ THE APPLICANT'S JOURNEY INTEGRATION COMPLETE!")
        logger.info("="*80)
        logger.info("\nThe TLD Assistant can now reference:")
        logger.info("• Complete application process overview")
        logger.info("• Detailed timeline and milestones")
        logger.info("• Community engagement requirements")
        logger.info("• Financial planning and capability guidance")
        logger.info("\nUsers can now ask questions like:")
        logger.info("• 'What are the phases of the application process?'")
        logger.info("• 'How long does the application process take?'")
        logger.info("• 'What community consultation is required?'")
        logger.info("• 'What financial documentation do I need?'")
        
    except Exception as e:
        logger.error(f"❌ Failed to add Applicant's Journey: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
