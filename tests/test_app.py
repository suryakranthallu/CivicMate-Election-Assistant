"""Unit tests for CivicMate Election Assistant."""
# pylint: disable=redefined-outer-name, import-outside-toplevel, wrong-import-position
import os
import sys

# Ensure app is in path before imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from unittest.mock import patch
import pytest
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['RATELIMIT_ENABLED'] = False
    with app.test_client() as test_client:
        yield test_client


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
    """Tests for the /chat JSON API endpoint."""

    def test_chat_invalid_request_returns_400(self, client):
        """Missing JSON data should return 400."""
        response = client.post('/chat', data="Not JSON")
        assert response.status_code == 400

    def test_chat_empty_message_returns_400(self, client):
        """Empty message should return 400 error."""
        response = client.post(
            '/chat',
            data=json.dumps({"message": ""}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_chat_whitespace_message_returns_400(self, client):
        """Whitespace-only message should return 400 error."""
        response = client.post(
            '/chat',
            data=json.dumps({"message": "   "}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_chat_too_long_message_returns_400(self, client):
        """Message over 500 characters should be rejected."""
        long_message = "a" * 501
        response = client.post(
            '/chat',
            data=json.dumps({"message": long_message}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "too long" in data["error"].lower()

    @patch('app.main.analyze_voter_intent')
    def test_chat_valid_message_returns_response(
        self, mock_analyze, client
    ):
        """Valid message should return a bot response."""
        mock_analyze.return_value = "You can register at vote.gov!"
        response = client.post(
            '/chat',
            data=json.dumps({"message": "How do I register?"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "response" in data
        assert data["response"] == "You can register at vote.gov!"

    @patch('app.main.analyze_voter_intent')
    def test_chat_api_error_returns_500(
        self, mock_analyze, client
    ):
        """API errors should return a 500 with friendly message."""
        mock_analyze.side_effect = Exception("API quota exceeded")
        response = client.post(
            '/chat',
            data=json.dumps({"message": "Hello"}),
            content_type='application/json'
        )
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data

    @patch('app.main.analyze_voter_intent')
    def test_chat_preserves_history(self, mock_analyze, client):
        """Chat history should persist across requests in session."""
        mock_analyze.return_value = "First response"
        client.post(
            '/chat',
            data=json.dumps({"message": "First message"}),
            content_type='application/json'
        )

        mock_analyze.return_value = "Second response"
        client.post(
            '/chat',
            data=json.dumps({"message": "Second message"}),
            content_type='application/json'
        )

        assert mock_analyze.call_count == 2
        second_call_args = mock_analyze.call_args_list[1]
        history = second_call_args[0][1]
        assert len(history) >= 2


class TestChatStreamRoute:
    """Tests for the /chat_stream SSE endpoint."""

    def test_stream_invalid_request_returns_400(self, client):
        """Missing JSON data should return 400."""
        response = client.post('/chat_stream', data="Not JSON")
        assert response.status_code == 400

    def test_stream_empty_message_returns_400(self, client):
        """Empty message should return 400."""
        response = client.post(
            '/chat_stream',
            data=json.dumps({"message": ""}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_stream_too_long_message_returns_400(self, client):
        """Over 500 char message should return 400."""
        response = client.post(
            '/chat_stream',
            data=json.dumps({"message": "x" * 501}),
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('app.main.analyze_voter_intent_stream')
    def test_stream_valid_message_returns_chunks(
        self, mock_stream, client
    ):
        """Valid message should stream response chunks."""
        mock_stream.return_value = iter(["Hello ", "world!"])
        response = client.post(
            '/chat_stream',
            data=json.dumps({"message": "Hi"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        assert b"Hello world!" in response.data


class TestSecurityHeaders:
    """Tests for security headers on all responses."""

    def test_has_xss_protection(self, client):
        """Response should have X-XSS-Protection header."""
        response = client.get('/')
        assert response.headers.get('X-XSS-Protection') == (
            '1; mode=block'
        )

    def test_has_content_type_options(self, client):
        """Response should have X-Content-Type-Options header."""
        response = client.get('/')
        assert response.headers.get(
            'X-Content-Type-Options'
        ) == 'nosniff'

    def test_has_frame_options(self, client):
        """Response should have X-Frame-Options header."""
        response = client.get('/')
        assert response.headers.get(
            'X-Frame-Options'
        ) == 'SAMEORIGIN'

    def test_has_hsts(self, client):
        """Response should have Strict-Transport-Security."""
        response = client.get('/')
        hsts = response.headers.get('Strict-Transport-Security')
        assert 'max-age' in hsts

    def test_has_csp(self, client):
        """Response should have Content-Security-Policy."""
        response = client.get('/')
        csp = response.headers.get('Content-Security-Policy')
        assert csp is not None
        assert "default-src" in csp

    def test_has_referrer_policy(self, client):
        """Response should have Referrer-Policy header."""
        response = client.get('/')
        assert response.headers.get('Referrer-Policy') is not None

    def test_static_asset_cache_control(self, client):
        """Static assets should have public cache-control."""
        response = client.get('/static/style.css')
        cache = response.headers.get('Cache-Control')
        assert cache is not None
        assert 'public' in cache
        assert '31536000' in cache


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

    def test_has_dark_mode_toggle(self, client):
        """Page should have a dark mode toggle button."""
        response = client.get('/')
        assert b'theme-toggle' in response.data

    def test_has_mic_button(self, client):
        """Page should have a microphone button for voice input."""
        response = client.get('/')
        assert b'mic-btn' in response.data


class TestVisionRoute:
    """Tests for the /chat_vision multimodal endpoint."""

    @patch('app.main.analyze_id_document')
    def test_chat_vision_success(self, mock_analyze, client):
        """Should return analysis for a valid image request."""
        mock_analyze.return_value = "Analysis complete."

        dummy_b64 = "data:image/jpeg;base64,ZHVtbXk="
        response = client.post('/chat_vision', json={
            'image': dummy_b64,
            'state': 'Texas'
        })

        assert response.status_code == 200
        assert response.json['analysis'] == "Analysis complete."
        # ZHVtbXk= is base64 for 'dummy'
        mock_analyze.assert_called_once_with(b'dummy', 'Texas')

    def test_chat_vision_no_data(self, client):
        """Should return 400 if no image is provided."""
        response = client.post('/chat_vision', json={})
        assert response.status_code == 400

    @patch('app.main.analyze_id_document')
    def test_chat_vision_exception(self, mock_analyze, client):
        """Should return 500 on internal errors."""
        mock_analyze.side_effect = Exception("Broke")
        response = client.post('/chat_vision', json={'image': 'ZHVtbXk='})
        assert response.status_code == 500


class TestSEO:
    """Tests for SEO-related endpoints."""

    def test_robots_txt(self, client):
        """Should serve robots.txt."""
        response = client.get('/robots.txt')
        assert response.status_code == 200
        assert b'User-agent' in response.data

    def test_sitemap_xml(self, client):
        """Should serve sitemap.xml."""
        response = client.get('/sitemap.xml')
        assert response.status_code == 200
        assert b'xml' in response.data
        assert b'urlset' in response.data
