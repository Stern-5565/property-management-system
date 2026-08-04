"""FastAPI dependency that builds a request-scoped RentPaymentService."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.rent_payment_service import RentPaymentService


def get_rent_payment_service(db: Session = Depends(get_db)) -> RentPaymentService:
    return RentPaymentService(db)
