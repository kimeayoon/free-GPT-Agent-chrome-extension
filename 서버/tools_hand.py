# -*- coding: utf-8 -*-
"""손 — 키보드와 마우스를 움직이는 마늘.

사용자가 판에서 [허용] 을 눌러야만 쓴다(gate.py). 허가는 창 하나 + 정해진 시간 동안만 간다.
  · 창 허가: 그 창이 맨 앞에 있을 때만 입력을 보낸다. 좌표는 창의 왼쪽 위 모서리 기준이고 창 밖은 거부한다.
  · 화면 전체('*') 허가: 좌표는 화면 기준. 가장 위험하므로 최대 5분.
  · 동작마다 허가가 살아 있는지 · 앞 창이 맞는지 다시 본다. 사용자가 판에서 [그만] 을 누르면 바로 멈춘다.
  · 입력은 1초에 60번까지, 한 번의 순서는 40단계까지.
  · 보낸 입력은 시각(초 단위 소수)과 함께 결과에 돌려주고 프로젝트의 .agent/손기록.jsonl 에 적는다.
"""

import json
import re
import time
from collections import deque

import gate
import sandbox
import 창조작

순서최대단계 = 40
순서최대쉼ms = 5000
키오래최대ms = 2000
초당최대입력 = 60
허가당최대입력 = 20000
막은키 = {"win"}                     # 시작 메뉴·바탕화면 단축키는 보내지 않는다
_지금초 = time.perf_counter          # 시험에서 바꿔 끼운다
_지금시각 = time.time
_잠자기 = time.sleep
_보낸때 = deque()                    # 최근 1초의 입력 시각(속도 제한)

짓들 = ("앞으로", "이동", "클릭", "누름", "뗌", "드래그", "스크롤", "키", "키누름", "키뗌", "글자", "순서", "다했음")
단추이름 = {"왼": "왼", "왼쪽": "왼", "left": "왼", "오른": "오른", "오른쪽": "오른", "right": "오른",
          "가운데": "가운데", "middle": "가운데"}


def _정수(값, 이름: str, 기본=None):
    if 값 is None or str(값).strip() == "":
        return 기본
    try:
        return int(float(str(값).strip()))
    except ValueError:
        raise ValueError(f'"{이름}" 은 숫자여야 합니다.')


def _단추(값) -> str:
    글 = str(값 or "").strip().lower()
    if not 글:
        return "왼"
    if 글 not in 단추이름:
        raise ValueError("버튼은 왼 · 오른 · 가운데 중 하나입니다.")
    return 단추이름[글]


def _점읽기(글) -> tuple:
    조각 = re.split(r"[\s,]+", str(글 or "").strip())
    if len(조각) != 2:
        raise ValueError('"곳" 은 가로,세로 두 숫자입니다. 예: 곳 640,360')
    try:
        return int(float(조각[0])), int(float(조각[1]))
    except ValueError:
        raise ValueError('"곳" 은 가로,세로 두 숫자입니다. 예: 곳 640,360')


def _키들(글) -> list:
    """'ctrl+shift+a' → 가상키 코드 목록."""
    이름들 = [p for p in str(글 or "").strip().split("+") if p.strip()]
    if not 이름들:
        raise ValueError('"키" 가 비었습니다. 예: 키 w   또는   키 ctrl+c')
    for 이름 in 이름들:
        if 이름.strip().lower() in 막은키:
            raise ValueError("윈도우 키는 보내지 않습니다.")
    return [창조작.키코드(이름) for 이름 in 이름들]


