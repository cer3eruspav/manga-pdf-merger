@echo off
chcp 65001 >nul

:: Check if files were dragged and dropped
if "%~1"=="" goto wait_drop

:: Pass all file paths to Python with quotes to prevent path breaking
py -3 "%~dp0merge_manga.py" %*

:wait_drop
echo.
echo --------------------------------------------------
echo  Processing complete! Countdown to close the window...
echo  (If you drag and drop a new set of files now, it will merge them automatically)
echo --------------------------------------------------

:: 10-second countdown
for /L %%i in (10,-1,1) do (
    <nul set /p "=  > Closing in %%i seconds...    "
    timeout /t 1 /nobreak >nul
)

echo.
echo Program closed. Thank you!
