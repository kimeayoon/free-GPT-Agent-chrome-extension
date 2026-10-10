# -*- coding: utf-8 -*-
"""예약 — 정한 간격마다 에이전트가 GPT 에게 먼저 말을 건다.

사람이 GPT 에게 "1분마다 학습이 어떻게 되는지 보고해줘" 라고 하면
GPT 가 배추로 예약을 건다. 때가 되면 확장이 그 말을 GPT 에게 보낸다.

  배추 : 예약 걸기   간격 1분 / 번 10 / 말《 … 》
  무   : 예약 보기   번호 없이 → 목록,  번호 … / 상태 그만 → 멈춤

예약은 방마다 방/<번호>/예약.json 에 남는다. 서버를 껐다 켜도 이어 간다.
서버는 '때가 됐다' 만 알려 준다. 보내는 것은 확장이 ChatGPT 가 비었을 때 한다.
"""

import json
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import rooms
import sandbox
import 안전파일
import tools_bg
import 현황

최소간격초 = 60             # 너무 잦으면 대화가 금방 무거워진다
최대간격초 = 7 * 24 * 3600
기본횟수 = 10
최대횟수 = 1000
말최대 = 1000
방마다최대 = 20             # 돌고 있는 예약 수

_잠금 = threading.Lock()

_단위 = [
    (("초", "s", "sec", "secs", "second", "seconds"), 1),
    (("분", "m", "min", "mins", "minute", "minutes"), 60),
    (("시간", "h", "hr", "hrs", "hour", "hours"), 3600),
    (("일", "d", "day", "days"), 86400),
]


def 간격읽기(글) -> int:
    """'1분' · '10분' · '1시간 30분' · '90초' · '2h' · '300' 을 초로 바꾼다."""
    원문 = str(글 or "").strip()
    if not 원문:
        raise ValueError('"간격" 이 비었습니다. 예: 간격 1분 / 간격 10분 / 간격 1시간')
    if re.fullmatch(r"\d+", 원문):
        초 = int(원문)
    else:
        조각들 = re.findall(r"(\d+(?:\.\d+)?)\s*([^\d\s.]+)", 원문)
        남은것 = re.sub(r"(\d+(?:\.\d+)?)\s*([^\d\s.]+)", "", 원문).replace("마다", "").strip()
        if not 조각들 or 남은것:
            raise ValueError(f'간격을 못 읽었습니다: "{원문}". 예: 1분 · 10분 · 1시간 · 1시간 30분')
        초 = 0.0
        for 수, 단위 in 조각들:
            단위 = 단위.replace("마다", "").lower()
            곱 = next((배 for 이름들, 배 in _단위 if 단위 in 이름들), None)
            if 곱 is None:
                raise ValueError(f'모르는 단위입니다: "{단위}". 초 · 분 · 시간 · 일 로 쓰세요.')
            초 += float(수) * 곱
        초 = int(round(초))
    if 초 < 최소간격초:
        raise ValueError(f"간격은 {최소간격초 // 60}분보다 짧게 못 합니다.")
    if 초 > 최대간격초:
        raise ValueError("간격은 7일까지만 됩니다.")
    return 초


def 간격글(초: int) -> str:
    조각 = []
    for 이름, 배 in (("일", 86400), ("시간", 3600), ("분", 60), ("초", 1)):
        if 초 >= 배:
            조각.append(f"{초 // 배}{이름}")
            초 %= 배
    return " ".join(조각) or "0초"


def _파일(쪽번호: str = ""):
    return rooms.방자료칸(쪽번호) / "예약.json"


def _읽기(쪽번호: str = "") -> list:
    return 안전파일.json읽기(_파일(쪽번호), [], list)


def _쓰기(목록: list, 쪽번호: str = "") -> None:
    안전파일.json쓰기(_파일(쪽번호), 목록)


def _시각글(초: float) -> str:
    return datetime.fromtimestamp(초).strftime("%m-%d %H:%M:%S")


