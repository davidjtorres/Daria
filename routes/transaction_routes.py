"""
Transaction routes for the financial API.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from repositories import TransactionRepository

# Create router
router = APIRouter(prefix="/transaction", tags=["transactions"])

# Initialize repository
transaction_repository = TransactionRepository()


# Pydantic models
class TransactionCreateRequest(BaseModel):
    amount: float
    description: str
    category: str
    type: str
    date: Optional[str] = None


class TransactionResponse(BaseModel):
    id: Optional[int]
    amount: int
    description: str
    category: str
    type: str
    date: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


@router.post("/", response_model=TransactionResponse)
async def create_transaction(request: TransactionCreateRequest):
    """
    Create a new transaction.
    
    Args:
        request: Transaction data including amount, description, category, type, and optional date
        
    Returns:
        The created transaction with all fields populated
    """
    try:
        # Parse date if provided
        transaction_date = None
        if request.date:
            try:
                transaction_date = datetime.fromisoformat(request.date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )
        
        # Convert amount to cents
        amount_cents = int(request.amount * 100)
        
        # Create transaction using repository
        transaction = transaction_repository.insert_transaction(
            amount=amount_cents,
            description=request.description,
            category=request.category,
            type=request.type,
            date=transaction_date,
        )
        
        # Convert to response format
        return TransactionResponse(
            id=transaction.id,
            amount=transaction.amount,
            description=transaction.description,
            category=transaction.category,
            type=transaction.type,
            date=transaction.date.isoformat() if transaction.date else None,
            created_at=transaction.created_at.isoformat() if transaction.created_at else None,
            updated_at=transaction.updated_at.isoformat() if transaction.updated_at else None,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating transaction: {str(e)}")
