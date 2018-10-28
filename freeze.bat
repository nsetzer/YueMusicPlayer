::#! call $this
:: this file will create a standalone exe file in the --onefile configuration

@echo off

cd %~dp0

:: add --debug build a console application
C:\Python37\Scripts\pyinstaller yue.spec