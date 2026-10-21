"""
Application-Focused RAG Agent for ICANN TLD Applications
Specialized version of the RAG chat agent for application generation
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import google.generativeai as genai
from crewai import Agent, Task, Crew
from crewai_service.rag_search_tool import rag_search_tool
from crewai_service.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class ApplicationRAGAgent:
    """Specialized RAG agent for ICANN application generation"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.setup_gemini()
        self.setup_agents()
    
    def get_applicant_data(self, applicant_id: str) -> Optional[Dict[str, Any]]:
        """Fetch applicant data directly from database"""
        try:
            response = self.supabase.table('applicants').select('*').eq('id', applicant_id).single().execute()
            if response.data:
                logger.info(f"Retrieved applicant data for {applicant_id}")
                return response.data
            return None
        except Exception as e:
            logger.error(f"Error fetching applicant data: {e}")
            return None
    
    def format_applicant_data_for_prompt(self, applicant: Dict[str, Any]) -> str:
        """Format applicant data as structured text for LLM prompt"""
        if not applicant:
            return "No applicant data available."
        
        # Format key personnel if present
        personnel_text = ""
        if applicant.get('key_personnel'):
            personnel_list = []
            for person in applicant['key_personnel']:
                personnel_list.append(f"  - {person.get('name', 'N/A')} ({person.get('title', 'N/A')}): {person.get('role', 'N/A')}")
            personnel_text = "\n".join(personnel_list)
        
        return f"""
EXAMPLE REGISTRY APPLICANT DATA:
=============================
Legal Name: {applicant.get('legal_name', 'N/A')}
Business Name: {applicant.get('business_name', 'N/A')}
Entity Type: {applicant.get('entity_type', 'N/A')}
Jurisdiction: {applicant.get('jurisdiction', 'N/A')}
Incorporation Date: {applicant.get('incorporation_date', 'N/A')}

ADDRESSES:
Business Address: {applicant.get('business_address', 'N/A')}
Mailing Address: {applicant.get('mailing_address', 'N/A')}

CONTACT INFORMATION:
Phone: {applicant.get('phone', 'N/A')}
Email: {applicant.get('email', 'N/A')}
Website: {applicant.get('website', 'N/A')}

FINANCIAL INFORMATION:
Funding Sources: {applicant.get('funding_sources', 'N/A')}
Annual Revenue: {applicant.get('annual_revenue', 'N/A')}
Total Assets: {applicant.get('total_assets', 'N/A')}

KEY PERSONNEL:
{personnel_text if personnel_text else 'N/A'}

REGISTRY EXPERIENCE:
Current TLDs: {', '.join(applicant.get('current_tlds', [])) if applicant.get('current_tlds') else 'N/A'}
Experience Description: {applicant.get('registry_experience_description', 'N/A')[:500] if applicant.get('registry_experience_description') else 'N/A'}...
"""

    def setup_gemini(self):
        """Initialize Gemini for responses"""
        try:
            api_key = os.getenv("GEMINI_API_KEY")

            if api_key:
                genai.configure(api_key=api_key)
                self.model_available = True
                logger.info("Gemini configured for Application RAG agent")
            else:
                self.model_available = False
                logger.error("Gemini API key not found for Application RAG agent")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini for Application RAG agent: {e}")
            self.model_available = False

    def setup_agents(self):
        """Create specialized agents for different data source types"""
        try:
            # Entity Data Agent - for Example Registry applicant information
            self.entity_agent = Agent(
                role="Entity Data Specialist",
                goal="""Extract and format Example Registry applicant data for ICANN application questions. 
                Always search for specific entity information and format it appropriately for ICANN requirements.""",
                backstory="""You are an expert at extracting entity information from Example Registry databases.
                You specialize in formatting applicant data, corporate structure, contact details, and legal entity information
                for ICANN application questions. Always use the RAG search tool with applicant_data content type.""",
                tools=[rag_search_tool],
                verbose=False,
                memory=False,
                max_iter=2,
                max_execution_time=15
            )

            # Evaluation Synthesis Agent - for risk assessment and evaluation data
            self.evaluation_agent = Agent(
                role="Evaluation Synthesis Specialist", 
                goal="""Synthesize TLD evaluation and risk assessment data into application responses.
                Use evaluation data to support technical capability, risk mitigation, and compliance responses.""",
                backstory="""You are an expert at interpreting TLD evaluations and risk assessments.
                You synthesize evaluation findings into compelling application responses that demonstrate
                awareness and mitigation of identified risks. Focus on tld_evaluation and risk_analysis content.""",
                tools=[rag_search_tool],
                verbose=False,
                memory=False,
                max_iter=2,
                max_execution_time=15
            )

            # Question Guidance Agent - for question-specific help and templates
            self.guidance_agent = Agent(
                role="Question Guidance Specialist",
                goal="""Provide question-specific guidance and templates for ICANN application questions.
                Help users understand what each question requires and provide templates or examples.""",
                backstory="""You are an expert on ICANN application requirements and question interpretation.
                You provide clear guidance on what each question is asking for, required data sources,
                and formatting requirements. Focus on question_guidance and answer_templates content.""",
                tools=[rag_search_tool],
                verbose=False,
                memory=False,
                max_iter=2,
                max_execution_time=15
            )

            logger.info("Application RAG agents created successfully")
        except Exception as e:
            logger.error(f"Failed to create Application RAG agents: {e}")
            self.entity_agent = None
            self.evaluation_agent = None
            self.guidance_agent = None

    async def generate_entity_answer(self, question_id: str, question_text: str, 
                                   applicant_id: Optional[str] = None,
                                   application_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate answer using Example Registry entity data - with direct database lookup"""
        try:
            if not self.entity_agent or not self.model_available:
                return {
                    "success": False,
                    "response": "Entity data agent unavailable",
                    "data_source": "none",
                    "confidence": 0.0
                }

            # DIRECT DATABASE LOOKUP - fetch applicant data directly instead of relying on RAG
            applicant_data = None
            applicant_context = ""
            
            if applicant_id:
                applicant_data = self.get_applicant_data(applicant_id)
                if applicant_data:
                    applicant_context = self.format_applicant_data_for_prompt(applicant_data)
                    logger.info(f"Using direct applicant data for question {question_id}")
                else:
                    logger.warning(f"No applicant data found for {applicant_id}")
            
            # Direct answer prompt - BE CONCISE
            prompt = f"""
Question {question_id}: {question_text}

{applicant_context if applicant_context else "No applicant data available."}

ANSWER DIRECTLY AND CONCISELY. Do NOT provide guidance, templates, or explanations.
Just give the specific answer using the Example Registry data above.

Examples of GOOD answers:
- "Example Registry Ltd."
- "123 Example Avenue, Wilmington, DE 19801, USA"  
- "Yes - Example Registry operates the .example TLD since 2023"
- "+34 686 084 480"

Examples of BAD answers (too verbose):
- "This question asks for..." 
- "The answer should include..."
- "Template: [fill in]..."

GIVE THE DIRECT ANSWER ONLY. If data is not available, say "N/A - [what's needed]"
            """

            task = Task(
                description=prompt,
                agent=self.entity_agent,
                expected_output="A SHORT, DIRECT answer (1-3 sentences max) using Example Registry data"
            )

            crew = Crew(
                agents=[self.entity_agent],
                tasks=[task],
                verbose=False,
                memory=False
            )

            result = await asyncio.wait_for(
                asyncio.to_thread(crew.kickoff),
                timeout=45.0
            )

            return {
                "success": True,
                "response": str(result),
                "data_source": "applicant_data",
                "confidence": 0.95 if applicant_data else 0.7,
                "question_id": question_id,
                "generated_at": datetime.utcnow().isoformat(),
                "applicant_data_found": applicant_data is not None
            }

        except asyncio.TimeoutError:
            logger.warning(f"Entity answer generation timed out for {question_id}")
            return {
                "success": False,
                "response": "Entity data search timed out. Please try again.",
                "data_source": "applicant_data",
                "confidence": 0.0
            }
        except Exception as e:
            logger.error(f"Entity answer generation error for {question_id}: {e}")
            return {
                "success": False,
                "response": f"Error generating entity answer: {str(e)}",
                "data_source": "applicant_data",
                "confidence": 0.0
            }

    async def generate_evaluation_answer(self, question_id: str, question_text: str,
                                       tld_string: Optional[str] = None,
                                       application_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate answer using TLD evaluation and risk assessment data"""
        try:
            if not self.evaluation_agent or not self.model_available:
                return {
                    "success": False,
                    "response": "Evaluation synthesis agent unavailable",
                    "data_source": "none",
                    "confidence": 0.0
                }

            prompt = f"""
Question {question_id}: {question_text}

TLD: {tld_string if tld_string else 'gif'}

Give a DIRECT, CONCISE answer (1-3 sentences max).
If this asks Yes/No, answer Yes or No first, then a brief explanation.
If this needs specific data we don't have, say "N/A - [what's needed]"

DO NOT write lengthy explanations, templates, or risk analyses.
Just answer the question directly.
            """

            task = Task(
                description=prompt,
                agent=self.evaluation_agent,
                expected_output="A SHORT, DIRECT answer (1-3 sentences max)"
            )

            crew = Crew(
                agents=[self.evaluation_agent],
                tasks=[task],
                verbose=False,
                memory=False
            )

            result = await asyncio.wait_for(
                asyncio.to_thread(crew.kickoff),
                timeout=45.0
            )

            return {
                "success": True,
                "response": str(result),
                "data_source": "evaluation_synthesis",
                "confidence": 0.85,
                "question_id": question_id,
                "generated_at": datetime.utcnow().isoformat()
            }

        except asyncio.TimeoutError:
            logger.warning(f"Evaluation answer generation timed out for {question_id}")
            return {
                "success": False,
                "response": "Evaluation synthesis timed out. Please try again.",
                "data_source": "evaluation_synthesis",
                "confidence": 0.0
            }
        except Exception as e:
            logger.error(f"Evaluation answer generation error for {question_id}: {e}")
            return {
                "success": False,
                "response": f"Error generating evaluation-based answer: {str(e)}",
                "data_source": "evaluation_synthesis",
                "confidence": 0.0
            }

    async def get_question_guidance(self, question_id: str, question_text: str) -> Dict[str, Any]:
        """Get guidance and templates for a specific question"""
        try:
            if not self.guidance_agent or not self.model_available:
                return {
                    "success": False,
                    "response": "Question guidance agent unavailable",
                    "data_source": "none",
                    "confidence": 0.0
                }

            prompt = f"""
Question {question_id}: {question_text}

Provide a SHORT, PLACEHOLDER answer for this ICANN application question.
Format: "[PLACEHOLDER: brief description of what's needed]"

Example outputs:
- "[PLACEHOLDER: Upload certificate of good standing from the applicant's company registry]"
- "[PLACEHOLDER: Enter stock symbol if publicly traded, otherwise N/A]"
- "N/A - Company is privately held"

Keep response under 50 words. No explanations or templates.
            """

            task = Task(
                description=prompt,
                agent=self.guidance_agent,
                expected_output="A SHORT placeholder or N/A response (under 50 words)"
            )

            crew = Crew(
                agents=[self.guidance_agent],
                tasks=[task],
                verbose=False,
                memory=False
            )

            result = await asyncio.wait_for(
                asyncio.to_thread(crew.kickoff),
                timeout=45.0  # Increased timeout for complex questions
            )

            return {
                "success": True,
                "response": str(result),
                "data_source": "question_guidance",
                "confidence": 0.9,
                "question_id": question_id,
                "generated_at": datetime.utcnow().isoformat()
            }

        except asyncio.TimeoutError:
            logger.warning(f"Question guidance timed out for {question_id}")
            return {
                "success": False,
                "response": "Question guidance search timed out. Please try again.",
                "data_source": "question_guidance", 
                "confidence": 0.0
            }
        except Exception as e:
            logger.error(f"Question guidance error for {question_id}: {e}")
            return {
                "success": False,
                "response": f"Error getting question guidance: {str(e)}",
                "data_source": "question_guidance",
                "confidence": 0.0
            }

    def classify_question_data_source(self, question_text: str, question_id: str) -> str:
        """Classify what type of data source is most appropriate for a question"""
        question_lower = question_text.lower()
        
        # String/TLD evaluation questions - MUST come first, use TLD evaluation data
        string_keywords = ['applied-for', 'gtld string', 'meaning/definition', 'definition of', 
                          'generic string', 'variant', 'replacement string', 'script of string',
                          'phonetic', 'idn', 'a-label', 'user communities', 'variant string']
        
        # Technical/evaluation-based questions  
        technical_keywords = ['registry services', 'technical capability', 'dns', 'security',
                            'infrastructure', 'operations', 'performance', 'safeguard']
        
        # Risk/evaluation synthesis questions
        risk_keywords = ['risk', 'trademark', 'collision', 'protection', 'dispute', 'compliance',
                        'rights protection', 'sunrise', 'claims', 'blocking']
        
        # Financial/business questions
        financial_keywords = ['financial', 'projections', 'revenue', 'business model', 'funding',
                             'capital', 'investment', 'economic']
        
        # Entity/applicant information questions
        entity_keywords = ['legal name', 'entity', 'applicant', 'company', 'address', 'contact', 
                          'incorporation', 'jurisdiction', 'website', 'lei', 'organization',
                          'phone', 'email', 'doing business', 'parent', 'stock', 'exchange',
                          'locality', 'region', 'postal', 'country', 'street', 'city', 'state',
                          'personnel', 'director', 'officer', 'employee', 'title', 'role',
                          'proof', 'good standing', 'establishment', 'registry operator', 'registrar',
                          'rsp', 'back-end', 'escrow', 'affiliate', 'experience']
        
        # Route string questions to evaluation synthesis (uses TLD evaluation data)
        if any(keyword in question_lower for keyword in string_keywords):
            return 'evaluation_synthesis'
        # Route technical/risk questions to evaluation synthesis
        elif any(keyword in question_lower for keyword in (technical_keywords + risk_keywords)):
            return 'evaluation_synthesis' 
        elif any(keyword in question_lower for keyword in financial_keywords):
            return 'evaluation_synthesis'
        else:
            return 'entity_data'  # Default to entity data for applicant info

# Global instance
application_rag_agent = ApplicationRAGAgent()