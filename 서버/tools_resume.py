# -*- coding: utf-8 -*-
"""이어하기 — 새 대화에서 한 번에 앞 상황을 넘겨받는다.

대화창은 바뀌어도 여기 남은 것은 그대로다.
새 대화를 열면 이것부터 부르면 된다. 한 번으로 끝난다.

  숙주 : 기억 + 목표와 차례 + 최근에 손댄 것 + 지금 등급 + 첫인상(폴더 구조 · README · 깃)을 한꺼번에 돌려준다.
"""

from datetime import datetime
from pathlib import Path

import permission
import sandbox
import tools_memory
import tools_plan
import 설명서
import 첫인상

def 백업뿌리():
    return sandbox.백업칸()


def _최근에손댄것(개수: int = 12) -> list:
    """보관 폴더를 훑어 최근에 바뀐 파일을 최신순으로 모은다."""
    if not 백업뿌리().exists():
        return []

    본것 = {}
    for 때폴더 in sorted(백업뿌리().iterdir(), reverse=True):
        if not 때폴더.is_dir():
            continue
        for 파일 in 때폴더.rglob("*"):
            if not 파일.is_file():
                continue
            상대 = 파일.relative_to(때폴더)
            열쇠 = str(상대).replace("\\", "/")
            if 열쇠 in 본것:
                continue
            때 = 때폴더.name
            try:
                보기좋게 = datetime.strptime(때[:15], "%Y%m%d-%H%M%S").strftime(
                    "%m-%d %H:%M"
                )
            except ValueError:
                보기좋게 = 때
            본것[열쇠] = {"밭": 열쇠, "마지막손댐": 보기좋게}
            if len(본것) >= 개수:
                return list(본것.values())
    return list(본것.values())


def resume(_표시=True, **_):
    """앞 대화에서 어디까지 했는지 한 번에 돌려준다. (_표시=False: 넘김 파일이 부를 때 — 이 대화에 보낸 것으로 안 적는다)"""
    기억 = tools_memory.read_memory()
    계획 = tools_plan.plan_get()
    최근 = _최근에손댄것()

    규칙 = 설명서.숙주용()
    if 규칙["설명서"] and _표시:
        설명서.보냈다고적기()          # 이 대화는 설명서를 받았다 — 첫 도구 결과에 또 얹지 않는다
    try:
        첫 = 첫인상.만들기()
    except Exception:
        첫 = {}                 # 첫인상은 덤이다 — 못 만들어도 이어하기는 돈다
    안내 = []
    if 규칙["설명서"]:
        안내.append("'설명서' 는 사용자가 정한 규칙입니다. 먼저 읽고 끝까지 따르세요.")
    if 규칙["프로젝트규칙안내"]:
        안내.append("프로젝트 규칙 파일도 읽으세요.")
    if 첫:
        안내.append(첫인상.안내글(첫))
    if not 기억["있음"]:
        안내.append("적어둔 기억이 없습니다. 일을 마치면 우엉으로 적어 두세요.")
    if not 계획.get("task"):
        안내.append("세워둔 목표가 없습니다. 두 단계 넘는 일이면 감자로 세우세요.")
    if 계획.get("task") and 계획.get("progress", "").split("/")[0] != \
            계획.get("progress", "").split("/")[-1]:
        안내.append("끝나지 않은 목표가 있습니다. 이어서 할지 사용자에게 물어보세요.")

    return {
        "설명서": 규칙["설명서"],
        "프로젝트규칙": 규칙["프로젝트규칙안내"],
        "기준자리": str(sandbox.기준자리()),
        "첫인상": 첫,
        "등급": permission.등급읽기(),
        "지금쓸수있는것": permission.지금쓸수있는것(),
        "기억있음": 기억["있음"],
        "content": 기억.get("content", ""),
        "task": 계획.get("task"),
        "progress": 계획.get("progress"),
        "board": 계획.get("board"),
        "최근손댐": 최근,
        "안내": " ".join(안내) or "이어서 하면 됩니다.",
    }


등록된도구 = {
    "resume": resume,
}
