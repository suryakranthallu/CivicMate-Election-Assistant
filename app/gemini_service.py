"""
Google Gemini Service Module.
Handles the AI chat interactions and intent analysis for CivicMate.
"""
import json
import logging
import os
import re
from typing import Dict, List, Optional

from dotenv import load_dotenv
from google import genai

from app.civic_api_service import get_civic_info

logger = logging.getLogger(__name__)

# Load API key securely from .env
load_dotenv()

# Initialize Gemini client (reused across requests for efficiency)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Simple in-memory cache for efficiency
_response_cache: Dict[str, str] = {}

# System prompt defining CivicMate's personality and knowledge
SYSTEM_PROMPT = """
You are 'CivicMate', an expert, neutral, and friendly US election assistant. 
Your goal is to help users with three main things:

1. REGISTRATION: If they want to register, ask what state they live in. If they provide a state, tell them to visit their state's official Secretary of State website or vote.gov to register.
2. POLLING PLACES: If they ask where to vote, ask for their full address or ZIP code. If system info is provided with their polling place, tell them the exact location.
3. LEARNING: If they ask how elections work, explain the concept simply, neutrally, and in less than 3 sentences.

Rule: Keep your answers short, conversational, and highly accurate. NEVER make up fake links or polling places.
"""


def extract_location(text: str) -> Optional[str]:
    """Basic extraction of address or zip code from text for the Civic API."""
    # Look for 5-digit zip codes
    zip_match = re.search(r'\b\d{5}\b', text)
    if zip_match:
        return zip_match.group(0)

    # Look for basic address patterns (e.g., "123 Main St")
    address_match = re.search(
        r'\b\d{1,5}\s+[A-Za-z0-9\s.,]+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Ct|Court|Pl|Place|Way|Apt|Unit|Suite|#)\b', text, re.IGNORECASE)
    if address_match:
        return address_match.group(0)

    return None


def analyze_voter_intent(user_message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
    """Uses Google Gemini to answer voter questions with conversation context."""

    if not os.getenv("GEMINI_API_KEY"):
        logger.error("Gemini API Key is missing.")
        raise ValueError("Gemini API Key is missing. Check your .env file.")

    # Check Cache for Efficiency
    history_str = json.dumps(chat_history) if chat_history else "[]"
    cache_key = f"{user_message}_{history_str}"
    if cache_key in _response_cache:
        logger.info("Serving response from cache.")
        return _response_cache[cache_key]

    # Integrate Google Civic Information API
    civic_context = ""
    location = extract_location(user_message)
    if location:
        logger.info("Location detected: %s. Fetching Google Civic Info...", location)
        civic_data = get_civic_info(location)
        if civic_data:
            civic_context = (
                f"\n[SYSTEM INFO: Google Civic API returned this data for the user's location: "
                f"{json.dumps(civic_data)}. Use this real data to answer their question about where to vote.]\n"
            )

    # Build the full prompt with conversation history for multi-turn context
    full_prompt = SYSTEM_PROMPT + civic_context + "\n\n"

    if chat_history:
        for entry in chat_history:
            role = "User" if entry["role"] == "user" else "Assistant"
            full_prompt += f"{role}: {entry['content']}\n"

    full_prompt += f"User: {user_message}\nAssistant:"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )

        result_text = response.text

        # Save to cache
        if result_text:
            _response_cache[cache_key] = result_text
            if len(_response_cache) > 1000:  # Prevent unbounded memory growth
                _response_cache.clear()

        return result_text

    except Exception as e: # pylint: disable=broad-exception-caught
        logger.error("Gemini API Error: %s", e)
        raise
