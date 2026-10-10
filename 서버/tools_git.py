# -*- coding: utf-8 -*-
"""칡 — 깃.

고친 것을 되돌릴 수 있게 남겨 두는 일이다.
미역(되돌리기)은 파일 하나를 백업에서 살리는 것이고, 칡은 프로젝트 전체를
'여기까지가 잘 되던 상태' 로 묶어 두는 것이다.

할 수 있는 짓만 적어 두고 나머지는 막는다. 셸을 거치지 않으므로
명령을 끼워 넣을 수 없다.

  밀기(push) 는 없다 — 바깥으로 내보내는 일은 사람이 직접 한다.
  되돌리기(reset --hard) 도 없다 — 고친 것이 통째로 날아간다.
"""

import subprocess
from pathlib import Path

import rooms
import sandbox

# 짓 → (실제 명령, 설명)
할수있는짓 = {
    "상태":   (["status", "--short", "--branch"], "무엇이 바뀌었는지"),
    "차이":   (["diff"], "아직 담지 않은 변경"),
    "담긴차이": (["diff", "--cached"], "담아 둔 변경"),
    "기록":   (["log", "--oneline", "-20"], "최근 20개"),
    "가지":   (["branch", "-a"], "가지 목록"),
    "담기":   (["add", "-A"], "고친 것 전부 담기"),
}

# 글을 따로 받아야 하는 짓
메시지필요 = "맡기기"

막는이유 = {
    "push": "밀기는 바깥으로 내보내는 일이라 사람이 직접 합니다.",
    "reset": "되돌리기는 고친 것이 통째로 날아갑니다.",
    "clean": "지우기는 안 담긴 파일이 전부 사라집니다.",
}


def _자리(cwd: str) -> Path:
    자리 = sandbox.경로검증(cwd or ".")
    if not 자리.is_dir():
        raise NotADirectoryError(f"칸이 아닙니다: {자리}")
    return 자리


def _깃있나(자리: Path) -> bool:
    여기 = 자리
    for _ in range(8):
        if (여기 / ".git").exists():
            return True
        if 여기.parent == 여기:
            break
        여기 = 여기.parent
    return False


def _돌리기(자리: Path, 뒷말: list) -> dict:
    try:
        끝 = subprocess.run(
            # quotepath 를 끄지 않으면 한글 파일이름이 \352\267\270 처럼 나온다
            ["git", "-c", "core.quotepath=false"] + 뒷말,
            cwd=str(자리),
            capture_output=True,
            timeout=120,
            text=False,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise ValueError("깃이 깔려 있지 않습니다.")
    except subprocess.TimeoutExpired:
        raise ValueError("2분을 넘겨 멈췄습니다.")

    글 = ((끝.stdout or b"") + (끝.stderr or b"")).decode("utf-8", errors="replace")
    return {
        "끝번호": 끝.returncode,
        "ok": 끝.returncode == 0,
        "나온것": 글.strip()[:8000] or "(출력 없음)",
    }


def git_do(action: str = "상태", cwd: str = ".", note: str = "", **_):
    """깃을 쓴다. 짓은 상태·차이·담긴차이·기록·가지·담기·맡기기·시작."""
    짓 = (action or "상태").strip()
    자리 = _자리(cwd)

    if 짓 == "시작":
        sandbox.경로검증(cwd or ".", 쓰기=True)
        if _깃있나(자리):
            return {"짓": "시작", "자리": sandbox.표시경로(자리),
                    "나온것": "이미 깃으로 관리되고 있습니다.", "ok": True}
        return {"짓": "시작", "자리": sandbox.표시경로(자리),
                **_돌리기(자리, ["init"])}

    if not _깃있나(자리):
        raise ValueError(
            f"{sandbox.표시경로(자리)} 는 깃으로 관리되고 있지 않습니다. "
            "시작하려면 짓에 '시작' 을 적으세요."
        )

    if 짓 == 메시지필요:
        쪽 = (note or "").strip()
        if not 쪽:
            raise ValueError("맡길 때는 쪽(무엇을 왜 바꿨는지)을 적어야 합니다.")
        sandbox.경로검증(cwd or ".", 쓰기=True)
        담기 = _돌리기(자리, ["add", "-A"])
        if not 담기["ok"]:
            return {"짓": 짓, "자리": sandbox.표시경로(자리), **담기}
        맡기기 = _돌리기(자리, ["commit", "-m", 쪽[:500]])
        return {"짓": 짓, "자리": sandbox.표시경로(자리), "쪽": 쪽[:500], **맡기기}

    if 짓 in 할수있는짓:
        뒷말, 설명 = 할수있는짓[짓]
        if 짓 == "담기":
            sandbox.경로검증(cwd or ".", 쓰기=True)
        return {"짓": 짓, "무엇": 설명, "자리": sandbox.표시경로(자리),
                **_돌리기(자리, 뒷말)}

    낮춘짓 = 짓.lower()
    for 막힌것, 이유 in 막는이유.items():
        if 막힌것 in 낮춘짓:
            raise sandbox.보안오류(이유)

    raise ValueError(
        "할 수 있는 짓: " + " · ".join(list(할수있는짓) + [메시지필요, "시작"])
    )


등록된도구 = {
    "git_do": git_do,
}
