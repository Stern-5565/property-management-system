-- ============================================================
-- 06-seed-demo-data.sql
-- Realistic demo/sample business data for PropertyManager: landlords,
-- properties, tenants, tenancies, rent payments, maintenance requests,
-- employees and user accounts.
--
-- Dates are fixed (not GETDATE()-relative) so the scenarios below -
-- overdue rent, tenancies ending soon, etc. - stay internally
-- consistent no matter when this script is actually run. They are
-- written relative to an assumed "today" of 2026-08-04.
--
-- This script is intended to run ONCE against a freshly created,
-- empty schema (immediately after scripts 01-05). If you need fresh
-- demo data later, rebuild the database (rerun 01-05) and then run
-- this script again - rerunning it against a database that already
-- has demo data will fail with unique-constraint violations (a
-- deliberate safety net rather than a silent duplicate-insert).
--
-- Password hashes below are obvious placeholders, not real bcrypt
-- hashes - nobody can log in with them. Real password hashing is
-- implemented in the FastAPI auth module (Prompt 10).
--
-- Run this after 05-seed-lookup-data.sql, connected to PropertyManagerDb.
-- ============================================================

USE PropertyManagerDb;
GO

-- Landlords/Tenants/Tenancies have filtered unique indexes, which
-- require QUOTED_IDENTIFIER ON for the session (see 03-create-constraints.sql).
SET QUOTED_IDENTIFIER ON;
GO
SET ANSI_NULLS ON;
GO

-- ============================================================
-- Employees (5)
-- ============================================================

INSERT INTO Employees (FirstName, LastName, Email, Phone, JobTitle, Department, HireDate)
VALUES
    (N'Sarah',  N'Mitchell', N'sarah.mitchell@propertymanager.example', N'020 7946 0011', N'Managing Director',       N'Management',           '2019-03-01'),
    (N'James',  N'Carter',   N'james.carter@propertymanager.example',   N'020 7946 0022', N'Senior Property Manager', N'Property Management',  '2020-06-15'),
    (N'Priya',  N'Patel',    N'priya.patel@propertymanager.example',    N'020 7946 0033', N'Property Manager',        N'Property Management',  '2021-09-01'),
    (N'Daniel', N'Osei',     N'daniel.osei@propertymanager.example',    N'020 7946 0044', N'Maintenance Technician',  N'Maintenance',           '2022-01-10'),
    (N'Emma',   N'Wilson',   N'emma.wilson@propertymanager.example',    N'020 7946 0055', N'Accounts Assistant',      N'Finance',               '2023-04-20');
GO

-- ============================================================
-- Users (5) - one per employee
-- ============================================================

INSERT INTO Users (EmployeeId, Username, Email, PasswordHash, LastLoginAt)
SELECT e.EmployeeId, u.Username, u.EmployeeEmail, u.PwdHash, u.LastLoginAt
FROM Employees e
JOIN (VALUES
    (N'sarah.mitchell@propertymanager.example', N'sarah.mitchell', N'DEMO-HASH-NOT-A-REAL-PASSWORD-sarah',  CAST('2026-08-04T08:15:00' AS DATETIME2)),
    (N'james.carter@propertymanager.example',   N'james.carter',   N'DEMO-HASH-NOT-A-REAL-PASSWORD-james',  CAST('2026-08-03T17:40:00' AS DATETIME2)),
    (N'priya.patel@propertymanager.example',    N'priya.patel',    N'DEMO-HASH-NOT-A-REAL-PASSWORD-priya',  CAST('2026-08-04T09:05:00' AS DATETIME2)),
    (N'daniel.osei@propertymanager.example',    N'daniel.osei',    N'DEMO-HASH-NOT-A-REAL-PASSWORD-daniel', CAST('2026-08-04T07:50:00' AS DATETIME2)),
    (N'emma.wilson@propertymanager.example',    N'emma.wilson',    N'DEMO-HASH-NOT-A-REAL-PASSWORD-emma',   CAST('2026-07-30T12:00:00' AS DATETIME2))
) AS u(EmployeeEmail, Username, PwdHash, LastLoginAt) ON e.Email = u.EmployeeEmail;
GO

-- ============================================================
-- UserRoles - one role per user (Priya doubles up is not needed;
-- each of the four roles is represented at least once)
-- ============================================================

INSERT INTO UserRoles (UserId, RoleId)
SELECT usr.UserId, r.RoleId
FROM (VALUES
    (N'sarah.mitchell', N'Administrator'),
    (N'james.carter',   N'PropertyManager'),
    (N'priya.patel',    N'PropertyManager'),
    (N'daniel.osei',    N'MaintenanceEmployee'),
    (N'emma.wilson',    N'ReadOnly')
) AS ur(Username, RoleName)
JOIN Users usr ON usr.Username = ur.Username
JOIN Roles r ON r.RoleName = ur.RoleName;
GO

