# -*- coding: utf-8 -*-
"""깃허브에 올려도 되는 파일만 모은 폴더(도구/배포/깃허브용/)를 만든다.

넣는 것: 서버 코드 · 확장 · 지침 문서 3개 · 도구(설치·시험 포함) · README · .gitignore
뺀 것  : 대화 기록(서버/방) · 설정 · 권한 · 허용 사이트 · 로그 · 작업기록 · 백업 · workspace · _archive
만들 때 내 경로·메일 같은 개인 자료가 글에 섞여 있으면 멈추고 알려 준다.

  만들기:  python -X utf8 도구/배포/깃허브폴더만들기.py
  결과:    도구/배포/깃허브용/   (이 폴더 안의 것을 GitHub 에 올린다)
"""

import io
import shutil
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent.parent
이칸 = Path(__file__).resolve().parent
나가는곳 = 이칸 / "깃허브용"

def 개인글만들기() -> list:
    """이 PC 의 사용자 이름과 이 프로젝트 · 사용자 폴더 경로. 이 글이 파일에 들어 있으면 개인 자료가 섞인 것이다.
    (이름을 코드에 박아 두지 않는다 — 박으면 이 파일 자체가 개인 자료가 된다.)"""
    import os
    글 = {str(뿌리), str(뿌리).replace(chr(92), "/"), str(Path.home()), str(Path.home()).replace(chr(92), "/")}
    for 이름 in (os.environ.get("USERNAME"), os.environ.get("USER"), Path.home().name):
        if 이름 and len(이름) >= 4:
            글.add(이름)
    return sorted(g for g in 글 if g)


문서목록 = ("프로토콜.md", "에이전트_설명서.md", "도구_첫사용_안내.md")


def 모으기() -> list:
    """(올릴 상대 경로, 원본 경로)"""
    나온 = []
    for 파일 in sorted((뿌리 / "서버").glob("*.py")):
        나온.append((f"서버/{파일.name}", 파일))
    호스트 = 뿌리 / "서버" / "자동켜기" / "agent_host.py"
    if 호스트.exists():
        나온.append(("서버/자동켜기/agent_host.py", 호스트))
    for 파일 in sorted((뿌리 / "확장").iterdir()):
        if 파일.is_file():
            나온.append((f"확장/{파일.name}", 파일))
    for 이름 in 문서목록:
        나온.append((f"문서/{이름}", 뿌리 / "문서" / 이름))
    for 파일 in sorted((뿌리 / "도구").glob("*")):
        if 파일.is_file() and 파일.suffix in (".py", ".bat"):
            나온.append((f"도구/{파일.name}", 파일))
    for 이름 in ("설치.py", "부트머리.cmd", "만들기.py", "깃허브폴더만들기.py"):
        나온.append((f"도구/배포/{이름}", 이칸 / 이름))
    시험 = 뿌리 / "도구" / "시험"
    for 파일 in sorted(시험.iterdir()):
        if 파일.is_file() and 파일.suffix in (".py", ".js"):
            나온.append((f"도구/시험/{파일.name}", 파일))
    return 나온


def 개인자료찾기(목록: list) -> list:
    문제 = []
    개인글 = 개인글만들기()
    for 이름, 자리 in 목록:
        try:
            글 = 자리.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for 낱말 in 개인글:
            if 낱말 in 글:
                문제.append(f"{이름}: '{낱말}' {글.count(낱말)}번")
    return 문제


