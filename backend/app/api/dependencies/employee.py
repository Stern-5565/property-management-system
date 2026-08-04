"""FastAPI dependency that builds a request-scoped EmployeeService."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.employee_service import EmployeeService


def get_employee_service(db: Session = Depends(get_db)) -> EmployeeService:
    return EmployeeService(db)