-- ============================================================
-- Landlords (5) - a mix of individuals and companies, to exercise
-- CK_Landlords_NameOrCompany
-- ============================================================

INSERT INTO Landlords (FirstName, LastName, CompanyName, Email, Phone, AddressLine1, AddressLine2, City, Postcode, Country, PreferredContactMethod)
VALUES
    (N'Robert', N'Jenkins', NULL,                        N'robert.jenkins@example.com',        N'07700 900101', N'45 Baker Street',              NULL, N'London',    N'NW1 6XE', N'United Kingdom', N'Email'),
    (NULL,      NULL,       N'Green Oak Properties Ltd', N'contact@greenoakproperties.co.uk',  N'0161 496 0102', N'Unit 4 Riverside Business Park', NULL, N'Manchester', N'M1 2WD',  N'United Kingdom', N'Email'),
    (N'Fiona',  N'Campbell', NULL,                        N'fiona.campbell@example.com',        N'07700 900103', N'12 Queens Road',               NULL, N'Bristol',   N'BS8 1QU', N'United Kingdom', N'Phone'),
    (NULL,      NULL,       N'Henderson Estates Ltd',    N'info@hendersonestates.co.uk',       N'0113 496 0104', N'88 Wellington Street',         NULL, N'Leeds',     N'LS1 4LT', N'United Kingdom', N'Post'),
    (N'Michael', N'O''Brien', NULL,                       N'michael.obrien@example.com',        N'07700 900105', N'3 Elm Grove',                  NULL, N'Leeds',     N'LS6 3HN', N'United Kingdom', N'Email');
GO

-- ============================================================
-- Properties (10) - covers Occupied, Vacant, Under Maintenance and
-- Archived statuses across all 5 landlords
-- ============================================================

INSERT INTO Properties (LandlordId, PropertyReference, AddressLine1, AddressLine2, City, Postcode, Country, PropertyType, Bedrooms, Bathrooms, MonthlyRent, DepositAmount, PropertyStatus, DateAcquired, Notes, IsActive)
SELECT l.LandlordId, v.PropertyReference, v.AddressLine1, v.AddressLine2, v.City, v.Postcode, v.Country, v.PropertyType, v.Bedrooms, v.Bathrooms, v.MonthlyRent, v.DepositAmount, v.PropertyStatus, v.DateAcquired, v.Notes, v.IsActive
FROM (VALUES
    (N'robert.jenkins@example.com',       N'PM-0001', N'12 Maple Street',      NULL, N'London',     N'N4 3JT',  N'United Kingdom', N'Flat',       2, 1, 1200.00, 1200.00, N'Occupied',          '2018-05-12', NULL, 1),
    (N'robert.jenkins@example.com',       N'PM-0002', N'14 Maple Street',      NULL, N'London',     N'N4 3JT',  N'United Kingdom', N'Flat',       1, 1,  950.00,  950.00, N'Vacant',            '2018-05-12', N'Being prepared for re-letting.', 1),
    (N'contact@greenoakproperties.co.uk', N'PM-0003', N'3 Oak Avenue',         NULL, N'Manchester', N'M14 5RT', N'United Kingdom', N'House',      3, 2, 1450.00, 1450.00, N'Occupied',          '2016-11-01', NULL, 1),
    (N'contact@greenoakproperties.co.uk', N'PM-0004', N'5 Oak Avenue',         NULL, N'Manchester', N'M14 5RT', N'United Kingdom', N'House',      3, 1, 1400.00, 1400.00, N'Occupied',          '2016-11-01', NULL, 1),
    (N'contact@greenoakproperties.co.uk', N'PM-0005', N'22 Birch Road',        NULL, N'Manchester', N'M20 2LB', N'United Kingdom', N'Bungalow',   2, 1, 1100.00, 1100.00, N'Under Maintenance', '2020-02-20', N'Boiler replacement in progress.', 1),
    (N'fiona.campbell@example.com',       N'PM-0006', N'7 Riverside Court',    NULL, N'Bristol',    N'BS1 6XN', N'United Kingdom', N'Flat',       2, 1, 1050.00, 1050.00, N'Occupied',          '2019-07-08', NULL, 1),
    (N'fiona.campbell@example.com',       N'PM-0007', N'9 Riverside Court',    NULL, N'Bristol',    N'BS1 6XN', N'United Kingdom', N'Studio',     0, 1,  750.00,  750.00, N'Vacant',            '2019-07-08', NULL, 1),
    (N'info@hendersonestates.co.uk',      N'PM-0008', N'18 Kings Road',        NULL, N'Leeds',      N'LS6 1EP', N'United Kingdom', N'Flat',       2, 1,  975.00,  975.00, N'Occupied',          '2017-09-15', NULL, 1),
    (N'info@hendersonestates.co.uk',      N'PM-0009', N'20 Kings Road',        NULL, N'Leeds',      N'LS6 1EP', N'United Kingdom', N'House',      4, 2, 1650.00, 1650.00, N'Occupied',          '2017-09-15', NULL, 1),
    (N'michael.obrien@example.com',       N'PM-0010', N'2 Church Lane',        NULL, N'Leeds',      N'LS7 4PW', N'United Kingdom', N'Maisonette', 3, 2, 1250.00, 1250.00, N'Archived',          '2014-03-03', N'Sold by landlord; no longer managed.', 0)
) AS v(LandlordEmail, PropertyReference, AddressLine1, AddressLine2, City, Postcode, Country, PropertyType, Bedrooms, Bathrooms, MonthlyRent, DepositAmount, PropertyStatus, DateAcquired, Notes, IsActive)
JOIN Landlords l ON l.Email = v.LandlordEmail;
GO