def _보기(예약: dict) -> dict:
    return {
        "번호": 예약["번호"],
        "간격": 간격글(예약["간격초"]),
        "조건": 예약.get("조건", ""),
        "말": 예약["말"],
        "보낸수": 예약["보낸수"],
        "횟수": 예약["횟수"],
        "남은횟수": max(0, 예약["횟수"] - 예약["보낸수"]),
        "상태": 예약["상태"],
        "다음": _시각글(예약["다음때"]) if 예약["상태"] == "도는중" else "",
    }


def _방번호() -> str:
    방 = rooms.지금방()
    if not 방:
        raise ValueError("고른 방이 없습니다. 예약은 방이 있어야 겁니다.")
    return 방["쪽번호"]


# ── 배추 : 예약 걸기 ───────────────────────────────────────────
def 확인한조건닫기(쪽번호: str, 나물: str, 인자: dict) -> int:
    """GPT 가 조건 예약이 기다리던 것을 스스로 확인했으면 그 예약을 닫는다(닫은 수).

    예약을 걸어 놓고도 GPT 가 고사리로 직접 들여다보다 끝난 걸 먼저 보면, 예약은 GPT 가
    한가해진 뒤에야 가서 '이미 끝난 작업' 을 또 알렸다(2026-09-30 실제로 그랬다).
    """
    조건 = ""
    try:
        if 나물 == "고사리" and 인자.get("job"):
            일 = tools_bg._요약(str(인자["job"]))
            if 일 and 일.get("상태") in ("끝남", "끊김"):
                조건 = "뒤뜰끝:" + str(인자["job"])
        elif 나물 in ("열무", "버섯") and 인자.get("path"):
            자리 = sandbox.경로검증(str(인자["path"]))
            if 자리.is_file():
                조건 = "파일생김:" + str(자리)
    except Exception:
        return 0
    if not 조건 or not 쪽번호:
        return 0
    with _잠금:
        목록 = _읽기(쪽번호)
        닫음 = 0
        for 예 in 목록:
            if 예.get("상태") == "도는중" and 예.get("조건") == 조건:
                예["상태"] = "끝"
                예["메모"] = "GPT 가 이미 확인함"
                닫음 += 1
        if 닫음:
            _쓰기(목록, 쪽번호)
    return 닫음


방금말들 = ("방금", "마지막", "최근")


def _가장최근뒤뜰(쪽번호: str) -> str:
    """이 방에서 가장 최근에 건 뒤뜰 일의 번호. 두릅과 같은 답에 배추를 담으면 번호를 아직 모른다 — 그때 '뒤뜰끝:방금' 으로 쓴다."""
    for 요약 in tools_bg._목록():                       # 시작이 최근인 것부터
        일 = tools_bg._일읽기(tools_bg._칸(요약["번호"])) or {}
        if 일.get("방") == 쪽번호:
            return 요약["번호"]
    raise ValueError("이 방에서 건 뒤뜰 일이 아직 없습니다. 먼저 두릅으로 일을 거세요.")


def _조건읽기(글: str, 쪽번호: str = "") -> tuple[str, str]:
    종류, 구분, 대상 = str(글).partition(":")
    if not 구분 or not 대상.strip() or 종류 not in ("뒤뜰끝", "파일생김"):
        raise ValueError("조건은 '뒤뜰끝:번호' 또는 '파일생김:경로' 로 쓰세요.")
    대상 = 대상.strip()
    if 종류 == "뒤뜰끝":
        if 대상 in 방금말들:
            대상 = _가장최근뒤뜰(쪽번호)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", 대상):
            # 실제 사고: GPT 가 두릅과 같은 답에 '뒤뜰끝:번호' 라고 낱말 그대로 적어 이 오류를 받고 한 바퀴를 더 돌았다
            raise ValueError("뒤뜰 번호는 두릅이 돌려주는 영문·숫자 번호(예 9db089d7)입니다. '번호' 라는 낱말을 그대로 쓰면 안 됩니다. "
                             "두릅과 같은 답에 걸려면 '뒤뜰끝:방금' (이 방에서 가장 최근에 건 일)으로 쓰세요.")
        if tools_bg._요약(대상) is None:
            raise ValueError(f"그런 뒤뜰 일이 없습니다: {대상}")
    else:
        대상 = str(sandbox.경로검증(대상))
    return 종류, 대상


