"""
Configuration settings for OI Pattern Tracker
"""

# AWS Bedrock Configuration
AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# Redis Configuration
REDIS_URL = "redis://localhost:6379"

# MCP Server Configuration
MCP_OI_EXECUTABLE = "/Users/sayantbh/Workspace/fintool/mcp_env/open_interest/bin/mcp-openinterest-server"
MCP_MARKET_DATA_EXECUTABLE = "/Users/sayantbh/Workspace/fintool/mcp_env/market_data_server/bin/mcp-market-data-server"

# Ticker List for Analysis
TICKERS = [
    # Major Indices ETFs
    "SPY", "AMD", "ACHR", "QQQ", "HOOD", "TTD", "COIN", "VIX",
    # Tech Giants
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "ORCL", "HIMS", "OSCR", "UNH"

]


# Analysis Parameters
OI_ANALYSIS_DAYS = 30
TARGET_DTE = 30
CONFIDENCE_THRESHOLD = 0.50