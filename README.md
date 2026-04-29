# CivicMate — Smart Election Assistant 🇺🇸

An AI-powered election assistant that helps US voters understand the election process, find registration info, locate polling places, and learn how elections work — all through a friendly, conversational chat interface.

## Chosen Vertical

**Election Process Assistant** — Helps users navigate voter registration, polling locations, and election education in an interactive, easy-to-follow way.

## Approach & Logic

CivicMate uses **Google Gemini AI** (via the `google-genai` SDK) to understand user intent and provide accurate, context-aware election guidance. The assistant categorizes queries into three intent buckets:

| Intent | Description | Example |
|--------|-------------|---------|
| **Registration** | Voter registration guidance | *"How do I register to vote in Texas?"* |
| **Polling Places** | Polling location help | *"Where do I vote?"* |
| **Learning** | Election education | *"What is the Electoral College?"* |

### Key Design Decisions

- **Multi-turn conversation memory** — The assistant remembers context within a session, so users can say "Washington" as a follow-up without repeating their question.
- **Intent-aware system prompt** — Gemini is guided by a carefully crafted system prompt that ensures neutral, accurate, and concise responses.
- **Quick action buttons** — One-click suggestions reduce friction for first-time users.
- **Input validation & rate limiting** — Messages are capped at 500 characters to prevent abuse.

## How It Works

```
┌─────────────┐     HTTP POST     ┌──────────────┐     API Call     ┌─────────────────┐
│   Browser    │ ───────────────► │  Flask Server │ ──────────────► │  Google Gemini   │
│  (Chat UI)  │ ◄─────────────── │  (main.py)    │ ◄────────────── │  (gemini-2.0)    │
└─────────────┘    JSON Response  └──────────────┘    AI Response   └─────────────────┘
                                        │
                                  Session Store
                                 (Chat History)
```

1. User types a question or clicks a quick action button
2. Frontend sends the message via `POST /chat`
3. Flask backend retrieves conversation history from the session
4. Full context (system prompt + history + new message) is sent to **Google Gemini 2.0 Flash**
5. Gemini's response is returned to the frontend and displayed with an animated typing indicator

## Google Services Used

- **Google Gemini AI** (`gemini-2.0-flash` via `google-genai` SDK) — Powers all conversational AI responses
- **Google Fonts** (Inter) — Used for premium typography in the chat interface

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python, Flask |
| AI Engine | Google Gemini 2.0 Flash |
| Frontend | HTML5, CSS3, JavaScript |
| Typography | Google Fonts (Inter) |
| Session Management | Flask Sessions |

## Setup Instructions

### Prerequisites
- Python 3.10+
- A Google Gemini API key ([Get one here](https://aistudio.google.com/apikey))

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/CivicMate-Election-Assistant.git
cd CivicMate-Election-Assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your Gemini API key

# Run the application
python -m flask --app app.main run --debug --port 5000
```

Then open **http://localhost:5000** in your browser.

### Running Tests

```bash
python -m pytest tests/ -v
```

## Assumptions

1. Users are primarily interested in **US elections** (federal and state level)
2. The assistant provides **general guidance** and directs users to official sources (vote.gov, state Secretary of State websites) rather than handling registration directly
3. The assistant maintains **political neutrality** — it does not endorse candidates or parties
4. Conversation context is maintained **per browser session** (resets on page refresh)
5. Users have a stable internet connection for API calls to Google Gemini

## Project Structure

```
CivicMate-Election-Assistant/
├── app/
│   ├── __init__.py          # Package initializer
│   ├── main.py              # Flask routes and session management
│   └── gemini_service.py    # Google Gemini API integration
├── templates/
│   └── index.html           # Chat interface (accessible, responsive)
├── static/
│   └── style.css            # Styling (animations, responsive, a11y)
├── tests/
│   └── test_app.py          # Unit tests
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Accessibility Features

- ARIA roles and labels for screen readers
- Skip-to-content navigation link
- Keyboard navigation support
- High contrast mode support (`prefers-contrast: high`)
- Reduced motion support (`prefers-reduced-motion: reduce`)
- Semantic HTML5 structure

## License

This project was built for the Google Antigravity Coding Challenge.
