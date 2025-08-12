"""
Enhanced OI Data Collector - Interfaces with MCP services
Collects open interest data + current market prices for comprehensive analysis
"""

import asyncio
import json
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional
from config.settings import MCP_OI_EXECUTABLE, MCP_MARKET_DATA_EXECUTABLE, TICKERS, OI_ANALYSIS_DAYS, TARGET_DTE

class MCPOIClient:
    def __init__(self, cmd: str = MCP_OI_EXECUTABLE, args: Optional[List[str]] = None):
        self.cmd = cmd
        self.args = args or []
        self.proc: Optional[asyncio.subprocess.Process] = None
        self.req_id = 0
        self.initialized = False

    async def start(self) -> None:
        self.proc = await asyncio.create_subprocess_exec(
            self.cmd, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=100 * 1024 * 1024,
        )
        await self._initialize()

    async def stop(self) -> None:
        if self.proc:
            self.proc.terminate()
            await self.proc.wait()

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self._assert_ready()
        resp = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        # Try to unwrap fastmcp-style text payload as JSON
        content = resp.get("result", {}).get("content", [])
        if isinstance(content, list) and content and isinstance(content[0], dict) and "text" in content[0]:
            try:
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                pass
        return resp

    async def _initialize(self) -> None:
        init = await self._rpc("initialize", {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {"name": "oi-tracker", "version": "1.0.0"},
        })
        # Send notifications/initialized (no response expected)
        await self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        self.initialized = True

    async def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.req_id += 1
        await self._send({"jsonrpc": "2.0", "id": self.req_id, "method": method, "params": params})
        line = await self._readline()
        return json.loads(line)

    async def _send(self, obj: Dict[str, Any]) -> None:
        self._assert_ready(proc_ok=False)
        data = (json.dumps(obj) + "\n").encode("utf-8")
        self.proc.stdin.write(data)
        await self.proc.stdin.drain()

    async def _readline(self) -> str:
        self._assert_ready()
        line = await self.proc.stdout.readline()
        if not line:
            # surface server stderr if it crashed
            err = (await self.proc.stderr.read()).decode(errors="replace") if self.proc.stderr else ""
            raise RuntimeError(f"MCP server closed pipe.\n{err}")
        return line.decode("utf-8").strip()

    def _assert_ready(self, proc_ok: bool = True) -> None:
        if not self.proc:
            raise RuntimeError("MCP server not started")
        if proc_ok and self.proc.returncode is not None:
            raise RuntimeError(f"MCP server exited with code {self.proc.returncode}")

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
                print(f"OI Error for {ticker}: {str(oi_result)}")
            else:
                combined_data["oi_status"] = "success"
                combined_data["oi_data"] = oi_result
                print(f"OI Success for {ticker}: Got {len(oi_result)} data points")
                # print(f"\n=== OI DATA FOR {ticker} ===")
                # print(json.dumps(oi_result, indent=2))
                # print(f"=== END OI DATA ===\n")
            
            if isinstance(market_data_result, Exception):
                combined_data["market_data_status"] = "error"
                combined_data["market_data_error"] = str(market_data_result)
                print(f"Market Data Error for {ticker}: {str(market_data_result)}")
            else:
                combined_data["market_data_status"] = "success" 
                combined_data["market_data"] = market_data_result
                print(f"Market Data Success for {ticker}: Got data")
                # print(f"\n=== MARKET DATA FOR {ticker} ===")
                # print(json.dumps(market_data_result, indent=2))
                # print(f"=== END MARKET DATA ===\n")
            
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
        """Call the MCP OpenInterest server using the working client"""
        client = MCPOIClient()
        try:
            await client.start()
            result = await client.call_tool("analyze_open_interest", {
                "ticker": ticker,
                "days": self.analysis_days,
                "target_dte": TARGET_DTE,
                "include_news": True
            })
            return result
        finally:
            await client.stop()
    
    async def _call_market_data_mcp_server(self, ticker):
        """Call the MCP Market Data server for current prices and technical zones"""
        init_msg = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "oi-tracker", "version": "1.0.0"}
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
                "arguments": {
                    "symbol": ticker
                }
            }
        })
        
        process = await asyncio.create_subprocess_exec(
            self.mcp_market_data_executable,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        input_data = f"{init_msg}\n{initialized_msg}\n{tool_msg}\n"
        
        stdout_lines = []
        
        async def read_output():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line_text = line.decode().strip()
                stdout_lines.append(line_text)
                if line_text and not line_text.startswith('{'):
                    print(f"[MD-{ticker}] {line_text}")
        
        read_task = asyncio.create_task(read_output())
        process.stdin.write(input_data.encode())
        process.stdin.close()
        await process.wait()
        await read_task
        
        stdout = '\n'.join(stdout_lines).encode()
        stderr = b''
        
        stdout_text = stdout.decode()
        
        if process.returncode != 0:
            print(f"Market data process failed with code {process.returncode}")
        
        responses = [line for line in stdout_text.strip().split('\n') if line.startswith('{')]
        
        if len(responses) < 2:
            raise Exception(f"Unexpected market data MCP response format - only {len(responses)} JSON responses found")
        
        # Print the final response before parsing
        final_response = responses[-1]
        print(f"\n=== FINAL MARKET DATA RESPONSE FOR {ticker} ===")
        print(json.dumps(json.loads(final_response), indent=2))
        print(f"=== END FINAL MARKET DATA RESPONSE ===\n")
        
        tool_response = json.loads(final_response)
        if "error" in tool_response:
            raise Exception(f"MCP Market Data tool error: {tool_response['error']}")
        
        result_content = tool_response["result"]["content"][0]["text"]
        return json.loads(result_content)
    
    async def collect_all_tickers(self):
        """Collect OI data for all tickers in parallel"""
        print(f"Starting OI data collection for {len(self.tickers)} tickers: {self.tickers}")
        print(f"Analysis days: {self.analysis_days}")
        print(f"Target DTE: {TARGET_DTE} days")
        
        # Execute tasks sequentially for better debugging
        results = []
        for ticker in self.tickers:
            print(f"\nProcessing {ticker}...")
            result = await self.collect_ticker_data(ticker)
            results.append(result)
            print(f"Completed {ticker}: {result['status']}")
        
        #print(results)
        #print("=====")
        # Process results
        successful_results = []
        failed_results = []
        
        for result in results:
            if result["status"] == "success":
                successful_results.append(result)
            else:
                failed_results.append(result)
        
        print(f"Collection complete: {len(successful_results)} successful, {len(failed_results)} failed")
        
        # Print successful results with better formatting
        for result in successful_results:
            ticker = result['ticker']
            data = result['data']
            print(f"\n=== {ticker} ===")
            print(f"OI Status: {data.get('oi_status', 'unknown')}")
            print(f"Market Data Status: {data.get('market_data_status', 'unknown')}")
            
            if data.get('oi_status') == 'success' and 'oi_data' in data:
                oi_summary = data['oi_data']
                print(f"OI Data Keys: {list(oi_summary.keys())}")
            
            if data.get('market_data_status') == 'success' and 'market_data' in data:
                market_summary = data['market_data']
                print(f"Market Data Keys: {list(market_summary.keys())}")
        
        if failed_results:
            print("\nFailed tickers:")
            for failure in failed_results:
                print(f"  {failure.get('ticker', 'unknown')}: {failure.get('error', 'unknown error')}")
        
        # Format as dict with ticker as key
        ticker_data = {}
        
        for result in successful_results:
            ticker = result['ticker']
            data = result['data']
            
            ticker_data[ticker] = {
                "oi_data": data.get('oi_data') if data.get('oi_status') == 'success' else None,
                "market_data": data.get('market_data') if data.get('market_data_status') == 'success' else None,
                "oi_error": data.get('oi_error') if data.get('oi_status') == 'error' else None,
                "market_data_error": data.get('market_data_error') if data.get('market_data_status') == 'error' else None,
                "timestamp": result['timestamp']
            }
        
        # Add failed tickers
        for failure in failed_results:
            ticker = failure.get('ticker', 'unknown')
            ticker_data[ticker] = {
                "oi_data": None,
                "market_data": None,
                "oi_error": failure.get('error'),
                "market_data_error": None,
                "timestamp": failure.get('timestamp')
            }
        
        #print("--------")
        #print(json.dumps(ticker_data, indent=2))
        #print("--------")
        return {
            "data": ticker_data,
            "summary": {
                "total_processed": len(results),
                "successful": len(successful_results),
                "failed": len(failed_results),
                "success_rate": len(successful_results) / len(results) if results else 0
            }
        }