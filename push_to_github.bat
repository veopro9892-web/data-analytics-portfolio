@echo off
cd /d "C:\Users\Vinayak80800\Desktop\project"
echo Pushing portfolio to GitHub (https://github.com/veopro9892-web/data-analytics-portfolio)...
echo If a GitHub sign-in window appears, click "Sign in with your browser" or "Authorize".
echo.
git push -u origin main
echo.
if %ERRORLEVEL% EQU 0 (
    echo ====================================================================
    echo Successfully pushed to GitHub!
    echo Visit: https://github.com/veopro9892-web/data-analytics-portfolio
    echo ====================================================================
) else (
    echo ====================================================================
    echo Push did not complete. Please check the error message above.
    echo ====================================================================
)
pause
