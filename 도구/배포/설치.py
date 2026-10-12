# -*- coding: utf-8 -*-
"""GPT Local Agent server installer — runs inside the one-file setup (GPT-LocalAgent-Server-Setup-<version>.cmd).

What it does (per-user only, no administrator rights needed):
  1. Unpacks the files to %LOCALAPPDATA%\\GPTLocalAgent (on update: replaces code, keeps your settings and chat data)
  2. Creates server/설정.json (settings) for this user (read/write scope = the user folder)
  3. Installs Pillow (for the image tools; optional), starts the server and makes it start at login
  4. Guides you through loading the Chrome extension (a separate download: GPT-LocalAgent-Extension-<version>.zip).
     If that zip sits next to this setup file, it is unpacked into the install folder for you.
  5. Copies the ChatGPT project instructions to the clipboard

  Uninstall: run uninstall.cmd in the install folder.

Options (for testing): --시험 (only unpack files; no registry/browser/server/pip)  --자리 <folder>  --yes (no prompts)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

이름 = "GPTLocalAgent"
실행키이름 = "GPTLocalAgent"
네이티브이름 = "com.local_agent.server"
묶음칸 = Path(__file__).resolve().parent
코드칸들 = ("서버", "문서", "도구")           # the extension ships as its own zip
릴리스주소 = "https://github.com/kimeayoon/free-GPT-Agent-chrome-extension/releases"
# Never overwrite these if they already exist (the user's settings, permissions, room list)
지킬것 = {"설정.json", "권한.json", "허용사이트.json", "방목록.json"}
제외 = {"__pycache__"}


def 말(글=""):
    print(글, flush=True)


def 묻기(글, 기본예=True, 자동=False):
    if 자동:
        return True
    답 = input(글 + (" [Enter=yes / n=no] " if 기본예 else " [y=yes / Enter=no] ")).strip().lower()
    return (답 != "n") if 기본예 else (답 == "y")


def 엔터기다리기(글, 자동=False):
    if not 자동:
        input(글)


def 설치자리(옵션) -> Path:
    if 옵션.자리:
        return Path(옵션.자리).resolve()
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / 이름


# ── 1. Unpack files ───────────────────────────────────────────────

def 파일풀기(대상: Path) -> int:
    수 = 0
    for 칸 in 코드칸들:
        원 = 묶음칸 / 칸
        if not 원.is_dir():
            continue
        for 파일 in 원.rglob("*"):
            if 파일.is_dir() or any(p in 제외 for p in 파일.parts):
                continue
            가는곳 = 대상 / 파일.relative_to(묶음칸)
            if 파일.name in 지킬것 and 가는곳.exists():
                continue
            가는곳.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(파일, 가는곳)
            수 += 1
    for 파일이름 in ("지침_붙여넣기.txt",):
        if (묶음칸 / 파일이름).exists():
            shutil.copy2(묶음칸 / 파일이름, 대상 / 파일이름)
    return 수


def 설정만들기(대상: Path) -> bool:
    """Create server/설정.json from the template if it does not exist yet. True if created."""
    자리 = 대상 / "서버" / "설정.json"
    if 자리.exists():
        return False
    템플릿 = (묶음칸 / "설정_템플릿.json").read_text(encoding="utf-8")
    집 = str(Path.home()).replace("\\", "/")
    설치 = str(대상).replace("\\", "/")
    글 = 템플릿.replace("{{HOME}}", 집).replace("{{INSTALL}}", 설치)
    json.loads(글)                       # stop here if it is broken
    자리.write_text(글, encoding="utf-8")
    return True


def 확장풀기(대상: Path) -> bool:
    """Unpack GPT-LocalAgent-Extension*.zip found next to the setup file into <install>/확장. True if unpacked."""
    import zipfile
    곁 = Path(os.environ.get("GPTA_SETUP_DIR") or 묶음칸)
    후보 = sorted(곁.glob("GPT-LocalAgent-Extension*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not 후보:
        return False
    확장칸 = 대상 / "확장"
    with zipfile.ZipFile(후보[0]) as 압축:
        이름들 = [n for n in 압축.namelist() if not n.endswith("/")]
        if not any(Path(n).name == "manifest.json" for n in 이름들):
            return False                    # not our extension zip
        shutil.rmtree(확장칸, ignore_errors=True)          # replace the old copy: stale files would stay loaded otherwise
        확장칸.mkdir(parents=True, exist_ok=True)
        for n in 이름들:                     # flatten the single top folder; names only, so nothing can escape 확장칸
            (확장칸 / Path(n).name).write_bytes(압축.read(n))
    return True


# ── 3. Server ─────────────────────────────────────────────────────

def 포트읽기(대상: Path) -> int:
    try:
        return int(json.loads((대상 / "서버" / "설정.json").read_text(encoding="utf-8")).get("포트", 8765))
    except Exception:
        return 8765


def 서버살았나(포트: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{포트}/ping", timeout=2) as 응:
            return 응.status == 200
    except Exception:
        return False


def 서버켜기(대상: Path) -> None:
    로그 = 대상 / "서버" / "서버출력.txt"
    플래그 = 0x08000000 | 0x00000008          # CREATE_NO_WINDOW | DETACHED_PROCESS
    with open(로그, "ab") as 파일:
        subprocess.Popen([sys.executable, "-X", "utf8", str(대상 / "서버" / "서버.py")], cwd=str(대상 / "서버"),
                         stdout=파일, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=플래그, close_fds=True)


def 숨겨켜기파일만들기(대상: Path) -> Path:
    """A tiny script that starts the server without a window at login (runs with Windows' own scripting host)."""
    파일 = 대상 / "서버숨겨켜기.vbs"
    본문 = (
        'Set sh = CreateObject("WScript.Shell")\r\n'
        f'sh.CurrentDirectory = "{대상 / "서버"}"\r\n'
        f'sh.Run """{sys.executable}"" -X utf8 ""{대상 / "서버" / "서버.py"}"" >> ""{대상 / "서버" / "서버출력.txt"}"" 2>&1", 0, False\r\n'
    )
    # wscript reads this file as ANSI (cp949 on Korean Windows)
    파일.write_bytes(본문.encode("mbcs", errors="replace"))
    return 파일


def 로그인켜기등록(vbs: Path) -> None:
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as 키:
        winreg.SetValueEx(키, 실행키이름, 0, winreg.REG_SZ, f'wscript.exe "{vbs}"')


def 필로우설치() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        끝 = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "pillow"],
                            capture_output=True, text=True, timeout=240)
        return 끝.returncode == 0
    except Exception:
        return False