README = """# GPT Local Agent

**Turn ChatGPT into a hands-on coding agent on your own PC.**
A Chrome extension + a local bridge server that lets ChatGPT (in your browser) read your project files,
edit code, run commands and long jobs — with approval modes so you stay in control.

> 한국어: ChatGPT 웹 대화창이 **내 PC의 파일을 읽고, 고치고, 명령을 실행**하게 해 주는 Chrome 확장 + 로컬 서버입니다.
> 전체권한 / 자동 / 수동 승인 모드로 어디까지 GPT에게 맡길지 정합니다. (Windows)

```
ChatGPT (web)  ->  Chrome extension  ->  127.0.0.1:8765  ->  local Python server  ->  your files / terminal
      ^                                                                               |
      +----------------------------- tool results ------------------------------------+
```

## Approval modes

| Mode | Who decides | Asks you before... |
|---|---|---|
| **Full** (전체권한) | ChatGPT | package installs, screen/keyboard control, outside tools (always) |
| **Auto** (자동) | ChatGPT for safe work inside your project folder | risky commands, deleting/moving many files, reading outside the folder, installs |
| **Manual** (수동) | You | every edit, delete, command, git commit, helper agent |

Always blocked in every mode: destructive commands (`rm -rf`, `format`, `shutdown`, `git push` ...) and reading secret files (`.env`, keys).
Secret files such as `.env` are **write-only** for ChatGPT, so you can fill in API keys yourself without sending them to ChatGPT.

## What the agent can do

Read / search / edit files (with automatic backups), run commands and long jobs (training etc.), git, plans and memory,
reminders, web reading, attach images to the chat, look at your screen and send keyboard/mouse input
(**each needs your explicit per-window, time-limited approval**), and spawn read-only helper agents.

## Install (Windows)

**Easy:** download `GPT-LocalAgent-Setup.cmd` from the [Releases](../../releases) page and double-click it.
It checks Python (3.10+), installs the server, and walks you through loading the extension.

**Manual:**
1. `python -X utf8 서버/서버.py` (Python 3.10+; Pillow is optional, for image tools)
2. Chrome -> `chrome://extensions` -> turn on *Developer mode* -> *Load unpacked* -> select the `확장` folder
3. Create a ChatGPT *Project* and paste the instructions from `문서/프로토콜.md` (the text inside the code fence) into its *Instructions*
4. Open a chat inside that project, click the extension icon to open the side panel, pick a work folder with **+**

## Safety notes

- ChatGPT can act on your computer through this tool. Start with **Manual** mode and move to **Auto** once you trust it.
- The server only listens on `127.0.0.1` and only trusts the extension and websites you approve.
- Reading / writing is limited to your user folder (configurable in `서버/설정.json`).
- This project is not affiliated with OpenAI. Automating a web UI may be against the terms of the service you use; use at your own risk.
- Do not use the input-control tool to automate online multiplayer games (anti-cheat bans).

## Tests

```
python -X utf8 도구/시험/다돌리기.py
```

## License

MIT
"""

GITIGNORE = """# Python
__pycache__/
*.py[cod]
.venv/
venv/

# local data of the agent (never commit)
서버/방/
서버/방목록.json
서버/방목록백업/
서버/설정.json
서버/권한.json
서버/허용사이트.json
서버/뒤뜰/
서버/실행로그.txt
서버/에러로그.txt
서버/서버출력.txt
서버/자동켜기/host.json
서버/자동켜기/agent_host.bat
서버/자동켜기/켜기일지.txt
서버/자동켜기/서버출력.txt
.agent/
작업기록/
_archive/
workspace/
설치된것/
도구/배포/결과/
도구/배포/깃허브용/

# secrets
.env
.env.*
*.pem
*.key
"""


def main():
    목록 = 모으기()
    문제 = 개인자료찾기(목록)
    if 문제:
        print("✗ 개인 자료가 섞여 있어 만들지 않습니다:")
        for 줄 in 문제:
            print("  -", 줄)
        return 1
    if 나가는곳.exists():
        shutil.rmtree(나가는곳)
    for 이름, 자리 in 목록:
        가는곳 = 나가는곳 / 이름
        가는곳.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(자리, 가는곳)
    (나가는곳 / "README.md").write_text(README, encoding="utf-8", newline="\n")
    (나가는곳 / ".gitignore").write_text(GITIGNORE, encoding="utf-8", newline="\n")
    수 = sum(1 for _ in 나가는곳.rglob("*") if _.is_file())
    print(f"✓ {나가는곳}")
    print(f"  파일 {수}개 (README.md · .gitignore 포함)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
