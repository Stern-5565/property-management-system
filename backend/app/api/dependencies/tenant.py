"""FastAPI dependency that builds a request-scoped TenantService."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.tenant_service import TenantService


def get_tenant_service(db: Session = Depends(get_db)) -> TenantService:
    return TenantService(db)
