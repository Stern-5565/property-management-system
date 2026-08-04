"""Health-check endpoint - confirms the API is running and the database is reachable."""

import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=None)
def health_check(db: Session = Depends(get_db)) -> dict | JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unavailable"},
        )
    return {"status": "ok", "database": "connected"}
