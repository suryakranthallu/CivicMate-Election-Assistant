"""
Tests for the vision service module.
"""
import os
import sys
from unittest.mock import patch, MagicMock

# Ensure app is in path before imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.vision_service import analyze_id_document


class TestVisionService:
    """Tests for the Voter ID Vision Analysis service."""
    @patch('app.vision_service.client.models.generate_content')
    def test_analyze_id_document_success(self, mock_generate):
        """Should return analysis text on success."""
        mock_response = MagicMock()
        mock_response.text = "This is a valid Driver's License."
        mock_generate.return_value = mock_response

        result = analyze_id_document(b"dummy_bytes", "California")

        assert "This is a valid Driver's License." in result
        mock_generate.assert_called_once()
        # Verify state is in the prompt
        _, kwargs = mock_generate.call_args
        assert "California" in kwargs['contents'][0]

    @patch('app.vision_service.client.models.generate_content')
    def test_analyze_id_document_no_state(self, mock_generate):
        """Should work without a state provided."""
        mock_response = MagicMock()
        mock_response.text = "Generic ID analysis."
        mock_generate.return_value = mock_response

        result = analyze_id_document(b"dummy_bytes")
        assert "Generic ID analysis." in result

    @patch('app.vision_service.client.models.generate_content')
    def test_analyze_id_document_error(self, mock_generate):
        """Should return error message on failure."""
        mock_generate.side_effect = Exception("API Down")

        result = analyze_id_document(b"dummy_bytes")
        assert "Error analyzing document" in result
