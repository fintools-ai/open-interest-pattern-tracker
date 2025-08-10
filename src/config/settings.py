"""
Configuration settings for OI Pattern Tracker
"""

# AWS Bedrock Configuration
AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

# Redis Configuration
REDIS_URL = "redis://localhost:6379"

# MCP Server Configuration
MCP_OI_EXECUTABLE = "/User/mcp-env/mcp-openinterest-server"
MCP_MARKET_DATA_EXECUTABLE = "/Users/sayantan/Documents/Workspace/mcp_env/market_data_server/bin/mcp-market-data-server"

# Ticker List for Analysis
TICKERS = [
    # Major Indices ETFs
    "SPY", "QQQ", "IWM", "DIA", "VTI",
    
    # Tech Giants
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "CRM", "ORCL",
    
    # Financial Sector
    "JPM", "BAC", "WFC", "GS", "MS", "C", "USB", "PNC", "TFC", "COF",
    
    # Healthcare
    "JNJ", "PFE", "UNH", "MRK", "ABT", "TMO", "DHR", "BMY", "AMGN", "GILD",
    
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "VLO", "PSX", "OXY", "BKR",
    
    # Consumer
    "WMT", "HD", "PG", "KO", "PEP", "MCD", "NKE", "SBUX", "TGT", "COST",
    
    # Industrial
    "BA", "CAT", "GE", "MMM", "HON", "UPS", "RTX", "LMT", "NOC", "GD"
]

# Analysis Parameters
OI_ANALYSIS_DAYS = 100
CONFIDENCE_THRESHOLD = 0.70