def _조건맞나(예약: dict) -> bool:
    조건 = 예약.get("조건", "")
    if not 조건:
        return True
    종류, _, 대상 = 조건.partition(":")
    if 종류 == "뒤뜰끝":
        일 = tools_bg._요약(대상)
        # 끊김 = 끝번호도 없는데 프로세스도 없다(컴퓨터를 껐다 켰거나 강제로 죽음). 이것도 알려야 한다 —
        # 끝남만 기다리면 일이 죽은 채 예약이 영영 안 울렸다.
        return bool(일 and 일["상태"] in ("끝남", "끊김"))
    if 종류 == "파일생김":
        try:
            return sandbox.경로검증(대상).is_file()
        except (OSError, sandbox.보안오류):
            return False
    return False


def set_timer(interval: str = "", count=None, message: str = "", condition: str = "", **_):
    초 = 간격읽기(interval or ("1분" if condition else ""))
    조건 = ""
    if condition:
        종류, 대상 = _조건읽기(condition, _방번호())
        조건 = f"{종류}:{대상}"
    말 = (message or "").strip()
    if not 말:
        raise ValueError('"말" 이 비었습니다. 때가 되면 당신에게 보낼 말을 적으세요. 예: 말 학습이 어떻게 되는지 고사리로 보고')
    if len(말) > 말최대:
        raise ValueError(f"말이 너무 깁니다. {말최대}자 안쪽으로.")
    if count in (None, ""):
        횟수 = 1 if 조건 else 기본횟수
    else:
        try:
            횟수 = int(count)
        except (TypeError, ValueError):
            raise ValueError('"번" 은 숫자로 쓰세요. 예: 번 10')
    if not 1 <= 횟수 <= 최대횟수:
        raise ValueError(f"번은 1에서 {최대횟수} 사이로 쓰세요.")

    쪽번호 = _방번호()
    with _잠금:
        목록 = _읽기(쪽번호)
        if sum(1 for 예 in 목록 if 예["상태"] == "도는중") >= 방마다최대:
            raise ValueError(f"돌고 있는 예약이 {방마다최대}개입니다. 무로 필요 없는 것을 멈추세요.")
        지금 = time.time()
        예약 = {
            "번호": uuid.uuid4().hex[:6],
            "간격초": 초,
            "횟수": 횟수,
            "말": 말,
            "조건": 조건,
            "보낸수": 0,
            "만든때": 지금,
            "다음때": 지금 + 초,
            "상태": "도는중",
        }
        목록.append(예약)
        _쓰기(목록[-100:], 쪽번호)
    return {**_보기(예약), "action": "예약함",
            "안내": (f"{간격글(초)}마다 {횟수}번 보냅니다. 멈추려면: 나물 무 / 번호 {예약['번호']} / 상태 그만. "
                   "'말' 은 때가 되면 당신에게 그대로 돌아옵니다 — 그때 당신이 바구니로 할 일입니다(결과 파일은 따로 오지 않습니다).")}


# ── 무 : 예약 보기 · 멈추기 ─────────────────────────────────────
def watch_timer(job: str = "", status: str = "", **_):
    쪽번호 = _방번호()
    번호 = (job or "").strip()
    with _잠금:
        목록 = _읽기(쪽번호)
        if not 번호:
            도는것 = [_보기(예) for 예 in 목록 if 예["상태"] == "도는중"]
            return {"예약들": 도는것, "개수": len(도는것)}
        예약 = next((예 for 예 in 목록 if 예["번호"] == 번호), None)
        if 예약 is None:
            raise ValueError(f"그런 예약이 없습니다: {번호}")
        if (status or "").strip() in ("그만", "멈춤", "중단"):
            if 예약["상태"] == "도는중":
                예약["상태"] = "그만"
                _쓰기(목록, 쪽번호)
                return {**_보기(예약), "action": "멈춤"}
            return {**_보기(예약), "action": "이미 끝나 있었습니다"}
        return _보기(예약)


