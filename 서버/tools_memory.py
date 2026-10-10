# -*- coding: utf-8 -*-
"""프로젝트 기억 — 매번 처음부터 훑지 않게 알아낸 것을 적어 둔다.

지금까지는 대화가 바뀔 때마다 가지 → 미나리 → 열무로 구조를 다시 파악했다.
그 낭비를 줄이려고, 한 번 알아낸 것을 적어 둔다.

두 군데에 같이 둔다.
  ① 방 칸   서버/방/<쪽번호>/기억.md      — 방마다 따로. 되돌릴 때 이것을 쓴다
  ② 프로젝트 <일하는 폴더>/.agent/기억.md  — 프로젝트를 옮기거나 방 목록이
     날아가도 같이 따라간다. 실제로 방 목록이 통째로 비는 일이 있었다.

읽을 때는 방 칸을 먼저 보고, 없으면 프로젝트 쪽을 본다.

  더덕 : 기억 보기
  우엉 : 기억 적기
"""

from datetime import datetime
from pathlib import Path

import sandbox
import 안전파일

기억최대 = 20000   # 너무 커지면 읽는 값이 없다


def _기억파일() -> Path:
    import rooms
    return rooms.방자료칸() / "기억.md"


def _같이쓰는기억파일() -> Path | None:
    """ChatGPT 프로젝트의 방들이 같이 쓰는 기억. 프로젝트 밖 방이면 None."""
    import rooms
    칸 = rooms.프로젝트기억칸()
    return (칸 / "기억.md") if 칸 else None


def _프로젝트기억파일() -> Path | None:
    """일하는 폴더 안의 기억 파일. 폴더를 안 정했으면 None."""
    import rooms
    밭 = rooms.지금밭()
    return (밭 / ".agent" / "기억.md") if 밭 else None


def read_memory(**_):
    """적어둔 것을 읽는다. 방 칸을 먼저 보고, 없으면 프로젝트 쪽을 본다."""
    # 같은 ChatGPT 프로젝트의 다른 대화가 적은 것도 보이게 같이 쓰는 칸을 먼저 본다.
    for 파일, 어디 in ((_같이쓰는기억파일(), "ChatGPT 프로젝트"), (_기억파일(), "방"),
                     (_프로젝트기억파일(), "프로젝트")):
        if 파일 is None or not 파일.exists():
            continue
        본문 = 안전파일.글읽기(파일)
        if not 본문.strip():
            continue
        return {
            "있음": True,
            "path": sandbox.표시경로(파일),
            "어디": 어디,
            "lines": len(본문.splitlines()),
            "content": 본문,
        }

    return {
        "있음": False,
        "content": "",
        "안내": "아직 적어둔 것이 없습니다. 알아낸 것을 우엉으로 적어 두세요.",
    }


def write_memory(content: str = "", append: bool = False, **_):
    """기억을 적는다. append 가 참이면 뒤에 덧붙인다."""
    if content is None:
        content = ""
    if not content.strip() and not append:
        raise ValueError('"속" 이 비었습니다. 적을 내용을 넣으세요.')

    파일 = _기억파일()

    # 덧붙일 때의 '앞 내용' 은 읽을 때와 같은 자리에서 가져온다.
    # 방 쪽만 보면, 방 칸이 없어졌을 때 프로젝트에 남아 있던 기억을 덮어써 버린다.
    앞것 = read_memory()
    기존 = 앞것.get("content", "") if 앞것.get("있음") else ""

    if append:
        도장 = datetime.now().strftime("%Y-%m-%d %H:%M")
        새본문 = (기존.rstrip() + f"\n\n<!-- {도장} -->\n" + content.strip() + "\n").lstrip()
    else:
        새본문 = content

    if len(새본문) > 기억최대:
        raise ValueError(
            f"기억이 너무 깁니다({len(새본문):,}자 > {기억최대:,}). "
            f"오래된 것을 지우고 짧게 간추리세요."
        )

    안전파일.쓰기(파일, 새본문, newline="\n")

    같이쓰는파일 = _같이쓰는기억파일()
    if 같이쓰는파일 is not None:
        안전파일.쓰기(같이쓰는파일, 새본문, newline="\n")

    # 프로젝트 쪽에도 같이 둔다. 한쪽이 없어져도 남아 있게.
    같이둔곳 = ""
    프로젝트파일 = _프로젝트기억파일()
    if 프로젝트파일 is not None:
        try:
            프로젝트파일.parent.mkdir(parents=True, exist_ok=True)
            안전파일.쓰기(프로젝트파일, 새본문, newline="\n")
            같이둔곳 = sandbox.표시경로(프로젝트파일)
        except OSError as e:
            같이둔곳 = f"(프로젝트 쪽에는 못 적었습니다: {e})"

    return {
        "path": sandbox.표시경로(파일),
        "같이둔곳": 같이둔곳,
        "action": "덧붙임" if append else "새로 씀",
        "lines": len(새본문.splitlines()),
    }


등록된도구 = {
    "read_memory": read_memory,
    "write_memory": write_memory,
}
