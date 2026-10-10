@echo off
chcp 65001 >nul
title GPT 로컬 에이전트 설치
setlocal EnableExtensions
echo.
echo   GPT 로컬 에이전트 설치를 시작합니다...

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
  echo   설치가 끝까지 되지 않았습니다. 위 글을 캡처해서 보내 주세요.
  pause
)
exit /b %RC%

:nopy
echo.
echo   이 프로그램을 돌리려면 파이썬 3.10 이상이 필요한데 이 PC 에서 찾지 못했습니다.
echo.
where winget >nul 2>&1
if errorlevel 1 goto :nowinget
echo   파이썬을 자동으로 설치합니다. (몇 분 걸릴 수 있습니다)
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
echo.
echo   설치가 끝났으면 이 파일을 한 번 더 더블클릭해 주세요.
pause
exit /b 1

:nowinget
echo   자동 설치 도구(winget)도 없습니다. 아래 주소에서 파이썬을 받아 설치한 뒤,
echo   설치할 때 "Add python.exe to PATH" 에 체크하고 이 파일을 다시 더블클릭해 주세요.
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
