# -*- coding: utf-8 -*-
"""눈 — 그림을 채팅에 붙이는 호박, 화면을 보는 오이.

호박(attach_image): 파일의 그림을 (필요하면 잘라 · 키우고 · 줄여서) 이 결과와 함께 ChatGPT 채팅에 붙인다.
오이(eye): 찰칵(화면·창·영역을 찍어 붙임) · 창목록 · 장면표(연속으로 찍어 한 장의 표로).
  화면은 사용자 몰래 보면 안 되므로 오이는 판에서 [허용] 을 눌러야 쓴다(gate.py — 창 하나 · 정해진 시간).

그림은 결과 JSON 의 `_첨부` 로 나간다. 밑줄로 시작하는 키는 GPT 에게 글로 가지 않고, 확장이 채팅에 파일로 붙인다.
"""

import base64
import io
import math
import re
import time
from datetime import datetime

import gate
import sandbox
import 창조작

그림최대개수 = 6
기본최대변 = 1280
가장큰최대변 = 2048
표기본최대변 = 1600
첨부합계최대바이트 = 8 * 1024 * 1024
한장최대바이트 = 1_500_000
장면최소 = 2
장면최대 = 12
틈최소ms = 30
틈최대ms = 1000
_지금초 = time.perf_counter          # 시험에서 바꿔 끼운다
_지금시각 = time.time                # 시계 시각(초) — 입력 시각과 맞춰 보는 데 쓴다
_잠자기 = time.sleep


def _정수(값, 이름: str, 기본=None, 작게=None, 크게=None):
    if 값 is None or str(값).strip() == "":
        return 기본
    try:
        수 = int(float(str(값).strip()))
    except ValueError:
        raise ValueError(f'"{이름}" 은 숫자여야 합니다.')
    if 작게 is not None:
        수 = max(작게, 수)
    if 크게 is not None:
        수 = min(크게, 수)
    return 수


def _영역읽기(글) -> tuple | None:
    """'x1,y1,x2,y2' → (x1, y1, x2, y2). 비었으면 None."""
    if not str(글 or "").strip():
        return None
    조각 = re.split(r"[\s,]+", str(글).strip())
    if len(조각) != 4:
        raise ValueError('"영역" 은 왼쪽,위,오른쪽,아래 네 숫자입니다. 예: 영역 559,188,578,202')
    try:
        x1, y1, x2, y2 = (int(float(v)) for v in 조각)
    except ValueError:
        raise ValueError('"영역" 은 왼쪽,위,오른쪽,아래 네 숫자입니다. 예: 영역 559,188,578,202')
    if x2 <= x1 or y2 <= y1:
        raise ValueError('"영역" 은 오른쪽·아래가 왼쪽·위보다 커야 합니다.')
    return (x1, y1, x2, y2)


def _다듬기(그림, 최대변: int, 배율=None):
    """배율(키우기, 픽셀이 보이게 가까운 점 방식) 뒤 긴 변이 최대변을 넘으면 줄인다."""
    from PIL import Image
    그림 = 그림.convert("RGB")
    if 배율:
        배 = float(배율)
        if 배 <= 0 or 배 > 32:
            raise ValueError('"배율" 은 0 보다 크고 32 이하여야 합니다.')
        if 배 != 1:
            그림 = 그림.resize((max(1, int(그림.width * 배)), max(1, int(그림.height * 배))),
                             Image.NEAREST if 배 > 1 else Image.LANCZOS)
    긴변 = max(그림.size)
    if 긴변 > 최대변:
        비율 = 최대변 / 긴변
        그림 = 그림.resize((max(1, int(그림.width * 비율)), max(1, int(그림.height * 비율))), Image.LANCZOS)
    return 그림


