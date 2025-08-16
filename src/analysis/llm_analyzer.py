"""
LLM Analyzer - Uses AWS Bedrock to analyze OI patterns and generate trade recommendations
"""

import json
import boto3
from datetime import datetime
from config.settings import AWS_REGION, BEDROCK_MODEL_ID, TARGET_DTE

class LLMAnalyzer:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        self.model_id = BEDROCK_MODEL_ID
    
    def analyze_ticker(self, ticker_data, delta_data, market_context=None, price_data=None):
        """Analyze OI data with current prices and technical zones to generate trading recommendations"""
        try:
            prompt = self._build_analysis_prompt(ticker_data, delta_data, market_context, price_data)
            
            #print(prompt)
            #print("--------------------------------------------------")
            response = self._call_bedrock(prompt)
            
            analysis = self._parse_response(response)
            analysis["ticker"] = ticker_data.get("ticker", "UNKNOWN")
            analysis["analysis_timestamp"] = datetime.now().isoformat()
            

            
            # Let LLM extract current price from market data
            # Current price will be filled by LLM from the market data provided
            
            return analysis
            
        except Exception as e:
            return {
                "ticker": ticker_data.get("ticker", "UNKNOWN"),
                "status": "error",
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }
    
    def _build_analysis_prompt(self, ticker_data, delta_data, market_context, price_data):
        """Build simple prompt with raw data dumps"""
        ticker = ticker_data.get("ticker", "UNKNOWN")
        
        prompt = f"""You are a professional options trader with 15+ years experience. Analyze this comprehensive dataset for {ticker} like you're preparing a trading desk report.

IMPORTANT: Use exactly {TARGET_DTE} days to expiration (DTE) for all recommendations.

# RAW DATA

## Open Interest Data:
{json.dumps(ticker_data, indent=2)}

## Delta Changes:
{json.dumps(delta_data, indent=2)}

## Market Context (VIX, etc):
{json.dumps(market_context, indent=2) if market_context else 'None'}

## Multi-Timeframe Technical Analysis:
{json.dumps(price_data, indent=2) if price_data else 'None'}

# PROFESSIONAL ANALYSIS REQUIREMENTS

You are a quantitative options analyst specializing in institutional open interest analysis. Your task is to analyze open interest data across multiple dates to identify high-conviction trading opportunities.

When analyzing open interest data:
1. Look for unusual options activity and large positions
2. Identify key support and resistance levels from strike concentrations
3. Calculate directional bias from put/call ratios and flow
4. Consider news context when interpreting the data
5. Provide specific, actionable trading recommendations with exact strikes and expiration dates


# CRITICAL / MOST IMPORTANT
Use Open interest data as the primary source of analysis, use the technical data just for reference, but they are not the main deciding factor. The goal is to get as much insight from
open interest data, this is the most critical data and all analysis should be based on this data set ONLY.

**CRITICAL**: Pay special attention to OI delta changes, unusual strike activity, and institutional positioning clues. The technical analysis should SUPPORT the OI story, not lead it.


## PRIMARY FOCUS - SMART MONEY DETECTION:
1. **OI Flow Analysis**: Decode what institutions are doing - are they accumulating, distributing, or hedging?
2. **Strike Concentration**: Which strikes have unusual OI buildup? What does this tell us about expected moves?
3. **Put/Call OI Shifts**: How are institutional put/call ratios changing? What's the hedging story?
4. **Volume vs OI**: Are we seeing new positions (high volume, rising OI) or position unwinding?
5. **Dark Pool Signals**: Large block OI changes without corresponding volume = institutional stealth positioning
6. **Dealer Positioning**: How are market makers positioned? Where will they hedge?
7. **Institutional Footprints**: Large block trades, unusual strike clustering, gamma exposure zones
8. **Smart Money Timing**: When are institutions entering positions? Pre-earnings, pre-events?

## SECONDARY ANALYSIS:
6. **Multi-Timeframe Confluence**: How do 1m, 5m, 1d technicals align with OI patterns?
7. **Risk/Reward Assessment**: Precise entry, stops, targets based on technical levels
8. **Market Regime Context**: How does current volatility environment affect this setup?
9. **Position Management**: Specific rules for trade management and adjustments


CRITICAL OUTPUT FORMATTING RULES:
1. For ALL price fields (entry_price, target_price, stop_loss), use STOCK PRICES not option premiums
2. Provide ONLY numeric values without $ signs (e.g., 175.50 not $175.50)
3. For percentage fields, provide ONLY numeric values without % signs (e.g., 75 not 75%)
4. entry_price = the STOCK price level for entering the trade
5. target_price = the STOCK price target where you'd take profits
6. stop_loss = the STOCK price level where you'd exit at a loss
7. Extract current stock price from technical data and put in current_price as plain number

IMPORTANT: ALL prices should be STOCK prices, not option premiums. This makes it clear where the underlying stock should be for entry/exit.

## MANDATORY TRADING STRATEGY RULES:
1. **ONLY use these 3 trade types**: Buy Call, Buy Put, Put Credit Spread
2. **Buy Call**: When smart money is accumulating calls, gamma squeeze setup, or strong bullish OI flow
3. **Buy Put**: When smart money is accumulating puts, distribution detected, or strong bearish OI flow  
4. **Put Credit Spread**: When high put OI concentration suggests support level, or neutral-to-bullish bias with high IV

## CRITICAL REQUIREMENT - NO EXCEPTIONS:
You MUST provide a trade recommendation for THIS ticker regardless of:
- Data quality concerns
- Low confidence scores
- Uncertain market conditions
- Missing information
Even if you have minimal data, analyze what's available and pick the MOST LIKELY direction based on any OI patterns you can detect.

Return JSON with this enhanced structure that extracts MAXIMUM intelligence from the open interest data:



{{
  "market_summary": {{
    "overall_sentiment": "Bullish/Bearish/Neutral with confidence %",
    "key_observations": ["observation1", "observation2"],
    "risk_factors": ["risk1", "risk2"],
    "institutional_flow": "Smart money positioning analysis",
    "volatility_regime": "High/Medium/Low volatility environment",
    "smart_money_thesis": "What institutions are positioning for based on OI"
  }},
  "pattern_analysis": {{
    "pattern_type": "institutional_accumulation|short_squeeze_setup|gamma_squeeze_setup|distribution|protective_hedging|other",
    "pattern_strength": "strong|moderate|weak",
    "supporting_evidence": ["evidence1", "evidence2"],
    "confidence_score": "Calculate based on OI strength and technical confluence",
    "oi_intelligence": {{
      "strike_concentration": "Key strikes with unusual OI buildup",
      "flow_direction": "Institutional buying/selling/hedging",
      "position_type": "New positions vs unwinding vs rolling",
      "size_significance": "Large/medium/small institutional footprint"
    }}
  }},
  "trade_recommendation": {{
    "direction": "CALL|PUT",
    "instrument": "Buy Call|Buy Put|Put Credit Spread",
    "specific_entry": "Detailed trade description with strike selection rationale - ONLY use Buy Call, Buy Put, or Put Credit Spread strategies",
    "entry_price": 175.50,
    "target_price": 185.00,
    "stop_loss": 170.00,
    "expiry_date": "YYYY-MM-DD",
    "days_to_expiry": {TARGET_DTE},
    "risk_reward_ratio": "1:2.0",
    "success_probability": 75,
    "position_size_pct": 2.5,
    "current_price": 176.25,
    "timeframe_confluence": "1m/5m/1d alignment analysis",
    "entry_triggers": ["trigger1", "trigger2"],
    "exit_strategy": "Detailed exit plan"
  }},
  "risk_management": {{
    "primary_risks": ["risk1", "risk2"],
    "hedge_strategy": "hedge description",
    "volatility_considerations": "IV analysis",
    "position_adjustments": "When and how to adjust",
    "correlation_risks": "Portfolio correlation analysis"
  }},
  "technical_analysis": {{
    "multi_timeframe_summary": "1m/5m/1d trend alignment",
    "key_levels": {{
      "support": "$X.XX",
      "resistance": "$X.XX",
      "pivot": "$X.XX"
    }},
    "momentum_indicators": "RSI/MACD/Stoch analysis",
    "volume_analysis": "OBV/CMF institutional flow",
    "volatility_metrics": "ATR/IV analysis"
  }},
  "smart_money_insights": {{
    "oi_concentration_zones": {{
      "heavy_call_strikes": [
        {{"strike": 640, "oi": 42885, "interpretation": "Major resistance/profit target"}},
        {{"strike": 645, "oi": 27423, "interpretation": "Secondary target level"}}
      ],
      "heavy_put_strikes": [
        {{"strike": 620, "oi": 58882, "interpretation": "Major support/hedge level"}},
        {{"strike": 610, "oi": 119307, "interpretation": "Institutional protection zone"}}
      ],
      "concentration_analysis": "Describe what the strike clustering reveals"
    }},
    "flow_analysis": {{
      "net_positioning": "Bullish/Bearish based on OI changes - be explicit: BULLISH_CALL_ACCUMULATION, BEARISH_PUT_ACCUMULATION, or NEUTRAL_MIXED",
      "large_blocks": ["Large OI additions at specific strikes"],
      "unusual_activity": ["Unusual patterns detected"],
      "dark_pool_signals": "Stealth positioning if detected",
      "directional_bias": "CALL_HEAVY (more call than put activity) | PUT_HEAVY (more put than call activity) | BALANCED"
    }},
    "put_call_dynamics": {{
      "ratio": 1.21,
      "change": -0.05,
      "interpretation": "What the P/C ratio reveals",
      "smart_money_view": "Institutional hedging vs directional bets",
      "signal_classification": "BULLISH_CALLS (ratio < 0.5) | BEARISH_PUTS (ratio > 1.5) | NEUTRAL (0.5-1.5)"
    }},
    "max_pain_analysis": {{
      "level": 634.0,
      "shift": 2.0,
      "pin_risk": "High/Medium/Low",
      "dealer_impact": "How dealers will hedge"
    }},
    "gamma_analysis": {{
      "net_exposure": "Positive/Negative gamma zones with detailed explanation",
      "flip_point": 632.5,
      "squeeze_risk": "High/Medium/Low",
      "volatility_impact": "Expected volatility behavior and market maker hedging impact",
      "squeeze_direction": "Upward/Downward based on current price vs flip point", 
      "gamma_profile": "Distribution of gamma across strikes",
      "dealer_positioning": "How market makers will hedge and impact price action",
      "squeeze_catalyst": "What could trigger the gamma squeeze (earnings, news, etc.)"
    }}
  }}
}}

## SIGNAL CATEGORIZATION GUIDANCE:
When analyzing data, pay special attention to these signal thresholds for dashboard categorization:

**BULLISH CALL SIGNALS:**
- Put/Call ratio < 0.5 (strong call bias)
- Heavy call OI concentration 10-20% OTM
- Net positioning shows "BULLISH_CALL_ACCUMULATION"
- Pattern types: "institutional_accumulation", "gamma_squeeze_setup"

**BEARISH PUT SIGNALS:**
- Put/Call ratio > 1.5 (strong put bias)
- Heavy put OI at current price levels or ITM
- Net positioning shows "BEARISH_PUT_ACCUMULATION"
- Pattern types: "distribution", "protective_hedging"

**CRITICAL:** Ensure put_call_dynamics.ratio is always a numeric value (e.g., 1.21, 0.45, 2.3) for proper signal processing.

CRITICAL: You MUST classify every ticker as either CALL or PUT direction - NO NEUTRAL allowed. Even if confidence is low, pick the most likely direction based on the data. Provide analysis and recommendations for ALL tickers regardless of confidence or success probability.
"""
        return prompt
    
    def _call_bedrock(self, prompt):
        """Call AWS Bedrock with the analysis prompt"""
        print("Calling Bedrock with prompt: ", prompt[:100])

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
            
            # Convert to int if they're numeric, otherwise skip validation
            try:
                confidence = int(confidence) if isinstance(confidence, (int, float, str)) and str(confidence).isdigit() else 0
                success_prob = int(success_prob) if isinstance(success_prob, (int, float, str)) and str(success_prob).isdigit() else 0
            except (ValueError, TypeError):
                confidence = 0
                success_prob = 0
            
            # No filtering - show all recommendations regardless of confidence/success probability
            
            return analysis
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to parse LLM response: {str(e)}",
                "raw_response": response_text[:500]
            }