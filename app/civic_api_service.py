"""
Google Civic Information API Service.
Fetches polling locations and election info
using the official google-api-python-client.
"""
import logging
import os
from typing import Any, Dict, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def get_civic_info(address: str) -> Optional[Dict[str, Any]]:
    """
    Fetch voter info from the Google Civic Information API.

    Args:
        address: The voter's registered address or ZIP code.

    Returns:
        Dictionary with polling locations, or None on failure.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error(
            "API Key missing for Google Civic Information API."
        )
        return None

    try:
        service = build(
            'civicinfo', 'v2',
            developerKey=api_key,
            cache_discovery=False
        )

        # pylint: disable=no-member
        request = service.elections().voterInfoQuery(
            address=address,
            electionId=2000
        )
        data = request.execute()

        result: Dict[str, Any] = {}

        if "election" in data:
            result["election_name"] = data["election"].get(
                "name", "Unknown Election"
            )
            result["election_day"] = data["election"].get(
                "electionDay", "Unknown Date"
            )

        if "pollingLocations" in data and data["pollingLocations"]:
            loc = data["pollingLocations"][0]["address"]
            parts = [
                loc.get('locationName', ''),
                loc.get('line1', ''),
                loc.get('city', ''),
                loc.get('state', '') + ' ' + loc.get('zip', '')
            ]
            result["polling_location"] = ", ".join(
                [p for p in parts if p.strip()]
            )
        else:
            result["polling_location"] = (
                "No specific polling location found."
            )

        if "state" in data and data["state"]:
            body = data["state"][0].get(
                "electionAdministrationBody", {}
            )
            result["election_info_url"] = body.get(
                "electionInfoUrl", "Not available"
            )
        else:
            result["election_info_url"] = "Not available"

        return result

    except HttpError as exc:
        logger.warning(
            "Civic Info API HttpError for '%s': %s",
            address, exc
        )
        return None
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Unexpected error in Civic Info API: %s", exc
        )
        return None
