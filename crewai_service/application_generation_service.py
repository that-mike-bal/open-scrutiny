"""
Application Generation Service — Legacy Compatibility Wrapper
==============================================================
This module now delegates to answer_generation_service.py.
Kept for backwards compatibility with any code that imports
`application_generation_service`.

The original implementation is archived at:
  archive/legacy_rag_generation/application_generation_service.py
"""

import logging
from crewai_service.answer_generation_service import answer_generation_service

logger = logging.getLogger(__name__)

# Re-export the new service under the old name for backwards compatibility
application_generation_service = answer_generation_service
