# -*- coding: utf-8 -*-
"""GPT 로컬 에이전트 설치 프로그램 — 한 파일 배포본(GPT로컬에이전트_설치.cmd) 안에서 돈다.

하는 일(전부 이 사용자 몫에만 쓴다 · 관리자 권한 필요 없음):
  ① 파일을 %LOCALAPPDATA%\\GPTLocalAgent 에 푼다(이미 있으면 코드만 바꾸고 설정 · 대화 기록은 둔다)
  ② 설정.json 을 이 사용자 기준으로 만든다(읽고 쓸 수 있는 범위 = 사용자 폴더)
  ③ Pillow(그림 도구용, 없어도 됨)를 설치하고 서버를 켠다 · 로그인할 때 저절로 켜지게 한다
  ④ 크롬에서 확장 불러오는 것을 안내한다(크롬 규칙상 이 한 단계는 사람이 해야 한다)
  ⑤ ChatGPT 프로젝트에 넣을 지침을 클립보드에 복사한다

  제거: 설치된 곳의 제거.cmd

옵션(시험·점검용): --시험(레지스트리·크롬·서버 켜기·설치를 안 건드리고 파일만 푼다) --자리 <폴더> --yes(묻지 않음)
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
코드칸들 = ("서버", "확장", "문서", "도구")
# 이미 있으면 덮어쓰지 않는다(사용자의 설정 · 허락 · 방 목록)
지킬것 = {"설정.json", "권한.json", "허용사이트.json", "방목록.json"}
제외 = {"__pycache__"}


def 말(글=""):
    print(글, flush=True)


def 묻기(글, 기본예=True, 자동=False):
    if 자동:
        return True
    답 = input(글 + (" [Enter=예 / n=아니오] " if 기본예 else " [y=예 / Enter=아니오] ")).strip().lower()
    return (답 != "n") if 기본예 else (답 == "y")


def 엔터기다리기(글, 자동=False):
    if not 자동:
        input(글)


def 설치자리(옵션) -> Path:
    if 옵션.자리:
        return Path(옵션.자리).resolve()
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / 이름


# ── ① 파일 풀기 ───────────────────────────────────────────────────

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
    """서버/설정.json 이 없으면 템플릿으로 만든다. 만들었으면 True."""
    자리 = 대상 / "서버" / "설정.json"
    if 자리.exists():
        return False
    템플릿 = (묶음칸 / "설정_템플릿.json").read_text(encoding="utf-8")
    집 = str(Path.home()).replace("\\", "/")
    설치 = str(대상).replace("\\", "/")
    글 = 템플릿.replace("{{HOME}}", 집).replace("{{INSTALL}}", 설치)
    json.loads(글)                       # 깨졌으면 여기서 멈춘다
    자리.write_text(글, encoding="utf-8")
    return True


# ── ③ 서버 ───────────────────────────────────────────────────────

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
    """로그인할 때 서버를 창 없이 켜는 작은 스크립트(윈도우 기본 앱으로 돈다)."""
    파일 = 대상 / "서버숨겨켜기.vbs"
    본문 = (
        'Set sh = CreateObject("WScript.Shell")\r\n'
        f'sh.CurrentDirectory = "{대상 / "서버"}"\r\n'
        f'sh.Run """{sys.executable}"" -X utf8 ""{대상 / "서버" / "서버.py"}"" >> ""{대상 / "서버" / "서버출력.txt"}"" 2>&1", 0, False\r\n'
    )
    # wscript 는 이 파일을 ANSI(한국어 윈도우면 cp949)로 읽는다
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


# ── ④ 크롬 · 클립보드 ─────────────────────────────────────────────

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
    """(실행 파일, 이름). 크롬을 먼저, 없으면 엣지."""
    import winreg
    for 이름_, 파일 in (("크롬", "chrome.exe"), ("엣지", "msedge.exe")):
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


# ── 제거 ─────────────────────────────────────────────────────────

