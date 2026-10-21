#!/usr/bin/env python3
"""
Application Questions Parser
============================

Parses the ICANN application questions markdown file and populates the
application_questions_enhanced table according to the parsing specification.

Usage:
    python parse_application_questions.py [--dry-run] [--verbose]
"""

import re
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import logging

# Add the project root to the path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from db.supabase_client import get_supabase
except ImportError:
    print("Warning: Could not import supabase_client. Running in dry-run mode.")
    get_supabase = None

@dataclass
class ParsedQuestion:
    """Represents a parsed ICANN application question"""
    question_number: str
    section_name: str
    sub_section: Optional[str]
    question_text: str
    notes_instructions: Optional[str]
    input_type: str
    character_limit: Optional[int]
    word_limit: Optional[int]
    file_upload_max_pages: Optional[int]
    acceptable_file_types: List[str]
    validation_rules: Dict[str, Any]
    criteria_codes: List[str]
    criteria_descriptions: List[str]
    is_public: bool
    is_required: bool
    is_conditional: bool
    condition_description: Optional[str]
    dependent_question_numbers: List[str]
    expected_data_type: str
    response_format: str
    parsing_confidence: float

class ApplicationQuestionParser:
    """Parser for ICANN application questions markdown file"""
    
    def __init__(self, file_path: str, verbose: bool = False):
        self.file_path = Path(file_path)
        self.verbose = verbose
        self.logger = self._setup_logger()
        self.questions: List[ParsedQuestion] = []
        self.parsing_errors: List[str] = []
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        return logger
    
    def parse_questions(self) -> List[ParsedQuestion]:
        """Parse all questions from the markdown file"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Questions file not found: {self.file_path}")
        
        content = self.file_path.read_text(encoding='utf-8')
        question_blocks = self._split_into_question_blocks(content)
        
        self.logger.info(f"Found {len(question_blocks)} question blocks")
        
        for i, block in enumerate(question_blocks):
            try:
                question = self._parse_question_block(block)
                if question:
                    self.questions.append(question)
                    if self.verbose:
                        self.logger.debug(f"Parsed question {question.question_number}")
            except Exception as e:
                error_msg = f"Error parsing question block {i+1}: {str(e)}"
                self.logger.error(error_msg)
                self.parsing_errors.append(error_msg)
        
        self.logger.info(f"Successfully parsed {len(self.questions)} questions")
        if self.parsing_errors:
            self.logger.warning(f"Encountered {len(self.parsing_errors)} parsing errors")
        
        return self.questions
    
    def _split_into_question_blocks(self, content: str) -> List[str]:
        """Split the markdown content into individual question blocks"""
        # Split on **Question X** pattern
        question_pattern = r'\*\*Question \d+\*\*'
        blocks = re.split(question_pattern, content)
        
        # Remove empty blocks and rejoin with question headers
        question_headers = re.findall(question_pattern, content)
        question_blocks = []
        
        for i, header in enumerate(question_headers):
            if i + 1 < len(blocks):  # Ensure we have content for this question
                block_content = blocks[i + 1].strip()
                if block_content:
                    question_blocks.append(header + '\n' + block_content)
        
        return question_blocks
    
    def _parse_question_block(self, block: str) -> Optional[ParsedQuestion]:
        """Parse a single question block into a ParsedQuestion object"""
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        # Extract question number from header
        question_number = self._extract_question_number(lines[0])
        if not question_number:
            return None
        
        # Initialize with defaults
        parsed_data = {
            'question_number': question_number,
            'section_name': '',
            'sub_section': None,
            'question_text': '',
            'notes_instructions': None,
            'input_type': 'text',
            'character_limit': None,
            'word_limit': None,
            'file_upload_max_pages': None,
            'acceptable_file_types': [],
            'validation_rules': {},
            'criteria_codes': [],
            'criteria_descriptions': [],
            'is_public': False,
            'is_required': True,
            'is_conditional': False,
            'condition_description': None,
            'dependent_question_numbers': [],
            'expected_data_type': 'organization_info',
            'response_format': 'narrative',
            'parsing_confidence': 1.0
        }
        
        # Parse each line and collect multi-line content
        current_field = None
        current_content = []
        
        for line in lines[1:]:
            if '**Sub-section:**' in line:
                parsed_data['section_name'] = self._extract_after_colon(line)
                parsed_data['sub_section'] = parsed_data['section_name']
                current_field = None
            elif '**Question:**' in line:
                parsed_data['question_text'] = self._extract_after_colon(line)
                current_field = None
            elif '**Public Posting:**' in line:
                parsed_data['is_public'] = 'Yes' in line
                current_field = None
            elif '**Notes/Instructions:**' in line:
                content = self._extract_after_colon(line)
                current_field = 'notes_instructions'
                current_content = [content] if content else []
            elif '**Criteria:**' in line:
                content = self._extract_after_colon(line)
                current_field = 'criteria'
                current_content = [content] if content else []
            elif '**Input Field Requirements:**' in line:
                content = self._extract_after_colon(line)
                current_field = 'requirements'
                current_content = [content] if content else []
            elif current_field and line.strip():
                # This is a continuation line for a multi-line field
                clean_line = self._extract_after_colon(line)
                if clean_line:
                    current_content.append(clean_line)
            
            # Process field when we hit a new field or end of block
            if current_field and (line.startswith('**') or line == lines[-1]):
                if current_field == 'notes_instructions':
                    parsed_data['notes_instructions'] = ' '.join(current_content)
                elif current_field == 'criteria':
                    criteria_text = ' '.join(current_content)
                    parsed_data['criteria_codes'], parsed_data['criteria_descriptions'] = self._parse_criteria(criteria_text)
                elif current_field == 'requirements':
                    requirements_text = ' '.join(current_content)
                    self._parse_input_requirements(requirements_text, parsed_data)
                
                if line.startswith('**'):
                    current_field = None
                    current_content = []
        
        # Derive additional fields
        self._derive_additional_fields(parsed_data)
        
        return ParsedQuestion(**parsed_data)
    
    def _extract_question_number(self, header_line: str) -> Optional[str]:
        """Extract question number from header line"""
        match = re.search(r'\*\*Question (\d+[a-zA-Z]*(?:\.\d+)*)\*\*', header_line)
        return match.group(1) if match else None
    
    def _extract_after_colon(self, line: str) -> str:
        """Extract text after the last colon in a line, cleaning markdown formatting"""
        if ':' in line:
            text = line.split(':', 1)[1].strip()
        else:
            text = line.strip()
        
        # Clean markdown formatting
        text = re.sub(r'\*+', '', text)  # Remove asterisks
        text = re.sub(r'^\s*\*\s*', '', text)  # Remove bullet points
        text = text.strip()
        
        return text
    
    def _parse_criteria(self, criteria_text: str) -> Tuple[List[str], List[str]]:
        """Parse criteria codes and descriptions"""
        codes = []
        descriptions = []
        
        # Find CR-X patterns
        cr_matches = re.findall(r'CR-\d+', criteria_text)
        codes.extend(cr_matches)
        
        # Split by CR- patterns to get descriptions
        parts = re.split(r'CR-\d+\.?\s*', criteria_text)
        for part in parts[1:]:  # Skip first empty part
            if part.strip():
                descriptions.append(part.strip().rstrip('.'))
        
        return codes, descriptions
    
    def _parse_input_requirements(self, requirements_text: str, parsed_data: Dict[str, Any]) -> None:
        """Parse input field requirements and update parsed_data"""
        text_lower = requirements_text.lower()
        validation_rules = {}
        
        # Character limits
        char_match = re.search(r'(\d+)\s+character\s+limit', text_lower)
        if char_match:
            parsed_data['character_limit'] = int(char_match.group(1))
            validation_rules['character_limit'] = int(char_match.group(1))
        
        # Word limits
        word_match = re.search(r'(\d+)\s+word\s+limit', text_lower)
        if word_match:
            parsed_data['word_limit'] = int(word_match.group(1))
            validation_rules['word_limit'] = int(word_match.group(1))
        
        # File upload pages
        pages_match = re.search(r'no more than (\d+)\s+pages', text_lower)
        if pages_match:
            parsed_data['file_upload_max_pages'] = int(pages_match.group(1))
            parsed_data['input_type'] = 'upload'
            validation_rules['max_pages'] = int(pages_match.group(1))
        
        # Input type detection
        if 'dropdown' in text_lower or 'select' in text_lower:
            parsed_data['input_type'] = 'dropdown'
        elif 'radio' in text_lower:
            parsed_data['input_type'] = 'radio'
        elif 'upload' in text_lower:
            parsed_data['input_type'] = 'upload'
        elif 'email' in text_lower:
            parsed_data['input_type'] = 'email'
            validation_rules['format'] = 'email'
        elif 'url' in text_lower:
            parsed_data['input_type'] = 'url'
            validation_rules['format'] = 'url'
        elif 'phone' in text_lower:
            parsed_data['input_type'] = 'phone'
            validation_rules['format'] = 'phone'
        elif parsed_data['character_limit'] and parsed_data['character_limit'] > 1000:
            parsed_data['input_type'] = 'textarea'
        
        # Validation rules
        if 'alphanumeric' in text_lower:
            validation_rules['alphanumeric_only'] = True
        if 'latin characters' in text_lower:
            validation_rules['latin_characters_only'] = True
        if 'no po box' in text_lower or 'physical address' in text_lower:
            validation_rules['no_po_box'] = True
        if 'option must be selected' in text_lower:
            validation_rules['required'] = True
        if 'valid url' in text_lower:
            validation_rules['valid_url'] = True
        if 'valid email' in text_lower:
            validation_rules['valid_email'] = True
        if 'valid phone' in text_lower:
            validation_rules['valid_phone'] = True
        
        parsed_data['validation_rules'] = validation_rules
    
    def _derive_additional_fields(self, parsed_data: Dict[str, Any]) -> None:
        """Derive expected_data_type and response_format from question content"""
        question_text = parsed_data['question_text'].lower()
        section_name = parsed_data['section_name'].lower()
        
        # Expected data type classification
        if any(term in question_text or term in section_name for term in [
            'legal name', 'entity', 'incorporation', 'jurisdiction', 'business name'
        ]):
            parsed_data['expected_data_type'] = 'organization_info'
        elif any(term in question_text or term in section_name for term in [
            'address', 'phone', 'email', 'contact', 'locality', 'region'
        ]):
            parsed_data['expected_data_type'] = 'contact_details'
        elif any(term in question_text or term in section_name for term in [
            'revenue', 'financial', 'asset', 'stock', 'exchange', 'funding'
        ]):
            parsed_data['expected_data_type'] = 'financial_data'
        elif any(term in question_text or term in section_name for term in [
            'certificate', 'proof', 'document', 'articles', 'incorporation'
        ]):
            parsed_data['expected_data_type'] = 'legal_documents'
        elif any(term in question_text or term in section_name for term in [
            'technical', 'registry', 'infrastructure', 'capability'
        ]):
            parsed_data['expected_data_type'] = 'technical_specs'
        
        # Response format
        if parsed_data['input_type'] == 'upload':
            parsed_data['response_format'] = 'document_upload'
        elif parsed_data['input_type'] in ['dropdown', 'radio']:
            parsed_data['response_format'] = 'selection'
        elif parsed_data['expected_data_type'] in ['contact_details', 'organization_info']:
            parsed_data['response_format'] = 'structured_data'
        else:
            parsed_data['response_format'] = 'narrative'
    
    def save_to_database(self, dry_run: bool = False) -> bool:
        """Save parsed questions to the database"""
        if not self.questions:
            self.logger.error("No questions to save")
            return False
        
        if dry_run:
            self.logger.info("DRY RUN: Would insert the following questions:")
            for question in self.questions[:5]:  # Show first 5 as sample
                self.logger.info(f"  Question {question.question_number}: {question.question_text[:50]}...")
            self.logger.info(f"  ... and {len(self.questions) - 5} more questions")
            return True
        
        if not get_supabase:
            self.logger.error("Supabase client not available. Cannot save to database.")
            return False
        
        try:
            db_client = get_supabase()
            supabase = db_client.client
            
            # Convert questions to dict format for insertion
            questions_data = []
            for question in self.questions:
                data = asdict(question)
                
                # Truncate fields that might exceed database constraints
                data['section_name'] = (question.section_name or '')[:100]
                data['sub_section'] = (question.sub_section or '')[:100] if question.sub_section else None
                
                # Convert lists and dicts to JSON strings for PostgreSQL
                data['acceptable_file_types'] = question.acceptable_file_types
                data['validation_rules'] = question.validation_rules
                data['criteria_codes'] = question.criteria_codes
                data['criteria_descriptions'] = question.criteria_descriptions
                data['dependent_question_numbers'] = question.dependent_question_numbers
                questions_data.append(data)
            
            # Insert in batches to avoid timeouts
            batch_size = 50
            total_inserted = 0
            
            for i in range(0, len(questions_data), batch_size):
                batch = questions_data[i:i + batch_size]
                result = supabase.table('application_questions_enhanced').insert(batch).execute()
                
                if result.data:
                    batch_count = len(result.data)
                    total_inserted += batch_count
                    self.logger.info(f"Inserted batch {i//batch_size + 1}: {batch_count} questions")
                else:
                    self.logger.error(f"Failed to insert batch {i//batch_size + 1}")
                    return False
            
            self.logger.info(f"Successfully inserted {total_inserted} questions into database")
            return True
            
        except Exception as e:
            self.logger.error(f"Database insertion failed: {str(e)}")
            return False
    
    def export_to_json(self, output_path: str) -> bool:
        """Export parsed questions to JSON file for inspection"""
        try:
            questions_data = [asdict(q) for q in self.questions]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_questions': len(self.questions),
                    'parsing_errors': self.parsing_errors,
                    'questions': questions_data
                }, f, indent=2, default=str)
            
            self.logger.info(f"Exported {len(self.questions)} questions to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"JSON export failed: {str(e)}")
            return False

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Parse ICANN application questions and populate database')
    parser.add_argument('--dry-run', action='store_true', help='Parse and validate without inserting to database')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--export-json', help='Export parsed data to JSON file')
    parser.add_argument('--input-file', default='data/application_questions.md', help='Input markdown file path')
    
    args = parser.parse_args()
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    input_file = project_root / args.input_file
    
    try:
        # Create parser and parse questions
        question_parser = ApplicationQuestionParser(str(input_file), verbose=args.verbose)
        questions = question_parser.parse_questions()
        
        if not questions:
            print("ERROR: No questions were successfully parsed")
            return 1
        
        # Export to JSON if requested
        if args.export_json:
            json_path = project_root / args.export_json
            question_parser.export_to_json(str(json_path))
        
        # Save to database
        success = question_parser.save_to_database(dry_run=args.dry_run)
        
        if success:
            print(f"✅ Successfully processed {len(questions)} questions")
            if question_parser.parsing_errors:
                print(f"⚠️  {len(question_parser.parsing_errors)} parsing errors encountered")
            return 0
        else:
            print("❌ Failed to save questions to database")
            return 1
            
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())