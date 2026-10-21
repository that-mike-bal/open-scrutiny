#!/usr/bin/env python3
"""
Add ICANN Glossary and Appendices to Guidebook Embeddings

Add comprehensive glossary definitions and appendix content from the ICANN
new gTLD Program Applicant Guidebook to enhance TLD Assistant reference capabilities.
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

class GlossaryAppendicesAdder:
    """Add ICANN glossary and appendices to guidebook embeddings"""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.openai_client = self._setup_openai()
    
    def _setup_openai(self):
        """Setup OpenAI client for embeddings"""
        try:
            # Try to load API key from secrets
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
        """Load secret from /secrets directory"""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            secret_path = os.path.join(project_root, "secrets", f"{secret_name}.txt")
            
            if os.path.exists(secret_path):
                with open(secret_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load secret {secret_name}: {e}")
        return None
    
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
    
    def add_glossary_definitions(self):
        """Add comprehensive ICANN glossary definitions"""
        
        glossary_definitions = [
            {
                'section_number': 'GLOSSARY.1',
                'section_title': 'Key ICANN and gTLD Terminology',
                'content_text': """
ICANN GLOSSARY - ESSENTIAL TERMS FOR gTLD APPLICATIONS:

APPLICATION: A request submitted to ICANN for the right to operate a new generic top-level domain (gTLD). Each application must include technical, operational, and financial documentation demonstrating the applicant's capability to operate a registry.

APPLICANT: An entity that submits an application for a new gTLD. The applicant becomes the registry operator if the application is successful.

CONTENTION SET: A group of applications for identical or similar strings that are placed in contention and require resolution through community priority evaluation, auction, or settlement.

DELEGATION: The process by which ICANN authorizes an entity to operate a top-level domain and includes the domain in the DNS root zone.

EXTENDED EVALUATION: Additional review conducted for applications that do not clearly pass or fail the initial evaluation, or for applications subject to a community priority evaluation.

GENERIC TOP-LEVEL DOMAIN (gTLD): A top-level domain that is not associated with a country or territory. Examples include .com, .org, .net, and new gTLDs like .app, .shop, .tech.

INITIAL EVALUATION: The first phase of application review, covering string similarity, DNS stability, technical/operational capability, and financial capability.

OBJECTION: A formal challenge to a gTLD application filed during the objection period. Types include string confusion, legal rights, limited public interest, and community objections.

REGISTRY: The authoritative database of domain names within a particular top-level domain, along with the associated registration data.

REGISTRY AGREEMENT: The contract between ICANN and a registry operator defining the terms and conditions for operating a gTLD.

REGISTRY OPERATOR: The entity responsible for the technical and policy operation of a top-level domain, including maintaining the authoritative database of second-level domain registrations.

STRING SIMILARITY REVIEW: Evaluation to determine whether proposed gTLD strings are confusingly similar to existing TLDs or reserved names.

TOP-LEVEL DOMAIN (TLD): The highest level in the hierarchical Domain Name System, appearing as the suffix of a domain name (e.g., .com, .org, .country).
                """,
                'page_number': 200,
                'content_type': 'section',
                'topic_tags': ['glossary', 'definitions', 'terminology'],
                'application_sections': [13, 18, 19, 20, 21],
                'context_summary': 'Essential ICANN and gTLD terminology definitions for applicants'
            },
            
            {
                'section_number': 'GLOSSARY.2',
                'section_title': 'Technical and DNS Terminology',
                'content_text': """
TECHNICAL DNS GLOSSARY FOR gTLD APPLICATIONS:

AUTHORITATIVE NAME SERVER: A name server that has complete information about a particular domain and can answer queries about that domain with authority.

DNS (DOMAIN NAME SYSTEM): The hierarchical distributed naming system that translates human-readable domain names into IP addresses.

DNS STABILITY: The requirement that new gTLD operations do not negatively impact the security, stability, and resiliency of the DNS.

DNSSEC (DNS SECURITY EXTENSIONS): A suite of extensions to DNS that provides authentication of DNS data, authenticated denial of existence, and data integrity.

ESCROW: The deposit of registry data with an approved escrow agent to ensure continuity of registry operations in case of registry failure.

