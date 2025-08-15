"""
Simple token-based authentication with AWS Cognito.
"""

import os
import hashlib
import hmac
import base64
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError


class CognitoConfig:
    """AWS Cognito configuration."""
    
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
        self.client_id = os.getenv("COGNITO_CLIENT_ID")
        self.client_secret = os.getenv("COGNITO_CLIENT_SECRET")
        
        if not self.user_pool_id or not self.client_id:
            raise ValueError(
                "COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID must be set in environment variables"
            )
        
        # Initialize Cognito client
        self.cognito_client = boto3.client(
            'cognito-idp',
            region_name=self.region
        )


class UserInfo(BaseModel):
    """User information model."""
    sub: str  # Cognito User ID
    username: str
    email: str
    email_verified: bool
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: Optional[UserInfo] = None


def compute_secret_hash(username: str, client_id: str, client_secret: str) -> str:
    """Compute SECRET_HASH for Cognito authentication."""
    message = username + client_id
    dig = hmac.new(
        str(client_secret).encode('utf-8'),
        msg=str(message).encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()


# Global Cognito config
cognito_config = CognitoConfig()

# HTTP Bearer for token validation
bearer_scheme = HTTPBearer()


async def update_token_settings(
    access_token_validity: int = 1,  # Hours
    id_token_validity: int = 1,      # Hours  
    refresh_token_validity: int = 30  # Days
) -> Dict[str, Any]:
    """Update token expiration settings for the Cognito app client."""
    try:
        response = cognito_config.cognito_client.update_user_pool_client(
            UserPoolId=cognito_config.user_pool_id,
            ClientId=cognito_config.client_id,
            AccessTokenValidity=access_token_validity,
            IdTokenValidity=id_token_validity,
            RefreshTokenValidity=refresh_token_validity
        )
        
        return response
        
    except ClientError as e:
        error_message = e.response['Error']['Message']
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update token settings: {error_message}"
        )


async def authenticate_user(username: str, password: str) -> TokenResponse:
    """Authenticate user with Cognito and return token."""
    try:
        # Prepare authentication parameters
        auth_params = {
            'USERNAME': username,
            'PASSWORD': password
        }
        
        # Add SECRET_HASH if client secret is configured
        if cognito_config.client_secret and cognito_config.client_id:
            auth_params['SECRET_HASH'] = compute_secret_hash(
                username, 
                cognito_config.client_id, 
                cognito_config.client_secret
            )
        
        # Authenticate user
        response = cognito_config.cognito_client.initiate_auth(
            ClientId=cognito_config.client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters=auth_params
        )

        # Check if user needs to set a new password
        if 'ChallengeName' in response and response['ChallengeName'] == 'NEW_PASSWORD_REQUIRED':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "NEW_PASSWORD_REQUIRED",
                    "session": response['Session'],
                    "user_id": response['ChallengeParameters']['USER_ID_FOR_SRP'],
                    "username": username,  # Include username for SECRET_HASH calculation
                    "message": "User must set a new password. Use /auth/set-new-password endpoint."
                }
            )
        
        # Get user information
        user_response = cognito_config.cognito_client.get_user(
            AccessToken=response['AuthenticationResult']['AccessToken']
        )
        
        # Extract user attributes
        user_attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}
        
        user_info = UserInfo(
            sub=user_attributes.get('sub'),
            username=username,
            email=user_attributes.get('email'),
            email_verified=user_attributes.get('email_verified', 'false').lower() == 'true',
            name=user_attributes.get('name'),
            given_name=user_attributes.get('given_name'),
            family_name=user_attributes.get('family_name')
        )
        
        return TokenResponse(
            access_token=response['AuthenticationResult']['AccessToken'],
            expires_in=response['AuthenticationResult']['ExpiresIn'],
            user=user_info
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        print(f"Error: {error_code} {error_message}")
        
        if error_code == 'NotAuthorizedException':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        elif error_code == 'UserNotConfirmedException':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not confirmed"
            )
        elif error_code == 'UserNotFoundException':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AWS Cognito error: {error_message}"
            )


async def verify_token(token: str) -> UserInfo:
    """Verify Cognito token and return user information."""
    try:
        # Get user information using the token
        user_response = cognito_config.cognito_client.get_user(
            AccessToken=token
        )
        
        # Extract user attributes
        user_attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}
        
        return UserInfo(
            sub=user_attributes.get('sub'),
            username=user_response['Username'],
            email=user_attributes.get('email'),
            email_verified=user_attributes.get('email_verified', 'false').lower() == 'true',
            name=user_attributes.get('name'),
            given_name=user_attributes.get('given_name'),
            family_name=user_attributes.get('family_name')
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'NotAuthorizedException':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )


