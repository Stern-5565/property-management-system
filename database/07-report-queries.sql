-- ============================================================
-- 07-report-queries.sql
-- The 10 MVP PropertyManager business reports.
--
-- Each report below is self-contained: run its DECLARE block (if it
-- has one) followed by its SELECT as a single batch. They are safe
-- to run in any order and do not modify data.
--
-- Run this after 06-seed-demo-data.sql to see realistic results,
-- connected to PropertyManagerDb.
-- ============================================================

USE PropertyManagerDb;
GO


-- ============================================================
-- Report 1: Rent due this month
-- Business question: how much rent is expected to be collected in
-- the current calendar month, regardless of whether it has been
-- paid yet?
--
-- Joins: RentPayments -> Tenancies (which lease this payment belongs
-- to) -> Properties and Tenants (who and where).
-- Filtering: excludes Cancelled payments (they are not real
-- obligations any more). Cancelled payments are never counted in any
-- report in this file, for the same reason.
-- Note on the date filter: it compares DueDate to a date RANGE
-- (@MonthStart / @MonthEnd) rather than wrapping DueDate in
-- YEAR()/MONTH() functions. Wrapping an indexed column in a function
-- stops SQL Server from using an index seek on IX_RentPayments_DueDate
-- (a "non-sargable" predicate) - the range form can still use it.
-- ============================================================

DECLARE @MonthStart DATE = DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1);
DECLARE @MonthEnd   DATE = DATEADD(MONTH, 1, @MonthStart);

SELECT
    rp.RentPaymentId,
    p.PropertyReference,
    CONCAT(p.AddressLine1, N', ', p.City) AS PropertyAddress,
    CONCAT(tn.FirstName, N' ', tn.LastName) AS TenantName,
    rp.DueDate,
    rp.AmountDue,
    rp.AmountPaid,
    rp.AmountDue - rp.AmountPaid AS AmountOutstanding,
    rp.PaymentStatus
FROM RentPayments rp
JOIN Tenancies ten ON ten.TenancyId = rp.TenancyId
JOIN Properties p ON p.PropertyId = ten.PropertyId
JOIN Tenants tn ON tn.TenantId = ten.TenantId
WHERE rp.PaymentStatus <> N'Cancelled'
  AND rp.DueDate >= @MonthStart
  AND rp.DueDate < @MonthEnd
ORDER BY rp.DueDate, p.PropertyReference;
GO


-- ============================================================
-- Report 2: Overdue rent
-- Business question: which rent payments are overdue right now?
--
-- Joins: RentPayments -> Tenancies -> Properties -> Landlords (so a
-- property manager can see who to escalate to) and Tenants.
-- Important design note: this report does NOT trust the stored
-- PaymentStatus = 'Overdue' value alone - it recalculates "overdue"
-- live from DueDate and AmountPaid vs AmountDue. PaymentStatus is an
-- application-maintained column (see database-design.md); if the
-- service layer's Pending -> Overdue sweep hasn't run yet today, the
-- stored value could be stale. Recalculating live means this report
-- is always correct even if that housekeeping job is behind.
-- NULL handling: COALESCE picks CompanyName when set, otherwise
-- builds "FirstName LastName" - landlords can be either.
-- ============================================================

SELECT
    rp.RentPaymentId,
    p.PropertyReference,
    CONCAT(tn.FirstName, N' ', tn.LastName) AS TenantName,
    COALESCE(l.CompanyName, CONCAT(l.FirstName, N' ', l.LastName)) AS LandlordName,
    rp.DueDate,
    DATEDIFF(DAY, rp.DueDate, CAST(GETDATE() AS DATE)) AS DaysOverdue,
    rp.AmountDue,
    rp.AmountPaid,
    rp.AmountDue - rp.AmountPaid AS AmountOutstanding
FROM RentPayments rp
JOIN Tenancies ten ON ten.TenancyId = rp.TenancyId
JOIN Properties p ON p.PropertyId = ten.PropertyId
JOIN Tenants tn ON tn.TenantId = ten.TenantId
JOIN Landlords l ON l.LandlordId = p.LandlordId
WHERE rp.PaymentStatus <> N'Cancelled'
  AND rp.DueDate < CAST(GETDATE() AS DATE)
  AND rp.AmountPaid < rp.AmountDue
ORDER BY DaysOverdue DESC;
GO


-- ============================================================
-- Report 3: Monthly rent collected
-- Business question: how much cash has actually been collected,
-- month by month? (Feeds the dashboard's "rent collected by month"
-- chart.)
--
-- Grouping: by the month money actually arrived (PaymentDate), NOT
-- the month it was due (DueDate) - a payment due in July but paid in
-- August should count as August's collected total.
-- Filtering: only Paid/Partially Paid rows have a real PaymentDate;
-- Pending/Overdue/Cancelled contribute nothing collected.
-- NULL handling: PaymentDate IS NOT NULL is required because GROUP BY
-- would otherwise fold every NULL PaymentDate into one misleading
-- "unknown month" group.
-- ============================================================

