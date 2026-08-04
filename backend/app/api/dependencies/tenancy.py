"""FastAPI dependency that builds a request-scoped TenancyService."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.tenancy_service import TenancyService


def get_tenancy_service(db: Session = Depends(get_db)) -> TenancyService:
    return TenancyService(db)
