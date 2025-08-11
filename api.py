"""
FastAPI application with LangChain financial agent.
"""

import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from financial_agent_new import FinancialAgent
from routes import transaction_router, auth_router
from auth_service import get_current_user, UserInfo

# Load environment variables
load_dotenv(find_dotenv())

# Create FastAPI app
app = FastAPI(
    title="Financial Assistant",
    description="AI-powered financial transaction manager",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the financial agent
financial_agent = FinancialAgent()


# Pydantic models
class ChatRequest(BaseModel):
    message: str
    chat_history: list = []


class ChatResponse(BaseModel):
    response: str
    message: str
    status: str
    user_id: int
    username: str


class HealthResponse(BaseModel):
    status: str
    message: str


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return HealthResponse(
        status="success", message="Financial Assistant API is running!"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", message="API is operational")


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_info: UserInfo = Depends(get_current_user)
):
    """
    Single chat endpoint that handles all financial requests.

    The agent can:
    - Insert transactions (e.g., "I spent $50 on groceries")
    - Query transactions (e.g., "How much did I spend on food?")
    - Extract transaction details from text
    """
    try:
        # Process the message with the financial agent
        response = financial_agent.chat(
            message=request.message, chat_history=request.chat_history
        )

        return ChatResponse(
            response=response, 
            message=request.message, 
            status="success",
            user_id=0,  # We'll get this from database if needed
            username=user_info.username
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Include transaction routes
app.include_router(transaction_router)

# Include authentication routes
app.include_router(auth_router)


if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable or default to 8000
    port = int(os.environ.get("PORT", 8000))

    # Run the application
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Enable auto-reload for development
    )
