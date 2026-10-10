# -*- coding: utf-8 -*-
"""자동 켜기 등록 — 확장이 서버를 스스로 켤 수 있게 크롬에 알려 둔다. 한 번만 하면 된다.

하는 일 (전부 이 사용자 몫에만 쓴다. 관리자 권한 필요 없음):
  ① 크롬 프로필에서 이 확장의 ID 를 찾는다 (확장/ 폴더를 불러온 것)
  ② 서버/자동켜기/agent_host.bat · host.json 을 만든다
  ③ 레지스트리 HKCU\\Software\\Google\\Chrome\\NativeMessagingHosts\\com.local_agent.server
     에 host.json 자리를 적는다

  등록:  python 도구▸자동켜기등록.py
  해제:  python 도구▸자동켜기등록.py --지우기

다시 해야 할 때: 프로젝트 폴더를 옮겼거나, 확장을 지웠다가 다시 불러와 ID 가 바뀌었을 때.
"""

import argparse
import glob
import json
import os
import sys
import winreg
from pathlib import Path

이름 = "com.local_agent.server"
레지스트리자리 = rf"Software\Google\Chrome\NativeMessagingHosts\{이름}"

뿌리 = Path(__file__).resolve().parent.parent
확장칸 = 뿌리 / "확장"
켜기칸 = 뿌리 / "서버" / "자동켜기"
배치파일 = 켜기칸 / "agent_host.bat"
설명파일 = 켜기칸 / "host.json"


def 확장아이디찾기() -> list[str]:
    """크롬 프로필마다 이 확장/ 폴더를 불러온 확장의 ID 를 모은다."""
    크롬 = Path(os.environ["LOCALAPPDATA"]) / "Google" / "Chrome" / "User Data"
    찾은것 = set()
    같은자리 = os.path.normcase(str(확장칸))
    for 파일 in (glob.glob(str(크롬 / "*" / "Secure Preferences"))
                 + glob.glob(str(크롬 / "*" / "Preferences"))):
        try:
            with open(파일, encoding="utf-8") as f:
                설정 = json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        for 번호, 값 in ((설정.get("extensions") or {}).get("settings") or {}).items():
            자리 = (값 or {}).get("path") or ""
            if 자리 and os.path.normcase(자리) == 같은자리:
                찾은것.add(번호)
    return sorted(찾은것)


def 등록():
    아이디들 = 확장아이디찾기()
    if not 아이디들:
        print("ERROR: This extension was not found in Chrome.")
        print(f"  In chrome://extensions use 'Load unpacked' and choose {확장칸} first, then run this again.")
        raise SystemExit(1)

    켜기칸.mkdir(parents=True, exist_ok=True)

    # stdio 로 크롬과 말해야 하므로 창 없는 pythonw 가 아니라 python 을 쓴다.
    # (크롬이 숨긴 채로 띄우므로 창은 안 뜬다)
    파이썬 = Path(sys.executable)
    if 파이썬.name.lower() == "pythonw.exe":
        파이썬 = 파이썬.with_name("python.exe")

    # 배치 파일 안에는 한글을 두지 않는다. cmd 가 코드페이지에 따라 깨뜨린다.
    # 자기 자리는 %~dp0 로 받는다(cmd 가 속으로 유니코드로 다룬다).
    배치파일.write_text(
        "@echo off\r\n"
        f'"{파이썬}" -X utf8 "%~dp0agent_host.py" %*\r\n',
        encoding="ascii",
    )

    설명 = {
        "name": 이름,
        "description": "로컬 에이전트 서버 자동 켜기",
        "path": str(배치파일),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{i}/" for i in 아이디들],
    }
    설명파일.write_text(json.dumps(설명, ensure_ascii=False, indent=2), encoding="utf-8")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, 레지스트리자리) as 열쇠:
        winreg.SetValueEx(열쇠, "", 0, winreg.REG_SZ, str(설명파일))

    print("OK: Auto-start registered.")
    print(f"  Extension ID : {', '.join(아이디들)}")
    print(f"  Python       : {파이썬}")
    print(f"  Host file    : {설명파일}")
    print(f"  Registry     : HKCU\\{레지스트리자리}")
    print("  Reload the extension; the server will then start by itself when you open the side panel.")


def 지우기():
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, 레지스트리자리)
        print("OK: Removed from the registry.")
    except FileNotFoundError:
        print("It was not registered.")
    print(f"  (The files are kept: {켜기칸})")


if __name__ == "__main__":
    받개 = argparse.ArgumentParser()
    받개.add_argument("--지우기", "--remove", dest="지우기", action="store_true")
    인자 = 받개.parse_args()
    지우기() if 인자.지우기 else 등록()
