@echo off

set PLAT="x86"
IF "%Platform%"=="x64" set PLAT="x64"

cl.exe /GS- /nologo /Od /Oi /c /Isrc src\unhook.c /Founhook.%PLAT%.o


@REM Includes Visual Studio header path headers

@REM set PLAT="x86"
@REM cl.exe /GS- /nologo /Od /Oi /c /Isrc /I"C:\Program Files (x86)\Windows Kits\10\Include\10.0.22000.0\um" /I"C:\Program Files (x86)\Windows Kits\10\Include\10.0.22000.0\shared" /I"C:\Program Files (x86)\Windows Kits\10\Include\10.0.22000.0\ucrt" src\unhook.c /Founhook.%PLAT%.o

@REM set PLAT="x64"
@REM cl.exe /GS- /nologo /Od /Oi /c /Isrc /I"C:\Program Files (x86)\Windows Kits\10\Include\10.0.22000.0\um" /I"C:\Program Files (x86)\Windows Kits\10\Include\10.0.22000.0\shared" /I"C:\Program Files (x86)\Windows Kits\10\Include\10.0.22000.0\ucrt" src\unhook.c /Founhook.%PLAT%.o


