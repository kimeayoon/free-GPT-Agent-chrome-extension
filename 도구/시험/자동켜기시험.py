# -*- coding: utf-8 -*-
"""자동 켜기 시험 — 크롬이 하는 짓을 그대로 흉내 내서, 서버가 살아남는지 본다.

크롬은 Native Messaging 프로그램을 Job 에 넣어 띄우고, 끝나면 Job 째로 죽인다.
그 안에서 띄운 서버가 같이 죽으면 '판을 열면 켜졌다가 바로 꺼지는' 일이 생긴다.
말로 '될 겁니다' 하지 않고 여기서 실제로 죽여 본다.

  두 판을 돌린다
    ㄱ. Job 이 빠져나가기를 허락할 때   → CREATE_BREAKAWAY_FROM_JOB 길
    ㄴ. Job 이 빠져나가기를 막을 때     → WMI 길
  판마다: 서버 끔 → Job 에 가둔 채 켜기 요청 → Job 닫아 몰살 → 3초 뒤 서버가 살아 있나

  돌리는 법:  python 도구▸시험▸자동켜기시험.py
  (주의) 이미 켜진 서버를 끄고 시작한다. 끝나면 서버는 켜진 채로 둔다.
"""

import ctypes
import ctypes.wintypes as w
import json
import socket
import struct
import subprocess
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent.parent
배치파일 = 뿌리 / "서버" / "자동켜기" / "agent_host.bat"
일지파일 = 뿌리 / "서버" / "자동켜기" / "켜기일지.txt"
포트 = 8765

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")

JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JobObjectExtendedLimitInformation = 9
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000


class 기본한계(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", w.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", w.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", w.DWORD),
                ("SchedulingClass", w.DWORD)]


class 입출력셈(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in
                ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                 "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class 넓은한계(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", 기본한계),
                ("IoInfo", 입출력셈),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]


def 살았나() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 포트), timeout=0.5):
            return True
    except OSError:
        return False


def 서버끄기():
    """8765 를 듣고 있는 프로세스를 끈다(이 서버만 이 자리를 쓴다)."""
    # netstat 은 한국어 윈도우에서 cp949 로 찍는다
    나온것 = subprocess.run(["netstat", "-ano"], capture_output=True).stdout.decode(
        "cp949", errors="replace")
    번호들 = {줄.split()[-1] for 줄 in 나온것.splitlines()
             if f"127.0.0.1:{포트}" in 줄 and "LISTENING" in 줄}
    for 번호 in 번호들:
        subprocess.run(["taskkill", "/PID", 번호, "/F"], capture_output=True)
    for _ in range(40):
        if not 살았나():
            return
        time.sleep(0.1)


def Job만들기(빠져나가기허락: bool) -> int:
    job = k32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "CreateJobObject")
    한계 = 넓은한계()
    깃발 = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if 빠져나가기허락:
        깃발 |= JOB_OBJECT_LIMIT_BREAKAWAY_OK
    한계.BasicLimitInformation.LimitFlags = 깃발
    if not k32.SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                       ctypes.byref(한계), ctypes.sizeof(한계)):
        raise OSError(ctypes.get_last_error(), "SetInformationJobObject")
    return job


def 한판(빠져나가기허락: bool) -> dict:
    서버끄기()
    assert not 살았나(), "서버를 못 껐습니다"
    일지앞 = 일지파일.read_text(encoding="utf-8") if 일지파일.exists() else ""

    job = Job만들기(빠져나가기허락)

    # 크롬과 똑같이: cmd /d /c "배치" <확장 주소>  (멈춘 채로 띄워 Job 에 먼저 넣는다)
    호스트 = subprocess.Popen(
        ["cmd", "/d", "/c", str(배치파일), "chrome-extension://시험/"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=CREATE_SUSPENDED | CREATE_NO_WINDOW,
    )
    if not k32.AssignProcessToJobObject(job, int(호스트._handle)):
        raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject")
    ntdll.NtResumeProcess(int(호스트._handle))

    몸 = json.dumps({"짓": "켜기"}).encode()
    호스트.stdin.write(struct.pack("<I", len(몸)) + 몸)
    호스트.stdin.flush()

    머리 = 호스트.stdout.read(4)
    답 = {}
    if len(머리) == 4:
        답 = json.loads(호스트.stdout.read(struct.unpack("<I", 머리)[0]).decode("utf-8"))

    # 크롬이 하는 것처럼 Job 째로 몰살
    k32.CloseHandle(job)
    try:
        호스트.kill()
    except OSError:
        pass

    time.sleep(3)
    일지 = 일지파일.read_text(encoding="utf-8") if 일지파일.exists() else ""
    return {"답": 답, "몰살 뒤 살아있나": 살았나(), "일지": 일지[len(일지앞):].strip()}


if __name__ == "__main__":
    k32.CreateJobObjectW.restype = w.HANDLE
    결과 = []
    for 허락, 이름 in ((True, "ㄱ. Job 이 빠져나가기를 허락"), (False, "ㄴ. Job 이 빠져나가기를 막음")):
        판 = 한판(허락)
        좋음 = bool(판["답"].get("됨")) and 판["몰살 뒤 살아있나"]
        결과.append(좋음)
        print(f"\n━━━ {이름} ━━━")
        print(f"  켜기 답        : {판['답']}")
        print(f"  Job 몰살 뒤    : {'살아 있음' if 판['몰살 뒤 살아있나'] else '죽었음'}")
        print(f"  켜기일지       : {판['일지'] or '(없음)'}")
        print(f"  → {'통과' if 좋음 else '실패'}")

    print()
    print("전부 통과" if all(결과) else "실패한 판이 있습니다")
    raise SystemExit(0 if all(결과) else 1)
