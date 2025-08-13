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
        
        # Get current analysis from Redis (latest)
        today = datetime.now().strftime('%Y-%m-%d')
        current_analysis = redis_manager.get_analysis_result(ticker, today)
        
        if not current_analysis:
            return jsonify({"error": f"No analysis found for {ticker}"}), 404
        
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
        
        # Process query - no async needed anymore
        response_text, tool_calls = interactive_service.process_query(session_id, user_query)
        
        result = {
            "response": response_text,
            "tools_used": [call["name"] for call in tool_calls]
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
        .suggestions { margin-bottom: 15px; }
        .suggestion { background: #333; color: #ccc; padding: 8px 12px; border-radius: 6px; display: inline-block; margin: 4px; cursor: pointer; font-size: 12px; }
        .suggestion:hover { background: #444; }
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
                    addMessage('ai', data.response, data.tools_used);
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
        
        function addMessage(type, content, tools = []) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            
            const time = new Date().toLocaleTimeString();
            const toolInfo = tools && tools.length > 0 ? ` • Tools: ${tools.join(', ')}` : '';
            
            messageDiv.innerHTML = `
                <div class="${type}-message">
                    <div class="message-time">${type === 'user' ? 'You' : 'AI Assistant'}${toolInfo} • ${time}</div>
                    <div class="message-content">${content.replace(/\\n/g, '<br>')}</div>
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