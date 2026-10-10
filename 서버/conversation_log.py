# -*- coding: utf-8 -*-
"""대화 원문 기록 — 답변과 되돌려 보낸 글을 손대지 않고 그대로 남긴다.

무엇이 오갔는지 나중에 그대로 다시 볼 수 있어야 한다.
요약하거나 다듬지 않는다. 원문 그대로다.

남는 곳: _archive/대화기록/YYYY-MM-DD.md
"""

from datetime import datetime
from pathlib import Path

import sandbox

기록뿌리 = Path(sandbox.설정["기준폴더"]).parent / "_archive" / "대화기록"
한파일최대 = 20 * 1024 * 1024   # 20MB 넘으면 더 안 쌓는다


def _오늘파일() -> Path:
    기록뿌리.mkdir(parents=True, exist_ok=True)
    return 기록뿌리 / (datetime.now().strftime("%Y-%m-%d") + ".md")


def 남기기(답변원문: str, 보낸글: str, 처리요약: list | None = None) -> dict:
    """한 차례(답변 → 처리 → 되돌림)를 통째로 남긴다."""
    파일 = _오늘파일()

    if 파일.exists() and 파일.stat().st_size > 한파일최대:
        return {"남김": False, "이유": "오늘 기록이 너무 커져서 멈췄습니다."}

    시각 = datetime.now().strftime("%H:%M:%S")
    조각 = [f"\n\n## {시각}\n"]

    if 처리요약:
        조각.append("| 나물 | 됨 | 한 줄 |")
        조각.append("|---|---|---|")
        for 항목 in 처리요약:
            이름 = str(항목.get("나물", "?"))
            됨 = "성공" if 항목.get("됨") else "실패"
            한줄 = str(항목.get("한줄", "")).replace("|", "\\|").replace("\n", " ")[:120]
            조각.append(f"| {이름} | {됨} | {한줄} |")
        조각.append("")

    조각.append("### 답변 원문")
    조각.append("~~~")
    조각.append(답변원문 or "(없음)")
    조각.append("~~~")
    조각.append("")
    조각.append("### 되돌려 보낸 글")
    조각.append("~~~")
    조각.append(보낸글 or "(없음)")
    조각.append("~~~")

    with open(파일, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(조각))

    return {"남김": True, "파일": str(파일)}


def 목차갱신() -> None:
    """대화기록 폴더에 날짜 목록을 만들어 둔다."""
    기록뿌리.mkdir(parents=True, exist_ok=True)
    날짜들 = sorted(
        (p for p in 기록뿌리.glob("*.md") if p.name != "_목차.md"), reverse=True
    )
    줄들 = ["# 대화기록 목차", "", "확장이 남긴 원문이다. 요약이 아니라 그대로다.", ""]
    for p in 날짜들:
        크기 = p.stat().st_size
        줄들.append(f"- [{p.stem}]({p.name}) — {크기:,}바이트")
    (기록뿌리 / "_목차.md").write_text("\n".join(줄들) + "\n", encoding="utf-8")