def _인코딩(그림):
    """(바이트, 종류, 확장자). 작으면 PNG, 크면 JPEG, 그래도 크면 줄여 가며."""
    from PIL import Image
    현재 = 그림
    for _ in range(6):
        글 = io.BytesIO()
        현재.save(글, "PNG", optimize=True)
        if len(글.getvalue()) <= 한장최대바이트:
            return 글.getvalue(), "image/png", "png"
        글 = io.BytesIO()
        현재.convert("RGB").save(글, "JPEG", quality=85)
        if len(글.getvalue()) <= 한장최대바이트:
            return 글.getvalue(), "image/jpeg", "jpg"
        현재 = 현재.resize((max(1, int(현재.width * 0.75)), max(1, int(현재.height * 0.75))), Image.LANCZOS)
    글 = io.BytesIO()
    현재.convert("RGB").save(글, "JPEG", quality=70)
    return 글.getvalue(), "image/jpeg", "jpg"


def _첨부항목(이름: str, 그림, 최대변: int, 배율=None) -> tuple:
    """(첨부 사전, 요약 사전)."""
    보낼 = _다듬기(그림, 최대변, 배율)
    바이트, 종류, 확장 = _인코딩(보낼)
    이름 = re.sub(r"[^\w.\-가-힣]+", "_", 이름)[:60] or "그림"
    이름 = 이름 if 이름.lower().endswith("." + 확장) else re.sub(r"\.[A-Za-z0-9]+$", "", 이름) + "." + 확장
    return ({"이름": 이름, "종류": 종류, "자료": base64.b64encode(바이트).decode("ascii")},
            {"이름": 이름, "가로": 보낼.width, "세로": 보낼.height, "크기": len(바이트)})


