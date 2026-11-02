@echo off
echo Starting Class Notes RAG Assistant (Backend + Frontend)...
start "Class Notes Backend" cmd /k "%~dp0run_backend.bat"
timeout /t 3 /nobreak >nul
start "Class Notes Frontend" cmd /k "%~dp0run_frontend.bat"
echo Both servers started!
echo Frontend will be available at http://localhost:3000
echo Backend API will be available at http://127.0.0.1:8000
