"""
Redis Manager for OI Pattern Tracker
Handles all Redis operations for caching OI data and analysis results
"""

import redis
import json
from datetime import datetime, timedelta
from config.settings import REDIS_URL

class RedisManager:
    def __init__(self):
        self.redis_client = redis.from_url(REDIS_URL)
        self.expiry_seconds = 604800  # 7 days
    
    def store_oi_data(self, ticker, date, oi_data):
        """Store OI data with key: ticker:YYYY-MM-DD"""
        key = f"{ticker}:{date}"
        self.redis_client.setex(
            key, 
            self.expiry_seconds, 
            json.dumps(oi_data)
        )
    
    def get_oi_data(self, ticker, date):
        """Retrieve OI data for specific ticker and date"""
        key = f"{ticker}:{date}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None
    
    def get_previous_oi_data(self, ticker, days_back=1):
        """Get OI data from N days ago"""
        target_date = datetime.now() - timedelta(days=days_back)
        date_str = target_date.strftime('%Y-%m-%d')
        return self.get_oi_data(ticker, date_str)
    
    def store_delta_data(self, ticker, date, delta_data):
        """Store calculated delta data"""
        key = f"delta:{ticker}:{date}"
        self.redis_client.setex(
            key,
            self.expiry_seconds,
            json.dumps(delta_data)
        )
    
    def get_delta_data(self, ticker, date):
        """Retrieve delta data for specific ticker and date"""
        key = f"delta:{ticker}:{date}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None
    
    def store_analysis_result(self, ticker, date, analysis_data):
        """Store LLM analysis results"""
        key = f"analysis:{ticker}:{date}"
        self.redis_client.setex(
            key,
            self.expiry_seconds,
            json.dumps(analysis_data)
        )
    
    def get_analysis_result(self, ticker, date):
        """Retrieve analysis results"""
        key = f"analysis:{ticker}:{date}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None