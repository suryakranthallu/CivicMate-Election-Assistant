import os
from google import genai
from dotenv import load_dotenv

# Load API key securely from .env
load_dotenv()

# Initialize Gemini client (reused across requests for efficiency)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# System prompt defining CivicMate's personality and knowledge
SYSTEM_PROMPT = """
You are 'CivicMate', an expert, neutral, and friendly US election assistant. 
Your goal is to help users with three main things:

1. REGISTRATION: If they want to register, ask what state they live in. If they provide a state, tell them to visit their state's official Secretary of State website or vote.gov to register.
2. POLLING PLACES: If they ask where to vote, tell them polling places are assigned by local counties, and they should check vote.org or their local election office.
3. LEARNING: If they ask how elections work, explain the concept (like the Electoral College or primaries) simply, neutrally, and in less than 3 sentences.

Rule: Keep your answers short, conversational, and highly accurate. NEVER make up fake links.
"""

def analyze_voter_intent(user_message, chat_history=None):
    """Uses Google Gemini to answer voter questions with conversation context."""
    
    if not os.getenv("GEMINI_API_KEY"):
        raise Exception("Gemini API Key is missing. Check your .env file.")
    
    # Build the full prompt with conversation history for multi-turn context
    full_prompt = SYSTEM_PROMPT + "\n\n"
    
    if chat_history:
        for entry in chat_history:
            role = "User" if entry["role"] == "user" else "Assistant"
            full_prompt += f"{role}: {entry['content']}\n"
    
    full_prompt += f"User: {user_message}\nAssistant:"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt
    )
    
    return response.text