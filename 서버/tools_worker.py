# -*- coding: utf-8 -*-
"""일꾼(서브 에이전트) — 대장 대화가 다른 ChatGPT 창에 일을 나눠 준다.

  콩 : 일꾼 부르기   역할 분석 / 이름 보상 조사 / 일《 … 》 / (먼저 번호,번호)
  팥 : 일꾼 살피기   번호 없이 → 목록 · 번호 … → 결과까지
                     상태 그만 · 다시 · 합치기 · 버리기 · (번호 없이) 실패만다시

흐름: 콩 → 장부에 '대기' → 대장 탭이 보고 새 탭을 엶 → 일꾼 탭이 일감 파일을 보냄 →
일꾼 GPT 가 제 방에서 일하고 【일꾼결과】…【일꾼결과끝】 으로 끝냄 → 장부 '끝' →
대장 탭이 한가할 때 결과를 대장 GPT 에게 보냄.

단계
  1  역할 분석·검토(읽기만).
  2  동시에 열두 명까지 돌기(처음엔 세 명이었다), 역할 시험(읽기 + 돌려보기), 다시 하기, 30분 넘으면 시간 초과.
  3  역할 구현 — 대장 폴더(깃 저장소)에 git worktree 로 일꾼 전용 복사 폴더
     <저장소>/.일꾼/<번호> (가지 일꾼/<번호>) 를 만들고, 일꾼 방은 그 폴더만 고친다.
     일꾼이 끝나면 그 가지에 맡긴다(commit). 대장이 '합치기' 로 본 폴더에 merge,
     충돌이면 merge 를 되돌리고 충돌 파일을 알린다. '버리기' 는 복사 폴더만 치우고 가지는 남긴다.
  4  순서 — '먼저' 로 적은 일꾼들이 끝나야 열린다. 앞 일꾼이 실패하면 뒤 일꾼도 실패.
     '실패만다시' 로 실패한 것만 다시.
일꾼은 일꾼을 못 부른다. 장부는 서버/방/_일꾼.json 하나(어느 탭이든 번호로 찾게).
"""

import json
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import rooms
import 안전파일

역할들 = ("분석", "검토", "시험", "구현")
동시최대 = 12                     # 실제로 도는(여는중·일하는중) 일꾼 수 — 탭이 이만큼 열린다
줄최대 = 24                       # 끝나지 않은(대기 포함) 일꾼 수
시간최대초 = 30 * 60              # 일하는 중으로 이만큼 넘으면 시간 초과
일최대 = 4000
이름최대 = 30
결과최대 = 30000
일꾼칸이름 = ".일꾼"               # 저장소 안의 worktree 자리(.git/info/exclude 로 숨김)
_잠금 = threading.RLock()

역할설명 = {
    "분석": "읽기만 합니다(열무·가지·미나리·버섯·더덕·토란·취). 파일을 고치거나 명령을 돌리지 마세요.",
    "검토": "읽기만 합니다. 바뀐 곳의 잘못·빠진 것·위험을 찾아 근거(자리·줄)와 함께 적으세요.",
    "시험": "읽고 돌려볼 수 있습니다(도라지·두릅·고사리). 파일은 고치지 마세요. 돌린 명령과 결과(끝번호·실패 줄)를 그대로 적으세요.",
    "구현": ("당신의 폴더는 일꾼 전용 복사본(git worktree)입니다. 거기서만 고치고 도라지로 확인하세요. "
            "끝나면 에이전트가 당신의 가지에 맡기고, 대장이 합칩니다. 칡 맡기기는 해도 되지만 밀기는 없습니다."),
}

끝난상태 = ("끝", "실패", "그만", "합침", "버림")


def _장부파일():
    return rooms.방뿌리 / "_일꾼.json"


def _읽기() -> list:
    return 안전파일.json읽기(_장부파일(), [], list)


def _쓰기(목록: list) -> None:
    파일 = _장부파일()
    파일.parent.mkdir(parents=True, exist_ok=True)
    안전파일.json쓰기(파일, 목록[-200:])


def _지금() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _보기(일꾼: dict, 결과도: bool = False) -> dict:
    값 = {k: 일꾼.get(k) for k in ("번호", "이름", "역할", "상태", "만든때", "끝때", "방", "먼저", "가지")}
    if 결과도:
        값["결과"] = 일꾼.get("결과", "")
    return 값