SELECT
    YEAR(rp.PaymentDate) AS PaymentYear,
    MONTH(rp.PaymentDate) AS PaymentMonth,
    DATENAME(MONTH, rp.PaymentDate) + N' ' + CAST(YEAR(rp.PaymentDate) AS VARCHAR(4)) AS MonthLabel,
    COUNT(*) AS PaymentCount,
    SUM(rp.AmountPaid) AS TotalCollected
FROM RentPayments rp
WHERE rp.PaymentStatus IN (N'Paid', N'Partially Paid')
  AND rp.PaymentDate IS NOT NULL
GROUP BY YEAR(rp.PaymentDate), MONTH(rp.PaymentDate), DATENAME(MONTH, rp.PaymentDate)
ORDER BY PaymentYear, PaymentMonth;
GO


-- ============================================================
-- Report 4: Rent collected by landlord
-- Business question: how much has been collected on each landlord's
-- behalf in a given period? (Feeds landlord income summaries.)
--
-- Parameters: @PeriodStart / @PeriodEnd - defaults to the current
-- calendar month below; change them to report on any period.
-- Joins: Landlords -> Properties -> Tenancies -> RentPayments, all as
-- LEFT JOIN so a landlord with zero collections in the period still
-- appears with a 0 total, rather than disappearing from the report.
-- Important gotcha this demonstrates: the payment-status/date filter
-- is inside the LEFT JOIN's ON clause, not in a WHERE clause. Putting
-- it in WHERE would silently turn the LEFT JOIN back into an INNER
-- JOIN (any row where RentPayments columns are NULL fails a WHERE
-- condition that references them), which would once again drop
-- landlords with no matching payments.
-- NULL handling: ISNULL(SUM(...), 0) turns "no matching rows" into 0
-- rather than NULL.
-- ============================================================

DECLARE @PeriodStart DATE = DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1);
DECLARE @PeriodEnd   DATE = DATEADD(MONTH, 1, @PeriodStart);

SELECT
    l.LandlordId,
    COALESCE(l.CompanyName, CONCAT(l.FirstName, N' ', l.LastName)) AS LandlordName,
    COUNT(DISTINCT p.PropertyId) AS PropertyCount,
    ISNULL(SUM(rp.AmountPaid), 0) AS TotalCollected
FROM Landlords l
LEFT JOIN Properties p ON p.LandlordId = l.LandlordId AND p.IsActive = 1
LEFT JOIN Tenancies ten ON ten.PropertyId = p.PropertyId
LEFT JOIN RentPayments rp
    ON rp.TenancyId = ten.TenancyId
    AND rp.PaymentStatus IN (N'Paid', N'Partially Paid')
    AND rp.PaymentDate >= @PeriodStart
    AND rp.PaymentDate < @PeriodEnd
WHERE l.IsActive = 1
GROUP BY l.LandlordId, COALESCE(l.CompanyName, CONCAT(l.FirstName, N' ', l.LastName))
ORDER BY TotalCollected DESC;
GO


-- ============================================================
-- Report 5: Occupancy report
-- Business question: what does the portfolio's occupancy look like
-- right now, overall and by status?
--
-- Two result sets: a breakdown by every PropertyStatus value, and a
-- simple headline occupancy-rate summary (used directly by the
-- dashboard KPI card).
-- NULL handling / safety: NULLIF(COUNT(*), 0) in the second query
-- prevents a divide-by-zero error if the Properties table is ever
-- empty (e.g. a brand new, still-empty environment).
-- Window function note: SUM(COUNT(*)) OVER () in the first query
-- gives the grand total alongside each group, without a second query
-- or a self-join, so we can compute each status's share of the whole
-- portfolio in the same pass.
-- ============================================================

-- 5a: breakdown by status
SELECT
    PropertyStatus,
    COUNT(*) AS PropertyCount,
    CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS DECIMAL(5,1)) AS PercentageOfPortfolio
FROM Properties
WHERE IsActive = 1
GROUP BY PropertyStatus
ORDER BY PropertyCount DESC;
GO

-- 5b: headline summary
SELECT
    COUNT(*) AS TotalProperties,
    SUM(CASE WHEN PropertyStatus = N'Occupied' THEN 1 ELSE 0 END) AS OccupiedCount,
    SUM(CASE WHEN PropertyStatus = N'Vacant' THEN 1 ELSE 0 END) AS VacantCount,
    CAST(SUM(CASE WHEN PropertyStatus = N'Occupied' THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0) AS DECIMAL(5,1)) AS OccupancyRatePercent
