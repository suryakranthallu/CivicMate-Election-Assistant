from flask import Flask, request, jsonify, render_template, session
from app.gemini_service import analyze_voter_intent
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "civicmate-dev-secret-key-change-in-prod")

@app.route('/')
def home():
    """Serve the main chat interface and reset conversation history."""
    session.pop('chat_history', None)
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle incoming chat messages and return AI responses."""
    data = request.json
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    # Limit input length to prevent abuse
    if len(user_message) > 500:
        return jsonify({"error": "Message too long. Please keep it under 500 characters."}), 400
    
    # Get chat history from session for multi-turn context
    chat_history = session.get('chat_history', [])
        
    try:
        bot_response = analyze_voter_intent(user_message, chat_history)
        
        # Save this exchange to session history
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": bot_response})
        # Keep only last 10 exchanges to avoid token limits
        session['chat_history'] = chat_history[-20:]
        
        return jsonify({"response": bot_response})
    except Exception as e:
        print(f"SERVER ERROR: {e}")
        return jsonify({"error": "Service temporarily unavailable. Please try again."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)