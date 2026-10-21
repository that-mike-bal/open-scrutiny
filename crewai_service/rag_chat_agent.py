"""
RAG-Powered Chat Agent for TLD Assistant
Single agent with semantic search capabilities
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import google.generativeai as genai
from crewai import Agent, Task, Crew
from crewai_service.rag_search_tool import rag_search_tool

logger = logging.getLogger(__name__)

class RAGChatAgent:
    """Simplified chat agent using semantic RAG search"""

    def __init__(self):
        self.setup_gemini()
        self.setup_agent()

    def setup_gemini(self):
        """Initialize Gemini for responses"""
        try:
            api_key = os.getenv("GEMINI_API_KEY")

            if api_key:
                genai.configure(api_key=api_key)
                self.model_available = True
                logger.info("Gemini configured for RAG chat agent")
            else:
                self.model_available = False
                logger.error("Gemini API key not found for RAG chat agent")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini for RAG agent: {e}")
            self.model_available = False

    def setup_agent(self):
        """Create the RAG-powered chat agent"""
        try:
            self.agent = Agent(
                role="TLD Evaluation Assistant",
                goal="""Provide expert guidance on TLD evaluations, applications, and ICANN processes. Always start with a helpful response, then use semantic search to enhance your answer with specific data.""",
                backstory="""You are an expert TLD consultant with access to comprehensive TLD evaluation data.

IMPORTANT INSTRUCTIONS:
1. ALWAYS provide an immediate helpful response first
2. Then use the RAG Vector Search tool to find specific supporting data
3. Keep responses focused and actionable
4. Don't spend too long searching - provide value quickly

