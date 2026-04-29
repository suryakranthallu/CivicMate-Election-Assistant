"""Unit tests for the Google Gemini Service."""
# pylint: disable=redefined-outer-name,import-outside-toplevel
from unittest.mock import MagicMock, patch

import pytest

from app.gemini_service import (
    _build_prompt,
    _get_civic_context,
    analyze_voter_intent,
    analyze_voter_intent_stream,
    extract_location,
)


class TestExtractLocation:
    """Tests for extract_location utility."""

    def test_extract_zip(self):
        """Should extract a 5-digit zip code."""
        assert extract_location("I live in 90210") == "90210"

    def test_extract_address(self):
        """Should extract a standard street address."""
        result = extract_location(
            "Where do I vote at 123 Main St in town?"
        )
        assert result == "123 Main St"

    def test_extract_none(self):
        """Should return None if no address or zip is found."""
        result = extract_location(
            "How does the electoral college work?"
        )
        assert result is None


class TestBuildPrompt:
    """Tests for _build_prompt helper."""

    def test_build_prompt_no_history(self):
        """Should build a prompt without history."""
        prompt = _build_prompt("Hello", None, "")
        assert "User: Hello" in prompt
        assert "Assistant:" in prompt

    def test_build_prompt_with_history(self):
        """Should include chat history in prompt."""
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"}
        ]
        prompt = _build_prompt("Follow up", history, "")
        assert "User: Hi" in prompt
        assert "Assistant: Hello!" in prompt

    def test_build_prompt_with_civic_context(self):
        """Should include civic context in prompt."""
        prompt = _build_prompt("test", None, "[CIVIC DATA]")
        assert "[CIVIC DATA]" in prompt


class TestGetCivicContext:
    """Tests for _get_civic_context helper."""

    @patch('app.gemini_service.get_civic_info')
    def test_returns_context_for_address(self, mock_civic):
        """Should return civic context when location found."""
        mock_civic.return_value = {"polling_location": "Hall"}
        result = _get_civic_context("Vote at 123 Main St")
        assert "SYSTEM INFO" in result

    @patch('app.gemini_service.get_civic_info')
    def test_returns_empty_for_no_location(self, mock_civic):
        """Should return empty string when no location found."""
        result = _get_civic_context("How do elections work?")
        assert result == ""
        mock_civic.assert_not_called()

    @patch('app.gemini_service.get_civic_info')
    def test_returns_empty_when_api_fails(self, mock_civic):
        """Should return empty string when civic API returns None."""
        mock_civic.return_value = None
        result = _get_civic_context("Vote at 123 Main St")
        assert result == ""


class TestAnalyzeVoterIntent:
    """Tests for analyze_voter_intent."""

    @patch('app.gemini_service.os.getenv')
    def test_missing_key_raises(self, mock_getenv):
        """Should raise ValueError if API key is missing."""
        mock_getenv.return_value = None
        with pytest.raises(ValueError, match="Gemini API Key"):
            analyze_voter_intent("Hello")

    @patch('app.gemini_service.client')
    @patch('app.gemini_service.get_civic_info')
    @patch('app.gemini_service.os.getenv')
    def test_with_civic_data(
        self, mock_getenv, mock_civic, mock_client
    ):
        """Should call civic API and use data in prompt."""
        mock_getenv.return_value = "TEST_KEY"
        mock_civic.return_value = {"polling_location": "Town Hall"}

        mock_response = MagicMock()
        mock_response.text = "You vote at Town Hall."
        mock_client.models.generate_content.return_value = (
            mock_response
        )

        from app.gemini_service import _response_cache
        _response_cache.clear()

        response = analyze_voter_intent(
            "Where do I vote at 123 Main St?"
        )

        assert response == "You vote at Town Hall."
        mock_civic.assert_called_once_with("123 Main St")

    @patch('app.gemini_service.client')
    @patch('app.gemini_service.os.getenv')
    def test_caching(self, mock_getenv, mock_client):
        """Should cache responses for identical queries."""
        mock_getenv.return_value = "TEST_KEY"

        mock_response = MagicMock()
        mock_response.text = "Cached response."
        mock_client.models.generate_content.return_value = (
            mock_response
        )

        from app.gemini_service import _response_cache
        _response_cache.clear()

        history = [{"role": "user", "content": "hi"}]
        res1 = analyze_voter_intent("What is voting?", history)
        res2 = analyze_voter_intent("What is voting?", history)

        assert res1 == "Cached response."
        assert res2 == "Cached response."
        mock_client.models.generate_content.assert_called_once()

    @patch('app.gemini_service.client')
    @patch('app.gemini_service.os.getenv')
    def test_api_error(self, mock_getenv, mock_client):
        """Should raise Exception if Gemini API fails."""
        mock_getenv.return_value = "TEST_KEY"
        mock_client.models.generate_content.side_effect = (
            Exception("API Down")
        )

        from app.gemini_service import _response_cache
        _response_cache.clear()

        with pytest.raises(Exception, match="API Down"):
            analyze_voter_intent("Fail please")


class TestAnalyzeVoterIntentStream:
    """Tests for analyze_voter_intent_stream."""

    @patch('app.gemini_service.os.getenv')
    def test_stream_missing_key(self, mock_getenv):
        """Should yield error message if API key missing."""
        mock_getenv.return_value = None
        chunks = list(analyze_voter_intent_stream("Hello"))
        assert any("missing" in c.lower() for c in chunks)

    @patch('app.gemini_service.client')
    @patch('app.gemini_service.os.getenv')
    def test_stream_success(self, mock_getenv, mock_client):
        """Should yield chunks from the API."""
        mock_getenv.return_value = "TEST_KEY"

        chunk1 = MagicMock()
        chunk1.text = "Hello "
        chunk2 = MagicMock()
        chunk2.text = "world!"
        mock_client.models.generate_content_stream.return_value = (
            [chunk1, chunk2]
        )

        from app.gemini_service import _response_cache
        _response_cache.clear()

        chunks = list(analyze_voter_intent_stream("Hi there"))
        assert chunks == ["Hello ", "world!"]

    @patch('app.gemini_service.client')
    @patch('app.gemini_service.os.getenv')
    def test_stream_cache(self, mock_getenv, mock_client):
        """Should serve cached response on duplicate stream."""
        mock_getenv.return_value = "TEST_KEY"

        chunk1 = MagicMock()
        chunk1.text = "Cached stream."
        mock_client.models.generate_content_stream.return_value = (
            [chunk1]
        )

        from app.gemini_service import _response_cache
        _response_cache.clear()

        list(analyze_voter_intent_stream("Cache test"))
        result = list(analyze_voter_intent_stream("Cache test"))
        assert result == ["Cached stream."]
        mock_client.models.generate_content_stream.assert_called_once()

    @patch('app.gemini_service.client')
    @patch('app.gemini_service.os.getenv')
    def test_stream_api_error(self, mock_getenv, mock_client):
        """Should yield error message if API fails."""
        mock_getenv.return_value = "TEST_KEY"
        mock_client.models.generate_content_stream.side_effect = (
            Exception("Stream failed")
        )

        from app.gemini_service import _response_cache
        _response_cache.clear()

        chunks = list(analyze_voter_intent_stream("Fail"))
        assert any("unavailable" in c.lower() for c in chunks)
