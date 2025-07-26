#!/usr/bin/env python3
"""
Startup script for the FastAPI application
"""

import uvicorn
import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("RELOAD", "true").lower() == "true"

    print(f"Starting FastAPI server on {host}:{port}")
    print(f"Auto-reload: {reload}")
    print(f"API Documentation: http://{host}:{port}/docs")

    # Run the application
    uvicorn.run("main_api:app", host=host, port=port, reload=reload, log_level="info")
