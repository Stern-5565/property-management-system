"""Pydantic schemas for the Reports module (Prompt 25).

One generic response shape (`ReportResponse`) is shared by all 10 MVP
reports rather than 10 separate strongly-typed row schemas - each
report's row shape differs too much (different columns, different join
targets) for a per-report Pydantic model to earn its keep, and the whole
point of Prompt 25's "reusable reporting pattern" instruction is that the
frontend renders any report from its own self-described `Columns` list,
never a hardcoded table shape per report. `Rows` stays a list of plain
dicts keyed by each column's `key` - the same "generic tabular data"
contract the frontend's own `utilities/csvExport.js` already expects.

No Create/Update schemas here - like Dashboard, this module is entirely
read-only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

# The 10 MVP reports (documentation/project-scope.md, "Ten MVP reports").
# Used as the {report_key} path parameter's type, so FastAPI 404s on an
# unknown key before it ever reaches ReportService.
ReportKey = Literal[
    "rent-due-this-month",
    "overdue-rent",
    "monthly-rent-collected",
    "rent-by-landlord",
    "occupancy",
    "vacant-properties",
    "tenancies-ending-soon",
    "maintenance-by-status",
    "maintenance-costs-by-property",
    "property-income",
]

# Tells the frontend how to format a column's cells (and how to align them
# for print) without either side hardcoding per-report knowledge of the
# other. "currency" and "percent" are distinct from "decimal"/"integer" so
# the frontend can add the £/% affix itself rather than the backend baking
# display formatting into the data.
ReportColumnType = Literal["string", "integer", "decimal", "currency", "date", "percent"]


class ReportColumn(BaseModel):
    key: str
    header: str
    type: ReportColumnType = "string"


class ReportResponse(BaseModel):
    ReportKey: str
    Title: str
    Description: str
    Columns: list[ReportColumn]
    Rows: list[dict[str, Any]]
    # Only the columns where summing makes sense appear here (e.g. an
    # AmountOutstanding total, never a TenantName total) - None entirely
    # for reports with no meaningful total (e.g. Tenancies Ending Soon).
    Totals: dict[str, Any] | None = None
    GeneratedAt: datetime