등록된도구 = {
    "set_timer": set_timer,
    "watch_timer": watch_timer,
}


# ── 확장이 부르는 것 (나물이 아님) ─────────────────────────────

def 목록(쪽번호: str) -> list:
    return [_보기(예) for 예 in _읽기(쪽번호) if 예["상태"] == "도는중"]


def _끊긴일알림만들기(쪽번호: str, 지금: float) -> None:
    """예약을 안 걸어 둔 일이라도 달리다 죽었으면(컴퓨터를 껐다 켬 등) 한 번 알리는 예약을 저절로 만든다."""
    try:
        끊긴 = tools_bg.끊긴일들(쪽번호)
    except Exception:
        return
    if not 끊긴:
        return
    with _잠금:
        목록 = _읽기(쪽번호)
        바뀜 = False
        for 번호, 이름 in 끊긴:
            tools_bg.끊김알림적기(번호)                      # 한 번만 — 알림이 가든 이미 예약이 있든
            if any(예.get("상태") == "도는중" and 예.get("조건") == f"뒤뜰끝:{번호}" for 예 in 목록):
                continue                                    # 사용자가 건 예약이 이미 알린다
            목록.append({
                "번호": uuid.uuid4().hex[:6], "간격초": 최소간격초, "횟수": 1,
                "말": (f"(자동) 뒤뜰 일 '{이름}'({번호})이 끝번호 없이 사라졌습니다. 컴퓨터를 껐다 켰거나 프로그램이 "
                      "죽었을 수 있습니다. 어디까지 했는지 확인하고, 다시 돌릴지 정리해 사용자에게 알려 주세요."),
                "조건": f"뒤뜰끝:{번호}", "보낸수": 0, "만든때": 지금, "다음때": 지금, "상태": "도는중",
            })
            바뀜 = True
        if 바뀜:
            _쓰기(목록[-100:], 쪽번호)


def 때된것(쪽번호: str, 지금: float | None = None) -> dict | None:
    """보낼 때가 된 예약 하나. 가장 오래 기다린 것부터."""
    지금 = time.time() if 지금 is None else 지금
    _끊긴일알림만들기(쪽번호, 지금)
    된것 = [예 for 예 in _읽기(쪽번호) if 예["상태"] == "도는중"
            and 예["다음때"] <= 지금 and _조건맞나(예)]
    if not 된것:
        return None
    예약 = min(된것, key=lambda 예: 예["다음때"])
    return {**_보기(예약), "보낼글": 보낼글(예약)}


def _초글(초) -> str:
    초 = int(초 or 0)
    if 초 < 60:
        return f"{초}초"
    if 초 < 3600:
        return f"{초 // 60}분 {초 % 60}초"
    return f"{초 // 3600}시간 {(초 % 3600) // 60}분"


_파일낱말 = re.compile(r"--(?:checkpoint|ckpt|log|out|output|save|model)[= ]+(\S+)")


def _일파일들(일: dict, 자리: str) -> list:
    """일을 시작한 명령에서 결과 파일 자리(--checkpoint · --log …)를 찾아 있는지·크기·언제 바뀌었는지."""
    결과 = []
    for 낱 in _파일낱말.findall(일.get("불", "")):
        낱 = 낱.strip("\"'")
        try:
            경로 = sandbox.경로검증(str(Path(자리 or ".") / 낱) if not Path(낱).is_absolute() else 낱)
        except Exception:
            continue
        try:
            if 경로.is_file():
                정보 = 경로.stat()
                결과.append(f"{낱} — 있음 · {정보.st_size:,}바이트 · 바뀐 때 "
                          f"{datetime.fromtimestamp(정보.st_mtime).strftime('%m-%d %H:%M')}")
            else:
                결과.append(f"{낱} — 없음")
        except OSError:
            continue
        if len(결과) >= 4:
            break
    return 결과


