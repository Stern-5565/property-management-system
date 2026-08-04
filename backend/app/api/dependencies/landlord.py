"""FastAPI dependency that builds a request-scoped LandlordService."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.landlord_service import LandlordService


def get_landlord_service(db: Session = Depends(get_db)) -> LandlordService:
    return LandlordService(db)
