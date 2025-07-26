import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from openai_client import OpenAIClient

# Load environment variables
load_dotenv(find_dotenv())

# Create FastAPI app
app = FastAPI(title="FinancIAl", description="Financial Assistant", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class ChatRequest(BaseModel):
    prompt: str
    model: str = None
    temperature: float = 1.0


class ChatResponse(BaseModel):
    response: str
    prompt: str
    status: str


class HealthResponse(BaseModel):
    status: str
    message: str


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return HealthResponse(status="success", message="FastAPI is running!")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", message="API is operational")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint that uses the OpenAI completion function"""
    try:
        # Get completion using the OpenAIClient
        response = OpenAIClient().get_completion(
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature
        )

        return ChatResponse(response=response, prompt=request.prompt, status="success")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable or default to 8000
    port = int(os.environ.get("PORT", 8000))

    # Run the application
    uvicorn.run(
        "main_api:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Enable auto-reload for development
    )