def 제거(옵션):
    대상 = 설치자리(옵션)
    말("\n  GPT 로컬 에이전트를 제거합니다.")
    말(f"  설치된 곳: {대상}\n")
    if not 묻기("  정말 제거할까요?", 기본예=False, 자동=옵션.yes):
        말("  취소했습니다.")
        return
    if os.name == "nt" and not 옵션.시험:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as 키:
                winreg.DeleteValue(키, 실행키이름)
            말("  ✓ 로그인 때 저절로 켜지는 것을 뺐습니다.")
        except OSError:
            pass
        try:       # 이 설치를 가리키는 것일 때만 지운다
            자리 = rf"Software\Google\Chrome\NativeMessagingHosts\{네이티브이름}"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 자리) as 키:
                가리킴 = winreg.QueryValue(키, None)
            if str(대상).lower() in str(가리킴).lower():
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, 자리)
                말("  ✓ 크롬 자동 켜기 등록을 지웠습니다.")
        except OSError:
            pass
        # 이 설치의 서버만 끈다: 포트를 듣는 프로세스 중 명령줄에 설치 폴더가 든 것
        포트 = 포트읽기(대상)
        # 명령줄에는 긴 경로 · 짧은 경로(RALLOS~1) 어느 꼴로든 적혀 있어 경로 전체를 맞대면 어긋난다.
        # 그래서 '설치폴더이름\서버\서버.py' 꼴로 본다(이 설치의 서버만 걸린다).
        꼴 = ("\\" + 대상.name + "\\서버\\서버.py").replace("'", "''")
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Get-NetTCPConnection -LocalPort {포트} -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{ "
                        "$p = Get-CimInstance Win32_Process -Filter \"ProcessId=$($_.OwningProcess)\"; "
                        f"if ($p.CommandLine -like '*{꼴}*') {{ Stop-Process -Id $_.OwningProcess -Force }} }}"],
                       capture_output=True, timeout=30)
        time.sleep(1.0)
        말("  ✓ 서버를 껐습니다.")
    기록 = 대상 / "서버" / "방"
    if 기록.exists() and not 묻기("  대화 기록(서버/방)도 같이 지울까요? 지우면 되돌릴 수 없습니다.", 기본예=False, 자동=옵션.yes):
        for 칸 in 코드칸들:
            shutil.rmtree(대상 / 칸 / "__pycache__", ignore_errors=True)
        말(f"  코드만 두고 갑니다. 기록은 {기록} 에 남습니다.")
        return
    shutil.rmtree(대상, ignore_errors=True)
    말("  ✓ 지웠습니다. 크롬의 chrome://extensions 에서 'GPT Local Agent' 확장도 직접 지워 주세요.")


# ── 설치 ─────────────────────────────────────────────────────────

