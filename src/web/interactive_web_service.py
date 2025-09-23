"""
Interactive Web Service - Flask API for deep analysis sessions
Provides REST endpoints for creating and managing interactive analysis sessions
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import asyncio
import json
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.interactive_analyzer import InteractiveAnalysisService
from data_pipeline.redis_manager import RedisManager
from config.settings import OI_ANALYSIS_DAYS, DEFAULT_DTE

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Initialize services
interactive_service = InteractiveAnalysisService()
redis_manager = RedisManager()

@app.route('/api/create-session', methods=['POST'])
def create_analysis_session():
    """Create new interactive analysis session"""
    try:
        data = request.get_json()
        ticker = data.get('ticker')
        direction = data.get('direction')
        
        if not ticker:
            return jsonify({"error": "Ticker is required"}), 400
        
        # Get current analysis from Redis (multi-timeframe support)
        today = datetime.now().strftime('%Y-%m-%d')

        # Try to get analysis for configured DTE periods (prioritize DEFAULT_DTE)
        current_analysis = None
        preferred_dtes = [DEFAULT_DTE] + [dte for dte in OI_ANALYSIS_DAYS if dte != DEFAULT_DTE]

        for dte in preferred_dtes:
            analysis_key = f"{ticker}:{dte}DTE"
            current_analysis = redis_manager.get_analysis_result(analysis_key, today)
            if current_analysis:
                print(f"Found analysis for {ticker} at {dte} DTE")
                break

        if not current_analysis:
            return jsonify({"error": f"No analysis found for {ticker} across any timeframes"}), 404
        
        # Create session
        session_id = interactive_service.create_session(ticker, current_analysis)
        
        return jsonify({
            "session_id": session_id,
            "ticker": ticker,
            "status": "created",
            "analysis_summary": {
                "pattern_type": current_analysis.get("pattern_analysis", {}).get("pattern_type", "Unknown"),
                "direction": current_analysis.get("trade_recommendation", {}).get("direction", "Unknown"),
                "confidence": current_analysis.get("pattern_analysis", {}).get("confidence_score", "Unknown")
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_query():
    """Process analysis query within session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_query = data.get('query')
        
        if not session_id or not user_query:
            return jsonify({"error": "Session ID and query are required"}), 400
        
        # Process query with detailed tool tracking
        response_text, tool_calls = interactive_service.process_query(session_id, user_query)
        
        # Extract tool execution details for UI
        tool_details = []
        for call in tool_calls:
            tool_detail = {
                "name": call["name"],
                "parameters": call.get("parameters", {}),
                "status": call.get("status", "unknown"),
                "started_at": call.get("started_at"),
                "completed_at": call.get("completed_at")
            }
            
            # Calculate execution time if available
            if call.get("started_at") and call.get("completed_at"):
                try:
                    start_time = datetime.fromisoformat(call["started_at"])
                    end_time = datetime.fromisoformat(call["completed_at"])
                    tool_detail["execution_time"] = round((end_time - start_time).total_seconds(), 2)
                except:
                    tool_detail["execution_time"] = "unknown"
            
            tool_details.append(tool_detail)
        
        result = {
            "response": response_text,
            "tools_used": [call["name"] for call in tool_calls],
            "tool_details": tool_details,
            "total_tools": len(tool_calls)
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session_info():
    """Get session information and conversation history"""
    try:
        session = interactive_service.get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify({
            "session_id": session_id,
            "ticker": session["ticker"],
            "created_at": session["created_at"],
            "conversation_history": session["conversation_history"],
            "tools_available": ["get_live_oi_data", "get_market_data"]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/session/<session_id>/close', methods=['POST'])
def close_session():
    """Close analysis session"""
    try:
        interactive_service.close_session(session_id)
        return jsonify({"status": "closed"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analysis/<session_id>')
def analysis_interface(session_id):
    """Serve the interactive analysis interface"""
    session = interactive_service.get_session(session_id)
    if not session:
        return "Session not found", 404
    
    # Serve HTML interface
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Analysis: {{ ticker }}</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a0a; color: #fff; }
        
        .analysis-container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .session-header { background: #111; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 20px; }
        .session-title { font-size: 28px; font-weight: 700; color: #00ff88; margin-bottom: 10px; }
        .session-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }
        .info-card { background: #1a1a1a; padding: 15px; border-radius: 8px; border: 1px solid #333; }
        .info-label { color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 5px; }
        .info-value { color: #fff; font-weight: 600; }
        
        .chat-container { background: #111; border: 1px solid #333; border-radius: 12px; height: 600px; display: flex; flex-direction: column; }
        .chat-header { padding: 20px; border-bottom: 1px solid #333; }
        .chat-title { color: #00ff88; font-weight: 600; }
        .tools-available { margin-top: 10px; color: #888; font-size: 14px; }
        .tool-tag { background: #333; padding: 3px 8px; border-radius: 4px; margin-right: 8px; font-size: 11px; }
        
        .chat-messages { flex: 1; padding: 20px; overflow-y: auto; }
        .message { margin-bottom: 20px; }
        .ai-message { background: #1a1a1a; padding: 15px; border-radius: 10px; border-left: 4px solid #00ff88; }
        .user-message { background: #222; padding: 15px; border-radius: 10px; border-left: 4px solid #0088ff; margin-left: 40px; }
        .message-time { color: #666; font-size: 11px; margin-bottom: 8px; }
        .message-content { line-height: 1.6; }
        
        .chat-input-container { padding: 20px; border-top: 1px solid #333; }
        .input-row { display: flex; gap: 10px; }
        .query-input { flex: 1; background: #222; border: 1px solid #444; border-radius: 8px; padding: 12px; color: #fff; font-size: 14px; }
        .query-input:focus { outline: none; border-color: #00ff88; }
        .send-btn { background: #00ff88; color: #000; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .send-btn:hover { background: #00cc66; }
        .send-btn:disabled { background: #444; color: #888; cursor: not-allowed; }
        
        .loading { text-align: center; color: #888; padding: 20px; }
        .tool-status { font-size: 11px; color: #666; margin-left: 5px; }
        .tool-success { color: #00ff88; }
        .tool-error { color: #ff4444; }
        .tool-pending { color: #ffaa00; }
        .suggestions { margin-bottom: 15px; }
        .suggestion { background: #333; color: #ccc; padding: 8px 12px; border-radius: 6px; display: inline-block; margin: 4px; cursor: pointer; font-size: 12px; }
        .suggestion:hover { background: #444; }
        
        /* Markdown styling for AI responses */
        .markdown-content h1, .markdown-content h2, .markdown-content h3 { color: #00ff88; margin: 16px 0 8px 0; }
        .markdown-content h1 { font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 8px; }
        .markdown-content h2 { font-size: 20px; border-bottom: 1px solid #333; padding-bottom: 4px; }
        .markdown-content h3 { font-size: 16px; }
        .markdown-content p { margin: 8px 0; line-height: 1.6; }
        .markdown-content ul, .markdown-content ol { margin: 8px 0 8px 20px; }
        .markdown-content li { margin: 4px 0; }
        .markdown-content code { background: #333; padding: 2px 6px; border-radius: 4px; font-family: 'Courier New', monospace; }
        .markdown-content pre { background: #1a1a1a; padding: 12px; border-radius: 6px; overflow-x: auto; border-left: 4px solid #00ff88; }
        .markdown-content pre code { background: none; padding: 0; }
        .markdown-content blockquote { border-left: 4px solid #666; margin: 12px 0; padding: 8px 16px; background: #1a1a1a; font-style: italic; }
        .markdown-content strong { color: #fff; font-weight: 700; }
        .markdown-content em { color: #ccc; font-style: italic; }
        .markdown-content table { border-collapse: collapse; width: 100%; margin: 12px 0; }
        .markdown-content th, .markdown-content td { border: 1px solid #333; padding: 8px 12px; text-align: left; }
        .markdown-content th { background: #333; color: #00ff88; font-weight: 600; }
        .markdown-content hr { border: none; height: 1px; background: #333; margin: 16px 0; }
    </style>
</head>
<body>
    <div class="analysis-container">
        <div class="session-header">
            <div class="session-title">🤖 Interactive Analysis: {{ ticker }}</div>
            <div class="session-info">
                <div class="info-card">
                    <div class="info-label">Pattern Type</div>
                    <div class="info-value">{{ pattern_type }}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Direction</div>
                    <div class="info-value">{{ direction }}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Confidence</div>
                    <div class="info-value">{{ confidence }}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Session</div>
                    <div class="info-value">{{ session_id }}</div>
                </div>
            </div>
        </div>
        
        <div class="chat-container">
            <div class="chat-header">
                <div class="chat-title">Interactive Analysis Session</div>
                <div class="tools-available">
                    <strong>Available Tools:</strong>
                    <span class="tool-tag">Live OI Data</span>
                    <span class="tool-tag">Market Data</span>
                    <span class="tool-tag">Custom DTE Analysis</span>
                </div>
            </div>
            
            <div class="chat-messages" id="chat-messages">
                <div class="message">
                    <div class="ai-message">
                        <div class="message-time">System • Just now</div>
                        <div class="message-content">
                            <strong>Analysis session initialized for {{ ticker }}</strong><br><br>
                            I have loaded the complete analysis context including current OI data, delta history, and smart money insights. 
                            You can ask me anything about this setup:<br><br>
                            
                            <div class="suggestions">
                                <div class="suggestion" onclick="sendSuggestion('Get fresh OI data for this ticker')">📊 Fresh OI Data</div>
                                <div class="suggestion" onclick="sendSuggestion('Show me OI data for 45 DTE options')">📈 Custom DTE Analysis</div>
                                <div class="suggestion" onclick="sendSuggestion('Get current market data and technicals')">⚡ Market Data</div>
                                <div class="suggestion" onclick="sendSuggestion('What does the current OI pattern tell us?')">🔍 Pattern Analysis</div>
                                <div class="suggestion" onclick="sendSuggestion('What are the key risks for this trade?')">⚠️ Risk Assessment</div>
                            </div>
                            
                            What would you like to explore first?
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="chat-input-container">
                <div class="input-row">
                    <input type="text" id="query-input" class="query-input" placeholder="Ask about OI patterns, risk scenarios, or request analysis..." />
                    <button id="send-btn" class="send-btn" onclick="sendQuery()">Analyze</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const sessionId = '{{ session_id }}';
        const chatMessages = document.getElementById('chat-messages');
        const queryInput = document.getElementById('query-input');
        const sendBtn = document.getElementById('send-btn');
        
        function sendQuery() {
            const query = queryInput.value.trim();
            if (!query) return;
            
            // Add user message
            addMessage('user', query);
            queryInput.value = '';
            sendBtn.disabled = true;
            sendBtn.textContent = 'Analyzing...';
            
            // Show loading
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'loading';
            loadingDiv.textContent = '🤖 Analyzing with AI tools...';
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Send to API
            fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({session_id: sessionId, query: query})
            })
            .then(response => response.json())
            .then(data => {
                loadingDiv.remove();
                if (data.error) {
                    addMessage('ai', `Error: ${data.error}`);
                } else {
                    addMessage('ai', data.response, data.tools_used, data.tool_details);
                }
            })
            .catch(error => {
                loadingDiv.remove();
                addMessage('ai', `Error: ${error.message}`);
            })
            .finally(() => {
                sendBtn.disabled = false;
                sendBtn.textContent = 'Analyze';
            });
        }
        
        function sendSuggestion(suggestion) {
            queryInput.value = suggestion;
            sendQuery();
        }
        
        function addMessage(type, content, tools = [], toolDetails = []) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            
            const time = new Date().toLocaleTimeString();
            let toolInfo = '';
            
            // Create detailed tool execution info
            if (toolDetails && toolDetails.length > 0) {
                const toolSummary = toolDetails.map(tool => {
                    const status = tool.status === 'success' ? '✅' : tool.status === 'error' ? '❌' : '⏳';
                    const execTime = tool.execution_time ? ` (${tool.execution_time}s)` : '';
                    return `${status} ${tool.name}${execTime}`;
                }).join(', ');
                toolInfo = ` • Tools: ${toolSummary}`;
            } else if (tools && tools.length > 0) {
                toolInfo = ` • Tools: ${tools.join(', ')}`;
            }
            
            // Render markdown for AI messages, plain text for user messages
            let renderedContent;
            if (type === 'ai' && window.marked) {
                // Configure marked for better code highlighting
                marked.setOptions({
                    breaks: true,
                    gfm: true
                });
                renderedContent = marked.parse(content);
            } else {
                renderedContent = content.replace(/\\n/g, '<br>');
            }
            
            messageDiv.innerHTML = `
                <div class="${type}-message">
                    <div class="message-time">${type === 'user' ? 'You' : 'AI Assistant'}${toolInfo} • ${time}</div>
                    <div class="message-content ${type === 'ai' ? 'markdown-content' : ''}">${renderedContent}</div>
                </div>
            `;
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Enter key support
        queryInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendQuery();
            }
        });
        
        // Focus input on load
        queryInput.focus();
    </script>
</body>
</html>
    """
    
    return render_template_string(html_template, 
        session_id=session_id,
        ticker=session["ticker"],
        pattern_type=session["current_analysis"].get("pattern_analysis", {}).get("pattern_type", "Unknown"),
        direction=session["current_analysis"].get("trade_recommendation", {}).get("direction", "Unknown"),
        confidence=session["current_analysis"].get("pattern_analysis", {}).get("confidence_score", "Unknown")
    )

@app.route('/')
def index():
    """Simple index page"""
    return """
    <h1>OI Pattern Tracker - Interactive Analysis Service</h1>
    <p>Interactive analysis sessions for options trading insights</p>
    <p>Use the main dashboard to create analysis sessions.</p>
    """

if __name__ == '__main__':
    print("Starting Interactive Analysis Web Service...")
    print("Access analysis sessions at: http://localhost:5001/analysis/{session_id}")
    app.run(host='0.0.0.0', port=5001, debug=True)