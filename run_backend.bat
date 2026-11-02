@echo off
title Class Notes RAG Backend (FastAPI)
echo Starting FastAPI Backend on http://127.0.0.1:8000 ...
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
