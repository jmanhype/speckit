"""Square OAuth API routes.

Endpoints:
- GET /square/connect - Initiate OAuth flow
- GET /square/callback - OAuth callback handler
- GET /square/status - Connection status
- DELETE /square/disconnect - Disconnect Square account
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.middleware.auth import get_current_vendor
from src.models.square_token import SquareToken
from src.models.vendor import Vendor
from src.services.square_oauth import square_oauth_service


router = APIRouter(prefix="/square", tags=["square"])


class ConnectResponse(BaseModel):
    """Response for initiating OAuth flow."""

    authorization_url: str
    state: str


class CallbackRequest(BaseModel):
    """Request for OAuth callback."""

    code: str
    state: str


class ConnectionStatus(BaseModel):
    """Square connection status."""

    is_connected: bool
    merchant_id: Optional[str] = None
    connected_at: Optional[str] = None
    scopes: Optional[list[str]] = None


@router.get("/connect", response_model=ConnectResponse)
def initiate_oauth_flow(
    vendor_id: UUID = Depends(get_current_vendor),
) -> ConnectResponse:
    """Initiate Square OAuth flow.

    Returns authorization URL for frontend to redirect to.

    Args:
        vendor_id: Current vendor ID (from auth middleware)

    Returns:
        ConnectResponse with authorization URL and state token
    """
    # Generate authorization URL with CSRF token
    auth_data = square_oauth_service.generate_authorization_url()

    return ConnectResponse(
        authorization_url=auth_data["url"],
        state=auth_data["state"],
    )


@router.post("/callback")
async def handle_oauth_callback(
    callback: CallbackRequest,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> dict:
    """Handle Square OAuth callback.

    Exchanges authorization code for access/refresh tokens.

    Args:
        callback: Authorization code and state from Square
        vendor_id: Current vendor ID (from auth middleware)
        db: Database session

    Returns:
        Success message with connection status
    """
    # TODO: Validate CSRF token (state) against session
    # For MVP, we'll skip CSRF validation but should add in production

    try:
        # Exchange code for tokens
        square_token = await square_oauth_service.exchange_code_for_tokens(
            authorization_code=callback.code,
            vendor_id=vendor_id,
            db=db,
        )

        return {
            "message": "Square connected successfully",
            "merchant_id": square_token.merchant_id,
            "connected_at": square_token.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect Square: {str(e)}",
        )


@router.get("/status", response_model=ConnectionStatus)
def get_connection_status(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> ConnectionStatus:
    """Get Square connection status for current vendor.

    Args:
        vendor_id: Current vendor ID (from auth middleware)
        db: Database session

    Returns:
        ConnectionStatus with connection details
    """
    # Get vendor
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )

    # Get Square token
    square_token = (
        db.query(SquareToken)
        .filter(
            SquareToken.vendor_id == vendor_id,
            SquareToken.is_active == True,
        )
        .first()
    )

    if not square_token:
        return ConnectionStatus(is_connected=False)

    # Parse scopes
    scopes = square_token.scopes.split() if square_token.scopes else []

    return ConnectionStatus(
        is_connected=True,
        merchant_id=square_token.merchant_id,
        connected_at=square_token.created_at.isoformat(),
        scopes=scopes,
    )


@router.delete("/disconnect")
def disconnect_square(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> dict:
    """Disconnect Square account.

    Marks Square token as inactive and updates vendor status.

    Args:
        vendor_id: Current vendor ID (from auth middleware)
        db: Database session

    Returns:
        Success message
    """
    # Get Square token
    square_token = (
        db.query(SquareToken).filter(SquareToken.vendor_id == vendor_id).first()
    )

    if square_token:
        # Mark as inactive
        square_token.is_active = False

    # Update vendor
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if vendor:
        vendor.square_connected = False
        vendor.square_merchant_id = None

    db.commit()

    return {"message": "Square disconnected successfully"}
