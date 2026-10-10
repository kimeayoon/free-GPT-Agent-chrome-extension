# -*- coding: utf-8 -*-
"""시험 전부 한 번에 — 서버와 확장.

돌리는 법:  python 도구▸시험▸다돌리기.py

고친 뒤에는 반드시 이것부터 돌린다. 하나라도 빨간불이면 사용자에게 주지 않는다.
"""

import subprocess
import sys
from pathlib import Path

여기 = Path(__file__).resolve().parent


def 돌리기(이름: str, 명령: list) -> bool:
    print(f"\n━━━ {이름} ━━━")
    끝 = subprocess.run(명령, cwd=str(여기))
    좋음 = 끝.returncode == 0
    print(f"  → {'통과' if 좋음 else '실패'}")
    return 좋음


if __name__ == "__main__":
    결과 = [
        돌리기("서버", [sys.executable, "-X", "utf8", "서버시험.py"]),
        돌리기("일꾼 통합(진짜 깃)", [sys.executable, "-X", "utf8", "일꾼통합시험.py"]),
        돌리기("확장", ["node", "확장시험.js"]),
        돌리기("판", ["node", "판시험.js"]),
        돌리기("배경", ["node", "배경시험.js"]),
        돌리기("다듬기", ["node", "다듬기시험.js"]),
    ]
    print()
    if all(결과):
        print("전부 통과")
        raise SystemExit(0)
    print("실패한 묶음이 있습니다")
    raise SystemExit(1)
