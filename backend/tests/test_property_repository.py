"""Tests for PropertyRepository - direct database access, no business rules.

Read-only against the seeded demo data (10 properties across 5 landlords) -
no cleanup needed here.
"""

from app.database.session import SessionLocal
from app.repositories.property_repository import PropertyRepository


def get_repo() -> tuple:
    db = SessionLocal()
    return db, PropertyRepository(db)


def test_get_by_id_returns_none_for_missing_property() -> None:
    db, repo = get_repo()
    try:
        assert repo.get_by_id(999_999) is None
    finally:
        db.close()


def test_get_by_reference_finds_property() -> None:
    db, repo = get_repo()
    try:
        property_ = repo.get_by_reference("PM-0001")
        assert property_ is not None
        assert property_.City == "London"
    finally:
        db.close()


def test_list_returns_all_seeded_properties() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(
            page=1, page_size=20, search=None, landlord_id=None, city=None,
            property_type=None, property_status=None, is_active=None,
            sort_by="PropertyReference", sort_dir="asc",
        )
        assert total == 10
        assert len(items) == 10
        assert items[0].PropertyReference == "PM-0001"  # default sort ascending
    finally:
        db.close()


def test_list_sort_by_monthly_rent_descending() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(
            page=1, page_size=20, search=None, landlord_id=None, city=None,
            property_type=None, property_status=None, is_active=None,
            sort_by="MonthlyRent", sort_dir="desc",
        )
        assert total == 10
        rents = [item.MonthlyRent for item in items]
        assert rents == sorted(rents, reverse=True)
    finally:
        db.close()


def test_list_filters_by_city() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(
            page=1, page_size=20, search=None, landlord_id=None, city="Leeds",
            property_type=None, property_status=None, is_active=None,
            sort_by="PropertyReference", sort_dir="asc",
        )
        # PM-0008, PM-0009, PM-0010 are in Leeds
        assert total == 3
    finally:
        db.close()


def test_list_filters_by_property_status() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(
            page=1, page_size=20, search=None, landlord_id=None, city=None,
            property_type=None, property_status="Vacant", is_active=None,
            sort_by="PropertyReference", sort_dir="asc",
        )
        assert total == 2  # PM-0002, PM-0007
    finally:
        db.close()


def test_list_filters_by_landlord_id() -> None:
    db, repo = get_repo()
    try:
        green_oak_property = repo.get_by_reference("PM-0003")
        items, total = repo.list(
            page=1, page_size=20, search=None, landlord_id=green_oak_property.LandlordId, city=None,
            property_type=None, property_status=None, is_active=None,
            sort_by="PropertyReference", sort_dir="asc",
        )
        # Green Oak Properties Ltd owns PM-0003, PM-0004, PM-0005
        assert total == 3
    finally:
        db.close()


def test_list_search_matches_property_reference() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(
            page=1, page_size=20, search="PM-0006", landlord_id=None, city=None,
            property_type=None, property_status=None, is_active=None,
            sort_by="PropertyReference", sort_dir="asc",
        )
        assert total == 1
        assert items[0].PropertyReference == "PM-0006"
    finally:
        db.close()


def test_list_search_matches_address() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(
            page=1, page_size=20, search="Riverside Court", landlord_id=None, city=None,
            property_type=None, property_status=None, is_active=None,
            sort_by="PropertyReference", sort_dir="asc",
        )
        assert total == 2  # PM-0006 and PM-0007 both on Riverside Court
    finally:
        db.close()


def test_has_active_tenancies_true_for_property_with_active_tenancy() -> None:
    db, repo = get_repo()
    try:
        pm_0003 = repo.get_by_reference("PM-0003")  # AGR-1002, Active
        assert repo.has_active_tenancies(pm_0003.PropertyId) is True
    finally:
        db.close()


def test_has_active_tenancies_false_for_property_with_only_ended_tenancy() -> None:
    db, repo = get_repo()
    try:
        pm_0002 = repo.get_by_reference("PM-0002")  # AGR-1008, Ended
        assert repo.has_active_tenancies(pm_0002.PropertyId) is False
    finally:
        db.close()
