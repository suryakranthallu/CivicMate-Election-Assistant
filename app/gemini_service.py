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
    "Indian election assistant.\n"
    "Your goal is to assess the user's voter readiness and categorize "
    "them into one of 3 states:\n\n"
    "STATE 1: Unregistered. (Action: Instruct them to fill out Form 6 online via the "
    "Election Commission of India (ECI) or NVSP portal).\n\n"
    "STATE 2: Registered, but missing Booth Info. (Action: Instruct them to search the ECI "
    "Electoral Roll using their EPIC number to find their Part Number and Polling Station).\n\n"
    "STATE 3: Fully Ready. (Action: Generate a markdown 'Voting Day Itinerary'. Suggest a "
    "specific time to vote to avoid crowds. You MUST output a JSON block inside "
    "[CALENDAR_DATA]...[/CALENDAR_DATA] tags. Use format: {\"title\": \"Voting Day\", "
    "\"date\": \"20240520\", \"description\": \"Vote at Booth X\"}).\n\n"
    "PREDICTIVE CROWD LOGIC (Apply when discussing when to vote):\n"
    "- Morning Rush (7AM-9AM): High crowd (Senior citizens & office-goers).\n"
    "- Mid-Day Lull (1PM-3PM): Low crowd (Peak heat, lowest turnout).\n"
    "- Evening Surge (4PM-6PM): High crowd (Last-minute & daily wage workers).\n\n"
    "REASONING TRACE: Before your final answer, you MUST provide a "
    "step-by-step reasoning block inside [REASONING]...[/REASONING] "
    "tags explaining which state the user is in and showing your crowd prediction logic.\n\n"
    "DATA VISUALIZATION: If discussing statistics, provide a JSON block inside "
    "[CHART_DATA]...[/CHART_DATA] tags.\n\n"
    "Rule: Keep answers highly accurate and conversational. Do not hallucinate links."
)


def extract_location(text: str) -> Optional[str]:
    """
    Extract an address or Indian Pincode from user text.
    Modified for ECI Edition to support 6-digit Pincodes.
    """
    pincode_match = re.search(r'\b\d{6}\b', text)
    if pincode_match:
        return pincode_match.group(0)

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
