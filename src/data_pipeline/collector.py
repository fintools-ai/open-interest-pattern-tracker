"""
Enhanced OI Data Collector - Interfaces with MCP services
Collects open interest data + current market prices for comprehensive analysis
"""

import asyncio
import json
import subprocess
from datetime import datetime
from config.settings import MCP_OI_EXECUTABLE, MCP_MARKET_DATA_EXECUTABLE, TICKERS, OI_ANALYSIS_DAYS

class EnhancedOIDataCollector:
    def __init__(self):
        self.mcp_oi_executable = MCP_OI_EXECUTABLE
        self.mcp_market_data_executable = MCP_MARKET_DATA_EXECUTABLE
        self.tickers = TICKERS
        self.analysis_days = OI_ANALYSIS_DAYS
    
    async def collect_ticker_data(self, ticker):
        """Collect comprehensive data for a single ticker (OI + current prices)"""
        try:
            # Collect both OI data and current market data in parallel
            oi_task = self._call_oi_mcp_server(ticker)
            market_data_task = self._call_market_data_mcp_server(ticker)
            
            oi_result, market_data_result = await asyncio.gather(
                oi_task, market_data_task, return_exceptions=True
            )
            
            # Process results
            combined_data = {"ticker": ticker}
            
            if isinstance(oi_result, Exception):
                combined_data["oi_status"] = "error"
                combined_data["oi_error"] = str(oi_result)
            else:
                combined_data["oi_status"] = "success"
                combined_data["oi_data"] = oi_result
            
            if isinstance(market_data_result, Exception):
                combined_data["market_data_status"] = "error"
                combined_data["market_data_error"] = str(market_data_result)
            else:
                combined_data["market_data_status"] = "success" 
                combined_data["market_data"] = market_data_result
            
            return {
                "ticker": ticker,
                "status": "success",
                "data": combined_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "ticker": ticker,
                "status": "error", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _call_oi_mcp_server(self, ticker):
        """Call the MCP OpenInterest server via subprocess"""
        # Prepare the MCP call
        mcp_input = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_open_interest",
                "arguments": {
                    "ticker": ticker,
                    "days": self.analysis_days,
                    "include_news": True
                }
            }
        }
        
        # Execute MCP server call
        process = await asyncio.create_subprocess_exec(
            self.mcp_oi_executable,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Send input and get result
        stdout, stderr = await process.communicate(
            input=json.dumps(mcp_input).encode()
        )
        
        if process.returncode != 0:
            raise Exception(f"MCP OI server failed: {stderr.decode()}")
        
        # Parse response
        response = json.loads(stdout.decode())
        
        if "error" in response:
            raise Exception(f"MCP OI tool error: {response['error']}")
        
        # Extract result data
        result_content = response["result"]["content"][0]["text"]
        return json.loads(result_content)
    
    async def _call_market_data_mcp_server(self, ticker):
        """Call the MCP Market Data server for current prices and technical zones"""
        # Prepare the MCP call for technical zones (includes current price)
        mcp_input = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "financial_technical_zones_tool",
                "arguments": {
                    "symbol": ticker
                }
            }
        }
        
        # Execute MCP server call
        process = await asyncio.create_subprocess_exec(
            self.mcp_market_data_executable,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Send input and get result
        stdout, stderr = await process.communicate(
            input=json.dumps(mcp_input).encode()
        )
        
        if process.returncode != 0:
            raise Exception(f"MCP Market Data server failed: {stderr.decode()}")
        
        # Parse response
        response = json.loads(stdout.decode())
        
        if "error" in response:
            raise Exception(f"MCP Market Data tool error: {response['error']}")
        
        # Extract result data
        result_content = response["result"]["content"][0]["text"]
        return json.loads(result_content)
    
    async def collect_all_tickers(self):
        """Collect OI data for all tickers in parallel"""
        print(f"Starting OI data collection for {len(self.tickers)} tickers...")
        
        # Create tasks for parallel execution
        tasks = [self.collect_ticker_data(ticker) for ticker in self.tickers]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append({
                    "ticker": "unknown",
                    "status": "error",
                    "error": str(result)
                })
            elif result["status"] == "success":
                successful_results.append(result)
            else:
                failed_results.append(result)
        
        print(f"Collection complete: {len(successful_results)} successful, {len(failed_results)} failed")
        
        if failed_results:
            print("Failed tickers:")
            for failure in failed_results:
                print(f"  {failure.get('ticker', 'unknown')}: {failure['error']}")
        
        return {
            "successful": successful_results,
            "failed": failed_results,
            "total_processed": len(results),
            "success_rate": len(successful_results) / len(results) if results else 0
        }