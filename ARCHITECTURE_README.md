# OI Pattern Tracker - Architecture Design

## 🔄 System Flow Sequence

```mermaid
sequenceDiagram
    participant P as Pipeline
    participant M as MCP Service
    participant R as Redis
    participant C as Claude API
    participant H as HTML Generator

    P->>M: analyze_open_interest("AAPL", days=5)
    M->>P: {"ticker":"AAPL", "data_by_date":{"2025-01-15":{"put_call_ratio":0.5,"max_pain":200,"strikes":{"calls":{"210":47866},"puts":{"200":46476}}}}}
    
    P->>R: store("AAPL:2025-01-15", oi_data)
    P->>R: get("AAPL:2025-01-14")
    R->>P: {"put_call_ratio":0.6,"max_pain":195,"strikes":{...}}
    
    P->>P: calculate_delta()
    Note over P: delta = {"ratio_change":-0.1,"max_pain_shift":+5,"new_strikes":[240,250]}
    
    P->>C: send_prompt(oi_data + delta)
    Note over C: Prompt: "Analyze AAPL OI data:<br/>Current: {put_call_ratio:0.5, strikes:{210:47866}}<br/>Delta: {ratio_change:-0.1, new_strikes:[240,250]}<br/>Return JSON with recommendation"
    
    C->>P: {"ticker":"AAPL","pattern":"accumulation","recommendation":{"direction":"CALL","strikes":[210,220],"expiry":"2025-10-17","confidence":0.82}}
    
    P->>P: cluster_analysis()
    Note over P: bullish_group = [{"ticker":"AAPL","confidence":0.82}]<br/>bearish_group = [{"ticker":"SPY","confidence":0.78}]
    
    P->>H: generate_html(bullish_group, bearish_group, all_analyses)
    Note over H: Template data:<br/>{{patterns_found: 8}}<br/>{{avg_success_rate: 74.3}}<br/>{{bullish_tickers: ["AAPL","TSLA"]}}<br/>{{trade_recs: [{ticker:"AAPL",direction:"CALL"}]}}
    
    H->>P: daily_overview.html + individual_reports/
```

## 🏗️ Simple System Architecture

```mermaid
graph TB
    A[Ticker List] --> B[MCP OI Service]
    B --> C[Redis Storage]
    C --> D[Delta Calculator]
    D --> E[LLM Analyzer]
    E --> F[Output Generator]
    
    F --> G[JSON Reports]
    F --> H[HTML Dashboards]
    F --> I[Bullish/Bearish Clusters]
    
    C --> J[(Redis Cache<br/>ticker:date → OI data)]
    E --> K[Anthropic Claude API]
```

## 📋 Enhanced Claude API Input Structure

```mermaid
graph TD
    A[Claude Input] --> B[System Prompt]
    A --> C[Market Context]
    A --> D[OI Data Package]
    
    B --> E["Expert options analyst<br/>Focus on institutional positioning<br/>70%+ success rate target"]
    
    C --> F[Market Regime: Bull/Bear/Sideways]
    C --> G[VIX Level & Change]
    C --> H[Key Events: Earnings/Fed/Expiry]
    
    D --> I[Core OI Metrics]
    D --> J[Delta Changes]
    D --> K[Flow Analysis]
    
    I --> L["• OI Change Velocity (1,3,5 day)<br/>• Strike Concentration<br/>• Volume/OI Ratio<br/>• Large Block Detection<br/>• Gamma Exposure"]
    
    J --> M["• Put/Call Ratio Delta<br/>• Max Pain Migration<br/>• New Strike Activity<br/>• Time-Weighted Changes"]
    
    K --> N["• Institutional Sweeps<br/>• Block Trades >500 contracts<br/>• Bid-Ask Spread Analysis<br/>• Historical Percentiles"]
```

## 🎯 Enhanced Claude API Output Structure

