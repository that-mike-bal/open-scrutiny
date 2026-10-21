"""
Application Response Parser
Extracts structured JSON data from generated application output files
and stores them in the database
"""

import json
import re
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from crewai_service.utils.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class ApplicationResponseParser:
    def __init__(self, outputs_dir: str = "outputs"):
        self.outputs_dir = Path(outputs_dir)
        self.supabase = get_supabase_client()
        
    def extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text that may contain markdown and other content"""
        # Look for JSON code blocks
        json_pattern = r'```json\s*\n(.*?)\n\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return None
        
        # If no code block, look for raw JSON
        try:
            # Try to find JSON-like structure
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
        return None
    
    def parse_application_responses(self, tld_string: str) -> Dict[str, Any]:
        """Parse all application response files for a given TLD string"""
        results = {
            "tld_string": tld_string,
            "sections": {},
            "summary": {
                "total_questions": 0,
                "total_responses": 0,
                "completion_percentage": 0
            }
        }
        
        # Define the file patterns and their sections
        file_patterns = {
            "organization_responses": "organization_information",
            "technical_capability": "technical_services", 
            "financial_capability": "financial_information",
            "legal_compliance": "legal_compliance",
            "integrated_application": "integrated_summary"
        }
        
        for file_pattern, section_name in file_patterns.items():
            file_path = self.outputs_dir / f"{file_pattern}_{tld_string}.md"
            
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    json_data = self.extract_json_from_text(content)
                    if json_data:
                        results["sections"][section_name] = json_data
                        
                        # Update summary counts
                        if "responses" in json_data:
                            results["summary"]["total_responses"] += len(json_data["responses"])
                        
                        if "generation_summary" in json_data:
                            expected = json_data["generation_summary"].get("expected_count", 0)
                            results["summary"]["total_questions"] += expected
                    else:
                        # Fallback: parse markdown for basic info
                        results["sections"][section_name] = {
                            "section": section_name,
                            "tld_string": tld_string,
                            "content": content,
                            "parsed_json": False
                        }
                        
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    
        # Calculate completion percentage
        if results["summary"]["total_questions"] > 0:
            results["summary"]["completion_percentage"] = round(
                (results["summary"]["total_responses"] / results["summary"]["total_questions"]) * 100, 2
            )
                    
        return results
    
    def get_questions_and_answers(self, tld_string: str) -> List[Dict[str, Any]]:
        """Extract all questions and answers in a flat list for display"""
        application_data = self.parse_application_responses(tld_string)
        questions_and_answers = []
        
        for section_name, section_data in application_data["sections"].items():
            if "responses" in section_data:
                for response in section_data["responses"]:
                    questions_and_answers.append({
                        "id": response.get("question_id", response.get("question_number")),
                        "question_number": response.get("question_number", ""),
                        "section": response.get("section", section_name),
                        "subsection": response.get("subsection", ""),
                        "question_text": response.get("question_text", ""),
                        "answer": response.get("answer", ""),
                        "character_count": response.get("character_count", 0),
                        "validation_status": response.get("validation_status", "PENDING"),
                        "data_source": response.get("data_source", "Generated"),
                        "required": response.get("required", True),
                        "public_posting": response.get("public_posting", False)
                    })
        
        # Sort by question number
        questions_and_answers.sort(key=lambda x: self._extract_question_sort_key(x["question_number"]))
        return questions_and_answers
    
    def _extract_question_sort_key(self, question_number: str) -> tuple:
        """Extract sort key from question number like '18a' or '19.1' or '20.b.i'"""
        try:
            # Handle formats like "18a", "19.1", "20.b.i"
            parts = re.findall(r'\d+|[a-z]+', str(question_number).lower())
            sort_key = []
            for part in parts:
                if part.isdigit():
                    sort_key.append(int(part))
                else:
                    # Convert letters to numbers (a=1, b=2, etc.)
                    sort_key.append(ord(part[0]) - ord('a') + 1)
            return tuple(sort_key)
        except:
            return (999, 999)  # Put unparseable items at the end

    def store_answers_in_database(self, application_id: str, questions_and_answers: List[Dict[str, Any]]) -> bool:
        """Store parsed answers in the database"""
        try:
            # First ensure questions exist in the database
            self._ensure_questions_exist(questions_and_answers)

            # Store answers
            stored_count = 0
            for qa in questions_and_answers:
                try:
                    # Find the question ID by question number
                    question_result = self.supabase.table('application_questions').select('id').eq('question_number', qa['question_number']).single().execute()

                    if not question_result.data:
                        logger.warning(f"Question {qa['question_number']} not found in database")
                        continue

                    question_id = question_result.data['id']

                    # Prepare answer data
                    answer_data = {
                        'application_id': application_id,
                        'question_id': question_id,
                        'answer_text': qa['answer'],
                        'status': 'ai_generated',
                        'ai_generated': True,
                        'last_modified': 'now()'
                    }

                    # Upsert the answer
                    result = self.supabase.table('application_answers').upsert(
                        answer_data,
                        on_conflict='application_id,question_id'
                    ).execute()

                    if result.data:
                        stored_count += 1
                        logger.debug(f"Stored answer for question {qa['question_number']}")

                except Exception as e:
                    logger.error(f"Error storing answer for question {qa['question_number']}: {e}")
                    continue

            logger.info(f"Successfully stored {stored_count}/{len(questions_and_answers)} answers for application {application_id}")
            return stored_count > 0

        except Exception as e:
            logger.error(f"Error storing answers in database: {e}")
            return False

    def _ensure_questions_exist(self, questions_and_answers: List[Dict[str, Any]]) -> None:
        """Ensure all questions from the parsed data exist in the database"""
        try:
            for qa in questions_and_answers:
                # Check if question exists
                existing = self.supabase.table('application_questions').select('id').eq('question_number', qa['question_number']).execute()

                if not existing.data:
                    # Create the question
                    question_data = {
                        'question_number': qa['question_number'],
                        'section': qa.get('section', 'Unknown'),
                        'subsection': qa.get('subsection', ''),
                        'question_text': qa.get('question_text', ''),
                        'field_type': 'textarea',
                        'required': qa.get('required', True),
                        'public_posting': qa.get('public_posting', False)
                    }

                    result = self.supabase.table('application_questions').insert(question_data).execute()
                    if result.data:
                        logger.info(f"Created question {qa['question_number']}")

        except Exception as e:
            logger.error(f"Error ensuring questions exist: {e}")

    def parse_and_store_application_responses(self, application_id: str, tld_string: str) -> Dict[str, Any]:
        """Parse application responses and store them in the database"""
        try:
            # Parse the responses from files
            questions_and_answers = self.get_questions_and_answers(tld_string)
            application_data = self.parse_application_responses(tld_string)

            # Store in database
            stored = self.store_answers_in_database(application_id, questions_and_answers)

            # Update application completion status
            if stored:
                self._update_application_status(application_id, len(questions_and_answers))

            return {
                "success": stored,
                "application_id": application_id,
                "tld_string": tld_string,
                "summary": application_data["summary"],
                "questions": questions_and_answers,
                "sections": list(application_data["sections"].keys()),
                "stored_in_db": stored
            }

        except Exception as e:
            logger.error(f"Error parsing and storing responses for {application_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "application_id": application_id,
                "tld_string": tld_string
            }

    def _update_application_status(self, application_id: str, total_answers: int) -> None:
        """Update application status and completion percentage"""
        try:
            # Calculate completion percentage (simple approach)
            total_questions_result = self.supabase.table('application_questions').select('id', count='exact').execute()
            total_questions = total_questions_result.count or 1

            completion_percentage = min(100.0, (total_answers / total_questions) * 100)

            # Update application
            update_data = {
                'completion_percentage': completion_percentage,
                'status': 'Completed' if completion_percentage >= 80 else 'Generating'
            }

            result = self.supabase.table('tld_applications').update(update_data).eq('id', application_id).execute()

            if result.data:
                logger.info(f"Updated application {application_id} completion to {completion_percentage}%")

        except Exception as e:
            logger.error(f"Error updating application status: {e}")


def main():
    """Test the parser"""
    parser = ApplicationResponseParser()
    
    # Test with existing files
    test_tlds = ["fart", "max", "test123"]
    
    for tld in test_tlds:
        print(f"\n=== Testing {tld} ===")
        results = parser.parse_application_responses(tld)
        print(f"Total sections found: {len(results['sections'])}")
        print(f"Summary: {results['summary']}")
        
        # Test Q&A extraction
        qa_list = parser.get_questions_and_answers(tld)
        print(f"Questions and answers found: {len(qa_list)}")
        
        if qa_list:
            print("Sample Q&A:")
            for qa in qa_list[:3]:  # Show first 3
                print(f"  Q{qa['question_number']}: {qa['question_text'][:60]}...")
                print(f"  A: {qa['answer'][:60]}...")


if __name__ == "__main__":
    main()