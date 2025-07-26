# FastAPI OpenAI Chat API

A FastAPI application that provides chat functionality using OpenAI's API.

## Features

- RESTful API endpoints for chat functionality
- Automatic API documentation with Swagger UI
- CORS support for frontend integration
- Health check endpoint
- Environment variable configuration

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. Run the application:
   ```bash
   python main_api.py
   ```

   Or using uvicorn directly:
   ```bash
   uvicorn main_api:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### GET /
- **Description**: Root endpoint
- **Response**: Basic status message

### GET /health
- **Description**: Health check endpoint
- **Response**: API health status

### POST /api/chat
- **Description**: Chat endpoint using OpenAI
- **Request Body**:
  ```json
  {
    "prompt": "Your message here",
    "model": "gpt-3.5-turbo"  // Optional
  }
  ```
- **Response**:
  ```json
  {
    "response": "AI response",
    "prompt": "Your original prompt",
    "status": "success"
  }
  ```

## API Documentation

Once the server is running, you can access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `PORT`: Server port (default: 8000)
- `FLASK_ENV`: Environment mode (development/production)

## Project Structure

```
├── main.py          # Original OpenAI completion function
├── main_api.py      # FastAPI application
├── requirements.txt  # Python dependencies
├── Pipfile          # Pipenv dependencies
└── README.md        # This file
``` 