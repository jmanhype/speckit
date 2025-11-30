"""Authentication API routes.

Endpoints:
- POST /auth/login: Authenticate vendor and return tokens
- POST /auth/refresh: Refresh access token using refresh token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.vendor import Vendor
from src.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    RefreshResponse,
    VendorResponse,
)
from src.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["authentication"])

# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Auth service instance
auth_service = AuthService()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate vendor and return access and refresh tokens.

    Args:
        credentials: Email and password
        db: Database session (injected)

    Returns:
        TokenResponse with access_token, refresh_token, and vendor info

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Find vendor by email
    vendor = db.query(Vendor).filter(Vendor.email == credentials.email).first()

    if not vendor:
        # Don't reveal whether email exists (security best practice)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not pwd_context.verify(credentials.password, vendor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate tokens
    access_token = auth_service.generate_access_token(
        vendor_id=vendor.id,
        email=vendor.email,
    )

    refresh_token = auth_service.generate_refresh_token(vendor_id=vendor.id)

    # Prepare vendor response
    vendor_response = VendorResponse(
        id=vendor.id,
        email=vendor.email,
        business_name=vendor.business_name,
        subscription_tier=vendor.subscription_tier,
        subscription_status=vendor.subscription_status,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        vendor=vendor_response,
    )


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
def refresh_access_token(
    request: RefreshTokenRequest,
) -> RefreshResponse:
    """Generate new access token from valid refresh token.

    Args:
        request: Refresh token and email

    Returns:
        RefreshResponse with new access_token

    Raises:
        HTTPException: 401 if refresh token is invalid or expired
    """
    from src.services.auth_service import (
        TokenExpiredError,
        InvalidTokenError,
        InvalidTokenTypeError,
    )

    try:
        # Generate new access token from refresh token
        new_access_token = auth_service.refresh_access_token(
            refresh_token=request.refresh_token,
            email=request.email,
        )

        return RefreshResponse(
            access_token=new_access_token,
            token_type="bearer",
        )

    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Refresh token expired: {str(e)}",
        ) from e

    except (InvalidTokenError, InvalidTokenTypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        ) from e
