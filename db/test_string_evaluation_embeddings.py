#!/usr/bin/env python3
"""
Test Guidebook Embeddings - String Types and Evaluation Focus

This script creates test data specifically focused on string types and evaluation
processes from the ICANN guidebook to validate our embedding system.

Usage:
    python db/test_string_evaluation_embeddings.py
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.populate_guidebook_embeddings import GuidebookEmbeddingsPopulator
from db.guidebook_search import GuidebookSearcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_string_evaluation_test_data() -> List[Dict[str, Any]]:
    """Create comprehensive test data focused on string types and evaluation"""
    
    return [
        {
            'section_number': '1.1.2.1',
            'section_title': 'String Similarity Review Process',
            'page_number': 15,
            'content_text': '''The String Similarity Review will be conducted by a String Similarity Panel consisting of experts in linguistics, intellectual property, and domain name policy. The panel will evaluate whether a proposed gTLD string is confusingly similar to an existing TLD or reserved name.

The review process considers:
1. Visual similarity - how the strings appear when displayed
2. Aural similarity - how the strings sound when spoken
3. Meaning similarity - conceptual relationships between strings
4. Overall likelihood of user confusion

Strings that are found to be confusingly similar may result in:
- Application rejection
- Entry into contention resolution process
- Required modifications to the proposed string

The panel uses established linguistic principles and considers the global nature of the DNS, including considerations for internationalized domain names (IDNs) and different scripts.''',
            'content_type': 'section'
        },
        {
            'section_number': '1.1.2.2',
            'section_title': 'String Similarity Criteria',
            'page_number': 16,
            'content_text': '''String similarity evaluation follows specific criteria established by ICANN:

VISUAL SIMILARITY:
- Identical strings differing only by case (e.g., "EXAMPLE" vs "example")
- Strings with character substitutions that create visual confusion (e.g., "0" vs "O", "1" vs "l")
- Strings with minor typographical variations
- Similar length strings with high character overlap

AURAL SIMILARITY:
- Strings that sound identical or nearly identical when pronounced
- Consideration of different pronunciation patterns across languages
- Phonetic equivalents in major languages

MEANING SIMILARITY:
- Translations of the same word across languages
- Synonyms or words with related meanings
- Generic terms for the same concept
- Brand names that reference similar concepts

TECHNICAL CONSIDERATIONS:
- Impact on DNS resolution and stability
- Potential for user confusion in typing
- Security implications of similar strings
- Internationalization and script mixing issues''',
            'content_type': 'section'
        },
        {
            'section_number': '1.1.2.3',
            'section_title': 'Reserved Names and Protected Strings',
            'page_number': 17,
            'content_text': '''Certain strings are reserved and cannot be used as gTLDs regardless of the application:

SPECIFICATION 5 RESERVED NAMES:
- Two-character country codes from ISO 3166-1
- Three-character country codes from ISO 3166-1 alpha-3
- Two-character territory codes
- UN specialized agency abbreviations
- International organization identifiers

RFC 6761 SPECIAL NAMES:
- .test - reserved for testing purposes
- .localhost - reserved for local host
- .local - reserved for link-local
- .example - reserved for documentation
- .invalid - reserved for invalid use

ICANN BLOCKED NAMES:
- Strings that could cause technical instability
- Names that conflict with DNS infrastructure
- Strings reserved for future ICANN use
- Names that could compromise security

ADDITIONAL PROTECTIONS:
- Geographic names requiring government support
- Intergovernmental organization names
- Red Cross and Red Crescent identifiers
- Olympic Committee identifiers

Applications for reserved strings will be rejected during initial review without proceeding to evaluation panels.''',
            'content_type': 'section'
        },
        {
            'section_number': '2.1.1',
            'section_title': 'String Evaluation Timeline and Process',
            'page_number': 45,
            'content_text': '''The string evaluation process follows a structured timeline designed to ensure thorough review:

INITIAL SCREENING (30 days):
- Administrative completeness check
- Reserved names verification
- Basic format validation
- Fee payment confirmation

STRING SIMILARITY REVIEW (60 days):
- Expert panel review
- Linguistic analysis
- Comparison with existing TLDs
- Public comment consideration

EXTENDED EVALUATION (if required):
- Additional expert review for complex cases
- Community input for geographic strings
- Technical analysis for IDN strings
- Legal review for trademark issues

OBJECTION PERIOD (60 days):
- Formal objection filing period
- String confusion objections
- Legal rights objections
- Community objections
- Limited public interest objections

DISPUTE RESOLUTION (varies):
- Expert panel hearings
- Evidence submission
- Final determinations
- Appeals process

The entire string evaluation process typically takes 5-8 months for standard applications, with additional time required for applications facing objections or requiring extended evaluation.''',
            'content_type': 'section'
        },
        {
            'section_number': '2.1.2',
            'section_title': 'String Contention Resolution',
            'page_number': 46,
            'content_text': '''When multiple applications are submitted for identical or confusingly similar strings, contention resolution procedures apply:

CONTENTION SETS:
- Applications for identical strings form direct contention
- Applications for confusingly similar strings may be placed in contention
- String Similarity Panel determines contention relationships
- All applications in a contention set compete for the same string

RESOLUTION METHODS:
1. Community Priority Evaluation
   - Community-based applications receive priority
   - Must demonstrate substantial opposition to non-community use
   - Evaluated by independent expert panels

2. Auction Process
   - Last resort mechanism for resolving contention
   - Sealed-bid auction format
   - Proceeds benefit ICANN community
   - Winner receives delegation rights

SETTLEMENT OPPORTUNITIES:
- Private resolution between applicants
- Withdrawal agreements
- Joint ventures or partnerships
- String modifications to avoid contention

TIMING CONSIDERATIONS:
- Contention resolution occurs after all evaluations complete
- Community priority evaluation precedes auctions
- Final resolution required before delegation

The contention resolution process ensures that only one registry operator receives rights to each unique string space in the DNS.''',
            'content_type': 'section'
        },
        {
            'section_number': '3.2.1',
            'section_title': 'Internationalized Domain Names (IDN) String Requirements',
            'page_number': 78,
            'content_text': '''IDN gTLD strings must comply with additional technical and policy requirements:

TECHNICAL STANDARDS:
- RFC 5891 (Internationalized Domain Names in Applications)
- Unicode Standard version compatibility
- IDNA2008 protocol compliance
- Script-specific validation rules

SCRIPT REQUIREMENTS:
- Single script per label (with limited exceptions)
- No mixing of scripts that could cause confusion
- Proper use of combining characters
- Adherence to script-specific rules

LANGUAGE REQUIREMENTS:
- Meaningful strings in supported languages
- Proper linguistic construction
- Cultural appropriateness
- Avoidance of offensive terms

CONFUSABILITY ANALYSIS:
- Visual confusability with existing strings
- Cross-script confusability assessment
- Whole-script confusability evaluation
- Mixed-script confusability prevention

VARIANT MANAGEMENT:
- Identification of variant labels
- Consistent treatment of variants
- User expectation management
- Technical implementation requirements

IDN applications undergo additional technical review by specialized panels with expertise in internationalization, linguistics, and the specific scripts being proposed.''',
            'content_type': 'section'
        },
        {
            'section_number': '3.2.2',
            'section_title': 'Geographic String Evaluation',
            'page_number': 79,
            'content_text': '''Geographic strings require special evaluation procedures and government endorsement:

GEOGRAPHIC STRING DEFINITION:
- Country names in any language or script
- Territory or place names
- Capital city names
- Significant geographic regions
- UNESCO World Heritage site names

GOVERNMENT SUPPORT REQUIREMENTS:
- Relevant government or public authority endorsement
- Documentation of support or non-objection
- Appropriate governmental level for the geographic scope
- Public interest considerations

EVALUATION CRITERIA:
- Accuracy of geographic representation
- Cultural sensitivity and appropriateness
- Potential for confusion with official government services
- Impact on local communities and stakeholders

SPECIAL PROCEDURES:
- Extended public comment periods
- Government notification requirements
- Geographic Names Panel review
- Additional documentation requirements

DELEGATION CONDITIONS:
- Ongoing government relationship requirements
- Public interest obligations
- Service availability in relevant regions
- Cultural and linguistic considerations

Geographic strings carry additional responsibilities to serve the public interest and maintain appropriate relationships with relevant governmental and community stakeholders.''',
            'content_type': 'section'
        },
        {
            'section_number': '4.1.1',
            'section_title': 'String Evaluation Fees and Costs',
            'page_number': 95,
            'content_text': '''String evaluation involves various fees and cost considerations:

BASE EVALUATION FEE:
- $185,000 USD per application
- Covers initial review and standard evaluation
- Non-refundable upon submission
- Includes basic string similarity review

EXTENDED EVALUATION FEES:
- $50,000 USD for extended evaluation
- Required for complex strings or applications
- Geographic strings requiring government consultation
- IDN strings requiring specialized review

ADDITIONAL COSTS:
- Community Priority Evaluation: $50,000
- Objection filing fees: $13,000-$45,000
- Dispute resolution costs: varies by panel
- Auction participation: deposit required

REFUND POLICIES:
- No refunds for withdrawn applications
- Limited refunds for ICANN-initiated withdrawals
- Objection fees refunded if objection succeeds
- Evaluation fees non-refundable regardless of outcome

FINANCIAL ASSISTANCE:
- Reduced fees for developing economy applicants
- Payment plan options available
- Community-based application discounts
- Pro bono support for qualifying applicants

The total cost of string evaluation can range from $185,000 for straightforward applications to over $500,000 for complex applications facing multiple objections and extended evaluation procedures.''',
            'content_type': 'section'
        }
    ]

def test_string_evaluation_embeddings():
    """Test the embedding system with string evaluation focused content"""
    
    logger.info("🧪 Starting String Evaluation Embeddings Test")
    
    # Create test data
    test_sections = create_string_evaluation_test_data()
    logger.info(f"Created {len(test_sections)} test sections focused on string evaluation")
    
    # Initialize populator
    populator = GuidebookEmbeddingsPopulator()
    
    # Save test data to database
    logger.info("💾 Saving test data to database...")
    saved_count = populator.save_to_database(test_sections)
    
    if saved_count == 0:
        logger.error("❌ Failed to save any test data")
        return False
    
    logger.info(f"✅ Successfully saved {saved_count}/{len(test_sections)} sections")
    
    # Test semantic search
    logger.info("🔍 Testing semantic search capabilities...")
    searcher = GuidebookSearcher()
    
    # Test queries focused on string evaluation
    test_queries = [
        "string similarity review process",
        "visual similarity criteria for TLD strings",
        "reserved names and protected strings",
        "IDN internationalized domain name requirements",
        "geographic string evaluation government support",
        "string contention resolution auction process",
        "confusingly similar strings evaluation",
        "string evaluation fees and costs"
    ]
    
    search_results = {}
    for query in test_queries:
        logger.info(f"🔍 Testing query: '{query}'")
        results = searcher.semantic_search(query, similarity_threshold=0.50, max_results=3)
        search_results[query] = results
        
        if results:
            logger.info(f"  ✅ Found {len(results)} results")
            for i, result in enumerate(results, 1):
                similarity = result.get('similarity_score', 0)
                section = result.get('section_number', 'Unknown')
                title = result.get('section_title', 'Unknown')[:50]
                logger.info(f"    {i}. [{section}] {title}... (similarity: {similarity})")
        else:
            logger.warning(f"  ⚠️ No results found for query: '{query}'")
    
    # Test TLD-specific context
    logger.info("🎯 Testing TLD evaluation context...")
    tld_context = searcher.get_context_for_tld_evaluation(
        tld_string="example",
        use_case="technology platform",
        evaluation_topics=["string similarity", "reserved names", "visual confusion"]
    )
    
    if tld_context:
        logger.info(f"✅ Found {len(tld_context)} context sections for TLD evaluation")
        for result in tld_context:
            section = result.get('section_number', 'Unknown')
            title = result.get('section_title', 'Unknown')[:40]
            logger.info(f"  📄 [{section}] {title}...")
    else:
        logger.warning("⚠️ No TLD evaluation context found")
    
    # Test topic classification
    logger.info("🏷️ Analyzing topic classification...")
    topic_counts = {}
    
    for query, results in search_results.items():
        for result in results:
            topics = result.get('topic_tags', [])
            for topic in topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    logger.info("📊 Topic tag distribution:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {topic}: {count} occurrences")
    
    # Generate summary report
    generate_test_report(search_results, tld_context, topic_counts)
    
    logger.info("🎉 String evaluation embeddings test completed!")
    return True

def generate_test_report(search_results: Dict, tld_context: List, topic_counts: Dict):
    """Generate a detailed test report"""
    
    report = {
        "test_summary": {
            "total_queries_tested": len(search_results),
            "queries_with_results": len([q for q, r in search_results.items() if r]),
            "total_search_results": sum(len(results) for results in search_results.values()),
            "tld_context_sections": len(tld_context),
            "unique_topics_found": len(topic_counts)
        },
        "query_results": {},
        "topic_analysis": topic_counts,
        "recommendations": []
    }
    
    # Analyze each query
    for query, results in search_results.items():
        report["query_results"][query] = {
            "result_count": len(results),
            "avg_similarity": sum(r.get('similarity_score', 0) for r in results) / len(results) if results else 0,
            "top_section": results[0].get('section_number') if results else None,
            "top_similarity": results[0].get('similarity_score') if results else 0
        }
    
    # Generate recommendations
    if report["test_summary"]["queries_with_results"] < len(search_results):
        report["recommendations"].append("Some queries returned no results - consider lowering similarity threshold")
    
    if report["test_summary"]["unique_topics_found"] < 5:
        report["recommendations"].append("Limited topic diversity - enhance topic classification logic")
    
    valid_similarities = [data["avg_similarity"] for data in report["query_results"].values() if data["avg_similarity"] > 0]
    avg_similarity = sum(valid_similarities) / len(valid_similarities) if valid_similarities else 0
    
    if avg_similarity < 0.80:
        report["recommendations"].append(f"Average similarity score is {avg_similarity:.3f} - consider improving embedding quality")
    
    # Save report
    report_path = "string_evaluation_embeddings_test_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"📋 Test report saved to: {report_path}")
    
    # Print key metrics
    print("\n" + "="*60)
    print("🧪 STRING EVALUATION EMBEDDINGS TEST RESULTS")
    print("="*60)
    print(f"✅ Queries tested: {report['test_summary']['total_queries_tested']}")
    print(f"✅ Successful queries: {report['test_summary']['queries_with_results']}")
    print(f"✅ Total results: {report['test_summary']['total_search_results']}")
    print(f"✅ TLD context sections: {report['test_summary']['tld_context_sections']}")
    print(f"✅ Average similarity: {avg_similarity:.3f}")
    print("\n🏷️ Top Topics:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {topic}: {count}")
    
    if report["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in report["recommendations"]:
            print(f"   • {rec}")
    
    print("\n" + "="*60)

def main():
    """Main test execution"""
    try:
        success = test_string_evaluation_embeddings()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