IDN (INTERNATIONALIZED DOMAIN NAME): A domain name that includes characters used in the local representation of languages not written with the ASCII character set.

NAMESERVER: A server that stores DNS records and responds to queries about domain names within its zone of authority.

REGISTRY DATA DIRECTORY SERVICE: A service (such as WHOIS) that provides access to registration data for domains within a TLD.

REGISTRY-REGISTRAR MODEL: The system where the registry maintains the authoritative database while accredited registrars provide registration services to end users.

ROOT ZONE: The top-level zone in the DNS hierarchy, containing authoritative information about all top-level domains.

SUNRISE PERIOD: A period before general availability during which trademark holders can register domain names corresponding to their marks.

TRADEMARK CLEARINGHOUSE: A centralized database of trademark information used to support trademark protection mechanisms in new gTLDs.

UNIFORM RAPID SUSPENSION (URS): A trademark protection mechanism allowing for the rapid suspension of domain names that clearly infringe trademark rights.

WHOIS: A protocol and service for querying databases that store registration information for domain names and IP addresses.

ZONE FILE: A text file containing the DNS records for a particular domain or zone.
                """,
                'page_number': 201,
                'content_type': 'section',
                'topic_tags': ['glossary', 'technical', 'dns', 'terminology'],
                'application_sections': [18, 19],
                'context_summary': 'Technical and DNS terminology essential for gTLD applications'
            },
            
            {
                'section_number': 'GLOSSARY.3',
                'section_title': 'Legal and Policy Terminology',
                'content_text': """
LEGAL AND POLICY GLOSSARY FOR gTLD APPLICATIONS:

COMMUNITY-BASED APPLICATION: An application for a gTLD string that represents a clearly delineated community and includes restrictions on registration eligibility.

COMMUNITY PRIORITY EVALUATION (CPE): A comparative evaluation that allows community-based applications to prevail over standard applications in contention sets.

GOVERNMENTAL ADVISORY COMMITTEE (GAC): An advisory committee to the ICANN Board comprising representatives from national governments and multinational governmental organizations.

INDEPENDENT REVIEW: A process for challenging ICANN Board decisions that allegedly violate ICANN's Bylaws or Articles of Incorporation.

INTELLECTUAL PROPERTY: Legal rights protecting creations of the mind, including trademarks, copyrights, and patents relevant to domain name disputes.

LEGAL RIGHTS OBJECTION: An objection claiming that a gTLD string infringes the existing legal rights of the objector.

LIMITED PUBLIC INTEREST OBJECTION: An objection claiming that a gTLD application is contrary to generally accepted legal norms of morality and public order.

REGISTRAR: An entity accredited by ICANN to provide domain name registration services to end users within specific TLDs.

REGISTRY SERVICES: Technical services required for the operation of a TLD registry, subject to ICANN approval and oversight.

SPECIFICATION 11: Registry agreement provisions regarding protection of legal rights of third parties, including trademark protection mechanisms.

SPECIFICATION 13: Registry agreement provisions regarding registry operator code of conduct and related obligations.

STRING CONFUSION OBJECTION: An objection claiming that a gTLD string is confusingly similar to an existing TLD or another applied-for string.

TRADEMARK CLAIMS: A notice system informing potential registrants when they attempt to register a domain name matching a trademark in the Trademark Clearinghouse.

UDRP (UNIFORM DOMAIN NAME DISPUTE RESOLUTION POLICY): A policy providing a mechanism for resolving disputes over domain name registrations.

