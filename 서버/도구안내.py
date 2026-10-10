# -*- coding: utf-8 -*-
"""도구 첫 사용 안내 — 드문 도구의 자세한 쓰는 법을 처음 부를 때 한 번 알려 준다.

프로젝트 지침은 8000자 한도라 자주 안 쓰는 도구(예약 · 일꾼 · 바깥 도구 · 받아오기 · 깃)의 설명을 다 못 담는다.
그래서 지침에는 한두 줄만 두고, 자세한 것은 문서/도구_첫사용_안내.md 에 둔다.
GPT 가 한 대화(방 + ChatGPT 대화 번호)에서 그 도구를 처음 부르면 결과에 `사용법` 으로 얹는다 — 성공이든 실패든.
(처음 부른 호출이 인자를 틀려도 결과에 쓰는 법이 같이 와서 바로 고쳐 다시 부를 수 있다.)
서버를 다시 켜면 한 번 더 간다(기록은 메모리에만 있다).
"""

import re
from pathlib import Path

import 설명서

안내파일 = Path(__file__).resolve().parent.parent / "문서" / "도구_첫사용_안내.md"
사람용표시 = "<!-- 여기부터 사람용 메모"
절최대글자 = 1500
_보낸것: dict = {}          # (방 쪽번호, ChatGPT 대화 번호) → 이미 안내한 도구 이름 집합


def 안내들() -> dict:
    """{나물 이름: 안내 글}. 파일이 없거나 깨져도 빈 사전(도구는 그대로 돈다)."""
    try:
        글 = 안내파일.read_text(encoding="utf-8")
    except OSError:
        return {}
    자리 = 글.find(chr(10) + 사람용표시)
    if 자리 != -1:
        글 = 글[:자리]
    결과 = {}
    조각 = re.split(r"(?m)^## (\S+)\s*$", 글)
    for 번 in range(1, len(조각) - 1, 2):
        내용 = 조각[번 + 1].strip()
        if len(내용) > 절최대글자:
            내용 = 내용[:절최대글자].rstrip() + "\n… (안내가 길어 여기서 잘렸습니다)"
        if 내용:
            결과[조각[번]] = 내용
    return 결과


def 첫사용얹기(답: dict, 도구이름: str, 이름키: str = "나물") -> dict:
    """이 대화에서 이 도구를 처음 부른 것이면 결과에 `사용법` 을 얹어 돌려준다."""
    if not isinstance(답, dict) or "사용법" in 답:
        return 답
    방, 대화 = 설명서._지금대화()
    if not 방:
        return 답
    안내 = 안내들().get(도구이름)
    if not 안내:
        return 답
    열쇠 = (방, 대화)
    본것 = _보낸것.setdefault(열쇠, set())
    if 도구이름 in 본것:
        return 답
    본것.add(도구이름)
    새 = {}
    넣음 = False
    for 번, (키, 값) in enumerate(답.items()):
        if 번 == 2 and not 넣음:
            새["사용법"] = 안내
            넣음 = True
        새[키] = 값
    if not 넣음:
        새["사용법"] = 안내
    return 새
