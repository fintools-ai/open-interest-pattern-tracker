"""
Main Orchestrator - Daily OI Pattern Analysis Workflow
Coordinates all components to generate trading signals and dashboards
"""

import asyncio
from datetime import datetime

# Import all components
from data_pipeline.collector import EnhancedOIDataCollector
from data_pipeline.redis_manager import RedisManager
from data_pipeline.delta_calculator import DeltaCalculator
from data_pipeline.market_context import MarketContextProvider
from analysis.llm_analyzer import LLMAnalyzer
from analysis.clustering_engine import ClusteringEngine
from output.html_generator import HTMLGenerator
import json

class OIPatternTracker:
    def __init__(self):
        # Initialize all components
        self.collector = EnhancedOIDataCollector()
        self.redis_manager = RedisManager()
        self.delta_calculator = DeltaCalculator()
        self.market_context_provider = MarketContextProvider()
        self.llm_analyzer = LLMAnalyzer()
        self.clustering_engine = ClusteringEngine()
        self.html_generator = HTMLGenerator()
        
        print("OI Pattern Tracker initialized")
    
    async def run_daily_analysis(self):
        """Execute complete daily analysis workflow"""
        start_time = datetime.now()
        print(f"\nStarting daily OI analysis at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Phase 1: Data Collection
            print("\nPhase 1: Data Collection")
            collection_results = await self.collector.collect_all_tickers()
            
            ticker_data = collection_results["data"]
            summary = collection_results["summary"]
            print(f"Collected data for {summary['successful']}/{summary['total_processed']} tickers")
            
            # Phase 2: Market Context
            print("\nPhase 2: Market Context Analysis")
            market_context = await self.market_context_provider.get_market_context()
            if market_context:
                print(f"Market context: {market_context['regime']} regime, {market_context['fear_level']} fear")
            else:
                print("Market context unavailable - proceeding without")
            
            # Phase 3: Delta Calculation & Storage
            print("\nPhase 3: Delta Calculation & Redis Storage")
            today = datetime.now().strftime('%Y-%m-%d')
            
            processed_tickers = []
            for ticker, data in ticker_data.items():
                oi_data = data.get("oi_data")
                market_data = data.get("market_data")
                
                if oi_data:
                    # Store current OI data in Redis
                    self.redis_manager.store_oi_data(ticker, today, oi_data)
                    
                    # Calculate deltas
                    previous_data = self.redis_manager.get_previous_oi_data(ticker, days_back=1)
                    print(f"  {ticker}: Previous data available: {'Yes' if previous_data else 'No'}")
                    
                    delta_data = self.delta_calculator.calculate_deltas(oi_data, previous_data, ticker)
                    
                    # Log delta calculation results
                    if delta_data.get("is_baseline"):
                        print(f"  {ticker}: Delta baseline created (first run)")
                    elif delta_data.get("error"):
                        print(f"  {ticker}: Delta calculation error: {delta_data['error']}")
                    else:
                        # Log key delta metrics
                        pcr_delta = delta_data.get("put_call_ratio_delta", 0)
                        max_pain_shift = delta_data.get("max_pain_shift", 0)
                        total_oi_change = delta_data.get("total_oi_change", 0)
                        print(f"  {ticker}: P/C Δ: {pcr_delta:.3f}, Max Pain Δ: ${max_pain_shift:.2f}, OI Δ: {total_oi_change}")
                    
                    # Store delta data
                    self.redis_manager.store_delta_data(ticker, today, delta_data)
                    
                    # Create ticker result for analysis
                    processed_tickers.append({
                        "ticker": ticker,
                        "oi_data": oi_data,
                        "delta": delta_data,
                        "market_data": market_data
                    })
                else:
                    print(f"  Warning: No OI data for {ticker}")
                    # Create empty delta with proper structure for LLM
                    empty_delta = {
                        "ticker": ticker,
                        "message": "No OI data available for delta calculation",
                        "is_baseline": True,
                        "put_call_ratio_delta": 0,
                        "max_pain_shift": 0,
                        "total_oi_change": 0,
                        "call_oi_change": 0,
                        "put_oi_change": 0
                    }
                    processed_tickers.append({
                        "ticker": ticker,
                        "oi_data": {},
                        "delta": empty_delta,
                        "market_data": market_data
                    })
            
            print(f"Calculated deltas and stored data for {len(processed_tickers)} tickers")
            
            # Phase 4: LLM Analysis
            print("\nPhase 4: Enhanced LLM Analysis with Price Context")
            analyses = []
            
            # Process all tickers with enhanced price data


            for ticker_result in processed_tickers:
                ticker = ticker_result["ticker"]
                print(f"  Analyzing {ticker}...")
                
                # Only analyze if we have OI data
                if ticker_result.get("oi_data"):
                    print(f"    OI data keys: {list(ticker_result['oi_data'].keys())}")
                    analysis = self.llm_analyzer.analyze_ticker(
                        ticker_result["oi_data"],
                        ticker_result["delta"],
                        market_context,
                        ticker_result.get("market_data")  # Pass market data with prices
                    )
                    print(f"    Analysis result: {(analysis)}")
                    
                    # Log if we have price enhancement
                    if ticker_result.get("market_data") and ticker_result["market_data"].get("current_price"):
                        print(f"    Enhanced with price: ${ticker_result['market_data']['current_price']}")
                else:
                    analysis = {
                        "ticker": ticker,
                        "status": "error",
                        "error": "No OI data available"
                    }
                
                analyses.append(analysis)
                print(f"    Analysis status: {analysis.get('status', 'unknown')}")
                if analysis.get('status') == 'error':
                    print(f"    Error: {analysis.get('error', 'unknown')}")
                
                # Store analysis result
                self.redis_manager.store_analysis_result(ticker, today, analysis)
            
            print(f"Completed LLM analysis for {len(analyses)} tickers")
            
            print("--------")
            print(json.dumps(analyses, indent=2))
            print("--------")
            # Phase 5: Clustering
            print("\nPhase 5: Pattern Clustering")
            clusters = self.clustering_engine.cluster_analyses(analyses)
            
            bullish_count = clusters["bullish_group"]["total_count"]
            bearish_count = clusters["bearish_group"]["total_count"]
            
            print(f"Clustering complete:")
            print(f"   Bullish signals: {bullish_count}")
            print(f"   Bearish signals: {bearish_count}")
            print(f"   Total signals: {bullish_count + bearish_count}")
            
            if bullish_count + bearish_count > 0:
                avg_success_rate = (
                    clusters["bullish_group"]["avg_success_probability"] + 
                    clusters["bearish_group"]["avg_success_probability"]
                ) / 2
                print(f"   Average success probability: {avg_success_rate:.1f}%")
            
            # Phase 6: Output Generation
            print("\nPhase 6: Dashboard & Report Generation")
            
            # Generate HTML dashboard
            dashboard_path = self.html_generator.generate_daily_dashboard(clusters, market_context)
            if dashboard_path:
                print(f"HTML dashboard: {dashboard_path}")
            
            # Generate JSON reports
            json_reports = self.html_generator.generate_json_reports(clusters, analyses)
            if json_reports:
                print(f"JSON reports: {len(json_reports)} files generated")
            
            # Phase 7: Summary
            end_time = datetime.now()
            duration = end_time - start_time
            
            print(f"\nDaily analysis complete!")
            print(f"Total processing time: {duration}")
            print(f"Analysis summary:")
            print(f"   • {len(processed_tickers)} tickers processed")
            print(f"   • {bullish_count + bearish_count} trading signals generated")
            print(f"   • Market bias: {clusters['summary']['market_bias']}")
            
            if bullish_count + bearish_count > 0:
                print(f"   • Top pattern: {clusters['summary']['dominant_patterns']}")
            
            return {
                "status": "success",
                "processed_tickers": len(processed_tickers),
                "bullish_signals": bullish_count,
                "bearish_signals": bearish_count,
                "dashboard_path": dashboard_path,
                "json_reports": json_reports,
                "duration": str(duration),
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            error_time = datetime.now()
            duration = error_time - start_time
            
            print(f"\nAnalysis failed after {duration}")
            print(f"Error: {str(e)}")
            
            return {
                "status": "error",
                "error": str(e),
                "duration": str(duration),
                "timestamp": error_time.isoformat()
            }

async def main():
    """Main entry point"""
    tracker = OIPatternTracker()
    result = await tracker.run_daily_analysis()
    
    if result["status"] == "success":
        print("\nOI Pattern Tracker execution successful!")
        if result.get("dashboard_path"):
            print(f"View dashboard: {result['dashboard_path']}")
    else:
        print(f"\nExecution failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())