"""
LLM Analyzer - Uses AWS Bedrock to analyze OI patterns and generate trade recommendations
"""

import json
import boto3
from datetime import datetime
from config.settings import AWS_REGION, BEDROCK_MODEL_ID

class LLMAnalyzer:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        self.model_id = BEDROCK_MODEL_ID
    
    async def analyze_ticker(self, ticker_data, delta_data, market_context=None, price_data=None):
        """Analyze OI data with current prices and technical zones to generate trading recommendations"""
        try:
            prompt = self._build_analysis_prompt(ticker_data, delta_data, market_context, price_data)
            
            response = await self._call_bedrock(prompt)
            
            analysis = self._parse_response(response)
            analysis["ticker"] = ticker_data.get("ticker", "UNKNOWN")
            analysis["analysis_timestamp"] = datetime.now().isoformat()
            
            # Add current price to analysis if available
            if price_data and price_data.get("current_price"):
                analysis["current_price"] = price_data["current_price"]
            
            return analysis
            
        except Exception as e:
            return {
                "ticker": ticker_data.get("ticker", "UNKNOWN"),
                "status": "error",
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }
    
    def _build_analysis_prompt(self, ticker_data, delta_data, market_context, price_data):
        """Build comprehensive analysis prompt for Bedrock with current price and technical zones"""
        ticker = ticker_data.get("ticker", "UNKNOWN")
        latest_date = max(ticker_data.get("data_by_date", {}).keys())
        current_oi = ticker_data["data_by_date"][latest_date]
        
        # Build market context section
        market_section = ""
        if market_context:
            market_section = f"""
## Market Context
- Market Regime: {market_context.get('regime', 'Unknown')}
- VIX Fear Level: {market_context.get('fear_level', 'Unknown')}
- Volatility Expectation: {market_context.get('volatility_expectation', 'Unknown')}
- Market Summary: {market_context.get('market_summary', 'No summary available')}
"""
        
        # Build price and technical zones section
        price_section = ""
        if price_data:
            current_price = price_data.get('current_price', 'Unknown')
            price_section = f"""
## Current Market Price & Technical Zones
- **Current Price**: ${current_price}
- **Price vs Max Pain**: Current ${current_price} vs Max Pain ${current_oi.get('max_pain', 'N/A')} (Distance: ${abs(float(current_price) - float(current_oi.get('max_pain', 0))):.2f})
"""
            
            # Add technical zones if available
            if price_data.get('timeframe_zones'):
                # Extract 5m zones for primary analysis
                zones_5m = price_data.get('timeframe_zones', {}).get('5m', {})
                if zones_5m and zones_5m.get('zones'):
                    price_section += "\n### Key Technical Zones (5-minute):\n"
                    for zone in zones_5m['zones'][:5]:  # Top 5 zones
                        price_section += f"- {zone['type']}: ${zone['level']:.2f} ({zone['source']}) - Strength: {zone['strength']}\n"
                
                # Add 1m zones for scalping context
                zones_1m = price_data.get('timeframe_zones', {}).get('1m', {})
                if zones_1m and zones_1m.get('zones'):
                    price_section += "\n### Scalping Zones (1-minute):\n"
                    for zone in zones_1m['zones'][:3]:  # Top 3 zones
                        price_section += f"- {zone['type']}: ${zone['level']:.2f} - {zone['source']}\n"
"""
        
        prompt = f"""# Enhanced Options Open Interest Analysis with Price Context - {latest_date}

## Analysis Target: {ticker}
{market_section}{price_section}
## Your Role
You are an expert institutional options analyst with access to current price data and technical zones. Analyze this comprehensive data to identify high-probability trading opportunities with 70%+ success rates.

Focus on:
1. **Moneyness Analysis**: Determine which strikes are ITM/ATM/OTM based on current price
2. **Pin Risk Assessment**: Calculate proximity to max OI strikes and pin risk potential
3. **Gamma Exposure**: Identify if we're near high-gamma strikes (dealer hedging zones)
4. **Strike Clustering vs Technical Zones**: Compare high OI strikes with technical support/resistance
5. **Put/Call Ratio Context**: Differentiate hedging (ITM) vs speculation (OTM)
6. **Max Pain Magnetism**: Assess likelihood of price moving toward max pain

