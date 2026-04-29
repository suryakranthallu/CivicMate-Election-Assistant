import logging
import os
from typing import Any, Dict, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def get_civic_info(address: str) -> Optional[Dict[str, Any]]:
    """
    Fetches voter information from the Google Civic Information API.

    Args:
        address (str): The voter's registered address.

    Returns:
        Optional[Dict[str, Any]]: Dictionary containing polling locations.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("API Key missing for Google Civic Information API.")
        return None

    try:
        service = build('civicinfo', 'v2', developerKey=api_key, cache_discovery=False)
        
        request = service.elections().voterInfoQuery(
            address=address,
            electionId=2000
        )
        data = request.execute()

        result = {}
        if "election" in data:
            result["election_name"] = data["election"].get("name", "Unknown Election")
            result["election_day"] = data["election"].get("electionDay", "Unknown Date")

        if "pollingLocations" in data and len(data["pollingLocations"]) > 0:
            loc = data["pollingLocations"][0]["address"]
            city = loc.get('city', '')
            state = loc.get('state', '')
            zip_code = loc.get('zip', '')
            loc_name = loc.get('locationName', '')
            line1 = loc.get('line1', '')
            
            addr_parts = [loc_name, line1, city, f"{state} {zip_code}"]
            result["polling_location"] = ", ".join([p for p in addr_parts if p.strip()])
        else:
            result["polling_location"] = "No specific polling location found."

        if "state" in data and len(data["state"]) > 0:
            body = data["state"][0].get("electionAdministrationBody", {})
            result["election_info_url"] = body.get("electionInfoUrl", "Not available")

        return result

    except HttpError as e:
        logger.warning(f"Failed to fetch Civic Info for address '{address}': {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error in Civic Info API: {e}")
        return None
