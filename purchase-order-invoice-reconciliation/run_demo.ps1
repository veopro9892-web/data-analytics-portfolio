# ==============================================================================
# SAP 3-Way Match Procurement Reconciliation — PowerShell Demo Runner
# ==============================================================================

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "Starting SAP Procurement 3-Way Match Reconciliation Pipeline..." -ForegroundColor Cyan
Write-Host "===================================================================="

Write-Host "`n[1/5] Generating Deterministic SAP Procurement Data & Benchmark Fixtures..." -ForegroundColor Yellow
python src\generate_sap_data.py
if ($LASTEXITCODE -ne 0) { throw "Data generation failed!" }

Write-Host "`n[2/5] Loading SQLite Database & Executing Independent Aggregation Match..." -ForegroundColor Yellow
python src\load_database.py
if ($LASTEXITCODE -ne 0) { throw "Database loading failed!" }

Write-Host "`n[3/5] Generating Analytical CSV Reports and Excel AP Review Workbook..." -ForegroundColor Yellow
python src\generate_excel_review.py
if ($LASTEXITCODE -ne 0) { throw "Excel workbook generation failed!" }

Write-Host "`n[4/5] Exporting Model-Ready CSVs for Power BI Desktop..." -ForegroundColor Yellow
python src\export_powerbi_tables.py
if ($LASTEXITCODE -ne 0) { throw "Power BI export failed!" }

Write-Host "`n[5/5] Executing Automated Validation Test Suite..." -ForegroundColor Yellow
python tests\test_reconciliation.py
if ($LASTEXITCODE -ne 0) { throw "Reconciliation validation tests failed!" }

Write-Host "`n====================================================================" -ForegroundColor Green
Write-Host "Project 2 Demo Run Completed Successfully!" -ForegroundColor Green
Write-Host "Excel Workbook: reports\AP_Invoice_Reconciliation_Workbook.xlsx"
Write-Host "SQLite DB:      database\sap_procurement.db"
Write-Host "Power BI Kit:   powerbi\ready_to_import_csv\"
Write-Host "===================================================================="
