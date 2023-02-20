rem @echo off

setlocal

if [%1] == [] (set /a v = 1) else (set /a v = %1)

if [%2] == [] (set /a c = 1) else (set /a c = %2)
	
rem for /l %%i in (1,1,10) do python ./Code/client/client.py --testdownload

python ./Code/client/client.py --testdownload --subfolder client_%v% > ./Out/client_count_%c%/client_%v%.txt

for /l %%i in (1,1,9) do python ./Code/client/client.py --testdownload --subfolder client_%v% >> ./Out/client_count_%c%/client_%v%.txt

endlocal

if [%2] neq [] (exit)