-- ============================================================
-- Tenants (12)
-- ============================================================

INSERT INTO Tenants (FirstName, LastName, Email, Phone, DateOfBirth, PreviousAddress, EmergencyContactName, EmergencyContactPhone, IdentificationReference, EmploymentStatus, IsActive)
VALUES
    (N'John',     N'Okafor',    N'john.okafor@example.com',     N'07700 900201', '1990-04-12', N'22 Station Road, London',       N'Grace Okafor',    N'07700 900301', N'Passport ref: 4K1-88213',  N'Employed',      1),
    (N'Laura',    N'Bennett',   N'laura.bennett@example.com',   N'07700 900202', '1988-11-03', N'5 Church Street, Manchester',   N'Peter Bennett',   N'07700 900302', N'Driving licence ref: BE775612', N'Employed', 1),
    (N'Ahmed',    N'Hassan',    N'ahmed.hassan@example.com',    N'07700 900203', '1979-02-25', N'18 Mill Lane, Manchester',      N'Layla Hassan',    N'07700 900303', N'Passport ref: 9H4-22190',  N'Self-Employed', 1),
    (N'Chloe',    N'Davies',    N'chloe.davies@example.com',    N'07700 900204', '1995-07-19', N'40 Park Avenue, Manchester',    N'Rhys Davies',     N'07700 900304', N'Driving licence ref: DA664521', N'Employed', 1),
    (N'Grace',    N'Kim',       N'grace.kim@example.com',       N'07700 900205', '1992-09-30', N'8 Harbour View, Bristol',       N'Min-jun Kim',     N'07700 900305', N'Passport ref: 2K9-51873',  N'Employed',      1),
    (N'Marcus',   N'Reid',      N'marcus.reid@example.com',     N'07700 900206', '1985-01-14', N'31 Victoria Street, Leeds',     N'Anna Reid',       N'07700 900306', N'Driving licence ref: RE448820', N'Self-Employed', 1),
    (N'Sophie',   N'Turner',    N'sophie.turner@example.com',   N'07700 900207', '1983-06-08', N'6 Prospect Place, Leeds',       N'Mark Turner',     N'07700 900307', N'Passport ref: 7T3-64025',  N'Employed',      1),
    (N'Oliver',   N'Bennett',   N'oliver.bennett@example.com',  N'07700 900208', '1998-03-11', N'2 Elm Court, London',           N'Karen Bennett',   N'07700 900308', N'Driving licence ref: BE229104', N'Employed', 1),
    (N'Isabelle', N'Moore',     N'isabelle.moore@example.com',  N'07700 900209', '2001-05-17', N'14 Wellington Row, Bristol',    N'Tom Moore',       N'07700 900309', N'Passport ref: 5M7-30918',  N'Student',       1),
    (N'Ryan',     N'Walsh',     N'ryan.walsh@example.com',      N'07700 900210', '1975-10-02', N'27 Fenwick Drive, Manchester',  N'Claire Walsh',    N'07700 900310', N'Driving licence ref: WA119983', N'Self-Employed', 1),
    (N'Nathan',   N'Green',     N'nathan.green@example.com',    N'07700 900211', '1960-08-29', N'11 Orchard Close, Leeds',       N'Susan Green',     N'07700 900311', N'Passport ref: 3G6-77104',  N'Retired',       1),
    (N'Amelia',   N'Foster',    N'amelia.foster@example.com',   N'07700 900212', '1993-03-05', N'9 Cedar Grove, London',         N'Liam Foster',     N'07700 900312', N'Driving licence ref: FO885210', N'Employed', 1);
GO

-- ============================================================
-- Tenancies (12)
-- Statuses: 6 Active, 4 Ended, 1 Ending Soon, 1 Upcoming.
-- PM-0001 shows a clean handover: T1 ends 2026-08-31, T12 (same
-- property) starts 2026-09-01 - sequential, not overlapping.
-- ============================================================

