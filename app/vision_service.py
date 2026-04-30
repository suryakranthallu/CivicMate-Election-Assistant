"""
Vision service for analyzing Voter ID documents using Gemini.
"""
import os
import logging
from typing import Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Initialize client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY", "dummy-key-for-ci")
)


def analyze_id_document(image_data: str, state: Optional[str] = None) -> str:
    """
    Analyzes an image of an ID document to verify voter eligibility requirements.
    image_data: base64 encoded image string
    state: optional state for specific requirement check
    """
    try:
        prompt = (
            "You are the 'Digital Polling Officer' for the Election Commission of India (ECI). "
            "Analyze this image of a document to verify voter eligibility based on ECI rules.\n\n"
        )
        if state:
            prompt += (
                f"Additionally, consider specific voting regulations for the state of {state}.\n\n"
            )

        prompt += (
            "**INDIAN ECI VALIDATION RULES:**\n"
            "1. **Document Type:** Is it an ECI-approved ID? Valid examples include EPIC/Voter ID, "
            "Aadhaar, PAN Card, Passport, Driving License, MGNREGA card, or Bank Passbook with "
            "photo.\n"
            "2. **Clarity/Legibility:** Is the photo clear? Are the name and key details "
            "readable?\n"
            "3. **Age Check:** If the Date of Birth (DOB) is visible, is the user likely 18 "
            "years or older?\n\n"
            "**OUTPUT FORMAT:**\n"
            "You MUST output your evaluation process inside an exact `[REASONING]...[/REASONING]` "
            "block. List your step-by-step logic checking the three rules above.\n"
            "After the `[REASONING]` block, provide a polite, neutral, and helpful conversational "
            "response addressing the user directly. (e.g., 'I see you have uploaded an Aadhaar "
            "card. It looks clear, but please ensure your current address matches your voting "
            "constituency.')\n"
            "DO NOT output any personal identifiable information (PII) like names or full ID "
            "numbers."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/jpeg"
                )
            ]
        )
        return response.text
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Vision analysis error: %s", e)
        return "Error analyzing document. Please ensure it's a clear photo of an ID."
