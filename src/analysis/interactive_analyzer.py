"""
Interactive Analysis Service - Deep dive analysis for individual ticker results
Provides chat-like interface with Bedrock for detailed OI pattern exploration
"""

import asyncio
import json
import subprocess
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from config.settings import AWS_REGION, BEDROCK_MODEL_ID, MCP_MARKET_DATA_EXECUTABLE
from data_pipeline.redis_manager import RedisManager
from data_pipeline.collector import MCPOIClient

class InteractiveAnalysisService:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        self.model_id = BEDROCK_MODEL_ID
        self.redis_manager = RedisManager()
        self.active_sessions = {}
        
    def create_session(self, ticker: str, current_analysis: Dict[str, Any]) -> str:
        """Create new interactive analysis session with current analysis context"""
        session_id = f"{ticker}_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        
        # Simple context for interactive LLM session
        context = {
            "session_id": session_id,
            "ticker": ticker,
            "created_at": datetime.now().isoformat(),
            "current_analysis": current_analysis,
            "conversation_history": []
        }
        
        self.active_sessions[session_id] = context
        
        # Store session in Redis for persistence
        self.redis_manager.redis_client.setex(
            f"session:{session_id}",
            3600,  # 1 hour expiry
            json.dumps(context, default=str)
        )
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session context"""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Try Redis
        session_data = self.redis_manager.redis_client.get(f"session:{session_id}")
        if session_data:
            context = json.loads(session_data)
            self.active_sessions[session_id] = context
            return context
        
        return None
    
    async def analyze_query(self, session_id: str, user_query: str) -> Dict[str, Any]:
        """Process user query with LLM and live tools"""
        context = self.get_session(session_id)
        if not context:
            return {"error": "Session not found"}
        
        # Build prompt with current context
        prompt = self._build_interactive_prompt(context, user_query)
        
        # Call Bedrock with tools (LLM will decide which tools to use)
        response = await self._call_bedrock_with_tools(prompt)
        
        # Update conversation history
        context["conversation_history"].append({
            "user_query": user_query,
            "ai_response": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update session
        self._update_session(session_id, context)
        
        return {
            "response": response,
            "session_updated": True
        }
    
    
    
    
    
    
    
    
    def _build_interactive_prompt(self, context: Dict[str, Any], user_query: str) -> str:
        """Build comprehensive prompt for interactive analysis"""
        ticker = context["ticker"]
        current_analysis = context["current_analysis"]
        
        prompt = f"""You are a world-class options trading expert with 20+ years of institutional experience. You have comprehensive access to {ticker} data and LIVE MCP TOOLS for real-time analysis.

🔧 AVAILABLE TOOLS - USE THESE AS NEEDED:
1. get_live_oi_data(ticker, days=7, target_dte=30, include_news=True) - Get live OI data for ANY ticker
2. get_market_data(ticker, timeframe="1d") - Get current market data and technical indicators  
3. get_vix_context(days=5) - Get current VIX OI for market regime analysis
4. compare_tickers(primary_ticker, comparison_tickers, days=7) - Compare OI patterns between tickers

CRITICAL: When user asks for data, USE THE TOOLS to get fresh information. Don't rely only on session context.

CURRENT SESSION CONTEXT:
Ticker: {ticker}
Current Analysis: {json.dumps(current_analysis.get("smart_money_insights", {}), indent=2)}
Pattern Type: {current_analysis.get("pattern_analysis", {}).get("pattern_type", "Unknown")}
Trade Recommendation: {current_analysis.get("trade_recommendation", {}).get("direction", "Unknown")}

CONVERSATION HISTORY:
{json.dumps(context["conversation_history"][-3:], indent=2) if context["conversation_history"] else "First interaction"}

USER QUERY: "{user_query}"

INSTRUCTIONS:
1. **ACTIVELY USE TOOLS** - If user asks for any data, call the appropriate tool first
2. **Real-time Analysis** - Get fresh OI data if user asks about current conditions
3. **Comparative Analysis** - Use compare_tickers for relative analysis  
4. **Market Context** - Use get_vix_context for regime analysis
5. **Technical Updates** - Use get_market_data for current price action
6. **Deep Insights** - Combine tool results with your expertise for actionable advice
7. **Be Conversational** - This is an interactive session, be engaging and helpful

