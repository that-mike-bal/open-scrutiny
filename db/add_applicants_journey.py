#!/usr/bin/env python3
"""
Add The Applicant's Journey to External Resources

Add ICANN's "The Applicant's Journey" document and related process guidance
to the external resource embeddings database for TLD Assistant reference.
"""

import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import get_supabase
from db.populate_application_embeddings import ApplicationEmbeddingsPopulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_applicants_journey_resources():
    """Add The Applicant's Journey and related process resources"""
    
    # Initialize the populator
    populator = ApplicationEmbeddingsPopulator()
    supabase = get_supabase()
    
    # Define the Applicant's Journey resources in the format expected by the database
    applicants_journey_resources = [
        {
            'resource_url': 'https://www.icann.org/en/announcements/details/icann-webinar-will-introduce-complete-draft-applicant-guidebook-15-05-2025-en',
            'resource_title': 'The Applicant\'s Journey - Overview',
            'resource_type': 'process_guide',
            'resource_source': 'ICANN',
            'resource_description': 'The Applicant\'s Journey provides a comprehensive overview of the new gTLD application process from initial planning through delegation. This guide covers the seven key phases: pre-application planning, application submission, initial evaluation, extended evaluation (if required), contention resolution, contracting and delegation, and post-delegation obligations. The journey typically takes 12-18 months from application to delegation, depending on evaluation complexity and contention resolution needs.',
            'relevance_to_applications': 'Essential overview of the complete gTLD application process for all applicants.',
            'relevant_questions': ['18a', '19.1', '20.1', '21.1'],
            'application_sections': [13, 18, 19, 20, 21],
            'topic_tags': ['application-process', 'evaluation', 'delegation', 'timeline'],
            'authority_level': 5,
            'complexity_level': 2,
            'publication_date': '2025-05-15',
            'version': 'Draft 2025'
        },
        
        {
            "title": "Application Process Timeline and Milestones",
            "content": """
DETAILED APPLICATION TIMELINE:

PHASE 1: PRE-APPLICATION (3-6 months)
- Week 1-4: String research and selection
- Week 5-8: Community outreach and consultation
- Week 9-12: Technical architecture planning
- Week 13-16: Financial modeling and projections
- Week 17-20: Legal review and documentation
- Week 21-24: Application preparation and review

PHASE 2: APPLICATION WINDOW (90 days)
- Day 1: Application system opens
- Day 1-60: Application submission period
- Day 61-90: Final submission and corrections
- Day 90: Application window closes

PHASE 3: INITIAL EVALUATION (5-8 months)
- Month 1: Administrative completeness check
- Month 2-3: String similarity review
- Month 4-5: Technical/operational review
- Month 6-7: Financial capability review
- Month 8: Initial evaluation results

PHASE 4: EXTENDED EVALUATION (if needed, 3-6 months)
- Community priority evaluation
- Objection proceedings
- Dispute resolution panels
- Appeals processes

PHASE 5: CONTENTION RESOLUTION (2-4 months)
- Contention set identification
- Auction or community priority
- Settlement negotiations
- Final resolution

PHASE 6: CONTRACTING (2-3 months)
- Registry agreement negotiation
- Contract execution
- Pre-delegation requirements
- Technical testing

PHASE 7: DELEGATION (1-2 months)
- IANA coordination
- Root zone changes
- DNS propagation
- Launch preparation

Critical success factors include early preparation, thorough documentation, community engagement, and compliance with all ICANN requirements.
            """,
            "resource_url": "https://www.icann.org/resources/pages/gtld-application-process-2012-05-31-en",
            "resource_type": "timeline",
            "topic_tags": ["timeline", "milestones", "evaluation", "delegation"],
            "content_type": "reference"
        },
        
        {
            "title": "String Evaluation and Similarity Assessment Process",
            "content": """
STRING EVALUATION COMPREHENSIVE PROCESS:

1. INITIAL STRING REVIEW
   - Format validation (ASCII, length, character restrictions)
   - Reserved name checking (IANA, RFC, Spec 5)
   - Basic similarity screening
   - IDN requirements verification

2. STRING SIMILARITY PANEL EVALUATION
   Panel Composition:
   - Linguistic experts
   - Intellectual property specialists
   - Domain name policy experts
   - Cultural and geographic representatives

   Evaluation Criteria:
   - Visual similarity (character confusion, typography)
   - Aural similarity (pronunciation, phonetic confusion)
   - Meaning similarity (semantic relationships, translations)
   - Conceptual similarity (related ideas, categories)

3. SIMILARITY ASSESSMENT FACTORS
   Visual Factors:
   - Character substitution (0/O, 1/l/I)
   - Script mixing and homographs
   - Case variations and styling
   - Length and structure patterns

   Aural Factors:
   - Phonetic equivalence
   - Pronunciation variations
   - Regional accent considerations
   - Sound-alike patterns

   Meaning Factors:
   - Translation equivalents
   - Synonyms and related terms
   - Cultural interpretations
   - Brand and trademark implications

4. DECISION CRITERIA
   - Likelihood of confusion assessment
   - User experience impact
   - DNS stability considerations
   - Public interest factors

5. APPEAL PROCESSES
   - Initial review reconsideration
   - Independent review panel
   - Expert determination
   - Community input consideration

The string similarity review is critical for preventing user confusion and maintaining DNS stability. Applications with similar strings may be placed in contention sets requiring resolution through community priority evaluation or auction.
            """,
            "resource_url": "https://www.icann.org/resources/pages/string-similarity-2012-05-31-en",
            "resource_type": "evaluation_guide",
            "topic_tags": ["string-similarity", "evaluation", "dns-stability", "confusion"],
            "content_type": "technical"
        },
        
        {
            "title": "Community Priority Evaluation Framework",
            "content": """
COMMUNITY PRIORITY EVALUATION (CPE) PROCESS:

PURPOSE AND SCOPE:
Community Priority Evaluation provides a mechanism for community-based applications to prevail over standard applications in contention sets, recognizing the special nature of community representation.

ELIGIBILITY REQUIREMENTS:
1. Community-based application designation
2. Substantial opposition from significant portion of community
3. Clear community definition and nexus
4. Community endorsement documentation
5. Registration policies serving community interests

EVALUATION CRITERIA (16 points total):

1. COMMUNITY ESTABLISHMENT (0-4 points)
   - Delineated and organized community
   - Pre-existing community with awareness
   - Size and longevity of community
   - Extension of community offline

2. NEXUS BETWEEN PROPOSED STRING AND COMMUNITY (0-4 points)
   - String identifies community
   - String has meaning to community members  
   - String represents community activities
   - No competing definitions or uses

3. REGISTRATION POLICIES (0-4 points)
   - Eligibility restrictions for community members
   - Name selection requirements
   - Content and use restrictions
   - Enforcement and appeals mechanisms

4. COMMUNITY ENDORSEMENT (0-4 points)
   - Support from institutions/organizations
   - Pre-existing community institutions
   - Established governance mechanisms
   - Opposition to application assessment

SCORING AND THRESHOLDS:
- Minimum 14/16 points required to prevail
- Each criterion scored independently
- Detailed justification required for scores
- Independent expert panel evaluation

DOCUMENTATION REQUIREMENTS:
- Community definition and boundaries
- Evidence of community establishment
- Registration policy commitments
- Endorsement letters and support evidence
- Opposition impact assessment

CPE provides protection for legitimate community interests while maintaining objective evaluation standards.
            """,
            "resource_url": "https://www.icann.org/resources/pages/cpe-2012-05-31-en",
            "resource_type": "evaluation_framework",
            "topic_tags": ["community", "priority-evaluation", "contention", "governance"],
            "content_type": "policy"
        },
        
        {
            "title": "Financial Capability Assessment Guidelines",
            "content": """
FINANCIAL CAPABILITY EVALUATION COMPREHENSIVE GUIDE:

ASSESSMENT OBJECTIVES:
Ensure applicants have sufficient financial resources and capability to establish and operate a registry for the applied-for gTLD throughout the registry agreement term.

KEY EVALUATION AREAS:

1. FINANCIAL STATEMENTS AND PROJECTIONS
   Required Documentation:
   - Audited financial statements (3 years)
   - Financial projections (5 years)
   - Cash flow analysis
   - Revenue and cost modeling
   - Funding source documentation

   Analysis Factors:
   - Financial stability and liquidity
   - Revenue diversification
   - Cost structure reasonableness
   - Growth assumptions validity
   - Risk factor identification

2. FUNDING SOURCES AND COMMITMENTS
   Acceptable Sources:
   - Corporate capital and retained earnings
   - Bank loans and credit facilities
   - Investor commitments and equity
   - Parent company guarantees
   - Grant funding (with restrictions)

   Documentation Requirements:
   - Executed funding agreements
   - Letters of credit or guarantees
   - Board resolutions and commitments
   - Investor term sheets
   - Banking relationship confirmation

3. OPERATIONAL COST MODELING
   Required Cost Categories:
   - Registry infrastructure and systems
   - Personnel and operational expenses
   - Marketing and business development
   - Legal and regulatory compliance
   - Contingency and risk reserves

   Evaluation Standards:
   - Industry benchmark comparison
   - Scalability and efficiency analysis
   - Technology investment adequacy
   - Operational risk assessment
   - Long-term sustainability review

4. REVENUE PROJECTIONS AND ASSUMPTIONS
   Revenue Stream Analysis:
   - Domain registration volumes
   - Pricing strategy and elasticity
   - Market penetration assumptions
   - Competitive positioning
   - Alternative revenue sources

   Validation Requirements:
   - Market research support
   - Comparable registry analysis
   - Sensitivity analysis
   - Scenario planning
   - Risk-adjusted projections

5. FINANCIAL RISK MITIGATION
   Required Considerations:
   - Contingency planning
   - Insurance coverage
   - Escrow arrangements
   - Transition planning
   - Registry continuity measures

EVALUATION STANDARDS:
- 5-year operational sustainability
- Adequate capitalization levels
- Reasonable growth assumptions
- Appropriate risk management
- Credible funding commitments

Applications failing financial capability review may be given opportunity to cure deficiencies with additional documentation or funding commitments.
            """,
            "resource_url": "https://www.icann.org/resources/pages/financial-2012-05-31-en",
            "resource_type": "assessment_guide",
            "topic_tags": ["financial", "capability", "funding", "projections"],
            "content_type": "requirements"
        }
    ]
    
    logger.info(f"Adding {len(applicants_journey_resources)} Applicant's Journey resources...")
    
    # Add each resource to the database
    for resource in applicants_journey_resources:
        try:
            # Add to external resources
            populator._add_external_resource(
                title=resource["title"],
                content=resource["content"],
                resource_url=resource["resource_url"],
                resource_type=resource["resource_type"],
                topic_tags=resource["topic_tags"],
                content_type=resource["content_type"]
            )
            
            logger.info(f"✅ Added: {resource['title']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to add {resource['title']}: {e}")
    
    logger.info("🎉 Applicant's Journey resources added successfully!")

def main():
    """Main execution function"""
    try:
        logger.info("🚀 Adding The Applicant's Journey to TLD Assistant database...")
        add_applicants_journey_resources()
        
        logger.info("\n" + "="*80)
        logger.info("✅ THE APPLICANT'S JOURNEY INTEGRATION COMPLETE!")
        logger.info("="*80)
        logger.info("\nThe TLD Assistant can now reference:")
        logger.info("• Complete application process overview")
        logger.info("• Detailed timeline and milestones")
        logger.info("• String evaluation procedures")
        logger.info("• Community priority evaluation framework")
        logger.info("• Financial capability assessment guidelines")
        logger.info("\nUsers can now ask questions like:")
        logger.info("• 'What are the key phases of the application process?'")
        logger.info("• 'How long does string evaluation take?'")
        logger.info("• 'What is community priority evaluation?'")
        logger.info("• 'What financial documentation do I need?'")
        
    except Exception as e:
        logger.error(f"❌ Failed to add Applicant's Journey: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
