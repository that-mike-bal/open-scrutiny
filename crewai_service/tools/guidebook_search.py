"""
ICANN New gTLD Program Applicant Guidebook Search Tool

Searches the official ICANN New gTLD Program Applicant Guidebook for relevant information.
Provides authoritative ICANN guidance for TLD evaluation criteria and requirements.
"""

from crewai.tools import BaseTool
import os
import json
import logging
from typing import Dict, List, Any, Optional
import re
from pathlib import Path

# PDF parsing imports
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    try:
        import pdfplumber
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False

logger = logging.getLogger(__name__)

class GuidebookSearchTool(BaseTool):
    name: str = "ICANN New gTLD Program Applicant Guidebook Search"
    description: str = "Searches the official ICANN New gTLD Program Applicant Guidebook for authoritative guidance on TLD evaluation criteria and requirements"
    
    def __init__(self):
        super().__init__()
        # Use object.__setattr__ to bypass Pydantic validation for internal attributes
        object.__setattr__(self, 'guidebook_path', self._resolve_guidebook_path())
        object.__setattr__(self, 'cached_content', None)
        
    def _run(self, query: str, section: str = "") -> str:
        """
        Search the ICANN New gTLD Program Applicant Guidebook for relevant information.
        
        Args:
            query: The search query or topic to find in the guidebook
            section: Optional specific section to search (e.g., "String Evaluation", "GAC Advice")
            
        Returns:
            JSON string with search results from the guidebook
        """
        query = query.strip()
        
        if not query:
            return json.dumps({
                "error": "No search query provided",
                "recommendation": "Provide a specific query to search the guidebook"
            }, indent=2)
        
        try:
            # Load PDF content
            pdf_content = self._load_pdf_content()
            
            if not pdf_content:
                return json.dumps({
                    "error": "Could not load guidebook content",
                    "fallback_advice": "Refer to ICANN New gTLD Program Applicant Guidebook manually"
                }, indent=2)
            
            # Search for relevant content
            search_results = self._search_content(query, pdf_content, section)
            
            result = {
                "query": query,
                "section_filter": section if section else "all_sections",
                "results_found": len(search_results),
                "guidebook_sections": search_results,
                "source": "ICANN New gTLD Program Applicant Guidebook",
                "authoritative": True,
                "search_summary": self._generate_search_summary(query, search_results)
            }
            
            logger.info(f"Guidebook search for '{query}': {len(search_results)} results found")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Guidebook search failed for '{query}': {e}")
            return json.dumps({
                "query": query,
                "error": str(e),
                "fallback_advice": "Manual review of ICANN New gTLD Program Applicant Guidebook required"
            }, indent=2)
    
    def _load_pdf_content(self) -> Optional[Dict[str, Any]]:
        """Load and parse PDF content."""
        if self.cached_content:
            return self.cached_content
        
        if not PDF_AVAILABLE:
            logger.error("PDF parsing libraries not available")
            return None
        
        if not os.path.exists(self.guidebook_path):
            logger.error(f"Guidebook PDF not found at {self.guidebook_path}")
            return None
        
        try:
            # Try PyPDF2 first
            try:
                import PyPDF2
                return self._parse_with_pypdf2()
            except ImportError:
                pass
            
            # Fallback to pdfplumber
            try:
                import pdfplumber
                return self._parse_with_pdfplumber()
            except ImportError:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            return None

    def _resolve_guidebook_path(self) -> str:
        """Resolve the path to the Guidebook PDF using env var and project-relative fallbacks."""
        # 1) Environment variable override
        env_path = os.getenv("NEW_GTLD_GUIDEBOOK_PATH")
        if env_path and os.path.exists(env_path):
            return env_path

        # 2) Project root detection
        try:
            project_root = Path(__file__).resolve().parents[2]
        except Exception:
            project_root = Path.cwd()

        candidate_names = [
            "New gTLD Program Applicant Guidebook.pdf",
            "new-gTLD-Applicant-Guidebook.pdf",
        ]
        candidate_dirs = [
            project_root,
            project_root / "docs",
        ]

        for cand_dir in candidate_dirs:
            for cand_name in candidate_names:
                cand_path = cand_dir / cand_name
                if cand_path.exists():
                    return str(cand_path)

        # 3) Fallback to original absolute (may not exist, but keeps previous behavior/logging)
        return "New gTLD Program Applicant Guidebook.pdf"
    
    def _parse_with_pypdf2(self) -> Dict[str, Any]:
        """Parse PDF using PyPDF2."""
        import PyPDF2
        
        content = {
            "pages": [],
            "text": "",
            "sections": {}
        }
        
        with open(self.guidebook_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                content["pages"].append({
                    "page_number": page_num + 1,
                    "text": page_text
                })
                content["text"] += page_text + "\n"
        
        # Extract sections
        content["sections"] = self._extract_sections(content["text"])
        self.cached_content = content
        return content
    
    def _parse_with_pdfplumber(self) -> Dict[str, Any]:
        """Parse PDF using pdfplumber."""
        import pdfplumber
        
        content = {
            "pages": [],
            "text": "",
            "sections": {}
        }
        
        with pdfplumber.open(self.guidebook_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                content["pages"].append({
                    "page_number": page_num + 1,
                    "text": page_text
                })
                content["text"] += page_text + "\n"
        
        # Extract sections
        content["sections"] = self._extract_sections(content["text"])
        self.cached_content = content
        return content
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract major sections from the guidebook."""
        sections = {}
        
        # Common section headers in ICANN guidebook
        section_patterns = [
            r'1\.\s*Introduction',
            r'2\.\s*String\s+Evaluation',
            r'3\.\s*Applicant\s+Evaluation',
            r'4\.\s*String\s+Contention',
            r'5\.\s*Transition\s+to\s+Delegation',
            r'6\.\s*Dispute\s+Resolution',
            r'Module\s+1',
            r'Module\s+2',
            r'Module\s+3',
            r'Module\s+4',
            r'Module\s+5',
            r'Module\s+6',
            r'String\s+Evaluation',
            r'DNS\s+Stability',
            r'Geographic\s+Names',
            r'String\s+Similarity',
            r'String\s+Confusion',
            r'Community\s+Evaluation',
            r'GAC\s+Advice',
            r'Government\s+Advisory\s+Committee',
            r'Trademark\s+Clearinghouse',
            r'Rights\s+Protection',
            r'Objection\s+Procedures',
            r'String\s+Contention\s+Resolution'
        ]
        
        # Split text into potential sections
        for i, pattern in enumerate(section_patterns):
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for match in matches:
                section_start = match.start()
                # Find the end of this section (start of next section or end of document)
                section_end = len(text)
                
                # Look for the next section header
                for next_pattern in section_patterns[i+1:]:
                    next_matches = list(re.finditer(next_pattern, text[section_start + 100:], re.IGNORECASE))
                    if next_matches:
                        section_end = section_start + 100 + next_matches[0].start()
                        break
                
                section_title = match.group().strip()
                section_content = text[section_start:section_end].strip()
                
                # Only include substantial sections
                if len(section_content) > 200:
                    sections[section_title] = section_content
        
        return sections
    
    def _search_content(self, query: str, content: Dict[str, Any], section_filter: str = "") -> List[Dict[str, Any]]:
        """Search through the PDF content for relevant information."""
        results = []
        query_lower = query.lower()
        
        # Search through sections first
        for section_title, section_content in content["sections"].items():
            if section_filter and section_filter.lower() not in section_title.lower():
                continue
            
            # Check if query matches section content
            if query_lower in section_content.lower():
                # Find relevant paragraphs
                paragraphs = self._find_relevant_paragraphs(query, section_content)
                
                if paragraphs:
                    results.append({
                        "section": section_title,
                        "relevance": "high",
                        "content_type": "section_match",
                        "relevant_paragraphs": paragraphs,
                        "context": "ICANN official guidance"
                    })
        
        # If no section matches, search through all pages
        if not results:
            for page in content["pages"]:
                if query_lower in page["text"].lower():
                    paragraphs = self._find_relevant_paragraphs(query, page["text"])
                    
                    if paragraphs:
                        results.append({
                            "section": f"Page {page['page_number']}",
                            "relevance": "medium",
                            "content_type": "page_match",
                            "relevant_paragraphs": paragraphs,
                            "context": "ICANN official guidance"
                        })
        
        # Sort results by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:5]  # Return top 5 most relevant results
    
    def _find_relevant_paragraphs(self, query: str, text: str) -> List[str]:
        """Find paragraphs relevant to the query."""
        query_lower = query.lower()
        paragraphs = []
        
        # Split text into sentences/paragraphs
        sentences = re.split(r'[.!?]\s+', text)
        
        # Find sentences containing the query
        relevant_sentences = []
        for sentence in sentences:
            if query_lower in sentence.lower() and len(sentence.strip()) > 20:
                relevant_sentences.append(sentence.strip())
        
        # Group related sentences into paragraphs
        if relevant_sentences:
            # Take surrounding context for each relevant sentence
            for sentence in relevant_sentences[:3]:  # Top 3 most relevant
                # Find the sentence in the original text
                sentence_pos = text.lower().find(sentence.lower())
                if sentence_pos != -1:
                    # Get context around the sentence
                    context_start = max(0, sentence_pos - 200)
                    context_end = min(len(text), sentence_pos + len(sentence) + 200)
                    context = text[context_start:context_end].strip()
                    
                    if context not in paragraphs:
                        paragraphs.append(context)
        
        return paragraphs
    
    def _generate_search_summary(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Generate a summary of search results."""
        if not results:
            return f"No specific guidance found for '{query}' in the ICANN New gTLD Program Applicant Guidebook"
        
        sections_found = [result["section"] for result in results]
        
        summary = f"Found {len(results)} relevant sections in the ICANN guidebook for '{query}': "
        summary += ", ".join(sections_found)
        
        return summary 