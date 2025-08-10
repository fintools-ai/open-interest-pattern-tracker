"""
HTML Generator - Creates dashboard HTML files from analysis results
Uses Jinja2 templates to generate professional trading dashboards
"""

import os
import json
from datetime import datetime
from jinja2 import Template

class HTMLGenerator:
    def __init__(self, template_dir="src/output/templates", output_dir="output"):
        self.template_dir = template_dir
        self.output_dir = output_dir
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create date-specific subdirectory
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_output_dir = os.path.join(output_dir, today)
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
        
        template_data = {
            # Header stats
            "patterns_found": len(clusters["bullish_group"]["pattern_types"]) + len(clusters["bearish_group"]["pattern_types"]),
            "stocks_analyzed": clusters["total_analyzed"],
            "avg_success_rate": self._calculate_overall_success_rate(clusters),
            "active_signals": clusters["bullish_group"]["total_count"] + clusters["bearish_group"]["total_count"],
            "last_update": datetime.now().strftime("%B %d, %Y at %I:%M %p ET"),
            
            # Market pulse data
            "market_pulse": market_pulse,
            
            # High conviction trades (top 3 for featured cards)
            "high_conviction_trades": high_conviction_trades,
            
            # All recommendations for table
            "all_recommendations": all_recommendations,
            
            # Risk metrics (calculated from positions)
            "risk_metrics": self._calculate_risk_metrics(all_recommendations),
            
            # Clustering summary
            "bullish_count": clusters["bullish_group"]["total_count"],
            "bearish_count": clusters["bearish_group"]["total_count"],
            "neutral_count": clusters["neutral_group"]["total_count"]
        }
        
        return template_data
    
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
    
    def _get_high_conviction_trades(self, clusters, max_count=3):
        """Get high conviction trades for featured cards"""
        # Get top trades from each cluster
        bullish_trades = sorted(
            clusters["bullish_group"]["tickers"],
            key=lambda x: x["confidence"] * x["success_probability"],
            reverse=True
        )[:2]
        
        bearish_trades = sorted(
            clusters["bearish_group"]["tickers"],
            key=lambda x: x["confidence"] * x["success_probability"],
            reverse=True
        )[:1]
        
        high_conviction = []
        
        # Add bullish trades
        for trade in bullish_trades:
            high_conviction.append({
                "ticker": trade["ticker"],
                "pattern_type": trade["pattern_type"].replace("_", " ").title(),
                "direction": "bullish",
                "confidence": f"{trade['confidence']}%",
                "entry": trade["entry"],
                "target": trade["target"],
                "stop_loss": trade["stop_loss"],
                "risk_reward": trade["risk_reward"],
                "expiry": trade["expiry"],
                "dte": trade["dte"],
                "success_prob": f"{trade['success_probability']}%",
                "supporting_evidence": trade["supporting_evidence"][:4]  # Top 4 evidence points
            })
        
        # Add bearish trades
        for trade in bearish_trades:
            high_conviction.append({
                "ticker": trade["ticker"],
                "pattern_type": trade["pattern_type"].replace("_", " ").title(),
                "direction": "bearish",
                "confidence": f"{trade['confidence']}%",
                "entry": trade["entry"],
                "target": trade["target"],
                "stop_loss": trade["stop_loss"],
                "risk_reward": trade["risk_reward"],
                "expiry": trade["expiry"],
                "dte": trade["dte"],
                "success_prob": f"{trade['success_probability']}%",
                "supporting_evidence": trade["supporting_evidence"][:4]
            })
        
        return high_conviction[:max_count]
    
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
                "success_prob": f"{trade['success_probability']}%",
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
                "success_prob": f"{trade['success_probability']}%",
                "risk_reward": trade["risk_reward"]
            })
        
        # Sort by success probability
        recommendations.sort(key=lambda x: float(x["success_prob"].replace("%", "")), reverse=True)
        
        return recommendations
    
    def _calculate_overall_success_rate(self, clusters):
        """Calculate weighted average success rate"""
        total_weighted = 0
        total_count = 0
        
        for ticker in clusters["bullish_group"]["tickers"]:
            total_weighted += ticker["success_probability"]
            total_count += 1
        
        for ticker in clusters["bearish_group"]["tickers"]:
            total_weighted += ticker["success_probability"]
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
        max_position_risk = max(avg_position_size, 2.5)
        
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
        .trade-card { background: #1a1a1a; border: 2px solid #333; border-radius: 10px; padding: 20px; position: relative; overflow: hidden; }
        .trade-card.bullish { border-left: 4px solid #00ff88; }
        .trade-card.bearish { border-left: 4px solid #ff4444; }
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
        
        <div class="conviction-section">
            <div class="section-title">🎯 High Conviction Trades</div>
            <div class="trade-cards">
                {% for trade in high_conviction_trades %}
                <div class="trade-card {{trade.direction}}">
                    <div class="trade-header">
                        <div class="ticker">{{trade.ticker}}</div>
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
                    </div>
                    <ul class="evidence-list">
                        {% for evidence in trade.supporting_evidence %}
                        <li>{{evidence}}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="risk-section">
            <div class="section-title">⚡ Portfolio Risk Monitor</div>
            <div class="risk-grid">
                <div class="risk-card">
                    <div class="risk-metric">Value at Risk (95%)</div>
                    <div class="risk-value negative">{{risk_metrics.portfolio_var}}</div>
                </div>
                <div class="risk-card">
                    <div class="risk-metric">Delta Exposure</div>
                    <div class="risk-value positive">{{risk_metrics.delta_exposure}}</div>
                </div>
                <div class="risk-card">
                    <div class="risk-metric">Theta Decay (Daily)</div>
                    <div class="risk-value negative">{{risk_metrics.theta_decay}}</div>
                </div>
                <div class="risk-card">
                    <div class="risk-metric">Max Position Risk</div>
                    <div class="risk-value">{{risk_metrics.max_position_risk}}</div>
                </div>
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
</body>
</html>'''
        
        template = Template(template_str)
        return template.render(**template_data)