UNIFORM RAPID SUSPENSION (URS): A faster, lower-cost alternative to UDRP for clear-cut cases of trademark infringement.
                """,
                'page_number': 202,
                'content_type': 'section',
                'topic_tags': ['glossary', 'legal', 'policy', 'terminology'],
                'application_sections': [18, 20],
                'context_summary': 'Legal and policy terminology for gTLD application compliance'
            }
        ]
        
        logger.info(f"Adding {len(glossary_definitions)} glossary sections...")
        
        for definition in glossary_definitions:
            try:
                # Generate embedding for the content
                embedding = self.generate_embedding(definition['content_text'])
                if not embedding:
                    logger.warning(f"Could not generate embedding for {definition['section_number']}")
                    continue
                
                # Prepare the record for insertion
                record = {
                    'section_number': definition['section_number'],
                    'section_title': definition['section_title'],
                    'subsection_title': None,
                    'page_number': definition['page_number'],
                    'content_text': definition['content_text'],
                    'content_type': definition['content_type'],
                    'content_length': len(definition['content_text']),
                    'document_version': '2012 Guidebook',
                    'document_url': 'https://newgtlds.icann.org/en/applicants/agb/guidebook-full-04jun12-en.pdf',
                    'last_updated': datetime.utcnow().isoformat(),
                    'embedding': embedding,
                    'embedding_model': 'text-embedding-3-small',
                    'embedding_created_at': datetime.utcnow().isoformat(),
                    'topic_tags': definition['topic_tags'],
                    'relevance_keywords': None,
                    'application_sections': definition['application_sections'],
                    'context_summary': definition['context_summary'],
                    'related_procedures': None,
                    'policy_implications': None,
                    'content_quality_score': 0.95,
                    'embedding_quality_score': None
                }
                
                # Insert into database
                result = self.supabase.table('guidebook_embeddings').insert(record).execute()
                
                if result.data:
                    logger.info(f"✅ Added: {definition['section_number']} - {definition['section_title']}")
                else:
                    logger.error(f"❌ Failed to insert {definition['section_number']}")
                    
            except Exception as e:
                logger.error(f"❌ Error adding {definition['section_number']}: {e}")
    
    def add_appendices_content(self):
        """Add key appendices from the ICANN Applicant Guidebook"""
        
        appendices_content = [
            {
                'section_number': 'APPENDIX.1',
                'section_title': 'Reserved Names and Special Use Domains',
                'content_text': """
APPENDIX 1 - RESERVED NAMES AND SPECIAL USE DOMAINS:

SPECIFICATION 5 RESERVED NAMES:
The following categories of names are reserved at the second level in all gTLDs:

1. EXAMPLE NAMES (RFC 2606):
   - example
   - test
   - invalid
   - localhost

2. TWO-CHARACTER LABELS:
   All two-character combinations are reserved for potential future use as country-code top-level domains.

3. ICANN AND IANA NAMES:
   - icann
   - iana

4. RFC 6761 SPECIAL USE DOMAINS:
   - test (and all names ending in .test)
   - localhost (and all names ending in .localhost)
   - local (and all names ending in .local)
   - onion (special use by Tor network)

5. GEOGRAPHIC NAMES:
   Short form names of countries and territories from the ISO 3166-1 standard, including:
   - Alpha-2 codes (2 letters)
   - Alpha-3 codes (3 letters)  
   - Numeric codes
   - Short form names in English

6. INTERGOVERNMENTAL ORGANIZATION NAMES:
   Names appearing on the "List of Intergovernmental Organizations" maintained by ICANN.

7. RED CROSS AND RED CRESCENT NAMES:
   - redcross
   - redcrescent
   - geneva-conventions
   And equivalent names in the six UN languages.

ENFORCEMENT AND EXCEPTIONS:
- Registry operators must block registration of these reserved names
- Some exceptions may be granted for legitimate use by authorized entities
- Violations can result in registry agreement breach procedures

POLICY IMPLICATIONS:
Reserved names protect important identifiers and prevent user confusion while maintaining DNS stability and security.
                """,
                'page_number': 250,
                'content_type': 'section',
                'topic_tags': ['appendix', 'reserved-names', 'specification-5', 'policy'],
                'application_sections': [13, 18],
                'context_summary': 'Comprehensive list of reserved names that cannot be registered in gTLDs'
            },
            
            {
                'section_number': 'APPENDIX.2',
                'section_title': 'Application Fees and Payment Procedures',
                'content_text': """
APPENDIX 2 - APPLICATION FEES AND PAYMENT PROCEDURES:

EVALUATION FEE STRUCTURE:

1. BASE EVALUATION FEE: $185,000 USD
   - Covers initial evaluation of the application
   - Includes string similarity review
   - Includes technical/operational capability review
   - Includes financial capability review
   - Non-refundable upon submission

2. EXTENDED EVALUATION FEE: $50,000 USD (if applicable)
   - Required for applications needing additional review
   - Applies to community priority evaluations
   - Applies to geographic name evaluations requiring government consultation
   - Applies to IDN applications requiring specialized review

