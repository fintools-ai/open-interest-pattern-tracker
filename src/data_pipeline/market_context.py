"""
Market Context Provider - Uses VIX OI data to determine market regime and context
"""

import asyncio
import json
import subprocess
from datetime import datetime
from config.settings import MCP_OI_EXECUTABLE, OI_ANALYSIS_DAYS

class MarketContextProvider:
    def __init__(self):
        self.mcp_executable = MCP_OI_EXECUTABLE
        self.vix_ticker = "VIX"
    
    async def get_market_context(self):
        """Get market context using VIX open interest data"""
        try:
            vix_data = await self._get_vix_oi_data()
            #print(json.dumps(vix_data, indent=2))
            #print("===")
            #print(f"VIX data received: {json.dumps(vix_data, indent=2) if vix_data else 'None'}")
            
            if not vix_data:
                return None
            
            context = self._analyze_vix_context(vix_data)
            if not context:
                return None
            
            print(json.dumps(context, indent=2))
            print("===")
                
            context["timestamp"] = datetime.now().isoformat()
            
            return context
            
        except Exception as e:
            print(f"Market context failed: {str(e)}")
            return None
    
    async def _get_vix_oi_data(self):
        """Get VIX open interest data via MCP service using working client"""
        from data_pipeline.collector import MCPOIClient
        
        try:
            client = MCPOIClient()
            try:
                await client.start()
                result = await client.call_tool("analyze_open_interest", {
                    "ticker": self.vix_ticker,
                    "days": OI_ANALYSIS_DAYS,
                    "include_news": True
                })
                return result
            finally:
                await client.stop()
            
        except Exception as e:
            raise Exception(f"VIX data collection failed: {str(e)}")
    
    def _analyze_vix_context(self, vix_data):
        """Analyze VIX OI data to determine market context"""
        data_by_date = vix_data.get("data_by_date", {})
        if not data_by_date:
            return {
                "source": "VIX_OI_Analysis",
                "regime": "unknown",
                "vix_put_call_ratio": 0,
                "vix_total_oi": 0,
                "vix_call_oi": 0,
                "vix_put_oi": 0,
                "fear_level": "unknown",
                "volatility_expectation": "unknown",
                "market_summary": "No VIX data available for analysis"
            }
        
        latest_date = max(data_by_date.keys())
        vix_oi = data_by_date[latest_date]
        
        # Extract from summary_metrics
        summary = vix_oi.get("summary_metrics", {})
        vix_put_call_ratio = summary.get("put_call_ratio", 0)
        vix_total_oi = summary.get("total_open_interest", 0)
        vix_call_oi = summary.get("call_open_interest", 0)
        vix_put_oi = summary.get("put_open_interest", 0)
        
        regime = self._determine_market_regime(vix_put_call_ratio)
        fear_level = self._calculate_fear_level(vix_put_call_ratio, vix_call_oi, vix_put_oi)
        
        context = {
            "source": "VIX_OI_Analysis",
            "regime": regime,
            "vix_put_call_ratio": vix_put_call_ratio,
            "vix_total_oi": vix_total_oi,
            "vix_call_oi": vix_call_oi,
            "vix_put_oi": vix_put_oi,
            "fear_level": fear_level,
            "volatility_expectation": "high" if vix_put_call_ratio < 0.8 else "low",
            "market_summary": self._generate_market_summary(regime, fear_level)
        }
        
        return context
    
    def _determine_market_regime(self, vix_pcr):
        """Determine market regime from VIX positioning"""
        if vix_pcr < 0.6:  # More VIX calls than puts
            return "bearish"  # Expecting volatility spike
        elif vix_pcr > 1.5:  # Much more VIX puts than calls
            return "bullish"  # Expecting low volatility
        else:
            return "sideways"  # Mixed signals
    
    def _calculate_fear_level(self, vix_pcr, call_oi, put_oi):
        """Calculate fear level from VIX positioning"""
        total_oi = call_oi + put_oi
        
        if total_oi == 0:
            return "unknown"
        
        call_percentage = call_oi / total_oi
        
        # High VIX call percentage = high fear
        if call_percentage > 0.6:
            return "high"
        elif call_percentage < 0.3:
            return "low"
        else:
            return "moderate"
    
    def _generate_market_summary(self, regime, fear_level):
        """Generate human-readable market summary"""
        regime_desc = {
            "bullish": "Low volatility expectation, supportive for directional trades",
            "bearish": "High volatility expectation, defensive positioning recommended", 
            "sideways": "Mixed volatility signals, range-bound environment likely"
        }
        
        fear_desc = {
            "high": "Elevated fear levels in options market",
            "moderate": "Moderate fear levels, normal market conditions",
            "low": "Low fear levels, complacent market conditions"
        }
        
        return f"{regime_desc.get(regime, 'Unknown regime')}. {fear_desc.get(fear_level, 'Unknown fear level')}."