import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CIVIC_INFO_API_URL = "https://www.googleapis.com/civicinfo/v2/voterinfo"

def get_civic_info(address: str) -> Optional[Dict[str, Any]]:
    """
    Fetches voter information (polling places, elections) from the Google Civic Information API.
    
    Args:
        address (str): The voter's registered address.
        
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing polling locations and election info,
                                  or None if the API fails or address is invalid.
    """
    api_key = os.getenv("GEMINI_API_KEY") # We reuse the general Google API key
    if not api_key:
        logger.error("API Key missing for Google Civic Information API.")
        return None

    params = {
        "address": address,
        "key": api_key,
        "electionId": 2000 # 2000 is the VIP Test Election, or use real ones if available
    }

    try:
        response = requests.get(CIVIC_INFO_API_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Extract relevant info
        result = {}
        if "election" in data:
            result["election_name"] = data["election"].get("name", "Unknown Election")
            result["election_day"] = data["election"].get("electionDay", "Unknown Date")
            
        if "pollingLocations" in data and len(data["pollingLocations"]) > 0:
            location = data["pollingLocations"][0]["address"]
            result["polling_location"] = f"{location.get('locationName', '')}, {location.get('line1', '')}, {location.get('city', '')}, {location.get('state', '')} {location.get('zip', '')}".strip(', ')
        else:
            result["polling_location"] = "No specific polling location found for this address. Please check your state's official voting website."

        if "state" in data and len(data["state"]) > 0:
            local_election_info = data["state"][0].get("electionAdministrationBody", {})
            result["election_info_url"] = local_election_info.get("electionInfoUrl", "Not available")
            
        return result

    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch Civic Info for address '{address}': {e}")
        return None
