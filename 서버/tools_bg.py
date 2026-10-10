# -*- coding: utf-8 -*-
"""뒤뜰 — 오래 걸리는 일을 떼어 놓고 돌린다.

도라지는 끝날 때까지 기다린다. 그래서 30분이 넘는 일(학습 같은 것)은
아예 할 수가 없었다. 뒤뜰은 다르다.

  두릅 : 일을 뒤뜰에 풀어놓고 바로 돌아온다
  고사리: 그 일이 어떻게 되고 있는지 들여다본다 (그만두게도 할 수 있다)

서버를 껐다 켜도 하던 일은 계속 돌아간다.
서버가 직접 돌리지 않고 '뒤뜰달리기.py' 를 떼어 놓은 프로세스로 띄우기 때문이다.
상태는 전부 디스크(일.json · 기록.txt · 끝번호.txt)에 있으므로,
새로 켠 서버도 칸만 읽으면 무슨 일이 돌고 있는지 그대로 안다.
"""

import ctypes
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import rooms
import sandbox
import 안전파일
import tools_run
import tools_venv

뒤뜰 = Path(__file__).with_name("뒤뜰")
달리기 = Path(__file__).with_name("뒤뜰달리기.py")

꼬리기본줄 = 40
꼬리최대줄 = 400

# 떼어 놓기 (윈도우). 서버가 죽어도 같이 죽지 않게 한다.
_떼어놓기 = 0x00000008 | 0x00000200        # DETACHED_PROCESS | NEW_PROCESS_GROUP


def _지금() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _칸(번호: str) -> Path:
    return 뒤뜰 / 번호


def _일읽기(칸: Path) -> dict | None:
    return 안전파일.json읽기(칸 / "일.json", None, dict)


def _살아있나(pid: int) -> bool:
    """그 번호의 프로세스가 아직 도는지 본다.

    os.kill 은 윈도우에서 신호 0 을 못 받고 그냥 죽여버리므로 쓰면 안 된다.
    """
    if not pid:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    커널 = ctypes.windll.kernel32
    손잡이 = 커널.OpenProcess(0x1000, False, pid)   # QUERY_LIMITED_INFORMATION
    if not 손잡이:
        return False
    try:
        끝번호 = ctypes.c_ulong()
        if not 커널.GetExitCodeProcess(손잡이, ctypes.byref(끝번호)):
            return False
        return 끝번호.value == 259                   # STILL_ACTIVE
    finally:
        커널.CloseHandle(손잡이)


