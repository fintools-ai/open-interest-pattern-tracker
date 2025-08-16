"""
Interactive Analysis Service - Professional OI Pattern Analysis Agent
Provides chat-like interface with Bedrock Converse API for intelligent OI analysis
"""

import asyncio
import json
import logging
import time
import uuid
import boto3
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from botocore.config import Config
from config.settings import AWS_REGION, BEDROCK_MODEL_ID, MCP_MARKET_DATA_EXECUTABLE
from data_pipeline.redis_manager import RedisManager
from data_pipeline.collector import MCPOIClient

logger = logging.getLogger("oi_tracker.interactive_analyzer")


class InteractiveAnalysisService:
    """
    Professional OI Pattern Analysis Agent
    Based on VTS Agent architecture with Bedrock Converse API
    """
    
    def __init__(self, max_workers=10, timeout=300):
        """Initialize the analysis service with proper Bedrock client"""
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=AWS_REGION,
            config=Config(connect_timeout=240, read_timeout=240))

        self.model_id = BEDROCK_MODEL_ID
        self.redis_manager = RedisManager()
        self.active_sessions = {}
        self.max_workers = max_workers
        self.default_timeout = timeout
        
    def create_session(self, ticker: str, current_analysis: Dict[str, Any]) -> str:
        """Create new interactive analysis session with current analysis context"""
        session_id = f"oi_{ticker.lower()}_{int(time.time())}"
        
        # Store initial context
        context = {
            "session_id": session_id,
            "ticker": ticker.upper(),
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
        
        logger.info(f"Created interactive session {session_id} for {ticker}")
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
    
    def process_query(self, session_id: str, user_query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process a user query through Claude with tools using Bedrock Converse API.
        
        Args:
            session_id: The session ID
            user_query: User's question or request
            
        Returns:
            Tuple of (response text, list of tool calls made with timing info)
        """
        context = self.get_session(session_id)
        if not context:
            return "Session not found", []
            
        ticker = context["ticker"]
        current_analysis = context["current_analysis"]
        conversation_history = context["conversation_history"]
        
        # Build messages array for Bedrock Converse
        messages = self._build_messages(user_query, current_analysis, conversation_history)
        
        # Call Bedrock with tools using Converse API
        start_time = time.time()
        logger.info(f"🚀 Starting Bedrock converse call for query: {user_query[:50]}...")
        try:
            response_text, tool_calls = self.converse(
                messages=messages,
                tools=self._get_tool_definitions(),
                tool_callback=self.execute_tool,
                conversation_id=session_id
            )
            total_time = time.time() - start_time
            logger.info(f"✅ Bedrock converse completed in {total_time:.2f}s. Response length: {len(response_text) if response_text else 0}")
        except Exception as e:
            logger.error(f"❌ Bedrock converse failed: {e}", exc_info=True)
            return f"Error processing query: {str(e)}", []
        
        # Store the conversation turn
        context["conversation_history"].append({
            "user_message": user_query,
            "assistant_message": response_text,
            "timestamp": datetime.now().isoformat(),
            "tool_calls": tool_calls,
            "total_time": total_time
        })
        
        # Update session
        self._update_session(session_id, context)
        
        return response_text, tool_calls
    
    def converse(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_callback: Callable,
        conversation_id: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Send a conversation to Claude using Bedrock Converse API with parallel tool execution.
        Based on VTS Agent implementation.
        """
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            
        tool_calls_made = []
        system_message = None
        
        # Extract system message if present
        if messages and messages[0]["role"] == "system":
            system_message = messages[0]["content"]
            messages = messages[1:]  # Remove system message from messages array
            
        try:
            # Prepare tool configuration
            tool_config = {
                "tools": tools
            }
            
            # Prepare inference configuration
            inference_config = {
                "maxTokens": 8000,
                "temperature": 0.1
            }
            
            # Format messages according to the API spec
            formatted_messages = []
            for msg in messages:
                formatted_msg = {
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}] if isinstance(msg["content"], str) else msg["content"]
                }
                formatted_messages.append(formatted_msg)
                
            # Send initial request
            logger.info(f"Sending request to Bedrock Converse with model ID: {self.model_id}")
            
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=formatted_messages,
                toolConfig=tool_config,
                inferenceConfig=inference_config,
                system=[{"text": system_message}] if system_message else None
            )
            
            # Process initial response
            current_response = response
            
            # Check if we need to use tools
            while current_response.get("stopReason") == "tool_use":
                # Get the tool use information from the output
                tool_message = current_response["output"]["message"]
                formatted_messages.append(tool_message)  # Add the tool request message
                
                # Process all tool calls in parallel
                tool_calls = []
                for content in tool_message["content"]:
                    if "toolUse" in content:
                        tool_use = content["toolUse"]
                        tool_name = tool_use.get("name", "")
                        tool_id = tool_use.get("toolUseId", "")
                        
                        # Parse parameters from tool input
                        tool_parameters = tool_use.get("input", {})
                        if isinstance(tool_parameters, str):
                            try:
                                tool_parameters = json.loads(tool_parameters)
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse tool parameters as JSON: {tool_parameters}")
                                tool_parameters = {}
                                
                        logger.info(f"🔧 Collecting tool call: {tool_name} with parameters: {tool_parameters}")
                        
                        # Track this tool call with timing
                        tool_calls_made.append({
                            "name": tool_name,
                            "parameters": tool_parameters,
                            "started_at": datetime.now().isoformat()
                        })
                        
                        # Add to list of calls to execute in parallel
                        tool_calls.append((tool_name, tool_parameters, tool_id))
                        
                # Execute all tool calls in parallel
                tool_results = []
                if tool_calls:
                    logger.info(f"Executing {len(tool_calls)} tools in parallel")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        # Submit all tool execution tasks
                        future_to_tool = {
                            executor.submit(tool_callback, name, params): (name, params, tool_id)
                            for name, params, tool_id in tool_calls
                        }
                        
                        # Process completed futures with timeout
                        try:
                            for future in concurrent.futures.as_completed(future_to_tool, timeout=self.default_timeout):
                                name, params, tool_id = future_to_tool[future]
                                try:
                                    tool_result = future.result()
                                    # Convert tool result to string if needed
                                    if not isinstance(tool_result, str):
                                        tool_result = json.dumps(tool_result)
                                        
                                    logger.info(f"✅ Completed tool call: {name}")
                                    logger.debug(f"Tool result: {tool_result[:200]}...")
                                    
                                    # Update tool call info with completion
                                    for tool_call in tool_calls_made:
                                        if tool_call["name"] == name:
                                            tool_call["completed_at"] = datetime.now().isoformat()
                                            tool_call["status"] = "success"
                                            break
                                    
                                    # Add to results
                                    tool_results.append({
                                        "toolResult": {
                                            "toolUseId": tool_id,
                                            "content": [{"text": tool_result}]
                                        }
                                    })
                                except Exception as exc:
                                    logger.error(f"❌ Tool {name} generated an exception: {exc}")
                                    # Add error result
                                    tool_results.append({
                                        "toolResult": {
                                            "toolUseId": tool_id,
                                            "content": [{"text": json.dumps({"error": f"Tool execution failed: {str(exc)}"})}]
                                        }
                                    })
                                    
                                    # Update tool call info with error
                                    for tool_call in tool_calls_made:
                                        if tool_call["name"] == name:
                                            tool_call["completed_at"] = datetime.now().isoformat()
                                            tool_call["status"] = "error"
                                            tool_call["error"] = str(exc)
                                            break
                                    
                        except concurrent.futures.TimeoutError:
                            # Handle timeout for remaining futures
                            for future, (name, params, tool_id) in future_to_tool.items():
                                if not future.done():
                                    future.cancel()
                                    logger.warning(f"Tool {name} timed out after {self.default_timeout}s")
                                    tool_results.append({
                                        "toolResult": {
                                            "toolUseId": tool_id,
                                            "content": [{"text": json.dumps({"error": "Tool execution timed out"})}]
                                        }
                                    })
                                    
                # Add all tool results as a user message
                if tool_results:
                    formatted_messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                    
                    # Send all tool results back to LLM at once
                    response = self.bedrock_client.converse(
                        modelId=self.model_id,
                        messages=formatted_messages,
                        toolConfig=tool_config,
                        inferenceConfig=inference_config,
                        system=[{"text": system_message}] if system_message else None
                    )
                    
                    current_response = response
                else:
                    # No tool use, break the loop
                    break
                    
            # Extract final response text
            response_text = ""
            if "output" in current_response and "message" in current_response["output"]:
                message = current_response["output"]["message"]
                if "content" in message:
                    for content in message["content"]:
                        if "text" in content:
                            response_text += content["text"]
                            
            # Return final response text and tool calls made
            return response_text, tool_calls_made
            
        except Exception as e:
            logger.error(f"Error in Bedrock converse: {e}", exc_info=True)
            return f"I encountered an error processing your request: {str(e)}", tool_calls_made
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Execute a tool call made by the LLM with detailed logging"""
        start_time = time.time()
        logger.info(f"🔧 Executing tool: {tool_name} with params: {parameters}")
        
        try:
            if tool_name == "get_live_oi_data":
                result = asyncio.run(self._tool_get_live_oi_data(**parameters))
            elif tool_name == "get_market_data":
                result = asyncio.run(self._tool_get_market_data(**parameters))
            else:
                error_msg = f"Unknown tool: {tool_name}"
                logger.error(f"❌ {error_msg}")
                return json.dumps({"error": error_msg})
            
            execution_time = time.time() - start_time
            logger.info(f"✅ Tool {tool_name} completed in {execution_time:.2f}s")
            
            # Add execution metadata to result
            if isinstance(result, dict):
                result["execution_time"] = execution_time
                result["tool_name"] = tool_name
            
            return json.dumps(result) if not isinstance(result, str) else result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"❌ Tool {tool_name} failed after {execution_time:.2f}s: {e}")
            return json.dumps({"error": error_msg, "execution_time": execution_time})
    
    def _build_messages(
        self,
        user_query: str,
        current_analysis: Dict[str, Any],
        conversation_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build the messages array for Bedrock Converse API"""
        messages = []
        
        # Add system message
        system_message = self._build_system_message(current_analysis)
        messages.append({
            "role": "system",
            "content": system_message
        })
        
        # Add conversation history
        for turn in conversation_history:
            # Add user message
            messages.append({
                "role": "user", 
                "content": turn["user_message"]
            })
            
            # Add assistant message
            messages.append({
                "role": "assistant",
                "content": turn["assistant_message"]
            })
            
        # Add current user query
        messages.append({
            "role": "user",
            "content": user_query
        })
        
        return messages
    
    def _build_system_message(self, current_analysis: Dict[str, Any]) -> str:
        """Build system message with OI trading context"""
        ticker = current_analysis.get("ticker", "UNKNOWN")
        pattern_type = current_analysis.get("pattern_analysis", {}).get("pattern_type", "Unknown")
        direction = current_analysis.get("trade_recommendation", {}).get("direction", "Unknown")
        confidence = current_analysis.get("pattern_analysis", {}).get("confidence_score", "Unknown")
        
        system_message = f"""You are a world-class institutional options trader with 20+ years of experience analyzing open interest patterns. You are currently analyzing {ticker}.

CURRENT ANALYSIS CONTEXT:
- Ticker: {ticker}
- Pattern Type: {pattern_type} 
- Direction: {direction}
- Confidence: {confidence}%
- Analysis: {json.dumps(current_analysis.get("smart_money_insights", {}), indent=2)}

AVAILABLE TOOLS - USE THESE TO GET LIVE DATA:
1. get_live_oi_data(ticker, days=7, target_dte=30, include_news=True) - Get live OI data for ANY ticker
2. get_market_data(ticker, timeframe="1d") - Get current market data and technical indicators

TRADING EXPERTISE:
- Analyze open interest patterns to identify smart money positioning
- Understand gamma exposure, max pain, and dealer positioning
- Interpret unusual options activity and institutional flow
- Provide actionable trading recommendations with risk management
- Explain complex options concepts in practical terms

TOOL USAGE WORKFLOW:
1. **USE TOOLS FIRST** - When user asks for data, invoke appropriate tools to get fresh information
2. **ANALYZE INTELLIGENTLY** - Process tool results to extract meaningful insights
3. **PROVIDE EXPERT ANALYSIS** - Give trading recommendations based on live data
4. **BE CONVERSATIONAL** - Respond like an experienced trader, not a data dumper

RESPONSE STYLE:
- Be precise, actionable, and evidence-driven
- Use live data from tools to support your analysis
- Explain what the data means for trading decisions
- Provide specific entry/exit levels when possible
- Highlight key risks and opportunities

CRITICAL: When user asks questions, use tools to get fresh data first, then analyze and respond with expert insights."""

        return system_message
    
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for Bedrock Converse API"""
        return [
            {
                "toolSpec": {
                    "name": "get_live_oi_data",
                    "description": "Get current or historical open interest data for any ticker with custom parameters",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "ticker": {"type": "string", "description": "Stock ticker symbol"},
                                "days": {"type": "integer", "description": "Number of days of historical data (1-30)", "default": 7},
                                "target_dte": {"type": "integer", "description": "Target days to expiration", "default": 30},
                                "include_news": {"type": "boolean", "description": "Include news analysis", "default": True}
                            },
                            "required": ["ticker"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_market_data",
                    "description": "Get current market data including prices, technical indicators, and volatility metrics",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "ticker": {"type": "string", "description": "Stock ticker symbol"},
                                "timeframe": {"type": "string", "description": "Timeframe for analysis", "enum": ["1m", "5m", "15m", "1h", "1d"], "default": "1d"}
                            },
                            "required": ["ticker"]
                        }
                    }
                }
            }
        ]
    
    async def _tool_get_live_oi_data(self, ticker: str, days: int = 7, target_dte: int = 30, include_news: bool = True) -> Dict[str, Any]:
        """Tool: Get live OI data via MCP service"""
        try:
            client = MCPOIClient()
            await client.start()
            
            result = await client.call_tool("analyze_open_interest", {
                "ticker": ticker,
                "days": target_dte,
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
        """Tool: Get market data via MCP service with proper executable path"""
        try:
            # Use the correct market data executable path 
            market_data_executable = MCP_MARKET_DATA_EXECUTABLE
            
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
            
            logger.info(f"📊 Calling market data MCP service for {ticker}")
            
            process = await asyncio.create_subprocess_exec(
                market_data_executable,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            input_data = f"{init_msg}\n{initialized_msg}\n{tool_msg}\n"
            
            stdout, stderr = await process.communicate(input=input_data.encode())
            
            if stderr:
                logger.warning(f"Market data stderr: {stderr.decode()}")
            
            # Parse responses
            responses = [line for line in stdout.decode().strip().split('\n') if line.strip().startswith('{')]
            logger.info(f"Market data responses count: {len(responses)}")
            
            if len(responses) >= 2:
                tool_response = json.loads(responses[-1])
                if "error" not in tool_response and "result" in tool_response:
                    result_content = tool_response["result"]["content"][0]["text"]
                    market_data = json.loads(result_content)
                    
                    market_data["tool_metadata"] = {
                        "tool": "get_market_data",
                        "ticker": ticker,
                        "timeframe": timeframe,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    logger.info(f"✅ Successfully retrieved market data for {ticker}")
                    return market_data
                else:
                    logger.error(f"❌ Market data tool error response: {tool_response}")
            
            # Fallback if MCP call fails
            logger.warning(f"⚠️ Market data service call failed for {ticker}")
            return {
                "ticker": ticker,
                "error": "Market data service unavailable - please try again",
                "tool_metadata": {
                    "tool": "get_market_data",
                    "ticker": ticker,
                    "timestamp": datetime.now().isoformat()
                },
                "debug_info": {
                    "responses_count": len(responses),
                    "stderr": stderr.decode() if stderr else None
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Market data tool exception for {ticker}: {e}")
            return {"error": f"Failed to get market data for {ticker}: {str(e)}"}
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