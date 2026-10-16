@echo off
setlocal
rem Edit the server/instance or authentication settings below for your computer.
set "CAPSTONE_STORAGE_BACKEND=sqlserver"
set "CAPSTONE_SQLSERVER_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=localhost\SQLEXPRESS;Database=CapstoneLinePlanning;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
python app.py
if errorlevel 1 pause
