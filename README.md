# GPT Local Agent

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
