"""Shared audit logging, used by any service that needs to record who
changed what (starting with TenancyService - the first module where the
scope doc explicitly requires it).
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        *,
        user_id: int | None,
        action: str,
        entity_name: str,
        entity_id: int,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Stages an AuditLog row - deliberately does NOT call db.commit().

        The audit entry is added to the SAME SQLAlchemy Session as the
        business change it documents, and both are committed together by
        the caller in one transaction. See TenancyService's module
        docstring for the full explanation of why that matters: if the
        caller's commit() never happens (e.g. an earlier validation
        failed), the audit entry never reaches the database either - there
        is no way to end up with an audit log entry describing a change
        that didn't actually happen.
        """
        entry = AuditLog(
            UserId=user_id,
            Action=action,
            EntityName=entity_name,
            EntityId=entity_id,
            OldValues=self._serialize(old_values),
            NewValues=self._serialize(new_values),
            IpAddress=ip_address,
        )
        self.db.add(entry)

    @staticmethod
    def _serialize(values: dict[str, Any] | None) -> str | None:
        if values is None:
            return None
        # default=str: covers Decimal, date and datetime values, none of
        # which json.dumps can serialize on its own.
        return json.dumps(values, default=str)