def _합계검사(첨부들: list):
    합계 = sum(len(a["자료"]) * 3 // 4 for a in 첨부들)
    if 합계 > 첨부합계최대바이트:
        raise ValueError(f"붙일 그림이 너무 큽니다({합계 // 1024:,}KB). 최대변을 줄이거나 장수를 줄이세요.")


# ── 호박 ─────────────────────────────────────────────────────────

def attach_image(path: str = "", crop: str = "", scale: str = "", max_side: str = "", **_):
    """파일의 그림을 채팅에 붙인다. 여러 장은 쉼표로. 영역(자르기)·배율(키우기)·최대변(줄이기)."""
    경로들 = [p.strip() for p in re.split(r"[,\n]", str(path or "")) if p.strip()]
    if not 경로들:
        raise ValueError('"밭" 이 비었습니다. 그림 파일 자리를 적으세요. 예: 밭 captures▸a.png')
    if len(경로들) > 그림최대개수:
        raise ValueError(f"한 번에 {그림최대개수}장까지 붙일 수 있습니다({len(경로들)}장을 받음).")
    최대변 = _정수(max_side, "최대변", 기본최대변, 64, 가장큰최대변)
    영역 = _영역읽기(crop)
    from PIL import Image
    첨부들, 요약들 = [], []
    for 자리 in 경로들:
        대상 = sandbox.경로검증(자리)
        if not 대상.exists() or 대상.is_dir():
            raise FileNotFoundError(f"그림 파일이 없습니다: {대상}")
        try:
            with Image.open(대상) as 원:
                원.load()
                그림 = 원.copy()
        except Exception:
            raise ValueError(f"그림 파일이 아닙니다(png·jpg·bmp·gif·webp 만 됩니다): {대상.name}")
        원래 = (그림.width, 그림.height)
        if 영역:
            x1, y1, x2, y2 = 영역
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(그림.width, x2), min(그림.height, y2)
            if x2 <= x1 or y2 <= y1:
                raise ValueError(f"영역이 그림 밖입니다(그림 크기 {원래[0]}x{원래[1]}).")
            그림 = 그림.crop((x1, y1, x2, y2))
        이름 = (f"자름_{대상.stem}" if 영역 else 대상.stem)
        첨부, 요약 = _첨부항목(이름, 그림, 최대변, scale or None)
        요약["원래크기"] = f"{원래[0]}x{원래[1]}"
        첨부들.append(첨부)
        요약들.append(요약)
    _합계검사(첨부들)
    return {"붙임": len(첨부들), "그림들": 요약들, "_첨부": 첨부들,
            "안내": f"그림 {len(첨부들)}장이 이 결과 메시지에 함께 붙어 갑니다. 그림을 보고 이어서 하세요."}


# ── 오이 ─────────────────────────────────────────────────────────

def _창찾기(패턴: str):
    """제목에 패턴이 든 창(맨 위에 있는 것). 없으면 None."""
    for 창 in 창조작.창들():
        if 패턴.lower() in 창["제목"].lower():
            return 창
    return None


def _저장(그림, 이름: str) -> str:
    """프로젝트의 .agent/캡처 에 원본 크기로 남긴다. 못 해도(일할 곳 없음 등) 보여 주는 것은 된다."""
    try:
        대상 = sandbox.경로검증(f".agent/캡처/{이름}", 쓰기=True)
        대상.parent.mkdir(parents=True, exist_ok=True)
        그림.save(대상, "PNG")
        return str(대상)
    except Exception:
        return ""


def _겨냥(창패턴: str, 영역):
    """(허가에 쓸 제목 또는 None, 찍을 네모(화면 좌표), 창 사전 또는 None)."""
    if 창패턴 != "*":
        창 = _창찾기(창패턴)
        if 창 is None:
            raise ValueError(f"'{창패턴}' 이 제목에 든 창을 못 찾았습니다. 접혀 있거나 닫혔을 수 있습니다. "
                             "오이 짓 창목록 으로 열린 창을 보세요.")
        왼, 위, 오른, 아래 = 창["왼"], 창["위"], 창["오른"], 창["아래"]
        if 영역:
            x1, y1, x2, y2 = 영역
            네모 = (왼 + max(0, x1), 위 + max(0, y1), min(오른, 왼 + x2), min(아래, 위 + y2))
            if 네모[2] <= 네모[0] or 네모[3] <= 네모[1]:
                raise ValueError("영역이 창 밖입니다(영역은 창의 왼쪽 위 모서리 기준입니다).")
            return 창["제목"], 네모, 창
        return 창["제목"], (왼, 위, 오른, 아래), 창
    if 영역:
        return None, 영역, None
    왼, 위, 가로, 세로 = 창조작.가상화면()
    return None, (왼, 위, 왼 + 가로, 위 + 세로), None


def _허가(창패턴: str, 제목, 분, 이유):
    """(허가, None) 또는 (None, 기다림 응답)."""
    허가 = gate.찾기("눈", 제목)
    if 허가 is None:
        return None, gate.요청하기("눈", 창패턴, 분, 이유)
    return 허가, None


def _표만들기(그림들: list, 시각들: list, 최대변: int):
    """프레임들을 시각 이름표를 달아 한 장의 격자 그림으로."""
    from PIL import Image, ImageDraw
    n = len(그림들)
    열 = min(4, max(1, math.ceil(math.sqrt(n))))
    줄 = math.ceil(n / 열)
    칸너비 = max(80, 최대변 // 열)
    비율 = 칸너비 / 그림들[0].width
    칸높이 = max(1, int(그림들[0].height * 비율))
    표 = Image.new("RGB", (칸너비 * 열, 칸높이 * 줄), (20, 20, 20))
    글씨 = ImageDraw.Draw(표)
    for i, (그림, 초) in enumerate(zip(그림들, 시각들)):
        작게 = 그림.convert("RGB").resize((칸너비, 칸높이), Image.LANCZOS)
        x, y = (i % 열) * 칸너비, (i // 열) * 칸높이
        표.paste(작게, (x, y))
        이름 = f"#{i + 1}  +{초:.3f}s"
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            글씨.text((x + 5 + dx, y + 4 + dy), 이름, fill=(0, 0, 0))
        글씨.text((x + 5, y + 4), 이름, fill=(255, 235, 60))
    return 표


def eye(action: str = "찰칵", window: str = "", region: str = "", frames: str = "", gap_ms: str = "",
        scale: str = "", max_side: str = "", minutes: str = "", why: str = "", **_):
    """화면을 본다. 짓: 찰칵(기본) · 창목록 · 장면표. 허가가 없으면 사용자에게 승인을 청한다."""
    짓 = (action or "찰칵").strip()
    if 짓 not in ("찰칵", "창목록", "장면표"):
        raise ValueError("짓 은 찰칵 · 창목록 · 장면표 중 하나입니다.")
    창패턴 = gate.창다듬기(window)
    영역 = _영역읽기(region)
    최대변 = _정수(max_side, "최대변", None, 64, 가장큰최대변)

    if 짓 == "창목록":
        if not gate.있나("눈"):
            return gate.요청하기("눈", 창패턴, minutes, why)
        보임 = []
        for 창 in 창조작.창들():
            if gate.찾기("눈", 창["제목"]) is not None:
                보임.append({"제목": 창["제목"].strip()[:80], "영역": f'{창["왼"]},{창["위"]},{창["오른"]},{창["아래"]}',
                            "앞": 창["앞"]})
        return {"개수": len(보임), "창들": 보임,
                "안내": "허가받은 창만 보입니다. 오이 / 창 제목의 일부 로 찍으세요."}

    제목, 네모, 창 = _겨냥(창패턴, 영역)
    허가, 기다림 = _허가(창패턴, 제목, minutes, why)
    if 기다림 is not None:
        return 기다림

    if 짓 == "찰칵":
        찍은때 = int(_지금시각() * 1000)
        그림 = 창조작.잡기(네모)
        gate.쓰기(허가)
        이름 = "찰칵_" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        저장 = _저장(그림, 이름 + ".png")
        첨부, 요약 = _첨부항목(이름, 그림, 최대변 or 기본최대변, scale or None)
        _합계검사([첨부])
        귀띔 = ""
        if 창 is not None and not 창["앞"]:
            귀띔 = "그 창이 맨 앞이 아니라서 다른 창이 위에 겹쳐 찍혔을 수 있습니다."
        return {"창": 제목 or "화면 전체", "영역": f"{네모[0]},{네모[1]},{네모[2]},{네모[3]}",
                "가로": 그림.width, "세로": 그림.height, "시각ms": 찍은때, "저장": 저장, "그림": 요약, "_첨부": [첨부],
                **({"귀띔": 귀띔} if 귀띔 else {}),
                "안내": "찍은 그림이 이 결과 메시지에 붙어 갑니다."}

    # 장면표
    장수 = _정수(frames, "장수", 8, 장면최소, 장면최대)
    틈 = _정수(gap_ms, "틈", 100, 틈최소ms, 틈최대ms)
    그림들, 시각들 = [], []
    시작시각ms = int(_지금시각() * 1000)
    시작 = _지금초()
    for i in range(장수):
        그림들.append(창조작.잡기(네모))
        시각들.append(_지금초() - 시작)
        if i < 장수 - 1:
            다음 = 시작 + (i + 1) * 틈 / 1000
            남음 = 다음 - _지금초()
            if 남음 > 0:
                _잠자기(남음)
    gate.쓰기(허가)
    표 = _표만들기(그림들, 시각들, 최대변 or 표기본최대변)
    이름 = "장면표_" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    저장 = _저장(표, 이름 + ".png")
    첨부, 요약 = _첨부항목(이름, 표, 최대변 or 표기본최대변, scale or None)
    _합계검사([첨부])
    return {"창": 제목 or "화면 전체", "영역": f"{네모[0]},{네모[1]},{네모[2]},{네모[3]}",
            "장수": 장수, "틈ms": 틈, "시작시각ms": 시작시각ms, "시각들": [round(t, 3) for t in 시각들], "저장": 저장, "그림": 요약,
            "_첨부": [첨부],
            "안내": "찍은 순서대로 격자에 놓았고 각 칸에 처음부터 흐른 초가 적혀 있습니다."}


등록된도구 = {
    "attach_image": attach_image,
    "eye": eye,
}
