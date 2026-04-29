"""Unit tests for CivicMate Election Assistant."""
from app.main import app
import json
import os
# Setup test client
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        yield client


class TestHomeRoute:
    """Tests for the home page route."""

    def test_home_returns_200(self, client):
        """Home page should load successfully."""
        response = client.get('/')
        assert response.status_code == 200

    def test_home_contains_civicmate(self, client):
        """Home page should contain the app name."""
        response = client.get('/')
        assert b'CivicMate' in response.data

    def test_home_contains_chat_form(self, client):
        """Home page should contain the chat input form."""
        response = client.get('/')
        assert b'chat-form' in response.data

    def test_home_contains_quick_actions(self, client):
        """Home page should contain quick action buttons."""
        response = client.get('/')
        assert b'quick-actions' in response.data


class TestChatRoute:
    """Tests for the chat API endpoint."""

    def test_chat_empty_message_returns_400(self, client):
        """Empty message should return 400 error."""
        response = client.post('/chat',
                               data=json.dumps({"message": ""}),
                               content_type='application/json'
                               )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_chat_whitespace_message_returns_400(self, client):
        """Whitespace-only message should return 400 error."""
        response = client.post('/chat',
                               data=json.dumps({"message": "   "}),
                               content_type='application/json'
                               )
        assert response.status_code == 400

    def test_chat_too_long_message_returns_400(self, client):
        """Message over 500 characters should be rejected."""
        long_message = "a" * 501
        response = client.post('/chat',
                               data=json.dumps({"message": long_message}),
                               content_type='application/json'
                               )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "too long" in data["error"].lower()

    @patch('app.main.analyze_voter_intent')
    def test_chat_valid_message_returns_response(self, mock_analyze, client):
        """Valid message should return a bot response."""
        mock_analyze.return_value = "You can register at vote.gov!"
        response = client.post('/chat',
                               data=json.dumps({"message": "How do I register?"}),
                               content_type='application/json'
                               )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "response" in data
        assert data["response"] == "You can register at vote.gov!"

    @patch('app.main.analyze_voter_intent')
    def test_chat_api_error_returns_500(self, mock_analyze, client):
        """API errors should return a 500 with friendly message."""
        mock_analyze.side_effect = Exception("API quota exceeded")
        response = client.post('/chat',
                               data=json.dumps({"message": "Hello"}),
                               content_type='application/json'
                               )
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data

    @patch('app.main.analyze_voter_intent')
    def test_chat_preserves_history(self, mock_analyze, client):
        """Chat history should be maintained across requests in a session."""
        mock_analyze.return_value = "First response"
        client.post('/chat',
                    data=json.dumps({"message": "First message"}),
                    content_type='application/json'
                    )

        mock_analyze.return_value = "Second response"
        client.post('/chat',
                    data=json.dumps({"message": "Second message"}),
                    content_type='application/json'
                    )

        # Verify analyze was called with history on the second call
        assert mock_analyze.call_count == 2
        second_call_args = mock_analyze.call_args_list[1]
        history = second_call_args[0][1]  # Second positional argument
        assert len(history) >= 2  # History from previous exchange is present


class TestAccessibility:
    """Tests for accessibility features."""

    def test_has_aria_labels(self, client):
        """Page should have proper ARIA labels."""
        response = client.get('/')
        assert b'aria-label' in response.data
        assert b'aria-live' in response.data

    def test_has_skip_link(self, client):
        """Page should have a skip navigation link."""
        response = client.get('/')
        assert b'skip-link' in response.data

    def test_has_meta_description(self, client):
        """Page should have a meta description for SEO."""
        response = client.get('/')
        assert b'meta name="description"' in response.data
