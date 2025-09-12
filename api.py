import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from financial_agent import FinancialAgent
from routes import transaction_router, gmail_router

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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


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


@app.get("/test-chat", response_class=HTMLResponse)
async def test_chat_page():
    """Redirect to the static chat test page"""
    with open("static/chat-test.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    # user_info: UserInfo = Depends(get_current_user)  # Temporarily disabled
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
            username="anonymous",  # Temporarily disabled auth
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    # user_info: UserInfo = Depends(get_current_user)  # Temporarily disabled
):
    """
    Streaming chat endpoint that handles all financial requests.
    Returns a server-sent events (SSE) stream of the agent's response.

    The agent can:
    - Insert transactions (e.g., "I spent $50 on groceries")
    - Query transactions (e.g., "How much did I spend on food?")
    - Extract transaction details from text
    """
    try:

        async def event_generator():

            try:
                chunk_count = 0
                async for chunk in financial_agent.stream_chat(
                    message=request.message, chat_history=request.chat_history
                ):
                    chunk_count += 1
                    if chunk:  # Only send non-empty chunks
                        data = {
                            "content": chunk,
                            "message": request.message,
                            "status": "streaming",
                            "user_id": 0,
                            "username": "anonymous",
                        }
                        sse_data = f"data: {json.dumps(data)}\n\n"
                        yield sse_data
                # Send a final message to indicate completion
                final_data = {
                    "content": "",
                    "status": "complete",
                    "user_id": 0,
                    "username": "anonymous",
                }
                final_sse = f"data: {json.dumps(final_data)}\n\n"
                yield final_sse

            except Exception as e:
                print(f"Error in event_generator: {e}")
                import traceback

                traceback.print_exc()
                error_data = {
                    "content": f"Error: {str(e)}",
                    "message": request.message,
                    "status": "error",
                    "user_id": 0,
                    "username": "anonymous",
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            event_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            },
        )

    except Exception as e:
        print(f"[DEBUG] Exception in stream_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Include transaction routes
app.include_router(transaction_router)

# Include Gmail routes
app.include_router(gmail_router)


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
