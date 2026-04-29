"""Unit tests for the Google Civic Information API Service."""
# pylint: disable=redefined-outer-name,import-outside-toplevel
from unittest.mock import MagicMock, patch

from app.civic_api_service import get_civic_info


class TestCivicApiService:
    """Tests for the get_civic_info function."""

    @patch('app.civic_api_service.build')
    @patch('app.civic_api_service.os.getenv')
    def test_missing_api_key(self, mock_getenv, mock_build):
        """Should return None if API key is missing."""
        mock_getenv.return_value = None
        result = get_civic_info("123 Main St")
        assert result is None
        mock_build.assert_not_called()

    @patch('app.civic_api_service.build')
    @patch('app.civic_api_service.os.getenv')
    def test_success(self, mock_getenv, mock_build):
        """Should extract polling and election info."""
        mock_getenv.return_value = "TEST_KEY"

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
                        "electionInfoUrl": (
                            "https://elections.il.gov"
                        )
                    }
                }
            ]
        }

        mock_service = MagicMock()
        mock_service.elections().voterInfoQuery.return_value = (
            mock_request
        )
        mock_build.return_value = mock_service

        result = get_civic_info("123 Main St")

        assert result is not None
        assert result["election_name"] == "VIP Test Election"
        assert result["election_day"] == "2024-11-05"
        assert "Town Hall" in result["polling_location"]
        assert result["election_info_url"] == (
            "https://elections.il.gov"
        )

    @patch('app.civic_api_service.build')
    @patch('app.civic_api_service.os.getenv')
    def test_http_error(self, mock_getenv, mock_build):
        """Should return None on HttpError."""
        mock_getenv.return_value = "TEST_KEY"

        from googleapiclient.errors import HttpError
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.reason = "Internal Server Error"

        mock_service = MagicMock()
        mock_service.elections().voterInfoQuery.side_effect = (
            HttpError(resp=mock_resp, content=b'{}')
        )
        mock_build.return_value = mock_service

        result = get_civic_info("123 Main St")
        assert result is None

    @patch('app.civic_api_service.build')
    @patch('app.civic_api_service.os.getenv')
    def test_general_exception(self, mock_getenv, mock_build):
        """Should return None on general Exception."""
        mock_getenv.return_value = "TEST_KEY"

        mock_service = MagicMock()
        mock_service.elections().voterInfoQuery.side_effect = (
            ValueError("Some weird error")
        )
        mock_build.return_value = mock_service

        result = get_civic_info("123 Main St")
        assert result is None

    @patch('app.civic_api_service.build')
    @patch('app.civic_api_service.os.getenv')
    def test_no_polling_or_state(self, mock_getenv, mock_build):
        """Should handle response without pollingLocations."""
        mock_getenv.return_value = "TEST_KEY"

        mock_request = MagicMock()
        mock_request.execute.return_value = {
            "election": {
                "name": "Test",
                "electionDay": "2024"
            }
        }
        mock_service = MagicMock()
        mock_service.elections().voterInfoQuery.return_value = (
            mock_request
        )
        mock_build.return_value = mock_service

        result = get_civic_info("123 Main St")

        assert result is not None
        assert "No specific" in result["polling_location"]
        assert result["election_info_url"] == "Not available"