FROM Properties
WHERE IsActive = 1;
GO


-- ============================================================
-- Report 6: Vacant properties
-- Business question: which properties are sitting vacant right now,
-- and how long have they been empty? (So property managers can
-- prioritise re-letting.)
--
-- OUTER APPLY: for each vacant property, runs a small correlated
-- subquery to find the most recent Ended/Cancelled tenancy's end
-- date. Unlike a JOIN, APPLY can reference columns from the outer
-- query (p.PropertyId) inside the subquery itself - this is the
-- standard pattern for "give me the latest related row per row".
-- NULL handling: ISNULL falls back to DateAcquired for a property
-- that has never had a tenancy at all, so DaysVacant is still
-- meaningful rather than NULL.
-- ============================================================

SELECT
    p.PropertyReference,
    p.AddressLine1, p.City, p.Postcode,
    p.PropertyType, p.Bedrooms, p.Bathrooms, p.MonthlyRent,
    COALESCE(l.CompanyName, CONCAT(l.FirstName, N' ', l.LastName)) AS LandlordName,
    l.Phone AS LandlordPhone,
    l.Email AS LandlordEmail,
    DATEDIFF(DAY, ISNULL(lastten.LastEndDate, p.DateAcquired), CAST(GETDATE() AS DATE)) AS DaysVacant
FROM Properties p
JOIN Landlords l ON l.LandlordId = p.LandlordId
OUTER APPLY (
    SELECT MAX(t.EndDate) AS LastEndDate
    FROM Tenancies t
    WHERE t.PropertyId = p.PropertyId
      AND t.TenancyStatus IN (N'Ended', N'Cancelled')
) AS lastten
WHERE p.PropertyStatus = N'Vacant' AND p.IsActive = 1
ORDER BY DaysVacant DESC;
GO


-- ============================================================
-- Report 7: Tenancies ending within 30, 60 or 90 days
-- Business question: which tenancies need a renewal conversation or
-- re-letting plan soon?
--
-- Parameter: @DaysAhead - set to 30, 60 or 90 (or any value) to reuse
-- this one query for all three lookahead windows.
-- Filtering: EndDate IS NOT NULL excludes periodic/open-ended
-- tenancies (there is no "ending soon" date to compare for those).
-- Status filter includes both 'Active' and 'Ending Soon' - the
-- TenancyStatus value is an administrative flag staff set once
-- notice is confirmed, but this report should surface any tenancy
-- approaching its end date regardless of whether that flag has been
-- set yet.
-- ============================================================

DECLARE @DaysAhead INT = 30; -- change to 60 or 90 to widen the window

SELECT
    t.AgreementReference,
    p.PropertyReference,
    CONCAT(p.AddressLine1, N', ', p.City) AS PropertyAddress,
    CONCAT(tn.FirstName, N' ', tn.LastName) AS TenantName,
    t.EndDate,
    DATEDIFF(DAY, CAST(GETDATE() AS DATE), t.EndDate) AS DaysUntilEnd,
    t.TenancyStatus
FROM Tenancies t
JOIN Properties p ON p.PropertyId = t.PropertyId
JOIN Tenants tn ON tn.TenantId = t.TenantId
WHERE t.TenancyStatus IN (N'Active', N'Ending Soon')
  AND t.EndDate IS NOT NULL
  AND t.EndDate >= CAST(GETDATE() AS DATE)
  AND t.EndDate < DATEADD(DAY, @DaysAhead, CAST(GETDATE() AS DATE))
ORDER BY t.EndDate;
GO


-- ============================================================
-- Report 8: Open maintenance by status and priority
-- Business question: what does the current maintenance workload look
-- like, broken down by status and priority?
--
-- Filtering: excludes Completed and Cancelled - "open" means work
-- that still needs attention.
-- Sorting: Priority is text (Low/Medium/High/Emergency), which does
-- NOT sort into business-meaningful order alphabetically. The CASE
-- expression maps each value to a rank so Emergency always sorts
-- first, matching how a property manager would actually triage the
-- list, regardless of alphabetical order.
-- ============================================================

SELECT
    MaintenanceStatus,
    Priority,
    COUNT(*) AS RequestCount
FROM MaintenanceRequests
WHERE MaintenanceStatus NOT IN (N'Completed', N'Cancelled')
GROUP BY MaintenanceStatus, Priority
ORDER BY
    CASE Priority
        WHEN N'Emergency' THEN 1
        WHEN N'High' THEN 2
        WHEN N'Medium' THEN 3
        WHEN N'Low' THEN 4
    END,
    MaintenanceStatus;
GO


