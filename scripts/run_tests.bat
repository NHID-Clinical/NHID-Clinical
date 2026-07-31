@echo off
echo Installing dependencies...
python -m pip install -r requirements.txt -q
echo.
echo Running tests...
python -m pytest tests/ -v
pause
