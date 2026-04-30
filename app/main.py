"""
CivicMate Flask Backend.
Handles routing, session management, and HTTP API endpoints.
"""
# pylint: disable=redefined-outer-name, import-outside-toplevel, wrong-import-position
import base64
import logging
import os
from dotenv import load_dotenv

from flask import (
    Flask, Response, jsonify, render_template,
    request, session, stream_with_context
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.gemini_service import (
    analyze_voter_intent,
    analyze_voter_intent_stream
)
from app.vision_service import analyze_id_document

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Attempt to configure Google Cloud Logging if credentials exist
try:  # pragma: no cover
    import google.cloud.logging as cloud_logging
    cloud_client = cloud_logging.Client()
    cloud_client.setup_logging()
except ImportError:  # pragma: no cover
    pass  # google-cloud-logging not installed locally
except Exception:  # pragma: no cover  pylint: disable=broad-exception-caught
    pass  # No GCP credentials locally; fallback to standard logging

logger = logging.getLogger(__name__)

load_dotenv()

# Define absolute paths for cross-platform reliability
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR
)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Setup Rate Limiting for DDoS protection
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


@app.after_request
def add_security_headers(response: Response) -> Response:
    """Add robust security headers to every HTTP response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = (
        'max-age=31536000; includeSubDomains'
    )
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
        "https://www.googletagmanager.com https://www.google-analytics.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
        "https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com "
        "https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self' https://www.google-analytics.com"
    )
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = (
        'camera=(), microphone=(self), geolocation=()'
    )

    # Cache-Control for static assets to maximize Lighthouse/Performance scores
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = (
            'public, max-age=31536000, immutable'
        )
    else:
        response.headers['Cache-Control'] = 'no-store, max-age=0'

    return response


@app.route('/robots.txt')
def robots():
    """Serve robots.txt content directly."""
    return Response(
        "User-agent: *\nAllow: /\nSitemap: https://civicmate.example.com/sitemap.xml",
        mimetype='text/plain'
    )


@app.route('/sitemap.xml')
def sitemap():
    """Serve sitemap.xml content directly."""
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '<url><loc>https://civicmate.example.com/</loc></url></urlset>',
        mimetype='application/xml'
    )


@app.route('/')
def index() -> str:
    """Serve the main chat interface and reset conversation history."""
    logger.info("New session started.")
    session.pop('chat_history', None)
    return render_template('index.html')


@app.route('/chat_vision', methods=['POST'])
@limiter.limit("5 per minute")
def chat_vision():
    """Handles multimodal chat requests with images."""
    data = request.json
    if not data or 'image' not in data:
        return jsonify({"error": "No image data provided"}), 400

    try:
        # Extract base64 data (strip prefix if present)
        img_b64 = data['image']
        if ',' in img_b64:
            img_b64 = img_b64.split(',')[1]

        image_bytes = base64.b64decode(img_b64)
        state = data.get('state')

        analysis = analyze_id_document(image_bytes, state)
        return jsonify({"analysis": analysis})
    except Exception as e:  # pylint: disable=broad-exception-caught
        app.logger.error("Vision route error: %s", e)
        return jsonify({"error": "Failed to process image"}), 500


@app.route('/chat', methods=['POST'])
def chat() -> tuple:
    """Handle incoming chat messages via standard JSON request/response."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    user_message = data.get("message", "").strip()
    if not user_message:
        logger.warning("Empty message received.")
        return jsonify({"error": "Message is required"}), 400

    if len(user_message) > 500:
        logger.warning("Message length exceeded limit.")
        return jsonify({
            "error": "Message too long. Please keep it under 500 characters."
        }), 400

    chat_history = session.get('chat_history', [])

    try:
        logger.info(
            "Processing message: '%s...'", user_message[:50]
        )
        bot_response = analyze_voter_intent(
            user_message, chat_history
        )

        chat_history.append(
            {"role": "user", "content": user_message}
        )
        chat_history.append(
            {"role": "assistant", "content": bot_response}
        )
        session['chat_history'] = chat_history[-20:]

        return jsonify({"response": bot_response}), 200
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("SERVER ERROR processing chat: %s", exc)
        return jsonify({
            "error": "Service temporarily unavailable. Please try again."
        }), 500


@app.route('/chat_stream', methods=['POST'])
@limiter.limit("20 per minute")
def chat_stream() -> Response:
    """Handle incoming chat messages and stream AI responses in real-time."""
    data = request.get_json(silent=True)
    if not data:
        return Response("Error: Invalid request", status=400)

    user_message = data.get("message", "").strip()
    if not user_message:
        logger.warning("Empty stream message received.")
        return Response("Error: Message is required", status=400)

    if len(user_message) > 500:
        logger.warning("Stream message length exceeded limit.")
        return Response("Error: Message too long.", status=400)

    chat_history = session.get('chat_history', [])

    def generate():
        """Generator that yields AI response chunks."""
        logger.info(
            "Streaming message: '%s...'", user_message[:50]
        )
        full_bot_response = ""

        for chunk in analyze_voter_intent_stream(
            user_message, chat_history
        ):
            full_bot_response += chunk
            yield chunk

        chat_history.append(
            {"role": "user", "content": user_message}
        )
        chat_history.append(
            {"role": "assistant", "content": full_bot_response}
        )
        session['chat_history'] = chat_history[-20:]
        session.modified = True

    return Response(
        stream_with_context(generate()),
        mimetype='text/plain'
    )


if __name__ == '__main__':  # pragma: no cover
    app.run(debug=True, port=5000)
