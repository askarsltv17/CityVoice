@echo off
setlocal

set "PSQL_EXE=C:\Program Files\PostgreSQL\17\bin\psql.exe"

if not exist "%PSQL_EXE%" (
  echo PostgreSQL client not found:
  echo %PSQL_EXE%
  exit /b 1
)

powershell -NoExit -NoProfile -Command ^
  "$env:PGPASSWORD='postgres';" ^
  "$env:PGCLIENTENCODING='UTF8';" ^
  "[Console]::InputEncoding = [System.Text.UTF8Encoding]::new();" ^
  "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new();" ^
  "& '%PSQL_EXE%' -h 127.0.0.1 -p 5432 -U postgres -d cityvoice"
