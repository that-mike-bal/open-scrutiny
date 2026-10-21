#!/usr/bin/env python3
"""
Populate Guidebook Embeddings into rag_content Table

Extracts content from the ICANN New gTLD Program Applicant Guidebook PDF,
generates embeddings, and stores them in the rag_content table for
semantic search via the similarity_search() RPC.

Usage:
    python db/populate_guidebook_embeddings.py \
        --pdf-path /path/to/guidebook.pdf \
        --target-table rag_content \
        --clear-existing

    python db/populate_guidebook_embeddings.py \
        --pdf-path /path/to/guidebook.pdf \
        --target-table guidebook_embeddings

    python db/populate_guidebook_embeddings.py --test-mode
"""

import os
import sys
import re
import argparse
import logging
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openai
import pdfplumber
from db.supabase_client import get_supabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Target ~800 tokens per chunk (~3200 chars), with 200-char overlap
CHUNK_MAX_CHARS = 3200
CHUNK_OVERLAP_CHARS = 200
EMBEDDING_MODEL = "text-embedding-3-small"


class GuidebookEmbeddingsPopulator:
    def __init__(self, target_table: str = "rag_content"):
        self.supabase = get_supabase()
        self.openai_client = self._setup_openai()
        self.target_table = target_table

    def _setup_openai(self):
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OpenAI API key not found — embeddings will not be generated")
                return None
            return openai.OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to setup OpenAI client: {e}")
            return None

    # ── PDF extraction ───────────────────────────────────────────────

    def extract_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract structured sections from the guidebook PDF."""
        logger.info(f"Extracting content from PDF: {pdf_path}")
        sections: List[Dict[str, Any]] = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                current_section = None
                content_buffer: List[str] = []

                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue

                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue

                        if self._is_section_header(line):
                            # Flush previous section
                            if current_section and content_buffer:
                                current_section['content_text'] = '\n'.join(content_buffer)
                                sections.append(current_section)

                            section_number, title = self._parse_section_header(line)
                            current_section = {
                                'section_number': section_number,
                                'section_title': title,
                                'page_number': page_num,
                            }
                            content_buffer = []
                        else:
                            content_buffer.append(line)

                # Flush last section
                if current_section and content_buffer:
                    current_section['content_text'] = '\n'.join(content_buffer)
                    sections.append(current_section)

        except Exception as e:
            logger.error(f"Failed to extract PDF content: {e}")
            return []

        logger.info(f"Extracted {len(sections)} sections from PDF")
        return sections

    _HEADER_RE = re.compile(
        r'^(\d+\.\d+(?:\.\d+)*)\s+(.+)$'       # 1.1 Title / 1.1.1 Title
        r'|^(Section\s+\d+)\s+(.+)$'            # Section 1 Title
        r'|^(Appendix\s+[A-Z])\s+(.+)$',        # Appendix A Title
        re.IGNORECASE,
    )

    def _is_section_header(self, line: str) -> bool:
        if len(line) > 120:
            return False
        return bool(self._HEADER_RE.match(line))

    def _parse_section_header(self, line: str) -> tuple:
        m = self._HEADER_RE.match(line)
        if m:
            # Groups come in pairs (number, title) across alternation branches
            groups = m.groups()
            for i in range(0, len(groups), 2):
                if groups[i] is not None:
                    return groups[i], groups[i + 1]
        return "unknown", line

    # ── Chunking ─────────────────────────────────────────────────────

    def chunk_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split large sections into overlapping chunks for better embedding quality."""
        chunks: List[Dict[str, Any]] = []

        for section in sections:
            text = section['content_text']

            # Strip common PDF noise (page headers/footers)
            text = re.sub(
                r'ICANN \| New gTLD Program:.*?Table of Contents\n?',
                '', text, flags=re.DOTALL,
            )
            text = text.strip()

            if not text:
                continue

            if len(text) <= CHUNK_MAX_CHARS:
                chunks.append({
                    **section,
                    'content_text': text,
                    'chunk_index': 0,
                    'total_chunks': 1,
                })
                continue

            # PDF text uses \n between lines. Try \n\n first; fall back to \n.
            paragraphs = re.split(r'\n\s*\n', text)
            if len(paragraphs) <= 1:
                # No double-newline breaks — split on single newlines instead
                paragraphs = text.split('\n')

            current_chunk: List[str] = []
            current_len = 0
            chunk_index = 0
            section_chunks: List[Dict[str, Any]] = []

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                if current_len + len(para) > CHUNK_MAX_CHARS and current_chunk:
                    # Flush current chunk
                    chunk_text = '\n'.join(current_chunk)
                    section_chunks.append({
                        **section,
                        'content_text': chunk_text,
                        'chunk_index': chunk_index,
                    })
                    chunk_index += 1

                    # Keep overlap: take last lines up to CHUNK_OVERLAP_CHARS
                    overlap_parts: List[str] = []
                    overlap_len = 0
                    for p in reversed(current_chunk):
                        if overlap_len + len(p) > CHUNK_OVERLAP_CHARS:
                            break
                        overlap_parts.insert(0, p)
                        overlap_len += len(p)

                    current_chunk = overlap_parts
                    current_len = overlap_len

                current_chunk.append(para)
                current_len += len(para)

            # Flush final chunk
            if current_chunk:
                chunk_text = '\n'.join(current_chunk)
                section_chunks.append({
                    **section,
                    'content_text': chunk_text,
                    'chunk_index': chunk_index,
                })

            total = len(section_chunks)
            for c in section_chunks:
                c['total_chunks'] = total

            chunks.extend(section_chunks)

        logger.info(f"Chunked {len(sections)} sections into {len(chunks)} chunks")
        return chunks

    # ── Embeddings ───────────────────────────────────────────────────

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        if not self.openai_client:
            return None
        try:
            # text-embedding-3-small supports up to 8191 tokens; truncate chars conservatively
            if len(text) > 8000:
                text = text[:8000] + "..."
            response = self.openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    # ── Content classification ───────────────────────────────────────

    def classify_content(self, section_title: str, content: str) -> Dict[str, Any]:
        title_lower = section_title.lower()

        topic_tags: List[str] = []
        tag_rules = [
            (['similarity', 'string', 'contention'], ['string-similarity', 'evaluation']),
            (['dns', 'technical', 'stability'], ['dns-stability', 'technical-review']),
            (['legal', 'trademark', 'rights'], ['legal-review', 'trademark']),
            (['financial', 'fee', 'payment'], ['financial', 'fees']),
            (['registry', 'operation'], ['registry-operations']),
            (['policy', 'icann', 'governance'], ['policy', 'governance']),
            (['geographic', 'country', 'territory'], ['geographic-names']),
            (['community', 'objection'], ['community', 'objection']),
            (['gac', 'government', 'advisory'], ['gac', 'government']),
            (['safeguard', 'protection', 'abuse'], ['safeguard', 'consumer-protection']),
        ]
        for keywords, tags in tag_rules:
            if any(kw in title_lower for kw in keywords):
                topic_tags.extend(tags)

        # Deduplicate
        topic_tags = list(dict.fromkeys(topic_tags))

        return {'topic_tags': topic_tags}

    # ── Database operations ──────────────────────────────────────────

    def clear_existing(self):
        """Delete all guidebook_section rows from the target table."""
        logger.info(f"Clearing existing guidebook_section rows from {self.target_table}")
        try:
            resp = (self.supabase.table(self.target_table)
                    .delete()
                    .eq('content_type', 'guidebook_section')
                    .execute())
            deleted = len(resp.data) if resp.data else 0
            logger.info(f"Deleted {deleted} existing guidebook_section rows")
        except Exception as e:
            logger.error(f"Failed to clear existing rows: {e}")

    def save_to_database(self, chunks: List[Dict[str, Any]], document_version: str = "2026") -> int:
        """Save chunks with embeddings to the target table."""
        logger.info(f"Saving {len(chunks)} chunks to {self.target_table}")
        saved_count = 0

        for i, chunk in enumerate(chunks):
            try:
                embedding = self.generate_embedding(chunk['content_text'])
                if not embedding:
                    logger.warning(f"Skipping chunk {i} ({chunk.get('section_number')}) — no embedding")
                    continue

                classification = self.classify_content(
                    chunk.get('section_title', ''),
                    chunk['content_text'],
                )

                if self.target_table == 'rag_content':
                    # source_id must be unique per (source_id, content_type).
                    # Append page + chunk index to handle duplicate section numbers.
                    sec_num = chunk.get('section_number', 'unknown')
                    page = chunk.get('page_number', 0)
                    cidx = chunk.get('chunk_index', 0)
                    source_id = f"{sec_num}_p{page}_c{cidx}"

                    record = {
                        'title': f"{sec_num} — {chunk.get('section_title', 'Untitled')}",
                        'content': chunk['content_text'],
                        'content_type': 'guidebook_section',
                        'source_id': source_id,
                        'metadata': {
                            'document_version': document_version,
                            'page_number': chunk.get('page_number'),
                            'chunk_index': chunk.get('chunk_index', 0),
                            'total_chunks': chunk.get('total_chunks', 1),
                            'topic_tags': classification['topic_tags'],
                            'embedding_model': EMBEDDING_MODEL,
                        },
                        'embedding': embedding,
                    }
                else:
                    # Legacy guidebook_embeddings table format
                    record = {
                        'section_number': chunk.get('section_number'),
                        'section_title': chunk.get('section_title'),
                        'page_number': chunk.get('page_number'),
                        'content_text': chunk['content_text'],
                        'content_type': 'section',
                        'content_length': len(chunk['content_text']),
                        'embedding': embedding,
                        'embedding_model': EMBEDDING_MODEL,
                        'topic_tags': classification['topic_tags'],
                        'application_sections': [],
                        'context_summary': f"ICANN guidebook: {chunk.get('section_title', '')}",
                        'content_quality_score': min(1.0, len(chunk['content_text']) / 1000.0),
                        'document_version': document_version,
                    }

                response = self.supabase.table(self.target_table).insert(record).execute()
                if response.data:
                    saved_count += 1
                    if saved_count % 20 == 0:
                        logger.info(f"Progress: {saved_count}/{len(chunks)} chunks saved")
                else:
                    logger.error(f"Failed to save chunk {i} ({chunk.get('section_number')})")

            except Exception as e:
                logger.error(f"Error saving chunk {i} ({chunk.get('section_number')}): {e}")
                continue

        logger.info(f"Successfully saved {saved_count}/{len(chunks)} chunks to {self.target_table}")
        return saved_count

    # ── Main pipeline ────────────────────────────────────────────────

    def process_pdf(self, pdf_path: str, clear_existing: bool = False,
                    document_version: str = "2026") -> int:
        logger.info(f"Starting guidebook embeddings population → {self.target_table}")

        if clear_existing:
            self.clear_existing()

        sections = self.extract_from_pdf(pdf_path)
        if not sections:
            logger.error("No sections extracted from PDF")
            return 0

        chunks = self.chunk_sections(sections)
        return self.save_to_database(chunks, document_version=document_version)


