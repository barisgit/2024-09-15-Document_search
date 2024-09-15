@echo off

echo Creating virtual environment...
python -m venv .venv

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Creating .env file...
(
echo DOC_DIR=./documents
echo INDEX_DIR=./index
) > .env

echo Creating directories...
if not exist "documents" mkdir documents
if not exist "index" mkdir index

echo Setup complete!
echo To activate the virtual environment, run:
echo   .venv\Scripts\activate.bat