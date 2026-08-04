"""Confirms each SQLAlchemy model correctly maps to its table.

These tests query the real local database (seeded via
database/06-seed-demo-data.sql) rather than mocking anything - the point of
this file is specifically to prove the ORM mappings are correct against the
actual schema, so a mock would defeat the purpose.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models import (
    AuditLog,
    Employee,
    Landlord,
    MaintenanceNote,
    MaintenanceRequest,
    Property,
    RentPayment,
    Role,
    Tenancy,
    Tenant,
    User,
)


def get_session() -> Session:
    return SessionLocal()


# ---------- Batch 1: Landlord + Property ----------


def test_can_query_landlords() -> None:
    with get_session() as db:
        landlords = db.execute(select(Landlord)).scalars().all()

        assert len(landlords) == 5
        assert any(l.CompanyName == "Green Oak Properties Ltd" for l in landlords)


def test_can_query_properties() -> None:
    with get_session() as db:
        properties = db.execute(select(Property)).scalars().all()

        assert len(properties) == 10
        pm0001 = next(p for p in properties if p.PropertyReference == "PM-0001")
        assert pm0001.MonthlyRent == Decimal("1200.00")
        assert pm0001.PropertyStatus == "Occupied"


def test_property_landlord_relationship_matches_foreign_key() -> None:
    with get_session() as db:
        property_ = db.execute(
            select(Property).where(Property.PropertyReference == "PM-0003")
        ).scalar_one()

        assert property_.Landlord.CompanyName == "Green Oak Properties Ltd"


def test_landlord_properties_relationship_returns_owned_properties() -> None:
    with get_session() as db:
        landlord = db.execute(
            select(Landlord).where(Landlord.CompanyName == "Henderson Estates Ltd")
        ).scalar_one()

        property_references = {p.PropertyReference for p in landlord.Properties}
        assert property_references == {"PM-0008", "PM-0009"}


# ---------- Batch 2: Tenant + Tenancy ----------


def test_can_query_tenants() -> None:
    with get_session() as db:
        tenants = db.execute(select(Tenant)).scalars().all()

        assert len(tenants) == 12
        assert any(t.Email == "john.okafor@example.com" for t in tenants)


def test_can_query_tenancies() -> None:
    with get_session() as db:
        tenancies = db.execute(select(Tenancy)).scalars().all()

        assert len(tenancies) == 12
        agr_1001 = next(t for t in tenancies if t.AgreementReference == "AGR-1001")
        assert agr_1001.TenancyStatus == "Ending Soon"
        assert agr_1001.MonthlyRent == Decimal("1200.00")


def test_tenancy_property_and_tenant_relationships() -> None:
    with get_session() as db:
        tenancy = db.execute(
            select(Tenancy).where(Tenancy.AgreementReference == "AGR-1002")
        ).scalar_one()

        assert tenancy.Property.PropertyReference == "PM-0003"
        assert tenancy.Tenant.Email == "laura.bennett@example.com"


def test_property_tenancies_relationship_includes_past_and_present() -> None:
    with get_session() as db:
        # PM-0004 has one Ended tenancy (AGR-1003) and one Active, open-
        # ended tenancy (AGR-1004) - confirms the relationship returns
        # tenancy history, not just the current one.
        property_ = db.execute(
            select(Property).where(Property.PropertyReference == "PM-0004")
        ).scalar_one()

        agreement_references = {t.AgreementReference for t in property_.Tenancies}
        assert agreement_references == {"AGR-1003", "AGR-1004"}


# ---------- Batch 3: Employee + RentPayment ----------


def test_can_query_employees() -> None:
    with get_session() as db:
        employees = db.execute(select(Employee)).scalars().all()

        assert len(employees) == 5
        assert any(e.Email == "daniel.osei@propertymanager.example" for e in employees)


def test_can_query_rent_payments() -> None:
    with get_session() as db:
        payments = db.execute(select(RentPayment)).scalars().all()

        assert len(payments) == 30
        overdue = next(p for p in payments if p.PaymentReference == "PAY-00004")
        assert overdue.PaymentStatus == "Overdue"
        assert overdue.AmountDue == Decimal("1200.00")
        assert overdue.AmountPaid == Decimal("0.00")


def test_rent_payment_tenancy_and_employee_relationships() -> None:
    with get_session() as db:
        payment = db.execute(
            select(RentPayment).where(RentPayment.PaymentReference == "PAY-00001")
        ).scalar_one()

        assert payment.Tenancy.AgreementReference == "AGR-1001"
        assert payment.CreatedByEmployee.Email == "james.carter@propertymanager.example"


def test_tenancy_rent_payments_relationship_returns_full_history() -> None:
    with get_session() as db:
        tenancy = db.execute(
            select(Tenancy).where(Tenancy.AgreementReference == "AGR-1001")
        ).scalar_one()

        payment_references = {p.PaymentReference for p in tenancy.RentPayments}
        assert payment_references == {"PAY-00001", "PAY-00002", "PAY-00003", "PAY-00004"}


# ---------- Batch 4: MaintenanceRequest + MaintenanceNote ----------


def test_can_query_maintenance_requests() -> None:
    with get_session() as db:
        requests = db.execute(select(MaintenanceRequest)).scalars().all()

        assert len(requests) == 20
        emergency_unassigned = next(r for r in requests if r.RequestReference == "MR-0020")
        assert emergency_unassigned.Priority == "Emergency"
        assert emergency_unassigned.AssignedEmployeeId is None


def test_can_query_maintenance_notes() -> None:
    with get_session() as db:
        notes = db.execute(select(MaintenanceNote)).scalars().all()

        assert len(notes) == 8


def test_maintenance_request_relationships() -> None:
    with get_session() as db:
        request = db.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.RequestReference == "MR-0001")
        ).scalar_one()

        assert request.Property.PropertyReference == "PM-0001"
        assert request.Tenancy.AgreementReference == "AGR-1001"
        assert request.Tenant.Email == "john.okafor@example.com"
        assert request.AssignedEmployee.Email == "daniel.osei@propertymanager.example"


def test_maintenance_request_notes_relationship() -> None:
    with get_session() as db:
        request = db.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.RequestReference == "MR-0007")
        ).scalar_one()

        note_texts = [n.NoteText for n in request.MaintenanceNotes]
        assert len(note_texts) == 2
        assert all(n.Employee.Email == "daniel.osei@propertymanager.example" for n in request.MaintenanceNotes)


def test_property_and_employee_maintenance_relationships() -> None:
    with get_session() as db:
        property_ = db.execute(
            select(Property).where(Property.PropertyReference == "PM-0001")
        ).scalar_one()
        request_references = {r.RequestReference for r in property_.MaintenanceRequests}
        assert request_references == {"MR-0001", "MR-0002", "MR-0018"}

        employee = db.execute(
            select(Employee).where(Employee.Email == "daniel.osei@propertymanager.example")
        ).scalar_one()
        assert len(employee.AssignedMaintenanceRequests) > 0


# ---------- Batch 5: Role, User, UserRoles, AuditLog ----------


def test_can_query_roles() -> None:
    with get_session() as db:
        roles = db.execute(select(Role)).scalars().all()

        role_names = {r.RoleName for r in roles}
        assert role_names == {"Administrator", "PropertyManager", "MaintenanceEmployee", "ReadOnly"}


def test_can_query_users() -> None:
    with get_session() as db:
        users = db.execute(select(User)).scalars().all()

        assert len(users) == 5
        assert any(u.Username == "sarah.mitchell" for u in users)


def test_user_employee_one_to_one_relationship() -> None:
    with get_session() as db:
        user = db.execute(select(User).where(User.Username == "james.carter")).scalar_one()

        assert user.Employee.Email == "james.carter@propertymanager.example"
        assert user.Employee.User is user


def test_user_roles_many_to_many_relationship() -> None:
    with get_session() as db:
        # Two PropertyManagers (James Carter, Priya Patel) share the same
        # role - a good check that the many-to-many join works both ways.
        pm_role = db.execute(select(Role).where(Role.RoleName == "PropertyManager")).scalar_one()
        usernames = {u.Username for u in pm_role.Users}
        assert usernames == {"james.carter", "priya.patel"}

        user = db.execute(select(User).where(User.Username == "sarah.mitchell")).scalar_one()
        assert [r.RoleName for r in user.Roles] == ["Administrator"]


def test_can_query_audit_logs() -> None:
    with get_session() as db:
        # No audit log rows are seeded by database/06-seed-demo-data.sql,
        # but real ones now exist from AuditService (used by TenancyService)
        # - this just confirms the table maps and is queryable without
        # error, not any particular count (test suite runs accumulate rows
        # here over time, which is expected and harmless: AuditLogs.EntityId
        # deliberately has no FK, since one audit table covers every entity
        # type, so nothing else depends on these rows being cleaned up).
        audit_logs = db.execute(select(AuditLog)).scalars().all()
        assert isinstance(audit_logs, list)