## Current OI Data for {ticker}
- Put/Call Ratio: {current_oi.get('put_call_ratio', 'N/A')}
- Max Pain: ${current_oi.get('max_pain', 'N/A')}
- Total OI: {current_oi.get('total_oi', 'N/A'):,}
- Call OI: {current_oi.get('call_oi', 'N/A'):,}
- Put OI: {current_oi.get('put_oi', 'N/A'):,}

### Strike Data
Call Strikes: {json.dumps(current_oi.get('strikes', {}).get('calls', {}), indent=2)}
Put Strikes: {json.dumps(current_oi.get('strikes', {}).get('puts', {}), indent=2)}

## Day-over-Day Changes
- Put/Call Ratio Change: {delta_data.get('put_call_ratio_delta', 'N/A')}
- Max Pain Shift: ${delta_data.get('max_pain_shift', 'N/A')}
- Total OI Change: {delta_data.get('total_oi_change', 'N/A'):,} ({delta_data.get('total_oi_pct_change', 0):.1f}%)
- Call OI Change: {delta_data.get('call_oi_change', 'N/A'):,} ({delta_data.get('call_oi_pct_change', 0):.1f}%)
- Put OI Change: {delta_data.get('put_oi_change', 'N/A'):,} ({delta_data.get('put_oi_pct_change', 0):.1f}%)

### Large OI Increases
{json.dumps(delta_data.get('large_oi_increases', []), indent=2)}

### New Strikes
New Call Strikes: {json.dumps(delta_data.get('new_call_strikes', []), indent=2)}
New Put Strikes: {json.dumps(delta_data.get('new_put_strikes', []), indent=2)}

### Unusual Activity Flags
{json.dumps(delta_data.get('unusual_activity', []), indent=2)}

## Required Output
Return response as JSON with this EXACT structure:

{{
  "market_summary": {{
    "overall_sentiment": "Bullish/Bearish/Neutral with confidence %",
    "key_observations": ["observation1", "observation2", "observation3"],
    "risk_factors": ["risk1", "risk2"]
  }},
  "pattern_analysis": {{
    "pattern_type": "institutional_accumulation|short_squeeze_setup|gamma_squeeze_setup|distribution|protective_hedging|other",
    "pattern_strength": "strong|moderate|weak",
    "supporting_evidence": ["evidence1", "evidence2", "evidence3"],
    "confidence_score": 85
  }},
  "trade_recommendation": {{
    "direction": "CALL|PUT|NEUTRAL",
    "instrument": "Call Spread|Put Spread|Long Call|Long Put",
    "specific_entry": "Exact trade description with strikes",
    "entry_price": "$X.XX",
    "target_price": "$X.XX",
    "stop_loss": "$X.XX",
    "expiry_date": "YYYY-MM-DD",
    "days_to_expiry": X,
    "risk_reward_ratio": "1:X.X",
    "success_probability": 78,
    "position_size_pct": 2.5
  }},
  "risk_management": {{
    "primary_risks": ["risk1", "risk2"],
    "hedge_strategy": "hedge description if needed",
    "volatility_considerations": "IV analysis"
  }}
}}

CRITICAL: Only recommend trades with confidence_score >= 70 and success_probability >= 70. If confidence is below 70, set direction to "NEUTRAL".
"""
        return prompt
    
    async def _call_bedrock(self, prompt):
        """Call AWS Bedrock with the analysis prompt"""
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def _parse_response(self, response_text):
        """Parse and validate the LLM response"""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end <= json_start:
                raise ValueError("No valid JSON found in response")
            
            json_text = response_text[json_start:json_end]
            analysis = json.loads(json_text)
            
            # Validate required sections
            required_sections = ["market_summary", "pattern_analysis", "trade_recommendation"]
            for section in required_sections:
                if section not in analysis:
                    raise ValueError(f"Missing required section: {section}")
            
            # Validate confidence thresholds
            confidence = analysis["pattern_analysis"].get("confidence_score", 0)
            success_prob = analysis["trade_recommendation"].get("success_probability", 0)
            
            if confidence < 70 or success_prob < 70:
                analysis["trade_recommendation"]["direction"] = "NEUTRAL"
                if "key_observations" not in analysis["market_summary"]:
                    analysis["market_summary"]["key_observations"] = []
                analysis["market_summary"]["key_observations"].append(
                    f"Low confidence ({confidence}%) or success probability ({success_prob}%) - trade not recommended"
                )
            
            return analysis
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to parse LLM response: {str(e)}",
                "raw_response": response_text[:500]
            }