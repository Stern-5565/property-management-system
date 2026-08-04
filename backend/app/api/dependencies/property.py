"""FastAPI dependency that builds a request-scoped PropertyService."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.property_service import PropertyService


def get_property_service(db: Session = Depends(get_db)) -> PropertyService:
    return PropertyService(db)
