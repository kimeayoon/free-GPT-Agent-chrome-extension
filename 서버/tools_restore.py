# -*- coding: utf-8 -*-
"""되돌리기 — 보관해 둔 원본으로 파일을 돌려놓는다.

오늘 두 번, 잘못 고쳐진 파일을 사람이 손으로 복구해야 했다.
보관은 계속 쌓이는데 정작 에이전트가 꺼내 쓸 방법이 없었다. 그걸 메운다.

  미역 : 밭만 주면 보관 목록을 보여주고, 때까지 주면 그때로 돌려놓는다.
"""

import shutil
from pathlib import Path

import sandbox

# 일터마다 따로 둔다. 부를 때 정해야 방을 옮겨도 맞는 자리를 본다.
def 보관뿌리():
    return sandbox.백업칸()


def _보관속경로(대상: Path) -> Path:
    return sandbox.보관속경로(대상)


def _보관목록(대상: Path) -> list:
    """이 파일의 보관본을 최신순으로 모은다."""
    if not 보관뿌리().exists():
        return []
    속 = _보관속경로(대상)
    찾은것 = []
    for 때폴더 in sorted(보관뿌리().iterdir(), reverse=True):
        if not 때폴더.is_dir():
            continue
        후보 = 때폴더 / 속
        if 후보.exists() and 후보.is_file():
            찾은것.append({
                "때": 때폴더.name,
                "크기": 후보.stat().st_size,
                "줄수": len(후보.read_bytes().splitlines()),
            })
    return 찾은것


def restore_file(path: str, when: str = "", **_):
    """보관본을 보여주거나, 지정한 때로 되돌린다."""
    대상 = sandbox.경로검증(path, 쓰기=True)
    목록 = _보관목록(대상)

    if not 목록:
        raise ValueError(
            f"보관된 것이 없습니다: {sandbox.표시경로(대상)}. "
            f"한 번도 고친 적이 없는 파일입니다."
        )

    if not when:
        return {
            "path": sandbox.표시경로(대상),
            "action": "보관 목록만 보여줌 (되돌리려면 '때' 를 넣으세요)",
            "count": len(목록),
            "backups": 목록,
        }

    고른것 = next((b for b in 목록 if b["때"] == when), None)
    if 고른것 is None:
        raise ValueError(
            f"그런 때가 없습니다: {when}. 쓸 수 있는 때: "
            + ", ".join(b["때"] for b in 목록[:8])
        )

    보관본 = 보관뿌리() / when / _보관속경로(대상)

    # 되돌리기 전에 지금 것도 한 번 보관해 둔다(되돌리기를 되돌릴 수 있게)
    from tools_edit import _백업
    지금것보관 = _백업(대상)

    대상.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(보관본, 대상)

    return {
        "path": sandbox.표시경로(대상),
        "action": f"{when} 시점으로 되돌림",
        "lines": len(대상.read_bytes().splitlines()),
        "backup": 지금것보관,
    }


등록된도구 = {
    "restore_file": restore_file,
}
