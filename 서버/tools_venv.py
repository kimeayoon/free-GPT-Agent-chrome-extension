# -*- coding: utf-8 -*-
"""일터(venv) 만들기 — 씨앗.

프로젝트마다 꾸러미를 따로 두려면 일터가 필요하다.
일터가 없으면 받아온 것이 컴퓨터 전체에 깔려서 프로젝트끼리 섞인다.

씨앗은 지금 방의 폴더 안에 .venv 를 만든다.
인터넷에서 받아오는 게 아니라(파이썬에 들어 있는 기능) 허락 물음 없이 바로 된다.
"""

import os
import subprocess
import sys
from pathlib import Path

import rooms
import sandbox

일터이름 = ".venv"


def 일터자리(밭: Path | None = None) -> Path | None:
    """이 방의 일터가 있을 자리. 방이 없으면 None."""
    뿌리 = 밭 or rooms.지금밭()
    return (뿌리 / 일터이름) if 뿌리 else None


def 일터파이썬(밭: Path | None = None) -> Path | None:
    """일터 안의 파이썬. 없으면 None."""
    자리 = 일터자리(밭)
    if 자리 is None:
        return None
    for 후보 in (자리 / "Scripts" / "python.exe", 자리 / "bin" / "python"):
        if 후보.exists():
            return 후보
    return None


def 일터환경(밭: Path | None = None) -> dict | None:
    """일터를 쓰도록 맞춘 환경변수. 일터가 없으면 None.

    이게 없으면 씨앗으로 일터를 만들고 도토리로 꾸러미를 깔아도
    도라지가 'python' 을 부를 때 컴퓨터 전체의 파이썬이 잡혀서
    깐 것이 하나도 안 보인다. 일터를 만든 보람이 없어진다.

    하는 일은 사람이 '일터 켜기(activate)' 를 눌렀을 때와 같다.
      - PATH 맨 앞에 일터의 Scripts 를 넣는다
      - VIRTUAL_ENV 를 알려준다
      - PYTHONHOME 은 있으면 방해가 되므로 뺀다
    """
    파이썬 = 일터파이썬(밭)
    if 파이썬 is None:
        return None

    환경 = dict(os.environ)
    환경["VIRTUAL_ENV"] = str(파이썬.parent.parent)
    환경["PATH"] = str(파이썬.parent) + os.pathsep + 환경.get("PATH", "")
    환경.pop("PYTHONHOME", None)
    return 환경


def _판찾기(판: str) -> str:
    """'3.12' 같은 판 번호로 실제 파이썬을 찾는다."""
    판 = (판 or "").strip()
    if not 판:
        return sys.executable

    try:
        끝 = subprocess.run(
            ["py", f"-{판}", "-c", "import sys; print(sys.executable)"],
            capture_output=True, timeout=30, text=False,
        )
        길 = (끝.stdout or b"").decode("utf-8", errors="replace").strip()
        if 끝.returncode == 0 and 길 and Path(길).exists():
            return 길
    except (OSError, subprocess.TimeoutExpired):
        pass

    raise ValueError(
        f"파이썬 {판} 을(를) 못 찾았습니다. "
        f"쓸 수 있는 것을 보려면 도라지로 'py -0p' 를 돌려 보세요."
    )


def 판목록() -> list:
    """이 컴퓨터에 깔린 파이썬 판 목록."""
    try:
        끝 = subprocess.run(["py", "-0p"], capture_output=True, timeout=30, text=False)
        글 = (끝.stdout or b"").decode("utf-8", errors="replace")
        return [줄.strip() for 줄 in 글.splitlines() if 줄.strip()]
    except (OSError, subprocess.TimeoutExpired):
        return []


def make_venv(version: str = "", **_):
    """지금 방 폴더에 일터를 만든다. 이미 있으면 그대로 알려준다."""
    밭 = rooms.지금밭()
    if 밭 is None:
        raise ValueError(
            "일할 방이 없거나 방에 폴더가 정해지지 않았습니다. "
            "사용자에게 창에서 일할 곳을 고르라고 말하세요."
        )

    # 쓰기 규칙을 그대로 탄다(다른 자리엔 못 만든다)
    자리 = sandbox.경로검증(str(일터자리(밭)), 쓰기=True)

    있던파이썬 = 일터파이썬(밭)
    if 있던파이썬:
        return {
            "path": sandbox.표시경로(자리),
            "action": "이미 있음",
            "파이썬": str(있던파이썬),
            "판목록": 판목록(),
        }

    만들파이썬 = _판찾기(version)

    try:
        끝 = subprocess.run(
            [만들파이썬, "-m", "venv", str(자리)],
            capture_output=True, timeout=300, text=False,
        )
    except subprocess.TimeoutExpired:
        raise ValueError("5분을 넘겨 멈췄습니다.")
    except OSError as e:
        raise ValueError(f"만들지 못했습니다: {e}")

    if 끝.returncode != 0:
        글 = ((끝.stdout or b"") + b"\n" + (끝.stderr or b"")).decode(
            "utf-8", errors="replace"
        ).strip()[-1500:]
        raise ValueError(f"만들지 못했습니다: {글}")

    새파이썬 = 일터파이썬(밭)
    return {
        "path": sandbox.표시경로(자리),
        "action": "만듦",
        "파이썬": str(새파이썬) if 새파이썬 else "(못 찾음)",
        "안내": (
            "이제 받아오는 것(도토리)은 여기로 들어갑니다. "
            "돌려볼 때(도라지)도 이 파이썬을 쓰세요: "
            + (str(새파이썬) if 새파이썬 else "")
        ),
    }


등록된도구 = {
    "make_venv": make_venv,
}