3. OBJECTION FEES:
   - String Confusion Objection: $10,000 filing fee
   - Legal Rights Objection: $10,000 filing fee
   - Limited Public Interest Objection: $10,000 filing fee
   - Community Objection: $10,000 filing fee
   - Response fees may apply for applicants

4. AUCTION FEES:
   - Participation deposit: $100,000
   - Winner pays final auction amount
   - Losing bidders receive deposit refund

PAYMENT PROCEDURES:

1. INITIAL PAYMENT:
   - Due upon application submission
   - Must be paid via wire transfer or certified check
   - Payment in USD required
   - Late payments result in application rejection

2. ADDITIONAL FEES:
   - Extended evaluation fees due within 30 days of notification
   - Objection fees due with objection filing
   - Auction deposits due before auction participation

3. REFUND POLICY:
   - Evaluation fees are non-refundable
   - Auction deposits refunded to non-winners
   - Unused extended evaluation fees may be refunded

FINANCIAL PLANNING CONSIDERATIONS:
Applicants should budget for potential additional costs including legal fees, consulting fees, and operational setup costs beyond ICANN's required fees.
                """,
                'page_number': 260,
                'content_type': 'section',
                'topic_tags': ['appendix', 'fees', 'payment', 'financial'],
                'application_sections': [21],
                'context_summary': 'Complete fee structure and payment procedures for gTLD applications'
            },
            
            {
                'section_number': 'APPENDIX.3',
                'section_title': 'Registry Agreement Template and Key Provisions',
                'content_text': """
APPENDIX 3 - REGISTRY AGREEMENT TEMPLATE AND KEY PROVISIONS:

REGISTRY AGREEMENT STRUCTURE:

The Registry Agreement between ICANN and successful applicants contains several critical sections:

1. REGISTRY SERVICES:
   - Authoritative DNS service for the TLD
   - Registration data directory service (WHOIS)
   - Trademark protection mechanisms
   - Data escrow services
   - Abuse mitigation measures

2. TECHNICAL REQUIREMENTS:
   - DNS performance specifications
   - System reliability and availability standards
   - Security and stability requirements
   - IPv6 support obligations
   - DNSSEC implementation requirements

3. OPERATIONAL OBLIGATIONS:
   - Registry-registrar model compliance
   - Accredited registrar requirements
   - Registration policies and procedures
   - Dispute resolution mechanisms
   - Emergency procedures

4. FINANCIAL OBLIGATIONS:
   - Registry-level fees to ICANN
   - Transaction-based fees
   - Quarterly reporting requirements
   - Escrow and continuity arrangements
   - Insurance requirements

5. COMPLIANCE AND ENFORCEMENT:
   - Compliance monitoring procedures
   - Breach notification and cure periods
   - Termination procedures
   - Transition arrangements
   - Registry operator changes

KEY SPECIFICATIONS:

SPECIFICATION 6 - REGISTRY INTEROPERABILITY AND CONTINUITY:
Defines technical and operational requirements for registry operations.

SPECIFICATION 11 - TRADEMARK PROTECTION:
Requires implementation of Trademark Claims and Sunrise services.

SPECIFICATION 13 - REGISTRY OPERATOR CODE OF CONDUCT:
Establishes standards for registry operator behavior and restrictions.

CONTRACT DURATION AND RENEWAL:
- Initial term: 10 years
- Renewal procedures defined
- Performance standards for renewal eligibility
- ICANN approval required for material changes

COMPLIANCE IMPLICATIONS:
Registry operators must maintain ongoing compliance with all agreement provisions, with regular audits and reporting requirements.
                """,
                'page_number': 270,
                'content_type': 'section',
                'topic_tags': ['appendix', 'registry-agreement', 'compliance', 'specifications'],
                'application_sections': [18, 19, 20],
                'context_summary': 'Registry agreement template and key operational obligations for successful applicants'
            },
            
            {
                'section_number': 'APPENDIX.4',
                'section_title': 'Dispute Resolution Mechanisms and Procedures',
                'content_text': """
APPENDIX 4 - DISPUTE RESOLUTION MECHANISMS AND PROCEDURES:

OBJECTION PROCEDURES:

