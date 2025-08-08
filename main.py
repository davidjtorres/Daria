#!/usr/bin/env python3
"""
Run script for the restructured Financial Assistant API.
"""

import os
import uvicorn
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())


def main():
    """Start the Financial Assistant API server."""
    print("Starting Financial Assistant API server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("Chat Endpoint: http://localhost:8000/chat")
    print("\nPress Ctrl+C to stop the server")

    # Get port from environment variable or default to 8000
    port = int(os.environ.get("PORT", 8000))

    # Run the application
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level="info",
    )


if __name__ == "__main__":
    main()