INSERT INTO Tenancies (PropertyId, TenantId, StartDate, EndDate, MonthlyRent, DepositAmount, PaymentDueDay, TenancyStatus, CheckInDate, CheckOutDate, AgreementReference, Notes)
SELECT p.PropertyId, tn.TenantId, v.StartDate, v.EndDate, v.MonthlyRent, v.DepositAmount, v.PaymentDueDay, v.TenancyStatus, v.CheckInDate, v.CheckOutDate, v.AgreementReference, v.Notes
FROM (VALUES
    (N'PM-0001', N'john.okafor@example.com',     '2025-09-01', '2026-08-31', 1200.00, 1200.00,  1, N'Ending Soon', '2025-09-01', NULL,         N'AGR-1001', N'Tenant has given notice; not renewing.'),
    (N'PM-0003', N'laura.bennett@example.com',   '2025-11-01', '2026-10-31', 1450.00, 1450.00,  1, N'Active',      '2025-11-01', NULL,         N'AGR-1002', NULL),
    (N'PM-0004', N'ahmed.hassan@example.com',    '2024-05-01', '2025-04-30', 1350.00, 1350.00,  5, N'Ended',       '2024-05-01', '2025-04-28', N'AGR-1003', NULL),
    (N'PM-0004', N'chloe.davies@example.com',    '2025-05-15', NULL,         1400.00, 1400.00, 15, N'Active',      '2025-05-15', NULL,         N'AGR-1004', N'Periodic tenancy - no fixed end date.'),
    (N'PM-0006', N'grace.kim@example.com',       '2026-01-01', '2026-12-31', 1050.00, 1050.00,  1, N'Active',      '2026-01-01', NULL,         N'AGR-1005', NULL),
    (N'PM-0008', N'marcus.reid@example.com',     '2025-07-01', '2026-06-30',  975.00,  975.00,  1, N'Active',      '2025-07-01', NULL,         N'AGR-1006', NULL),
    (N'PM-0009', N'sophie.turner@example.com',   '2025-02-01', '2027-01-31', 1650.00, 1650.00, 28, N'Active',      '2025-02-01', NULL,         N'AGR-1007', NULL),
    (N'PM-0002', N'oliver.bennett@example.com',  '2024-01-01', '2024-12-31',  900.00,  900.00,  1, N'Ended',       '2024-01-01', '2024-12-30', N'AGR-1008', NULL),
    (N'PM-0007', N'isabelle.moore@example.com',  '2025-03-01', '2026-02-28',  720.00,  720.00,  1, N'Ended',       '2025-03-01', '2026-02-27', N'AGR-1009', NULL),
    (N'PM-0005', N'ryan.walsh@example.com',      '2025-10-01', '2026-09-30', 1100.00, 1100.00,  1, N'Active',      '2025-10-01', NULL,         N'AGR-1010', N'Tenant remains in situ during boiler works.'),
    (N'PM-0010', N'nathan.green@example.com',    '2022-01-01', '2023-12-31', 1200.00, 1200.00,  1, N'Ended',       '2022-01-01', '2023-12-30', N'AGR-1011', NULL),
    (N'PM-0001', N'amelia.foster@example.com',   '2026-09-01', '2027-08-31', 1250.00, 1250.00,  1, N'Upcoming',    NULL,         NULL,         N'AGR-1012', N'Agreed to start the day after the current tenancy ends.')
) AS v(PropertyRef, TenantEmail, StartDate, EndDate, MonthlyRent, DepositAmount, PaymentDueDay, TenancyStatus, CheckInDate, CheckOutDate, AgreementReference, Notes)
JOIN Properties p ON p.PropertyReference = v.PropertyRef
JOIN Tenants tn ON tn.Email = v.TenantEmail;
GO

-- ============================================================
-- RentPayments (30)
-- 7 currently-active-ish tenancies x 4 months (May-Aug 2026) = 28,
-- plus 2 final historical payments for ended tenancies = 30.
-- Statuses covered: Paid, Partially Paid, Overdue, Pending, Cancelled.
-- ============================================================