def 설치(옵션):
    if os.name != "nt":
        말("이 설치 프로그램은 윈도우용입니다.")
        return 1
    대상 = 설치자리(옵션)
    자동 = 옵션.yes
    말("")
    말("  ╔════════════════════════════════════════════════════╗")
    말("  ║   GPT 로컬 에이전트 설치                           ║")
    말("  ╚════════════════════════════════════════════════════╝")
    말("")
    말("  ChatGPT 웹 대화창이 이 PC 의 파일을 읽고 고치고 명령을 돌리게 해 주는 도구입니다.")
    말("  ChatGPT 가 시키는 일은 이 PC 에서 실제로 일어납니다. 아래를 확인하고 진행하세요.")
    말("")
    말("  이 설치가 하는 일")
    말(f"   · 파일을 {대상} 에 풉니다")
    말(f"   · 읽고 쓸 수 있는 범위를 사용자 폴더({Path.home()}) 안으로 정합니다")
    말("   · 이 PC 안(127.0.0.1)에서만 도는 서버를 켜고, 로그인할 때 저절로 켜지게 합니다")
    말("   · 그림 도구용 Pillow 를 설치합니다(없어도 동작)")
    말("   · 크롬에 확장을 불러오는 방법을 안내합니다(직접 해야 합니다)")
    말("   · ChatGPT 프로젝트에 붙여넣을 지침을 클립보드에 복사합니다")
    말("")
    말("  지우려면: 설치된 곳의 제거.cmd")
    말("")
    if not 묻기("  진행할까요?", 기본예=True, 자동=자동):
        말("  취소했습니다. 아무것도 바꾸지 않았습니다.")
        return 0

    말("\n[1/5] 파일을 풉니다…")
    갯수 = 파일풀기(대상)
    (대상 / "workspace").mkdir(exist_ok=True)
    새설정 = 설정만들기(대상)
    말(f"  ✓ {갯수}개 파일 · 설정 {'새로 만듦' if 새설정 else '기존 것 그대로'}")
    제거파일 = 대상 / "제거.cmd"
    제거파일.write_bytes(
        ('@echo off\r\nchcp 65001 >nul\r\n'
         'where py >nul 2>&1 && (py -3 -X utf8 "%~dp0도구\\설치.py" --제거 --자리 "%~dp0.") || (python -X utf8 "%~dp0도구\\설치.py" --제거 --자리 "%~dp0.")\r\n'
         'pause\r\n').encode("utf-8"))

    if 옵션.시험:
        말("\n  (시험 모드: 서버·레지스트리·크롬·설치는 건드리지 않았습니다)")
        return 0

    말("\n[2/5] 그림 도구(Pillow)를 확인합니다…")
    말("  ✓ 준비됨" if 필로우설치() else "  · 설치하지 못했습니다. 그림·화면 도구만 못 쓰고 나머지는 됩니다.")

    말("\n[3/5] 서버를 켭니다…")
    포트 = 포트읽기(대상)
    if 서버살았나(포트):
        말(f"  · 이미 서버가 돌고 있습니다(포트 {포트}). 새 코드는 PC 를 다시 시작하면 적용됩니다.")
    else:
        서버켜기(대상)
        for _ in range(20):
            time.sleep(0.75)
            if 서버살았나(포트):
                break
        말("  ✓ 서버가 켜졌습니다" if 서버살았나(포트) else
          f"  ✗ 서버가 아직 안 뜹니다. {대상 / '서버' / '서버출력.txt'} 를 보세요.")
    try:
        로그인켜기등록(숨겨켜기파일만들기(대상))
        말("  ✓ 로그인할 때 저절로 켜지게 했습니다")
    except Exception as e:
        말(f"  · 저절로 켜기 등록을 못 했습니다({e}). 켜져 있지 않으면 도구/서버 켜기.bat 를 쓰세요.")

    말("\n[4/5] 크롬에 확장을 불러옵니다 (한 번만, 직접 해야 하는 단계입니다)")
    확장칸 = 대상 / "확장"
    클립 = 클립보드에(str(확장칸))
    브라우저, 브라우저이름 = 브라우저찾기()
    if 브라우저:
        주소 = "chrome://extensions" if 브라우저이름 == "크롬" else "edge://extensions"
        subprocess.Popen([브라우저, 주소])
    else:
        말("  · 크롬을 못 찾았습니다. 크롬을 직접 열고 주소창에 chrome://extensions 를 치세요.")
    subprocess.Popen(["explorer", str(확장칸)])
    말("")
    말("   ① 열린 확장 프로그램 페이지의 오른쪽 위 '개발자 모드' 를 켭니다")
    말("   ② 왼쪽 위 '압축해제된 확장 프로그램을 로드' 를 누릅니다")
    말("   ③ 폴더 선택 창에서 아래 폴더를 고릅니다" + (" (경로를 클립보드에 복사해 뒀습니다 — 주소줄에 Ctrl+V)" if 클립 else ""))
    말(f"        {확장칸}")
    말("   ④ 'GPT Local Agent' 가 목록에 뜨면 성공입니다")
    말("")
    엔터기다리기("  확장을 불러왔으면 Enter 를 누르세요… ", 자동)
    등록 = 대상 / "도구" / "자동켜기등록.py"
    if 등록.exists():
        끝 = subprocess.run([sys.executable, "-X", "utf8", str(등록)], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=60)
        말("  ✓ 확장이 서버를 스스로 켜게 등록했습니다" if 끝.returncode == 0 else
          "  · 자동 켜기 등록은 건너뜁니다(로그인할 때 켜지므로 괜찮습니다)")

    말("\n[5/5] ChatGPT 지침을 복사합니다")
    지침 = (대상 / "지침_붙여넣기.txt")
    if 지침.exists():
        복사됨 = 클립보드에(지침.read_text(encoding="utf-8"))
        말("  ✓ 지침을 클립보드에 복사했습니다" if 복사됨 else f"  · 복사하지 못했습니다. {지침} 를 열어 전부 복사하세요.")
    import webbrowser
    webbrowser.open("https://chatgpt.com/")
    말("")
    말("   ① ChatGPT 에서 '새 프로젝트' 를 만듭니다(이름은 아무거나)")
    말("   ② 프로젝트 화면의 '지침'(또는 '지침 추가') 칸에 Ctrl+V 로 붙여넣고 저장합니다")
    말("   ③ 그 프로젝트 안에서 새 대화를 열고, 크롬 오른쪽 위 퍼즐 → 'GPT Local Agent' 를 눌러 옆 판을 엽니다")
    말("   ④ 판의 '＋' 로 일할 폴더를 고른 뒤 ChatGPT 에 일을 시키면 됩니다")
    말("")
    말(f"  설치된 곳: {대상}")
    말("  끝났습니다. 이 창은 닫아도 됩니다.")
    엔터기다리기("  Enter 로 닫기… ", 자동)
    return 0


def main():
    인자 = argparse.ArgumentParser()
    인자.add_argument("--제거", action="store_true")
    인자.add_argument("--시험", action="store_true")
    인자.add_argument("--yes", action="store_true")
    인자.add_argument("--자리", default="")
    옵션 = 인자.parse_args()
    if 옵션.제거:
        제거(옵션)
        return 0
    return 설치(옵션)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        말("\n  취소했습니다.")
        sys.exit(1)
