"""
Question-to-Data Mapping Engine
===============================

Maps ICANN application questions to relevant evaluation data sources and creates
targeted responses using the appropriate data integration strategies.

This module handles the core logic for connecting the 227 ICANN application questions
to the various data sources available from string evaluations, entity data, and
market research.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import re

logger = logging.getLogger(__name__)

class QuestionCategory(Enum):
    """Categories of ICANN application questions"""
    ORGANIZATION = "organization"
    TECHNICAL = "technical" 
    FINANCIAL = "financial"
    LEGAL = "legal"
    UNKNOWN = "unknown"

class DataSourceType(Enum):
    """Types of data sources available for mapping"""
    APPLICANT_ENTITY = "applicant_entity"
    TECHNICAL_ASSESSMENT = "technical_assessment"
    BUSINESS_SCORING = "business_scoring"
    TRADEMARK_ANALYSIS = "trademark_analysis"
    LEGAL_RISK_ASSESSMENT = "legal_risk_assessment"
    DNS_STABILITY = "dns_stability"
    COLLISION_ANALYSIS = "collision_analysis"
    MARKET_ANALYSIS = "market_analysis"
    GAC_RISK_ANALYSIS = "gac_risk_analysis"

@dataclass
class QuestionMapping:
    """Represents the mapping between a question and its data sources"""
    question_number: str
    question_text: str
    category: QuestionCategory
    data_sources: List[DataSourceType]
    agent_specialist: str
    priority: int = 1  # 1 = high priority, 3 = low priority
    character_limit: Optional[int] = None
    format_requirements: List[str] = None
    validation_rules: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.format_requirements is None:
            self.format_requirements = []
        if self.validation_rules is None:
            self.validation_rules = {}

class QuestionMappingEngine:
    """
    Core engine for mapping ICANN questions to data sources and generating responses
    """
    
    def __init__(self):
        self.question_mappings: Dict[str, QuestionMapping] = {}
        self._initialize_question_mappings()
        
    def _initialize_question_mappings(self):
        """Initialize the core question mappings for key question categories"""
        
        # ORGANIZATION QUESTIONS (Q7-125)
        org_questions = [
            # Legal Entity Information (Q7-25)
            ("Q7", "Legal Entity Identifier (LEI)", ["alphanumeric"], 20),
            ("Q8", "Proof of Establishment", ["upload"], 10),
            ("Q9", "Proof of Good Standing", ["upload"], 10),
            ("Q10", "Website URL", ["url"], 255),
            ("Q11", "Business Description", ["textarea"], 4000),
            ("Q12", "Legal Name", ["text"], 255),
            ("Q13", "Entity Type", ["dropdown"], None),
            ("Q14", "Incorporation Jurisdiction", ["text"], 255),
            ("Q15", "Incorporation Date", ["date"], None),
            
            # Contact Information (Q16-35) 
            ("Q16", "Primary Business Address Line 1", ["text", "no_po_box"], 255),
            ("Q17", "Primary Business Address Line 2", ["text"], 255),
            ("Q18", "Primary Business City", ["text"], 255),
            ("Q19", "Primary Business State/Province", ["text"], 255),
            ("Q20", "Primary Business Postal Code", ["text"], 50),
            ("Q21", "Primary Business Country", ["dropdown"], None),
            ("Q22", "Primary Business Phone", ["phone"], 50),
            ("Q23", "Primary Business Email", ["email"], 255),
            ("Q24", "Primary Contact Person", ["text"], 255),
            ("Q25", "Primary Contact Title", ["text"], 255),
            
            # Additional organization questions would be added here
        ]
        
        for q_num, q_text, format_reqs, char_limit in org_questions:
            self.question_mappings[q_num] = QuestionMapping(
                question_number=q_num,
                question_text=q_text,
                category=QuestionCategory.ORGANIZATION,
                data_sources=[DataSourceType.APPLICANT_ENTITY],
                agent_specialist="organization_info_agent",
                character_limit=char_limit,
                format_requirements=format_reqs,
                validation_rules=self._get_validation_rules(format_reqs)
            )
        
        # TECHNICAL QUESTIONS (Q18-55 overlapping with registry services)
        tech_questions = [
            ("Q18", "Registry Services Description", ["textarea"], 7500),
            ("Q26", "Technical Capability Overview", ["textarea"], 5000),
            ("Q27", "DNS Infrastructure Architecture", ["textarea"], 6000),
            ("Q28", "DNSSEC Implementation", ["textarea"], 4000),
            ("Q29", "IPv6 Support", ["textarea"], 3000),
            ("Q30", "EPP Implementation", ["textarea"], 4000),
            ("Q36", "Security Framework", ["textarea"], 6000),
            ("Q37", "Monitoring and Incident Response", ["textarea"], 5000),
            ("Q46", "Operational Procedures", ["textarea"], 5000),
            ("Q47", "Maintenance Procedures", ["textarea"], 4000),
        ]
        
        for q_num, q_text, format_reqs, char_limit in tech_questions:
            self.question_mappings[q_num] = QuestionMapping(
                question_number=q_num,
                question_text=q_text,
                category=QuestionCategory.TECHNICAL,
                data_sources=[
                    DataSourceType.TECHNICAL_ASSESSMENT,
                    DataSourceType.DNS_STABILITY,
                    DataSourceType.COLLISION_ANALYSIS
                ],
                agent_specialist="technical_capability_agent",
                character_limit=char_limit,
                format_requirements=format_reqs
            )
        
        # FINANCIAL QUESTIONS (Q126-210)
        financial_questions = [
            ("Q126", "Five-Year Financial Projections", ["textarea"], 8000),
            ("Q127", "Revenue Model Description", ["textarea"], 5000),
            ("Q128", "Registration Volume Projections", ["textarea"], 4000),
            ("Q129", "Pricing Strategy", ["textarea"], 4000),
            ("Q130", "Cost Analysis", ["textarea"], 6000),
            ("Q151", "Business Model Overview", ["textarea"], 6000),
            ("Q152", "Target Market Analysis", ["textarea"], 5000),
            ("Q153", "Competitive Analysis", ["textarea"], 5000),
            ("Q166", "Funding Sources", ["textarea"], 4000),
            ("Q167", "Financial Capability Demonstration", ["textarea"], 6000),
        ]
        
        for q_num, q_text, format_reqs, char_limit in financial_questions:
            self.question_mappings[q_num] = QuestionMapping(
                question_number=q_num,
                question_text=q_text,
                category=QuestionCategory.FINANCIAL,
                data_sources=[
                    DataSourceType.BUSINESS_SCORING,
                    DataSourceType.MARKET_ANALYSIS,
                    DataSourceType.APPLICANT_ENTITY
                ],
                agent_specialist="financial_capability_agent",
                character_limit=char_limit,
                format_requirements=format_reqs
            )
        
        # LEGAL QUESTIONS (Q211-275)
        legal_questions = [
            ("Q211", "Rights Protection Mechanisms", ["textarea"], 6000),
            ("Q212", "Trademark Claims Service", ["textarea"], 4000),
            ("Q213", "Sunrise Period Implementation", ["textarea"], 5000),
            ("Q231", "Legal Compliance Framework", ["textarea"], 6000),
            ("Q232", "Regulatory Compliance Procedures", ["textarea"], 5000),
            ("Q246", "Dispute Resolution Policy", ["textarea"], 6000),
            ("Q247", "UDRP Implementation", ["textarea"], 4000),
            ("Q261", "Law Enforcement Cooperation", ["textarea"], 4000),
        ]
        
        for q_num, q_text, format_reqs, char_limit in legal_questions:
            self.question_mappings[q_num] = QuestionMapping(
                question_number=q_num,
                question_text=q_text,
                category=QuestionCategory.LEGAL,
                data_sources=[
                    DataSourceType.TRADEMARK_ANALYSIS,
                    DataSourceType.LEGAL_RISK_ASSESSMENT,
                    DataSourceType.GAC_RISK_ANALYSIS
                ],
                agent_specialist="legal_compliance_agent",
                character_limit=char_limit,
                format_requirements=format_reqs
            )
        
        logger.info(f"Initialized {len(self.question_mappings)} question mappings")
    
    def _get_validation_rules(self, format_requirements: List[str]) -> Dict[str, Any]:
        """Generate validation rules based on format requirements"""
        rules = {}
        
        for req in format_requirements:
            if req == "email":
                rules["valid_email"] = True
            elif req == "url":
                rules["valid_url"] = True
            elif req == "phone":
                rules["valid_phone"] = True
            elif req == "alphanumeric":
                rules["alphanumeric_only"] = True
            elif req == "no_po_box":
                rules["no_po_box"] = True
            elif req == "upload":
                rules["file_upload"] = True
                rules["max_pages"] = 10
        
        return rules
    
    def get_question_mapping(self, question_number: str) -> Optional[QuestionMapping]:
        """Get the mapping for a specific question number"""
        return self.question_mappings.get(question_number)
    
    def get_questions_by_category(self, category: QuestionCategory) -> List[QuestionMapping]:
        """Get all questions in a specific category"""
        return [
            mapping for mapping in self.question_mappings.values()
            if mapping.category == category
        ]
    
    def get_questions_by_agent(self, agent_name: str) -> List[QuestionMapping]:
        """Get all questions handled by a specific agent"""
        return [
            mapping for mapping in self.question_mappings.values()
            if mapping.agent_specialist == agent_name
        ]
    
    def get_data_sources_for_question(self, question_number: str) -> List[DataSourceType]:
        """Get the data sources needed for a specific question"""
        mapping = self.get_question_mapping(question_number)
        return mapping.data_sources if mapping else []
    
    def validate_question_response(
        self, 
        question_number: str, 
        response: str, 
        metadata: Dict[str, Any] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate a question response against its requirements
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        mapping = self.get_question_mapping(question_number)
        if not mapping:
            return False, [f"Unknown question number: {question_number}"]
        
        errors = []
        
        # Character limit validation
        if mapping.character_limit and len(response) > mapping.character_limit:
            errors.append(
                f"Response exceeds character limit: {len(response)} > {mapping.character_limit}"
            )
        
        # Format validation
        for req in mapping.format_requirements:
            if req == "email" and not self._validate_email(response):
                errors.append("Invalid email format")
            elif req == "url" and not self._validate_url(response):
                errors.append("Invalid URL format")
            elif req == "phone" and not self._validate_phone(response):
                errors.append("Invalid phone number format")
            elif req == "alphanumeric" and not response.replace(" ", "").isalnum():
                errors.append("Response must contain only alphanumeric characters")
        
        # Validation rules
        if mapping.validation_rules:
            if mapping.validation_rules.get("no_po_box") and "po box" in response.lower():
                errors.append("PO Box addresses are not allowed")
        
        return len(errors) == 0, errors
    
    def _validate_email(self, email: str) -> bool:
        """Basic email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_url(self, url: str) -> bool:
        """Basic URL validation"""
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url))
    
    def _validate_phone(self, phone: str) -> bool:
        """Basic phone number validation"""
        # Remove common formatting characters
        clean_phone = re.sub(r'[\s\-\(\)\+\.]', '', phone)
        return clean_phone.isdigit() and 7 <= len(clean_phone) <= 15
    
    def generate_question_context(
        self, 
        question_numbers: List[str], 
        available_data: Dict[DataSourceType, Any]
    ) -> Dict[str, Any]:
        """
        Generate context for a set of questions based on available data sources
        
        Args:
            question_numbers: List of question numbers to generate context for
            available_data: Dictionary mapping data source types to their data
        
        Returns:
            Dictionary containing context for question generation
        """
        context = {
            "questions": {},
            "data_sources": {},
            "validation_requirements": {}
        }
        
        # Collect question mappings and their requirements
        for q_num in question_numbers:
            mapping = self.get_question_mapping(q_num)
            if mapping:
                context["questions"][q_num] = {
                    "text": mapping.question_text,
                    "category": mapping.category.value,
                    "agent": mapping.agent_specialist,
                    "character_limit": mapping.character_limit,
                    "format_requirements": mapping.format_requirements,
                    "data_sources_needed": [ds.value for ds in mapping.data_sources]
                }
                
                context["validation_requirements"][q_num] = mapping.validation_rules
        
        # Map available data to questions
        for data_type, data in available_data.items():
            if data:
                context["data_sources"][data_type.value] = data
        
        return context
    
    def get_progressive_generation_phases(self) -> Dict[str, List[str]]:
        """
        Get the progressive generation phases with their question numbers
        
        Returns:
            Dictionary mapping phase names to question number lists
        """
        phases = {
            "organization_phase": [],
            "technical_phase": [],
            "financial_phase": [],
            "legal_phase": []
        }
        
        for q_num, mapping in self.question_mappings.items():
            if mapping.category == QuestionCategory.ORGANIZATION:
                phases["organization_phase"].append(q_num)
            elif mapping.category == QuestionCategory.TECHNICAL:
                phases["technical_phase"].append(q_num)
            elif mapping.category == QuestionCategory.FINANCIAL:
                phases["financial_phase"].append(q_num)
            elif mapping.category == QuestionCategory.LEGAL:
                phases["legal_phase"].append(q_num)
        
        # Sort question numbers within each phase
        for phase in phases:
            phases[phase].sort(key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0)
        
        return phases
    
    def export_mapping_schema(self, output_file: str = None) -> Dict[str, Any]:
        """
        Export the complete question mapping schema for documentation or debugging
        """
        schema = {
            "total_questions": len(self.question_mappings),
            "categories": {},
            "agents": {},
            "data_sources": {},
            "mappings": {}
        }
        
        # Group by categories
        for category in QuestionCategory:
            questions = self.get_questions_by_category(category)
            schema["categories"][category.value] = {
                "count": len(questions),
                "questions": [q.question_number for q in questions]
            }
        
        # Group by agents
        agents = set(mapping.agent_specialist for mapping in self.question_mappings.values())
        for agent in agents:
            questions = self.get_questions_by_agent(agent)
            schema["agents"][agent] = {
                "count": len(questions),
                "questions": [q.question_number for q in questions]
            }
        
        # Group by data sources
        for data_source in DataSourceType:
            questions = [
                mapping for mapping in self.question_mappings.values()
                if data_source in mapping.data_sources
            ]
            schema["data_sources"][data_source.value] = {
                "count": len(questions),
                "questions": [q.question_number for q in questions]
            }
        
        # Export individual mappings
        for q_num, mapping in self.question_mappings.items():
            schema["mappings"][q_num] = {
                "text": mapping.question_text,
                "category": mapping.category.value,
                "agent": mapping.agent_specialist,
                "data_sources": [ds.value for ds in mapping.data_sources],
                "character_limit": mapping.character_limit,
                "format_requirements": mapping.format_requirements,
                "validation_rules": mapping.validation_rules
            }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(schema, f, indent=2)
            logger.info(f"Exported mapping schema to {output_file}")
        
        return schema

# Global instance for easy access
question_mapping_engine = QuestionMappingEngine()

def get_question_mapping_engine() -> QuestionMappingEngine:
    """Get the global question mapping engine instance"""
    return question_mapping_engine