def 도는중인가(일꾼: dict) -> bool:
    return 일꾼.get("상태") in ("대기", "여는중", "일하는중")


def _달리는수(장부: list) -> int:
    return sum(1 for w in 장부 if w.get("상태") in ("여는중", "일하는중"))


def _시간넘은것치우기(장부: list) -> bool:
    """일하는 중으로 시간최대초를 넘긴 일꾼은 '실패(시간 초과)' 로. 바뀐 게 있으면 True."""
    바뀜 = False
    지금 = time.time()
    for w in 장부:
        if w.get("상태") in ("여는중", "일하는중") and 지금 - float(w.get("연때") or w.get("만든초") or 지금) > 시간최대초:
            w["상태"] = "실패"
            w["결과"] = f"시간 초과 — {시간최대초 // 60}분 안에 끝나지 않았습니다. 마지막 상태는 일꾼 방 기록을 보세요."
            w["끝때"] = _지금()
            바뀜 = True
    return 바뀜


def 다시하기(일꾼: dict) -> None:
    일꾼.update({"상태": "대기", "결과": "", "알림함": False, "끝때": "", "연때": 0, "만든초": time.time()})


# ── 깃 (3단계) ──────────────────────────────────────────────────
_이름표 = ["-c", "user.name=로컬 에이전트 일꾼", "-c", "user.email=agent@localhost"]


