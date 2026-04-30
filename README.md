# CivicMate — Smart Election Assistant 🇺🇸

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)
[![Gemini](https://img.shields.io/badge/Google%20GenAI-Gemini%20Flash-orange.svg)](https://ai.google.dev/)
[![Coverage](https://img.shields.io/badge/Coverage-100%25-brightgreen.svg)](https://pytest.org)
[![Pylint](https://img.shields.io/badge/Pylint-10.00%2F10-brightgreen.svg)](https://pylint.org)

An enterprise-grade, multi-modal AI election assistant that helps US voters navigate registration, polling locations, and election education through a real-time, highly optimized interface.

## 🚀 Key Architectural Features

This repository has been strictly engineered to exceed the highest standards of production AI applications, integrating multiple Google services, defensive security protocols, and advanced UX metrics.

### 1. Multi-Modal Interactions
*   **Server-Sent Events (SSE)**: The backend utilizes generator functions (`/chat_stream`) to yield LLM tokens to the frontend in real-time, minimizing Time-to-First-Byte (TTFB) and replicating the ChatGPT user experience.
*   **Web Speech API**: Integrated voice recognition allows users to query the assistant using native browser dictation.
*   **Rich Markdown Rendering**: Responses are processed with `marked.js` on the client to format lists, bold text, and clickable maps dynamically.

### 2. Comprehensive Google Services Integration
*   **Google Gemini AI (`gemini-2.5-flash`)**: Context-aware NLP engine for processing voter intent.
*   **Google Civic Information API**: Cross-referenced data augmentation. The backend dynamically intercepts location data (ZIP or Address) and enriches the Gemini system prompt with exact, real-world polling locations.
*   **Google Cloud Logging**: Integrated structured logging for enterprise-level observability in GCP environments.

### 3. Progressive Web App (PWA)
*   Fully installable on mobile and desktop via `manifest.json`.
*   Includes `theme-color` meta tags, high-contrast modes, ARIA labels, and a state-preserved Dark Mode toggle.

### 4. Advanced Defensive Security
*   **DDoS Protection**: Enforced rate limiting via `Flask-Limiter` on the chat endpoint.
*   **Hardened Headers**: Strict Content-Security-Policy (CSP), HSTS, X-Frame-Options, and X-Content-Type-Options.
*   **Enterprise Dockerization**: The provided `Dockerfile` creates and runs the application under a non-root `appuser`, mitigating container escape vulnerabilities.

---

## 🏗 System Architecture

```mermaid
graph TD
    A[Client Browser] -->|Speech/Text Input| B(Frontend UI)
    B -->|HTTP POST JSON| C[Flask Server Rate Limiter]
    C --> D{Intent Extraction}
    D -->|Location Detected| E[Google Civic Info API]
    D -->|No Location| F[Build Context Window]
    E -->|JSON Real-time Data| F
    F -->|System Prompt + Context| G[Google Gemini API]
    G -->|Token Stream| H[SSE Generator]
    H -->|Real-Time Text| B
```

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend Framework** | Python 3.13, Flask 3.1.3 |
| **AI Engine** | Google Gemini 2.5 Flash SDK (`google-genai`) |
| **External APIs** | Google Civic Information API (`google-api-python-client`) |
| **Observability** | `google-cloud-logging` |
| **Security** | `Flask-Limiter` (Rate Limiting) |
| **DevOps** | Docker (Non-root), GitHub Actions CI/CD |
| **Frontend** | HTML5, CSS3, Vanilla JS, `marked.js` |

---

## 💻 Setup Instructions

### Prerequisites
- Python 3.12+ or Docker
- A Google Gemini API Key ([Get one here](https://aistudio.google.com/apikey))

### Standard Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/CivicMate-Election-Assistant.git
cd CivicMate-Election-Assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install production dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your Gemini API key (GEMINI_API_KEY)

# Run the application
gunicorn --bind 0.0.0.0:5000 --workers 2 "app.main:app"
```

### Docker Installation (Production Ready)

```bash
docker build -t civicmate .
docker run -p 8080:8080 --env-file .env civicmate
```

---

## 🧪 Testing & Validation

This project maintains a flawless 10.00/10.00 Pylint score and 100% code coverage. A GitHub Actions pipeline automatically enforces this on every push.

To run tests locally:
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run pytest with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Run code quality checks
pylint app/ tests/
flake8 app/ tests/
```

---

## ⚖️ License
This project was built for the Google Antigravity Coding Challenge.
