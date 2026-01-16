@echo off
echo ================================================
echo    SQL Assistant - Starting Application
echo ================================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    echo [INFO] Virtual environment created.
    echo.
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
echo.

REM Install/Update dependencies
echo [INFO] Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo [INFO] Dependencies installed.
echo.

REM Check if .env exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Please create a .env file with your GROQ_API_KEY
    pause
    exit /b 1
)

echo ================================================
echo    Starting Backend API Server (Port 8000)
echo ================================================
echo.

REM Start API in new window
start "SQL Assistant API" cmd /k "call .venv\Scripts\activate.bat && uvicorn api:app --reload --host 127.0.0.1 --port 8000"

REM Wait for API to start
echo [INFO] Waiting for API to start...
timeout /t 5 /nobreak > nul
echo.

echo ================================================
echo    Starting Frontend UI (Streamlit)
echo ================================================
echo.

REM Start Streamlit
streamlit run ui.py

REM If streamlit exits, keep window open
pause
