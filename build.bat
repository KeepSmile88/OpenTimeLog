@echo off
set PY=python.exe

set CERT_NAME=Smiley Software
set CERT_PFX=smiley.pfx
set CERT_PASS=123456

echo ===== Building Manager with Nuitka =====

python.exe -m nuitka main.py ^
    --standalone ^
    --follow-imports ^
    --plugin-enable=pyside6 ^
    --include-qt-plugins=platforms ^
    --lto=yes ^
    --include-qt-plugins=styles ^
    --windows-icon-from-ico=.\app_icon.ico ^
    --remove-output ^
    --assume-yes-for-downloads ^
    --windows-console-mode=disable ^
    --output-filename=add_video_marker.exe ^
    --windows-company-name="%CERT_NAME%" ^
    --windows-product-name="ATimeLogPro" ^
    --windows-file-description="ATimeLogPro Application" ^
    --windows-file-version="2.1.0" ^
    --windows-product-version="2.1.0"
    
::     ::--windows-console-mode=disable

echo.
echo ===== Nuitka Build Completed: manager.dist =====

for %%f in (main.dist\*.exe) do (
    signtool sign ^
        /f %CERT_PFX% ^
        /p %CERT_PASS% ^
        /tr http://timestamp.digicert.com ^
        /td sha256 ^
        /fd sha256 ^
        "%%f"
)

pause
