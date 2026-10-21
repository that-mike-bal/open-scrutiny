"""
Use Case Driven Evaluation Store

Database operations for the new multi-stage workflow:
1. Use Case Discovery (StrategicIdeationAgent)
2. Parallel Business Case Analysis (Business Case Agents)  
3. Portfolio Strategy Synthesis (PortfolioStrategyAgent)

This store integrates with the comprehensive schema in schema.sql
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

from db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

class UseCaseDrivenStore:
    """Database operations for use case driven evaluation workflow"""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    # =====================================================
    # MAIN EVALUATION LIFECYCLE OPERATIONS
    # =====================================================
    
    async def create_evaluation(
        self, 
        user_id: str, 
        tld_string: str, 
        workflow_type: str = "use_case_driven"
    ) -> str:
        """
        Create a new TLD evaluation record
        
        Returns:
            str: Evaluation ID (UUID)
        """
        try:
            evaluation_data = {
                "user_id": user_id,
                "tld_string": tld_string.lower(),
                "status": "PENDING",
                "workflow_type": workflow_type,
                "created_at": datetime.utcnow().isoformat(),
                "workflow_metadata": {}
            }
            
            result = self.supabase.table("tld_evaluations").insert(evaluation_data).execute()
            
            if result.data:
                evaluation_id = result.data[0]["id"]
                logger.info(f"Created TLD evaluation {evaluation_id} for {tld_string}")
                return evaluation_id
            else:
                raise Exception("Failed to create evaluation record")
                
        except Exception as e:
            logger.error(f"Error creating evaluation: {e}")
            raise
    
    async def update_evaluation_status(
        self, 
        evaluation_id: str, 
        status: str,
        stage: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update evaluation status and optional error info"""
        try:
            update_data = {"status": status}
            
            if status == "RUNNING" and stage:
                update_data["started_at"] = datetime.utcnow().isoformat()
                update_data["error_stage"] = stage
            elif status == "COMPLETED":
                update_data["completed_at"] = datetime.utcnow().isoformat()
            elif status == "FAILED":
                update_data["error_message"] = error_message
                if stage:
                    update_data["error_stage"] = stage
            
            result = self.supabase.table("tld_evaluations").update(update_data).eq("id", evaluation_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating evaluation status: {e}")
            raise
    
    async def save_discovery_results(
        self, 
        evaluation_id: str, 
        discovery_results: Dict[str, Any]
    ) -> bool:
        """Save the results from Stage 1: Use Case Discovery"""
        try:
            update_data = {
                "discovery_results": discovery_results,
                "workflow_metadata": {
                    "discovery_completed_at": datetime.utcnow().isoformat(),
                    "discovered_use_cases_count": len(discovery_results.get("discovered_use_cases", [])),
                    "selected_for_analysis_count": len(discovery_results.get("selected_for_analysis", []))
                }
            }
            
            result = self.supabase.table("tld_evaluations").update(update_data).eq("id", evaluation_id).execute()
            
            # Create use case analysis records for each selected use case
            if "selected_for_analysis" in discovery_results:
                await self._create_use_case_analysis_records(evaluation_id, discovery_results["selected_for_analysis"])
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error saving discovery results: {e}")
            raise
    
    async def save_portfolio_strategy(
        self, 
        evaluation_id: str, 
        portfolio_strategy: Dict[str, Any]
    ) -> bool:
        """Save the results from Stage 3: Portfolio Strategy Synthesis"""
        try:
            strategy_data = {
                "tld_evaluation_id": evaluation_id,
                "primary_strategy_type": portfolio_strategy.get("primary_strategy", "Single Use Case Focus"),
                "recommended_use_cases": portfolio_strategy.get("recommended_use_cases", []),
                "strategic_rationale": portfolio_strategy.get("strategic_rationale", ""),
                "implementation_phases": portfolio_strategy.get("implementation_timeline", {}),
                "portfolio_analysis_summary": portfolio_strategy.get("portfolio_analysis", {}),
                "individual_use_case_rankings": portfolio_strategy.get("use_case_rankings", {}),
                "total_use_cases_analyzed": len(portfolio_strategy.get("use_case_analyses", [])),
                "confidence_level": portfolio_strategy.get("confidence_level", "MEDIUM"),
                "recommendation_strength": portfolio_strategy.get("recommendation_strength", "MODERATE"),
                "full_synthesis_report": portfolio_strategy,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("portfolio_strategies").insert(strategy_data).execute()
            
            # Update main evaluation with final recommendation
            final_recommendation = {
                "recommended_use_case": portfolio_strategy.get("recommended_use_case"),
                "strategic_rationale": portfolio_strategy.get("strategic_rationale"),
                "implementation_timeline": portfolio_strategy.get("implementation_timeline"),
                "confidence_level": portfolio_strategy.get("confidence_level", "MEDIUM")
            }
            
            await self.supabase.table("tld_evaluations").update({
                "final_recommendation": final_recommendation
            }).eq("id", evaluation_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error saving portfolio strategy: {e}")
            raise
    
    # =====================================================
    # USE CASE ANALYSIS OPERATIONS
    # =====================================================
    
    async def _create_use_case_analysis_records(
        self, 
        evaluation_id: str, 
        selected_use_cases: List[str]
    ) -> List[str]:
        """Create analysis records for each selected use case"""
        try:
            analysis_records = []
            for rank, use_case in enumerate(selected_use_cases, 1):
                record = {
                    "tld_evaluation_id": evaluation_id,
                    "use_case": use_case,
                    "use_case_rank": rank,
                    "status": "PENDING",
                    "created_at": datetime.utcnow().isoformat()
                }
                analysis_records.append(record)
            
            result = self.supabase.table("use_case_analyses").insert(analysis_records).execute()
            
            return [record["id"] for record in result.data]
            
        except Exception as e:
            logger.error(f"Error creating use case analysis records: {e}")
            raise
    
    async def update_use_case_analysis(
        self, 
        evaluation_id: str,
        use_case: str,
        business_case_report: Dict[str, Any]
    ) -> bool:
        """Save business case analysis results for a specific use case"""
        try:
            # Extract key metrics for easy querying
            metrics = self._extract_business_metrics(business_case_report)
            insights = self._extract_business_insights(business_case_report)
            
            update_data = {
                "status": "COMPLETED",
                "completed_at": datetime.utcnow().isoformat(),
                "full_report": business_case_report,
                
                # Core scores
                "overall_business_score": metrics.get("overall_business_potential_score", 0),
                "market_potential_score": metrics.get("market_opportunity_score", 0),
                "financial_viability_score": metrics.get("financial_viability_score", 0),
                "competitive_position_score": metrics.get("competitive_position_score", 0),
                "risk_score": 100 - metrics.get("risk_adjusted_score", 50),  # Invert for risk
                
                # Business recommendation
                "final_recommendation_category": self._determine_recommendation_category(
                    metrics.get("overall_business_potential_score", 0)
                ),
                "confidence_level": business_case_report.get("confidence_level", "MEDIUM"),
                
                # Financial projections
                "estimated_revenue_y1_usd": metrics.get("estimated_revenue_y1_usd"),
                "estimated_revenue_y5_usd": metrics.get("estimated_revenue_y5_usd"),
                "break_even_registrations": metrics.get("break_even_registrations"),
                "break_even_timeframe_months": metrics.get("break_even_timeframe_months"),
                "roi_projection_percent": metrics.get("roi_projection_percent"),
                "estimated_investment_usd": metrics.get("estimated_total_investment_usd"),
                
                # Market metrics
                "estimated_market_size_usd": metrics.get("estimated_market_size_usd"),
                "projected_registrations_y1": metrics.get("projected_registration_volume_y1"),
                "projected_registrations_y5": metrics.get("projected_registration_volume_y5"),
                "market_growth_rate_percent": metrics.get("market_growth_rate_percent"),
                
                # Risk assessment
                "overall_risk_level": metrics.get("overall_risk_level", "UNKNOWN"),
                "regulatory_risk_score": metrics.get("regulatory_risk_score", 0),
                "market_risk_score": metrics.get("market_risk_score", 0),
                "operational_risk_score": metrics.get("operational_risk_score", 0)
            }
            
            result = self.supabase.table("use_case_analyses").update(update_data).eq(
                "tld_evaluation_id", evaluation_id
            ).eq("use_case", use_case).execute()
            
            # Save detailed metrics and insights in separate tables
            if result.data:
                analysis_id = result.data[0]["id"]
                await self._save_detailed_business_metrics(analysis_id, metrics)
                await self._save_detailed_business_insights(analysis_id, insights)
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating use case analysis: {e}")
            raise
    
    async def _save_detailed_business_metrics(
        self, 
        analysis_id: str, 
        metrics: Dict[str, Any]
    ) -> bool:
        """Save detailed business metrics in separate table for analytics"""
        try:
            metrics_data = {
                "use_case_analysis_id": analysis_id,
                "created_at": datetime.utcnow().isoformat(),
                
                # Market metrics
                "market_opportunity_score": metrics.get("market_opportunity_score", 0),
                "estimated_market_size_usd": metrics.get("estimated_market_size_usd"),
                "market_growth_rate_percent": metrics.get("market_growth_rate_percent"),
                "target_market_segments": [],  # Will be extracted from insights
                
                # Competitive metrics
                "competitive_position_score": metrics.get("competitive_position_score", 0),
                "direct_competitors_count": metrics.get("direct_competitors_count", 0),
                "competitive_advantage_score": metrics.get("competitive_advantage_score", 0),
                "market_differentiation_score": metrics.get("market_differentiation_score", 0),
                
                # Financial metrics
                "financial_viability_score": metrics.get("financial_viability_score", 0),
                "estimated_total_investment_usd": metrics.get("estimated_total_investment_usd"),
                "estimated_annual_operating_cost_usd": metrics.get("estimated_annual_operating_cost_usd"),
                "estimated_time_to_market_months": metrics.get("estimated_time_to_market_months"),
                
                # Risk metrics
                "risk_adjusted_score": metrics.get("risk_adjusted_score", 0),
                "primary_risks_identified": [],  # Will be extracted from insights
                "risk_mitigation_strategies": [],  # Will be extracted from insights
                
                # Additional data
                "key_success_factors": [],  # Will be extracted from insights
                "critical_assumptions": [],  # Will be extracted from insights
                "data_quality_score": 75  # Default score, could be calculated
            }
            
            result = self.supabase.table("business_metrics").insert(metrics_data).execute()
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error saving detailed business metrics: {e}")
            return False
    
    async def _save_detailed_business_insights(
        self, 
        analysis_id: str, 
        insights: Dict[str, Any]
    ) -> bool:
        """Save detailed business insights in separate table for analytics"""
        try:
            insights_data = {
                "use_case_analysis_id": analysis_id,
                "created_at": datetime.utcnow().isoformat(),
                
                # Market intelligence insights
                "relevant_trends": insights.get("relevant_trends", []),
                "market_drivers": insights.get("market_drivers", []),
                "target_market_analysis": insights.get("target_market_analysis", ""),
                "demand_indicators": insights.get("demand_indicators", []),
                
                # Competitive landscape
                "competitive_positioning": insights.get("competitive_positioning", ""),
                "key_competitors": insights.get("key_competitors", []),
                "competitive_advantages": insights.get("competitive_advantages", []),
                "market_gaps_identified": insights.get("market_gaps_identified", []),
                
                # Adoption assessment
                "adoption_drivers": insights.get("adoption_drivers", []),
                "adoption_barriers": insights.get("adoption_barriers", []),
                "adoption_timeline_assessment": insights.get("adoption_timeline_assessment", ""),
                "early_adopter_segments": insights.get("early_adopter_segments", []),
                
                # Supporting data
                "data_sources_consulted": insights.get("data_sources_consulted", []),
                "key_research_findings": insights.get("key_research_findings", []),
                "benchmark_comparisons": insights.get("benchmark_comparisons", []),
                "expert_opinions": insights.get("expert_opinions", []),
                
                # Risk assessment
                "primary_risks_identified": insights.get("primary_risks_identified", []),
                "risk_mitigation_strategies": insights.get("risk_mitigation_strategies", []),
                "contingency_planning": insights.get("contingency_planning", []),
                "black_swan_scenarios": insights.get("black_swan_scenarios", []),
                
                # Strategic recommendations
                "go_to_market_strategy": insights.get("go_to_market_strategy", ""),
                "pricing_strategy_recommendations": insights.get("pricing_strategy_recommendations", []),
                "partnership_opportunities": insights.get("partnership_opportunities", []),
                "marketing_strategy_recommendations": insights.get("marketing_strategy_recommendations", []),
                
                # Success factors
                "critical_success_factors": insights.get("critical_success_factors", []),
                "key_performance_indicators": insights.get("key_performance_indicators", []),
                "milestone_recommendations": insights.get("milestone_recommendations", []),
                
                # Investment considerations
                "funding_requirements": insights.get("funding_requirements", ""),
                "investment_risks": insights.get("investment_risks", []),
                "return_expectations": insights.get("return_expectations", ""),
                "exit_strategy_considerations": insights.get("exit_strategy_considerations", [])
            }
            
            result = self.supabase.table("business_insights").insert(insights_data).execute()
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error saving detailed business insights: {e}")
            return False
    
    # =====================================================
    # QUERY AND RETRIEVAL OPERATIONS
    # =====================================================
    
    async def get_evaluation_by_id(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """Get complete evaluation data by ID"""
        try:
            # Get main evaluation record
            eval_result = self.supabase.table("tld_evaluations").select("*").eq("id", evaluation_id).execute()
            
            if not eval_result.data:
                return None
            
            evaluation = eval_result.data[0]
            
            # Get use case analyses
            analysis_result = self.supabase.table("use_case_analyses").select("*").eq(
                "tld_evaluation_id", evaluation_id
            ).order("use_case_rank").execute()
            
            # Get portfolio strategy
            strategy_result = self.supabase.table("portfolio_strategies").select("*").eq(
                "tld_evaluation_id", evaluation_id
            ).execute()
            
            # Combine all data
            evaluation["use_case_analyses"] = analysis_result.data
            evaluation["portfolio_strategy"] = strategy_result.data[0] if strategy_result.data else None
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error getting evaluation by ID: {e}")
            return None
    
    async def get_evaluations_by_user(
        self, 
        user_id: str, 
        limit: int = 50,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all evaluations for a specific user"""
        try:
            query = self.supabase.table("tld_evaluations").select("*").eq("user_id", user_id)
            
            if status_filter:
                query = query.eq("status", status_filter)
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting evaluations by user: {e}")
            return []
    
    async def get_evaluations_by_tld(self, tld_string: str) -> List[Dict[str, Any]]:
        """Get all evaluations for a specific TLD string"""
        try:
            result = self.supabase.table("tld_evaluations").select("*").eq(
                "tld_string", tld_string.lower()
            ).order("created_at", desc=True).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting evaluations by TLD: {e}")
            return []
    
    async def search_evaluations(
        self, 
        search_query: str, 
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search evaluations by TLD string or use case content"""
        try:
            query = self.supabase.table("tld_evaluations").select("*")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            # Use ilike for case-insensitive search
            query = query.or_(f"tld_string.ilike.%{search_query}%")
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error searching evaluations: {e}")
            return []
    
    # =====================================================
    # ANALYTICS AND REPORTING OPERATIONS
    # =====================================================
    
    async def get_portfolio_comparison_data(
        self, 
        evaluation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get structured data for portfolio comparison UI"""
        try:
            evaluation = await self.get_evaluation_by_id(evaluation_id)
            
            if not evaluation or not evaluation.get("use_case_analyses"):
                return None
            
            # Build comparison data structure
            comparison_data = {
                "tld_string": evaluation["tld_string"],
                "evaluation_status": evaluation["status"],
                "total_use_cases": len(evaluation["use_case_analyses"]),
                "use_case_comparisons": [],
                "portfolio_recommendation": evaluation.get("final_recommendation"),
                "portfolio_strategy": evaluation.get("portfolio_strategy")
            }
            
            # Process each use case analysis
            for analysis in evaluation["use_case_analyses"]:
                use_case_data = {
                    "use_case": analysis["use_case"],
                    "rank": analysis["use_case_rank"],
                    "overall_score": analysis["overall_business_score"],
                    "market_score": analysis["market_potential_score"],
                    "financial_score": analysis["financial_viability_score"],
                    "competitive_score": analysis["competitive_position_score"],
                    "risk_score": analysis["risk_score"],
                    "recommendation": analysis["final_recommendation_category"],
                    "confidence": analysis["confidence_level"],
                    
                    # Financial highlights
                    "revenue_y1": analysis["estimated_revenue_y1_usd"],
                    "revenue_y5": analysis["estimated_revenue_y5_usd"],
                    "investment_required": analysis["estimated_investment_usd"],
                    "break_even_months": analysis["break_even_timeframe_months"],
                    "roi_projection": analysis["roi_projection_percent"],
                    
                    # Market highlights
                    "market_size": analysis["estimated_market_size_usd"],
                    "registrations_y1": analysis["projected_registrations_y1"],
                    "registrations_y5": analysis["projected_registrations_y5"],
                    "growth_rate": analysis["market_growth_rate_percent"],
                    
                    # Risk assessment
                    "risk_level": analysis["overall_risk_level"],
                    "regulatory_risk": analysis["regulatory_risk_score"],
                    "market_risk": analysis["market_risk_score"],
                    "operational_risk": analysis["operational_risk_score"]
                }
                
                comparison_data["use_case_comparisons"].append(use_case_data)
            
            # Sort by overall score descending
            comparison_data["use_case_comparisons"].sort(
                key=lambda x: x["overall_score"], reverse=True
            )
            
            return comparison_data
            
        except Exception as e:
            logger.error(f"Error getting portfolio comparison data: {e}")
            return None
    
    async def get_dashboard_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics data for dashboard"""
        try:
            # Get evaluation counts by status
            status_counts = {}
            status_result = self.supabase.table("tld_evaluations").select(
                "status", count="exact"
            ).eq("user_id", user_id).execute()
            
            # Get recent evaluations
            recent_result = self.supabase.table("tld_evaluations").select("*").eq(
                "user_id", user_id
            ).order("created_at", desc=True).limit(10).execute()
            
            # Get top performing use cases
            top_use_cases_result = self.supabase.table("use_case_analyses").select(
                "use_case, overall_business_score, final_recommendation_category"
            ).order("overall_business_score", desc=True).limit(10).execute()
            
            return {
                "total_evaluations": len(recent_result.data),
                "status_breakdown": status_counts,
                "recent_evaluations": recent_result.data,
                "top_performing_use_cases": top_use_cases_result.data,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard analytics: {e}")
            return {}
    
    # =====================================================
    # UTILITY METHODS
    # =====================================================
    
    def _extract_business_metrics(self, business_case_report: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured metrics from business case report"""
        # This would extract metrics from various sections of the business case report
        # For now, return basic structure - this should be enhanced based on actual report format
        return business_case_report.get("metrics", {})
    
    def _extract_business_insights(self, business_case_report: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured insights from business case report"""
        return business_case_report.get("insights", {})
    
    def _determine_recommendation_category(self, overall_score: int) -> str:
        """Convert overall business score to recommendation category"""
        if overall_score >= 90:
            return "HIGHLY_RECOMMENDED"
        elif overall_score >= 75:
            return "RECOMMENDED"
        elif overall_score >= 50:
            return "PROCEED_WITH_CAUTION"
        else:
            return "NOT_RECOMMENDED"

# Create global instance
use_case_driven_store = UseCaseDrivenStore() 