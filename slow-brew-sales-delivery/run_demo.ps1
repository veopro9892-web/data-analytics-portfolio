# ==============================================================================
# Slow Brew Coffee Sales & Delivery Performance — PowerShell Demo Runner
# ==============================================================================

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "Starting Slow Brew Sales & Delivery Analytics Pipeline..." -ForegroundColor Cyan
Write-Host "===================================================================="

Write-Host "`n[1/5] Generating 90-Day Synthetic POS and Zomato Data..." -ForegroundColor Yellow
python src\generate_synthetic_data.py
if ($LASTEXITCODE -ne 0) { throw "Data generation failed!" }

Write-Host "`n[2/5] Running Data Cleaning, Deduplication, Rejection Logging, and SQLite Load..." -ForegroundColor Yellow
python src\etl_and_load.py
if ($LASTEXITCODE -ne 0) { throw "ETL failed!" }

Write-Host "`n[3/5] Generating Analytical CSV Reports and Excel Reconciliation Workbook..." -ForegroundColor Yellow
python src\generate_excel_reconciliation.py
if ($LASTEXITCODE -ne 0) { throw "Excel generation failed!" }

Write-Host "`n[4/5] Exporting Clean Star-Schema CSVs for Power BI Desktop..." -ForegroundColor Yellow
python src\export_powerbi_tables.py
if ($LASTEXITCODE -ne 0) { throw "Power BI export failed!" }

Write-Host "`n[5/5] Executing Automated Validation Test Suite..." -ForegroundColor Yellow
python tests\test_validation.py
if ($LASTEXITCODE -ne 0) { throw "Validation tests failed!" }

Write-Host "`n====================================================================" -ForegroundColor Green
Write-Host "Project 1 Demo Run Completed Successfully!" -ForegroundColor Green
Write-Host "Excel Workbook: reports\Slow_Brew_Sales_Reconciliation.xlsx"
Write-Host "SQLite DB:      database\slow_brew.db"
Write-Host "Power BI Kit:   powerbi\ready_to_import_csv\"
Write-Host "===================================================================="
