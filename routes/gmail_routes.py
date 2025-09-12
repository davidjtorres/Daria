"""
Gmail authentication routes for Google OAuth integration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from auth_service import get_current_user, UserInfo


# Create router
gmail_router = APIRouter(prefix="/gmail", tags=["Gmail"])


class GoogleTokensRequest(BaseModel):
    """Google OAuth tokens request model."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str


class GoogleTokensResponse(BaseModel):
    """Google OAuth tokens response model."""
    status: str
    message: str
    user_id: str


@gmail_router.post("/connect", response_model=GoogleTokensResponse)
async def store_google_tokens(
    tokens: GoogleTokensRequest, user_info: UserInfo = Depends(get_current_user)
):
    """
    Store Google OAuth tokens for authenticated user.

    This endpoint receives Google OAuth tokens after successful authentication
    and associates them with the current user for Gmail API access.
    """
    try:
        # TODO: Store tokens in database associated with user_info.user_id
        # Example database storage:
        # await store_user_google_tokens(
        #     user_id=user_info.user_id,
        #     access_token=tokens.access_token,
        #     refresh_token=tokens.refresh_token,
        #     expires_in=tokens.expires_in,
        #     scope=tokens.scope
        # )

        # For now, just return success
        # In production, you would:
        # 1. Validate the tokens by making a test API call to Google
        # 2. Store tokens securely in your database
        # 3. Set up token refresh mechanism
        return GoogleTokensResponse(
            status="success",
            message="Google account connected successfully",
            user_id=user_info.user_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store Google tokens: {str(e)}",
        )
