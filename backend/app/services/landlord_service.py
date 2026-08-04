"""Business rules for the Landlord module.

Request flow for every Landlord endpoint:

    React request
      -> FastAPI route (app/api/routes/landlords.py) - HTTP concerns only:
         parses the request, calls one method on this service, converts the
         result to a response schema.
      -> LandlordService (this file) - business rules: not-found handling,
         duplicate-email checking, the "can this be deleted" decision, and
         owns the transaction boundary (commits/refreshes).
      -> LandlordRepository - translates a request into SQLAlchemy queries,
         nothing more.
      -> SQL Server, via the SQLAlchemy engine.
      -> the row(s) that come back are handed back up the same chain, and
         the route converts them to a Pydantic response schema at the end.

Nothing above the repository knows any SQL; nothing below the service
enforces any business rule. That split is what makes each layer testable on
its own (see tests/test_landlord_repository.py and tests/test_landlord_service.py).
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.landlord import Landlord
from app.repositories.landlord_repository import LandlordRepository
from app.schemas.landlord import LandlordCreate, LandlordUpdate
from app.utilities.datetime_utils import utc_now


class LandlordService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = LandlordRepository(db)

    def list_landlords(
        self, *, page: int, page_size: int, search: str | None, is_active: bool | None
    ) -> tuple[Sequence[Landlord], int]:
        return self.repository.list(page=page, page_size=page_size, search=search, is_active=is_active)

    def get_landlord(self, landlord_id: int) -> Landlord:
        landlord = self.repository.get_by_id(landlord_id)
        if landlord is None:
            raise AppError("LANDLORD_NOT_FOUND", f"No landlord found with id {landlord_id}.", status_code=404)
        return landlord

    def create_landlord(self, data: LandlordCreate) -> Landlord:
        self._ensure_email_not_taken(data.Email, exclude_landlord_id=None)

        landlord = Landlord(**data.model_dump(), IsActive=True)
        self.repository.add(landlord)
        self.db.commit()
        # Not strictly required (SQLAlchemy would lazily reload expired
        # attributes on next access anyway, since expire_on_commit defaults
        # to True), but refreshing explicitly here means the object handed
        # back to the route is already fully loaded - no surprise query
        # firing later, during response serialization.
        self.db.refresh(landlord)
        return landlord

    def update_landlord(self, landlord_id: int, data: LandlordUpdate) -> Landlord:
        landlord = self.get_landlord(landlord_id)
        self._ensure_email_not_taken(data.Email, exclude_landlord_id=landlord_id)

        for field, value in data.model_dump().items():
            setattr(landlord, field, value)
        landlord.UpdatedAt = utc_now()

        self.db.commit()
        self.db.refresh(landlord)
        return landlord

    def set_active_status(self, landlord_id: int, is_active: bool) -> Landlord:
        landlord = self.get_landlord(landlord_id)
        landlord.IsActive = is_active
        landlord.UpdatedAt = utc_now()

        self.db.commit()
        self.db.refresh(landlord)
        return landlord

    def deactivate_landlord(self, landlord_id: int) -> Landlord:
        """Handles DELETE /api/landlords/{id}.

        This never performs a real SQL DELETE - it deactivates instead,
        even on a landlord with zero connected rows - so the endpoint's
        behaviour is consistent and this layer never risks surfacing a raw
        foreign-key constraint error to the client. A landlord with active
        properties cannot be deactivated this way at all; those properties
        must be reassigned to another landlord or made inactive first.
        """
        landlord = self.get_landlord(landlord_id)

        if self.repository.has_active_properties(landlord_id):
            raise AppError(
                "LANDLORD_HAS_ACTIVE_PROPERTIES",
                "This landlord has active properties and cannot be deleted. "
                "Reassign or deactivate their properties first.",
                status_code=409,
            )

        landlord.IsActive = False
        landlord.UpdatedAt = utc_now()
        self.db.commit()
        self.db.refresh(landlord)
        return landlord

    def _ensure_email_not_taken(self, email: str | None, *, exclude_landlord_id: int | None) -> None:
        if not email:
            return
        existing = self.repository.get_by_email(email)
        if existing is not None and existing.LandlordId != exclude_landlord_id:
            raise AppError(
                "DUPLICATE_EMAIL",
                f"A landlord with the email '{email}' already exists.",
                status_code=409,
            )
