@echo off
REM Windows batch file to run Streamlit Waiting List App
REM Double-click this file to launch the app


cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run waiting_list_app.py
pause
