@echo off
cd /d D:\Projects-macro-monitor
D:\Anaconda\python.exe run.py --fetch-only --max-pages 5 >> update.log 2>&1
D:\Anaconda\python.exe run.py --extract >> update.log 2>&1
D:\Anaconda\python.exe run.py --analyze >> update.log 2>&1
D:\Anaconda\python.exe run.py --analyze-cross >> update.log 2>&1
