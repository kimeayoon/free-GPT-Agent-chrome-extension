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
- 옆 판에서 ChatGPT 모델(GPT-6 · GPT-5.6 Sol 등)과 추론 수준 바꾸기
- 옆 판 언어: 영어 기본, ⋮ 메뉴의 Language 에서 한국어로 바꿈

### 설치 (Windows)

**쉬운 방법:** [Releases](../../releases)에서 아래 두 파일을 **같은 폴더에** 받습니다.

| 파일 | 내용 |
|---|---|
| `GPT-LocalAgent-Server-Setup-<버전>.cmd` | 로컬 서버 설치 프로그램 |
| `GPT-LocalAgent-Extension-<버전>.zip` | 크롬 확장 |

1. `GPT-LocalAgent-Server-Setup-<버전>.cmd`를 더블클릭합니다. 파이썬(3.10 이상)을 확인하고 서버를 설치합니다.
   같은 폴더에 있는 확장 zip은 설치 폴더 안에 알아서 풀어 줍니다.
2. 안내대로 Chrome → `chrome://extensions` → *개발자 모드* → *압축해제된 확장 프로그램을 로드* → 안내된 `확장` 폴더를 고릅니다.
3. ChatGPT에서 *프로젝트*를 만들고, 클립보드에 복사된 지침을 프로젝트 *지침*에 붙여넣습니다.
   지침은 한국어로 쓰여 있지만 그대로 붙이면 됩니다. ChatGPT는 사용자가 쓰는 언어로 답합니다.
4. 그 프로젝트 안에서 새 대화를 열고, 확장 아이콘을 눌러 옆 판을 연 뒤 **＋**로 일할 폴더를 고릅니다.

**직접 설치:**
1. `python -X utf8 서버/서버.py` 실행 (Python 3.10 이상, 그림 도구를 쓰려면 Pillow 선택)
2. Chrome → `chrome://extensions` → *개발자 모드* 켜기 → *압축해제된 확장 프로그램을 로드* → `확장` 폴더 선택
3. ChatGPT에서 *프로젝트*를 만들고, `문서/프로토콜.md`의 코드 울타리 안쪽 글을 프로젝트 *지침*에 붙여넣기
4. 그 프로젝트 안에서 새 대화를 열고, 확장 아이콘을 눌러 옆 판을 연 뒤 **＋**로 일할 폴더 고르기

### 서버는 어떻게 실행되나

| 항목 | 내용 |
|---|---|
| 설치 위치 | `%LOCALAPPDATA%\GPTLocalAgent` (관리자 권한 없이, 이 사용자에게만) |
| 실행 | `python -X utf8 서버\서버.py` 가 창 없이 돕니다 |
| 자동 시작 | 로그인할 때 켜지고, 꺼져 있으면 확장이 옆 판을 열 때 다시 켭니다 |
| 주소 | `127.0.0.1:8765` — 내 PC 안에서만 듣습니다. 확장과 사용자가 허용한 사이트의 요청만 받습니다 |
| 흐름 | ChatGPT 답 속의 요청 → 확장이 읽음 → 서버가 내 PC에서 실행 → 결과를 대화에 파일로 붙임 |
| 기록 · 설정 | `서버\서버출력.txt` · `서버\설정.json` |
| 끄기 · 지우기 | 설치 폴더의 `uninstall.cmd` (대화 기록을 남길지 묻습니다) |
| 손으로 켜기 | `도구\서버 켜기.bat` |

버전은 한 숫자(주.부.수)이고, 서버 · 확장 · 릴리스가 같은 숫자를 씁니다. 옆 판 아래에 서버 버전이 보입니다.

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
- Switch the ChatGPT model (GPT-6, GPT-5.6 Sol ...) and thinking level from the side panel
- Side panel in English by default; switch to Korean from the ⋮ menu → Language

### Install (Windows)

**Easy:** download these two files from the [Releases](../../releases) page **into the same folder**.

| File | What it is |
|---|---|
| `GPT-LocalAgent-Server-Setup-<version>.cmd` | installer for the local server |
| `GPT-LocalAgent-Extension-<version>.zip` | the Chrome extension |

1. Double-click `GPT-LocalAgent-Server-Setup-<version>.cmd`. It checks Python (3.10+) and installs the server.
   The extension zip in the same folder is unpacked into the install folder for you.
2. Follow the prompts: Chrome → `chrome://extensions` → *Developer mode* → *Load unpacked* → pick the `확장` folder it shows.
3. Create a ChatGPT *Project* and paste the instructions (already on your clipboard) into its *Instructions*.
   The instructions are written in Korean; paste them as they are. ChatGPT answers in the language you write in.
4. Open a chat inside that project, click the extension icon to open the side panel, pick a work folder with **+**.

**Manual:**
1. `python -X utf8 서버/서버.py` (Python 3.10+; Pillow is optional, for image tools)
2. Chrome → `chrome://extensions` → turn on *Developer mode* → *Load unpacked* → select the `확장` folder
3. Create a ChatGPT *Project* and paste the instructions from `문서/프로토콜.md` (the text inside the code fence) into its *Instructions*
4. Open a chat inside that project, click the extension icon to open the side panel, pick a work folder with **+**

### How the server runs

| Item | Details |
|---|---|
| Install location | `%LOCALAPPDATA%\GPTLocalAgent` (per user, no administrator rights) |
| Process | `python -X utf8 서버\서버.py`, running without a window |
| Auto-start | starts when you log in; if it is not running, the extension starts it when you open the side panel |
| Address | `127.0.0.1:8765` — this PC only. It accepts requests only from the extension and from websites you approve |
| Flow | request in ChatGPT's answer → the extension reads it → the server runs it on your PC → the result is attached to the chat as a file |
| Log · settings | `서버\서버출력.txt` · `서버\설정.json` |
| Stop · remove | `uninstall.cmd` in the install folder (asks whether to keep your chat history) |
| Start by hand | `도구\서버 켜기.bat` |

There is one version number (major.minor.patch) shared by the server, the extension and the release. The side panel shows the server version.

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
