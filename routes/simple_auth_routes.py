"""
Simple authentication routes for token-based authentication with AWS Cognito.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from auth_service import (
    authenticate_user,
    create_user,
    confirm_user_signup,
    forgot_password,
    confirm_forgot_password,
    set_new_password,
    update_token_settings,
    get_current_user,
    UserInfo,
    TokenResponse
)

# Create router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request Models
class UserRegisterRequest(BaseModel):
    """User registration request model."""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    """User login request model."""
    username: str
    password: str


class ConfirmSignupRequest(BaseModel):
    """Confirm signup request model."""
    username: str
    confirmation_code: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request model."""
    username: str


class ConfirmForgotPasswordRequest(BaseModel):
    """Confirm forgot password request model."""
    username: str
    confirmation_code: str
    new_password: str


class SetNewPasswordRequest(BaseModel):
    """Set new password request model."""
    session: str
    username: str
    new_password: str


class TokenSettingsRequest(BaseModel):
    """Token settings request model."""
    access_token_validity: int = 1  # Hours
    id_token_validity: int = 1      # Hours
    refresh_token_validity: int = 30  # Days


# Response Models
class AuthResponse(BaseModel):
    """Authentication response model."""
    message: str
    user: Optional[dict] = None
    token: Optional[TokenResponse] = None


class UserResponse(BaseModel):
    """User response model."""
    cognito_user_id: str
    username: str
    email: str
    full_name: Optional[str]
    given_name: Optional[str]
    family_name: Optional[str]
    email_verified: bool


# Authentication Endpoints
@auth_router.post("/register", response_model=AuthResponse)
async def register_user(request: UserRegisterRequest):
    """Register a new user with AWS Cognito."""
    # Create user in AWS Cognito
    cognito_attributes = {}
    if request.full_name:
        cognito_attributes["name"] = request.full_name
    if request.given_name:
        cognito_attributes["given_name"] = request.given_name
    if request.family_name:
        cognito_attributes["family_name"] = request.family_name
    
    try:
        cognito_response = await create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            attributes=cognito_attributes
        )
        
        return AuthResponse(
            message="User registered successfully. Please check your email for confirmation code.",
            user=UserResponse(
                cognito_user_id=cognito_response["User"]["Username"],
                username=request.username,
                email=request.email,
                full_name=request.full_name,
                given_name=request.given_name,
                family_name=request.family_name,
                email_verified=False
            ).dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@auth_router.post("/login", response_model=AuthResponse)
async def login_user(request: UserLoginRequest):
    """Login user and return token."""
    try:
        # Authenticate with Cognito
        token_response = await authenticate_user(
            username=request.username,
            password=request.password
        )
        
        return AuthResponse(
            message="Login successful",
            user=UserResponse(
                cognito_user_id=token_response.user.sub,
                username=token_response.user.username,
                email=token_response.user.email,
                full_name=token_response.user.name,
                given_name=token_response.user.given_name,
                family_name=token_response.user.family_name,
                email_verified=token_response.user.email_verified
            ).dict(),
            token=token_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@auth_router.post("/confirm-signup", response_model=AuthResponse)
async def confirm_signup(request: ConfirmSignupRequest):
    """Confirm user signup with confirmation code."""
    try:
        # Confirm signup in Cognito
        await confirm_user_signup(
            username=request.username,
            confirmation_code=request.confirmation_code
        )
        
        return AuthResponse(
            message="User account confirmed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Confirmation failed: {str(e)}"
        )


@auth_router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password_endpoint(request: ForgotPasswordRequest):
    """Initiate forgot password flow."""
    try:
        await forgot_password(username=request.username)
        
        return AuthResponse(
            message="Password reset code sent successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate password reset: {str(e)}"
        )


@auth_router.post("/confirm-forgot-password", response_model=AuthResponse)
async def confirm_forgot_password_endpoint(request: ConfirmForgotPasswordRequest):
    """Confirm forgot password with new password."""
    try:
        await confirm_forgot_password(
            username=request.username,
            confirmation_code=request.confirmation_code,
            new_password=request.new_password
        )
        
        return AuthResponse(
            message="Password reset successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )


@auth_router.post("/set-new-password", response_model=AuthResponse)
async def set_new_password_endpoint(request: SetNewPasswordRequest):
    """Set new password for user in NEW_PASSWORD_REQUIRED challenge."""
    try:
        # Set new password in Cognito
        token_response = await set_new_password(
            session=request.session,
            username=request.username,
            new_password=request.new_password
        )
        
        return AuthResponse(
            message="Password set successfully",
            user=UserResponse(
                cognito_user_id=token_response.user.sub,
                username=token_response.user.username,
                email=token_response.user.email,
                full_name=token_response.user.name,
                given_name=token_response.user.given_name,
                family_name=token_response.user.family_name,
                email_verified=token_response.user.email_verified
            ).dict(),
            token=token_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set new password: {str(e)}"
        )


@auth_router.post("/token-settings", response_model=AuthResponse)
async def update_token_settings_endpoint(request: TokenSettingsRequest):
    """Update token expiration settings."""
    try:
        await update_token_settings(
            access_token_validity=request.access_token_validity,
            id_token_validity=request.id_token_validity,
            refresh_token_validity=request.refresh_token_validity
        )
        
        return AuthResponse(
            message=(
                f"Token settings updated successfully. "
                f"Access token: {request.access_token_validity}h, "
                f"ID token: {request.id_token_validity}h, "
                f"Refresh token: {request.refresh_token_validity} days"
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update token settings: {str(e)}"
        )


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(cognito_user_info: UserInfo = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        cognito_user_id=cognito_user_info.sub,
        username=cognito_user_info.username,
        email=cognito_user_info.email,
        full_name=cognito_user_info.name,
        given_name=cognito_user_info.given_name,
        family_name=cognito_user_info.family_name,
        email_verified=cognito_user_info.email_verified
    )
