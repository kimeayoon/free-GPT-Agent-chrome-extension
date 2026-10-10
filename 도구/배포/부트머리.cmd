@echo off
chcp 65001 >nul
title GPT Local Agent - Setup
setlocal EnableExtensions
echo.
echo   Starting GPT Local Agent setup...

set "PYX="
for %%C in ("py -3" "python" "python3") do (
  if not defined PYX (
    %%~C -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1 && set "PYX=%%~C"
  )
)
if not defined PYX goto :nopy

%PYX% -X utf8 -c "import sys;t=open(sys.argv[1],encoding='utf-8').read();exec(compile(t.split('#BOOT-PY\n',1)[1].split('#BOOT-END\n',1)[0],'boot','exec'))" "%~f0" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo   Setup did not finish. Please take a screenshot of the text above and send it to the person who gave you this file.
  pause
)
exit /b %RC%

:nopy
echo.
echo   Python 3.10 or newer is required, but it was not found on this PC.
echo.
where winget >nul 2>&1
if errorlevel 1 goto :nowinget
echo   Installing Python automatically. This can take a few minutes.
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
echo.
echo   When the installation has finished, double-click this file once more.
pause
exit /b 1

:nowinget
echo   The automatic installer (winget) is not available either.
echo   Please download Python from the address below, and during setup tick "Add python.exe to PATH".
echo   Then double-click this file again.
echo.
echo       https://www.python.org/downloads/
start "" "https://www.python.org/downloads/"
pause
exit /b 1

#BOOT-PY
import base64, io, os, runpy, sys, tempfile, zipfile
원 = open(sys.argv[1], encoding='utf-8').read()
짐 = 원.split('#PAYLOAD\n', 1)[1]
임시 = tempfile.mkdtemp(prefix='gpta_')
zipfile.ZipFile(io.BytesIO(base64.b64decode(짐))).extractall(임시)
sys.argv = [os.path.join(임시, '_설치.py')] + sys.argv[2:]
sys.path.insert(0, 임시)
runpy.run_path(sys.argv[0], run_name='__main__')
#BOOT-END