# ── 4. Browser and clipboard ──────────────────────────────────────

def 클립보드에(글: str) -> bool:
    try:
        끝 = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Console]::InputEncoding=[Text.Encoding]::UTF8; Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
            input=글.encode("utf-8"), capture_output=True, timeout=30)
        return 끝.returncode == 0
    except Exception:
        return False


def 브라우저찾기() -> tuple:
    """(executable, name). Chrome first, then Edge."""
    import winreg
    for 이름_, 파일 in (("Chrome", "chrome.exe"), ("Edge", "msedge.exe")):
        for 뿌리 in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(뿌리, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{파일}") as 키:
                    값 = winreg.QueryValue(키, None)
                if 값 and Path(값).exists():
                    return 값, 이름_
            except OSError:
                pass
        for 기준 in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            루트 = os.environ.get(기준)
            if not 루트:
                continue
            후보 = Path(루트) / ("Google/Chrome/Application/chrome.exe" if 파일 == "chrome.exe" else "Microsoft/Edge/Application/msedge.exe")
            if 후보.exists():
                return str(후보), 이름_
    return "", ""


# ── Uninstall ─────────────────────────────────────────────────────

def 제거(옵션):
    대상 = 설치자리(옵션)
    말("\n  Uninstalling GPT Local Agent.")
    말(f"  Installed at: {대상}\n")
    if not 묻기("  Are you sure you want to uninstall?", 기본예=False, 자동=옵션.yes):
        말("  Cancelled.")
        return
    if os.name == "nt" and not 옵션.시험:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as 키:
                winreg.DeleteValue(키, 실행키이름)
            말("  OK  Removed the start-at-login entry.")
        except OSError:
            pass
        try:       # only if it points at this install
            자리 = rf"Software\Google\Chrome\NativeMessagingHosts\{네이티브이름}"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 자리) as 키:
                가리킴 = winreg.QueryValue(키, None)
            if str(대상).lower() in str(가리킴).lower():
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, 자리)
                말("  OK  Removed the Chrome auto-start registration.")
        except OSError:
            pass
        # Stop only this install's server: the process listening on its port whose command line has this folder name
        포트 = 포트읽기(대상)
        꼴 = ("\\" + 대상.name + "\\서버\\서버.py").replace("'", "''")
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Get-NetTCPConnection -LocalPort {포트} -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{ "
                        "$p = Get-CimInstance Win32_Process -Filter \"ProcessId=$($_.OwningProcess)\"; "
                        f"if ($p.CommandLine -like '*{꼴}*') {{ Stop-Process -Id $_.OwningProcess -Force }} }}"],
                       capture_output=True, timeout=30)
        time.sleep(1.0)
        말("  OK  Stopped the server.")
    기록 = 대상 / "서버" / "방"
    if 기록.exists() and not 묻기("  Also delete the chat history (server/방)? This cannot be undone.", 기본예=False, 자동=옵션.yes):
        for 칸 in 코드칸들:
            shutil.rmtree(대상 / 칸 / "__pycache__", ignore_errors=True)
        말(f"  Kept the history at {기록}. Only the code was left in place.")
        return
    shutil.rmtree(대상, ignore_errors=True)
    말("  OK  Deleted. Please also remove the 'GPT Local Agent' extension in chrome://extensions.")


