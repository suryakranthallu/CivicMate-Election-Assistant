"""Unit tests for the Google Gemini Service."""

from unittest.mock import MagicMock, patch

import pytest

from app.gemini_service import analyze_voter_intent, extract_location


class TestGeminiService:
    def test_extract_location_zip(self):
        """Should extract a 5-digit zip code."""
        assert extract_location("I live in 90210") == "90210"

    def test_extract_location_address(self):
        """Should extract a standard street address."""
        assert extract_location("Where do I vote at 123 Main St in town?") == "123 Main St"

    def test_extract_location_none(self):
        """Should return None if no address or zip is found."""
        assert extract_location("How does the electoral college work?") is None

    @patch('app.gemini_service.os.getenv')
    def test_analyze_voter_intent_missing_key(self, mock_getenv):
        """Should raise ValueError if API key is missing."""
        mock_getenv.return_value = None
        with pytest.raises(ValueError, match="Gemini API Key is missing"):
            analyze_voter_intent("Hello")

    @patch('app.gemini_service.client')
    @patch('app.gemini_service.get_civic_info')
    @patch('app.gemini_service.os.getenv')
    def test_analyze_voter_intent_with_civic_data(self, mock_getenv, mock_civic, mock_client):
        """Should call civic API if address is provided and use it in prompt."""
        mock_getenv.return_value = "TEST_KEY"
        mock_civic.return_value = {"polling_location": "Town Hall"}
        
        mock_response = MagicMock()
        mock_response.text = "You vote at Town Hall."
        mock_client.models.generate_content.return_value = mock_response

        # Clear cache before test to ensure it hits the API
        from app.gemini_service import _response_cache
        _response_cache.clear()

        response = analyze_voter_intent("Where do I vote at 123 Main St?")
        
        assert response == "You vote at Town Hall."
        mock_civic.assert_called_once_with("123 Main St")
        mock_client.models.generate_content.assert_called_once()

    @patch('app.gemini_service.client')
    @patch('app.gemini_service.os.getenv')
    def test_analyze_voter_intent_caching(self, mock_getenv, mock_client):
        """Should cache responses for identical queries."""
        mock_getenv.return_value = "TEST_KEY"
        
        mock_response = MagicMock()
        mock_response.text = "This is a cached response."
        mock_client.models.generate_content.return_value = mock_response

        from app.gemini_service import _response_cache
        _response_cache.clear()

        # First call hits API
        res1 = analyze_voter_intent("What is voting?", [{"role": "user", "content": "hi"}])
        
        # Second call hits cache
        res2 = analyze_voter_intent("What is voting?", [{"role": "user", "content": "hi"}])
        
        assert res1 == "This is a cached response."
        assert res2 == "This is a cached response."
        # Verify API was only called ONCE
        mock_client.models.generate_content.assert_called_once()

    @patch('app.gemini_service.client')
    @patch('app.gemini_service.os.getenv')
    def test_analyze_voter_intent_api_error(self, mock_getenv, mock_client):
        """Should raise Exception if Gemini API fails."""
        mock_getenv.return_value = "TEST_KEY"
        
        mock_client.models.generate_content.side_effect = Exception("API Down")

        from app.gemini_service import _response_cache
        _response_cache.clear()

        with pytest.raises(Exception, match="API Down"):
            analyze_voter_intent("Fail please")
