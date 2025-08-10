"""
Clustering Engine - Groups ticker analyses into bullish/bearish clusters
Calculates success probabilities and pattern classifications
"""

from datetime import datetime
from config.settings import CONFIDENCE_THRESHOLD

class ClusteringEngine:
    def __init__(self):
        self.confidence_threshold = CONFIDENCE_THRESHOLD
    
    def cluster_analyses(self, all_analyses):
        """Group all ticker analyses into bullish/bearish/neutral clusters"""
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
            "neutral_group": {
                "tickers": [],
                "avg_confidence": 0,
                "reasons": [],
                "total_count": 0
            }
        }
        
        # Process each analysis
        for analysis in all_analyses:
            if analysis.get("status") == "error":
                self._add_to_neutral(clusters, analysis, "Analysis error")
                continue
            
            classification = self._classify_analysis(analysis)
            
            if classification == "bullish":
                self._add_to_bullish(clusters, analysis)
            elif classification == "bearish":
                self._add_to_bearish(clusters, analysis)
            else:
                self._add_to_neutral(clusters, analysis, classification)
        
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
            if confidence < self.confidence_threshold * 100:  # Convert to percentage
                return f"low_confidence_{confidence}%"
            
            if success_prob < self.confidence_threshold * 100:
                return f"low_success_probability_{success_prob}%"
            
            # Classify based on direction
            if direction == "CALL":
                return "bullish"
            elif direction == "PUT":
                return "bearish"
            else:
                return "neutral_signal"
                
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
    
    def _add_to_neutral(self, clusters, analysis, reason):
        """Add analysis to neutral cluster"""
        ticker_info = {
            "ticker": analysis.get("ticker", "UNKNOWN"),
            "reason": reason,
            "confidence": analysis.get("pattern_analysis", {}).get("confidence_score", 0)
        }
        clusters["neutral_group"]["tickers"].append(ticker_info)
        
        if reason not in clusters["neutral_group"]["reasons"]:
            clusters["neutral_group"]["reasons"].append(reason)
    
    def _extract_ticker_info(self, analysis, cluster_type):
        """Extract key information for ticker clustering"""
        trade_rec = analysis.get("trade_recommendation", {})
        pattern_analysis = analysis.get("pattern_analysis", {})
        
        return {
            "ticker": analysis.get("ticker", "UNKNOWN"),
            "confidence": pattern_analysis.get("confidence_score", 0),
            "success_probability": trade_rec.get("success_probability", 0),
            "pattern_type": pattern_analysis.get("pattern_type", "unknown"),
            "pattern_strength": pattern_analysis.get("pattern_strength", "unknown"),
            "entry": trade_rec.get("specific_entry", "No entry specified"),
            "target": trade_rec.get("target_price", "No target"),
            "stop_loss": trade_rec.get("stop_loss", "No stop"),
            "risk_reward": trade_rec.get("risk_reward_ratio", "N/A"),
            "expiry": trade_rec.get("expiry_date", "N/A"),
            "dte": trade_rec.get("days_to_expiry", 0),
            "position_size": trade_rec.get("position_size_pct", 2.0),
            "supporting_evidence": pattern_analysis.get("supporting_evidence", [])
        }
    
    def _calculate_group_stats(self, clusters):
        """Calculate statistics for each cluster group"""
        # Bullish group stats
        bullish_tickers = clusters["bullish_group"]["tickers"]
        if bullish_tickers:
            total_confidence = sum(t["confidence"] for t in bullish_tickers)
            total_success_prob = sum(t["success_probability"] for t in bullish_tickers)
            count = len(bullish_tickers)
            
            clusters["bullish_group"]["avg_confidence"] = total_confidence / count
            clusters["bullish_group"]["avg_success_probability"] = total_success_prob / count
            clusters["bullish_group"]["total_count"] = count
        
        # Bearish group stats
        bearish_tickers = clusters["bearish_group"]["tickers"]
        if bearish_tickers:
            total_confidence = sum(t["confidence"] for t in bearish_tickers)
            total_success_prob = sum(t["success_probability"] for t in bearish_tickers)
            count = len(bearish_tickers)
            
            clusters["bearish_group"]["avg_confidence"] = total_confidence / count
            clusters["bearish_group"]["avg_success_probability"] = total_success_prob / count
            clusters["bearish_group"]["total_count"] = count
        
        # Neutral group stats
        neutral_tickers = clusters["neutral_group"]["tickers"]
        if neutral_tickers:
            confidences = [t.get("confidence", 0) for t in neutral_tickers if "confidence" in t]
            if confidences:
                clusters["neutral_group"]["avg_confidence"] = sum(confidences) / len(confidences)
            clusters["neutral_group"]["total_count"] = len(neutral_tickers)
    
    def _generate_cluster_summary(self, clusters):
        """Generate human-readable cluster summary"""
        bullish_count = clusters["bullish_group"]["total_count"]
        bearish_count = clusters["bearish_group"]["total_count"]
        neutral_count = clusters["neutral_group"]["total_count"]
        total = clusters["total_analyzed"]
        
        summary = {
            "distribution": {
                "bullish_signals": bullish_count,
                "bearish_signals": bearish_count, 
                "neutral_or_filtered": neutral_count,
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
            "market_bias": self._determine_market_bias(bullish_count, bearish_count, neutral_count)
        }
        
        return summary
    
    def _get_dominant_pattern(self, pattern_types):
        """Get the most common pattern type in a group"""
        if not pattern_types:
            return "none"
        return max(pattern_types, key=pattern_types.get)
    
    def _determine_market_bias(self, bullish_count, bearish_count, neutral_count):
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
            key=lambda x: (x["confidence"] * x["success_probability"]),
            reverse=True
        )
        
        # Get top bearish trades
        bearish_sorted = sorted(
            clusters["bearish_group"]["tickers"],
            key=lambda x: (x["confidence"] * x["success_probability"]),
            reverse=True
        )
        
        # Combine and select top trades
        all_trades = bullish_sorted + bearish_sorted
        all_trades_sorted = sorted(
            all_trades,
            key=lambda x: (x["confidence"] * x["success_probability"]),
            reverse=True
        )
        
        return all_trades_sorted[:max_count]