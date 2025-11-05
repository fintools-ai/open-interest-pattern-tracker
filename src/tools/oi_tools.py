"""
Open Interest Tools - Wraps existing OI functionality from data_pipeline
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Import existing classes
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.collector import MCPOIClient
from data_pipeline.redis_manager import RedisManager
from data_pipeline.delta_calculator import DeltaCalculator

logger = logging.getLogger("oi_tracker.tools.oi")


async def get_live_oi_data(
    ticker: str,
    days: int = 7,
    target_dte: int = 30,
    include_news: bool = True
) -> Dict[str, Any]:
    """
    Get live open interest data for a ticker via MCP service.
    Wraps MCPOIClient.call_tool("analyze_open_interest")

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "TSLA")
        days: Number of days of historical data (1-30)
        target_dte: Target days to expiration for options analysis
        include_news: Whether to include news context in analysis

    Returns:
        Dictionary containing OI data from MCP service
    """
    try:
        logger.info(f"Fetching live OI data for {ticker} (target_dte={target_dte})")

        client = MCPOIClient()
        await client.start()

        result = await client.call_tool("analyze_open_interest", {
            "ticker": ticker,
            "days": days,
            "target_dte": target_dte,
            "include_news": include_news
        })

        await client.stop()

        # Add metadata
        result["tool_metadata"] = {
            "tool": "get_live_oi_data",
            "ticker": ticker,
            "target_dte": target_dte,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }

        logger.info(f"Successfully fetched OI data for {ticker}")
        return result

    except Exception as e:
        logger.error(f"Failed to get OI data for {ticker}: {e}")
        return {
            "error": f"Failed to fetch OI data: {str(e)}",
            "ticker": ticker,
            "tool_metadata": {
                "tool": "get_live_oi_data",
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
        }


async def calculate_delta_changes(
    ticker: str,
    current_oi_data: Dict[str, Any],
    days_back: int = 1
) -> Dict[str, Any]:
    """
    Calculate day-over-day delta changes in open interest.
    Wraps DeltaCalculator.calculate_deltas()

    Args:
        ticker: Stock ticker symbol
        current_oi_data: Current OI data from get_live_oi_data
        days_back: How many days back to compare (default: 1 for day-over-day)

    Returns:
        Dictionary containing delta calculations
    """
    try:
        logger.info(f"Calculating OI delta for {ticker} (days_back={days_back})")

        redis_manager = RedisManager()
        calculator = DeltaCalculator()

        # Get previous OI data from Redis
        oi_key = f"{ticker}:30DTE"  # Default to 30 DTE
        previous_data = redis_manager.get_previous_oi_data(oi_key, days_back=days_back)

        if not previous_data:
            logger.warning(f"No previous data found for {ticker}, returning baseline")
            delta_data = calculator.calculate_deltas(current_oi_data, None, ticker)
        else:
            # Calculate deltas using existing method
            delta_data = calculator.calculate_deltas(current_oi_data, previous_data, ticker)

        logger.info(f"Calculated deltas for {ticker}")
        return delta_data

    except Exception as e:
        logger.error(f"Failed to calculate delta for {ticker}: {e}")
        return {
            "error": f"Delta calculation failed: {str(e)}",
            "ticker": ticker,
            "is_baseline": True
        }


async def get_historical_oi_data(
    ticker: str,
    days_back: int = 1
) -> Optional[Dict[str, Any]]:
    """
    Get historical OI data from Redis cache.
    Wraps RedisManager.get_previous_oi_data()

    Args:
        ticker: Stock ticker symbol
        days_back: Number of days back to retrieve

    Returns:
        Historical OI data dictionary or None if not found
    """
    try:
        logger.info(f"Fetching historical OI data for {ticker} ({days_back} days back)")

        redis_manager = RedisManager()
        oi_key = f"{ticker}:30DTE"

        data = redis_manager.get_previous_oi_data(oi_key, days_back=days_back)

        if data:
            logger.info(f"Retrieved historical OI data for {ticker}")
        else:
            logger.warning(f"No historical data found for {ticker}")

        return data

    except Exception as e:
        logger.error(f"Failed to get historical OI for {ticker}: {e}")
        return None