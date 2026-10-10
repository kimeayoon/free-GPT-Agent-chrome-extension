@echo off
chcp 65001 > nul
title 로컬 에이전트 서버
cd /d "%~dp0..\서버"

echo.
echo   (보통은 필요 없습니다. 판을 열면 서버가 스스로 켜집니다.)
echo   자동 켜기가 안 될 때만 쓰는 손잡이입니다.
echo.
echo   로컬 에이전트 서버를 켭니다.
echo   이 창을 닫으면 서버도 꺼집니다. 켜 둔 채로 두세요.
echo.

python -X utf8 서버.py

echo.
echo   서버가 멈췄습니다. 위에 이유가 적혀 있습니다.
pause
