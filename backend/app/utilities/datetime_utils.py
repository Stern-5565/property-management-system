"""Datetime helpers.

Named datetime_utils, not datetime.py, so this module doesn't shadow the
standard library's datetime module for anything that imports it.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """A naive (no tzinfo) UTC datetime, matching what SQL Server's
    SYSUTCDATETIME() produces in a DATETIME2 column.

    Used to set UpdatedAt on UPDATE statements: the database's
    SYSUTCDATETIME() default (see database/02-create-tables.sql) only fires
    when a column is omitted from an INSERT - SQL Server does not
    automatically refresh a DEFAULT on UPDATE. The application is
    responsible for setting UpdatedAt itself whenever it modifies a row.
    """
    return datetime.now(UTC).replace(tzinfo=None)
