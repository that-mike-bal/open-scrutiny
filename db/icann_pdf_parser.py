#!/usr/bin/env python3
"""
ICANN Guidebook PDF Parser

Advanced PDF parsing system using open source tools to extract structured content
from the ICANN Applicant Guidebook PDF, preserving table of contents structure,
sections, and hierarchical organization.
"""

import sys
import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DocumentSection:
    """Represents a structured section from the PDF"""
    section_number: str
    title: str
    content: str
    page_number: int
    level: int  # Hierarchy level (1 = main section, 2 = subsection, etc.)
    parent_section: Optional[str] = None
    subsections: List[str] = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []

@dataclass
class TableOfContentsEntry:
    """Represents a TOC entry"""
    section_number: str
    title: str
    page_number: int
    level: int
    parent: Optional[str] = None

class ICANNPDFParser:
    """Advanced PDF parser for ICANN guidebook documents"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.sections: List[DocumentSection] = []
        self.toc_entries: List[TableOfContentsEntry] = []
        self.doc = None
        
        # Install required packages if not available
        self._ensure_dependencies()
    
    def _ensure_dependencies(self):
        """Ensure required PDF parsing libraries are available"""
        try:
            import fitz  # PyMuPDF
            logger.info("✅ PyMuPDF available")
        except ImportError:
            logger.error("❌ PyMuPDF not available. Install with: pip install PyMuPDF")
            sys.exit(1)
        
        try:
            import pdfplumber
            logger.info("✅ pdfplumber available")
        except ImportError:
            logger.warning("⚠️ pdfplumber not available. Install with: pip install pdfplumber")
        
        # Check for advanced parsing tools
        try:
            import camelot
            logger.info("✅ Camelot available for table extraction")
        except ImportError:
            logger.info("ℹ️ Camelot not available (optional). Install with: pip install camelot-py[cv]")
    
    def load_pdf(self) -> bool:
        """Load the PDF document"""
        try:
            import fitz
            self.doc = fitz.open(self.pdf_path)
            logger.info(f"✅ Loaded PDF: {self.pdf_path}")
            logger.info(f"📄 Document has {len(self.doc)} pages")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load PDF: {e}")
            return False
    
    def extract_table_of_contents(self) -> List[TableOfContentsEntry]:
        """Extract table of contents from the PDF"""
        if not self.doc:
            logger.error("❌ Document not loaded")
            return []
        
        logger.info("📋 Extracting table of contents...")
        toc_entries = []
        
        try:
            # Get PDF outline/bookmarks (if available)
            outline = self.doc.get_toc()
            
            if outline:
                logger.info(f"✅ Found {len(outline)} TOC entries from PDF bookmarks")
                for level, title, page in outline:
                    # Extract section number from title if present
                    section_match = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)', title.strip())
                    if section_match:
                        section_number = section_match.group(1)
                        clean_title = section_match.group(2)
                    else:
                        section_number = ""
                        clean_title = title.strip()
                    
                    toc_entry = TableOfContentsEntry(
                        section_number=section_number,
                        title=clean_title,
                        page_number=page,
                        level=level
                    )
                    toc_entries.append(toc_entry)
            else:
                # Fallback: Parse TOC from text content
                logger.info("📋 No PDF bookmarks found, parsing TOC from text...")
                toc_entries = self._parse_toc_from_text()
            
            self.toc_entries = toc_entries
            return toc_entries
            
        except Exception as e:
            logger.error(f"❌ Failed to extract TOC: {e}")
            return []
    
    def _parse_toc_from_text(self) -> List[TableOfContentsEntry]:
        """Parse TOC from text content when bookmarks aren't available"""
        toc_entries = []
        
        # Look for TOC pages (usually early in document)
        for page_num in range(min(20, len(self.doc))):  # Check first 20 pages
            page = self.doc[page_num]
            text = page.get_text()
            
            # Look for TOC patterns
            toc_patterns = [
                r'^(\d+(?:\.\d+)*)\s+(.+?)\s+(\d+)$',  # "1.2.3 Section Title 45"
                r'^(.+?)\s+\.{3,}\s*(\d+)$',          # "Section Title .... 45"
                r'^(\d+(?:\.\d+)*)\s+(.+?)\.{3,}(\d+)$'  # "1.2 Title....45"
            ]
            
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                for pattern in toc_patterns:
                    match = re.match(pattern, line)
                    if match:
                        if len(match.groups()) == 3:
                            section_number, title, page = match.groups()
                        else:
                            section_number = ""
                            title, page = match.groups()
                        
                        try:
                            page_number = int(page)
                            level = len(section_number.split('.')) if section_number else 1
                            
                            toc_entry = TableOfContentsEntry(
                                section_number=section_number,
                                title=title.strip(),
                                page_number=page_number,
                                level=level
                            )
                            toc_entries.append(toc_entry)
                        except ValueError:
                            continue
        
        logger.info(f"✅ Parsed {len(toc_entries)} TOC entries from text")
        return toc_entries
    
    def extract_sections(self) -> List[DocumentSection]:
        """Extract all sections based on TOC structure"""
        if not self.toc_entries:
            logger.error("❌ No TOC entries available")
            return []
        
        logger.info("📖 Extracting sections based on TOC structure...")
        sections = []
        
        for i, toc_entry in enumerate(self.toc_entries):
            try:
                # Determine page range for this section
                start_page = toc_entry.page_number - 1  # 0-indexed
                
                # Find end page (start of next section or end of document)
                if i + 1 < len(self.toc_entries):
                    end_page = self.toc_entries[i + 1].page_number - 1
                else:
                    end_page = len(self.doc)
                
                # Extract content from page range
                content = self._extract_content_from_pages(start_page, end_page)
                
                # Create section
                section = DocumentSection(
                    section_number=toc_entry.section_number,
                    title=toc_entry.title,
                    content=content,
                    page_number=toc_entry.page_number,
                    level=toc_entry.level
                )
                
                sections.append(section)
                logger.info(f"✅ Extracted: {section.section_number} {section.title}")
                
            except Exception as e:
                logger.error(f"❌ Failed to extract section {toc_entry.section_number}: {e}")
                continue
        
        self.sections = sections
        return sections
    
    def _extract_content_from_pages(self, start_page: int, end_page: int) -> str:
        """Extract clean content from a range of pages"""
        content_parts = []
        
        for page_num in range(start_page, min(end_page, len(self.doc))):
            try:
                page = self.doc[page_num]
                
                # Extract text
                text = page.get_text()
                
                # Clean up text
                cleaned_text = self._clean_text(text)
                
                if cleaned_text.strip():
                    content_parts.append(cleaned_text)
                
                # Extract tables if available
                tables = self._extract_tables_from_page(page)
                if tables:
                    content_parts.extend(tables)
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to extract from page {page_num + 1}: {e}")
                continue
        
        return '\n\n'.join(content_parts)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove page headers/footers (common patterns)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip common header/footer patterns
            if (re.match(r'^\d+$', line) or  # Page numbers
                re.match(r'^Page \d+', line, re.IGNORECASE) or
                'ICANN' in line and len(line) < 50 or
                'Applicant Guidebook' in line and len(line) < 100):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_tables_from_page(self, page) -> List[str]:
        """Extract tables from a page"""
        tables = []
        
        try:
            # Try to extract tables using PyMuPDF
            tabs = page.find_tables()
            
            for tab in tabs:
                table_data = tab.extract()
                if table_data:
                    # Convert table to text format
                    table_text = self._format_table_as_text(table_data)
                    tables.append(f"\n[TABLE]\n{table_text}\n[/TABLE]\n")
                    
        except Exception as e:
            logger.debug(f"Table extraction failed for page: {e}")
        
        return tables
    
    def _format_table_as_text(self, table_data: List[List[str]]) -> str:
        """Format table data as readable text"""
        if not table_data:
            return ""
        
        # Find column widths
        col_widths = []
        for row in table_data:
            for i, cell in enumerate(row):
                if len(col_widths) <= i:
                    col_widths.append(0)
                col_widths[i] = max(col_widths[i], len(str(cell or "")))
        
        # Format rows
        formatted_rows = []
        for row in table_data:
            formatted_cells = []
            for i, cell in enumerate(row):
                cell_str = str(cell or "").ljust(col_widths[i])
                formatted_cells.append(cell_str)
            formatted_rows.append(" | ".join(formatted_cells))
        
        return "\n".join(formatted_rows)
    
    def export_to_json(self, output_path: str) -> bool:
        """Export extracted sections to JSON"""
        try:
            data = {
                "document_info": {
                    "source_pdf": self.pdf_path,
                    "extraction_date": datetime.utcnow().isoformat(),
                    "total_pages": len(self.doc) if self.doc else 0,
                    "total_sections": len(self.sections)
                },
                "table_of_contents": [
                    {
                        "section_number": entry.section_number,
                        "title": entry.title,
                        "page_number": entry.page_number,
                        "level": entry.level
                    }
                    for entry in self.toc_entries
                ],
                "sections": [
                    {
                        "section_number": section.section_number,
                        "title": section.title,
                        "content": section.content,
                        "page_number": section.page_number,
                        "level": section.level,
                        "content_length": len(section.content)
                    }
                    for section in self.sections
                ]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Exported to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to export JSON: {e}")
            return False
    
    def close(self):
        """Close the PDF document"""
        if self.doc:
            self.doc.close()

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parse ICANN Guidebook PDF")
    parser.add_argument("pdf_path", help="Path to the ICANN PDF file")
    parser.add_argument("--output", "-o", default="icann_guidebook_parsed.json", 
                       help="Output JSON file path")
    parser.add_argument("--download", "-d", action="store_true",
                       help="Download the latest ICANN guidebook PDF")
    
    args = parser.parse_args()
    
    try:
        # Download PDF if requested
        if args.download:
            logger.info("📥 Downloading ICANN guidebook...")
            # You can add download logic here for the official PDF
            # For now, user needs to provide the PDF path
            pass
        
        # Parse PDF
        parser = ICANNPDFParser(args.pdf_path)
        
        if not parser.load_pdf():
            sys.exit(1)
        
        # Extract structure
        toc_entries = parser.extract_table_of_contents()
        if not toc_entries:
            logger.error("❌ Could not extract table of contents")
            sys.exit(1)
        
        # Extract sections
        sections = parser.extract_sections()
        if not sections:
            logger.error("❌ Could not extract sections")
            sys.exit(1)
        
        # Export results
        if parser.export_to_json(args.output):
            logger.info("\n" + "="*60)
            logger.info("✅ PDF PARSING COMPLETE!")
            logger.info("="*60)
            logger.info(f"📄 Processed: {args.pdf_path}")
            logger.info(f"📋 TOC entries: {len(toc_entries)}")
            logger.info(f"📖 Sections extracted: {len(sections)}")
            logger.info(f"💾 Output: {args.output}")
            logger.info("\nNext step: Use this structured data to create embeddings")
        
        parser.close()
        
    except Exception as e:
        logger.error(f"❌ PDF parsing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
