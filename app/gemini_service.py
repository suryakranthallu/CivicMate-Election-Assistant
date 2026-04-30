"""
Google Gemini Service Module.
Handles AI chat interactions and intent analysis for CivicMate.
"""
import json
import logging
import os
import re
from typing import Dict, Generator, List, Optional

from dotenv import load_dotenv
from google import genai

from app.civic_api_service import get_civic_info

logger = logging.getLogger(__name__)

# Load API key securely from .env
load_dotenv()

# Initialize Gemini client (reused across requests for efficiency)
# A fallback key is provided so pytest can import this module in CI environments
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY", "dummy-key-for-ci")
)

# Simple in-memory cache for efficiency
_response_cache: Dict[str, str] = {}

# System prompt defining CivicMate's personality and knowledge
SYSTEM_PROMPT = (
    "You are 'CivicMate', an expert, neutral, and friendly "
    "US election assistant.\n"
    "Your goal is to help users with three main things:\n\n"
    "1. REGISTRATION: If they want to register, ask what state "
    "they live in. If they provide a state, tell them to visit "
    "their state's official Secretary of State website or "
    "vote.gov to register.\n"
    "2. POLLING PLACES: If they ask where to vote, ask for "
    "their full address or ZIP code. If system info is provided "
    "respond entirely in that same language. Ensure all "
    "polling data and links are translated naturally.\n\n"
    "REASONING TRACE: Before your final answer, you MUST provide a "
    "concise, step-by-step reasoning block inside [REASONING]...[/REASONING] "
    "tags. List the specific data points you are checking (e.g., ZIP code, "
    "State, Google Civic API, ID Laws).\n\n"
    "DATA VISUALIZATION: Whenever you discuss statistics (like turnout), "
    "timelines (deadlines), or comparisons, also provide a "
    "structured JSON block inside [CHART_DATA]...[/CHART_DATA] tags.\n\n"
    "Rule: Keep your answers short, conversational, and highly "
    "accurate. NEVER make up fake links or polling places."
)


def extract_location(text: str) -> Optional[str]:
    """Extract an address or zip code from user text."""
    zip_match = re.search(r'\b\d{5}\b', text)
    if zip_match:
        return zip_match.group(0)

    address_pattern = (
        r'\b\d{1,5}\s+[A-Za-z0-9\s.,]+'
        r'(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|'
        r'Dr|Drive|Ln|Lane|Ct|Court|Pl|Place|Way|'
        r'Apt|Unit|Suite|#)\b'
    )
    address_match = re.search(address_pattern, text, re.IGNORECASE)
    if address_match:
        return address_match.group(0)

    return None


def _build_prompt(
    user_message: str,
    chat_history: Optional[List[Dict[str, str]]],
    civic_context: str
) -> str:
    """Build the full prompt with system prompt, civic data, and history."""
    full_prompt = SYSTEM_PROMPT + civic_context + "\n\n"

    if chat_history:
        for entry in chat_history:
            role = "User" if entry["role"] == "user" else "Assistant"
            full_prompt += f"{role}: {entry['content']}\n"

    full_prompt += f"User: {user_message}\nAssistant:"
    return full_prompt


def _get_civic_context(user_message: str) -> str:
    """Fetch civic data if a location is detected in the message."""
    location = extract_location(user_message)
    if not location:
        return ""

    logger.info(
        "Location detected: %s. Fetching Google Civic Info...",
        location
    )
    civic_data = get_civic_info(location)
    if civic_data:
        return (
            "\n[SYSTEM INFO: Google Civic API returned this data "
            "for the user's location: "
            f"{json.dumps(civic_data)}. "
            "Use this real data to answer their question.]\n"
        )
    return ""


def analyze_voter_intent(
    user_message: str,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """Use Google Gemini to answer voter questions with context."""
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("Gemini API Key is missing.")
        raise ValueError(
            "Gemini API Key is missing. Check your .env file."
        )

    # Check Cache for Efficiency
    history_str = json.dumps(chat_history) if chat_history else "[]"
    cache_key = f"{user_message}_{history_str}"
    if cache_key in _response_cache:
        logger.info("Serving response from cache.")
        return _response_cache[cache_key]

    civic_context = _get_civic_context(user_message)
    full_prompt = _build_prompt(
        user_message, chat_history, civic_context
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )

        result_text = response.text

        # Save to cache
        if result_text:
            _response_cache[cache_key] = result_text
            if len(_response_cache) > 1000:  # pragma: no cover
                _response_cache.clear()

        return result_text

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Gemini API Error: %s", exc)
        raise  # pragma: no cover


def analyze_voter_intent_stream(
    user_message: str,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> Generator[str, None, None]:
    """Stream AI response chunks for real-time typing effect."""
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("Gemini API Key is missing.")
        yield "Error: Gemini API Key is missing."
        return

    # Check Cache
    history_str = json.dumps(chat_history) if chat_history else "[]"
    cache_key = f"stream_{user_message}_{history_str}"
    if cache_key in _response_cache:
        logger.info("Serving stream from cache.")
        yield _response_cache[cache_key]
        return

    civic_context = _get_civic_context(user_message)
    full_prompt = _build_prompt(
        user_message, chat_history, civic_context
    )

    try:
        response_stream = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=full_prompt
        )

        full_response = ""
        for chunk in response_stream:
            text = chunk.text
            full_response += text
            yield text

        # Save to cache
        if full_response:
            _response_cache[cache_key] = full_response
            if len(_response_cache) > 1000:  # pragma: no cover
                _response_cache.clear()

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Gemini Stream Error: %s", exc)
        yield "Error: Service temporarily unavailable."
