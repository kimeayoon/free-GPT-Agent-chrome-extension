@echo off
chcp 65001 > nul
title GPT Local Agent server
cd /d "%~dp0..\서버"

echo.
echo   (Normally you do not need this. The server starts by itself when you open the side panel.)
echo   This is a manual switch for when automatic start does not work.
echo.
echo   Starting the GPT Local Agent server.
echo   Closing this window stops the server. Leave it open.
echo.

python -X utf8 서버.py

echo.
echo   The server has stopped. The reason is written above.
pause
