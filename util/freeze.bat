::#! call $this
:: this file will create a standalone exe file in the --onefile configuration

@echo off

cd %~dp0/src

C:\Python34\Scripts\pyinstaller yue.spec --debug