class _자리:
    """한 번의 부름 동안 쓰는 겨냥(창 · 허가) — 동작마다 다시 확인한다."""

    def __init__(self, 창패턴: str, 허가: dict, 창):
        self.창패턴 = 창패턴
        self.허가 = 허가
        self.창 = 창
        self.시작 = _지금초()
        self.시작시각 = _지금시각()
        self.기록 = []

    def 확인(self):
        # 사용자가 [그만] 을 눌렀거나 시간이 다 됐으면 여기서 멈춘다
        지금허가 = gate.찾기("손", self.창["제목"] if self.창 else None)
        if 지금허가 is None:
            raise ValueError("손 허가가 끝났습니다(시간이 다 됐거나 사용자가 그만하게 했습니다). 필요하면 다시 요청하세요.")
        self.허가 = 지금허가
        if self.허가.get("쓴수", 0) >= 허가당최대입력:
            raise ValueError("이 허가로 보낼 수 있는 입력 수를 다 썼습니다. 다시 요청하세요.")
        if self.창 is not None:
            앞 = 창조작.앞창()
            if not 앞 or not gate.덮나(self.허가, 앞["제목"]):
                raise ValueError("허가받은 창이 맨 앞에 없습니다. 입력을 보내지 않았습니다. "
                                 "사용자가 그 창을 앞으로 가져오거나 '앞으로' 짓을 쓰세요.")
            # 창이 움직였을 수 있으니 네모를 새로 읽는다
            self.창 = 앞
        지금 = _지금초()
        while _보낸때 and 지금 - _보낸때[0] > 1.0:
            _보낸때.popleft()
        if len(_보낸때) >= 초당최대입력:
            raise ValueError(f"입력이 너무 빠릅니다(1초에 {초당최대입력}번까지). 쉬기를 넣으세요.")
        _보낸때.append(지금)
        gate.쓰기(self.허가)

    def 절대점(self, 글) -> tuple:
        x, y = _점읽기(글)
        if self.창 is None:
            return x, y
        가로, 세로 = self.창["오른"] - self.창["왼"], self.창["아래"] - self.창["위"]
        if not (0 <= x < 가로 and 0 <= y < 세로):
            raise ValueError(f"곳이 허가받은 창 밖입니다(창 크기 {가로}x{세로}, 곳은 창의 왼쪽 위 모서리 기준).")
        return self.창["왼"] + x, self.창["위"] + y

    def 적기(self, 짓: str, 자세: str = "", 때=None):
        """입력 하나를 적는다. 때 = 그 동작이 시작된 초(_지금초 기준). 누르고 기다리는 키도 '누른 때' 가 찍힌다."""
        때 = _지금초() if 때 is None else 때
        지난 = _지금초() - 때
        self.기록.append({"번": len(self.기록) + 1, "짓": 짓, **({"자세": 자세} if 자세 else {}),
                        "초": round(때 - self.시작, 4), "시각ms": int((_지금시각() - 지난) * 1000)})


def _한단계(자리: _자리, 짓: str, 곳="", 끝곳="", 키글="", 글="", 값="", 단추="", 오래="", 번="") -> None:
    """동작 하나를 보낸다. 동작 앞에 허가를 다시 확인한다."""
    자리.확인()
    시작 = _지금초()
    if 짓 == "이동":
        x, y = 자리.절대점(곳)
        창조작.마우스이동(x, y)
        자리.적기("이동", f"{x},{y}", 때=시작)
    elif 짓 == "클릭":
        if str(곳).strip():
            x, y = 자리.절대점(곳)
            창조작.마우스이동(x, y)
        회 = max(1, min(_정수(번, "번", 1), 3))
        for _ in range(회):
            창조작.마우스단추(_단추(단추), "누름")
            창조작.마우스단추(_단추(단추), "뗌")
        자리.적기("클릭", f"{_단추(단추)} x{회}", 때=시작)
    elif 짓 in ("누름", "뗌"):
        창조작.마우스단추(_단추(단추), 짓)
        자리.적기(짓, _단추(단추), 때=시작)
    elif 짓 == "드래그":
        x1, y1 = 자리.절대점(곳)
        x2, y2 = 자리.절대점(끝곳)
        창조작.마우스이동(x1, y1)
        창조작.마우스단추(_단추(단추), "누름")
        _잠자기(0.03)
        창조작.마우스이동(x2, y2)
        _잠자기(0.03)
        창조작.마우스단추(_단추(단추), "뗌")
        자리.적기("드래그", f"{x1},{y1}→{x2},{y2}", 때=시작)
    elif 짓 == "스크롤":
        창조작.휠(max(-30, min(_정수(값, "값", 0), 30)))
        자리.적기("스크롤", str(값), 때=시작)
    elif 짓 in ("키", "키누름", "키뗌"):
        코드들 = _키들(키글)
        if 짓 == "키뗌":
            for 코드 in reversed(코드들):
                창조작.키(코드, "뗌")
        else:
            for 코드 in 코드들:
                창조작.키(코드, "누름")
            if 짓 == "키":
                ms = max(0, min(_정수(오래, "오래", 0), 키오래최대ms))
                if ms:
                    _잠자기(ms / 1000)
                for 코드 in reversed(코드들):
                    창조작.키(코드, "뗌")
        자리.적기(짓, str(키글), 때=시작)
    elif 짓 == "글자":
        if not str(글):
            raise ValueError('"속" 이 비었습니다.')
        창조작.글자(str(글)[:500])
        자리.적기("글자", f"{min(len(str(글)), 500)}자", 때=시작)
    else:
        raise ValueError(f"모르는 동작입니다: {짓}")