-- ============================================================
-- Report 9: Maintenance costs by property
-- Business question: how much has each property cost in completed
-- maintenance work? (Useful for landlord discussions and expense
-- tracking.)
--
-- Filtering: only Completed requests are counted - EstimatedCost on
-- open requests is a guess, not an actual spend, so it is
-- deliberately excluded here (ActualCost is only populated once work
-- is done, per the schema's business rules).
-- NULL handling: LEFT JOIN keeps properties with zero completed
-- maintenance requests in the report (showing 0), rather than an
-- INNER JOIN silently dropping them. ISNULL wraps the aggregates for
-- the same reason - SUM/AVG of zero rows is NULL, not 0.
-- ============================================================

SELECT
    p.PropertyReference,
    CONCAT(p.AddressLine1, N', ', p.City) AS PropertyAddress,
    COALESCE(l.CompanyName, CONCAT(l.FirstName, N' ', l.LastName)) AS LandlordName,
    COUNT(mr.MaintenanceRequestId) AS CompletedRequestCount,
    ISNULL(SUM(mr.ActualCost), 0) AS TotalActualCost,
    ISNULL(AVG(mr.ActualCost), 0) AS AverageActualCost
FROM Properties p
JOIN Landlords l ON l.LandlordId = p.LandlordId
LEFT JOIN MaintenanceRequests mr
    ON mr.PropertyId = p.PropertyId
    AND mr.MaintenanceStatus = N'Completed'
WHERE p.IsActive = 1
GROUP BY p.PropertyReference, p.AddressLine1, p.City, l.CompanyName, l.FirstName, l.LastName
ORDER BY TotalActualCost DESC;
GO


-- ============================================================
-- Report 10: Property income and performance
-- Business question: for each property, how does rent collection
-- compare to what was due, and what did maintenance cost, over a
-- period? (A combined income/cost performance view.)
--
-- Parameters: @PeriodStart / @PeriodEnd - defaults to year-to-date.
-- Two OUTER APPLYs: one aggregates rent due/collected for the
-- property in the period, the other aggregates completed maintenance
-- cost in the period. APPLY is used (rather than two more LEFT
-- JOIN + GROUP BY passes) because each subquery already returns
-- exactly one row of pre-aggregated totals per property - simpler to
-- read than folding everything into one giant GROUP BY.
-- NULL handling: NULLIF(rent.TotalRentDue, 0) avoids a divide-by-zero
-- for a property with no rent due in the period (e.g. it was vacant
-- the whole time); ISNULL covers properties with no maintenance at
-- all in the period.
-- ============================================================

DECLARE @PeriodStart DATE = DATEFROMPARTS(YEAR(GETDATE()), 1, 1); -- start of this year
DECLARE @PeriodEnd   DATE = DATEADD(DAY, 1, CAST(GETDATE() AS DATE)); -- through today, inclusive

SELECT
    p.PropertyReference,
    CONCAT(p.AddressLine1, N', ', p.City) AS PropertyAddress,
    COALESCE(l.CompanyName, CONCAT(l.FirstName, N' ', l.LastName)) AS LandlordName,
    ISNULL(rent.TotalRentDue, 0) AS TotalRentDue,
    ISNULL(rent.TotalRentCollected, 0) AS TotalRentCollected,
    CAST(ISNULL(rent.TotalRentCollected, 0) * 100.0
        / NULLIF(rent.TotalRentDue, 0) AS DECIMAL(5,1)) AS CollectionRatePercent,
    ISNULL(maint.TotalMaintenanceCost, 0) AS TotalMaintenanceCost,
    ISNULL(rent.TotalRentCollected, 0) - ISNULL(maint.TotalMaintenanceCost, 0) AS NetIncome
FROM Properties p
JOIN Landlords l ON l.LandlordId = p.LandlordId
OUTER APPLY (
    SELECT
        SUM(rp.AmountDue) AS TotalRentDue,
        SUM(rp.AmountPaid) AS TotalRentCollected
    FROM RentPayments rp
    JOIN Tenancies t ON t.TenancyId = rp.TenancyId
    WHERE t.PropertyId = p.PropertyId
      AND rp.PaymentStatus <> N'Cancelled'
      AND rp.DueDate >= @PeriodStart
      AND rp.DueDate < @PeriodEnd
) AS rent
OUTER APPLY (
    SELECT SUM(mr.ActualCost) AS TotalMaintenanceCost
    FROM MaintenanceRequests mr
    WHERE mr.PropertyId = p.PropertyId
      AND mr.MaintenanceStatus = N'Completed'
      AND mr.CompletedDate >= @PeriodStart
      AND mr.CompletedDate < @PeriodEnd
) AS maint
WHERE p.IsActive = 1
ORDER BY NetIncome DESC;
GO
