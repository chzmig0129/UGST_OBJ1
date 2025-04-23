@echo off
cd C:\Users\migue\Documents\VALGEOUGST
call venv_new\Scripts\activate
python check_fitz.py > fitz_report.txt
echo Diagnóstico completado. Revisa el archivo fitz_report.txt
pause 