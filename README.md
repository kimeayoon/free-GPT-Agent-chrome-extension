# GPT Local Agent

[한국어](#한국어) · [English](#english)

---

## 한국어

**내 PC에서 ChatGPT를 직접 손을 움직이는 코딩 에이전트로 바꿔 줍니다.**

ChatGPT 웹 대화창이 내 컴퓨터의 프로젝트 파일을 읽고, 코드를 고치고, 명령과 오래 걸리는 작업(학습 등)을 실행하게 해 주는
**Chrome 확장 + 로컬 서버**입니다. 어디까지 맡길지는 승인 모드로 정합니다. (Windows)

```
ChatGPT (웹)  ->  Chrome 확장  ->  127.0.0.1:8765  ->  로컬 Python 서버  ->  내 파일 / 터미널
      ^                                                                        |
      +----------------------------- 도구 결과 --------------------------------+
```

### 승인 모드

| 모드 | 누가 결정하나 | 이럴 때 사용자에게 묻습니다 |
|---|---|---|
| **전체권한** | ChatGPT | 패키지 설치, 화면·키보드·마우스 제어, 바깥 도구 (항상) |
| **자동** | 일할 폴더 안의 안전한 일은 ChatGPT | 위험한 명령, 파일을 많이 지우거나 옮길 때, 일할 폴더 밖 읽기, 설치 |
| **수동** | 사용자 | 파일 고치기, 지우기, 명령 실행, 깃 기록, 일꾼 부르기 전부 |

어느 모드에서나 **항상 막는 것**: 파괴 명령(`rm -rf`, `format`, `shutdown`, `git push` 등)과 비밀 파일 읽기(`.env`, 키 파일).
`.env` 같은 비밀 파일은 ChatGPT가 **쓰기만** 할 수 있어서, API 키를 사용자가 직접 채워 넣어도 ChatGPT로 새지 않습니다.

### 할 수 있는 일

- 파일 읽기·찾기·고치기(자동 백업), 폴더 만들기, 지우기(휴지통으로)
- 명령 실행, 오래 걸리는 작업 실행과 진행률 확인(학습 등)
- 깃, 목표와 차례, 기억, 예약(시간·조건)
- 웹 글 읽기, 그림을 채팅에 붙이기
- 화면 보기, 키보드·마우스 보내기 — **창 하나, 시간 제한, 사용자 승인이 있어야만** 됩니다
- 읽기 전용 일꾼(보조 에이전트) 부르기

### 설치 (Windows)

**쉬운 방법:** [Releases](../../releases)에서 `GPT-LocalAgent-Setup.cmd`를 받아 더블클릭합니다.
파이썬(3.10 이상)을 확인하고, 서버를 설치하고, 확장을 불러오는 방법을 순서대로 안내합니다.

**직접 설치:**
1. `python -X utf8 서버/서버.py` 실행 (Python 3.10 이상, 그림 도구를 쓰려면 Pillow 선택)
2. Chrome → `chrome://extensions` → *개발자 모드* 켜기 → *압축해제된 확장 프로그램을 로드* → `확장` 폴더 선택
3. ChatGPT에서 *프로젝트*를 만들고, `문서/프로토콜.md`의 코드 울타리 안쪽 글을 프로젝트 *지침*에 붙여넣기
4. 그 프로젝트 안에서 새 대화를 열고, 확장 아이콘을 눌러 옆 판을 연 뒤 **＋**로 일할 폴더 고르기

### 안전 주의

- 이 도구로 ChatGPT는 내 컴퓨터에서 실제로 일을 합니다. 처음에는 **수동**으로 시작하고, 믿음이 생기면 **자동**으로 바꾸세요.
- 서버는 `127.0.0.1`(내 PC 안)에서만 듣고, 확장과 사용자가 허용한 사이트만 믿습니다.
- 읽고 쓰는 범위는 사용자 폴더 안입니다(`서버/설정.json`에서 바꿀 수 있습니다).
- 이 프로젝트는 OpenAI와 관계가 없습니다. 웹 화면을 자동으로 다루는 것은 이용 약관에 어긋날 수 있으니 본인 책임으로 쓰세요.
- 입력 제어 도구로 온라인 멀티플레이 게임을 자동화하지 마세요(안티치트 제재).

### 시험

```
python -X utf8 도구/시험/다돌리기.py
```

### 라이선스

MIT

---

## English

**Turn ChatGPT into a hands-on coding agent on your own PC.**

A Chrome extension + a local bridge server that lets ChatGPT (in your browser) read your project files,
edit code, run commands and long jobs — with approval modes so you stay in control. (Windows)

```
ChatGPT (web)  ->  Chrome extension  ->  127.0.0.1:8765  ->  local Python server  ->  your files / terminal
      ^                                                                               |
      +----------------------------- tool results ------------------------------------+
```

### Approval modes

| Mode | Who decides | Asks you before... |
|---|---|---|
| **Full** (전체권한) | ChatGPT | package installs, screen/keyboard control, outside tools (always) |
| **Auto** (자동) | ChatGPT for safe work inside your project folder | risky commands, deleting/moving many files, reading outside the folder, installs |
| **Manual** (수동) | You | every edit, delete, command, git commit, helper agent |

Always blocked in every mode: destructive commands (`rm -rf`, `format`, `shutdown`, `git push` ...) and reading secret files (`.env`, keys).
Secret files such as `.env` are **write-only** for ChatGPT, so you can fill in API keys yourself without sending them to ChatGPT.

### What the agent can do

- Read / search / edit files (with automatic backups), create folders, delete (to a trash folder)
- Run commands and long jobs (training etc.) and watch their progress
- Git, goals and plans, memory, reminders (time or condition based)
- Read web pages, attach images to the chat
- Look at your screen and send keyboard/mouse input — **only with your explicit, per-window, time-limited approval**
- Spawn read-only helper agents

### Install (Windows)

**Easy:** download `GPT-LocalAgent-Setup.cmd` from the [Releases](../../releases) page and double-click it.
It checks Python (3.10+), installs the server, and walks you through loading the extension.

**Manual:**
1. `python -X utf8 서버/서버.py` (Python 3.10+; Pillow is optional, for image tools)
2. Chrome → `chrome://extensions` → turn on *Developer mode* → *Load unpacked* → select the `확장` folder
3. Create a ChatGPT *Project* and paste the instructions from `문서/프로토콜.md` (the text inside the code fence) into its *Instructions*
4. Open a chat inside that project, click the extension icon to open the side panel, pick a work folder with **+**

### Safety notes

- ChatGPT can act on your computer through this tool. Start with **Manual** mode and move to **Auto** once you trust it.
- The server only listens on `127.0.0.1` and only trusts the extension and websites you approve.
- Reading / writing is limited to your user folder (configurable in `서버/설정.json`).
- This project is not affiliated with OpenAI. Automating a web UI may be against the terms of the service you use; use at your own risk.
- Do not use the input-control tool to automate online multiplayer games (anti-cheat bans).

### Tests

```
python -X utf8 도구/시험/다돌리기.py
```

### License

MIT