INSERT INTO RentPayments (TenancyId, PaymentReference, DueDate, AmountDue, AmountPaid, PaymentDate, PaymentMethod, PaymentStatus, Notes, CreatedByEmployeeId)
SELECT t.TenancyId, v.PaymentReference, v.DueDate, v.AmountDue, v.AmountPaid, v.PaymentDate, v.PaymentMethod, v.PaymentStatus, v.Notes, emp.EmployeeId
FROM (VALUES
    -- AGR-1001 (John Okafor, PM-0001, rent 1200, due day 1)
    (N'AGR-1001', N'PAY-00001', '2026-05-01', 1200.00, 1200.00, '2026-05-01', N'Standing Order', N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1001', N'PAY-00002', '2026-06-01', 1200.00, 1200.00, '2026-06-01', N'Standing Order', N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1001', N'PAY-00003', '2026-07-01', 1200.00, 1200.00, '2026-07-01', N'Standing Order', N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1001', N'PAY-00004', '2026-08-01', 1200.00,    0.00, NULL,         NULL,               N'Overdue',         N'No payment received; tenant contacted 2026-08-03.', N'james.carter@propertymanager.example'),

    -- AGR-1002 (Laura Bennett, PM-0003, rent 1450, due day 1)
    (N'AGR-1002', N'PAY-00005', '2026-05-01', 1450.00, 1450.00, '2026-05-01', N'Bank Transfer', N'Paid',            NULL,                                              N'priya.patel@propertymanager.example'),
    (N'AGR-1002', N'PAY-00006', '2026-06-01', 1450.00, 1450.00, '2026-06-01', N'Bank Transfer', N'Paid',            NULL,                                              N'priya.patel@propertymanager.example'),
    (N'AGR-1002', N'PAY-00007', '2026-07-01', 1450.00, 1450.00, '2026-07-01', N'Bank Transfer', N'Paid',            NULL,                                              N'priya.patel@propertymanager.example'),
    (N'AGR-1002', N'PAY-00008', '2026-08-01', 1450.00,  700.00, '2026-08-02', N'Bank Transfer', N'Partially Paid',  N'Tenant to pay remaining GBP 750 by 2026-08-10.',    N'priya.patel@propertymanager.example'),

    -- AGR-1004 (Chloe Davies, PM-0004, rent 1400, due day 15)
    (N'AGR-1004', N'PAY-00009', '2026-05-15', 1400.00, 1400.00, '2026-05-15', N'Direct Debit',  N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1004', N'PAY-00010', '2026-06-15', 1400.00, 1400.00, '2026-06-15', N'Direct Debit',  N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1004', N'PAY-00011', '2026-07-15', 1400.00, 1400.00, '2026-07-15', N'Direct Debit',  N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1004', N'PAY-00012', '2026-08-15', 1400.00,    0.00, NULL,         NULL,               N'Pending',         N'Not yet due.',                                   N'james.carter@propertymanager.example'),

    -- AGR-1005 (Grace Kim, PM-0006, rent 1050, due day 1)
    (N'AGR-1005', N'PAY-00013', '2026-05-01', 1050.00, 1050.00, '2026-05-01', N'Card',          N'Paid',            NULL,                                              N'priya.patel@propertymanager.example'),
    (N'AGR-1005', N'PAY-00014', '2026-06-01', 1050.00, 1050.00, '2026-06-01', N'Card',          N'Paid',            NULL,                                              N'priya.patel@propertymanager.example'),
    (N'AGR-1005', N'PAY-00015', '2026-07-01', 1050.00, 1050.00, '2026-07-01', N'Card',          N'Paid',            NULL,                                              N'priya.patel@propertymanager.example'),
    (N'AGR-1005', N'PAY-00016', '2026-08-01', 1050.00, 1050.00, '2026-08-01', N'Card',          N'Paid',            NULL,                                              N'priya.patel@propertymanager.example'),

    -- AGR-1006 (Marcus Reid, PM-0008, rent 975, due day 1)
    (N'AGR-1006', N'PAY-00017', '2026-05-01',  975.00,  975.00, '2026-05-01', N'Bank Transfer', N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1006', N'PAY-00018', '2026-06-01',  975.00,  975.00, '2026-06-01', N'Bank Transfer', N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1006', N'PAY-00019', '2026-07-01',  975.00,    0.00, NULL,         NULL,               N'Overdue',         N'Missed payment; follow-up letter sent 2026-07-20.', N'james.carter@propertymanager.example'),
    (N'AGR-1006', N'PAY-00020', '2026-08-01',  975.00,  975.00, '2026-08-01', N'Bank Transfer', N'Paid',            N'July arrears still outstanding separately.',    N'james.carter@propertymanager.example'),

    -- AGR-1007 (Sophie Turner, PM-0009, rent 1650, due day 28)
    (N'AGR-1007', N'PAY-00021', '2026-05-28', 1650.00, 1650.00, '2026-05-28', N'Standing Order', N'Paid',           NULL,                                              N'priya.patel@propertymanager.example'),
    (N'AGR-1007', N'PAY-00022', '2026-06-28', 1650.00, 1650.00, '2026-06-28', N'Standing Order', N'Paid',           NULL,                                              N'priya.patel@propertymanager.example'),
    (N'AGR-1007', N'PAY-00023', '2026-07-28', 1650.00, 1650.00, '2026-07-28', N'Standing Order', N'Paid',           NULL,                                              N'priya.patel@propertymanager.example'),
    (N'AGR-1007', N'PAY-00024', '2026-08-28', 1650.00,    0.00, NULL,         NULL,               N'Pending',        N'Not yet due.',                                   N'priya.patel@propertymanager.example'),

    -- AGR-1010 (Ryan Walsh, PM-0005, rent 1100, due day 1)
    (N'AGR-1010', N'PAY-00025', '2026-05-01', 1100.00, 1100.00, '2026-05-01', N'Cash',          N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1010', N'PAY-00026', '2026-06-01', 1100.00,    0.00, NULL,         NULL,               N'Cancelled',       N'June rent waived - compensation for extended boiler outage.', N'sarah.mitchell@propertymanager.example'),
    (N'AGR-1010', N'PAY-00027', '2026-07-01', 1100.00, 1100.00, '2026-07-01', N'Cash',          N'Paid',            NULL,                                              N'james.carter@propertymanager.example'),
    (N'AGR-1010', N'PAY-00028', '2026-08-01', 1100.00,  600.00, '2026-08-03', N'Cash',          N'Partially Paid',  N'Tenant to pay remaining GBP 500 by 2026-08-15.',    N'james.carter@propertymanager.example'),

    -- Final historical payments on ended tenancies
    (N'AGR-1003', N'PAY-00029', '2025-04-05', 1350.00, 1350.00, '2025-04-05', N'Bank Transfer', N'Paid',            N'Final rent payment before tenancy ended.',       N'priya.patel@propertymanager.example'),
    (N'AGR-1008', N'PAY-00030', '2024-12-01',  900.00,  900.00, '2024-12-01', N'Bank Transfer', N'Paid',            N'Final rent payment before tenancy ended.',       N'james.carter@propertymanager.example')
) AS v(AgreementRef, PaymentReference, DueDate, AmountDue, AmountPaid, PaymentDate, PaymentMethod, PaymentStatus, Notes, CreatedByEmail)
JOIN Tenancies t ON t.AgreementReference = v.AgreementRef
JOIN Employees emp ON emp.Email = v.CreatedByEmail;
GO

-- ============================================================
-- MaintenanceRequests (20)
-- 6 Completed, 12 open (Reported/Assigned/In Progress/Waiting for
-- Parts/Waiting for Approval), 2 Cancelled. 4 Emergency priority
-- (including one still unassigned).
-- ============================================================

INSERT INTO MaintenanceRequests (PropertyId, TenancyId, TenantId, AssignedEmployeeId, RequestReference, Title, Description, Category, Priority, MaintenanceStatus, ReportedDate, ScheduledDate, CompletedDate, EstimatedCost, ActualCost, ResolutionNotes)
SELECT p.PropertyId, ten.TenancyId, tn.TenantId, emp.EmployeeId, v.RequestReference, v.Title, v.Description, v.Category, v.Priority, v.MaintenanceStatus, v.ReportedDate, v.ScheduledDate, v.CompletedDate, v.EstimatedCost, v.ActualCost, v.ResolutionNotes
FROM (VALUES
    (N'PM-0001', N'AGR-1001', N'john.okafor@example.com',    N'daniel.osei@propertymanager.example', N'MR-0001', N'Kitchen tap dripping',        N'Cold tap in kitchen drips constantly.',        N'Plumbing',   N'High',      N'Completed',          '2026-06-10', '2026-06-12', '2026-06-13', 150.00, 165.00, N'Replaced kitchen tap washer.'),
    (N'PM-0001', N'AGR-1001', N'john.okafor@example.com',    N'daniel.osei@propertymanager.example', N'MR-0002', N'No power in hallway',         N'Hallway socket and light not working.',        N'Electrical', N'Emergency', N'In Progress',        '2026-08-02', '2026-08-04', NULL,         300.00,   NULL, NULL),
    (N'PM-0002', NULL,        NULL,                          NULL,                                    N'MR-0003', N'General inspection follow-up', N'Minor scuffed paintwork noted during void inspection.', N'General',  N'Low',       N'Reported',           '2026-07-20', NULL,         NULL,          NULL,   NULL, NULL),
    (N'PM-0003', N'AGR-1002', N'laura.bennett@example.com',  N'daniel.osei@propertymanager.example', N'MR-0004', N'Radiator not heating',        N'Living room radiator stays cold even with heating on.', N'Heating',  N'Medium',    N'Assigned',           '2026-07-28', '2026-08-06', NULL,         200.00,   NULL, NULL),
    (N'PM-0004', N'AGR-1004', N'chloe.davies@example.com',   N'daniel.osei@propertymanager.example', N'MR-0005', N'Washing machine belt broken',  N'Washing machine drum not turning.',            N'Appliance',  N'Medium',    N'Completed',          '2026-05-15', '2026-05-18', '2026-05-19', 120.00, 110.00, N'Replaced washing machine belt.'),
    (N'PM-0004', N'AGR-1004', N'chloe.davies@example.com',   NULL,                                    N'MR-0006', N'Crack in garden wall',        N'Vertical crack appearing in rear garden boundary wall.', N'Structural', N'Low',      N'Waiting for Approval', '2026-07-01', NULL,       NULL,          800.00,   NULL, NULL),
    (N'PM-0005', N'AGR-1010', N'ryan.walsh@example.com',     N'daniel.osei@propertymanager.example', N'MR-0007', N'Boiler breakdown',            N'No hot water or heating; boiler showing fault code.', N'Heating',   N'Emergency', N'In Progress',        '2026-07-30', '2026-08-01', NULL,         500.00,   NULL, NULL),
    (N'PM-0005', N'AGR-1010', N'ryan.walsh@example.com',     N'daniel.osei@propertymanager.example', N'MR-0008', N'Kitchen sink blocked',        N'Slow-draining kitchen sink, now fully blocked.', N'Plumbing',   N'High',      N'Waiting for Parts',  '2026-07-25', NULL,         NULL,          250.00,   NULL, NULL),
    (N'PM-0006', N'AGR-1005', N'grace.kim@example.com',      N'daniel.osei@propertymanager.example', N'MR-0009', N'Front door lock faulty',      N'Key sticking in front door lock.',             N'Security',   N'High',      N'Completed',          '2026-03-10', '2026-03-11', '2026-03-11',  90.00,  85.00, N'Replaced front door lock.'),
    (N'PM-0006', N'AGR-1005', N'grace.kim@example.com',      NULL,                                    N'MR-0010', N'Requested carpet clean',      N'Tenant requested professional carpet cleaning.', N'Cleaning',   N'Low',       N'Cancelled',          '2026-06-01', NULL,         NULL,          NULL,   NULL, NULL),
    (N'PM-0007', NULL,        NULL,                          NULL,                                    N'MR-0011', N'Pre-let touch-up needed',      N'Minor wall scuffs to fix before re-letting.',  N'General',    N'Low',       N'Reported',           '2026-07-15', NULL,         NULL,          NULL,   NULL, NULL),
    (N'PM-0008', N'AGR-1006', N'marcus.reid@example.com',    N'daniel.osei@propertymanager.example', N'MR-0012', N'Faulty living room socket',   N'Socket sparked when plug was inserted.',       N'Electrical', N'Medium',    N'Completed',          '2026-04-05', '2026-04-08', '2026-04-09', 180.00, 175.00, N'Fixed faulty socket in living room.'),
    (N'PM-0008', N'AGR-1006', N'marcus.reid@example.com',    NULL,                                    N'MR-0013', N'Fridge freezer noisy',        N'Fridge freezer making a loud humming noise.',  N'Appliance',  N'Medium',    N'Reported',           '2026-08-01', NULL,         NULL,          NULL,   NULL, NULL),
    (N'PM-0009', N'AGR-1007', N'sophie.turner@example.com',  N'daniel.osei@propertymanager.example', N'MR-0014', N'No heating in bedrooms',      N'Upstairs radiators not heating up at all.',    N'Heating',    N'Emergency', N'Assigned',           '2026-08-03', '2026-08-05', NULL,         400.00,   NULL, NULL),
    (N'PM-0009', N'AGR-1007', N'sophie.turner@example.com',  N'daniel.osei@propertymanager.example', N'MR-0015', N'Dripping bathroom tap',       N'Bathroom basin tap drips overnight.',          N'Plumbing',   N'Low',       N'Completed',          '2026-02-14', '2026-02-16', '2026-02-16',  75.00,  70.00, N'Fixed dripping tap in bathroom.'),
    (N'PM-0003', N'AGR-1002', N'laura.bennett@example.com',  NULL,                                    N'MR-0016', N'Squeaky floorboard',          N'Floorboard on landing squeaks loudly.',        N'Other',      N'Low',       N'Reported',           '2026-08-03', NULL,         NULL,          NULL,   NULL, NULL),
    (N'PM-0010', NULL,        NULL,                          NULL,                                    N'MR-0017', N'Guttering repair',            N'Guttering reported loose before property was sold.', N'Structural', N'Low',       N'Cancelled',          '2025-11-01', NULL,         NULL,          NULL,   NULL, NULL),
    (N'PM-0001', N'AGR-1001', N'john.okafor@example.com',    N'daniel.osei@propertymanager.example', N'MR-0018', N'End of tenancy clean',        N'Deep clean ahead of tenancy handover.',        N'Cleaning',   N'Low',       N'Completed',          '2026-01-20', '2026-01-22', '2026-01-22',  60.00,  60.00, N'End of tenancy clean completed ahead of renewal.'),
    (N'PM-0002', NULL,        NULL,                          N'daniel.osei@propertymanager.example', N'MR-0019', N'Void property security check', N'Locks and window latches to be checked while vacant.', N'Security', N'Medium',    N'In Progress',        '2026-07-29', '2026-08-05', NULL,         220.00,   NULL, NULL),
    (N'PM-0004', N'AGR-1004', N'chloe.davies@example.com',   NULL,                                    N'MR-0020', N'Burning smell from fuse box',  N'Tenant reports burning smell near the fuse box.', N'Electrical', N'Emergency', N'Reported',          '2026-08-04', NULL,         NULL,          NULL,   NULL, NULL)
) AS v(PropertyRef, AgreementRef, TenantEmail, AssignedEmail, RequestReference, Title, Description, Category, Priority, MaintenanceStatus, ReportedDate, ScheduledDate, CompletedDate, EstimatedCost, ActualCost, ResolutionNotes)
JOIN Properties p ON p.PropertyReference = v.PropertyRef
LEFT JOIN Tenancies ten ON ten.AgreementReference = v.AgreementRef
LEFT JOIN Tenants tn ON tn.Email = v.TenantEmail
LEFT JOIN Employees emp ON emp.Email = v.AssignedEmail;
GO

-- ============================================================
-- MaintenanceNotes (8) - a running log on a handful of open requests
-- ============================================================

INSERT INTO MaintenanceNotes (MaintenanceRequestId, EmployeeId, NoteText)
SELECT mr.MaintenanceRequestId, emp.EmployeeId, v.NoteText
FROM (VALUES
    (N'MR-0002', N'daniel.osei@propertymanager.example', N'Isolated the circuit; waiting on replacement consumer unit part.'),
    (N'MR-0004', N'daniel.osei@propertymanager.example', N'Bled the radiator, no improvement - likely a pump issue, booked for 06/08.'),
    (N'MR-0006', N'james.carter@propertymanager.example', N'Sent photos to landlord for repair approval; awaiting response.'),
    (N'MR-0007', N'daniel.osei@propertymanager.example', N'Part ordered from supplier, expected 2026-08-06. Tenant given a temporary electric heater.'),
    (N'MR-0007', N'daniel.osei@propertymanager.example', N'Part arrived early - rescheduled repair for tomorrow morning.'),
    (N'MR-0008', N'daniel.osei@propertymanager.example', N'Blockage is further down the stack than expected; drain rods on order.'),
    (N'MR-0014', N'priya.patel@propertymanager.example', N'Tenant confirmed availability for 2026-08-05 morning appointment.'),
    (N'MR-0020', N'james.carter@propertymanager.example', N'Advised tenant to switch off affected circuit at the fuse box until inspected.')
) AS v(RequestReference, EmployeeEmail, NoteText)
JOIN MaintenanceRequests mr ON mr.RequestReference = v.RequestReference
JOIN Employees emp ON emp.Email = v.EmployeeEmail;
GO

-- ============================================================
-- Verification: record counts
-- ============================================================

SELECT 'Employees' AS TableName, COUNT(*) AS RecordCount FROM Employees
UNION ALL SELECT 'Users', COUNT(*) FROM Users
UNION ALL SELECT 'UserRoles', COUNT(*) FROM UserRoles
UNION ALL SELECT 'Landlords', COUNT(*) FROM Landlords
UNION ALL SELECT 'Properties', COUNT(*) FROM Properties
UNION ALL SELECT 'Tenants', COUNT(*) FROM Tenants
UNION ALL SELECT 'Tenancies', COUNT(*) FROM Tenancies
UNION ALL SELECT 'RentPayments', COUNT(*) FROM RentPayments
UNION ALL SELECT 'MaintenanceRequests', COUNT(*) FROM MaintenanceRequests
UNION ALL SELECT 'MaintenanceNotes', COUNT(*) FROM MaintenanceNotes;
GO

-- Scenario checks - each should return at least 1 row
SELECT 'Occupied properties' AS Scenario, COUNT(*) AS Cnt FROM Properties WHERE PropertyStatus = N'Occupied'
UNION ALL SELECT 'Vacant properties', COUNT(*) FROM Properties WHERE PropertyStatus = N'Vacant'
UNION ALL SELECT 'Active tenancies', COUNT(*) FROM Tenancies WHERE TenancyStatus = N'Active'
UNION ALL SELECT 'Ended tenancies', COUNT(*) FROM Tenancies WHERE TenancyStatus = N'Ended'
UNION ALL SELECT 'Tenancies ending soon (status)', COUNT(*) FROM Tenancies WHERE TenancyStatus = N'Ending Soon'
UNION ALL SELECT 'Fully paid rent', COUNT(*) FROM RentPayments WHERE PaymentStatus = N'Paid'
UNION ALL SELECT 'Partially paid rent', COUNT(*) FROM RentPayments WHERE PaymentStatus = N'Partially Paid'
UNION ALL SELECT 'Overdue rent', COUNT(*) FROM RentPayments WHERE PaymentStatus = N'Overdue'
UNION ALL SELECT 'Open maintenance', COUNT(*) FROM MaintenanceRequests WHERE MaintenanceStatus NOT IN (N'Completed', N'Cancelled')
UNION ALL SELECT 'Emergency maintenance', COUNT(*) FROM MaintenanceRequests WHERE Priority = N'Emergency'
UNION ALL SELECT 'Completed maintenance', COUNT(*) FROM MaintenanceRequests WHERE MaintenanceStatus = N'Completed';
GO