def _깃(자리, *뒷말, 이름표=False) -> tuple[int, str]:
    try:
        끝 = subprocess.run(["git", "-c", "core.quotepath=false"] + (_이름표 if 이름표 else []) + list(뒷말),
                           cwd=str(자리), capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        raise ValueError("깃이 깔려 있지 않습니다.")
    except subprocess.TimeoutExpired:
        raise ValueError("깃이 2분을 넘겨 멈췄습니다.")
    글 = ((끝.stdout or b"") + (끝.stderr or b"")).decode("utf-8", errors="replace").strip()
    return 끝.returncode, 글


def _저장소뿌리(밭: str) -> Path:
    번, 글 = _깃(밭, "rev-parse", "--show-toplevel")
    if 번 != 0:
        raise ValueError("구현 일꾼은 깃 저장소 폴더에서만 부를 수 있습니다. 먼저 칡 짓 시작 으로 저장소를 만드세요.")
    return Path(글.splitlines()[-1].strip())


def _일꾼칸숨기기(뿌리: Path) -> None:
    번, 글 = _깃(뿌리, "rev-parse", "--git-common-dir")
    if 번 != 0:
        return
    깃칸 = Path(글.splitlines()[-1].strip())
    if not 깃칸.is_absolute():
        깃칸 = 뿌리 / 깃칸
    제외 = 깃칸 / "info" / "exclude"
    제외.parent.mkdir(parents=True, exist_ok=True)
    있던것 = 제외.read_text(encoding="utf-8") if 제외.exists() else ""
    if (일꾼칸이름 + "/") not in 있던것.split():
        제외.write_text(있던것.rstrip("\n") + ("\n" if 있던것 else "") + 일꾼칸이름 + "/\n", encoding="utf-8")


def 복사폴더만들기(대장밭: str, 번호: str) -> dict:
    """대장 폴더 저장소에 일꾼 전용 worktree 를 만든다. 일꾼 방이 쓸 폴더를 돌려준다."""
    뿌리 = _저장소뿌리(대장밭)
    try:
        속자리 = Path(대장밭).resolve().relative_to(뿌리.resolve())
    except ValueError:
        속자리 = Path(".")
    _일꾼칸숨기기(뿌리)
    자리 = 뿌리 / 일꾼칸이름 / 번호
    가지 = "일꾼/" + 번호
    번, 글 = _깃(뿌리, "worktree", "add", "-b", 가지, str(자리), "HEAD")
    if 번 != 0:
        raise ValueError("일꾼 복사 폴더를 못 만들었습니다: " + 글[-400:])
    _, 바뀜 = _깃(뿌리, "status", "--porcelain")
    return {"자리": str(자리 / 속자리), "뿌리": str(뿌리), "복사뿌리": str(자리), "가지": 가지,
            "안맡긴수": len([줄 for 줄 in 바뀜.splitlines() if 줄.strip()])}


def _일꾼맡기기(일꾼: dict) -> str:
    """구현 일꾼이 끝났다 — 복사 폴더의 바뀐 것을 제 가지에 맡긴다. 한 줄 요약을 돌려준다."""
    복사 = 일꾼.get("복사뿌리")
    if not 복사 or not Path(복사).exists():
        return "(복사 폴더가 없습니다)"
    _, 바뀜 = _깃(복사, "status", "--porcelain")
    if 바뀜.strip():
        _깃(복사, "add", "-A")
        번, 글 = _깃(복사, "commit", "-m", f"일꾼 {일꾼['이름']} ({일꾼['번호']})", 이름표=True)
        if 번 != 0:
            return "맡기지 못했습니다: " + 글[-300:]
    _, 기록 = _깃(복사, "log", "--oneline", "-1")
    _, 통계 = _깃(일꾼["뿌리"], "diff", "--stat", "HEAD..." + 일꾼["가지"])
    return f"가지 {일꾼['가지']} · 마지막 {기록.splitlines()[0] if 기록 else '(없음)'}\n{통계 or '(본 폴더와 달라진 것 없음)'}"


def 합치기(일꾼: dict) -> dict:
    뿌리 = 일꾼["뿌리"]
    번, 글 = _깃(뿌리, "merge", "--no-ff", "--no-edit", 일꾼["가지"], 이름표=True)
    if 번 != 0:
        _, 충돌 = _깃(뿌리, "diff", "--name-only", "--diff-filter=U")
        _깃(뿌리, "merge", "--abort")
        충돌들 = [줄 for 줄 in 충돌.splitlines() if 줄.strip()]
        return {"합침": False, "충돌": 충돌들,
                "안내": ("충돌이 나서 되돌렸습니다. 충돌 파일을 보고 대장이 직접 고치거나, 일꾼에게 다시 시키세요."
                        if 충돌들 else "합치지 못했습니다(본 폴더에 맡기지 않은 변경이 있으면 먼저 칡 맡기기): " + 글[-300:])}
    복사폴더치우기(일꾼)
    return {"합침": True, "안내": 글.splitlines()[-1] if 글 else "합쳤습니다"}


def 복사폴더치우기(일꾼: dict) -> None:
    """worktree 폴더만 치운다. 가지는 남긴다(그 안의 작업이 사라지지 않게)."""
    복사 = 일꾼.get("복사뿌리")
    if 복사 and Path(복사).exists():
        _깃(일꾼["뿌리"], "worktree", "remove", "--force", 복사)


# ── 콩 : 일꾼 부르기 ───────────────────────────────────────────
def spawn_worker(task: str = "", name: str = "", role: str = "분석", after="", **_):
    대장 = rooms.지금방()
    if not 대장:
        raise ValueError("고른 방이 없습니다.")
    if 대장.get("부모"):
        raise ValueError("일꾼은 일꾼을 부를 수 없습니다. 결과를 【일꾼결과】 로 대장에게 넘기세요.")
    역할 = (role or "분석").strip()
    if 역할 not in 역할들:
        raise ValueError(f"역할은 {', '.join(역할들)} 중 하나입니다.")
    일 = (task or "").strip()
    if not 일:
        raise ValueError('"일" 이 비었습니다. 일꾼이 할 일을 구체적으로 적으세요(무엇을·어디서·무엇을 돌려줄지).')
    if len(일) > 일최대:
        raise ValueError(f"일이 너무 깁니다({일최대}자 안쪽).")
    이름 = ((name or "").strip() or 일.splitlines()[0])[:이름최대]
    먼저 = [x.strip() for x in (after if isinstance(after, list) else str(after or "").replace("，", ",").split(","))
           if str(x).strip()]

    with _잠금:
        장부 = _읽기()
        if sum(1 for w in 장부 if 도는중인가(w)) >= 줄최대:
            raise ValueError(f"끝나지 않은 일꾼이 {줄최대}명입니다. 팥으로 보고 끝나기를 기다리세요.")
        for 앞 in 먼저:
            if not any(w["번호"] == 앞 and w.get("대장방") == 대장["쪽번호"] for w in 장부):
                raise ValueError(f"'먼저' 의 일꾼을 못 찾았습니다: {앞}")
        번호 = uuid.uuid4().hex[:6]
        복사 = None
        if 역할 == "구현":
            if not 대장.get("밭"):
                raise ValueError("구현 일꾼은 일할 폴더가 정해진 방에서만 부를 수 있습니다.")
            복사 = 복사폴더만들기(대장["밭"], 번호)
        방 = rooms.일꾼방만들기(대장["쪽번호"], 이름, 역할, 밭=(복사 or {}).get("자리"))
        일꾼 = {
            "번호": 번호, "대장방": 대장["쪽번호"], "방": 방["쪽번호"], "이름": 이름, "역할": 역할,
            "일": 일, "상태": "대기", "만든때": _지금(), "끝때": "", "결과": "", "알림함": False,
            "만든초": time.time(), "먼저": 먼저,
        }
        if 복사:
            일꾼.update({"뿌리": 복사["뿌리"], "복사뿌리": 복사["복사뿌리"], "가지": 복사["가지"]})
        장부.append(일꾼)
        _쓰기(장부)
    안내 = (f"일꾼이 새 탭에서 일합니다(동시에 {동시최대}명까지, 넘으면 줄 섭니다). 끝나면 결과가 저절로 옵니다. "
            "서로 독립인 갈래가 더 있으면 같은 답에 콩을 더 부르고, 다 불렀으면 답을 끝내세요.")
    if 먼저:
        안내 = f"먼저 {', '.join(먼저)} 이 끝나면 열립니다. " + 안내
    if 복사:
        안내 += f" 일꾼 폴더: {복사['자리']} (가지 {복사['가지']}). 끝나면 팥 번호 {번호} / 상태 합치기."
        if 복사["안맡긴수"]:
            안내 += f" ◆ 본 폴더에 맡기지 않은 변경 {복사['안맡긴수']}개는 일꾼 폴더에 없습니다."
    return {**_보기(일꾼), "action": "부름", "안내": 안내}


# ── 팥 : 일꾼 살피기 ───────────────────────────────────────────
def _고칠수있나() -> None:
    import permission
    되나, 까닭 = permission.쓸수있나("부추")
    if not 되나:
        raise ValueError(까닭)


def watch_worker(job: str = "", status: str = "", **_):
    대장 = rooms.지금방() or {}
    번호 = (job or "").strip()
    짓 = (status or "").strip()
    with _잠금:
        장부 = _읽기()
        if not 번호:
            if 짓 in ("실패만다시", "실패다시"):
                다시들 = [w for w in 장부 if w.get("대장방") == 대장.get("쪽번호") and w.get("상태") == "실패"]
                for w in 다시들:
                    다시하기(w)
                _쓰기(장부)
                return {"일꾼들": [_보기(w) for w in 다시들], "개수": len(다시들), "action": "실패만 다시 부름"}
            내것 = [_보기(w) for w in 장부 if w.get("대장방") == 대장.get("쪽번호")][-10:]
            return {"일꾼들": 내것, "개수": len(내것)}
        일꾼 = next((w for w in 장부 if w["번호"] == 번호), None)
        if 일꾼 is None:
            raise ValueError(f"그런 일꾼이 없습니다: {번호}")
        if 짓 in ("다시", "다시하기"):
            if 도는중인가(일꾼):
                return {**_보기(일꾼), "action": "아직 돌고 있습니다"}
            if 일꾼["상태"] in ("합침", "버림"):
                raise ValueError("합치거나 버린 일꾼은 다시 할 수 없습니다. 콩으로 새로 부르세요.")
            다시하기(일꾼)
            _쓰기(장부)
            return {**_보기(일꾼), "action": "다시 부름"}
        if 짓 in ("그만", "멈춤", "중단"):
            if 도는중인가(일꾼):
                일꾼["상태"] = "그만"
                일꾼["끝때"] = _지금()
                _쓰기(장부)
                return {**_보기(일꾼), "action": "멈춤"}
            return {**_보기(일꾼), "action": "이미 끝나 있었습니다"}
        if 짓 == "합치기":
            if 일꾼.get("역할") != "구현" or not 일꾼.get("가지"):
                raise ValueError("합치기는 구현 일꾼만 합니다.")
            if 일꾼["상태"] != "끝":
                raise ValueError(f"끝난 일꾼만 합칩니다(지금 {일꾼['상태']}).")
            _고칠수있나()
            결과 = 합치기(일꾼)
            if 결과["합침"]:
                일꾼["상태"] = "합침"
                일꾼["끝때"] = _지금()
                _쓰기(장부)
            return {**_보기(일꾼), **결과, "action": "합침" if 결과["합침"] else "충돌"}
        if 짓 == "버리기":
            if 도는중인가(일꾼):
                raise ValueError("돌고 있는 일꾼은 먼저 멈추세요(상태 그만).")
            복사폴더치우기(일꾼)
            일꾼["상태"] = "버림"
            _쓰기(장부)
            return {**_보기(일꾼), "action": "복사 폴더를 치움(가지는 남김)"}
        return _보기(일꾼, 결과도=True)


등록된도구 = {
    "spawn_worker": spawn_worker,
    "watch_worker": watch_worker,
}


# ── 확장이 부르는 것 (나물이 아님) ─────────────────────────────

def 일감글(일꾼: dict) -> str:
    압축, _ = rooms.압축읽기(일꾼["대장방"])
    기억 = ""
    try:
        import tools_memory
        앞방 = rooms._고정된방()                      # 잡혀 있던 방을 풀어 버리지 않게 되돌린다
        rooms.방고정(일꾼["대장방"])
        try:
            기억 = tools_memory.read_memory().get("content", "")
        finally:
            rooms.방고정(앞방 or "")
    except Exception:
        기억 = ""
    앞결과 = []
    for 앞 in 일꾼.get("먼저") or []:
        w = next((x for x in _읽기() if x["번호"] == 앞), None)
        if w:
            앞결과 += [f"── 앞 일꾼 {w['이름']} ({w['번호']}) ──", (w.get("결과") or "(없음)").strip()]
    return "\n".join([
        "【일감 파일】 로컬 에이전트가 만든 일꾼 일감 (사용자 행동 아님)",
        f"일꾼: {일꾼['이름']}   역할: {일꾼['역할']}   번호: {일꾼['번호']}",
        "",
        "당신은 대장 대화가 부른 일꾼입니다. 사람과 이야기하지 않습니다. 아래 일만 하세요.",
        f"역할 규칙: {역할설명.get(일꾼['역할'], '')}",
        "숙주는 부르지 마세요. 필요한 앞 사정은 아래에 있습니다.",
        "",
        "끝내는 법: 일이 끝나면 바구니 없이 아래 꼴로 답하세요. 에이전트가 대장에게 넘깁니다.",
        "  【일꾼결과】",
        "  찾은 것(또는 바꾼 것) / 자리와 줄 / 근거·확인 결과 / 남은 의문",
        "  【일꾼결과끝】",
        "",
        "━━━━ 할 일 ━━━━",
        일꾼["일"],
        "",
        *(["━━━━ 앞 일꾼들의 결과 ━━━━", *앞결과, ""] if 앞결과 else []),
        "━━━━ 대장 대화의 압축 요약 ━━━━",
        압축.strip() or "(없음)",
        "",
        "━━━━ 프로젝트 기억 ━━━━",
        (기억 or "(없음)").strip(),
        "",
    ])


def _앞이끝났나(일꾼: dict, 장부: list) -> str:
    """'열어도 됨' · '기다림' · '실패:<까닭>'"""
    for 앞 in 일꾼.get("먼저") or []:
        w = next((x for x in 장부 if x["번호"] == 앞), None)
        if w is None:
            return f"실패:앞 일꾼 {앞} 을 못 찾음"
        if w["상태"] in ("실패", "그만", "버림"):
            return f"실패:앞 일꾼 {w['이름']} ({앞}) 이 {w['상태']}"
        if w["상태"] not in ("끝", "합침"):
            return "기다림"
    return "열어도 됨"


def 처리(짓: str, 몸통: dict) -> dict:
    with _잠금:
        장부 = _읽기()
        if _시간넘은것치우기(장부):
            _쓰기(장부)
        번호 = (몸통.get("번호") or "").strip()
        일꾼 = next((w for w in 장부 if w["번호"] == 번호), None) if 번호 else None
        if 일꾼 is None and 몸통.get("일꾼방"):       # 판은 방 번호로 부른다
            일꾼 = next((w for w in reversed(장부) if w.get("방") == 몸통["일꾼방"]), None)

        if 짓 == "열것":                       # 대장 탭: 열어야 할 일꾼이 있나
            방 = 몸통.get("방") or ""
            바뀜 = False
            열것 = None
            for w in 장부:
                if w.get("대장방") != 방 or w["상태"] != "대기":
                    continue
                판정 = _앞이끝났나(w, 장부)
                if 판정.startswith("실패:"):
                    w.update({"상태": "실패", "결과": 판정[3:], "끝때": _지금()})
                    바뀜 = True
                elif 판정 == "열어도 됨" and 열것 is None and _달리는수(장부) < 동시최대:
                    열것 = w
            if 열것 is not None:
                열것["상태"] = "여는중"
                열것["연때"] = time.time()
                바뀜 = True
            if 바뀜:
                _쓰기(장부)
            return {"일꾼": _보기(열것) if 열것 else None}

        if 짓 == "일감":                       # 일꾼 탭: 무엇을 하나
            if 일꾼 is None:
                raise ValueError("그런 일꾼이 없습니다.")
            if 일꾼["상태"] in ("여는중", "대기"):
                일꾼["상태"] = "일하는중"
                일꾼["연때"] = time.time()
                _쓰기(장부)
            return {"일꾼": _보기(일꾼), "글": 일감글(일꾼)}

        if 짓 == "상태":                       # 일꾼 탭: 멈추라고 했나
            if 일꾼 is None:
                raise ValueError("그런 일꾼이 없습니다.")
            return {"일꾼": _보기(일꾼)}

        if 짓 == "결과":                       # 일꾼 탭: 끝냈다
            if 일꾼 is None:
                raise ValueError("그런 일꾼이 없습니다.")
            if 도는중인가(일꾼):
                실패 = bool(몸통.get("실패"))
                글 = str(몸통.get("글") or "")
                if 일꾼.get("역할") == "구현" and not 실패:
                    try:
                        글 += "\n\n── 맡긴 것 ──\n" + _일꾼맡기기(일꾼) + \
                             f"\n합치려면: 나물 팥 / 번호 {일꾼['번호']} / 상태 합치기"
                    except ValueError as e:
                        글 += f"\n\n(맡기기 실패: {e})"
                일꾼["상태"] = "실패" if 실패 else "끝"
                일꾼["결과"] = 글[:결과최대]
                일꾼["끝때"] = _지금()
                _쓰기(장부)
            return {"일꾼": _보기(일꾼)}

        if 짓 == "알릴것":                     # 대장 탭: 넘겨받을 결과가 있나
            방 = 몸통.get("방") or ""
            일꾼 = next((w for w in 장부 if w.get("대장방") == 방 and w["상태"] in ("끝", "실패")
                        and not w.get("알림함")), None)
            return {"일꾼": _보기(일꾼, 결과도=True) if 일꾼 else None}

        if 짓 == "알림함":
            if 일꾼 is not None:
                일꾼["알림함"] = True
                _쓰기(장부)
            return {"일꾼": _보기(일꾼) if 일꾼 else None}

        if 짓 == "그만":                       # 판의 ⋮ 일꾼 멈추기
            if 일꾼 is None:
                raise ValueError("그런 일꾼이 없습니다.")
            if 도는중인가(일꾼):
                일꾼["상태"] = "그만"
                일꾼["끝때"] = _지금()
                _쓰기(장부)
            return {"일꾼": _보기(일꾼)}

        if 짓 == "다시":                       # 판의 ⋮ 일꾼 다시
            if 일꾼 is None:
                raise ValueError("그런 일꾼이 없습니다.")
            if not 도는중인가(일꾼) and 일꾼["상태"] not in ("합침", "버림"):
                다시하기(일꾼)
                _쓰기(장부)
            return {"일꾼": _보기(일꾼)}

        if 짓 == "합치기":                     # 판의 ⋮ 일꾼 합치기 (구현)
            if 일꾼 is None:
                raise ValueError("그런 일꾼이 없습니다.")
            앞방 = rooms._고정된방()
            rooms.방고정(일꾼["대장방"])
            try:
                return watch_worker(job=일꾼["번호"], status="합치기")
            finally:
                rooms.방고정(앞방 or "")

        if 짓 == "목록":
            방 = 몸통.get("방") or ""
            return {"일꾼들": [_보기(w) for w in 장부 if w.get("대장방") == 방][-10:]}

        raise ValueError(f"모르는 짓입니다: {짓}")


def 방상태표() -> dict:
    """일꾼 방 번호 → 그 방의 가장 최근 일꾼 상태(판에 보인다)."""
    with _잠금:
        장부 = _읽기()
    표 = {}
    for w in 장부:
        표[w.get("방")] = w.get("상태")
    return 표
