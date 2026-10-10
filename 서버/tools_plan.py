# -*- coding: utf-8 -*-
"""목표(차례) 도구 — 감자(세우기) · 고구마(고치기·갱신) · 토란(보기).

복잡한 작업에서 GPT 가 지금 몇 단계인지 놓치지 않게 한다.
목표는 방 자료칸의 차례.json 에 저장되므로 대화가 끊겨도 남는다.

목표는 유연해야 한다 — 접을 수도, 갈아엎을 수도, 고칠 수도 있다. 대신 아무것도 사라지지 않는다.
  · 감자로 새 목표를 세우면 앞 목표는 '지난 목표'(차례기록.json)로 자동 보관된다.
  · 고구마의 짓: 상태(기본) · 고치기 · 더하기 · 빼기 · 옮기기 · 목표고치기 · 포기 · 되살리기 · 되돌리기
  · 구조를 바꾸는 수정은 바꾸기 전 모양을 '되돌림' 에 쌓아 두므로 마지막 것은 되돌릴 수 있다.
  · 사용자가 판에서 고치면(누가=사용자) GPT 가 다음 도구 결과에서 알게 한다(덮어쓰기 방지).
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path

import sandbox
import 안전파일

허용상태 = ("기다림", "하는중", "끝", "실패", "건너뜀")
표시 = {
    "기다림": "☐",
    "하는중": "▶",
    "끝": "☑",
    "실패": "✗",
    "건너뜀": "–",
}

단계최대 = 20
지난목표최대 = 20
되돌림최대 = 10
알림최대 = 5
기록파일이름 = "차례기록.json"

# 차례.json 을 읽고 고쳐 쓰는 동안 다른 요청(판에서 고치기 vs GPT 도구)이 끼어들지 못하게 한다
_자물쇠 = threading.RLock()


def _계획파일() -> Path:
    import rooms
    return rooms.방자료칸() / "차례.json"


def _기록파일() -> Path:
    import rooms
    return rooms.방자료칸() / 기록파일이름


def _읽기() -> dict:
    파일 = _계획파일()
    if not 파일.exists():
        return {"task": None, "steps": [], "updated": None}
    return 안전파일.json읽기(파일, {"task": None, "steps": [], "updated": None}, dict)


def _쓰기(계획: dict) -> dict:
    계획["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    안전파일.json쓰기(_계획파일(), 계획)
    return _보기좋게(계획)


def _기록읽기() -> dict:
    값 = 안전파일.json읽기(_기록파일(), {}, dict)
    값.setdefault("목록", [])        # 지난 목표 (오래된 것이 앞)
    값.setdefault("되돌림", [])      # 구조를 바꾸기 전 모양 (오래된 것이 앞)
    return 값


def _기록쓰기(기록: dict) -> None:
    안전파일.json쓰기(_기록파일(), 기록)


# GPT 에게 돌려주는 결과에 붙는 쪽지는 이만큼만 싣는다.
# 예전엔 고구마 한 번마다 모든 단계의 긴 쪽지를 통째로 돌려줘서 결과가 5만 자를 넘었다.
# 그걸 ChatGPT 입력칸에 붙여 넣다가 페이지가 뻗었고, 대화도 그만큼 무거워졌다.
# 쪽지 전체는 판(/plan)에서 보이고, GPT 는 '토란 / 몇 N' 으로 한 단계씩 볼 수 있다.
쪽지최대 = 80


def _쪽지줄임(글: str) -> str:
    글 = (글 or "").strip()
    if len(글) <= 쪽지최대:
        return 글
    첫줄 = 글.splitlines()[0][:쪽지최대]
    return f"{첫줄}… ({len(글)}자, 전체는 토란 몇)"


def _보기좋게(계획: dict, 전체: bool = False) -> dict:
    줄들 = []
    단계들 = []
    for i, 단계 in enumerate(계획["steps"], 1):
        표식 = 표시.get(단계["status"], "?")
        쪽 = 단계.get("note") or ""
        보일쪽 = 쪽 if 전체 else _쪽지줄임(쪽)
        줄 = f"{표식} {i}. {단계['name']}"
        if 보일쪽:
            줄 += f"  — {보일쪽}"
        줄들.append(줄)
        단계들.append({**단계, "note": 보일쪽})

    끝난수 = sum(1 for s in 계획["steps"] if s["status"] in ("끝", "건너뜀"))
    return {
        "task": 계획.get("task"),
        "progress": f"{끝난수}/{len(계획['steps'])}",
        "steps": 단계들,
        "board": "\n".join(줄들) or "(계획 없음)",
    }


def _진도(계획: dict) -> str:
    끝 = sum(1 for s in 계획.get("steps", []) if s["status"] in ("끝", "건너뜀"))
    return f"{끝}/{len(계획.get('steps', []))}"


def _지금글() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _모양복사(계획: dict) -> dict:
    return {"task": 계획.get("task"), "steps": [dict(s) for s in 계획.get("steps", [])]}


def _이름들(계획: dict) -> list:
    return [s["name"] for s in 계획.get("steps", [])]


def _번호(값, 길이: int, 이름: str = "몇") -> int:
    try:
        번 = int(float(값))
    except (TypeError, ValueError):
        raise ValueError(f"'{이름}' 은 숫자여야 합니다.")
    if not (1 <= 번 <= 길이):
        raise ValueError(f"'{이름}' 은 1~{길이} 사이여야 합니다.")
    return 번


def _하는중하나로(계획: dict) -> None:
    """하는중은 하나만 둔다. 하는중이 사라졌으면(뺐거나 되돌렸으면) 다음 기다림을 올린다."""
    단계들 = 계획["steps"]
    하는 = [i for i, s in enumerate(단계들) if s["status"] == "하는중"]
    for i in 하는[1:]:
        단계들[i]["status"] = "기다림"
    if not 하는:
        for 단계 in 단계들:
            if 단계["status"] == "기다림":
                단계["status"] = "하는중"
                break


# ── 지난 목표 · 되돌림 ─────────────────────────────────────────

def _보관(계획: dict, 까닭: str, 이유: str, 누가: str):
    """지금 목표를 '지난 목표' 로 옮겨 적는다. 적을 게 없으면 None.

    같은 목표를 같은 까닭으로 또 보내면 중복해서 쌓지 않는다.
    """
    if not 계획.get("steps") and not 계획.get("task"):
        return None
    기록 = _기록읽기()
    항목 = {
        "번호": "g" + str(int(time.time() * 1000))[-9:],
        "일": 계획.get("task"),
        "차례": [dict(s) for s in 계획.get("steps", [])],
        "진도": _진도(계획),
        "끝낸때": _지금글(),
        "까닭": 까닭,
        "이유": (이유 or "").strip()[:200],
        "누가": 누가,
    }
    마지막 = 기록["목록"][-1] if 기록["목록"] else None
    if (마지막 and 마지막["일"] == 항목["일"] and 마지막["까닭"] == 까닭
            and [s["name"] for s in 마지막["차례"]] == _이름들(계획)):
        return 마지막
    기록["목록"].append(항목)
    기록["목록"] = 기록["목록"][-지난목표최대:]
    _기록쓰기(기록)
    return 항목


def _되돌림쌓기(계획: dict, 무엇: str, 누가: str, 보관번호: str = "") -> None:
    """구조를 바꾸기 '전' 의 모양을 쌓아 둔다. 비어 있는 목표는 쌓을 게 없다."""
    if not 계획.get("steps") and not 계획.get("task"):
        return
    기록 = _기록읽기()
    기록["되돌림"].append({
        "때": _지금글(), "무엇": 무엇, "누가": 누가, "보관번호": 보관번호,
        "일": 계획.get("task"), "차례": [dict(s) for s in 계획.get("steps", [])],
    })
    기록["되돌림"] = 기록["되돌림"][-되돌림최대:]
    _기록쓰기(기록)


def _최근고침(계획: dict, 무엇: str, 누가: str) -> None:
    계획["최근고침"] = {"무엇": 무엇, "누가": 누가, "때": time.time()}
    if 누가 == "사용자":
        알림 = 계획.setdefault("알림", [])
        알림.append(무엇)
        계획["알림"] = 알림[-알림최대:]


def _지난목표요약(항목: dict) -> dict:
    return {
        "번호": 항목["번호"], "일": 항목.get("일"), "진도": 항목.get("진도"),
        "단계수": len(항목.get("차례", [])), "끝낸때": 항목.get("끝낸때"),
        "까닭": 항목.get("까닭"), "이유": 항목.get("이유", ""), "누가": 항목.get("누가", ""),
    }


def 판정보() -> dict:
    """판의 목표 창이 쓰는 덧붙임 — 지난 목표 목록 · 되돌릴 수 있는 수 · 방금 고친 것."""
    기록 = _기록읽기()
    계획 = _읽기()
    return {
        "지난목표": [_지난목표요약(x) for x in reversed(기록["목록"])],
        "되돌림수": len(기록["되돌림"]),
        "최근고침": 계획.get("최근고침"),
    }


def 사용자고침알림가져오기() -> list:
    """사용자가 판에서 고친 것을 GPT 가 한 번 알게 한다(알린 뒤에는 지운다)."""
    with _자물쇠:
        계획 = _읽기()
        알림 = 계획.get("알림") or []
        if not 알림:
            return []
        계획["알림"] = []
        안전파일.json쓰기(_계획파일(), 계획)
        return 알림


# ── 고치기 ─────────────────────────────────────────────────────

def 적용(짓: str = "", 누가: str = "GPT", step=None, status: str = "", note=None, name: str = "",
        task: str = "", steps=None, to_step=None, why: str = "", job: str = "") -> dict:
    """목표를 바꾸는 모든 길이 지나는 한 곳. GPT 도구와 판의 /plan 이 같이 쓴다."""
    짓 = (짓 or "").strip() or "상태"
    with _자물쇠:
        if 짓 == "상태":
            return _상태바꾸기(누가, step, status, note)
        if 짓 == "세우기":
            return _세우기(누가, task, steps, why)
        if 짓 == "되살리기":
            return _되살리기(누가, job)
        if 짓 == "되돌리기":
            return _되돌리기(누가)
        if 짓 == "포기":
            return _포기(누가, why)
        if 짓 in ("고치기", "더하기", "빼기", "옮기기", "목표고치기"):
            return _구조고치기(짓, 누가, step, note, name, task, to_step)
        raise ValueError("'짓' 은 상태·고치기·더하기·빼기·옮기기·목표고치기·포기·되살리기·되돌리기 중 하나입니다.")


def _상태바꾸기(누가, step, status, note) -> dict:
    if status not in 허용상태:
        raise ValueError(f"'상태' 는 {', '.join(허용상태)} 중 하나여야 합니다.")
    계획 = _읽기()
    if not 계획["steps"]:
        raise ValueError("세워둔 것이 없습니다. 감자를 먼저 부르세요.")
    번 = _번호(step, len(계획["steps"]))

    계획["steps"][번 - 1]["status"] = status
    if note:
        계획["steps"][번 - 1]["note"] = note

    # 하는중은 하나만 둔다. 앞 단계를 안 끝낸 채 5번을 '하는중' 으로 바꾸면
    # 판에 ◉ 가 둘 떴다(1번·5번). 끝났는지는 서버가 알 수 없으니 '기다림' 으로 돌린다.
    if status == "하는중":
        for i, 단계 in enumerate(계획["steps"], 1):
            if i != 번 and 단계["status"] == "하는중":
                단계["status"] = "기다림"

    # 한 단계가 끝나면 다음 기다림 단계를 저절로 '하는중' 으로 올린다.
    # 이미 하는중인 단계가 있으면 올리지 않는다(하는중이 둘이 된다).
    # 방금 끝낸 단계 뒤쪽을 먼저 보고, 없으면 맨 앞부터 본다.
    if status in ("끝", "건너뜀") and not any(s["status"] == "하는중" for s in 계획["steps"]):
        for 단계 in 계획["steps"][번:] + 계획["steps"][:번]:
            if 단계["status"] == "기다림":
                단계["status"] = "하는중"
                break

    if 누가 == "사용자":
        # 사용자가 판에서 단계 상태를 바꿨다 — GPT 가 덮어쓰지 않게 알린다(되돌림·배너는 구조 수정만)
        알림 = 계획.setdefault("알림", [])
        알림.append(f"단계 {번} '{계획['steps'][번 - 1]['name']}' 을(를) '{status}' 로 바꿨습니다")
        계획["알림"] = 알림[-알림최대:]
    return _쓰기(계획)


def _세우기(누가, task, steps, why) -> dict:
    if not steps or not isinstance(steps, list):
        raise ValueError('"차례" 는 글 목록이어야 합니다.')
    if len(steps) > 단계최대:
        raise ValueError(f"차례가 너무 많습니다(최대 {단계최대}).")
    task = (task or "").strip()
    if not task:
        raise ValueError('"일" 이 비었습니다. 무엇을 하는 목표인지 적어 주세요.')
    새이름들 = [str(s).strip() for s in steps if str(s).strip()]
    if not 새이름들:
        raise ValueError('"차례" 가 비었습니다.')

    옛 = _읽기()
    안끝남 = any(s["status"] not in ("끝", "건너뜀") for s in 옛.get("steps", []))
    # 같은 목표를 또 보낸 것(대화가 바뀌어 다시 세우는 경우) — 쌓은 진도를 지우지 않는다
    if 옛.get("task") == task and _이름들(옛) == 새이름들 and 안끝남:
        결과 = _쓰기(옛)
        결과["한일"] = "같은 목표라 진도를 그대로 두었습니다"
        return 결과

    앞목표 = None
    무엇 = f"새 목표 '{task}' ({len(새이름들)}단계)"
    if 옛.get("steps") or 옛.get("task"):
        보관 = _보관(옛, "교체", why, 누가)
        _되돌림쌓기(옛, 무엇, 누가, (보관 or {}).get("번호", ""))
        앞목표 = {"일": 옛.get("task"), "진도": _진도(옛), "번호": (보관 or {}).get("번호", ""),
                "끝났나": not 안끝남}

    계획 = {"task": task, "steps": [{"name": n, "status": "기다림", "note": ""} for n in 새이름들]}
    계획["steps"][0]["status"] = "하는중"
    if 앞목표:
        _최근고침(계획, 무엇 + f" — 앞 목표 '{앞목표['일']}'({앞목표['진도']})는 지난 목표로 보관", 누가)
    결과 = _쓰기(계획)
    if 앞목표:
        결과["앞목표"] = 앞목표
        결과["한일"] = f"앞 목표 '{앞목표['일']}'({앞목표['진도']}) 는 지난 목표로 보관했습니다"
    return 결과


def _구조고치기(짓, 누가, step, note, name, task, to_step) -> dict:
    계획 = _읽기()
    if not 계획["steps"] and not 계획.get("task"):
        raise ValueError("세워둔 것이 없습니다. 감자를 먼저 부르세요.")
    단계들 = 계획["steps"]
    이름 = (name or "").strip()[:200]
    앞모양 = _모양복사(계획)

    if 짓 == "목표고치기":
        새 = (task or name or "").strip()[:200]
        if not 새:
            raise ValueError("새 목표 이름이 필요합니다. 예) 나물 고구마 / 짓 목표고치기 / 일 전투 PPO 안정화")
        무엇 = f"목표 이름 '{계획.get('task')}' → '{새}'"
        _되돌림쌓기(앞모양, 무엇, 누가)
        계획["task"] = 새
    elif 짓 == "고치기":
        번 = _번호(step, len(단계들))
        if not 이름 and note is None:
            raise ValueError("고칠 것이 없습니다. 이름 또는 쪽 을 주세요.")
        옛이름 = 단계들[번 - 1]["name"]
        무엇 = f"단계 {번} 고침" + (f" '{옛이름}' → '{이름}'" if 이름 else " (쪽지)")
        _되돌림쌓기(앞모양, 무엇, 누가)
        if 이름:
            단계들[번 - 1]["name"] = 이름
        if note is not None:
            단계들[번 - 1]["note"] = str(note)
    elif 짓 == "더하기":
        if not 이름:
            raise ValueError("더할 단계의 이름이 필요합니다. 예) 나물 고구마 / 짓 더하기 / 이름 회귀 시험 / 몇 3")
        if len(단계들) >= 단계최대:
            raise ValueError(f"차례가 너무 많습니다(최대 {단계최대}).")
        자리 = len(단계들) + 1 if step in (None, "") else _번호(step, len(단계들) + 1)
        무엇 = f"단계 {자리} '{이름}' 더함"
        _되돌림쌓기(앞모양, 무엇, 누가)
        단계들.insert(자리 - 1, {"name": 이름, "status": "기다림", "note": ""})
    elif 짓 == "빼기":
        번 = _번호(step, len(단계들))
        if len(단계들) == 1:
            raise ValueError("단계가 하나뿐입니다. 목표를 접으려면 짓 포기 를 쓰세요.")
        무엇 = f"단계 {번} '{단계들[번 - 1]['name']}' 뺌"
        _되돌림쌓기(앞모양, 무엇, 누가)
        단계들.pop(번 - 1)
    else:                                            # 옮기기
        번 = _번호(step, len(단계들))
        새번 = _번호(to_step, len(단계들), "새몇")
        무엇 = f"단계 {번} '{단계들[번 - 1]['name']}' → {새번}번 자리"
        _되돌림쌓기(앞모양, 무엇, 누가)
        단계들.insert(새번 - 1, 단계들.pop(번 - 1))

    _하는중하나로(계획)
    _최근고침(계획, 무엇, 누가)
    결과 = _쓰기(계획)
    결과["한일"] = 무엇
    return 결과


def _포기(누가, why) -> dict:
    계획 = _읽기()
    if not 계획["steps"] and not 계획.get("task"):
        raise ValueError("접을 목표가 없습니다.")
    무엇 = f"목표 '{계획.get('task')}' ({_진도(계획)}) 포기"
    보관 = _보관(계획, "포기", why, 누가)
    _되돌림쌓기(계획, 무엇, 누가, (보관 or {}).get("번호", ""))
    새 = {"task": None, "steps": []}
    _최근고침(새, 무엇 + (f" — {why.strip()[:80]}" if (why or "").strip() else ""), 누가)
    if 누가 == "사용자":
        새.setdefault("알림", [])
    결과 = _쓰기(새)
    결과["한일"] = 무엇 + ". 지난 목표로 보관했습니다(되살리기 번호 " + (보관 or {}).get("번호", "") + ")"
    return 결과


def _되살리기(누가, job) -> dict:
    번호 = (job or "").strip()
    기록 = _기록읽기()
    항목 = next((x for x in 기록["목록"] if x["번호"] == 번호), None)
    if 항목 is None:
        있는것 = ", ".join(f"{x['번호']}({x.get('일')})" for x in reversed(기록["목록"][-5:])) or "(없음)"
        raise ValueError(f"그런 지난 목표가 없습니다: {번호}. 있는 것: {있는것}")
    옛 = _읽기()
    무엇 = f"지난 목표 '{항목.get('일')}' ({항목.get('진도')}) 되살림"
    보관번호 = ""
    if 옛.get("steps") or 옛.get("task"):
        보관 = _보관(옛, "교체", f"'{항목.get('일')}' 되살리기로 바뀜", 누가)
        보관번호 = (보관 or {}).get("번호", "")
        _되돌림쌓기(옛, 무엇, 누가, 보관번호)
    기록 = _기록읽기()                                 # _보관 이 다시 썼으니 새로 읽는다
    기록["목록"] = [x for x in 기록["목록"] if x["번호"] != 번호]
    _기록쓰기(기록)
    계획 = {"task": 항목.get("일"), "steps": [dict(s) for s in 항목.get("차례", [])]}
    _하는중하나로(계획)
    _최근고침(계획, 무엇, 누가)
    결과 = _쓰기(계획)
    결과["한일"] = 무엇
    return 결과


def _되돌리기(누가) -> dict:
    기록 = _기록읽기()
    if not 기록["되돌림"]:
        raise ValueError("되돌릴 수정이 없습니다.")
    앞 = 기록["되돌림"].pop()
    # 그 수정이 앞 목표를 지난 목표로 보냈다면, 되돌린 지금은 지난 목표에서도 뺀다(같은 목표가 둘이 되지 않게)
    if 앞.get("보관번호"):
        기록["목록"] = [x for x in 기록["목록"] if x["번호"] != 앞["보관번호"]]
    _기록쓰기(기록)
    현재 = _읽기()
    계획 = {"task": 앞.get("일"), "steps": [dict(s) for s in 앞.get("차례", [])]}
    if 현재.get("알림"):
        계획["알림"] = 현재["알림"]
    무엇 = f"'{앞.get('무엇')}' 을(를) 되돌림"
    if 누가 == "사용자":
        알림 = 계획.setdefault("알림", [])
        알림.append(무엇)
        계획["알림"] = 알림[-알림최대:]
    계획["최근고침"] = {"무엇": 무엇, "누가": 누가, "때": time.time(), "되돌림": True}
    결과 = _쓰기(계획)
    결과["한일"] = 무엇
    return 결과


# ── GPT 가 부르는 도구 ─────────────────────────────────────────

def plan_set(task: str = "", steps: list = None, why: str = "", **_):
    """새 목표를 세운다. 앞 목표가 있으면 '지난 목표' 로 보관한다(덮어써서 사라지지 않는다)."""
    return 적용("세우기", "GPT", task=task, steps=steps, why=why)


def plan_update(step=None, status: str = "", note=None, action: str = "", name: str = "",
                task: str = "", to_step=None, why: str = "", job: str = "", **_):
    """목표를 갱신·수정한다. 짓을 안 주면 단계 상태 바꾸기(몇 + 상태)."""
    return 적용(action, "GPT", step=step, status=status, note=note, name=name,
              task=task, to_step=to_step, why=why, job=job)


def plan_get(step: int | None = None, 전체: bool = False, action: str = "", **_):
    """현재 목표를 본다. 짓 기록 이면 지난 목표 목록.

    step 을 주면 그 단계 하나를 쪽지 전체와 함께 돌려준다(GPT 가 긴 쪽지를 볼 때).
    전체=True 는 판(/plan)이 쓴다 — 모든 쪽지를 자르지 않는다.
    """
    if (action or "").strip() == "기록":
        정보 = 판정보()
        return {"지난목표": 정보["지난목표"], "개수": len(정보["지난목표"]),
                "되돌림수": 정보["되돌림수"],
                "안내": "되살리려면 나물 고구마 / 짓 되살리기 / 번호 …"}
    계획 = _읽기()
    if step is not None:
        if not (1 <= int(step) <= len(계획["steps"])):
            raise ValueError(f"'몇' 은 1~{len(계획['steps'])} 사이여야 합니다.")
        단계 = 계획["steps"][int(step) - 1]
        return {"task": 계획.get("task"), "step": int(step), **단계}
    return _보기좋게(계획, 전체=전체)


등록된도구 = {
    "plan_set": plan_set,
    "plan_update": plan_update,
    "plan_get": plan_get,
}