async def create_user(
    username: str,
    email: str,
    password: str,
    attributes: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create a new user in AWS Cognito."""
    try:
        # Prepare user attributes
        user_attributes = [
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": "true"}
        ]
        
        # Add custom attributes if provided
        if attributes:
            for key, value in attributes.items():
                user_attributes.append({"Name": key, "Value": value})
        
        # Create user in Cognito
        response = cognito_config.cognito_client.admin_create_user(
            UserPoolId=cognito_config.user_pool_id,
            Username=username,
            UserAttributes=user_attributes,
            TemporaryPassword=password,
            MessageAction="SUPPRESS"  # Don't send welcome email
        )
        
        return response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UsernameExistsException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        elif error_code == 'InvalidPasswordException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet requirements"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AWS Cognito error: {error_message}"
            )


async def confirm_user_signup(username: str, confirmation_code: str) -> Dict[str, Any]:
    """Confirm user signup with confirmation code."""
    try:
        # Prepare parameters
        params = {
            "ClientId": cognito_config.client_id,
            "Username": username,
            "ConfirmationCode": confirmation_code
        }
        
        # Add SECRET_HASH if client secret is configured
        if cognito_config.client_secret and cognito_config.client_id:
            params["SecretHash"] = compute_secret_hash(
                username, 
                cognito_config.client_id, 
                cognito_config.client_secret
            )
        
        response = cognito_config.cognito_client.confirm_sign_up(**params)
        
        return response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'CodeMismatchException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid confirmation code"
            )
        elif error_code == 'ExpiredCodeException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation code has expired"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AWS Cognito error: {error_message}"
            )


async def forgot_password(username: str) -> Dict[str, Any]:
    """Initiate forgot password flow."""
    try:
        # Prepare parameters
        params = {
            "ClientId": cognito_config.client_id,
            "Username": username
        }
        
        # Add SECRET_HASH if client secret is configured
        if cognito_config.client_secret and cognito_config.client_id:
            params["SecretHash"] = compute_secret_hash(
                username, 
                cognito_config.client_id, 
                cognito_config.client_secret
            )
        
        response = cognito_config.cognito_client.forgot_password(**params)
        
        return response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UserNotFoundException':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AWS Cognito error: {error_message}"
            )


async def set_new_password(
    session: str,
    username: str,
    new_password: str
) -> TokenResponse:
    """Set new password for user in NEW_PASSWORD_REQUIRED challenge."""
    try:
        # Prepare parameters
        params = {
            "ClientId": cognito_config.client_id,
            "ChallengeName": "NEW_PASSWORD_REQUIRED",
            "Session": session,
            "ChallengeResponses": {
                "USERNAME": username,
                "NEW_PASSWORD": new_password
            }
        }
        
        # Add SECRET_HASH if client secret is configured
        if cognito_config.client_secret and cognito_config.client_id:
            params["ChallengeResponses"]["SECRET_HASH"] = compute_secret_hash(
                username, 
                cognito_config.client_id, 
                cognito_config.client_secret
            )
        
        # Complete the auth challenge
        response = cognito_config.cognito_client.respond_to_auth_challenge(**params)
        
        # Get user information
        user_response = cognito_config.cognito_client.get_user(
            AccessToken=response['AuthenticationResult']['AccessToken']
        )
        
        # Extract user attributes
        user_attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}
        
        user_info = UserInfo(
            sub=user_attributes.get('sub'),
            username=username,
            email=user_attributes.get('email'),
            email_verified=user_attributes.get('email_verified', 'false').lower() == 'true',
            name=user_attributes.get('name'),
            given_name=user_attributes.get('given_name'),
            family_name=user_attributes.get('family_name')
        )
        
        return TokenResponse(
            access_token=response['AuthenticationResult']['AccessToken'],
            expires_in=response['AuthenticationResult']['ExpiresIn'],
            user=user_info
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'InvalidPasswordException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password does not meet requirements"
            )
        elif error_code == 'ExpiredCodeException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session has expired"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AWS Cognito error: {error_message}"
            )


async def confirm_forgot_password(
    username: str,
    confirmation_code: str,
    new_password: str
) -> Dict[str, Any]:
    """Confirm forgot password with new password."""
    try:
        # Prepare parameters
        params = {
            "ClientId": cognito_config.client_id,
            "Username": username,
            "ConfirmationCode": confirmation_code,
            "Password": new_password
        }
        
        # Add SECRET_HASH if client secret is configured
        if cognito_config.client_secret and cognito_config.client_id:
            params["SecretHash"] = compute_secret_hash(
                username, 
                cognito_config.client_id, 
                cognito_config.client_secret
            )
        
        response = cognito_config.cognito_client.confirm_forgot_password(**params)
        
        return response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'CodeMismatchException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid confirmation code"
            )
        elif error_code == 'ExpiredCodeException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation code has expired"
            )
        elif error_code == 'InvalidPasswordException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password does not meet requirements"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AWS Cognito error: {error_message}"
            )

# Dependency to get current user
async def get_current_user(credentials=Depends(bearer_scheme)) -> UserInfo:
    """Get current authenticated user from token."""
    return await verify_token(credentials.credentials)
