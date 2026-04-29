from flask import Flask, request, jsonify, render_template, session, Response
from typing import Tuple, Dict, Any, Union
from app.gemini_service import analyze_voter_intent
import os
import logging
from dotenv import load_dotenv

# Configure structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "civicmate-dev-secret-key-change-in-prod")

@app.route('/')
def home() -> str:
    """Serve the main chat interface and reset conversation history."""
    logger.info("New session started.")
    session.pop('chat_history', None)
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat() -> Tuple[Response, int]:
    """Handle incoming chat messages and return AI responses."""
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400
        
    user_message = data.get("message", "").strip()
    
    if not user_message:
        logger.warning("Empty message received.")
        return jsonify({"error": "Message is required"}), 400
    
    # Limit input length to prevent abuse
    if len(user_message) > 500:
        logger.warning("Message length exceeded limit.")
        return jsonify({"error": "Message too long. Please keep it under 500 characters."}), 400
    
    # Get chat history from session for multi-turn context
    chat_history = session.get('chat_history', [])
        
    try:
        logger.info(f"Processing message: '{user_message[:50]}...'")
        bot_response = analyze_voter_intent(user_message, chat_history)
        
        # Save this exchange to session history
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": bot_response})
        # Keep only last 10 exchanges to avoid token limits
        session['chat_history'] = chat_history[-20:]
        
        return jsonify({"response": bot_response}), 200
    except Exception as e:
        logger.error(f"SERVER ERROR processing chat: {e}")
        return jsonify({"error": "Service temporarily unavailable. Please try again."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)