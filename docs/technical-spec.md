# OI Pattern Tracker - Technical Documentation

## System Architecture

### Data Collection Pipeline

```python
# Daily OI collection script
import pandas as pd
from datetime import datetime
import requests

class OIDataCollector:
    def __init__(self, tickers):
        self.tickers = tickers
        self.data_source = "CBOE"  # or broker API
        
    def collect_daily_oi(self):
        """Pull OI data for all tracked tickers"""
        daily_data = {}
        
        for ticker in self.tickers:
            # Get options chain
            chain = self.fetch_options_chain(ticker)
            
            # Calculate metrics
            oi_metrics = {
                'date': datetime.now().date(),
                'ticker': ticker,
                'total_call_oi': chain['calls']['open_interest'].sum(),
                'total_put_oi': chain['puts']['open_interest'].sum(),
                'put_call_ratio': self.calculate_pc_ratio(chain),
                'max_pain': self.calculate_max_pain(chain),
                'key_strikes': self.identify_key_strikes(chain)
            }
            
            daily_data[ticker] = oi_metrics
            
        return daily_data
```

### Pattern Detection Algorithms

```python
class PatternDetector:
    def __init__(self, lookback_days=30):
        self.lookback_days = lookback_days
        self.patterns = {
            'accumulation': self.detect_accumulation,
            'distribution': self.detect_distribution,
            'gamma_squeeze': self.detect_gamma_squeeze,
            'put_wall': self.detect_put_wall
        }
    
    def detect_accumulation(self, oi_history):
        """Detect steady call OI accumulation pattern"""
        # Look for 5+ consecutive days of increasing call OI
        consecutive_increases = 0
        total_increase = 0
        
        for i in range(1, len(oi_history)):
            daily_change = (oi_history[i]['call_oi'] - oi_history[i-1]['call_oi']) / oi_history[i-1]['call_oi']
            
            if daily_change > 0:
                consecutive_increases += 1
                total_increase += daily_change
            else:
                consecutive_increases = 0
                
        if consecutive_increases >= 5 and total_increase > 0.15:
            return {
                'pattern': 'ACCUMULATION',
                'strength': min(total_increase / 0.15, 1.0),
                'days': consecutive_increases,
                'signal': 'BUY_CALL'
            }
            
        return None
```

### Clustering Algorithm

```python
from sklearn.cluster import DBSCAN
import numpy as np

class StockClusterer:
    def __init__(self):
        self.features = [
            'oi_change_7d',
            'pc_ratio_change',
            'consecutive_days',
            'acceleration_rate'
        ]
        
    def cluster_stocks(self, stock_data):
        """Group stocks with similar OI patterns"""
        # Extract features
        X = self.extract_features(stock_data)
        
        # Normalize features
        X_normalized = self.normalize_features(X)
        
        # Cluster using DBSCAN
        clustering = DBSCAN(eps=0.3, min_samples=3)
        clusters = clustering.fit_predict(X_normalized)
        
        # Group stocks by cluster
        clustered_stocks = {}
        for idx, cluster_id in enumerate(clusters):
            if cluster_id not in clustered_stocks:
                clustered_stocks[cluster_id] = []
            clustered_stocks[cluster_id].append(stock_data[idx]['ticker'])
            
        return clustered_stocks
```

### Database Schema

```sql
-- Time series OI data
CREATE TABLE oi_snapshots (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    strike DECIMAL(10,2) NOT NULL,
    expiration DATE NOT NULL,
    call_oi INTEGER DEFAULT 0,
    put_oi INTEGER DEFAULT 0,
    call_volume INTEGER DEFAULT 0,
    put_volume INTEGER DEFAULT 0,
    underlying_price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ticker_date (ticker, date),
    INDEX idx_expiration (expiration)
);

-- Daily aggregates
CREATE TABLE oi_daily_summary (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    total_call_oi INTEGER,
    total_put_oi INTEGER,
    pc_ratio DECIMAL(5,3),
    max_pain DECIMAL(10,2),
    oi_change_pct DECIMAL(5,2),
    pattern_detected VARCHAR(50),
    UNIQUE KEY unique_ticker_date (ticker, date)
);

-- Pattern detections
CREATE TABLE pattern_signals (
    id SERIAL PRIMARY KEY,
    detection_date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    pattern_type VARCHAR(50),
    confidence DECIMAL(5,2),
    suggested_action VARCHAR(20),
    suggested_strike DECIMAL(10,2),
    suggested_expiration DATE,
    cluster_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trade outcomes (for backtesting)
CREATE TABLE trade_outcomes (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES pattern_signals(id),
    entry_date DATE,
    exit_date DATE,
    entry_price DECIMAL(10,2),
    exit_price DECIMAL(10,2),
    outcome VARCHAR(20), -- 'WIN', 'LOSS', 'BREAKEVEN'
    return_pct DECIMAL(5,2)
);
```

### Signal Generation Logic

