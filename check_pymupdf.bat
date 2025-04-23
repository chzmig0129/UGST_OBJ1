@echo off
cd C:\Users\migue\Documents\VALGEOUGST
call venv_new\Scripts\activate
python check_pymupdf.py > pymupdf_report.txt
echo Diagnóstico completado. Revisa el archivo pymupdf_report.txt
pause 