def _뒤뜰사실(번호: str) -> list:
    항 = 현황.일항목(번호)
    if not 항.get("있음"):
        return [f"- 뒤뜰 일 {번호} 를 찾지 못했습니다(기록이 지워졌거나 번호가 틀렸을 수 있습니다)."]
    상태, 끝번호 = 항["상태"], 항.get("끝번호")
    if 상태 == "끝남":
        상태글 = ("끝남 · 끝번호 0(성공)" if 끝번호 == 0
                else "멈춤(사람이 멈춤)" if 끝번호 == -9 else f"실패로 끝남 · 끝번호 {끝번호}")
    elif 상태 == "끊김":
        상태글 = "끊김 — 끝번호도 없는데 프로세스가 사라졌습니다. 컴퓨터를 껐다 켰거나 강제로 죽은 것일 수 있습니다"
    else:
        상태글 = "아직 도는 중"
    줄들 = [f"- 일 '{항.get('이름')}'({번호}): {상태글} · {'걸린' if 상태 != '달리는중' else '경과'} {_초글(항.get('경과초'))}"]
    진행 = 항.get("진행")
    if 진행 and 진행.get("지금") is not None and 진행.get("전체"):
        줄들.append(f"- 진행: {진행['지금']}/{진행['전체']}" + (f" ({진행['퍼센트']}%)" if 진행.get("퍼센트") is not None else ""))
    숫자들 = [f"{숫['이름']} {숫['최신']}" + {"오름": " ▲", "내림": " ▼"}.get(숫.get("추이"), "") for 숫 in (항.get("숫자들") or [])[:4]]
    if 숫자들:
        줄들.append("- 마지막 지표: " + ", ".join(숫자들))
    if 항.get("끝줄들"):
        줄들.append("- 로그 끝: " + " / ".join(항["끝줄들"]))
    elif 항.get("기록크기") == 0:
        줄들.append("- 로그가 비어 있습니다.")
    일 = tools_bg._요약(번호) or {}
    for 파일 in _일파일들(일, 일.get("자리", "")):
        줄들.append("- 파일 " + 파일)
    return 줄들


def _파일사실(경로: str) -> list:
    try:
        정보 = Path(경로).stat()
    except OSError:
        return [f"- 파일 {경로} 를 지금은 읽을 수 없습니다."]
    return [f"- 파일 {경로} — 있음 · {정보.st_size:,}바이트 · 바뀐 때 "
            f"{datetime.fromtimestamp(정보.st_mtime).strftime('%m-%d %H:%M')}"]


def 확인한사실(예약: dict) -> str:
    """조건 예약이 울릴 때, 서버가 직접 재서 알림에 붙일 사실. 조건이 없거나 못 재면 빈 글(알림은 그대로 간다)."""
    종류, _, 대상 = (예약.get("조건") or "").partition(":")
    try:
        if 종류 == "뒤뜰끝":
            줄들 = _뒤뜰사실(대상)
        elif 종류 == "파일생김":
            줄들 = _파일사실(대상)
        else:
            return ""
    except Exception:
        return ""
    return ("── 서버가 방금 직접 확인한 사실(GPT 말이 아니라 잰 값) ──\n" + "\n".join(줄들) + "\n"
            "이 사실로 먼저 판단하세요. 결과가 안 보이거나 이상하면(끊김 · 로그 비어 있음 · 파일 없음) "
            "사용자에게 파일이나 결과를 달라고 하지 말고, 컴퓨터가 꺼졌거나 프로그램이 죽은 것은 아닌지 의심해 "
            "고사리 · 열무로 직접 다시 확인한 뒤 보고하세요. 다시 돌려야 하면 【물음】 으로 사용자에게 고르게 하세요.")


지금상태일수 = 2
지금상태시간 = 24 * 3600


