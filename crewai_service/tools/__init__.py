# TLD Evaluation Tools for CrewAI Service
# Comprehensive toolkit for TLD string evaluation and compliance checking

# Core Analysis Tools
from .string_analyzer import StringAnalyzerTool
from .similarity_analyzer import SimilarityAnalyzerTool
from .magnitude_collision import MagnitudeCollisionTool

# Compliance & Checking Tools
# Binary compliance checking is now handled client-side in /client/src/lib/binaryCompliance.ts

# Risk Assessment Tools
from .gac_precedent import GACPrecedentTool
from .competitive_research import CompetitiveResearchTool
from .deep_research_legal import DeepResearchLegalTool

# Document Search Tools (pgvector index of the guidebook; see docs/KNOWLEDGE_BASE.md)
from .guidebook_rag_search import GuidebookRAGSearchTool

# Web Search Tool (uses Brave Search API with logging)
from .brave_web_search import BraveWebSearchTool

# Tool Registry for Dynamic Loading
TOOL_REGISTRY = {
    'string_analyzer': StringAnalyzerTool,
    'similarity_analyzer': SimilarityAnalyzerTool,
    'magnitude_collision': MagnitudeCollisionTool,
    'gac_precedent_analyzer': GACPrecedentTool,
    'competitive_research': CompetitiveResearchTool,
    'competitive_research_agent': CompetitiveResearchTool,  # Alias
    'deep_research_legal': DeepResearchLegalTool,
    'deep_research_legal_analyzer': DeepResearchLegalTool,  # Alias
    'guidebook_search': GuidebookRAGSearchTool,
    'brave_web_search': BraveWebSearchTool,
}

# Export all tools
__all__ = [
    'StringAnalyzerTool',
    'SimilarityAnalyzerTool',
    'MagnitudeCollisionTool',
    'GACPrecedentTool',
    'CompetitiveResearchTool',
    'DeepResearchLegalTool',
    'GuidebookRAGSearchTool',
    'BraveWebSearchTool',
    'TOOL_REGISTRY'
]
