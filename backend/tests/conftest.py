"""Shared pytest fixtures available to every test file automatically."""

import pytest
from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.user import User


@pytest.fixture
def admin_user_id() -> int:
    """UserId of the seeded Administrator demo user - used wherever a test
    needs a valid user_id for audit logging but isn't testing auth itself."""
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.Email == "sarah.mitchell@propertymanager.example")).scalar_one()
        return user.UserId
    finally:
        db.close()
