@echo off
setlocal
echo Checking for FFmpeg...

:: 1. Check if already in PATH
where ffmpeg >nul 2>nul
if %errorlevel% equ 0 (
    echo FFmpeg is already in your PATH.
    ffmpeg -version | findstr "version"
    goto :Done
)

:: 2. Search common locations (e.g., C:\ffmpeg, Program Files)
echo FFmpeg not found in PATH. Searching common locations...

set "FOUND_PATH="
if exist "C:\ffmpeg\bin\ffmpeg.exe" set "FOUND_PATH=C:\ffmpeg\bin"
if exist "C:\Program Files\ffmpeg\bin\ffmpeg.exe" set "FOUND_PATH=C:\Program Files\ffmpeg\bin"
:: Add more paths if known

if defined FOUND_PATH (
    echo Found FFmpeg at: %FOUND_PATH%
    echo Adding to PATH for this session...
    set "PATH=%PATH%;%FOUND_PATH%"
    
    :: Option to add permanently?
    choice /M "Do you want to add this to your SYSTEM PATH permanently?"
    if %errorlevel% equ 1 (
        echo Adding to User Environment PATH...
        setx PATH "%PATH%;%FOUND_PATH%"
        echo Done. Please restart your terminal/apps.
    )
) else (
    echo FFmpeg not found in common locations.
    echo Please install FFmpeg or extract it to C:\ffmpeg
)

:Done
pause
