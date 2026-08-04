-- ============================================================
-- 01-create-database.sql
-- Creates the PropertyManagerDb database if it does not already exist.
-- Run this first, connected to the "master" database.
-- ============================================================

USE master;
GO

IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'PropertyManagerDb')
BEGIN
    CREATE DATABASE PropertyManagerDb;
END
GO
