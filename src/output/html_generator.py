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
        """Prepare data for dashboard template"""
        high_conviction_trades = self._get_high_conviction_trades(clusters, max_count=3)
        all_recommendations = self._get_all_recommendations(clusters)
        market_pulse = self._prepare_market_pulse(clusters, market_context)
        gamma_squeeze_data = self._prepare_gamma_squeeze_data(clusters)
        
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
            
            # ALL trades for featured cards
            "high_conviction_trades": high_conviction_trades,
            
            # All recommendations for table
            "all_recommendations": all_recommendations,
            
            # Risk metrics (calculated from positions)
            "risk_metrics": self._calculate_risk_metrics(all_recommendations),
            
            # Clustering summary
            "bullish_count": clusters["bullish_group"]["total_count"],
            "bearish_count": clusters["bearish_group"]["total_count"]
        }
        
        return template_data
    
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
        .trade-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .trade-card { background: #1a1a1a; border: 2px solid #333; border-radius: 10px; padding: 20px; position: relative; overflow: hidden; cursor: pointer; transition: all 0.3s ease; }
        .trade-card:hover { border-color: #00ff88; box-shadow: 0 5px 20px rgba(0, 255, 136, 0.2); transform: translateY(-2px); }
        .trade-card.bullish { border-left: 4px solid #00ff88; }
        .trade-card.bearish { border-left: 4px solid #ff4444; }
        .trade-card.bearish:hover { border-color: #ff4444; box-shadow: 0 5px 20px rgba(255, 68, 68, 0.2); }
        .interactive-badge { position: absolute; top: 10px; right: 10px; background: rgba(0, 255, 136, 0.2); color: #00ff88; padding: 4px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; border: 1px solid #00ff88; }
        .click-hint { position: absolute; bottom: 10px; right: 15px; color: #666; font-size: 11px; opacity: 0; transition: opacity 0.3s ease; }
        .trade-card:hover .click-hint { opacity: 1; }

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
            <div class="section-title">🎯 High Conviction Trades</div>
            <div class="trade-cards">
                {% for trade in high_conviction_trades %}
                <div class="trade-card {{trade.direction}}" onclick="openDeepAnalysis('{{trade.ticker}}', '{{trade.direction}}')">
                    <div class="interactive-badge">🔍 DEEP ANALYSIS</div>
                    <div class="click-hint">Click for interactive session</div>
                    <div class="trade-header">
                        <div class="ticker">{{trade.ticker}} <span style="font-size: 16px; color: #888; font-weight: 400;">${{trade.current_price}}</span></div>
                        <div class="confidence-badge {% if trade.direction == 'bearish' %}bearish{% endif %}">{{trade.confidence}} CONFIDENCE</div>
                    </div>
                    <div class="pattern-type {% if trade.direction == 'bearish' %}bearish{% endif %}">{{trade.pattern_type}}</div>
                    <div class="trade-details">
                        <div class="trade-row">
                            <span class="trade-label">Entry:</span>
                            <span class="trade-value">{{trade.entry}}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Target:</span>
                            <span class="trade-value">{{trade.target}}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Stop Loss:</span>
                            <span class="trade-value">{{trade.stop_loss}}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Risk/Reward:</span>
                            <span class="trade-value">{{trade.risk_reward}}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Expiry:</span>
                            <span class="trade-value">{{trade.expiry}} ({{trade.dte}} DTE)</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Success Probability:</span>
                            <span class="trade-value {% if trade.direction == 'bullish' %}positive{% else %}negative{% endif %}">{{trade.success_prob}}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Timeframe Confluence:</span>
                            <span class="trade-value">{{trade.timeframe_confluence}}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Volatility Regime:</span>
                            <span class="trade-value">{{trade.volatility_regime}}</span>
                        </div>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <div style="font-size: 12px; color: #888; margin-bottom: 8px; text-transform: uppercase;">Smart Money Analysis:</div>
                        <div style="font-size: 12px; color: #ccc; margin-bottom: 8px;">{{trade.institutional_flow}}</div>
                        <div style="font-size: 11px; color: #aaa;">{{trade.smart_money_thesis}}</div>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <div style="font-size: 12px; color: #888; margin-bottom: 8px; text-transform: uppercase;">Entry Triggers:</div>
                        <div style="font-size: 12px; color: #ccc;">
                            {% for trigger in trade.entry_triggers %}
                            <span style="background: #333; padding: 2px 8px; border-radius: 4px; margin-right: 8px; margin-bottom: 4px; display: inline-block;">{{trigger}}</span>
                            {% endfor %}
                        </div>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <div style="font-size: 12px; color: #888; margin-bottom: 8px; text-transform: uppercase;">Key Levels:</div>
                        <div style="font-size: 12px; color: #ccc;">
                            <span style="background: #1a4d1a; padding: 2px 8px; border-radius: 4px; margin-right: 8px;">Support: {{trade.technical_levels.support}}</span>
                            <span style="background: #4d1a1a; padding: 2px 8px; border-radius: 4px; margin-right: 8px;">Resistance: {{trade.technical_levels.resistance}}</span>
                            <span style="background: #4d4d1a; padding: 2px 8px; border-radius: 4px;">Pivot: {{trade.technical_levels.pivot}}</span>
                        </div>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <div style="font-size: 12px; color: #888; margin-bottom: 8px; text-transform: uppercase;">Supporting Evidence:</div>
                        <ul class="evidence-list">
                            {% for evidence in trade.supporting_evidence %}
                            <li>{{evidence}}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% if trade.smart_money_insights %}
                    <div class="smart-money-section" style="background: #1a1a1a; border: 1px solid #444; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                        <div style="font-size: 12px; color: #00ff88; margin-bottom: 12px; text-transform: uppercase; font-weight: 600;">🎯 Smart Money Intelligence</div>
                        
                        {% if trade.smart_money_insights.oi_concentration_zones %}
                        <div style="margin-bottom: 12px;">
                            <div style="font-size: 11px; color: #888; margin-bottom: 6px;">OI CONCENTRATION ANALYSIS:</div>
                            <div style="font-size: 11px; color: #ddd;">{{trade.smart_money_insights.oi_concentration_zones.concentration_analysis}}</div>
                            {% if trade.smart_money_insights.oi_concentration_zones.heavy_call_strikes %}
                            <div style="margin-top: 8px;">
                                <span style="font-size: 10px; color: #00ff88; font-weight: 500;">Heavy Call Strikes:</span>
                                {% for strike in trade.smart_money_insights.oi_concentration_zones.heavy_call_strikes %}
                                <span style="background: #004422; padding: 2px 6px; border-radius: 3px; margin-left: 4px; font-size: 10px;">{{strike.strike}} ({{strike.oi}})</span>
                                {% endfor %}
                            </div>
                            {% endif %}
                            {% if trade.smart_money_insights.oi_concentration_zones.heavy_put_strikes %}
                            <div style="margin-top: 8px;">
                                <span style="font-size: 10px; color: #ff4444; font-weight: 500;">Heavy Put Strikes:</span>
                                {% for strike in trade.smart_money_insights.oi_concentration_zones.heavy_put_strikes %}
                                <span style="background: #442222; padding: 2px 6px; border-radius: 3px; margin-left: 4px; font-size: 10px;">{{strike.strike}} ({{strike.oi}})</span>
                                {% endfor %}
                            </div>
                            {% endif %}
                        </div>
                        {% endif %}
                        
                        {% if trade.smart_money_insights.flow_analysis %}
                        <div style="margin-bottom: 12px;">
                            <div style="font-size: 11px; color: #888; margin-bottom: 6px;">FLOW ANALYSIS:</div>
                            <div style="font-size: 11px; color: #ddd;">{{trade.smart_money_insights.flow_analysis.net_positioning}}</div>
                            {% if trade.smart_money_insights.flow_analysis.large_blocks %}
                            <div style="margin-top: 4px;">
                                {% for block in trade.smart_money_insights.flow_analysis.large_blocks %}
                                <div style="font-size: 10px; color: #ccc;">• {{block}}</div>
                                {% endfor %}
                            </div>
                            {% endif %}
                        </div>
                        {% endif %}
                        
                        {% if trade.smart_money_insights.put_call_dynamics %}
                        <div style="margin-bottom: 12px;">
                            <div style="font-size: 11px; color: #888; margin-bottom: 6px;">PUT/CALL DYNAMICS:</div>
                            <div style="font-size: 11px; color: #ddd;">
                                <span style="color: #ffaa00;">Ratio: {{trade.smart_money_insights.put_call_dynamics.ratio}}</span>
                                <span style="margin-left: 15px; color: #00ff88;">Change: {{trade.smart_money_insights.put_call_dynamics.change}}</span>
                            </div>
                            <div style="font-size: 10px; color: #ccc; margin-top: 4px;">{{trade.smart_money_insights.put_call_dynamics.smart_money_view}}</div>
                        </div>
                        {% endif %}
                        
                        {% if trade.smart_money_insights.max_pain_analysis %}
                        <div style="margin-bottom: 12px;">
                            <div style="font-size: 11px; color: #888; margin-bottom: 6px;">MAX PAIN ANALYSIS:</div>
                            <div style="font-size: 11px; color: #ddd;">
                                <span style="color: #ffaa00;">Level: ${{trade.smart_money_insights.max_pain_analysis.level}}</span>
                                <span style="margin-left: 15px; color: #ff4444;">Pin Risk: {{trade.smart_money_insights.max_pain_analysis.pin_risk}}</span>
                            </div>
                            <div style="font-size: 10px; color: #ccc; margin-top: 4px;">{{trade.smart_money_insights.max_pain_analysis.dealer_impact}}</div>
                        </div>
                        {% endif %}
                        
                        {% if trade.smart_money_insights.gamma_analysis %}
                        <div style="margin-bottom: 8px;">
                            <div style="font-size: 11px; color: #888; margin-bottom: 6px;">GAMMA EXPOSURE:</div>
                            <div style="font-size: 11px; color: #ddd;">
                                <span style="color: #00ff88;">{{trade.smart_money_insights.gamma_analysis.net_exposure}}</span>
                                <span style="margin-left: 15px; color: #ffaa00;">Squeeze Risk: {{trade.smart_money_insights.gamma_analysis.squeeze_risk}}</span>
                            </div>
                            {% if trade.smart_money_insights.gamma_analysis.flip_point %}
                            <div style="margin-top: 6px; font-size: 10px; color: #ccc;">
                                <span style="color: #888;">Gamma Flip:</span> 
                                <span style="color: #ffaa00; font-weight: 500;">${{trade.smart_money_insights.gamma_analysis.flip_point}}</span>
                                <span style="margin-left: 10px; color: #888;">Impact:</span>
                                <span style="color: #ccc;">{{trade.smart_money_insights.gamma_analysis.volatility_impact}}</span>
                            </div>
                            {% endif %}
                        </div>
                        {% endif %}
                    </div>
                    {% endif %}
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
        function openDeepAnalysis(ticker, direction) {
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
        
        // Add startup notification
        document.addEventListener('DOMContentLoaded', function() {
            // Check if interactive service is running
            fetch('http://localhost:5001/')
            .then(response => {
                if (response.ok) {
                    console.log('✅ Interactive Analysis Service is running');
                    // Add visual indicator that deep analysis is available
                    const badge = document.createElement('div');
                    badge.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(0, 255, 136, 0.9); color: #000; padding: 8px 15px; border-radius: 20px; font-size: 12px; font-weight: 600; z-index: 1000; box-shadow: 0 4px 15px rgba(0, 255, 136, 0.3);';
                    badge.textContent = '🔍 Deep Analysis Available';
                    document.body.appendChild(badge);
                    
                    // Auto-hide after 5 seconds
                    setTimeout(() => {
                        badge.style.opacity = '0';
                        badge.style.transition = 'opacity 0.5s ease';
                        setTimeout(() => badge.remove(), 500);
                    }, 5000);
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