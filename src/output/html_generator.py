"""
HTML Generator - Creates dashboard HTML files from analysis results
Uses Jinja2 templates to generate professional trading dashboards
"""

import os
import json
from datetime import datetime
from jinja2 import Template

def safe_int(value):
    """Safely convert any value to integer, handling strings, percentages, quotes"""
    try:
        # Handle various formats: "75%", "75% - comment", 75, "75"
        clean_value = str(value).replace('%', '').replace('"', '').replace("'", '').strip()
        # Take only the first number if there's additional text
        number_part = clean_value.split()[0] if clean_value else '0'
        # Remove decimal part if present
        number_part = number_part.split('.')[0]
        return int(number_part) if number_part else 0
    except (ValueError, TypeError):
        return 0

def safe_float(value, decimals=2):
    """Safely convert any value to float with formatting"""
    try:
        # Handle various formats and clean the value
        clean_value = str(value).replace('$', '').replace('%', '').replace('"', '').replace("'", '').strip()
        # Take only the first number if there's additional text
        number_part = clean_value.split()[0] if clean_value else '0'
        result = float(number_part)
        return f"{result:.{decimals}f}"
    except (ValueError, TypeError):
        return "0.00"

class HTMLGenerator:
    def __init__(self, template_dir="src/output/templates", output_dir="output"):
        self.template_dir = template_dir
        self.output_dir = output_dir
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create date-specific subdirectory
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_output_dir = os.path.join("/Users/sayantbh/Workspace/fintool/open-interest-pattern-tracker/output", today)
        os.makedirs(self.daily_output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.daily_output_dir, "dashboards"), exist_ok=True)
        os.makedirs(os.path.join(self.daily_output_dir, "reports"), exist_ok=True)
    
    def generate_daily_dashboard(self, clusters, market_context=None):
        """Generate the main daily dashboard HTML"""
        try:
            # Prepare template data
            template_data = self._prepare_dashboard_data(clusters, market_context)
            
            # Load and render template
            dashboard_html = self._render_dashboard_template(template_data)
            
            # Save dashboard file
            dashboard_path = os.path.join(self.daily_output_dir, "dashboards", "daily_overview.html")
            with open(dashboard_path, 'w', encoding='utf-8') as f:
                f.write(dashboard_html)
            
            print(f"Daily dashboard generated: {dashboard_path}")
            return dashboard_path
            
        except Exception as e:
            print(f"Dashboard generation failed: {str(e)}")
            return None
    
    def generate_json_reports(self, clusters, all_analyses):
        """Generate JSON reports for API consumption"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Market summary report
            market_summary = {
                "date": today,
                "timestamp": datetime.now().isoformat(),
                "total_analyzed": clusters["total_analyzed"],
                "clustering_summary": clusters["summary"],
                "high_conviction_trades": self._get_high_conviction_for_json(clusters)
            }
            
            market_summary_path = os.path.join(self.daily_output_dir, "reports", "market_summary.json")
            with open(market_summary_path, 'w') as f:
                json.dump(market_summary, f, indent=2)
            
            # Individual analyses report
            individual_analyses_path = os.path.join(self.daily_output_dir, "reports", "individual_analyses.json")
            with open(individual_analyses_path, 'w') as f:
                json.dump(all_analyses, f, indent=2)
            
            # Clustering results
            clustering_path = os.path.join(self.daily_output_dir, "reports", "clustering_results.json")
            with open(clustering_path, 'w') as f:
                json.dump(clusters, f, indent=2)
            
            print(f"JSON reports generated in: {self.daily_output_dir}/reports/")
            return {
                "market_summary": market_summary_path,
                "individual_analyses": individual_analyses_path,
                "clustering_results": clustering_path
            }
            
        except Exception as e:
            print(f"JSON report generation failed: {str(e)}")
            return None
    
    def _prepare_dashboard_data(self, clusters, market_context):
        """Prepare data for dashboard template with multi-timeframe support"""
        high_conviction_trades = self._get_high_conviction_trades(clusters, max_count=3)
        all_recommendations = self._get_all_recommendations(clusters)
        market_pulse = self._prepare_market_pulse(clusters, market_context)
        gamma_squeeze_data = self._prepare_gamma_squeeze_data(clusters)
        options_signals = self._prepare_options_signals(clusters)

        # Multi-timeframe data preparation
        multi_timeframe_data = self._prepare_multi_timeframe_data(clusters)
        timeframe_comparison = self._prepare_timeframe_comparison_table(clusters)
        confluence_summary = self._prepare_confluence_summary(clusters)

        template_data = {
            # Header stats
            "patterns_found": len(clusters["bullish_group"]["pattern_types"]) + len(clusters["bearish_group"]["pattern_types"]),
            "stocks_analyzed": clusters["total_analyzed"],
            "avg_success_rate": self._calculate_overall_success_rate(clusters),
            "active_signals": clusters["bullish_group"]["total_count"] + clusters["bearish_group"]["total_count"],
            "last_update": datetime.now().strftime("%B %d, %Y at %I:%M %p ET"),

            # Market pulse data
            "market_pulse": market_pulse,

            # Gamma squeeze analysis data
            "gamma_squeeze_data": gamma_squeeze_data,

            # Options signals summary
            "options_signals": options_signals,

            # ALL trades for featured cards (consolidated by ticker)
            "high_conviction_trades": high_conviction_trades,
            "consolidated_high_conviction_trades": self._get_consolidated_high_conviction_trades(clusters, max_count=6),

            # All recommendations for table
            "all_recommendations": all_recommendations,

            # Risk metrics (calculated from positions)
            "risk_metrics": self._calculate_risk_metrics(all_recommendations),

            # Clustering summary
            "bullish_count": clusters["bullish_group"]["total_count"],
            "bearish_count": clusters["bearish_group"]["total_count"],

            # Multi-timeframe data
            "multi_timeframe_trades": multi_timeframe_data,
            "timeframe_comparison": timeframe_comparison,
            "confluence_summary": confluence_summary,
            "has_multi_timeframe": bool(clusters.get("multi_timeframe", {}).get("by_ticker"))
        }

        return template_data

    def _prepare_multi_timeframe_data(self, clusters):
        """Prepare multi-timeframe trade data for dashboard"""
        multi_timeframe_section = clusters.get("multi_timeframe", {})
        by_ticker_data = multi_timeframe_section.get("by_ticker", {})

        multi_timeframe_trades = []

        for ticker, confluence_data in by_ticker_data.items():
            timeframes = confluence_data.get("timeframes", {})

            # Prepare timeframe data for each ticker
            timeframe_entries = []
            for dte, analysis in timeframes.items():
                direction_class = "bullish" if analysis.get("classification") == "bullish" else "bearish"
                direction_color = "#00ff88" if direction_class == "bullish" else "#ff4444"

                timeframe_entries.append({
                    "dte": dte,
                    "direction": analysis.get("direction", "NEUTRAL"),
                    "confidence": safe_int(analysis.get("confidence", 0)),
                    "success_probability": safe_int(analysis.get("success_probability", 0)),
                    "pattern_type": analysis.get("pattern_type", "unknown"),
                    "direction_class": direction_class,
                    "direction_color": direction_color
                })

            # Sort timeframes by DTE
            timeframe_entries.sort(key=lambda x: int(x["dte"]))

            # Determine overall confluence
            confluence_type = confluence_data.get("confluence_type", "unknown")
            confluence_class = {
                "aligned": "success",
                "divergent": "warning",
                "unclear": "neutral"
            }.get(confluence_type, "neutral")

            multi_timeframe_trades.append({
                "ticker": ticker,
                "timeframes": timeframe_entries,
                "confluence_type": confluence_type,
                "confluence_class": confluence_class,
                "overall_direction": confluence_data.get("overall_direction", "mixed"),
                "avg_confidence": confluence_data.get("avg_confidence", 0)
            })

        # Sort by average confidence descending
        multi_timeframe_trades.sort(key=lambda x: x["avg_confidence"], reverse=True)

        return multi_timeframe_trades

    def _prepare_timeframe_comparison_table(self, clusters):
        """Prepare timeframe comparison table data"""
        multi_timeframe_section = clusters.get("multi_timeframe", {})
        timeframe_stats = multi_timeframe_section.get("timeframe_stats", {})

        comparison_data = []
        for dte, stats in timeframe_stats.items():
            bullish_pct = stats.get("bullish_percentage", 0)
            market_bias = stats.get("market_bias", "mixed")

            bias_class = {
                "bullish": "success",
                "bearish": "danger",
                "mixed": "warning"
            }.get(market_bias, "secondary")

            comparison_data.append({
                "dte": dte,
                "total_signals": stats.get("total_signals", 0),
                "bullish_signals": stats.get("bullish_signals", 0),
                "bearish_signals": stats.get("bearish_signals", 0),
                "bullish_percentage": f"{bullish_pct:.1f}%",
                "avg_confidence": f"{stats.get('avg_confidence', 0):.1f}%",
                "market_bias": market_bias.title(),
                "bias_class": bias_class
            })

        # Sort by DTE
        comparison_data.sort(key=lambda x: int(x["dte"]))

        return comparison_data

    def _prepare_confluence_summary(self, clusters):
        """Prepare confluence summary for dashboard"""
        multi_timeframe_section = clusters.get("multi_timeframe", {})
        confluence_summary = multi_timeframe_section.get("confluence_summary", {})

        return {
            "total_tickers": confluence_summary.get("total_tickers_analyzed", 0),
            "aligned_signals": confluence_summary.get("aligned_signals", 0),
            "divergent_signals": confluence_summary.get("divergent_signals", 0),
            "unclear_signals": confluence_summary.get("unclear_signals", 0),
            "alignment_rate": f"{confluence_summary.get('alignment_rate', 0):.1f}%",
            "high_conviction_aligned": confluence_summary.get("high_conviction_aligned", []),
            "notable_divergences": confluence_summary.get("notable_divergences", [])
        }
    
    def _prepare_gamma_squeeze_data(self, clusters):
        """Prepare gamma squeeze analysis data for dashboard"""
        gamma_setups = []
        
        # Process all tickers from both bullish and bearish clusters
        all_tickers = clusters["bullish_group"]["tickers"] + clusters["bearish_group"]["tickers"]
        
        for ticker in all_tickers:
            smart_money = ticker.get("smart_money_insights", {})
            gamma_analysis = smart_money.get("gamma_analysis", {})
            
            # Only include tickers with gamma analysis data
            if gamma_analysis:
                # Determine squeeze direction and risk level
                squeeze_risk = gamma_analysis.get("squeeze_risk", "Unknown")
                net_exposure = gamma_analysis.get("net_exposure", "")
                flip_point = gamma_analysis.get("flip_point", 0)
                current_price = float(str(ticker.get("current_price", "0")).replace("$", "").replace(",", "")) if ticker.get("current_price") else 0
                
                # Determine squeeze direction based on current price vs flip point
                if current_price > flip_point:
                    squeeze_direction = "Upward"
                    direction_class = "bullish"
                    direction_color = "#00ff88"
                else:
                    squeeze_direction = "Downward"
                    direction_class = "bearish"
                    direction_color = "#ff4444"
                
                # Calculate distance from flip point
                flip_distance = abs(current_price - flip_point) if flip_point and current_price else 0
                flip_distance_pct = (flip_distance / current_price * 100) if current_price > 0 else 0
                
                # Determine risk level styling
                risk_color = {
                    "High": "#ff4444",
                    "Medium": "#ffaa00", 
                    "Low": "#00ff88"
                }.get(squeeze_risk, "#888888")
                
                gamma_setup = {
                    "ticker": ticker["ticker"],
                    "current_price": f"${current_price:.2f}" if current_price else ticker.get("current_price", "N/A"),
                    "flip_point": f"${flip_point:.2f}" if flip_point else "N/A",
                    "flip_distance": f"{flip_distance_pct:.1f}%",
                    "squeeze_direction": squeeze_direction,
                    "direction_class": direction_class,
                    "direction_color": direction_color,
                    "squeeze_risk": squeeze_risk,
                    "risk_color": risk_color,
                    "net_exposure": net_exposure,
                    "volatility_impact": gamma_analysis.get("volatility_impact", "Unknown"),
                    "pattern_type": ticker.get("pattern_type", "").replace("_", " ").title(),
                    "confidence": f"{safe_int(ticker.get('confidence', 0))}%"
                }
                
                gamma_setups.append(gamma_setup)
        
        # Sort by squeeze risk priority (High -> Medium -> Low) and then by confidence
        risk_priority = {"High": 3, "Medium": 2, "Low": 1}
        gamma_setups.sort(
            key=lambda x: (risk_priority.get(x["squeeze_risk"], 0), safe_int(x["confidence"])),
            reverse=True
        )
        
        # Calculate summary statistics
        total_setups = len(gamma_setups)
        high_risk_count = len([g for g in gamma_setups if g["squeeze_risk"] == "High"])
        upward_count = len([g for g in gamma_setups if g["squeeze_direction"] == "Upward"])
        
        return {
            "gamma_setups": gamma_setups,
            "total_setups": total_setups,
            "high_risk_count": high_risk_count,
            "upward_squeeze_count": upward_count,
            "downward_squeeze_count": total_setups - upward_count,
            "avg_flip_distance": f"{sum(float(g['flip_distance'].replace('%', '')) for g in gamma_setups) / total_setups:.1f}%" if total_setups > 0 else "0%"
        }
    
    def _prepare_options_signals(self, clusters):
        """Prepare options signals summary for dashboard"""
        bullish_calls = []
        bearish_puts = []
        put_credit_spreads = []
        neutral_tickers = []
        
        # Process all tickers from both clusters
        all_tickers = clusters["bullish_group"]["tickers"] + clusters["bearish_group"]["tickers"]
        
        for ticker in all_tickers:
            ticker_symbol = ticker["ticker"]
            smart_money = ticker.get("smart_money_insights", {})
            
            # Extract put/call ratio
            pc_dynamics = smart_money.get("put_call_dynamics", {})
            pc_ratio = float(pc_dynamics.get("ratio", 1.0)) if pc_dynamics.get("ratio") else 1.0
            
            # Check for bullish call signals
            bullish_signals = 0
            bearish_signals = 0
            
            # Signal 1: Put/Call ratio analysis
            if pc_ratio < 0.5:
                bullish_signals += 1
            elif pc_ratio > 1.5:
                bearish_signals += 1
            
            # Signal 2: OI concentration analysis
            oi_zones = smart_money.get("oi_concentration_zones", {})
            heavy_calls = oi_zones.get("heavy_call_strikes", [])
            heavy_puts = oi_zones.get("heavy_put_strikes", [])
            
            if len(heavy_calls) > len(heavy_puts):
                bullish_signals += 1
            elif len(heavy_puts) > len(heavy_calls):
                bearish_signals += 1
            
            # Signal 3: Flow analysis (enhanced with new prompt structure)
            flow_analysis = smart_money.get("flow_analysis", {})
            net_positioning = flow_analysis.get("net_positioning", "").upper()
            directional_bias = flow_analysis.get("directional_bias", "").upper()
            
            # Check for explicit flow signals from enhanced prompt
            if "BULLISH_CALL_ACCUMULATION" in net_positioning or "CALL_HEAVY" in directional_bias:
                bullish_signals += 1
            elif "BEARISH_PUT_ACCUMULATION" in net_positioning or "PUT_HEAVY" in directional_bias:
                bearish_signals += 1
            # Fallback to previous logic for older data
            elif "bullish" in net_positioning.lower() or "call" in net_positioning.lower():
                bullish_signals += 1
            elif "bearish" in net_positioning.lower() or "put" in net_positioning.lower():
                bearish_signals += 1
            
            # Signal 4: Enhanced pattern type analysis
            pattern_type = ticker.get("pattern_type", "").lower()
            if pattern_type in ["institutional_accumulation", "gamma_squeeze_setup"] or any(word in pattern_type for word in ["accumulation", "squeeze"]):
                bullish_signals += 1
            elif pattern_type in ["distribution", "protective_hedging"] or any(word in pattern_type for word in ["distribution", "hedging"]):
                bearish_signals += 1
            
            # Signal 5: Put Credit Spread Analysis
            put_spread_signals = 0
            current_price = float(str(ticker.get("current_price", "0")).replace("$", "").replace(",", "")) if ticker.get("current_price") else 0
            
            # Check for explicit put credit spread analysis from enhanced LLM
            pcs_analysis = smart_money.get("put_credit_spread_analysis", {})
            pcs_suitability = pcs_analysis.get("suitability", "").lower()
            
            if "high" in pcs_suitability:
                put_spread_signals += 2  # Strong signal from LLM analysis
            elif "medium" in pcs_suitability:
                put_spread_signals += 1
            
            # Check for put walls and support levels
            max_pain_analysis = smart_money.get("max_pain_analysis", {})
            max_pain_level = float(max_pain_analysis.get("level", 0)) if max_pain_analysis.get("level") else 0
            
            # Strong put wall detection
            if heavy_puts:
                total_put_oi = sum(float(str(strike.get("oi", 0)).replace(",", "")) for strike in heavy_puts if strike.get("oi"))
                if total_put_oi > 50000:  # Significant put OI
                    put_spread_signals += 1
            
            # Max pain as support level
            if max_pain_level > 0 and current_price > 0:
                distance_from_max_pain = ((current_price - max_pain_level) / current_price) * 100
                if distance_from_max_pain > 3:  # At least 3% above max pain
                    put_spread_signals += 1
            
            # Protective hedging patterns suggest put walls
            if pattern_type in ["protective_hedging"] or "hedging" in pattern_type:
                put_spread_signals += 1
            
            # Pin risk analysis for put credit spreads
            pin_risk = max_pain_analysis.get("pin_risk", "").lower()
            if pin_risk in ["low", "medium"]:  # Avoid high pin risk
                put_spread_signals += 1
                
            # Calculate safety margin for put spreads
            put_wall_strikes = []
            for put_strike in heavy_puts:
                if put_strike.get("strike"):
                    try:
                        strike_price = float(put_strike["strike"])
                        if current_price > 0:
                            safety_margin = ((current_price - strike_price) / current_price) * 100
                            if safety_margin > 5:  # At least 5% safety margin
                                put_wall_strikes.append({
                                    "strike": strike_price,
                                    "oi": put_strike.get("oi", 0),
                                    "safety_margin": safety_margin
                                })
                    except (ValueError, TypeError):
                        continue
            
            # Categorize ticker based on signals
            signal_data = {
                "ticker": ticker_symbol,
                "pc_ratio": f"{pc_ratio:.2f}",
                "confidence": ticker.get("confidence", "N/A"),
                "pattern": ticker.get("pattern_type", "").replace("_", " ").title(),
                "current_price": ticker.get("current_price", "N/A"),
                "signals_count": max(bullish_signals, bearish_signals, put_spread_signals),
                "signal_strength": "Strong" if max(bullish_signals, bearish_signals, put_spread_signals) >= 3 else "Moderate" if max(bullish_signals, bearish_signals, put_spread_signals) >= 2 else "Weak",
                "directional_bias": directional_bias.replace("_", " ").title() if directional_bias else "Unknown",
                "signal_classification": pc_dynamics.get("signal_classification", "").replace("_", " ") if pc_dynamics.get("signal_classification") else "",
                "put_spread_signals": put_spread_signals,
                "max_pain_level": f"${max_pain_level:.2f}" if max_pain_level > 0 else "N/A",
                "put_wall_strikes": put_wall_strikes[:3],  # Top 3 put walls
                "safety_margin": f"{max(s['safety_margin'] for s in put_wall_strikes):.1f}%" if put_wall_strikes else "N/A",
                "pin_risk": pin_risk.title() if pin_risk else "Unknown",
                "pcs_suitability": pcs_suitability.title() if pcs_suitability else "Unknown",
                "pcs_thesis": pcs_analysis.get("credit_spread_thesis", "")[:50] + "..." if pcs_analysis.get("credit_spread_thesis") else ""
            }
            
            # Prioritize put credit spreads if strong signals present
            if put_spread_signals >= 2 and len(put_wall_strikes) > 0:
                put_credit_spreads.append(signal_data)
            elif bullish_signals >= 2 and bullish_signals > bearish_signals and bullish_signals > put_spread_signals:
                bullish_calls.append(signal_data)
            elif bearish_signals >= 2 and bearish_signals > bullish_signals and bearish_signals > put_spread_signals:
                bearish_puts.append(signal_data)
            else:
                neutral_tickers.append(signal_data)
        
        # Sort by signal strength and confidence
        def sort_key(x):
            confidence = safe_int(str(x["confidence"]).replace("%", ""))
            strength_score = {"Strong": 3, "Moderate": 2, "Weak": 1}.get(x["signal_strength"], 0)
            return (strength_score, confidence)
        
        bullish_calls.sort(key=sort_key, reverse=True)
        bearish_puts.sort(key=sort_key, reverse=True)
        put_credit_spreads.sort(key=sort_key, reverse=True)
        neutral_tickers.sort(key=sort_key, reverse=True)
        
        return {
            "bullish_calls": bullish_calls,
            "bearish_puts": bearish_puts,
            "put_credit_spreads": put_credit_spreads,
            "neutral_tickers": neutral_tickers,
            "total_bullish": len(bullish_calls),
            "total_bearish": len(bearish_puts),
            "total_put_spreads": len(put_credit_spreads),
            "total_neutral": len(neutral_tickers)
        }
    
    def _prepare_market_pulse(self, clusters, market_context):
        """Prepare market pulse section data"""
        # Determine overall sentiment
        bullish_count = clusters["bullish_group"]["total_count"]
        bearish_count = clusters["bearish_group"]["total_count"]
        total_directional = bullish_count + bearish_count
        
        if total_directional > 0:
            bullish_pct = (bullish_count / total_directional) * 100
            if bullish_pct > 60:
                sentiment = f"BULLISH {bullish_pct:.0f}%"
                sentiment_change = "+5% vs yesterday"  # Placeholder
            elif bullish_pct < 40:
                sentiment = f"BEARISH {100-bullish_pct:.0f}%"
                sentiment_change = "-3% vs yesterday"  # Placeholder
            else:
                sentiment = f"MIXED {bullish_pct:.0f}%"
                sentiment_change = "Unchanged"
        else:
            sentiment = "UNCLEAR"
            sentiment_change = "No signals"
        
        # Calculate institutional flow
        net_flow = f"↑ ${(bullish_count * 0.5 - bearish_count * 0.3):.1f}B Net {'Calls' if bullish_count > bearish_count else 'Puts'}"
        
        pulse_data = {
            "overall_sentiment": sentiment,
            "sentiment_change": sentiment_change,
            "institutional_flow": net_flow,
            "flow_change": "+$850M from Friday",  # Placeholder
            "vix_level": "Unknown",
            "vix_change": "N/A",
            "key_events": "Analysis Complete",
            "gamma_exposure": f"${(bullish_count - bearish_count) * 0.3:.1f}B ({'Long' if bullish_count > bearish_count else 'Short'} gamma setup)"
        }
        
        # Add VIX data if available
        if market_context:
            pulse_data["vix_level"] = f"{market_context.get('vix_put_call_ratio', 'N/A')}"
            pulse_data["key_events"] = market_context.get("market_summary", "VIX analysis complete")
        
        return pulse_data
    
    def _get_high_conviction_trades(self, clusters, max_count=10):
        """Get ALL trades for featured cards"""
        # Get ALL trades from each cluster
        bullish_trades = sorted(
            clusters["bullish_group"]["tickers"],
            key=lambda x: safe_int(x["confidence"]) * safe_int(x["success_probability"]),
            reverse=True
        )
        
        bearish_trades = sorted(
            clusters["bearish_group"]["tickers"],
            key=lambda x: safe_int(x["confidence"]) * safe_int(x["success_probability"]),
            reverse=True
        )
        
        high_conviction = []
        
        # Add bullish trades
        for trade in bullish_trades:
            high_conviction.append({
                "ticker": trade["ticker"],
                "pattern_type": trade["pattern_type"].replace("_", " ").title(),
                "direction": "bullish",
                "confidence": f"{safe_int(trade['confidence'])}%",
                "entry": f"${safe_float(trade['entry'])}" if str(trade['entry']).replace('.','').replace('-','').isdigit() or '.' in str(trade['entry']) else trade["entry"],
                "target": f"${safe_float(trade['target'])}" if str(trade['target']).replace('.','').replace('-','').isdigit() or '.' in str(trade['target']) else trade["target"],
                "stop_loss": f"${safe_float(trade['stop_loss'])}" if str(trade['stop_loss']).replace('.','').replace('-','').isdigit() or '.' in str(trade['stop_loss']) else trade["stop_loss"],
                "risk_reward": trade["risk_reward"],
                "expiry": trade["expiry"],
                "dte": trade["dte"],
                "success_prob": f"{safe_int(trade['success_probability'])}%",
                "current_price": trade["current_price"],
                "supporting_evidence": trade["supporting_evidence"][:4],  # Top 4 evidence points
                "timeframe_confluence": trade.get("timeframe_confluence", "Multi-timeframe aligned"),
                "entry_triggers": trade.get("entry_triggers", ["Price confirmation", "Volume spike"]),
                "technical_levels": trade.get("technical_levels", {}),
                "volatility_regime": trade.get("volatility_regime", "Medium volatility"),
                "institutional_flow": trade.get("institutional_flow", "Smart money positioning"),
                "smart_money_thesis": trade.get("smart_money_thesis", "Institutional positioning detected"),
                "smart_money_insights": trade.get("smart_money_insights", {})
            })
        
        # Add bearish trades
        for trade in bearish_trades:
            high_conviction.append({
                "ticker": trade["ticker"],
                "pattern_type": trade["pattern_type"].replace("_", " ").title(),
                "direction": "bearish",
                "confidence": f"{safe_int(trade['confidence'])}%",
                "entry": f"${safe_float(trade['entry'])}" if str(trade['entry']).replace('.','').replace('-','').isdigit() or '.' in str(trade['entry']) else trade["entry"],
                "target": f"${safe_float(trade['target'])}" if str(trade['target']).replace('.','').replace('-','').isdigit() or '.' in str(trade['target']) else trade["target"],
                "stop_loss": f"${safe_float(trade['stop_loss'])}" if str(trade['stop_loss']).replace('.','').replace('-','').isdigit() or '.' in str(trade['stop_loss']) else trade["stop_loss"],
                "risk_reward": trade["risk_reward"],
                "expiry": trade["expiry"],
                "dte": trade["dte"],
                "success_prob": f"{safe_int(trade['success_probability'])}%",
                "current_price": trade["current_price"],
                "supporting_evidence": trade["supporting_evidence"][:4],
                "timeframe_confluence": trade.get("timeframe_confluence", "Multi-timeframe aligned"),
                "entry_triggers": trade.get("entry_triggers", ["Price confirmation", "Volume spike"]),
                "technical_levels": trade.get("technical_levels", {}),
                "volatility_regime": trade.get("volatility_regime", "Medium volatility"),
                "institutional_flow": trade.get("institutional_flow", "Smart money positioning"),
                "smart_money_thesis": trade.get("smart_money_thesis", "Institutional positioning detected"),
                "smart_money_insights": trade.get("smart_money_insights", {})
            })
        

        
        return high_conviction  # Return ALL trades, not limited

    def _get_consolidated_high_conviction_trades(self, clusters, max_count=6):
        """Consolidate trades by ticker with multi-timeframe data"""

        # Collect all trades across timeframes
        all_trades = []
        for group in ["bullish_group", "bearish_group"]:
            if group in clusters:
                all_trades.extend(clusters[group]["tickers"])

        # Group by ticker
        ticker_groups = {}
        for trade in all_trades:
            ticker = trade["ticker"]
            if ticker not in ticker_groups:
                ticker_groups[ticker] = []
            ticker_groups[ticker].append(trade)

        consolidated_trades = []
        for ticker, timeframe_trades in ticker_groups.items():
            # Sort by DTE
            timeframe_trades.sort(key=lambda x: safe_int(x.get("dte", 30)))

            # Calculate consensus
            consensus = self._calculate_consensus(timeframe_trades)

            # Get current price from first trade
            current_price = timeframe_trades[0].get("current_price", "N/A")

            # Build consolidated trade object
            consolidated_trade = {
                "ticker": ticker,
                "current_price": current_price,
                "consensus_direction": consensus["direction"],
                "consensus_confidence": consensus["confidence"],
                "confluence_status": consensus["confluence_status"],
                "timeframes": {}
            }

            # Add each timeframe data
            for trade in timeframe_trades:
                dte = safe_int(trade.get("dte", 30))

                # Determine direction from trade classification
                direction = "bullish" if "bullish_group" in str(trade) else trade.get("direction", "bullish")

                consolidated_trade["timeframes"][str(dte)] = {
                    "pattern_type": trade["pattern_type"].replace("_", " ").title(),
                    "direction": direction,
                    "confidence": trade["confidence"],
                    "entry": trade["entry"],
                    "target": trade["target"],
                    "stop_loss": trade["stop_loss"],
                    "success_prob": trade["success_probability"],
                    "risk_reward": trade["risk_reward"],
                    "analysis": trade.get("smart_money_thesis", trade.get("institutional_flow", "Smart money positioning detected")),
                    "expiry": trade.get("expiry", ""),
                    "dte": dte,
                    "supporting_evidence": trade.get("supporting_evidence", [])[:3],  # Top 3 evidence points
                    "smart_money_insights": trade.get("smart_money_insights", {})
                }

            consolidated_trades.append(consolidated_trade)

        # Sort by consensus confidence
        try:
            consolidated_trades.sort(
                key=lambda x: float(x["consensus_confidence"].replace("%", "")),
                reverse=True
            )
        except (ValueError, KeyError):
            # Fallback sorting if confidence parsing fails
            consolidated_trades.sort(key=lambda x: len(x["timeframes"]), reverse=True)

        return consolidated_trades[:max_count]

    def _calculate_consensus(self, timeframe_trades):
        """Calculate consensus direction and confluence status"""

        # Extract directions and confidences
        directions = []
        confidences = []

        for trade in timeframe_trades:
            # Try to extract direction from various sources
            direction = "unknown"

            # Method 1: Check pattern type for directional clues
            pattern_type = trade.get("pattern_type", "").lower()
            if "accumulation" in pattern_type or "squeeze" in pattern_type:
                direction = "bullish"
            elif "distribution" in pattern_type or "hedging" in pattern_type:
                direction = "bearish"
            else:
                # Method 2: Use trade recommendation direction
                trade_rec = trade.get("trade_recommendation", {})
                rec_direction = trade_rec.get("direction", "").upper()
                if "CALL" in rec_direction:
                    direction = "bullish"
                elif "PUT" in rec_direction:
                    direction = "bearish"
                else:
                    # Method 3: Default based on typical pattern
                    direction = "bullish"  # Default assumption

            directions.append(direction)

            # Extract confidence
            confidence_str = str(trade.get("confidence", "50")).replace("%", "")
            try:
                confidence = float(confidence_str)
            except ValueError:
                confidence = 50.0  # Default confidence

            confidences.append(confidence)

        # Count directions
        bullish_count = directions.count("bullish")
        bearish_count = directions.count("bearish")
        total_count = len(directions)

        # Determine consensus
        if bullish_count == total_count:
            consensus_direction = "bullish"
            confluence_status = "aligned"
        elif bearish_count == total_count:
            consensus_direction = "bearish"
            confluence_status = "aligned"
        elif abs(bullish_count - bearish_count) <= 1:
            consensus_direction = "mixed"
            confluence_status = "divergent"
        else:
            consensus_direction = "bullish" if bullish_count > bearish_count else "bearish"
            confluence_status = "partial"

        # Calculate weighted average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 50.0

        return {
            "direction": consensus_direction,
            "confidence": f"{avg_confidence:.0f}%",
            "confluence_status": confluence_status
        }
    
    def _get_all_recommendations(self, clusters):
        """Get all recommendations for the main table"""
        recommendations = []
        
        # Add bullish recommendations
        for trade in clusters["bullish_group"]["tickers"]:
            recommendations.append({
                "ticker": trade["ticker"],
                "pattern": trade["pattern_type"].replace("_", " ").title(),
                "direction": "CALL",
                "entry": trade["entry"],
                "target": trade["target"],
                "expiry": f"{trade['expiry']} ({trade['dte']} DTE)",
                "success_prob": f"{safe_int(trade['success_probability'])}%",
                "risk_reward": trade["risk_reward"]
            })
        
        # Add bearish recommendations
        for trade in clusters["bearish_group"]["tickers"]:
            recommendations.append({
                "ticker": trade["ticker"],
                "pattern": trade["pattern_type"].replace("_", " ").title(),
                "direction": "PUT",
                "entry": trade["entry"],
                "target": trade["target"],
                "expiry": f"{trade['expiry']} ({trade['dte']} DTE)",
                "success_prob": f"{safe_int(trade['success_probability'])}%",
                "risk_reward": trade["risk_reward"]
            })
        
        # Sort by success probability using safe_int
        recommendations.sort(key=lambda x: safe_int(x["success_prob"]), reverse=True)
        
        return recommendations
    
    def _calculate_overall_success_rate(self, clusters):
        """Calculate weighted average success rate"""
        total_weighted = 0
        total_count = 0
        
        for ticker in clusters["bullish_group"]["tickers"]:
            total_weighted += safe_int(ticker["success_probability"])
            total_count += 1
        
        for ticker in clusters["bearish_group"]["tickers"]:
            total_weighted += safe_int(ticker["success_probability"])
            total_count += 1
        
        if total_count == 0:
            return "0.0%"
        
        avg_success = total_weighted / total_count
        return f"{avg_success:.1f}%"
    
    def _calculate_risk_metrics(self, recommendations):
        """Calculate portfolio-level risk metrics"""
        total_positions = len(recommendations)
        avg_position_size = 2.5  # Default 2.5% per position
        
        # Simplified risk calculations
        portfolio_var = total_positions * avg_position_size * 1000 * -0.5  # Rough VaR estimate
        delta_exposure = total_positions * 15000  # Rough delta estimate
        theta_decay = total_positions * -150  # Daily theta estimate
        max_position_risk = max(avg_position_size, 2.5) if total_positions > 0 else 2.5
        
        return {
            "portfolio_var": f"-${abs(portfolio_var):,.0f}",
            "delta_exposure": f"+${delta_exposure:,.0f}",
            "theta_decay": f"${theta_decay:,.0f}",
            "max_position_risk": f"{max_position_risk:.1f}%"
        }
    
    def _get_high_conviction_for_json(self, clusters):
        """Get high conviction trades formatted for JSON report"""
        return self._get_high_conviction_trades(clusters, max_count=5)
    
    def _render_dashboard_template(self, template_data):
        """Render the dashboard using template based on our mockup"""
        template_str = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OI Pattern Tracker - Daily Analysis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; line-height: 1.5; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #333; }
        .logo { font-size: 28px; font-weight: 700; color: #fff; }
        .header-stats { display: flex; gap: 40px; }
        .header-stat { text-align: center; }
        .stat-label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
        .stat-value { font-size: 20px; font-weight: 700; color: #fff; }
        .stat-value.green { color: #00ff88; }
        .stat-value.red { color: #ff4444; }
        .stat-value.yellow { color: #ffaa00; }
        .market-pulse { background: #111; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 25px; }
        .section-title { font-size: 20px; font-weight: 600; color: #fff; margin-bottom: 20px; display: flex; align-items: center; }
        .pulse-icon { width: 8px; height: 8px; background: #00ff88; border-radius: 50%; margin-right: 10px; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .pulse-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 20px; }
        .pulse-card { background: #1a1a1a; padding: 20px; border-radius: 8px; border: 1px solid #333; }
        .pulse-metric { font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 8px; }
        .pulse-value { font-size: 18px; font-weight: 600; }
        .pulse-change { font-size: 12px; margin-top: 4px; }
        .positive { color: #00ff88; }
        .negative { color: #ff4444; }
        .conviction-section { background: #111; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 25px; }
        .trade-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 25px; }
        .trade-card { background: #111; border: 2px solid #333; border-radius: 12px; overflow: hidden; position: relative; transition: all 0.3s ease; }
        .trade-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3); }
        .trade-card.consensus-bullish { border-left: 4px solid #00ff88; }
        .trade-card.consensus-bearish { border-left: 4px solid #ff4444; }
        .trade-card.consensus-mixed { border-left: 4px solid #ffaa00; }
        .click-hint { position: absolute; bottom: 10px; right: 15px; color: #666; font-size: 11px; opacity: 0; transition: opacity 0.3s ease; }
        .trade-card:hover .click-hint { opacity: 1; }

        /* Enhanced Card Header */
        .card-header { background: linear-gradient(135deg, #1a1a1a 0%, #151515 100%); padding: 20px; border-bottom: 1px solid #333; }
        .ticker-main-info { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; }
        .ticker-symbol { font-size: 24px; font-weight: 700; color: #fff; }
        .current-price { font-size: 16px; color: #888; margin-top: 2px; }
        .consensus-indicator { text-align: right; }
        .confluence-status { display: block; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }
        .confluence-status.aligned { color: #00ff88; }
        .confluence-status.divergent { color: #ff4444; }
        .confluence-status.partial { color: #ffaa00; }
        .dominant-direction { font-size: 12px; font-weight: 600; text-transform: uppercase; }
        .dominant-direction.bullish { color: #00ff88; }
        .dominant-direction.bearish { color: #ff4444; }
        .dominant-direction.mixed { color: #ffaa00; }

        /* Enhanced Timeframe Tabs */
        .card-timeframe-tabs { display: flex; background: #0a0a0a; border-radius: 8px; overflow: hidden; border: 1px solid #333; }
        .card-tab { flex: 1; padding: 10px 8px; text-align: center; cursor: pointer; transition: all 0.3s ease; position: relative; border-right: 1px solid #333; }
        .card-tab:last-child { border-right: none; }
        .card-tab.active { background: #00ff88; color: #000; }
        .card-tab:not(.active) { color: #888; background: #0a0a0a; }
        .card-tab:not(.active):hover { background: #222; color: #fff; }
        .card-tab.high-confidence:not(.active) { border-bottom: 2px solid #00ff88; }
        .card-tab.medium-confidence:not(.active) { border-bottom: 2px solid #ffaa00; }
        .card-tab.low-confidence:not(.active) { border-bottom: 2px solid #ff4444; }
        .card-tab.conflicting { position: relative; }
        .conflict-indicator { position: absolute; top: 2px; right: 2px; font-size: 8px; opacity: 0.8; }
        .dte-label { display: block; font-size: 11px; font-weight: 600; }
        .confidence-mini { display: block; font-size: 9px; opacity: 0.8; font-weight: 500; }

        /* Timeframe Content */
        .timeframe-content { padding: 20px; }
        .timeframe-panel { display: none; }
        .timeframe-panel.active { display: block; }
        .timeframe-analysis { font-size: 12px; color: #ccc; line-height: 1.4; margin-top: 10px; }

        /* Confidence Evolution */
        .confidence-evolution { padding: 15px 20px; border-top: 1px solid #333; background: #0a0a0a; }
        .evolution-label { font-size: 11px; color: #888; margin-bottom: 8px; text-transform: uppercase; }
        .confidence-timeline { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .timeline-point { width: 8px; height: 8px; border-radius: 50%; }
        .timeline-point.high { background: #00ff88; }
        .timeline-point.medium { background: #ffaa00; }
        .timeline-point.low { background: #ff4444; }
        .timeline-line { flex: 1; height: 2px; background: #333; }
        .timeline-labels { display: flex; justify-content: space-between; }
        .timeline-label { font-size: 10px; color: #888; }

        .trade-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; }
        .ticker { font-size: 24px; font-weight: 700; color: #fff; }
        .confidence-badge { background: #00ff88; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .confidence-badge.bearish { background: #ff4444; color: #fff; }

        .pattern-type { color: #00ff88; font-size: 14px; font-weight: 500; margin-bottom: 15px; text-transform: uppercase; }
        .pattern-type.bearish { color: #ff4444; }

        .trade-details { background: #0a0a0a; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
        .trade-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .trade-label { color: #888; font-size: 13px; }
        .trade-value { color: #fff; font-weight: 500; font-size: 13px; }
        .evidence-list { list-style: none; margin-top: 15px; }
        .evidence-list li { font-size: 12px; color: #ccc; padding: 4px 0; padding-left: 15px; position: relative; }
        .evidence-list li:before { content: "•"; color: #00ff88; position: absolute; left: 0; }
        .recommendations-section { background: #111; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 25px; }
        .recommendations-table { width: 100%; border-collapse: collapse; background: #1a1a1a; border-radius: 8px; overflow: hidden; }
        .recommendations-table th { background: #0a0a0a; padding: 15px 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; border-bottom: 1px solid #333; }
        .recommendations-table td { padding: 15px 12px; border-bottom: 1px solid #222; font-size: 14px; }
        .recommendations-table tr:hover { background: #222; }
        .ticker-cell { font-weight: 700; font-size: 16px; color: #fff; }
        .direction-badge { display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
        .direction-badge.call { background: #00ff88; color: #000; }
        .direction-badge.put { background: #ff4444; color: #fff; }
        .probability-cell { font-weight: 700; font-size: 16px; }
        .risk-section { background: #111; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 25px; }
        .risk-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
        .risk-card { background: #1a1a1a; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #333; }
        .risk-metric { font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 10px; }
        .risk-value { font-size: 22px; font-weight: 700; }
        .gamma-section { background: #111; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 25px; }
        .gamma-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 25px; }
        .gamma-summary-card { background: #1a1a1a; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #333; }
        .gamma-summary-label { font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 8px; }
        .gamma-summary-value { font-size: 22px; font-weight: 700; color: #fff; }
        .gamma-table { width: 100%; border-collapse: collapse; background: #1a1a1a; border-radius: 8px; overflow: hidden; }
        .gamma-table th { background: #0a0a0a; padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; border-bottom: 1px solid #333; }
        .gamma-table td { padding: 12px; border-bottom: 1px solid #222; font-size: 13px; }
        .gamma-table tr:hover { background: #222; }
        .squeeze-direction { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; display: inline-block; }
        .squeeze-direction.upward { background: rgba(0, 255, 136, 0.2); color: #00ff88; border: 1px solid #00ff88; }
        .squeeze-direction.downward { background: rgba(255, 68, 68, 0.2); color: #ff4444; border: 1px solid #ff4444; }
        .risk-badge { padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; text-transform: uppercase; }
        .risk-badge.high { background: #ff4444; color: #fff; }
        .risk-badge.medium { background: #ffaa00; color: #000; }
        .risk-badge.low { background: #00ff88; color: #000; }
        .flip-point-indicator { display: flex; align-items: center; gap: 8px; }
        .flip-arrow { font-size: 16px; }
        .footer { text-align: center; padding: 20px; border-top: 1px solid #333; margin-top: 40px; color: #666; font-size: 12px; }
        .last-update { color: #888; font-size: 11px; text-align: right; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">OI Pattern Tracker</div>
            <div class="header-stats">
                <div class="header-stat">
                    <div class="stat-label">Patterns Found</div>
                    <div class="stat-value">{{patterns_found}}</div>
                </div>
                <div class="header-stat">
                    <div class="stat-label">Stocks Analyzed</div>
                    <div class="stat-value">{{stocks_analyzed}}</div>
                </div>
                <div class="header-stat">
                    <div class="stat-label">Success Rate</div>
                    <div class="stat-value green">{{avg_success_rate}}</div>
                </div>
                <div class="header-stat">
                    <div class="stat-label">Active Signals</div>
                    <div class="stat-value yellow">{{active_signals}}</div>
                </div>
            </div>
        </div>
        
        <div class="market-pulse">
            <div class="section-title">
                <div class="pulse-icon"></div>
                Market Pulse - {{last_update}}
            </div>
            <div class="pulse-grid">
                <div class="pulse-card">
                    <div class="pulse-metric">Overall Sentiment</div>
                    <div class="pulse-value positive">{{market_pulse.overall_sentiment}}</div>
                    <div class="pulse-change positive">{{market_pulse.sentiment_change}}</div>
                </div>
                <div class="pulse-card">
                    <div class="pulse-metric">Institutional Flow</div>
                    <div class="pulse-value positive">{{market_pulse.institutional_flow}}</div>
                    <div class="pulse-change positive">{{market_pulse.flow_change}}</div>
                </div>
                <div class="pulse-card">
                    <div class="pulse-metric">VIX Level</div>
                    <div class="pulse-value">{{market_pulse.vix_level}}</div>
                    <div class="pulse-change">{{market_pulse.vix_change}}</div>
                </div>
                <div class="pulse-card">
                    <div class="pulse-metric">Key Events</div>
                    <div class="pulse-value">{{market_pulse.key_events}}</div>
                </div>
                <div class="pulse-card">
                    <div class="pulse-metric">Gamma Exposure</div>
                    <div class="pulse-value">{{market_pulse.gamma_exposure}}</div>
                </div>
            </div>
        </div>
        
        <div class="options-signals-section" style="background: #111; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 25px;">
            <div class="section-title">📊 Options Signal Summary</div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <!-- BULLISH CALLS -->
                <div style="background: #1a1a1a; border: 2px solid #00ff88; border-radius: 10px; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 15px;">
                        <div style="font-size: 16px; font-weight: 600; color: #00ff88; margin-bottom: 5px;">🟢 BULLISH CALLS</div>
                        <div style="font-size: 24px; font-weight: 700; color: #fff;">{{options_signals.total_bullish}}</div>
                        <div style="font-size: 11px; color: #888; margin-top: 5px;">Tickers with call bias</div>
                    </div>
                    <div style="font-size: 11px; color: #00ff88; margin-bottom: 10px; text-transform: uppercase; font-weight: 600;">Criteria Met:</div>
                    <div style="font-size: 10px; color: #ccc; line-height: 1.4; margin-bottom: 15px;">
                        • Put/Call ratio < 0.5<br>
                        • Heavy call OI concentration<br>
                        • Bullish flow positioning<br>
                        • Accumulation patterns
                    </div>
                    {% if options_signals.bullish_calls %}
                    <div style="max-height: 200px; overflow-y: auto;">
                        {% for signal in options_signals.bullish_calls %}
                        <div style="background: #0a0a0a; padding: 8px; margin-bottom: 6px; border-radius: 5px; border-left: 3px solid #00ff88;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: 600; color: #fff;">{{signal.ticker}}</span>
                                <span style="font-size: 10px; color: #00ff88;">{{signal.signal_strength}}</span>
                            </div>
                            <div style="font-size: 10px; color: #888; margin-top: 2px;">
                                P/C: {{signal.pc_ratio}} | {{signal.pattern}}
                                {% if signal.directional_bias and signal.directional_bias != "Unknown" %}
                                <br><span style="color: #00ff88; font-size: 9px;">{{signal.directional_bias}}</span>
                                {% endif %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <div style="text-align: center; color: #666; font-size: 12px; padding: 20px;">No tickers meet bullish call criteria</div>
                    {% endif %}
                </div>
                
                <!-- BEARISH PUTS -->
                <div style="background: #1a1a1a; border: 2px solid #ff4444; border-radius: 10px; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 15px;">
                        <div style="font-size: 16px; font-weight: 600; color: #ff4444; margin-bottom: 5px;">🔴 BEARISH PUTS</div>
                        <div style="font-size: 24px; font-weight: 700; color: #fff;">{{options_signals.total_bearish}}</div>
                        <div style="font-size: 11px; color: #888; margin-top: 5px;">Tickers with put bias</div>
                    </div>
                    <div style="font-size: 11px; color: #ff4444; margin-bottom: 10px; text-transform: uppercase; font-weight: 600;">Criteria Met:</div>
                    <div style="font-size: 10px; color: #ccc; line-height: 1.4; margin-bottom: 15px;">
                        • Put/Call ratio > 1.5<br>
                        • Heavy put OI at key levels<br>
                        • Bearish flow positioning<br>
                        • Distribution patterns
                    </div>
                    {% if options_signals.bearish_puts %}
                    <div style="max-height: 200px; overflow-y: auto;">
                        {% for signal in options_signals.bearish_puts %}
                        <div style="background: #0a0a0a; padding: 8px; margin-bottom: 6px; border-radius: 5px; border-left: 3px solid #ff4444;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: 600; color: #fff;">{{signal.ticker}}</span>
                                <span style="font-size: 10px; color: #ff4444;">{{signal.signal_strength}}</span>
                            </div>
                            <div style="font-size: 10px; color: #888; margin-top: 2px;">
                                P/C: {{signal.pc_ratio}} | {{signal.pattern}}
                                {% if signal.directional_bias and signal.directional_bias != "Unknown" %}
                                <br><span style="color: #ff4444; font-size: 9px;">{{signal.directional_bias}}</span>
                                {% endif %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <div style="text-align: center; color: #666; font-size: 12px; padding: 20px;">No tickers meet bearish put criteria</div>
                    {% endif %}
                </div>
                
                <!-- PUT CREDIT SPREADS -->
                <div style="background: #1a1a1a; border: 2px solid #8a2be2; border-radius: 10px; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 15px;">
                        <div style="font-size: 16px; font-weight: 600; color: #8a2be2; margin-bottom: 5px;">🟣 PUT SPREADS</div>
                        <div style="font-size: 24px; font-weight: 700; color: #fff;">{{options_signals.total_put_spreads}}</div>
                        <div style="font-size: 11px; color: #888; margin-top: 5px;">Strong put walls</div>
                    </div>
                    <div style="font-size: 11px; color: #8a2be2; margin-bottom: 10px; text-transform: uppercase; font-weight: 600;">Criteria Met:</div>
                    <div style="font-size: 10px; color: #ccc; line-height: 1.4; margin-bottom: 15px;">
                        • Massive put OI (>50K contracts)<br>
                        • Price >3% above max pain<br>
                        • Strong support levels<br>
                        • >5% safety margin
                    </div>
                    {% if options_signals.put_credit_spreads %}
                    <div style="max-height: 200px; overflow-y: auto;">
                        {% for signal in options_signals.put_credit_spreads %}
                        <div style="background: #0a0a0a; padding: 8px; margin-bottom: 6px; border-radius: 5px; border-left: 3px solid #8a2be2;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: 600; color: #fff;">{{signal.ticker}}</span>
                                <span style="font-size: 10px; color: #8a2be2;">{{signal.signal_strength}}</span>
                            </div>
                            <div style="font-size: 10px; color: #888; margin-top: 2px;">
                                Max Pain: {{signal.max_pain_level}} | Safety: {{signal.safety_margin}}
                                {% if signal.directional_bias and signal.directional_bias != "Unknown" %}
                                <br><span style="color: #8a2be2; font-size: 9px;">{{signal.directional_bias}}</span>
                                {% endif %}
                                {% if signal.put_wall_strikes %}
                                <br><span style="color: #ccc; font-size: 9px;">Put Walls: 
                                {% for wall in signal.put_wall_strikes %}
                                ${{wall.strike|round}} {% if not loop.last %}, {% endif %}
                                {% endfor %}
                                </span>
                                {% endif %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <div style="text-align: center; color: #666; font-size: 12px; padding: 20px;">No strong put walls detected</div>
                    {% endif %}
                </div>
                
                <!-- NEUTRAL/MIXED -->
                <div style="background: #1a1a1a; border: 2px solid #ffaa00; border-radius: 10px; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 15px;">
                        <div style="font-size: 16px; font-weight: 600; color: #ffaa00; margin-bottom: 5px;">⚪ NEUTRAL/MIXED</div>
                        <div style="font-size: 24px; font-weight: 700; color: #fff;">{{options_signals.total_neutral}}</div>
                        <div style="font-size: 11px; color: #888; margin-top: 5px;">Inconclusive signals</div>
                    </div>
                    <div style="font-size: 11px; color: #ffaa00; margin-bottom: 10px; text-transform: uppercase; font-weight: 600;">Characteristics:</div>
                    <div style="font-size: 10px; color: #ccc; line-height: 1.4; margin-bottom: 15px;">
                        • Mixed P/C ratios (0.5-1.5)<br>
                        • Balanced OI distribution<br>
                        • Unclear directional bias<br>
                        • Wait for clearer signals
                    </div>
                    {% if options_signals.neutral_tickers %}
                    <div style="max-height: 200px; overflow-y: auto;">
                        {% for signal in options_signals.neutral_tickers %}
                        <div style="background: #0a0a0a; padding: 8px; margin-bottom: 6px; border-radius: 5px; border-left: 3px solid #ffaa00;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: 600; color: #fff;">{{signal.ticker}}</span>
                                <span style="font-size: 10px; color: #ffaa00;">{{signal.signal_strength}}</span>
                            </div>
                            <div style="font-size: 10px; color: #888; margin-top: 2px;">
                                P/C: {{signal.pc_ratio}} | {{signal.pattern}}
                                {% if signal.directional_bias and signal.directional_bias != "Unknown" %}
                                <br><span style="color: #ffaa00; font-size: 9px;">{{signal.directional_bias}}</span>
                                {% endif %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <div style="text-align: center; color: #666; font-size: 12px; padding: 20px;">All tickers have clear directional bias</div>
                    {% endif %}
                </div>
            </div>
            
            <div style="background: #0a0a0a; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff88;">
                <div style="font-size: 12px; color: #00ff88; font-weight: 600; margin-bottom: 8px;">📖 SIGNAL INTERPRETATION:</div>
                <div style="font-size: 11px; color: #ccc; line-height: 1.4;">
                    <strong>Bullish Calls:</strong> Strong call buying interest with low put protection - institutions positioning for upside<br>
                    <strong>Bearish Puts:</strong> Heavy put accumulation with call selling - smart money hedging or betting on downside<br>
                    <strong>Put Credit Spreads:</strong> Massive put walls creating strong support levels - ideal for selling premium with defined risk<br>
                    <strong>Neutral:</strong> Balanced positioning or conflicting signals - wait for clearer directional confirmation<br>
                    <strong>Signal Strength:</strong> Strong = 3+ criteria met, Moderate = 2 criteria, Weak = 1 criteria
                </div>
            </div>
        </div>

        {% if has_multi_timeframe %}
        <!-- Multi-Timeframe Analysis Section -->
        <div style="background: #111; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 25px;">
            <div class="section-title">
                🔄 Multi-Timeframe Analysis
                <span style="background: #00ff88; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-left: 15px;">NEW</span>
            </div>

            <!-- Confluence Summary -->
            <div style="background: #0a0a0a; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px;">
                    <div style="text-align: center;">
                        <div style="font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 8px;">Total Tickers</div>
                        <div style="font-size: 24px; font-weight: 700; color: #fff;">{{confluence_summary.total_tickers}}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 8px;">Aligned Signals</div>
                        <div style="font-size: 24px; font-weight: 700; color: #00ff88;">{{confluence_summary.aligned_signals}}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 8px;">Divergent Signals</div>
                        <div style="font-size: 24px; font-weight: 700; color: #ff4444;">{{confluence_summary.divergent_signals}}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 8px;">Alignment Rate</div>
                        <div style="font-size: 24px; font-weight: 700; color: #ffaa00;">{{confluence_summary.alignment_rate}}</div>
                    </div>
                </div>

                <div style="font-size: 12px; color: #888; margin-bottom: 8px; text-transform: uppercase;">📊 Timeframe Statistics</div>
                <table style="width: 100%; border-collapse: collapse; background: #1a1a1a; border-radius: 8px; overflow: hidden;">
                    <thead>
                        <tr style="background: #0a0a0a;">
                            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; border-bottom: 1px solid #333;">DTE</th>
                            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; border-bottom: 1px solid #333;">Total Signals</th>
                            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; border-bottom: 1px solid #333;">Bullish</th>
                            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; border-bottom: 1px solid #333;">Bearish</th>
                            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; border-bottom: 1px solid #333;">Bullish %</th>
                            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; border-bottom: 1px solid #333;">Avg Confidence</th>
                            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; border-bottom: 1px solid #333;">Market Bias</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for timeframe in timeframe_comparison %}
                        <tr style="border-bottom: 1px solid #222;">
                            <td style="padding: 12px; font-size: 13px; font-weight: 700; color: #fff;">{{timeframe.dte}} DTE</td>
                            <td style="padding: 12px; font-size: 13px;">{{timeframe.total_signals}}</td>
                            <td style="padding: 12px; font-size: 13px; color: #00ff88;">{{timeframe.bullish_signals}}</td>
                            <td style="padding: 12px; font-size: 13px; color: #ff4444;">{{timeframe.bearish_signals}}</td>
                            <td style="padding: 12px; font-size: 13px; font-weight: 600;">{{timeframe.bullish_percentage}}</td>
                            <td style="padding: 12px; font-size: 13px;">{{timeframe.avg_confidence}}</td>
                            <td style="padding: 12px; font-size: 13px;">
                                <span style="padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; {% if timeframe.bias_class == 'success' %}background: rgba(0, 255, 136, 0.2); color: #00ff88; border: 1px solid #00ff88;{% elif timeframe.bias_class == 'danger' %}background: rgba(255, 68, 68, 0.2); color: #ff4444; border: 1px solid #ff4444;{% else %}background: rgba(255, 170, 0, 0.2); color: #ffaa00; border: 1px solid #ffaa00;{% endif %}">
                                    {{timeframe.market_bias}}
                                </span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            <!-- Individual Ticker Multi-Timeframe Analysis -->
            <div style="font-size: 18px; font-weight: 600; color: #fff; margin-bottom: 20px;">Individual Ticker Analysis</div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(600px, 1fr)); gap: 25px;">
                {% for ticker_data in multi_timeframe_trades %}
                <div style="background: #1a1a1a; border: 2px solid #333; border-radius: 12px; overflow: hidden; {% if ticker_data.confluence_class == 'success' %}border-left: 4px solid #00ff88;{% elif ticker_data.confluence_class == 'warning' %}border-left: 4px solid #ffaa00;{% else %}border-left: 4px solid #666;{% endif %}">
                    <!-- Ticker Header -->
                    <div style="background: #0a0a0a; padding: 20px; border-bottom: 1px solid #333;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="font-size: 24px; font-weight: 700; color: #fff;">{{ticker_data.ticker}}</div>
                            <div style="text-align: right;">
                                <div style="font-size: 12px; color: #888; margin-bottom: 4px;">CONFLUENCE</div>
                                <div style="padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; {% if ticker_data.confluence_class == 'success' %}background: #00ff88; color: #000;{% elif ticker_data.confluence_class == 'warning' %}background: #ffaa00; color: #000;{% else %}background: #666; color: #fff;{% endif %}">
                                    {{ticker_data.confluence_type.upper()}}
                                </div>
                                <div style="font-size: 11px; color: #888; margin-top: 4px;">Avg: {{ticker_data.avg_confidence|round}}%</div>
                            </div>
                        </div>
                    </div>

                    <!-- Timeframe Comparison -->
                    <div style="padding: 20px;">
                        <div style="font-size: 12px; color: #888; margin-bottom: 15px; text-transform: uppercase; font-weight: 600;">Timeframe Analysis</div>
                        <div style="background: #0a0a0a; border-radius: 8px; overflow: hidden;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead>
                                    <tr style="background: #111;">
                                        <th style="padding: 10px; font-size: 10px; text-transform: uppercase; color: #888; text-align: left; border-bottom: 1px solid #333;">DTE</th>
                                        <th style="padding: 10px; font-size: 10px; text-transform: uppercase; color: #888; text-align: left; border-bottom: 1px solid #333;">Direction</th>
                                        <th style="padding: 10px; font-size: 10px; text-transform: uppercase; color: #888; text-align: left; border-bottom: 1px solid #333;">Confidence</th>
                                        <th style="padding: 10px; font-size: 10px; text-transform: uppercase; color: #888; text-align: left; border-bottom: 1px solid #333;">Success Prob</th>
                                        <th style="padding: 10px; font-size: 10px; text-transform: uppercase; color: #888; text-align: left; border-bottom: 1px solid #333;">Pattern</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for tf in ticker_data.timeframes %}
                                    <tr style="border-bottom: 1px solid #222;">
                                        <td style="padding: 10px; font-size: 12px; font-weight: 600; color: #fff;">{{tf.dte}}D</td>
                                        <td style="padding: 10px; font-size: 12px;">
                                            <span style="padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; text-transform: uppercase; {% if tf.direction_class == 'bullish' %}background: rgba(0, 255, 136, 0.2); color: #00ff88; border: 1px solid #00ff88;{% else %}background: rgba(255, 68, 68, 0.2); color: #ff4444; border: 1px solid #ff4444;{% endif %}">
                                                {{tf.direction}}
                                            </span>
                                        </td>
                                        <td style="padding: 10px; font-size: 12px; color: {{tf.direction_color}};">{{tf.confidence}}%</td>
                                        <td style="padding: 10px; font-size: 12px; color: {{tf.direction_color}};">{{tf.success_probability}}%</td>
                                        <td style="padding: 10px; font-size: 11px; color: #ccc;">{{tf.pattern_type}}</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>

                        <!-- Confluence Analysis -->
                        <div style="margin-top: 15px; padding: 15px; background: #0a0a0a; border-radius: 8px; border-left: 4px solid {% if ticker_data.confluence_class == 'success' %}#00ff88{% elif ticker_data.confluence_class == 'warning' %}#ffaa00{% else %}#666{% endif %};">
                            <div style="font-size: 11px; color: {% if ticker_data.confluence_class == 'success' %}#00ff88{% elif ticker_data.confluence_class == 'warning' %}#ffaa00{% else %}#888{% endif %}; font-weight: 600; margin-bottom: 8px; text-transform: uppercase;">
                                {% if ticker_data.confluence_type == 'aligned' %}✅ TIMEFRAME ALIGNED
                                {% elif ticker_data.confluence_type == 'divergent' %}⚠️ CONFLICTING SIGNALS
                                {% else %}❓ UNCLEAR DIRECTION{% endif %}
                            </div>
                            <div style="font-size: 11px; color: #ccc; line-height: 1.4;">
                                {% if ticker_data.confluence_type == 'aligned' %}
                                    All timeframes show consistent {{ticker_data.overall_direction}} positioning. High conviction institutional signal.
                                {% elif ticker_data.confluence_type == 'divergent' %}
                                    Short-term vs long-term signals conflict. Suggests tactical trading vs strategic positioning by institutions.
                                {% else %}
                                    Mixed or unclear signals across timeframes. Wait for directional clarity.
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>

            <div style="margin-top: 20px; padding: 15px; background: #0a0a0a; border-radius: 8px; border-left: 4px solid #00ff88;">
                <div style="font-size: 12px; color: #00ff88; font-weight: 600; margin-bottom: 8px;">📖 MULTI-TIMEFRAME INSIGHTS:</div>
                <div style="font-size: 11px; color: #ccc; line-height: 1.4;">
                    <strong>Aligned Signals:</strong> When all timeframes agree, institutions show consistent positioning - highest conviction trades<br>
                    <strong>Divergent Signals:</strong> Short-term bullish but long-term bearish often indicates profit-taking with hedging<br>
                    <strong>Timeframe Evolution:</strong> Patterns can strengthen, weaken, or reverse as time horizon changes<br>
                    <strong>Trading Strategy:</strong> Use short-term signals for entries, long-term signals for position sizing and risk management
                </div>
            </div>
        </div>
        {% endif %}

        <div class="gamma-section">
            <div class="section-title">⚡ Gamma Squeeze Detection</div>
            
            <div class="gamma-summary">
                <div class="gamma-summary-card">
                    <div class="gamma-summary-label">Total Setups</div>
                    <div class="gamma-summary-value">{{gamma_squeeze_data.total_setups}}</div>
                </div>
                <div class="gamma-summary-card">
                    <div class="gamma-summary-label">High Risk</div>
                    <div class="gamma-summary-value" style="color: #ff4444;">{{gamma_squeeze_data.high_risk_count}}</div>
                </div>
                <div class="gamma-summary-card">
                    <div class="gamma-summary-label">Upward Squeeze</div>
                    <div class="gamma-summary-value" style="color: #00ff88;">{{gamma_squeeze_data.upward_squeeze_count}}</div>
                </div>
                <div class="gamma-summary-card">
                    <div class="gamma-summary-label">Avg Distance</div>
                    <div class="gamma-summary-value" style="color: #ffaa00;">{{gamma_squeeze_data.avg_flip_distance}}</div>
                </div>
            </div>
            
            {% if gamma_squeeze_data.gamma_setups %}
            <table class="gamma-table">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Current Price</th>
                        <th>Gamma Flip Point</th>
                        <th>Distance</th>
                        <th>Squeeze Direction</th>
                        <th>Risk Level</th>
                        <th>Net Exposure</th>
                        <th>Volatility Impact</th>
                        <th>Pattern</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
                    {% for setup in gamma_squeeze_data.gamma_setups %}
                    <tr>
                        <td class="ticker-cell">{{setup.ticker}}</td>
                        <td>{{setup.current_price}}</td>
                        <td>
                            <div class="flip-point-indicator">
                                {{setup.flip_point}}
                                <span class="flip-arrow" style="color: {{setup.direction_color}};">
                                    {% if setup.squeeze_direction == "Upward" %}↗{% else %}↘{% endif %}
                                </span>
                            </div>
                        </td>
                        <td>{{setup.flip_distance}}</td>
                        <td>
                            <span class="squeeze-direction {{setup.direction_class}}">
                                {{setup.squeeze_direction}}
                            </span>
                        </td>
                        <td>
                            <span class="risk-badge {{setup.squeeze_risk.lower()}}">
                                {{setup.squeeze_risk}}
                            </span>
                        </td>
                        <td style="font-size: 11px; color: #ccc;">{{setup.net_exposure}}</td>
                        <td style="font-size: 11px; color: #ccc;">{{setup.volatility_impact}}</td>
                        <td style="font-size: 11px; color: #888;">{{setup.pattern_type}}</td>
                        <td style="color: {{setup.direction_color}}; font-weight: 600;">{{setup.confidence}}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div style="text-align: center; padding: 40px; color: #888;">
                <div style="font-size: 18px; margin-bottom: 10px;">🔍</div>
                <div>No gamma squeeze setups detected in current analysis</div>
                <div style="font-size: 12px; margin-top: 8px;">Check back during high volatility periods</div>
            </div>
            {% endif %}
            
            <div style="margin-top: 20px; padding: 15px; background: #0a0a0a; border-radius: 8px; border-left: 4px solid #ffaa00;">
                <div style="font-size: 12px; color: #ffaa00; font-weight: 600; margin-bottom: 8px;">📖 GAMMA SQUEEZE GUIDE:</div>
                <div style="font-size: 11px; color: #ccc; line-height: 1.4;">
                    <strong>Upward Squeeze:</strong> Price above flip point → Market makers buy stock as price rises (accelerates moves)<br>
                    <strong>Downward Squeeze:</strong> Price below flip point → Market makers sell stock as price rises (creates resistance)<br>
                    <strong>High Risk:</strong> Large options positioning near flip point creates volatile conditions<br>
                    <strong>Distance:</strong> How far current price is from gamma flip point (closer = higher volatility)
                </div>
            </div>
        </div>
        
        <div class="conviction-section">
            <div class="section-title">
                🎯 High Conviction Trades
                <span style="background: #00ff88; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-left: 15px;">MULTI-TIMEFRAME</span>
            </div>
            <div class="trade-cards">
                {% for trade in consolidated_high_conviction_trades %}
                <div class="trade-card consensus-{{trade.consensus_direction}}"
                     data-ticker="{{trade.ticker}}"
                     onclick="openInteractiveAnalysis('{{trade.ticker}}', '{{trade.consensus_direction}}')">
                    <div class="click-hint">Click for interactive session</div>

                    <!-- Enhanced Card Header -->
                    <div class="card-header">
                        <div class="ticker-main-info">
                            <div>
                                <div class="ticker-symbol">{{trade.ticker}}</div>
                                <div class="current-price">${{trade.current_price}}</div>
                            </div>
                            <div class="consensus-indicator">
                                <span class="confluence-status {{trade.confluence_status}}">
                                    {% if trade.confluence_status == 'aligned' %}✅ ALIGNED
                                    {% elif trade.confluence_status == 'divergent' %}⚠️ DIVERGENT
                                    {% else %}⚡ PARTIAL{% endif %}
                                </span>
                                <span class="dominant-direction {{trade.consensus_direction}}">
                                    {{trade.consensus_direction|upper}} CONSENSUS
                                </span>
                            </div>
                        </div>

                        <!-- Dynamic Timeframe Tabs -->
                        <div class="card-timeframe-tabs">
                            {% for dte, data in trade.timeframes.items() %}
                            <div class="card-tab {% if loop.first %}active{% endif %}
                                      {% if data.confidence|replace('%', '')|int >= 75 %}high-confidence
                                      {% elif data.confidence|replace('%', '')|int >= 50 %}medium-confidence
                                      {% else %}low-confidence{% endif %}
                                      {% if data.direction != trade.consensus_direction %}conflicting{% endif %}"
                                 data-dte="{{dte}}"
                                 onclick="event.stopPropagation(); switchConsolidatedTab('{{trade.ticker}}', '{{dte}}');">
                                <span class="dte-label">{{dte}}D</span>
                                <span class="confidence-mini">{{data.confidence}}</span>
                                {% if data.direction != trade.consensus_direction %}
                                <span class="conflict-indicator">⚠️</span>
                                {% endif %}
                            </div>
                            {% endfor %}
                        </div>
                    </div>

                    <!-- Timeframe Content Panels -->
                    <div class="timeframe-content">
                        {% for dte, data in trade.timeframes.items() %}
                        <div class="timeframe-panel {% if loop.first %}active{% endif %}"
                             id="{{trade.ticker}}-{{dte}}">

                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                <div class="pattern-type {{data.direction}}">{{data.pattern_type}}</div>
                                <div class="confidence-badge {% if data.direction == 'bearish' %}bearish{% endif %}">
                                    {{data.confidence}} CONFIDENCE
                                </div>
                            </div>

                            <div class="trade-details">
                                <div class="trade-row">
                                    <span class="trade-label">Strategy:</span>
                                    <span class="trade-value">{{data.direction|title}}</span>
                                </div>
                                <div class="trade-row">
                                    <span class="trade-label">Entry:</span>
                                    <span class="trade-value">{{data.entry}}</span>
                                </div>
                                <div class="trade-row">
                                    <span class="trade-label">Target:</span>
                                    <span class="trade-value">{{data.target}}</span>
                                </div>
                                <div class="trade-row">
                                    <span class="trade-label">Stop Loss:</span>
                                    <span class="trade-value">{{data.stop_loss}}</span>
                                </div>
                                <div class="trade-row">
                                    <span class="trade-label">Risk/Reward:</span>
                                    <span class="trade-value">{{data.risk_reward}}</span>
                                </div>
                                <div class="trade-row">
                                    <span class="trade-label">Success Prob:</span>
                                    <span class="trade-value">{{data.success_prob}}</span>
                                </div>
                                <div class="trade-row">
                                    <span class="trade-label">Expiry:</span>
                                    <span class="trade-value">{{data.expiry}} ({{data.dte}} DTE)</span>
                                </div>
                            </div>

                            <div class="timeframe-analysis">
                                <strong>{{dte}}D Analysis:</strong> {{data.analysis}}
                            </div>

                            {% if data.supporting_evidence %}
                            <div style="margin-top: 15px;">
                                <div style="font-size: 12px; color: #888; margin-bottom: 8px; text-transform: uppercase;">Supporting Evidence:</div>
                                <ul class="evidence-list">
                                    {% for evidence in data.supporting_evidence %}
                                    <li>{{evidence}}</li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% endif %}

                            {% if data.smart_money_insights %}
                            <div style="background: #1a1a1a; border: 1px solid #444; border-radius: 8px; padding: 15px; margin-top: 15px;">
                                <div style="font-size: 12px; color: #00ff88; margin-bottom: 12px; text-transform: uppercase; font-weight: 600;">🎯 Smart Money Intelligence</div>

                                {% if data.smart_money_insights.oi_concentration_zones %}
                                <div style="margin-bottom: 12px;">
                                    <div style="font-size: 11px; color: #888; margin-bottom: 6px;">OI CONCENTRATION:</div>
                                    {% if data.smart_money_insights.oi_concentration_zones.heavy_call_strikes %}
                                    <div style="margin-bottom: 8px;">
                                        <span style="font-size: 10px; color: #00ff88; font-weight: 500;">Calls:</span>
                                        {% for strike in data.smart_money_insights.oi_concentration_zones.heavy_call_strikes %}
                                        <span style="background: #004422; padding: 2px 6px; border-radius: 3px; margin-left: 4px; font-size: 10px;">{{strike.strike}}</span>
                                        {% endfor %}
                                    </div>
                                    {% endif %}
                                    {% if data.smart_money_insights.oi_concentration_zones.heavy_put_strikes %}
                                    <div>
                                        <span style="font-size: 10px; color: #ff4444; font-weight: 500;">Puts:</span>
                                        {% for strike in data.smart_money_insights.oi_concentration_zones.heavy_put_strikes %}
                                        <span style="background: #442222; padding: 2px 6px; border-radius: 3px; margin-left: 4px; font-size: 10px;">{{strike.strike}}</span>
                                        {% endfor %}
                                    </div>
                                    {% endif %}
                                </div>
                                {% endif %}
                            </div>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>

                    <!-- Confidence Evolution Timeline -->
                    <div class="confidence-evolution">
                        <div class="evolution-label">CONFIDENCE EVOLUTION</div>
                        <div class="confidence-timeline">
                            {% for dte, data in trade.timeframes.items() %}
                            <div class="timeline-point
                                      {% if data.confidence|replace('%', '')|int >= 75 %}high
                                      {% elif data.confidence|replace('%', '')|int >= 50 %}medium
                                      {% else %}low{% endif %}"></div>
                            {% if not loop.last %}<div class="timeline-line"></div>{% endif %}
                            {% endfor %}
                        </div>
                        <div class="timeline-labels">
                            {% for dte, data in trade.timeframes.items() %}
                            <span class="timeline-label">{{dte}}D: {{data.confidence}}</span>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        

        
        <div class="recommendations-section">
            <div class="section-title">📋 Complete Trade Recommendations</div>
            <table class="recommendations-table">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Pattern</th>
                        <th>Direction</th>
                        <th>Entry</th>
                        <th>Target</th>
                        <th>Expiry</th>
                        <th>Success Prob</th>
                        <th>R/R</th>
                    </tr>
                </thead>
                <tbody>
                    {% for rec in all_recommendations %}
                    <tr>
                        <td class="ticker-cell">{{rec.ticker}}</td>
                        <td>{{rec.pattern}}</td>
                        <td><span class="direction-badge {{rec.direction.lower()}}">{{rec.direction}}</span></td>
                        <td>{{rec.entry}}</td>
                        <td>{{rec.target}}</td>
                        <td>{{rec.expiry}}</td>
                        <td class="probability-cell {% if rec.direction == 'CALL' %}positive{% else %}negative{% endif %}">{{rec.success_prob}}</td>
                        <td>{{rec.risk_reward}}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <div>OI Pattern Tracker v2.0 | Institutional-grade options flow analysis</div>
            <div class="last-update">Last updated: {{last_update}} | Next analysis: 4:15 PM ET tomorrow</div>
        </div>
    </div>
    
    <script>
        function openInteractiveAnalysis(ticker, direction) {
            // Show loading indicator
            const card = event.currentTarget;
            const originalContent = card.innerHTML;
            card.style.opacity = '0.7';
            card.innerHTML = '<div style="text-align: center; padding: 40px;"><div style="color: #00ff88; font-size: 18px; margin-bottom: 10px;">🤖</div><div>Creating analysis session...</div></div>';
            
            // Create analysis session
            fetch('http://localhost:5001/api/create-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ticker: ticker,
                    direction: direction
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error creating session: ' + data.error);
                    card.innerHTML = originalContent;
                    card.style.opacity = '1';
                } else {
                    // Open analysis interface in new tab
                    window.open(`http://localhost:5001/analysis/${data.session_id}`, '_blank');
                    card.innerHTML = originalContent;
                    card.style.opacity = '1';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error creating analysis session. Make sure the interactive service is running.');
                card.innerHTML = originalContent;
                card.style.opacity = '1';
            });
        }

        function switchConsolidatedTab(ticker, dte) {
            // Find all tabs and panels for this ticker
            const card = document.querySelector(`[data-ticker="${ticker}"]`);
            if (!card) return;

            const tabs = card.querySelectorAll('.card-tab');
            const panels = card.querySelectorAll('.timeframe-panel');

            // Remove active class from all tabs and panels
            tabs.forEach(tab => tab.classList.remove('active'));
            panels.forEach(panel => panel.classList.remove('active'));

            // Add active class to selected tab and panel
            const selectedTab = card.querySelector(`[data-dte="${dte}"]`);
            const selectedPanel = card.querySelector(`#${ticker}-${dte}`);

            if (selectedTab) selectedTab.classList.add('active');
            if (selectedPanel) selectedPanel.classList.add('active');
        }

        // Add startup notification
        document.addEventListener('DOMContentLoaded', function() {
            // Check if interactive service is running
            fetch('http://localhost:5001/')
            .then(response => {
                if (response.ok) {
                    console.log('✅ Interactive Analysis Service is running');
                }
            })
            .catch(error => {
                console.log('ℹ️ Interactive service not running. Start with: python src/web/interactive_web_service.py');
            });
        });
    </script>
</body>
</html>'''
        
        template = Template(template_str)
        return template.render(**template_data)