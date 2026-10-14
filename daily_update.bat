@echo off
cd /d "%~dp0"
if not defined PYTHON set PYTHON=python
"%PYTHON%" run.py --fetch-only --max-pages 5 >> update.log 2>&1
"%PYTHON%" run.py --extract >> update.log 2>&1
"%PYTHON%" run.py --analyze >> update.log 2>&1
"%PYTHON%" run.py --analyze-cross >> update.log 2>&1
