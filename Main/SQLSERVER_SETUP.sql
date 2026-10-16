-- Run this once in SQL Server Management Studio, connected to your SQL Express instance.
-- Assumes you have permission to create a database.
IF DB_ID(N'CapstoneLinePlanning') IS NULL
BEGIN
    EXEC(N'CREATE DATABASE CapstoneLinePlanning');
END
GO
USE CapstoneLinePlanning;
GO
-- The Flask application creates dbo.CapstoneSaves automatically on first access.
-- To verify that it is populated after migration:
-- SELECT save_type, file_name, revision, modified_utc FROM dbo.CapstoneSaves;
