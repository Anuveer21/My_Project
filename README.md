# AI Backend (Flask + SQLite)

## Features
- Chat endpoint with AI integration
- SQLite database for persistence
- Basic user memory
- Rate limiting for security

## Setup

1. Clone the repo
2. Install dependencies:
   pip install -r requirements.txt

3. Create a `.env` file:
   OPENROUTER_API_KEY=your_api_key_here

4. Run the server:
   python ai_cli.py

## API

POST /chat

Body:
{
  "message": "Hello"
}

## Notes
- `.env` is not included for security reasons
- Uses OpenRouter API
- 