Your expertise covers TLD risk analysis, ICANN processes, trademark considerations, and technical DNS operations.""",
                tools=[rag_search_tool],
                verbose=False,
                memory=False,
                max_iter=2,
                max_execution_time=20
            )
            logger.info("RAG chat agent created successfully")
        except Exception as e:
            logger.error(f"Failed to create RAG chat agent: {e}")
            self.agent = None

    async def process_query(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process user query using RAG-powered agent with immediate response"""
        try:
            if not self.agent or not self.model_available:
                return {
                    "success": False,
                    "response": "Chat agent unavailable - please check configuration",
                    "sources": [],
                    "metadata": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": "Agent or model not available"
                    }
                }

            # Provide immediate response based on query type
            immediate_response = self.get_immediate_response(message, context)
            
            # Enhanced prompt that encourages quick responses
            enhanced_prompt = self.build_enhanced_prompt(message, context)

            # Create task with timeout
            task = Task(
                description=enhanced_prompt,
                agent=self.agent,
                expected_output="A helpful, accurate response. Use the RAG search tool ONLY if you need specific data to enhance your answer."
            )

            # Create crew with minimal configuration
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False,
                memory=False
            )

            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(crew.kickoff), 
                    timeout=25.0
                )
                response_text = str(result)
            except asyncio.TimeoutError:
                logger.warning("Agent response timed out, using immediate response")
                response_text = immediate_response

            # Extract sources from response
            sources = self.extract_sources_from_response(response_text)

            return {
                "success": True,
                "response": response_text,
                "sources": sources,
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_type": "rag_powered",
                    "search_method": "semantic_vector",
                    "context_used": bool(context)
                }
            }

        except Exception as e:
            logger.error(f"RAG chat agent error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Fallback to immediate response on error
            fallback_response = self.get_immediate_response(message, context)
            
            return {
                "success": True,  # Still successful, just using fallback
                "response": fallback_response + "\n\n*Note: Enhanced search temporarily unavailable*",
                "sources": [],
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "fallback_used": True
                }
            }

    def get_immediate_response(self, message: str, context: Optional[Dict] = None) -> str:
        """Provide immediate helpful response based on query patterns"""
        message_lower = message.lower()
        
        # Context-aware responses
        if context and context.get("tld_string"):
            tld = context["tld_string"]
            if "risk" in message_lower or "evaluation" in message_lower:
                return f"I can help you understand the risk evaluation for .{tld}. Let me search for specific evaluation data and risk assessments..."
            elif "trademark" in message_lower:
                return f"For .{tld}, I'll check trademark conflicts and legal considerations. Searching trademark databases..."
            elif "application" in message_lower:
                return f"I can guide you through the application process for .{tld}. Let me find relevant application requirements..."
        
        # General topic responses
        if "guidebook" in message_lower or "icann" in message_lower:
            return "I can help you with ICANN Applicant Guidebook requirements and policies. Let me search for the most relevant sections..."
        elif "trademark" in message_lower:
            return "I'll help you understand trademark considerations for TLD applications. Searching for relevant trademark policies and precedents..."
        elif "risk" in message_lower or "evaluation" in message_lower:
            return "I can provide guidance on TLD risk evaluation methodologies and criteria. Let me find relevant evaluation examples..."
        elif "application" in message_lower:
            return "I'll help you with TLD application preparation and requirements. Searching for application guidance..."
        elif "dns" in message_lower or "technical" in message_lower:
            return "I can assist with technical DNS and registry operation requirements. Let me find the relevant technical specifications..."
        elif "safeguard" in message_lower or "protection" in message_lower:
            return "I'll help you understand safeguard requirements and consumer protection measures. Searching for safeguard policies..."
        else:
            return "I'm here to help with TLD evaluations, applications, and ICANN processes. Let me search for information relevant to your question..."

    def build_enhanced_prompt(self, message: str, context: Optional[Dict]) -> str:
        """Build context-aware prompt for the agent"""
        base_prompt = f"""
User Question: {message}

IMPORTANT: Provide a helpful response immediately. Use the RAG Vector Search tool ONLY if you need specific data to enhance your answer.

If you use the search tool:
- Search for the most relevant information
- Keep the search focused and specific
- Don't over-search - one good search is often enough

Response Requirements:
- Be helpful and actionable
- Reference specific data when available
- Keep responses focused and concise
- Provide next steps when appropriate
        """.strip()

        # Add context if available
        if context:
            context_info = []
            if context.get("tld_string"):
                context_info.append(f"Current TLD: .{context['tld_string']}")
                base_prompt += f"\n\nCONTEXT: User is currently viewing .{context['tld_string']} evaluation page."

            if context.get("page_type"):
                context_info.append(f"Page type: {context['page_type']}")

            if context_info:
                base_prompt += f"\nContext: {' | '.join(context_info)}"
                base_prompt += "\nIf the user references 'this string', 'this evaluation', or similar, they're referring to the current context."

        return base_prompt

    def extract_sources_from_response(self, response_text: str) -> List[Dict]:
        """Extract source information from agent response"""
        sources = []

        # Look for patterns that indicate the agent used the search tool
        if "🔍 Semantic Search Results" in response_text:
            # Parse search results to extract sources
            lines = response_text.split('\n')
            current_source = None

            for line in lines:
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
                    # New source found
                    if '📊' in line or '⚠️' in line or '📋' in line or '📚' in line:
                        # Extract title and similarity
                        parts = line.split('(Similarity:')
                        if len(parts) == 2:
                            title = parts[0].split('. ', 1)[1].strip()
                            similarity = parts[1].strip().rstrip('%)')

                            current_source = {
                                "id": f"rag_result_{len(sources)}",
                                "type": "rag_search",
                                "title": title,
                                "similarity_score": float(similarity) / 100 if similarity.replace('.', '').isdigit() else 0.8,
                                "excerpt": ""
                            }
                            sources.append(current_source)

                elif current_source and line.strip() and not line.startswith('   Source:'):
                    # Add content to current source excerpt
                    if len(current_source["excerpt"]) < 200:
                        current_source["excerpt"] += line.strip() + " "

        # Fallback: create generic source if agent used the tool
        if not sources and "search" in response_text.lower():
            sources.append({
                "id": "rag_search_generic",
                "type": "semantic_search",
                "title": "TLD Evaluation Database",
                "similarity_score": 0.8,
                "excerpt": "Semantic search across TLD evaluations, ICANN policies, and application guidance"
            })

        return sources

# Global instance
rag_chat_agent = RAGChatAgent()