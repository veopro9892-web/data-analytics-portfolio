@echo off
REM ==============================================================================
REM SAP 3-Way Match Procurement Reconciliation — Complete Demo Runner
REM Windows Batch Command (.bat)
REM ==============================================================================

echo ====================================================================
echo Starting SAP Procurement 3-Way Match Reconciliation Pipeline...
echo ====================================================================

echo [1/5] Generating Deterministic SAP Procurement Data & Benchmark Fixtures...
python src\generate_sap_data.py
if %ERRORLEVEL% NEQ 0 (
    echo Error generating SAP data! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo [2/5] Loading SQLite Database & Executing Independent Aggregation Match...
python src\load_database.py
if %ERRORLEVEL% NEQ 0 (
    echo Error loading database! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo [3/5] Generating Analytical CSV Reports and Excel AP Review Workbook...
python src\generate_excel_review.py
if %ERRORLEVEL% NEQ 0 (
    echo Error generating Excel workbook! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo [4/5] Exporting Model-Ready CSVs for Power BI Desktop...
python src\export_powerbi_tables.py
if %ERRORLEVEL% NEQ 0 (
    echo Error exporting Power BI tables! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo [5/5] Executing Automated Validation Test Suite...
python tests\test_reconciliation.py
if %ERRORLEVEL% NEQ 0 (
    echo Tests failed! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo ====================================================================
echo Project 2 Demo Run Completed Successfully!
echo Excel Workbook: reports\AP_Invoice_Reconciliation_Workbook.xlsx
echo SQLite DB:      database\sap_procurement.db
echo Power BI Kit:   powerbi\ready_to_import_csv\
echo ====================================================================
pause
