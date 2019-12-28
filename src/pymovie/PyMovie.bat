@echo off
cd C:\Anaconda3

echo Creating run-pymovie.py in C:\Anaconda3

@echo from pymovie import main > run-pymovie.py
@echo main.main() >> run-pymovie.py

echo.
echo Activating the base Anaconda environment

call C:\Anaconda3\Scripts\activate.bat

echo.
echo Executing the run-pymovie.py script

python C:\Anaconda3\run-pymovie.py

set /p stuff="Press Enter to exit: "