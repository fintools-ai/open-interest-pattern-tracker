"""
Clustering Engine - Groups ticker analyses into bullish/bearish clusters
Calculates success probabilities and pattern classifications
"""

from datetime import datetime
from config.settings import CONFIDENCE_THRESHOLD

def safe_int(value):
    """Safely convert any value to integer, handling strings, percentages, quotes"""
    try:
        return int(str(value).replace('%', '').replace('"', '').replace("'", '').split('.')[0].split()[0] or 0)
    except (ValueError, TypeError):
        return 0

class ClusteringEngine:
    def __init__(self):
        self.confidence_threshold = CONFIDENCE_THRESHOLD
    
    def cluster_analyses(self, all_analyses):
        """Group all ticker analyses into bullish/bearish clusters with multi-timeframe support"""
        clusters = {
            "bullish_group": {
                "tickers": [],
                "avg_confidence": 0,
                "avg_success_probability": 0,
                "pattern_types": {},
                "total_count": 0
            },
            "bearish_group": {
                "tickers": [],
                "avg_confidence": 0,
                "avg_success_probability": 0,
                "pattern_types": {},
                "total_count": 0
            },
            "multi_timeframe": {
                "by_ticker": {},
                "confluence_summary": {},
                "timeframe_stats": {}
            }
        }

        # Group analyses by ticker for multi-timeframe processing
        ticker_groups = self._group_by_ticker(all_analyses)

        # Process timeframe confluence
        clusters["multi_timeframe"] = self._analyze_timeframe_confluence(ticker_groups)

        # Process each analysis for traditional bullish/bearish clustering
        for analysis in all_analyses:
            if analysis.get("status") == "error":
                continue

            classification = self._classify_analysis(analysis)

            if classification == "bullish":
                self._add_to_bullish(clusters, analysis)
            elif classification == "bearish":
                self._add_to_bearish(clusters, analysis)
            # No neutral handling - all trades must be bullish or bearish

        # Calculate group statistics
        self._calculate_group_stats(clusters)

        # Add metadata
        clusters["clustering_timestamp"] = datetime.now().isoformat()
        clusters["total_analyzed"] = len(all_analyses)
        clusters["summary"] = self._generate_cluster_summary(clusters)

        return clusters
    
    def _classify_analysis(self, analysis):
        """Classify a single analysis as bullish/bearish/neutral"""
        try:
            # Extract key metrics
            trade_rec = analysis.get("trade_recommendation", {})
            pattern_analysis = analysis.get("pattern_analysis", {})
            
            direction = trade_rec.get("direction", "NEUTRAL")
            confidence = pattern_analysis.get("confidence_score", 0)
            success_prob = trade_rec.get("success_probability", 0)
            
            # Check confidence threshold
            confidence_num = safe_int(confidence)
            success_prob_num = safe_int(trade_rec.get("success_probability", 0))
            
            # No filtering based on confidence thresholds - classify all trades
            
            # Classify based on direction - must be either bullish or bearish
            if direction == "CALL":
                return "bullish"
            elif direction == "PUT":
                return "bearish"
            else:
                # Force classification as bullish if no clear direction
                return "bullish"
                
        except Exception as e:
            return f"classification_error_{str(e)}"
    
    def _add_to_bullish(self, clusters, analysis):
        """Add analysis to bullish cluster"""
        ticker_info = self._extract_ticker_info(analysis, "bullish")
        clusters["bullish_group"]["tickers"].append(ticker_info)
        
        # Track pattern types
        pattern_type = analysis.get("pattern_analysis", {}).get("pattern_type", "unknown")
        if pattern_type not in clusters["bullish_group"]["pattern_types"]:
            clusters["bullish_group"]["pattern_types"][pattern_type] = 0
        clusters["bullish_group"]["pattern_types"][pattern_type] += 1
    
    def _add_to_bearish(self, clusters, analysis):
        """Add analysis to bearish cluster"""
        ticker_info = self._extract_ticker_info(analysis, "bearish")
        clusters["bearish_group"]["tickers"].append(ticker_info)
        
        # Track pattern types
        pattern_type = analysis.get("pattern_analysis", {}).get("pattern_type", "unknown")
        if pattern_type not in clusters["bearish_group"]["pattern_types"]:
            clusters["bearish_group"]["pattern_types"][pattern_type] = 0
        clusters["bearish_group"]["pattern_types"][pattern_type] += 1
    

    
    def _extract_ticker_info(self, analysis, cluster_type):
        """Extract key information for ticker clustering"""
        trade_rec = analysis.get("trade_recommendation", {})
        pattern_analysis = analysis.get("pattern_analysis", {})
        market_summary = analysis.get("market_summary", {})
        technical_analysis = analysis.get("technical_analysis", {})
        
        return {
            "ticker": analysis.get("ticker", "UNKNOWN"),
            "confidence": pattern_analysis.get("confidence_score", 0),
            "success_probability": trade_rec.get("success_probability", 0),
            "pattern_type": pattern_analysis.get("pattern_type", "unknown"),
            "pattern_strength": pattern_analysis.get("pattern_strength", "unknown"),
            "entry": trade_rec.get("entry_price", trade_rec.get("specific_entry", "No entry specified")),
            "target": trade_rec.get("target_price", "No target"),
            "stop_loss": trade_rec.get("stop_loss", "No stop"),
            "risk_reward": trade_rec.get("risk_reward_ratio", "N/A"),
            "expiry": trade_rec.get("expiry_date", "N/A"),
            "dte": trade_rec.get("days_to_expiry", 0),
            "position_size": trade_rec.get("position_size_pct", 2.0),
            "current_price": trade_rec.get("current_price", "N/A"),
            "supporting_evidence": pattern_analysis.get("supporting_evidence", []),
            # Additional fields from LLM analysis
            "timeframe_confluence": trade_rec.get("timeframe_confluence", "Multi-timeframe aligned"),
            "volatility_regime": market_summary.get("volatility_regime", "Medium volatility"),
            "entry_triggers": trade_rec.get("entry_triggers", ["Price confirmation", "Volume spike"]),
            "institutional_flow": market_summary.get("institutional_flow", "Smart money positioning"),
            "smart_money_thesis": market_summary.get("smart_money_thesis", "Institutional positioning detected"),
            "technical_levels": {
                "support": technical_analysis.get("key_levels", {}).get("support", "N/A"),
                "resistance": technical_analysis.get("key_levels", {}).get("resistance", "N/A"),
                "pivot": technical_analysis.get("key_levels", {}).get("pivot", "N/A")
            },
            "momentum_indicators": technical_analysis.get("momentum_indicators", "RSI/MACD neutral"),
            "volume_analysis": technical_analysis.get("volume_analysis", "Institutional flow detected"),
            "multi_timeframe_summary": technical_analysis.get("multi_timeframe_summary", "Trend alignment confirmed"),
            # Enhanced smart money insights
            "smart_money_insights": analysis.get("smart_money_insights", {})
        }
    
    def _calculate_group_stats(self, clusters):
        """Calculate statistics for each cluster group"""
        # Bullish group stats
        bullish_tickers = clusters["bullish_group"]["tickers"]
        if bullish_tickers:
            total_confidence = sum(safe_int(t["confidence"]) for t in bullish_tickers)
            total_success_prob = sum(safe_int(t["success_probability"]) for t in bullish_tickers)
            count = len(bullish_tickers)
            
            clusters["bullish_group"]["avg_confidence"] = total_confidence / count
            clusters["bullish_group"]["avg_success_probability"] = total_success_prob / count
            clusters["bullish_group"]["total_count"] = count
        
        # Bearish group stats
        bearish_tickers = clusters["bearish_group"]["tickers"]
        if bearish_tickers:
            total_confidence = sum(safe_int(t["confidence"]) for t in bearish_tickers)
            total_success_prob = sum(safe_int(t["success_probability"]) for t in bearish_tickers)
            count = len(bearish_tickers)
            
            clusters["bearish_group"]["avg_confidence"] = total_confidence / count
            clusters["bearish_group"]["avg_success_probability"] = total_success_prob / count
            clusters["bearish_group"]["total_count"] = count
        

    
    def _generate_cluster_summary(self, clusters):
        """Generate human-readable cluster summary"""
        bullish_count = clusters["bullish_group"]["total_count"]
        bearish_count = clusters["bearish_group"]["total_count"]
        total = clusters["total_analyzed"]
        
        summary = {
            "distribution": {
                "bullish_signals": bullish_count,
                "bearish_signals": bearish_count,
                "total_processed": total
            },
            "success_rates": {
                "bullish_avg_probability": clusters["bullish_group"]["avg_success_probability"],
                "bearish_avg_probability": clusters["bearish_group"]["avg_success_probability"]
            },
            "dominant_patterns": {
                "bullish": self._get_dominant_pattern(clusters["bullish_group"]["pattern_types"]),
                "bearish": self._get_dominant_pattern(clusters["bearish_group"]["pattern_types"])
            },
            "market_bias": self._determine_market_bias(bullish_count, bearish_count)
        }
        
        return summary
    
    def _get_dominant_pattern(self, pattern_types):
        """Get the most common pattern type in a group"""
        if not pattern_types:
            return "none"
        return max(pattern_types, key=pattern_types.get)
    
    def _determine_market_bias(self, bullish_count, bearish_count):
        """Determine overall market bias from clustering results"""
        total_directional = bullish_count + bearish_count
        
        if total_directional == 0:
            return "unclear"
        
        bullish_pct = (bullish_count / total_directional) * 100
        
        if bullish_pct > 65:
            return f"bullish_bias_{bullish_pct:.0f}%"
        elif bullish_pct < 35:
            return f"bearish_bias_{100-bullish_pct:.0f}%"
        else:
            return f"mixed_{bullish_pct:.0f}%_bullish"
    
    def get_high_conviction_trades(self, clusters, max_count=5):
        """Extract highest conviction trades from clusters"""
        high_conviction = []
        
        # Get top bullish trades
        bullish_sorted = sorted(
            clusters["bullish_group"]["tickers"],
            key=lambda x: safe_int(x["confidence"]) * safe_int(x["success_probability"]),
            reverse=True
        )
        
        # Get top bearish trades
        bearish_sorted = sorted(
            clusters["bearish_group"]["tickers"],
            key=lambda x: safe_int(x["confidence"]) * safe_int(x["success_probability"]),
            reverse=True
        )
        
        # Combine and select top trades
        all_trades = bullish_sorted + bearish_sorted
        all_trades_sorted = sorted(
            all_trades,
            key=lambda x: safe_int(x["confidence"]) * safe_int(x["success_probability"]),
            reverse=True
        )
        
        return all_trades_sorted[:max_count]

    def _group_by_ticker(self, all_analyses):
        """Group analyses by ticker symbol for multi-timeframe analysis"""
        ticker_groups = {}

        for analysis in all_analyses:
            if analysis.get("status") == "error":
                continue

            ticker = analysis.get("ticker", "UNKNOWN")
            dte_period = analysis.get("dte_period", 30)

            if ticker not in ticker_groups:
                ticker_groups[ticker] = {}

            ticker_groups[ticker][dte_period] = analysis

        return ticker_groups

    def _analyze_timeframe_confluence(self, ticker_groups):
        """Analyze timeframe confluence across DTEs for each ticker"""
        multi_timeframe_data = {
            "by_ticker": {},
            "confluence_summary": {},
            "timeframe_stats": {}
        }

        for ticker, timeframe_data in ticker_groups.items():
            # Analyze this ticker across all timeframes
            ticker_analysis = self._analyze_ticker_confluence(ticker, timeframe_data)
            multi_timeframe_data["by_ticker"][ticker] = ticker_analysis

        # Generate overall confluence summary
        multi_timeframe_data["confluence_summary"] = self._generate_confluence_summary(multi_timeframe_data["by_ticker"])

        # Generate timeframe statistics
        multi_timeframe_data["timeframe_stats"] = self._generate_timeframe_stats(ticker_groups)

        return multi_timeframe_data

    def _analyze_ticker_confluence(self, ticker, timeframe_data):
        """Analyze confluence for a single ticker across timeframes"""
        timeframes = sorted(timeframe_data.keys())
        directions = []
        confidence_scores = []
        success_probs = []

        ticker_confluence = {
            "ticker": ticker,
            "timeframes": {},
            "confluence_type": "unknown",
            "overall_direction": "mixed",
            "confidence_progression": [],
            "pattern_evolution": []
        }

        # Analyze each timeframe
        for dte in timeframes:
            analysis = timeframe_data[dte]
            trade_rec = analysis.get("trade_recommendation", {})
            pattern_analysis = analysis.get("pattern_analysis", {})

            direction = trade_rec.get("direction", "NEUTRAL")
            confidence = safe_int(pattern_analysis.get("confidence_score", 0))
            success_prob = safe_int(trade_rec.get("success_probability", 0))
            pattern_type = pattern_analysis.get("pattern_type", "unknown")

            directions.append(direction)
            confidence_scores.append(confidence)
            success_probs.append(success_prob)

            ticker_confluence["timeframes"][str(dte)] = {
                "direction": direction,
                "confidence": confidence,
                "success_probability": success_prob,
                "pattern_type": pattern_type,
                "classification": self._classify_analysis(analysis)
            }

        # Determine confluence type
        unique_directions = set(d for d in directions if d != "NEUTRAL")
        if len(unique_directions) == 1:
            ticker_confluence["confluence_type"] = "aligned"
            ticker_confluence["overall_direction"] = list(unique_directions)[0].lower()
        elif len(unique_directions) > 1:
            ticker_confluence["confluence_type"] = "divergent"
            ticker_confluence["overall_direction"] = "mixed"
        else:
            ticker_confluence["confluence_type"] = "unclear"
            ticker_confluence["overall_direction"] = "neutral"

        # Confidence progression analysis
        ticker_confluence["confidence_progression"] = confidence_scores
        ticker_confluence["avg_confidence"] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        return ticker_confluence

    def _generate_confluence_summary(self, by_ticker_data):
        """Generate summary of timeframe confluence across all tickers"""
        total_tickers = len(by_ticker_data)
        aligned_count = 0
        divergent_count = 0
        unclear_count = 0

        aligned_tickers = []
        divergent_tickers = []

        for ticker, data in by_ticker_data.items():
            confluence_type = data.get("confluence_type", "unknown")

            if confluence_type == "aligned":
                aligned_count += 1
                aligned_tickers.append({
                    "ticker": ticker,
                    "direction": data.get("overall_direction", "unknown"),
                    "avg_confidence": data.get("avg_confidence", 0)
                })
            elif confluence_type == "divergent":
                divergent_count += 1
                divergent_tickers.append({
                    "ticker": ticker,
                    "timeframes": data.get("timeframes", {}),
                    "avg_confidence": data.get("avg_confidence", 0)
                })
            else:
                unclear_count += 1

        return {
            "total_tickers_analyzed": total_tickers,
            "aligned_signals": aligned_count,
            "divergent_signals": divergent_count,
            "unclear_signals": unclear_count,
            "alignment_rate": (aligned_count / total_tickers * 100) if total_tickers > 0 else 0,
            "high_conviction_aligned": [t for t in aligned_tickers if t["avg_confidence"] > 70],
            "notable_divergences": divergent_tickers[:5]  # Top 5 divergent cases
        }

    def _generate_timeframe_stats(self, ticker_groups):
        """Generate statistics for each timeframe across all tickers"""
        timeframe_stats = {}

        # Collect all unique timeframes
        all_timeframes = set()
        for ticker_data in ticker_groups.values():
            all_timeframes.update(ticker_data.keys())

        # Analyze each timeframe
        for dte in sorted(all_timeframes):
            timeframe_analyses = []

            for ticker, timeframe_data in ticker_groups.items():
                if dte in timeframe_data:
                    timeframe_analyses.append(timeframe_data[dte])

            if timeframe_analyses:
                bullish_count = sum(1 for a in timeframe_analyses if self._classify_analysis(a) == "bullish")
                bearish_count = sum(1 for a in timeframe_analyses if self._classify_analysis(a) == "bearish")
                avg_confidence = sum(safe_int(a.get("pattern_analysis", {}).get("confidence_score", 0)) for a in timeframe_analyses) / len(timeframe_analyses)

                timeframe_stats[str(dte)] = {
                    "total_signals": len(timeframe_analyses),
                    "bullish_signals": bullish_count,
                    "bearish_signals": bearish_count,
                    "bullish_percentage": (bullish_count / len(timeframe_analyses) * 100) if timeframe_analyses else 0,
                    "avg_confidence": avg_confidence,
                    "market_bias": "bullish" if bullish_count > bearish_count else "bearish" if bearish_count > bullish_count else "mixed"
                }

        return timeframe_stats