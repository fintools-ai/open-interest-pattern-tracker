"""
Market Data Tools - Wraps existing market data functionality
"""

import asyncio
import json
import logging
from typing import Dict, Any
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import MCP_MARKET_DATA_EXECUTABLE

logger = logging.getLogger("oi_tracker.tools.market")


async def get_market_data(
    ticker: str,
    timeframe: str = "1d"
) -> Dict[str, Any]:
    """
    Get current market data including price, volume, and technical indicators.
    Wraps EnhancedOIDataCollector._call_market_data_mcp_server()

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "TSLA")
        timeframe: Timeframe for analysis ("1m", "5m", "15m", "1h", "1d")

    Returns:
        Dictionary containing market data from MCP service
    """
    try:
        logger.info(f"Fetching market data for {ticker} ({timeframe})")

        # Call MCP Market Data Service using existing logic
        init_msg = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "oi-tracker-tools", "version": "1.0.0"}
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

        stdout_lines = []

        async def read_output():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line_text = line.decode().strip()
                stdout_lines.append(line_text)

        read_task = asyncio.create_task(read_output())
        process.stdin.write(input_data.encode())
        process.stdin.close()
        await process.wait()
        await read_task

        stdout = '\n'.join(stdout_lines).encode()
        stdout_text = stdout.decode()

        if process.returncode != 0:
            logger.warning(f"Market data process returned code {process.returncode}")

        # Parse responses
        responses = [line for line in stdout_text.strip().split('\n') if line.startswith('{')]

        if len(responses) >= 2:
            tool_response = json.loads(responses[-1])
            if "error" not in tool_response and "result" in tool_response:
                result_content = tool_response["result"]["content"][0]["text"]
                market_data = json.loads(result_content)

                market_data["tool_metadata"] = {
                    "tool": "get_market_data",
                    "ticker": ticker,
                    "timeframe": timeframe,
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }

                logger.info(f"Successfully retrieved market data for {ticker}")
                return market_data

        # Fallback
        logger.warning(f"Market data service call failed for {ticker}")
        return {
            "ticker": ticker,
            "error": "Market data service unavailable",
            "tool_metadata": {
                "tool": "get_market_data",
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
        }

    except Exception as e:
        logger.error(f"Failed to get market data for {ticker}: {e}")
        return {
            "error": f"Failed to fetch market data: {str(e)}",
            "ticker": ticker,
            "tool_metadata": {
                "tool": "get_market_data",
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
        }