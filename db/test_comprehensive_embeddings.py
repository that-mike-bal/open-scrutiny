#!/usr/bin/env python3
"""
Comprehensive Embeddings Test

Test the complete embeddings system including:
- ICANN Guidebook content
- Application questions  
- External resources
- Unified search capabilities
- Question context generation
- TLD evaluation support

Usage:
    python db/test_comprehensive_embeddings.py
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.unified_search import UnifiedSearcher, SearchResultType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_unified_search():
    """Test unified search across all knowledge sources"""
    logger.info("🔍 Testing Unified Search Capabilities")
    
    searcher = UnifiedSearcher()
    
    test_queries = [
        "string similarity evaluation criteria",
        "technical infrastructure requirements",
        "DNS stability and performance",
        "financial capability assessment", 
        "registry operations procedures",
        "trademark protection mechanisms",
        "geographic string evaluation",
        "IDN internationalized domain names"
    ]
    
    all_results = {}
    
    for query in test_queries:
        logger.info(f"🔍 Testing query: '{query}'")
        
        results = searcher.search_all(query, max_results=5)
        all_results[query] = results
        
        if results:
            logger.info(f"  ✅ Found {len(results)} results")
            
            # Categorize results by type
            by_type = {}
            for result in results:
                result_type = result.type.value
                if result_type not in by_type:
                    by_type[result_type] = []
                by_type[result_type].append(result)
            
            for result_type, type_results in by_type.items():
                logger.info(f"    📄 {result_type.upper()}: {len(type_results)} results")
                for result in type_results[:2]:  # Show top 2
                    logger.info(f"      - {result.title} (similarity: {result.similarity_score})")
        else:
            logger.warning(f"  ⚠️ No results found for query: '{query}'")
        
        print()  # Add spacing
    
    return all_results

def test_question_context():
    """Test comprehensive question context generation"""
    logger.info("🎯 Testing Question Context Generation")
    
    searcher = UnifiedSearcher()
    
    test_questions = ["18a", "19.1", "20.1", "21.1"]
    
    question_contexts = {}
    
    for question_number in test_questions:
        logger.info(f"🎯 Getting context for question {question_number}")
        
        context = searcher.search_for_question_context(question_number, max_results=3)
        question_contexts[question_number] = context
        
        if context:
            for category, results in context.items():
                if results:
                    logger.info(f"  📚 {category.upper()}: {len(results)} results")
                    for result in results:
                        logger.info(f"    - {result.title} (similarity: {result.similarity_score})")
                else:
                    logger.info(f"  📚 {category.upper()}: No results")
        else:
            logger.warning(f"  ⚠️ No context found for question {question_number}")
        
        print()  # Add spacing
    
    return question_contexts

def test_tld_evaluation_context():
    """Test TLD evaluation context generation"""
    logger.info("🎯 Testing TLD Evaluation Context")
    
    searcher = UnifiedSearcher()
    
    test_cases = [
        {
            'tld_string': 'tech',
            'intended_use': 'technology platform',
            'evaluation_areas': ['string similarity', 'dns stability', 'technical requirements']
        },
        {
            'tld_string': 'bank',
            'intended_use': 'financial services',
            'evaluation_areas': ['reserved names', 'trademark protection', 'security requirements']
        },
        {
            'tld_string': 'city',
            'intended_use': 'geographic community',
            'evaluation_areas': ['geographic evaluation', 'government support', 'community benefit']
        }
    ]
    
    tld_contexts = {}
    
    for test_case in test_cases:
        tld_string = test_case['tld_string']
        logger.info(f"🎯 Getting evaluation context for .{tld_string}")
        
        context = searcher.search_for_tld_evaluation(
            tld_string=tld_string,
            intended_use=test_case['intended_use'],
            evaluation_areas=test_case['evaluation_areas'],
            max_results=3
        )
        tld_contexts[tld_string] = context
        
        if context:
            for category, results in context.items():
                if results and category != 'all_results':  # Skip the combined results for cleaner output
                    logger.info(f"  📚 {category.upper()}: {len(results)} results")
                    for result in results:
                        logger.info(f"    - {result.title} (similarity: {result.similarity_score})")
        else:
            logger.warning(f"  ⚠️ No evaluation context found for .{tld_string}")
        
        print()  # Add spacing
    
    return tld_contexts

def test_source_coverage():
    """Test coverage across different knowledge sources"""
    logger.info("📊 Testing Knowledge Source Coverage")
    
    searcher = UnifiedSearcher()
    
    # Test each source type individually
    source_tests = [
        (SearchResultType.GUIDEBOOK, "ICANN guidebook policy content"),
        (SearchResultType.QUESTION, "application question requirements"),
        (SearchResultType.RESOURCE, "external technical specifications")
    ]
    
    coverage_results = {}
    
    for result_type, test_query in source_tests:
        logger.info(f"📊 Testing {result_type.value.upper()} source")
        
        results = searcher.search_all(
            query=test_query,
            max_results=5,
            result_types=[result_type]
        )
        
        coverage_results[result_type.value] = len(results)
        
        if results:
            logger.info(f"  ✅ Found {len(results)} {result_type.value} results")
            for result in results[:2]:  # Show top 2
                logger.info(f"    - {result.title} (similarity: {result.similarity_score})")
        else:
            logger.warning(f"  ⚠️ No {result_type.value} results found")
        
        print()
    
    return coverage_results

def generate_comprehensive_report(
    search_results: Dict[str, List],
    question_contexts: Dict[str, Dict],
    tld_contexts: Dict[str, Dict],
    coverage_results: Dict[str, int]
):
    """Generate comprehensive test report"""
    
    report = {
        "test_summary": {
            "total_search_queries": len(search_results),
            "successful_queries": len([q for q, r in search_results.items() if r]),
            "total_search_results": sum(len(results) for results in search_results.values()),
            "questions_tested": len(question_contexts),
            "tld_evaluations_tested": len(tld_contexts),
            "source_coverage": coverage_results
        },
        "search_performance": {},
        "question_context_analysis": {},
        "tld_evaluation_analysis": {},
        "recommendations": []
    }
    
    # Analyze search performance
    for query, results in search_results.items():
        if results:
            avg_similarity = sum(r.similarity_score for r in results) / len(results)
            type_distribution = {}
            for result in results:
                result_type = result.type.value
                type_distribution[result_type] = type_distribution.get(result_type, 0) + 1
            
            report["search_performance"][query] = {
                "result_count": len(results),
                "avg_similarity": round(avg_similarity, 4),
                "type_distribution": type_distribution
            }
    
    # Analyze question contexts
    for question_num, context in question_contexts.items():
        context_stats = {}
        for category, results in context.items():
            context_stats[category] = len(results)
        report["question_context_analysis"][question_num] = context_stats
    
    # Analyze TLD evaluations
    for tld_string, context in tld_contexts.items():
        evaluation_stats = {}
        for category, results in context.items():
            if category != 'all_results':
                evaluation_stats[category] = len(results)
        report["tld_evaluation_analysis"][tld_string] = evaluation_stats
    
    # Generate recommendations
    total_results = report["test_summary"]["total_search_results"]
    if total_results < 20:
        report["recommendations"].append("Consider lowering similarity thresholds to increase result coverage")
    
    if coverage_results.get("guidebook", 0) == 0:
        report["recommendations"].append("No guidebook results found - check guidebook embeddings")
    
    if coverage_results.get("question", 0) == 0:
        report["recommendations"].append("No question results found - check question embeddings")
    
    if coverage_results.get("resource", 0) == 0:
        report["recommendations"].append("No resource results found - check resource embeddings")
    
    successful_rate = report["test_summary"]["successful_queries"] / report["test_summary"]["total_search_queries"]
    if successful_rate < 0.8:
        report["recommendations"].append(f"Low success rate ({successful_rate:.1%}) - consider improving embeddings quality")
    
    # Save report
    report_path = "comprehensive_embeddings_test_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"📋 Comprehensive test report saved to: {report_path}")
    
    # Print summary
    print("\n" + "="*80)
    print("🧪 COMPREHENSIVE EMBEDDINGS TEST RESULTS")
    print("="*80)
    print(f"✅ Search queries tested: {report['test_summary']['total_search_queries']}")
    print(f"✅ Successful queries: {report['test_summary']['successful_queries']}")
    print(f"✅ Total results found: {report['test_summary']['total_search_results']}")
    print(f"✅ Questions with context: {report['test_summary']['questions_tested']}")
    print(f"✅ TLD evaluations tested: {report['test_summary']['tld_evaluations_tested']}")
    
    print(f"\n📊 Source Coverage:")
    for source, count in coverage_results.items():
        print(f"   {source}: {count} results")
    
    if report["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in report["recommendations"]:
            print(f"   • {rec}")
    
    print("\n" + "="*80)
    
    return report

def main():
    """Run comprehensive embeddings test"""
    logger.info("🚀 Starting Comprehensive Embeddings Test")
    
    try:
        # Test unified search
        search_results = test_unified_search()
        
        # Test question context
        question_contexts = test_question_context()
        
        # Test TLD evaluation context  
        tld_contexts = test_tld_evaluation_context()
        
        # Test source coverage
        coverage_results = test_source_coverage()
        
        # Generate comprehensive report
        report = generate_comprehensive_report(
            search_results, question_contexts, tld_contexts, coverage_results
        )
        
        logger.info("🎉 Comprehensive embeddings test completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