def 지금상태글(쪽번호: str) -> str:
    """이 방에서 최근에 돈 뒤뜰 일과 예약이 '지금' 어떤 상태인지 서버가 직접 재서 돌려준다.

    넘김 파일의 '마지막 도구 결과' 는 그때 것이라, 이미 울린 예약이 '도는중' 으로 실려 가서
    새 대화의 GPT 가 '결과가 올 것' 이라며 기다렸다. 그래서 넘기는 순간과 되돌려 보낼 때 지금 값을 같이 준다.
    """
    줄들 = []
    try:
        일들 = []
        for 요약 in tools_bg._목록():
            일 = tools_bg._일읽기(tools_bg._칸(요약["번호"])) or {}
            if 일.get("방") != 쪽번호:
                continue
            try:
                시작 = datetime.strptime(요약.get("시작", ""), "%Y-%m-%d %H:%M:%S").timestamp()
            except ValueError:
                시작 = 0
            if time.time() - 시작 > 지금상태시간:
                continue
            일들.append(요약["번호"])
            if len(일들) >= 지금상태일수:
                break
        for 번호 in 일들:
            줄들.extend(_뒤뜰사실(번호))
    except Exception:
        pass
    try:
        목록 = _읽기(쪽번호)
        도는 = [예 for 예 in 목록 if 예.get("상태") == "도는중"]
        if 도는:
            for 예 in 도는[:3]:
                줄들.append(f"- 예약 {예['번호']}: 아직 도는 중 ({예.get('조건') or 간격글(예['간격초']) + '마다'})")
        elif 목록:
            줄들.append("- 돌고 있는 예약: 없음. 앞서 건 예약은 이미 울렸거나 끝났습니다 — 더 올 알림이 없습니다.")
    except Exception:
        pass
    if not 줄들:
        return ""
    return ("── 서버가 지금 직접 확인한 상태(GPT 말이 아니라 잰 값) ──\n" + "\n".join(줄들) + "\n"
            "결과는 저절로 오지 않습니다. 이 값으로 판단하고, 더 필요한 것은 바구니(고사리 · 열무)로 직접 확인해서 이어서 진행하세요.")


def 보낼글(예약: dict) -> str:
    설명 = (f"조건 {예약['조건']}" if 예약.get("조건")
          else f"{간격글(예약['간격초'])}마다")
    # 말을 '끝나면 결과를 알려 주세요' 처럼 남에게 하는 부탁으로 적어 두면, 그 말이 그대로 돌아왔을 때
    # GPT 가 '누가 결과를 보내 줄 것' 으로 읽고 기다렸다. 그래서 알림이 무엇인지 알림 스스로 밝힌다.
    글 = (f"⏰ 예약 알림 ({예약['보낸수'] + 1}/{예약['횟수']}, {설명})\n"
          "당신이 걸어 둔 예약입니다. 아래 '할 일' 은 그때 당신이 적어 둔 말이고, 결과 파일은 따로 오지 않습니다. "
          "누가 대신 확인해 주지 않으니 지금 바구니(고사리 · 열무)로 직접 확인하고 이어서 진행하세요.\n"
          f"할 일: {예약['말']}")
    사실 = 확인한사실(예약)
    return 글 + ("\n" + 사실 if 사실 else "")


def 보냄(쪽번호: str, 번호: str, 지금: float | None = None) -> dict:
    """보냈다고 적는다. 놓친 때는 몰아 보내지 않고 다음 때를 지금 뒤로 민다."""
    지금 = time.time() if 지금 is None else 지금
    with _잠금:
        목록 = _읽기(쪽번호)
        예약 = next((예 for 예 in 목록 if 예["번호"] == 번호), None)
        if 예약 is None:
            raise ValueError(f"그런 예약이 없습니다: {번호}")
        if 예약["상태"] != "도는중":
            return _보기(예약)
        예약["보낸수"] += 1
        if 예약["보낸수"] >= 예약["횟수"]:
            예약["상태"] = "끝"
        else:
            다음 = 예약["다음때"] + 예약["간격초"]
            if 다음 <= 지금:                     # 잠들어 여러 번 놓쳤다 — 한 번만 치고 지금부터 다시 센다
                다음 = 지금 + 예약["간격초"]
            예약["다음때"] = 다음
        _쓰기(목록, 쪽번호)
        return _보기(예약)


def 그만(쪽번호: str, 번호: str) -> dict:
    rooms.방고정(쪽번호)
    try:
        return watch_timer(job=번호, status="그만")
    finally:
        rooms.방풀기()
