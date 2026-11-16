@echo off
REM ==============================================================================
REM Slow Brew Coffee Sales & Delivery Performance — Complete Demo Runner
REM Windows Batch Command (.bat)
REM ==============================================================================

echo ====================================================================
echo Starting Slow Brew Sales & Delivery Analytics Pipeline...
echo ====================================================================

echo [1/5] Generating 90-Day Synthetic POS and Zomato Data...
python src\generate_synthetic_data.py
if %ERRORLEVEL% NEQ 0 (
    echo Error generating synthetic data! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo [2/5] Running Data Cleaning, Deduplication, Rejection Logging, and SQLite Load...
python src\etl_and_load.py
if %ERRORLEVEL% NEQ 0 (
    echo Error during ETL and Load! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo [3/5] Generating Analytical CSV Reports and Excel Reconciliation Workbook...
python src\generate_excel_reconciliation.py
if %ERRORLEVEL% NEQ 0 (
    echo Error generating Excel reconciliation! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo [4/5] Exporting Clean Star-Schema CSVs for Power BI Desktop...
python src\export_powerbi_tables.py
if %ERRORLEVEL% NEQ 0 (
    echo Error exporting Power BI tables! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo [5/5] Executing Automated Validation Test Suite...
python tests\test_validation.py
if %ERRORLEVEL% NEQ 0 (
    echo Tests failed! Exiting.
    exit /b %ERRORLEVEL%
)

echo.
echo ====================================================================
echo Project 1 Demo Run Completed Successfully!
echo Excel Workbook: reports\Slow_Brew_Sales_Reconciliation.xlsx
echo SQLite DB:      database\slow_brew.db
echo Power BI Kit:   powerbi\ready_to_import_csv\
echo ====================================================================
pause