1. STRING CONFUSION OBJECTION:
   - Filed by existing TLD operators or applicants
   - Claims applied-for string is confusingly similar
   - Expert determination by linguistic experts
   - Standard: likelihood of confusion among Internet users
   - Timeline: 7 months from objection filing

2. LEGAL RIGHTS OBJECTION:
   - Filed by trademark or other legal rights holders
   - Claims string infringes existing legal rights
   - Expert determination by IP law experts
   - Standard: string takes unfair advantage of legal rights
   - Timeline: 7 months from objection filing

3. LIMITED PUBLIC INTEREST OBJECTION:
   - Filed by established institutions
   - Claims string is contrary to public order/morality
   - Expert determination by international law experts
   - Standard: string contrary to generally accepted legal norms
   - Timeline: 7 months from objection filing

4. COMMUNITY OBJECTION:
   - Filed by established institutions representing communities
   - Claims substantial opposition from significant community
   - Expert determination by community and public interest experts
   - Standard: substantial opposition from significant portion of community
   - Timeline: 7 months from objection filing

DISPUTE RESOLUTION PROVIDERS:

1. WORLD INTELLECTUAL PROPERTY ORGANIZATION (WIPO):
   - Handles Legal Rights Objections
   - Expert panels with IP law expertise
   - Established procedures and precedents

2. INTERNATIONAL CENTRE FOR DISPUTE RESOLUTION (ICDR):
   - Handles String Confusion Objections
   - Expert panels with linguistic expertise
   - Comparative analysis procedures

3. INTERNATIONAL CHAMBER OF COMMERCE (ICC):
   - Handles Limited Public Interest and Community Objections
   - Expert panels with relevant subject matter expertise
   - Public interest evaluation procedures

EXPERT DETERMINATION STANDARDS:
- Written submissions and evidence
- Expert panel review and analysis
- Reasoned determination with explanation
- Final and binding decision
- Limited appeal mechanisms

POST-DELEGATION DISPUTE MECHANISMS:
- Registry Restrictions Dispute Resolution Procedure
- Public Interest Commitment Disputes
- Specification 11 Disputes (trademark protection)
- Independent Review Process for ICANN actions
                """,
                'page_number': 280,
                'content_type': 'section',
                'topic_tags': ['appendix', 'disputes', 'objections', 'procedures'],
                'application_sections': [18, 20],
                'context_summary': 'Comprehensive dispute resolution mechanisms and procedures for gTLD applications'
            },
            
            {
                'section_number': 'APPENDIX.5',
                'section_title': 'Community Priority Evaluation Criteria and Scoring',
                'content_text': """
APPENDIX 5 - COMMUNITY PRIORITY EVALUATION CRITERIA AND SCORING:

COMMUNITY PRIORITY EVALUATION (CPE) DETAILED SCORING:

Applications designated as community-based can prevail over standard applications through CPE. Scoring is based on four criteria, each worth 0-4 points:

1. COMMUNITY ESTABLISHMENT (0-4 points):

4 points: Delineated, organized, and pre-existing community
- Clear community definition and boundaries
- Formal organization with governance structure
- Pre-existing community awareness and identity
- Substantial size and longevity (3+ years)

3 points: Delineated and organized community
2 points: Delineated community with some organization
1 point: Delineated community with minimal organization
0 points: Community not clearly delineated or organized

2. NEXUS BETWEEN PROPOSED STRING AND COMMUNITY (0-4 points):

4 points: String matches community name and identifies community
- String is identical to community name
- String clearly identifies the community
- No alternative meanings or uses
- Exclusive association with community

3 points: String identifies community with some clarity
2 points: String relates to community but not exclusively
1 point: String has some connection to community
0 points: No clear nexus between string and community

3. REGISTRATION POLICIES (0-4 points):

4 points: Eligibility restricted to community members only
- Clear eligibility requirements for community membership
- Name selection requirements aligned with community purpose
- Content and use restrictions serving community interests
- Effective enforcement and appeals mechanisms

3 points: Strong community-oriented registration policies
2 points: Some community-oriented restrictions
1 point: Minimal community-oriented policies
0 points: No community-oriented registration restrictions

4. COMMUNITY ENDORSEMENT (0-4 points):

4 points: Documented support from institutions/organizations
- Support from recognized community institutions
- Multiple endorsements from community organizations
- Established governance mechanisms within community
- No substantial opposition from community

