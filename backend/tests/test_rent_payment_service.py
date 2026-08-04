"""Tests for RentPaymentService - business rules.

Unlike Tenancy, a rent payment doesn't cascade into any other entity's
state, so tests here attach throwaway payment rows directly to an
EXISTING seeded tenancy (AGR-1005, chosen because no other test touches
it) rather than needing a whole property/tenant/tenancy fixture chain -
just delete the payment row afterward and the seeded tenancy is
untouched.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.database.session import SessionLocal
from app.models.tenancy import Tenancy
from app.schemas.rent_payment import RentPaymentCreate, RentPaymentUpdate
from app.services.rent_payment_service import RentPaymentService, calculate_payment_status

TODAY = date.today()


# ---------- calculate_payment_status: pure function, no DB needed ----------


def test_status_is_pending_when_nothing_paid_and_not_yet_due() -> None:
    status = calculate_payment_status(
        amount_due=1000, amount_paid=0, due_date=TODAY + timedelta(days=5), current_status="Pending"
    )
    assert status == "Pending"


def test_status_is_overdue_when_nothing_paid_and_due_date_passed() -> None:
    status = calculate_payment_status(
        amount_due=1000, amount_paid=0, due_date=TODAY - timedelta(days=1), current_status="Pending"
    )
    assert status == "Overdue"


def test_status_is_partially_paid_when_some_but_not_all_paid() -> None:
    status = calculate_payment_status(amount_due=1000, amount_paid=400, due_date=TODAY, current_status="Pending")
    assert status == "Partially Paid"


def test_status_is_paid_when_amount_paid_meets_or_exceeds_due() -> None:
    assert calculate_payment_status(amount_due=1000, amount_paid=1000, due_date=TODAY, current_status="Pending") == "Paid"
    # Overpayment still just reads as Paid, not some special state.
    assert calculate_payment_status(amount_due=1000, amount_paid=1200, due_date=TODAY, current_status="Pending") == "Paid"


def test_status_stays_cancelled_regardless_of_amounts() -> None:
    """Cancelled is terminal - even a fully-paid-looking cancelled record
    stays Cancelled, never flips back to Paid."""
    status = calculate_payment_status(amount_due=1000, amount_paid=1000, due_date=TODAY, current_status="Cancelled")
    assert status == "Cancelled"


# ---------- Service tests against a throwaway payment on a real tenancy ----------


@pytest.fixture
def service():
    db = SessionLocal()
    try:
        yield RentPaymentService(db)
    finally:
        db.close()


@pytest.fixture
def agr_1005_tenancy_id(service: RentPaymentService) -> int:
    tenancy = service.db.execute(select(Tenancy).where(Tenancy.AgreementReference == "AGR-1005")).scalar_one()
    return tenancy.TenancyId


def _payload(tenancy_id: int, **overrides) -> RentPaymentCreate:
    defaults = {
        "TenancyId": tenancy_id,
        "PaymentReference": "PAY-SVC-TEST-001",
        "DueDate": TODAY + timedelta(days=10),
        "AmountDue": "1000.00",
    }
    defaults.update(overrides)
    return RentPaymentCreate(**defaults)


def _delete(service: RentPaymentService, payment) -> None:
    service.db.delete(payment)
    service.db.commit()


def test_create_payment_starts_pending_when_due_date_in_future(
    service: RentPaymentService, agr_1005_tenancy_id: int, admin_user_id: int
) -> None:
    payment = service.create_payment(_payload(agr_1005_tenancy_id), created_by_employee_id=None, user_id=admin_user_id)
    try:
        assert payment.PaymentStatus == "Pending"
        assert payment.AmountPaid == 0
    finally:
        _delete(service, payment)


def test_create_payment_starts_overdue_when_due_date_already_passed(
    service: RentPaymentService, agr_1005_tenancy_id: int, admin_user_id: int
) -> None:
    payment = service.create_payment(
        _payload(agr_1005_tenancy_id, DueDate=TODAY - timedelta(days=3)), created_by_employee_id=None, user_id=admin_user_id
    )
    try:
        assert payment.PaymentStatus == "Overdue"
    finally:
        _delete(service, payment)


def test_create_payment_rejects_unknown_tenancy(service: RentPaymentService, admin_user_id: int) -> None:
    with pytest.raises(AppError) as exc_info:
        service.create_payment(_payload(999_999), created_by_employee_id=None, user_id=admin_user_id)
    assert exc_info.value.code == "TENANCY_NOT_FOUND"


def test_create_payment_rejects_duplicate_reference(
    service: RentPaymentService, agr_1005_tenancy_id: int, admin_user_id: int
) -> None:
    payment = service.create_payment(_payload(agr_1005_tenancy_id), created_by_employee_id=None, user_id=admin_user_id)
    try:
        with pytest.raises(AppError) as exc_info:
            service.create_payment(_payload(agr_1005_tenancy_id), created_by_employee_id=None, user_id=admin_user_id)
        assert exc_info.value.code == "DUPLICATE_PAYMENT_REFERENCE"
    finally:
        _delete(service, payment)


def test_get_payment_raises_not_found_for_missing_id(service: RentPaymentService) -> None:
    with pytest.raises(AppError) as exc_info:
        service.get_payment(999_999)
    assert exc_info.value.code == "PAYMENT_NOT_FOUND"


def test_record_partial_then_full_payment_accumulates(
    service: RentPaymentService, agr_1005_tenancy_id: int, admin_user_id: int
) -> None:
    payment = service.create_payment(_payload(agr_1005_tenancy_id), created_by_employee_id=None, user_id=admin_user_id)
    try:
        after_first = service.record_payment(
            payment.RentPaymentId, amount_paid=400, payment_date=None, payment_method="Bank Transfer", notes=None,
            user_id=admin_user_id,
        )
        assert after_first.AmountPaid == 400
        assert after_first.PaymentStatus == "Partially Paid"

        after_second = service.record_payment(
            payment.RentPaymentId, amount_paid=600, payment_date=None, payment_method="Bank Transfer", notes=None,
            user_id=admin_user_id,
        )
        assert after_second.AmountPaid == 1000
        assert after_second.PaymentStatus == "Paid"
    finally:
        _delete(service, payment)


def test_record_payment_rejects_already_cancelled_payment(
    service: RentPaymentService, agr_1005_tenancy_id: int, admin_user_id: int
) -> None:
    payment = service.create_payment(_payload(agr_1005_tenancy_id), created_by_employee_id=None, user_id=admin_user_id)
    try:
        service.cancel_payment(payment.RentPaymentId, notes=None, user_id=admin_user_id)

        with pytest.raises(AppError) as exc_info:
            service.record_payment(
                payment.RentPaymentId, amount_paid=100, payment_date=None, payment_method="Cash", notes=None,
                user_id=admin_user_id,
            )
        assert exc_info.value.code == "PAYMENT_ALREADY_CANCELLED"
    finally:
        _delete(service, payment)


def test_cancel_payment_rejects_already_cancelled_payment(
    service: RentPaymentService, agr_1005_tenancy_id: int, admin_user_id: int
) -> None:
    payment = service.create_payment(_payload(agr_1005_tenancy_id), created_by_employee_id=None, user_id=admin_user_id)
    try:
        service.cancel_payment(payment.RentPaymentId, notes=None, user_id=admin_user_id)

        with pytest.raises(AppError) as exc_info:
            service.cancel_payment(payment.RentPaymentId, notes=None, user_id=admin_user_id)
        assert exc_info.value.code == "PAYMENT_ALREADY_CANCELLED"
    finally:
        _delete(service, payment)


def test_update_payment_succeeds_while_amount_paid_is_zero(
    service: RentPaymentService, agr_1005_tenancy_id: int, admin_user_id: int
) -> None:
    payment = service.create_payment(_payload(agr_1005_tenancy_id), created_by_employee_id=None, user_id=admin_user_id)
    try:
        updated = service.update_payment(
            payment.RentPaymentId,
            RentPaymentUpdate(**{**_payload(agr_1005_tenancy_id).model_dump(), "AmountDue": "1200.00"}),
            user_id=admin_user_id,
        )
        assert updated.AmountDue == 1200
    finally:
        _delete(service, payment)


def test_update_payment_is_rejected_once_money_has_been_recorded(
    service: RentPaymentService, agr_1005_tenancy_id: int, admin_user_id: int
) -> None:
    payment = service.create_payment(_payload(agr_1005_tenancy_id), created_by_employee_id=None, user_id=admin_user_id)
    try:
        service.record_payment(
            payment.RentPaymentId, amount_paid=100, payment_date=None, payment_method="Cash", notes=None,
            user_id=admin_user_id,
        )

        with pytest.raises(AppError) as exc_info:
            service.update_payment(
                payment.RentPaymentId,
                RentPaymentUpdate(**_payload(agr_1005_tenancy_id).model_dump()),
                user_id=admin_user_id,
            )
        assert exc_info.value.code == "PAYMENT_NOT_EDITABLE"
    finally:
        _delete(service, payment)


def test_get_live_status_reflects_current_date_even_without_a_write(
    service: RentPaymentService, agr_1005_tenancy_id: int, admin_user_id: int
) -> None:
    """The core reason calculate_payment_status is called fresh for every
    response: a payment created as Pending, due yesterday by the time we
    ask, must report Overdue even though nothing has written to the row
    since it was created."""
    payment = service.create_payment(
        _payload(agr_1005_tenancy_id, DueDate=TODAY + timedelta(days=1)), created_by_employee_id=None, user_id=admin_user_id
    )
    try:
        assert payment.PaymentStatus == "Pending"

        # Simulate a day passing without any write to the row.
        payment.DueDate = TODAY - timedelta(days=1)

        assert service.get_live_status(payment) == "Overdue"
    finally:
        _delete(service, payment)
