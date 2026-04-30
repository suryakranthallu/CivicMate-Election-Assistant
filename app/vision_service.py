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
            "You are the 'CivicMate ID Assistant'. Analyze this image of a document "
            "and determine if it is a valid form of Voter ID. "
        )
        if state:
            prompt += f"Focus specifically on the laws for the state of {state}. "
        
        prompt += (
            "\n\nInstructions:\n"
            "1. Identify the document type (e.g., Driver's License, Passport, Utility Bill).\n"
            "2. Check if it typically meets voter ID requirements (photo, expiration, etc.).\n"
            "3. DO NOT output any personal identifiable information (PII) like names or numbers.\n"
            "4. Provide a clear 'Verification Status' (Likely Valid / Needs More Info / Invalid).\n"
            "5. If it's a utility bill, explain that it's often used as secondary proof.\n\n"
            "Safety: If the image is not a document, say 'No valid document detected.'"
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
    except Exception as e:
        logger.error(f"Vision analysis error: {e}")
        return "Error analyzing document. Please ensure it's a clear photo of an ID."
