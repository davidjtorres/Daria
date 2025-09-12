"""
OAuth-based authentication with AWS Cognito JWT token validation.
"""

import os
from typing import Optional, Dict, Any
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError
from jose import JWTError, jwt
import requests


class CognitoConfig:
    """AWS Cognito configuration."""

    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
        self.client_id = os.getenv("COGNITO_CLIENT_ID")

        if not self.user_pool_id or not self.client_id:
            raise ValueError(
                "COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID must be set in environment variables"
            )

        # Cognito JWT issuer URL
        self.jwt_issuer = (
            f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
        )

        # JWKS URL for public keys
        self.jwks_url = f"{self.jwt_issuer}/.well-known/jwks.json"

        # Initialize Cognito client for user info if needed
        self.cognito_client = boto3.client("cognito-idp", region_name=self.region)


class UserInfo(BaseModel):
    """User information model."""

    user_id: str  # sub claim from JWT
    username: str
    email: str
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None


# Global Cognito config
cognito_config = CognitoConfig()

# HTTP Bearer for token validation
bearer_scheme = HTTPBearer()


@lru_cache(maxsize=1)
def get_cognito_public_keys() -> Dict[str, Any]:
    """Fetch and cache Cognito public keys for JWT validation."""
    try:
        response = requests.get(cognito_config.jwks_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch Cognito public keys: {str(e)}",
        )


def get_public_key(token_header: Dict[str, Any]) -> str:
    """Get the public key for JWT verification."""
    jwks = get_cognito_public_keys()
    kid = token_header.get("kid")

    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token header missing 'kid'",
        )

    # Find the key with matching kid
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find appropriate public key",
    )


async def verify_jwt_token(token: str) -> UserInfo:
    """Verify JWT token and extract user information."""
    try:
        # Decode token header to get kid
        unverified_header = jwt.get_unverified_header(token)

        # Get the public key
        public_key = get_public_key(unverified_header)

        # Verify and decode the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=cognito_config.client_id,
            issuer=cognito_config.jwt_issuer,
        )

        # Extract user information from JWT claims
        user_info = UserInfo(
            user_id=payload.get("sub") or "",
            username=payload.get("cognito:username", payload.get("username", "")),
            email=payload.get("email", ""),
            email_verified=payload.get("email_verified", False),
            name=payload.get("name"),
            given_name=payload.get("given_name"),
            family_name=payload.get("family_name"),
        )

        return user_info

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT token: {str(e)}",
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token payload: missing {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
        )


async def get_user_from_cognito(access_token: str) -> UserInfo:
    """Alternative method: Get user info directly from Cognito API."""
    try:
        # Get user information using the access token
        user_response = cognito_config.cognito_client.get_user(AccessToken=access_token)

        # Extract user attributes
        user_attributes = {
            attr["Name"]: attr["Value"] for attr in user_response["UserAttributes"]
        }

        return UserInfo(
            user_id=user_attributes.get("sub") or "",
            username=user_response["Username"],
            email=user_attributes.get("email", ""),
            email_verified=user_attributes.get("email_verified", "false").lower()
            == "true",
            name=user_attributes.get("name"),
            given_name=user_attributes.get("given_name"),
            family_name=user_attributes.get("family_name"),
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code == "NotAuthorizedException":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {e.response['Error']['Message']}",
            )


# Dependency to get current user from JWT token
async def get_current_user(credentials=Depends(bearer_scheme)) -> UserInfo:
    """
    Get current authenticated user from JWT token.

    This dependency validates the JWT token and returns user information.
    Use this as a dependency in your FastAPI routes that require authentication.
    """
    token = credentials.credentials

    # Try JWT validation first (faster, stateless)
    try:
        return await verify_jwt_token(token)
    except HTTPException:
        # Fallback to Cognito API call if JWT validation fails
        # This is useful during development or if you need the most up-to-date user info
        return await get_user_from_cognito(token)


# Optional: Dependency for optional authentication
async def get_current_user_optional(
    credentials=Depends(HTTPBearer(auto_error=False)),
) -> Optional[UserInfo]:
    """
    Optional authentication dependency.
    Returns user info if valid token provided, None otherwise.
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        return await verify_jwt_token(credentials.credentials)
    except HTTPException:
        return None
