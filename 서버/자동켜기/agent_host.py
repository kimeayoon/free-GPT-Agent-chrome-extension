# -*- coding: utf-8 -*-
"""자동 켜기 — 확장이 부르면 서버를 켜 주는 작은 프로그램.

사람이 서버를 따로 켜지 않아도 되게 한다. 크롬의 Native Messaging 으로 불린다.

  확장 → chrome.runtime.sendNativeMessage("com.local_agent.server", {짓:"켜기"})
       → 크롬이 agent_host.bat 을 띄움 → 이 파일
       → 8765 가 비어 있으면 서버.py 를 띄우고, 뜰 때까지 기다렸다가 답한다

지켜야 할 것 두 가지 (어기면 서버가 켜졌다가 바로 죽는다):
  ① 크롬은 이 프로그램을 Job 에 넣고, 연결이 끊기면 2초 뒤 강제로 끈다.
     그래서 서버는 반드시 Job 밖으로 띄운다(CREATE_BREAKAWAY_FROM_JOB).
     Job 이 그걸 막으면 WMI 로 띄운다 — WMI 가 띄운 것은 처음부터 Job 밖이다.
  ② stdout 은 크롬과 말하는 통로다. 여기에 아무 글자나 찍으면 통로가 깨진다.
     그래서 print 를 쓰지 않고, 서버 출력도 파일로만 보낸다.

주고받는 꼴: [길이 4바이트(리틀엔디언)] + [JSON 바이트]
"""

import json
import os
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

여기 = Path(__file__).resolve().parent
서버칸 = 여기.parent
서버파일 = 서버칸 / "서버.py"
출력파일 = 여기 / "서버출력.txt"
일지파일 = 여기 / "켜기일지.txt"

포트 = 8765
뜨기기다림초 = 12

# Windows 프로세스 깃발
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_NO_WINDOW = 0x08000000


def 적기(*조각):
    """무슨 일이 있었는지 파일에 남긴다. stdout 에는 절대 안 쓴다."""
    try:
        with 일지파일.open("a", encoding="utf-8") as f:
            f.write(datetime.now().strftime("%m-%d %H:%M:%S ") + " ".join(map(str, 조각)) + "\n")
    except OSError:
        pass


# ── 크롬과 주고받기 ────────────────────────────────────────────

def 받기() -> dict:
    머리 = sys.stdin.buffer.read(4)
    if len(머리) < 4:
        return {}
    길이 = struct.unpack("<I", 머리)[0]
    몸 = sys.stdin.buffer.read(길이)
    try:
        return json.loads(몸.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def 보내기(값: dict) -> None:
    몸 = json.dumps(값, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(몸)))
    sys.stdout.buffer.write(몸)
    sys.stdout.buffer.flush()


# ── 서버 ──────────────────────────────────────────────────────

def 서버살았나() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 포트), timeout=0.5):
            return True
    except OSError:
        return False


def 창없는파이썬() -> str:
    """콘솔 창이 안 뜨는 pythonw 를 쓴다. 없으면 python 으로."""
    지금 = Path(sys.executable)
    if os.name != "nt":
        return str(지금)
    w = 지금.with_name("pythonw.exe")
    return str(w if w.exists() else 지금)


def 깃발로띄우기(명령: list) -> str:
    """Job 밖으로 띄운다. 막히면 예외를 그대로 올린다."""
    출력 = 출력파일.open("ab")
    try:
        옵션 = {"cwd": str(서버칸), "stdin": subprocess.DEVNULL,
              "stdout": 출력, "stderr": subprocess.STDOUT, "close_fds": True}
        if os.name == "nt":
            옵션["creationflags"] = (DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                                    | CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW)
        else:
            옵션["start_new_session"] = True
        subprocess.Popen(명령, **옵션)
    finally:
        출력.close()
    return "breakaway" if os.name == "nt" else "session"


def WMI로띄우기(명령: list) -> str:
    """WMI 가 띄운 프로세스는 부모가 WmiPrvSE 라 처음부터 어느 Job 에도 안 들어 있다."""
    # WMI 는 표준출력을 넘겨받지 못한다. 이 길로 켜면 서버 출력은 안 남는다.
    # (cmd 로 감싸 파일로 흘리는 방법은 따옴표가 세 겹이 되어 깨지기 쉬워 안 쓴다)
    줄 = subprocess.list2cmdline(명령)
    ps = (
        "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
        f"-Arguments @{{CommandLine='{줄.replace(chr(39), chr(39) * 2)}'; "
        f"CurrentDirectory='{str(서버칸).replace(chr(39), chr(39) * 2)}'}}; "
        "exit $r.ReturnValue"
    )
    끝 = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW, timeout=20,
    )
    if 끝.returncode != 0:
        raise OSError(f"WMI 로 띄우지 못했습니다(돌아온 값 {끝.returncode})")
    return "wmi"


def 서버켜기() -> dict:
    if 서버살았나():
        return {"됨": True, "이미켜짐": True}

    if not 서버파일.exists():
        return {"됨": False, "탈": f"서버.py 가 없습니다: {서버파일}"}

    명령 = [창없는파이썬(), "-X", "utf8", str(서버파일)]
    어떻게 = ""
    try:
        어떻게 = 깃발로띄우기(명령)
    except OSError as e:
        if os.name != "nt":
            적기("Linux 서버 시작 실패", e)
            return {"됨": False, "탈": f"서버를 띄우지 못했습니다: {e}"}
        적기("breakaway 막힘 → WMI 로", e)
        try:
            어떻게 = WMI로띄우기(명령)
        except (OSError, subprocess.SubprocessError) as e2:
            적기("WMI 도 실패", e2)
            return {"됨": False, "탈": f"서버를 띄우지 못했습니다: {e2}"}

    끝때 = time.time() + 뜨기기다림초
    while time.time() < 끝때:
        if 서버살았나():
            적기("켬", 어떻게)
            return {"됨": True, "이미켜짐": False, "어떻게": 어떻게}
        time.sleep(0.25)

    적기("띄웠지만 안 떴음", 어떻게)
    return {"됨": False,
            "탈": f"서버를 띄웠는데 {뜨기기다림초}초 안에 안 떴습니다. {출력파일} 을 보세요."}


def 실행():
    쪽지 = 받기()
    짓 = 쪽지.get("짓", "켜기")
    try:
        if 짓 == "확인":
            보내기({"됨": True, "살음": 서버살았나()})
        else:
            보내기(서버켜기())
    except Exception as e:           # 무엇이 터져도 크롬에게는 답을 준다
        적기("터짐", repr(e))
        보내기({"됨": False, "탈": f"자동 켜기가 터졌습니다: {e}"})


if __name__ == "__main__":
    실행()