```mermaid
graph TD
    A[Claude Response] --> B[High Conviction Trades]
    A --> C[Market Structure Analysis]
    A --> D[Risk Management]
    
    B --> E[Primary Signal]
    B --> F[Secondary Signals]
    B --> G[Watchlist Items]
    
    E --> H["Ticker: AAPL<br/>Pattern: BULLISH_BREAKOUT<br/>Confidence: 85%<br/>Success Probability: 78%"]
    
    E --> I["Entry: Buy 190/195 Call Spread<br/>Price: $1.85<br/>Target: $3.50<br/>Stop: $0.90<br/>R/R: 1:3.2"]
    
    C --> J["Support Levels<br/>Resistance Levels<br/>Key Expirations<br/>Gamma Exposure Levels"]
    
    D --> K["Position Size: 2%<br/>Hedge Strategy<br/>IV Considerations<br/>Time Decay Impact"]
```

## 🔄 Clustering Logic

```mermaid
graph TB
    A[All Ticker Analyses] --> B{Direction?}
    
    B -->|CALL + >70% confidence| C[Bullish Cluster]
    B -->|PUT + >70% confidence| D[Bearish Cluster]
    B -->|<70% confidence| E[Mixed/Neutral]
    
    C --> F[Calculate Group Success Rate]
    D --> G[Calculate Group Success Rate]
    E --> H[Low Confidence Group]
    
    F --> I[HTML Dashboard Generation]
    G --> I
    H --> I
```

## 🖥️ Critical Dashboard Information Structure

```mermaid
graph TD
    A[Daily Dashboard] --> B[Market Pulse]
    A --> C[High Conviction Trades]
    A --> D[Risk Monitor]
    A --> E[OI Heatmap]
    
    B --> F["Overall Sentiment: BULLISH 72%<br/>Institutional Flow: ↑ $2.3B Net Calls<br/>Success Rate 30-day: 76.5%<br/>VIX: 18.5 (+2.1%)<br/>Key Events: Fed Meeting Wed"]
    
    C --> G[Primary Signals]
    C --> H[Secondary Signals]
    C --> I[Watchlist]
    
    G --> J["AAPL: BULLISH BREAKOUT<br/>Entry: 190/195 Call Spread @ $1.85<br/>Target: $3.50 | R/R: 1:3.2<br/>Evidence: 25K sweep, GEX flip<br/>Success Prob: 78%"]
    
    D --> K["Portfolio VaR: -$12,450<br/>Delta Exposure: +$45,000<br/>Theta Decay: -$850/day<br/>Max Position Risk: 2.5%<br/>Correlation Risk: Low"]
    
    E --> L["Strike vs Expiry Grid<br/>Color: OI Intensity<br/>Size: Volume Activity<br/>Interactive Drill-Down<br/>Real-time Updates"]
```

## 📊 Data Transformation Flow

```mermaid
graph LR
    A["MCP Raw Data<br/>{exp, bulkOpenInterest}"] --> B["Processed OI<br/>{put_call_ratio, strikes}"]
    B --> C["Delta Calculation<br/>{changes, new_strikes}"]
    C --> D["Claude Input<br/>{current + delta}"]
    D --> E["Claude Output<br/>{recommendation, confidence}"]
    E --> F["Clustered Data<br/>{bullish[], bearish[]}"]
    F --> G["HTML Variables<br/>{{template_data}}"]
```

## 🗄️ Redis Data Storage

```mermaid
graph LR
    subgraph Redis Keys
        A["AAPL:2025-01-15<br/>{put_call_ratio: 0.5, max_pain: 200}"]
        B["SPY:2025-01-15<br/>{put_call_ratio: 2.38, max_pain: 590}"]
        C["system:last_run<br/>2025-01-15T16:15:00Z"]
    end
```

## 📱 Output Generation Flow

```mermaid
graph LR
    A[Clustered Results] --> B[Template Engine]
    B --> C[Daily Overview HTML]
    B --> D[Bullish Group HTML]
    B --> E[Bearish Group HTML]
    B --> F[Individual Ticker HTMLs]
    B --> G[JSON Reports]
```