def _순서읽기(글: str) -> list:
    """한 줄에 한 단계. 이동 x,y · 클릭 [x,y] [왼|오른|가운데] [번] · 누름 [단추] · 뗌 [단추] · 드래그 x1,y1 x2,y2 ·
    스크롤 n · 키 이름 [오래ms] · 키누름 이름 · 키뗌 이름 · 글자 글 · 쉬기 ms"""
    단계들 = []
    for 줄 in str(글 or "").splitlines():
        줄 = 줄.strip()
        if not 줄:
            continue
        머리, _, 나머지 = 줄.partition(" ")
        나머지 = 나머지.strip()
        조각 = 나머지.split()
        if 머리 == "이동":
            단계들.append({"짓": "이동", "곳": 나머지})
        elif 머리 == "클릭":
            점 = ""
            단추 = ""
            회 = ""
            for 말 in 조각:
                if "," in 말:
                    점 = 말
                elif 말.isdigit():
                    회 = 말
                else:
                    단추 = 말
            단계들.append({"짓": "클릭", "곳": 점, "단추": 단추, "번": 회})
        elif 머리 in ("누름", "뗌"):
            단계들.append({"짓": 머리, "단추": 조각[0] if 조각 else ""})
        elif 머리 == "드래그":
            if len(조각) < 2:
                raise ValueError("드래그 줄은 '드래그 x1,y1 x2,y2' 꼴입니다.")
            단계들.append({"짓": "드래그", "곳": 조각[0], "끝곳": 조각[1], "단추": 조각[2] if len(조각) > 2 else ""})
        elif 머리 == "스크롤":
            단계들.append({"짓": "스크롤", "값": 나머지})
        elif 머리 in ("키", "키누름", "키뗌"):
            단계들.append({"짓": 머리, "키글": 조각[0] if 조각 else "", "오래": 조각[1] if len(조각) > 1 else ""})
        elif 머리 == "글자":
            단계들.append({"짓": "글자", "글": 나머지})
        elif 머리 == "쉬기":
            단계들.append({"짓": "쉬기", "값": 나머지})
        else:
            raise ValueError(f"순서의 모르는 줄입니다: '{줄[:30]}'. 이동·클릭·누름·뗌·드래그·스크롤·키·키누름·키뗌·글자·쉬기 로 시작해야 합니다.")
    return 단계들


def _기록남기기(자리: _자리, 짓: str):
    """프로젝트 .agent/손기록.jsonl 에 이번 부름의 입력 시각을 적는다(못 적어도 입력은 이미 간 것)."""
    if not 자리.기록:
        return
    try:
        대상 = sandbox.경로검증(".agent/손기록.jsonl", 쓰기=True)
        대상.parent.mkdir(parents=True, exist_ok=True)
        with open(대상, "a", encoding="utf-8") as f:
            for 줄 in 자리.기록:
                f.write(json.dumps({"창": 자리.창패턴, "부름": 짓, "부름시작ms": int(자리.시작시각 * 1000), **줄},
                                   ensure_ascii=False) + "\n")
    except Exception:
        pass