```python
class SignalGenerator:
    def __init__(self, min_confidence=0.70):
        self.min_confidence = min_confidence
        
    def generate_signals(self, patterns, historical_success):
        """Convert patterns into specific trade recommendations"""
        signals = []
        
        for ticker, pattern in patterns.items():
            # Calculate confidence based on historical data
            confidence = self.calculate_confidence(pattern, historical_success)
            
            if confidence >= self.min_confidence:
                signal = {
                    'ticker': ticker,
                    'pattern': pattern['type'],
                    'action': 'BUY_CALL' if pattern['bullish'] else 'BUY_PUT',
                    'strike': self.calculate_optimal_strike(ticker, pattern),
                    'expiration': self.calculate_optimal_expiration(pattern),
                    'confidence': confidence,
                    'entry_zone': self.calculate_entry_zone(ticker),
                    'stop_loss': self.calculate_stop_loss(ticker, pattern),
                    'target': self.calculate_target(ticker, pattern)
                }
                signals.append(signal)
                
        return sorted(signals, key=lambda x: x['confidence'], reverse=True)
    
    def calculate_optimal_strike(self, ticker, pattern):
        """Determine best strike based on pattern type"""
        current_price = self.get_current_price(ticker)
        
        if pattern['type'] == 'ACCUMULATION':
            # 2-3% OTM for accumulation patterns
            return round(current_price * 1.025, 0)
        elif pattern['type'] == 'GAMMA_SQUEEZE':
            # ATM for gamma squeezes
            return round(current_price, 0)
        # ... other patterns
```

### API Endpoints

```python
# FastAPI backend example
from fastapi import FastAPI, HTTPException
from typing import List, Optional
import datetime

app = FastAPI()

@app.get("/api/daily-signals")
async def get_daily_signals(date: Optional[str] = None):
    """Get trading signals for a specific date"""
    if not date:
        date = datetime.date.today()
        
    signals = db.query("""
        SELECT * FROM pattern_signals 
        WHERE detection_date = %s 
        AND confidence >= 70
        ORDER BY confidence DESC
    """, date)
    
    return {"date": date, "signals": signals}

@app.get("/api/pattern-history/{ticker}")
async def get_pattern_history(ticker: str, days: int = 30):
    """Get OI pattern history for a ticker"""
    history = db.query("""
        SELECT date, total_call_oi, total_put_oi, pc_ratio, pattern_detected
        FROM oi_daily_summary
        WHERE ticker = %s
        AND date >= CURRENT_DATE - INTERVAL %s DAY
        ORDER BY date
    """, ticker, days)
    
    return {"ticker": ticker, "history": history}

@app.get("/api/clusters")
async def get_current_clusters():
    """Get current pattern clusters"""
    clusters = db.query("""
        SELECT cluster_id, pattern_type, GROUP_CONCAT(ticker) as tickers,
               AVG(confidence) as avg_confidence
        FROM pattern_signals
        WHERE detection_date = CURRENT_DATE
        GROUP BY cluster_id, pattern_type
    """)
    
    return {"clusters": clusters}

@app.post("/api/backtest")
async def run_backtest(pattern_type: str, lookback_days: int = 365):
    """Backtest a specific pattern"""
    results = backtest_pattern(pattern_type, lookback_days)
    return {
        "pattern": pattern_type,
        "success_rate": results['success_rate'],
        "avg_return": results['avg_return'],
        "total_trades": results['total_trades']
    }
```

### Configuration File

```yaml
# config.yaml
data_sources:
  primary: "CBOE"
  backup: "Yahoo Finance"
  
tickers:
  - SPY
  - QQQ
  - IWM
  - DIA
  - NVDA
  - AAPL
  - MSFT
  - GOOGL
  - AMZN
  - META
  - TSLA
  # ... add more

patterns:
  accumulation:
    min_days: 5
    min_increase: 0.15
    lookback: 30
    
  gamma_squeeze:
    oi_concentration: 0.30
    strike_range: 0.05
    
  put_wall:
    min_pc_ratio: 1.5
    min_increase: 0.20
    
trading_rules:
  min_confidence: 0.70
  default_dte: 70
  position_size: 0.02  # 2% per trade
  max_positions: 10
  
alerts:
  email: "trader@example.com"
  webhook: "https://discord.com/api/webhooks/..."
```

## Deployment

### Docker Compose Setup

```yaml
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg14
    environment:
      POSTGRES_DB: oi_tracker
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
      
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://admin:secure_password@postgres/oi_tracker
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"
      
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://backend:8000
      
  scheduler:
    build: ./scheduler
    environment:
      DATABASE_URL: postgresql://admin:secure_password@postgres/oi_tracker
    depends_on:
      - postgres
      
volumes:
  postgres_data:
```

This technical documentation provides the foundation for building the OI Pattern Tracker system. The modular design allows for easy extension and modification as patterns are refined through backtesting.