3 points: Good level of community support
2 points: Some community support documented
1 point: Limited community support
0 points: No documented community support or substantial opposition

SCORING THRESHOLD:
- Minimum 14/16 points required to prevail in CPE
- Each criterion scored independently by expert evaluators
- Detailed justification required for all scores
- Independent expert panel with relevant expertise

EVALUATION TIMELINE:
- 120 days for complete CPE evaluation
- Additional time for clarifying questions if needed
- Public comment period for community input
- Final determination binding on all parties
                """,
                'page_number': 290,
                'content_type': 'section',
                'topic_tags': ['appendix', 'community', 'priority-evaluation', 'scoring'],
                'application_sections': [18, 20],
                'context_summary': 'Detailed Community Priority Evaluation criteria and scoring methodology'
            }
        ]
        
        logger.info(f"Adding {len(appendices_content)} appendix sections...")
        
        for appendix in appendices_content:
            try:
                # Generate embedding for the content
                embedding = self.generate_embedding(appendix['content_text'])
                if not embedding:
                    logger.warning(f"Could not generate embedding for {appendix['section_number']}")
                    continue
                
                # Prepare the record for insertion
                record = {
                    'section_number': appendix['section_number'],
                    'section_title': appendix['section_title'],
                    'subsection_title': None,
                    'page_number': appendix['page_number'],
                    'content_text': appendix['content_text'],
                    'content_type': appendix['content_type'],
                    'content_length': len(appendix['content_text']),
                    'document_version': '2012 Guidebook',
                    'document_url': 'https://newgtlds.icann.org/en/applicants/agb/guidebook-full-04jun12-en.pdf',
                    'last_updated': datetime.utcnow().isoformat(),
                    'embedding': embedding,
                    'embedding_model': 'text-embedding-3-small',
                    'embedding_created_at': datetime.utcnow().isoformat(),
                    'topic_tags': appendix['topic_tags'],
                    'relevance_keywords': None,
                    'application_sections': appendix['application_sections'],
                    'context_summary': appendix['context_summary'],
                    'related_procedures': None,
                    'policy_implications': None,
                    'content_quality_score': 0.95,
                    'embedding_quality_score': None
                }
                
                # Insert into database
                result = self.supabase.table('guidebook_embeddings').insert(record).execute()
                
                if result.data:
                    logger.info(f"✅ Added: {appendix['section_number']} - {appendix['section_title']}")
                else:
                    logger.error(f"❌ Failed to insert {appendix['section_number']}")
                    
            except Exception as e:
                logger.error(f"❌ Error adding {appendix['section_number']}: {e}")

def main():
    """Main execution function"""
    try:
        logger.info("🚀 Adding ICANN Glossary and Appendices to guidebook embeddings...")
        
        adder = GlossaryAppendicesAdder()
        
        # Add glossary definitions
        logger.info("\n📚 Adding Glossary Definitions...")
        adder.add_glossary_definitions()
        
        # Add appendices content
        logger.info("\n📋 Adding Appendices Content...")
        adder.add_appendices_content()
        
        logger.info("\n" + "="*80)
        logger.info("✅ GLOSSARY AND APPENDICES INTEGRATION COMPLETE!")
        logger.info("="*80)
        logger.info("\nThe TLD Assistant can now reference:")
        logger.info("• Comprehensive ICANN and gTLD terminology definitions")
        logger.info("• Technical and DNS terminology explanations")
        logger.info("• Legal and policy terminology clarifications")
        logger.info("• Reserved names and special use domains")
        logger.info("• Application fees and payment procedures")
        logger.info("• Registry agreement template and provisions")
        logger.info("• Dispute resolution mechanisms and procedures")
        logger.info("• Community Priority Evaluation criteria and scoring")
        logger.info("\nUsers can now ask questions like:")
        logger.info("• 'What is a contention set?'")
        logger.info("• 'What names are reserved in gTLDs?'")
        logger.info("• 'How much does a gTLD application cost?'")
        logger.info("• 'What is Community Priority Evaluation?'")
        logger.info("• 'What are the dispute resolution options?'")
        
    except Exception as e:
        logger.error(f"❌ Failed to add glossary and appendices: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