def _끝번호(칸: Path):
    파일 = 칸 / "끝번호.txt"
    if not 파일.exists():
        return None
    try:
        return int(파일.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _상태(칸: Path, 일: dict) -> str:
    if _끝번호(칸) is not None:
        return "끝남"
    if _살아있나(일.get("pid", 0)):
        return "달리는중"
    return "끊김"          # 끝번호도 없는데 프로세스도 없다 = 강제로 죽은 것


def _기록꼬리(칸: Path, 줄수: int) -> tuple[list, int]:
    파일 = 칸 / "기록.txt"
    if not 파일.exists():
        return [], 0
    try:
        글 = 파일.read_bytes()
    except OSError:
        return [], 0
    for 인코딩 in ("utf-8", "cp949"):
        try:
            풀린글 = 글.decode(인코딩)
            break
        except UnicodeDecodeError:
            continue
    else:
        풀린글 = 글.decode("utf-8", errors="replace")

    줄들 = 풀린글.splitlines()
    return 줄들[-줄수:], len(줄들)


def _요약(번호: str) -> dict | None:
    칸 = _칸(번호)
    일 = _일읽기(칸)
    if 일 is None:
        return None
    return {
        "번호": 번호,
        "이름": 일.get("이름", ""),
        "불": 일.get("불", ""),
        "자리": 일.get("자리", ""),
        "시작": 일.get("시작", ""),
        "상태": _상태(칸, 일),
        "끝번호": _끝번호(칸),
    }


def 끊긴일들(방: str) -> list:
    """달리다가 끝번호도 없이 사라진 일 중 아직 알리지 않은 것. [(번호, 이름)]"""
    결과 = []
    if not 방 or not 뒤뜰.exists():
        return 결과
    for 칸 in 뒤뜰.iterdir():
        if not 칸.is_dir() or not (칸 / "달리던중.txt").exists() or (칸 / "끊김알림.txt").exists():
            continue
        일 = _일읽기(칸)
        if not 일 or 일.get("방") != 방:
            continue
        if _상태(칸, 일) == "끊김":
            결과.append((칸.name, 일.get("이름", "")))
    return 결과


def 끊김알림적기(번호: str) -> None:
    try:
        (_칸(번호) / "끊김알림.txt").write_text("1", encoding="utf-8")
    except OSError:
        pass


def _목록() -> list:
    if not 뒤뜰.exists():
        return []
    것들 = []
    for 칸 in 뒤뜰.iterdir():
        if not 칸.is_dir():
            continue
        요약 = _요약(칸.name)
        if 요약:
            것들.append(요약)
    것들.sort(key=lambda x: x.get("시작", ""), reverse=True)
    return 것들


# ── 두릅 : 뒤뜰에 풀어놓기 ─────────────────────────────────────

def run_bg(command: str, cwd: str = ".", name: str = "", **_):
    """오래 걸리는 일을 뒤뜰에 풀어놓고 바로 돌아온다."""
    tools_run.명령검사(command)       # 도라지와 똑같은 규칙을 탄다

    작업폴더 = sandbox.경로검증(cwd)
    if not 작업폴더.exists() or not 작업폴더.is_dir():
        raise NotADirectoryError(f"작업 폴더가 없습니다: {작업폴더}")

    번호 = uuid.uuid4().hex[:8]
    칸 = _칸(번호)
    칸.mkdir(parents=True, exist_ok=True)

    일 = {
        "번호": 번호,
        "이름": (name or "").strip()[:60] or command[:60],
        "불": command,
        "자리": str(작업폴더),
        "시작": _지금(),
        "방": (rooms.지금방() or {}).get("쪽번호", ""),
        "pid": 0,
    }
    안전파일.json쓰기(칸 / "일.json", 일)
    (칸 / "기록.txt").write_bytes(b"")

    환경 = tools_venv.일터환경()

    try:
        새것 = subprocess.Popen(
            [sys.executable, str(달리기), str(칸)],
            cwd=str(작업폴더),
            env=환경,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=_떼어놓기 if os.name == "nt" else 0,
            start_new_session=(os.name != "nt"),
        )
    except OSError as e:
        raise ValueError(f"뒤뜰에 풀어놓지 못했습니다: {e}")

    일["pid"] = 새것.pid
    안전파일.json쓰기(칸 / "일.json", 일)
    # '달리던 일' 표 — 나중에 끝번호도 없이 사라지면(컴퓨터를 껐다 켬 · 강제로 죽음) 그것을 알아챌 수 있다.
    # 표 없는 옛 일은 건드리지 않는다(표를 만들기 전에 죽은 일들까지 한꺼번에 알리지 않게).
    try:
        (칸 / "달리던중.txt").write_text("1", encoding="utf-8")
    except OSError:
        pass

    return {
        "번호": 번호,
        "이름": 일["이름"],
        "불": command,
        "자리": sandbox.표시경로(작업폴더),
        "상태": "달리는중",
        "일터": bool(환경),
        "안내": f"고사리로 들여다보세요: 나물 고사리 / 번호 {번호}",
    }


# ── 고사리 : 들여다보기 · 그만두기 ─────────────────────────────

def watch_bg(job: str = "", max_results: int = 0, status: str = "", **_):
    """뒤뜰 일을 들여다본다. 번호를 안 주면 목록을 보여준다.

    상태에 '그만' 을 주면 그 일을 멈춘다.
    """
    번호 = (job or "").strip()
    if not 번호:
        return {"일들": _목록(), "개수": len(_목록())}

    칸 = _칸(번호)
    일 = _일읽기(칸)
    if 일 is None:
        raise ValueError(f"그런 뒤뜰 일이 없습니다: {번호}")

    if (status or "").strip() in ("그만", "멈춤", "중단"):
        return _그만두기(번호, 칸, 일)

    줄수 = max(1, min(int(max_results or 꼬리기본줄), 꼬리최대줄))
    꼬리, 총줄 = _기록꼬리(칸, 줄수)

    return {
        **_요약(번호),
        "총줄": 총줄,
        "보인줄": len(꼬리),
        "나온것": "\n".join(꼬리) or "(아직 나온 것 없음)",
    }


def _그만두기(번호: str, 칸: Path, 일: dict) -> dict:
    pid = 일.get("pid", 0)
    if _끝번호(칸) is not None:
        return {**_요약(번호), "한일": "이미 끝나 있었습니다"}

    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True, timeout=30)
    else:
        try:
            os.killpg(pid, 15)
        except OSError:
            pass

    (칸 / "끝번호.txt").write_text("-9", encoding="utf-8")
    return {**_요약(번호), "한일": "그만두게 했습니다"}


등록된도구 = {
    "run_bg": run_bg,
    "watch_bg": watch_bg,
}