EXAMPLE TOOL USAGE:
- "Get current OI for AAPL" → use get_live_oi_data("AAPL")
- "How does AAPL compare to TSLA?" → use compare_tickers("AAPL", ["TSLA"])
- "What's the VIX setup?" → use get_vix_context()
- "Get latest price data" → use get_market_data("{ticker}")

Focus on practical trading insights that help make profitable decisions using LIVE DATA."""

        return prompt
    
    async def _call_bedrock_with_tools(self, prompt: str) -> str:
        """Call Bedrock with tool-calling capability"""
        # Define available tools for the LLM
        tools = [
            {
                "name": "get_live_oi_data",
                "description": "Get current or historical open interest data for any ticker with custom parameters",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        "days": {"type": "integer", "description": "Number of days of historical data (1-30)", "default": 7},
                        "target_dte": {"type": "integer", "description": "Target days to expiration", "default": 30},
                        "include_news": {"type": "boolean", "description": "Include news analysis", "default": True}
                    },
                    "required": ["ticker"]
                }
            },
            {
                "name": "get_market_data",
                "description": "Get current market data including prices, technical indicators, and volatility metrics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        "timeframe": {"type": "string", "description": "Timeframe for analysis", "enum": ["1m", "5m", "15m", "1h", "1d"], "default": "1d"}
                    },
                    "required": ["ticker"]
                }
            },
            {
                "name": "get_vix_context",
                "description": "Get current VIX open interest and volatility context for market regime analysis",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "description": "Days of VIX history", "default": 5}
                    }
                }
            },
            {
                "name": "compare_tickers",
                "description": "Compare open interest patterns between multiple tickers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "primary_ticker": {"type": "string", "description": "Main ticker to analyze"},
                        "comparison_tickers": {"type": "array", "items": {"type": "string"}, "description": "Other tickers to compare against"},
                        "days": {"type": "integer", "description": "Days of data for comparison", "default": 7}
                    },
                    "required": ["primary_ticker", "comparison_tickers"]
                }
            }
        ]
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "tools": tools,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Call Bedrock with tools
        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content']
        
        # Handle response - simplified to avoid tool_use validation errors
        final_response = ""
        
        for item in content:
            if item['type'] == 'text':
                final_response += item['text']
            elif item['type'] == 'tool_use':
                # For now, just acknowledge tool use without complex flow
                tool_name = item.get('name', 'unknown_tool')
                final_response += f"\n\n[Tool called: {tool_name}]\n"
                
                # Execute the tool call and include result
                try:
                    tool_result = await self._execute_tool_call(item)
                    if 'error' not in tool_result:
                        final_response += f"Tool result: {json.dumps(tool_result, indent=2)}\n"
                    else:
                        final_response += f"Tool error: {tool_result['error']}\n"
                except Exception as e:
                    final_response += f"Tool execution failed: {str(e)}\n"
        
        return final_response
    
    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool call made by LLM"""
        tool_name = tool_call['name']
        tool_input = tool_call['input']
        
        try:
            if tool_name == "get_live_oi_data":
                return await self._tool_get_live_oi_data(**tool_input)
            elif tool_name == "get_market_data":
                return await self._tool_get_market_data(**tool_input)
            elif tool_name == "get_vix_context":
                return await self._tool_get_vix_context(**tool_input)
            elif tool_name == "compare_tickers":
                return await self._tool_compare_tickers(**tool_input)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    async def _tool_get_live_oi_data(self, ticker: str, days: int = 7, target_dte: int = 30, include_news: bool = True) -> Dict[str, Any]:
        """Tool: Get live OI data via MCP service"""
        try:
            client = MCPOIClient()
            await client.start()
            
            result = await client.call_tool("analyze_open_interest", {
                "ticker": ticker,
                "days": days,
                "target_dte": target_dte,
                "include_news": include_news
            })
            
            await client.stop()
            
            # Add metadata about the call
            result["tool_metadata"] = {
                "tool": "get_live_oi_data",
                "ticker": ticker,
                "days_requested": days,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to get OI data for {ticker}: {str(e)}"}
    
    async def _tool_get_market_data(self, ticker: str, timeframe: str = "1d") -> Dict[str, Any]:
        """Tool: Get market data via MCP service"""
        try:
            # Call the market data MCP service directly
            
            init_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "interactive-analyzer", "version": "1.0.0"}
                }
            })
            
            initialized_msg = json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            })
            
            tool_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "financial_technical_analysis_tool",
                    "arguments": {"symbol": ticker}
                }
            })
            
            
            process = await asyncio.create_subprocess_exec(
                MCP_MARKET_DATA_EXECUTABLE,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            input_data = f"{init_msg}\n{initialized_msg}\n{tool_msg}\n"
            
            stdout, stderr = await process.communicate(input=input_data.encode())
            
            # Parse responses
            responses = [line for line in stdout.decode().strip().split('\n') if line.startswith('{')]
            
            if len(responses) >= 2:
                tool_response = json.loads(responses[-1])
                if "error" not in tool_response:
                    result_content = tool_response["result"]["content"][0]["text"]
                    market_data = json.loads(result_content)
                    
                    market_data["tool_metadata"] = {
                        "tool": "get_market_data",
                        "ticker": ticker,
                        "timeframe": timeframe,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    return market_data
            
            # Fallback if MCP call fails
            return {
                "ticker": ticker,
                "error": "Market data service unavailable",
                "tool_metadata": {
                    "tool": "get_market_data",
                    "ticker": ticker,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to get market data for {ticker}: {str(e)}"}
    
    async def _tool_get_vix_context(self, days: int = 5) -> Dict[str, Any]:
        """Tool: Get VIX context via MCP service"""
        try:
            client = MCPOIClient()
            await client.start()
            
            result = await client.call_tool("analyze_open_interest", {
                "ticker": "VIX",
                "days": days,
                "include_news": True
            })
            
            await client.stop()
            
            result["tool_metadata"] = {
                "tool": "get_vix_context",
                "days_requested": days,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to get VIX context: {str(e)}"}
    
    async def _tool_compare_tickers(self, primary_ticker: str, comparison_tickers: List[str], days: int = 7) -> Dict[str, Any]:
        """Tool: Compare OI patterns between tickers"""
        try:
            client = MCPOIClient()
            await client.start()
            
            # Get data for all tickers
            results = {"primary": None, "comparisons": {}}
            
            # Primary ticker
            results["primary"] = await client.call_tool("analyze_open_interest", {
                "ticker": primary_ticker,
                "days": days,
                "include_news": True
            })
            
            # Comparison tickers
            for ticker in comparison_tickers:
                try:
                    ticker_data = await client.call_tool("analyze_open_interest", {
                        "ticker": ticker,
                        "days": days,
                        "include_news": False  # Faster
                    })
                    results["comparisons"][ticker] = ticker_data
                except Exception as e:
                    results["comparisons"][ticker] = {"error": str(e)}
            
            await client.stop()
            
            results["tool_metadata"] = {
                "tool": "compare_tickers",
                "primary_ticker": primary_ticker,
                "comparison_tickers": comparison_tickers,
                "days_requested": days,
                "timestamp": datetime.now().isoformat()
            }
            
            return results
            
        except Exception as e:
            return {"error": f"Failed to compare tickers: {str(e)}"}
    
    def _update_session(self, session_id: str, context: Dict[str, Any]):
        """Update session in memory and Redis"""
        self.active_sessions[session_id] = context
        self.redis_manager.redis_client.setex(
            f"session:{session_id}",
            3600,
            json.dumps(context, default=str)
        )
    
    
    
    def close_session(self, session_id: str):
        """Close and cleanup session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Remove from Redis
        self.redis_manager.redis_client.delete(f"session:{session_id}")