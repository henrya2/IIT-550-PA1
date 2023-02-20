rem @echo off
setlocal

if [%1] == [] (set /a v = 1) else (set /a v = %1)

for /l %%i in (1,1, %v%) do start test_single_client.bat %%i %v%

endlocal