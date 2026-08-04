"""FastAPI dependency that builds a request-scoped MaintenanceService."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.maintenance_service import MaintenanceService


def get_maintenance_service(db: Session = Depends(get_db)) -> MaintenanceService:
    return MaintenanceService(db)
