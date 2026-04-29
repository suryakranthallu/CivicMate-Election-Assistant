"""Unit tests for the Google Civic Information API Service."""
from unittest.mock import MagicMock, patch

from app.civic_api_service import get_civic_info


class TestCivicApiService:
    @patch('app.civic_api_service.build')
    @patch('app.civic_api_service.os.getenv')
    def test_get_civic_info_missing_api_key(self, mock_getenv, mock_build):
        """Should return None and log error if API key is missing."""
        mock_getenv.return_value = None
        result = get_civic_info("123 Main St")
        assert result is None
        mock_build.assert_not_called()

    @patch('app.civic_api_service.build')
    @patch('app.civic_api_service.os.getenv')
    def test_get_civic_info_success(self, mock_getenv, mock_build):
        """Should extract polling and election info correctly from API response."""
        mock_getenv.return_value = "TEST_KEY"

        # Mock API Response
        mock_request = MagicMock()
        mock_request.execute.return_value = {
            "election": {
                "name": "VIP Test Election",
                "electionDay": "2024-11-05"
            },
            "pollingLocations": [
                {
                    "address": {
                        "locationName": "Town Hall",
                        "line1": "123 Main St",
                        "city": "Springfield",
                        "state": "IL",
                        "zip": "62701"
                    }
                }
            ],
            "state": [
                {
                    "electionAdministrationBody": {
                        "electionInfoUrl": "https://elections.il.gov"
                    }
                }
            ]
        }
        
        mock_service = MagicMock()
        mock_service.elections().voterInfoQuery.return_value = mock_request
        mock_build.return_value = mock_service

        result = get_civic_info("123 Main St")

        assert result is not None
        assert result["election_name"] == "VIP Test Election"
        assert result["election_day"] == "2024-11-05"
        assert result["polling_location"] == "Town Hall, 123 Main St, Springfield, IL 62701"
        assert result["election_info_url"] == "https://elections.il.gov"

    @patch('app.civic_api_service.build')
    @patch('app.civic_api_service.os.getenv')
    def test_get_civic_info_api_failure(self, mock_getenv, mock_build):
        """Should return None if the API request fails."""
        mock_getenv.return_value = "TEST_KEY"
        
        # Make the mock service raise an exception
        mock_service = MagicMock()
        mock_service.elections().voterInfoQuery.side_effect = Exception("Network Error")
        mock_build.return_value = mock_service

        result = get_civic_info("123 Main St")

        assert result is None