# ── Install ───────────────────────────────────────────────────────

def 설치(옵션):
    if os.name != "nt":
        말("This installer is for Windows.")
        return 1
    대상 = 설치자리(옵션)
    자동 = 옵션.yes
    말("")
    말("  ==================================================")
    말("   GPT Local Agent - Setup")
    말("  ==================================================")
    말("")
    말("  This lets ChatGPT in your browser read and edit files and run commands on this PC.")
    말("  What ChatGPT asks for really happens on this computer. Please read what follows.")
    말("")
    말("  This setup will:")
    말(f"   - unpack its files to {대상}")
    말(f"   - limit reading/writing to your user folder ({Path.home()})")
    말("   - start a server that only listens on this PC (127.0.0.1) and start it at login")
    말("   - install Pillow for the image tools (optional)")
    말("   - show you how to load the browser extension (a separate download; you do this step yourself)")
    말("   - copy the ChatGPT project instructions to the clipboard")
    말("")
    말("  To remove it later: run uninstall.cmd in the install folder.")
    말("")
    if not 묻기("  Continue?", 기본예=True, 자동=자동):
        말("  Cancelled. Nothing was changed.")
        return 0

    말("\n[1/5] Unpacking files...")
    갯수 = 파일풀기(대상)
    (대상 / "workspace").mkdir(exist_ok=True)
    새설정 = 설정만들기(대상)
    말(f"  OK  {갯수} files - settings {'created' if 새설정 else 'kept as they were'}")
    try:
        확장풀림 = 확장풀기(대상)
    except Exception as e:
        확장풀림 = False
        말(f"  --  Could not unpack the extension zip ({e}).")
    if 확장풀림:
        말("  OK  Unpacked the extension zip found next to this setup file")
    제거파일 = 대상 / "uninstall.cmd"
    제거파일.write_bytes(
        ('@echo off\r\nchcp 65001 >nul\r\n'
         'where py >nul 2>&1 && (py -3 -X utf8 "%~dp0도구\\설치.py" --제거 --자리 "%~dp0.") || (python -X utf8 "%~dp0도구\\설치.py" --제거 --자리 "%~dp0.")\r\n'
         'pause\r\n').encode("utf-8"))

    if 옵션.시험:
        말("\n  (test mode: the server, registry, browser and installs were not touched)")
        return 0

    말("\n[2/5] Checking the image tools (Pillow)...")
    말("  OK  Ready" if 필로우설치() else "  --  Could not install it. Only the image/screen tools are unavailable; everything else works.")

    말("\n[3/5] Starting the server...")
    포트 = 포트읽기(대상)
    if 서버살았나(포트):
        말(f"  --  A server is already running (port {포트}). New code takes effect after you restart the PC.")
    else:
        서버켜기(대상)
        for _ in range(20):
            time.sleep(0.75)
            if 서버살았나(포트):
                break
        말("  OK  The server is running" if 서버살았나(포트) else
          f"  !!  The server did not start yet. See {대상 / '서버' / '서버출력.txt'}")
    try:
        로그인켜기등록(숨겨켜기파일만들기(대상))
        말("  OK  It will start automatically when you log in")
    except Exception as e:
        말(f"  --  Could not register start-at-login ({e}). If the server is not running, use 도구/서버 켜기.bat.")

    말("\n[4/5] Load the extension in Chrome (one time - you have to do this step yourself)")
    확장칸 = 대상 / "확장"
    if not (확장칸 / "manifest.json").exists():
        말("  --  The extension is a separate download. Get GPT-LocalAgent-Extension-<version>.zip from")
        말(f"        {릴리스주소}")
        말("      and unzip it (anywhere you will keep it). Use that folder in step 3 below.")
        확장칸 = None
    클립 = 클립보드에(str(확장칸)) if 확장칸 else False
    브라우저, 브라우저이름 = 브라우저찾기()
    if 브라우저:
        주소 = "chrome://extensions" if 브라우저이름 == "Chrome" else "edge://extensions"
        subprocess.Popen([브라우저, 주소])
    else:
        말("  --  Chrome was not found. Open Chrome yourself and go to chrome://extensions")
    if 확장칸:
        subprocess.Popen(["explorer", str(확장칸)])
    말("")
    말("   1) On the extensions page, turn on 'Developer mode' (top right)")
    말("   2) Click 'Load unpacked' (top left)")
    if 확장칸:
        말("   3) Choose this folder" + (" (the path is on your clipboard - paste it into the address bar with Ctrl+V)" if 클립 else ""))
        말(f"        {확장칸}")
    else:
        말("   3) Choose the folder you unzipped (the one that contains manifest.json)")
    말("   4) 'GPT Local Agent' should appear in the list")
    말("")
    엔터기다리기("  Press Enter after you have loaded the extension... ", 자동)
    등록 = 대상 / "도구" / "자동켜기등록.py"
    if 등록.exists():
        끝 = subprocess.run([sys.executable, "-X", "utf8", str(등록)], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=60)
        말("  OK  The extension can now start the server by itself" if 끝.returncode == 0 else
          "  --  Skipped the auto-start registration (fine: the server already starts at login)")

    말("\n[5/5] Copying the ChatGPT instructions")
    지침 = (대상 / "지침_붙여넣기.txt")
    if 지침.exists():
        복사됨 = 클립보드에(지침.read_text(encoding="utf-8"))
        말("  OK  The instructions are on your clipboard" if 복사됨 else f"  --  Could not copy. Open {지침} and copy all of it.")
    import webbrowser
    webbrowser.open("https://chatgpt.com/")
    말("")
    말("   1) In ChatGPT, create a new Project (any name)")
    말("   2) In the project's 'Instructions' box, paste with Ctrl+V and save")
    말("   3) Open a new chat inside that project, then click the extension icon ('GPT Local Agent') to open the side panel")
    말("   4) In the panel, pick a work folder with '+', then give ChatGPT a task")
    말("")
    말(f"  Installed at: {대상}")
    말("  Done. You can close this window.")
    엔터기다리기("  Press Enter to close... ", 자동)
    return 0


def main():
    인자 = argparse.ArgumentParser()
    인자.add_argument("--제거", "--uninstall", dest="제거", action="store_true")
    인자.add_argument("--시험", "--test", dest="시험", action="store_true")
    인자.add_argument("--yes", action="store_true")
    인자.add_argument("--자리", "--dir", dest="자리", default="")
    옵션 = 인자.parse_args()
    if 옵션.제거:
        제거(옵션)
        return 0
    return 설치(옵션)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        말("\n  Cancelled.")
        sys.exit(1)