def main():
    parser = argparse.ArgumentParser(description='Populate guidebook embeddings')
    parser.add_argument('--pdf-path', type=str, help='Path to ICANN guidebook PDF')
    parser.add_argument('--target-table', type=str, default='rag_content',
                        choices=['rag_content', 'guidebook_embeddings'],
                        help='Target table (default: rag_content)')
    parser.add_argument('--clear-existing', action='store_true',
                        help='Delete existing guidebook_section rows before populating')
    parser.add_argument('--document-version', type=str, default='2026',
                        help='Guidebook version string stored in metadata (default: 2026)')
    parser.add_argument('--test-mode', action='store_true',
                        help='Run with sample data only')

    args = parser.parse_args()

    populator = GuidebookEmbeddingsPopulator(target_table=args.target_table)

    if args.test_mode:
        logger.info("Running in test mode with sample data")
        sample_chunks = [
            {
                'section_number': '1.1.2.1',
                'section_title': 'String Similarity Review Process',
                'page_number': 15,
                'content_text': 'The String Similarity Review will be conducted by a String Similarity Panel consisting of experts in linguistics, intellectual property, and domain name policy.',
                'chunk_index': 0,
                'total_chunks': 1,
            },
            {
                'section_number': '2.2.1',
                'section_title': 'DNS Stability Requirements',
                'page_number': 45,
                'content_text': 'Registry operators must demonstrate technical capability to operate a gTLD registry in a stable and secure manner.',
                'chunk_index': 0,
                'total_chunks': 1,
            },
        ]
        if args.clear_existing:
            populator.clear_existing()
        saved = populator.save_to_database(sample_chunks, document_version=args.document_version)
        logger.info(f"Test mode complete. Saved {saved} chunks.")
        return 0 if saved > 0 else 1

    if not args.pdf_path:
        logger.error("Must provide --pdf-path (or use --test-mode)")
        return 1

    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF file not found: {args.pdf_path}")
        return 1

    saved_count = populator.process_pdf(
        args.pdf_path,
        clear_existing=args.clear_existing,
        document_version=args.document_version,
    )

    logger.info(f"Processing complete. Saved {saved_count} chunks with embeddings.")
    return 0 if saved_count > 0 else 1


if __name__ == "__main__":
    exit(main())