def hand(action: str = "", window: str = "", point: str = "", end_point: str = "", keys: str = "",
         content: str = "", value: str = "", button: str = "", hold_ms: str = "", count: str = "",
         minutes: str = "", why: str = "", **_):
    """키보드·마우스를 움직인다. 허가(판의 [허용])가 있어야 한다."""
    짓 = (action or "").strip()
    if 짓 not in 짓들:
        raise ValueError("짓 은 " + " · ".join(짓들) + " 중 하나입니다.")
    창패턴 = gate.창다듬기(window)

    if 짓 == "다했음":
        창 = _창찾기(창패턴) if 창패턴 != "*" else None
        허가 = gate.찾기("손", 창["제목"] if 창 else None)
        if 허가 is None:
            return {"거둠": 0, "안내": "거둘 허가가 없습니다."}
        return {"거둠": gate.그만(허가["번호"]), "안내": "손 허가를 거뒀습니다. 다시 쓰려면 새로 요청해야 합니다."}

    창 = None
    if 창패턴 != "*":
        창 = _창찾기(창패턴)
        if 창 is None:
            raise ValueError(f"'{창패턴}' 이 제목에 든 창을 못 찾았습니다(접혔거나 닫혔을 수 있습니다).")
    허가 = gate.찾기("손", 창["제목"] if 창 else None)
    if 허가 is None:
        return gate.요청하기("손", 창패턴, minutes, why)

    자리 = _자리(창패턴, 허가, 창)
    if 짓 == "앞으로":
        if 창 is None:
            raise ValueError("화면 전체 허가에서는 앞으로 가져올 창이 없습니다. 창 이름을 적으세요.")
        됨 = 창조작.앞으로(창["핸들"])
        return {"앞으로": bool(됨), "안내": "윈도우가 막으면 앞으로 오지 않을 수 있습니다. 안 오면 사용자에게 그 창을 눌러 달라고 하세요."}

    try:
        if 짓 == "순서":
            단계들 = _순서읽기(content)
            if not 단계들:
                raise ValueError('"속" 에 한 줄에 한 단계씩 적으세요. 예: 이동 640,360 / 클릭 / 쉬기 100 / 키 w 300')
            if len(단계들) > 순서최대단계:
                raise ValueError(f"한 번에 {순서최대단계}단계까지입니다({len(단계들)}단계).")
            쉼합 = sum(max(0, _정수(s.get("값"), "쉬기", 0)) for s in 단계들 if s["짓"] == "쉬기")
            if 쉼합 > 순서최대쉼ms:
                raise ValueError(f"쉬기 합이 너무 깁니다({쉼합}ms > {순서최대쉼ms}ms).")
            for 단 in 단계들:
                if 단["짓"] == "쉬기":
                    쉬기시작 = _지금초()
                    _잠자기(max(0, _정수(단.get("값"), "쉬기", 0)) / 1000)
                    자리.적기("쉬기", str(단.get("값")), 때=쉬기시작)
                else:
                    _한단계(자리, **단)
        else:
            _한단계(자리, 짓, 곳=point, 끝곳=end_point, 키글=keys, 글=content, 값=value, 단추=button, 오래=hold_ms, 번=count)
    finally:
        _기록남기기(자리, 짓)

    남은 = max(0, int(자리.허가["끝"] - gate._지금()))
    return {"보냄": len(자리.기록), "단계들": 자리.기록, "시작시각ms": int(자리.시작시각 * 1000),
            "걸린초": round(_지금초() - 자리.시작, 4), "허가남은초": 남은,
            "안내": "단계마다 초는 이 부름이 시작된 때부터 흐른 시간입니다(오이의 시각ms 와 맞춰 보세요)."}


def _창찾기(패턴: str):
    for 창 in 창조작.창들():
        if 패턴.lower() in 창["제목"].lower():
            return 창
    return None


등록된도구 = {
    "hand": hand,
}
