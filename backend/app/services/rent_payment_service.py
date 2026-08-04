"""Business rules for the RentPayment module.

Automatic payment status - why it's computed live, not just stored:

PaymentStatus (Pending/Partially Paid/Paid/Overdue/Cancelled) depends on
AmountDue, AmountPaid, DueDate, and today's date. The first three only
change when someone writes to the row (create, record-payment, cancel),
but "today's date" moves on its own - a Pending payment silently becomes
Overdue the moment its due date passes, with nobody having touched the
row at all. There is no scheduled sweep job in this MVP to catch that
transition (same category of deferred work as Tenancy's Upcoming -> Active
sweep - see documentation/progress-log.md).

Rather than let the API report a stale "Pending" for a payment that is,
today, actually overdue, calculate_payment_status() is called fresh every
time a response is built (see RentPaymentResponse.from_payment), not just
when a write happens. The stored PaymentStatus column is still kept
reasonably fresh (updated on every actual write, and used directly by
database/07-report-queries.sql and by the `payment_status` list filter
below), but the API's own responses are always correct regardless of how
long a row has sat untouched. This mirrors exactly how
database/07-report-queries.sql's Report 2 (Overdue rent) recalculates
"overdue" live rather than trusting the stored column - see that report's
comment block for the original reasoning.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.rent_payment import RentPayment
from app.repositories.rent_payment_repository import RentPaymentRepository
from app.repositories.tenancy_repository import TenancyRepository
from app.schemas.rent_payment import RentPaymentCreate, RentPaymentUpdate
from app.services.audit_service import AuditService
from app.utilities.datetime_utils import utc_now


def calculate_payment_status(*, amount_due, amount_paid, due_date: date, current_status: str) -> str:
    """Pure function, not a method: no I/O, easy to unit test on its own.

    Cancelled is terminal - once cancelled, a payment stays Cancelled
    regardless of what the amounts say, which is why current_status must
    be passed in rather than deriving everything from amounts/date alone.
    """
    if current_status == "Cancelled":
        return "Cancelled"
    if amount_paid >= amount_due:
        return "Paid"
    if amount_paid > 0:
        return "Partially Paid"
    if due_date < date.today():
        return "Overdue"
    return "Pending"


class RentPaymentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = RentPaymentRepository(db)
        self.tenancy_repository = TenancyRepository(db)
        self.audit_service = AuditService(db)

    def list_payments(
        self,
        *,
        page: int,
        page_size: int,
        tenancy_id: int | None,
        property_id: int | None,
        tenant_id: int | None,
        payment_status: str | None,
        due_date_from: date | None,
        due_date_to: date | None,
    ) -> tuple[Sequence[RentPayment], int]:
        return self.repository.list(
            page=page,
            page_size=page_size,
            tenancy_id=tenancy_id,
            property_id=property_id,
            tenant_id=tenant_id,
            payment_status=payment_status,
            due_date_from=due_date_from,
            due_date_to=due_date_to,
        )

    def list_overdue(self) -> Sequence[RentPayment]:
        return self.repository.list_overdue()

    def list_due_this_month(self) -> Sequence[RentPayment]:
        return self.repository.list_due_this_month()

    def get_payment(self, payment_id: int) -> RentPayment:
        payment = self.repository.get_by_id(payment_id)
        if payment is None:
            raise AppError("PAYMENT_NOT_FOUND", f"No rent payment found with id {payment_id}.", status_code=404)
        return payment

    def get_live_status(self, payment: RentPayment) -> str:
        return calculate_payment_status(
            amount_due=payment.AmountDue,
            amount_paid=payment.AmountPaid,
            due_date=payment.DueDate,
            current_status=payment.PaymentStatus,
        )

    def create_payment(self, data: RentPaymentCreate, *, created_by_employee_id: int | None, user_id: int) -> RentPayment:
        self._ensure_tenancy_exists(data.TenancyId)
        self._ensure_reference_not_taken(data.PaymentReference, exclude_payment_id=None)

        status = calculate_payment_status(
            amount_due=data.AmountDue, amount_paid=0, due_date=data.DueDate, current_status="Pending"
        )
        payment = RentPayment(
            **data.model_dump(),
            AmountPaid=0,
            PaymentStatus=status,
            CreatedByEmployeeId=created_by_employee_id,
        )
        self.repository.add(payment)

        self.audit_service.log(
            user_id=user_id,
            action="CREATE",
            entity_name="RentPayment",
            entity_id=payment.RentPaymentId,
            new_values={"TenancyId": payment.TenancyId, "DueDate": payment.DueDate, "AmountDue": payment.AmountDue},
        )

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update_payment(self, payment_id: int, data: RentPaymentUpdate, *, user_id: int) -> RentPayment:
        payment = self.get_payment(payment_id)
        if payment.PaymentStatus == "Cancelled":
            raise AppError("PAYMENT_ALREADY_CANCELLED", "This payment has been cancelled and cannot be edited.", status_code=409)
        if payment.AmountPaid > 0:
            raise AppError(
                "PAYMENT_NOT_EDITABLE",
                "This payment already has money recorded against it and can no longer be edited directly. "
                "Cancel it and create a new obligation instead.",
                status_code=409,
            )

        self._ensure_tenancy_exists(data.TenancyId)
        self._ensure_reference_not_taken(data.PaymentReference, exclude_payment_id=payment_id)

        old_values = {"TenancyId": payment.TenancyId, "DueDate": payment.DueDate, "AmountDue": payment.AmountDue}
        for field, value in data.model_dump().items():
            setattr(payment, field, value)
        payment.PaymentStatus = calculate_payment_status(
            amount_due=payment.AmountDue, amount_paid=payment.AmountPaid, due_date=payment.DueDate, current_status="Pending"
        )
        payment.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="UPDATE",
            entity_name="RentPayment",
            entity_id=payment.RentPaymentId,
            old_values=old_values,
            new_values={"TenancyId": payment.TenancyId, "DueDate": payment.DueDate, "AmountDue": payment.AmountDue},
        )

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def record_payment(
        self, payment_id: int, *, amount_paid, payment_date: date | None, payment_method: str, notes: str | None, user_id: int
    ) -> RentPayment:
        payment = self.get_payment(payment_id)
        if payment.PaymentStatus == "Cancelled":
            raise AppError(
                "PAYMENT_ALREADY_CANCELLED", "This payment has been cancelled and cannot accept further payment.", status_code=409
            )

        old_amount_paid = payment.AmountPaid
        payment.AmountPaid = payment.AmountPaid + amount_paid
        payment.PaymentDate = payment_date or date.today()
        payment.PaymentMethod = payment_method
        if notes:
            payment.Notes = notes
        payment.PaymentStatus = calculate_payment_status(
            amount_due=payment.AmountDue, amount_paid=payment.AmountPaid, due_date=payment.DueDate, current_status="Pending"
        )
        payment.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="RECORD_PAYMENT",
            entity_name="RentPayment",
            entity_id=payment.RentPaymentId,
            old_values={"AmountPaid": old_amount_paid},
            new_values={"AmountPaid": payment.AmountPaid, "PaymentStatus": payment.PaymentStatus},
        )

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def cancel_payment(self, payment_id: int, *, notes: str | None, user_id: int) -> RentPayment:
        payment = self.get_payment(payment_id)
        if payment.PaymentStatus == "Cancelled":
            raise AppError("PAYMENT_ALREADY_CANCELLED", "This payment has already been cancelled.", status_code=409)

        old_status = payment.PaymentStatus
        payment.PaymentStatus = "Cancelled"
        if notes:
            payment.Notes = notes
        payment.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="CANCEL",
            entity_name="RentPayment",
            entity_id=payment.RentPaymentId,
            old_values={"PaymentStatus": old_status},
            new_values={"PaymentStatus": "Cancelled"},
        )

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def _ensure_tenancy_exists(self, tenancy_id: int) -> None:
        if self.tenancy_repository.get_by_id(tenancy_id) is None:
            raise AppError("TENANCY_NOT_FOUND", f"No tenancy found with id {tenancy_id}.", status_code=404)

    def _ensure_reference_not_taken(self, reference: str, *, exclude_payment_id: int | None) -> None:
        existing = self.repository.get_by_reference(reference)
        if existing is not None and existing.RentPaymentId != exclude_payment_id:
            raise AppError(
                "DUPLICATE_PAYMENT_REFERENCE",
                f"A rent payment with reference '{reference}' already exists.",
                status_code=409,
            )
