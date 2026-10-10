# -*- coding: utf-8 -*-
"""폴더와 대화방.

  폴더   : 윈도우 선택창으로 고른 진짜 폴더. 이름은 폴더 이름 그대로.
  대화방 : 그 폴더에서 하는 일 하나. 이름은 에이전트가 처음에 짓는다.

한 폴더 밑에 대화방을 여러 개 둘 수 있다. 방마다 기억과 차례가 따로 남는다.
방 자료는 작업 폴더를 어지럽히지 않게 서버/방/ 밑에 모아 둔다.

ChatGPT 대화와는 묶이지 않는다. 어느 대화에서든 방을 눌러 이어서 하면 된다.
"""

import json
import os
import shutil
import threading
import time
import re
import uuid
from datetime import datetime
from pathlib import Path

import sandbox
import 안전파일

방뿌리 = Path(__file__).with_name("방")
목록파일 = Path(__file__).with_name("방목록.json")

없는폴더이름 = "폴더 없음"


def _정규화(p) -> Path:
    try:
        return Path(os.path.realpath(str(p)))
    except OSError:
        return Path(str(p)).absolute()


def _지금() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _기본값() -> dict:
    return {"폴더들": [], "방들": [], "지금방": None, "허락": []}


# ── 이번 요청이 볼 방 ──────────────────────────────────────────
# ChatGPT 창을 여러 개 띄워 놓고 서로 다른 프로젝트를 동시에 하려면,
# 서버에 '지금방' 이 하나뿐이어서는 안 된다.
# 그래서 도구를 부를 때 어느 방인지 같이 보내고, 그 요청 동안만 그 방을 본다.
# (요청마다 실이 따로라 서로 섞이지 않는다)
_이번 = threading.local()


def 방고정(쪽번호: str) -> None:
    _이번.방 = (쪽번호 or "").strip() or None


def 방풀기() -> None:
    _이번.방 = None


def _고정된방() -> str | None:
    return getattr(_이번, "방", None)


# 목록 파일은 요청마다(서버는 요청마다 실이 따로) 읽고 쓴다. 예전엔 쓰는 도중(파일을 비운 뒤 채우기 전)
# 다른 실이 읽으면 읽기 실패 → '빈 목록' 이 돌아왔고, 그 상태로 고쳐 쓰는 바람에 폴더·방 목록이 통째로 날아갔다
# (재현: 쓰는 실과 읽는 실을 같이 돌리면 읽기 1000번 중 377번이 빈 목록).
# 그래서 ① 임시 파일에 다 쓴 뒤 한 번에 바꿔 끼우고(읽는 쪽은 늘 온전한 파일을 봄) ② 읽기가 실패하면
# 빈 목록으로 가기 전에 다시 읽고, 끝내 안 되면 백업에서 읽고 ③ 쓰기 전에 백업을 남긴다.
_파일자물쇠 = threading.RLock()
백업간격초 = 600
백업개수 = 30


def _백업폴더() -> Path:
    return 목록파일.with_name("방목록백업")


def _백업목록() -> list:
    try:
        return sorted(_백업폴더().glob("방목록_*.json"))
    except OSError:
        return []


def _값읽기(경로: Path) -> dict | None:
    """온전한 목록이면 값, 아니면 None."""
    try:
        값 = json.loads(경로.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return 값 if isinstance(값, dict) else None


def _백업남기기() -> None:
    """지금 파일이 온전하고 방이 있으면, 마지막 백업이 오래됐을 때 한 부 복사한다."""
    현재 = _값읽기(목록파일)
    if not 현재 or not (현재.get("방들") or 현재.get("폴더들")):
        return
    백업들 = _백업목록()
    if 백업들 and time.time() - 백업들[-1].stat().st_mtime < 백업간격초:
        return
    try:
        폴더 = _백업폴더()
        폴더.mkdir(exist_ok=True)
        이름 = "방목록_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
        shutil.copy2(목록파일, 폴더 / 이름)
        for 옛 in _백업목록()[:-백업개수]:
            옛.unlink(missing_ok=True)
    except OSError:
        pass                          # 백업이 안 돼도 본 저장은 막지 않는다


def 읽기() -> dict:
    값 = None
    for 번 in range(4):
        if not 목록파일.exists():
            return _기본값()          # 처음 쓰는 것이면 빈 목록이 맞다
        값 = _값읽기(목록파일)
        if 값 is not None:
            break
        time.sleep(0.05 * (번 + 1))
    if 값 is None:
        # 파일이 정말 깨졌다 — 깨진 것은 따로 두고, 가장 최근 백업에서 읽는다(빈 목록으로 덮어쓰지 않는다)
        안전파일.깨진것남기기(목록파일)
        for 백업 in reversed(_백업목록()):
            값 = _값읽기(백업)
            if 값 is not None:
                break
    if 값 is None:
        return _기본값()
    기본 = _기본값()
    기본.update(값)
    return 기본


def 안전쓰기(경로: Path, 글: str) -> None:
    """임시 파일에 다 쓴 뒤 한 번에 바꿔 끼운다 — 읽는 쪽은 늘 온전한 파일을 보고, 쓰다 죽어도 원본이 남는다."""
    안전파일.쓰기(경로, 글)


def 쓰기(값: dict) -> None:
    글 = json.dumps(값, ensure_ascii=False, indent=2)
    with _파일자물쇠:
        _백업남기기()
        안전쓰기(목록파일, 글)


# ── 폴더 ───────────────────────────────────────────────────────

def 폴더더하기(밭: str, 이름: str = "") -> dict:
    """윈도우 선택창에서 고른 자리를 폴더로 등록한다."""
    대상 = _정규화(밭)
    if not 대상.exists():
        raise ValueError(f"그런 자리가 없습니다: {대상}")
    if not 대상.is_dir():
        raise ValueError(f"폴더가 아닙니다: {대상}")

    뿌리 = _정규화(Path(sandbox.설정["루트"]))
    try:
        대상.relative_to(뿌리)
    except ValueError:
        raise ValueError(
            f"{뿌리} 안쪽만 됩니다. 고른 자리: {대상}"
        )

    설정 = 읽기()
    for 폴더 in 설정["폴더들"]:
        if 폴더["밭"] == str(대상):
            return 폴더

    폴더 = {
        "쪽번호": uuid.uuid4().hex[:8],
        "이름": 이름 or 대상.name or str(대상),
        "밭": str(대상),
        "만든때": _지금(),
    }
    설정["폴더들"].append(폴더)
    쓰기(설정)
    return 폴더


def 폴더빼기(쪽번호: str) -> dict:
    """폴더를 목록에서 뺀다. 디스크는 건드리지 않는다."""
    설정 = 읽기()
    설정["폴더들"] = [f for f in 설정["폴더들"] if f["쪽번호"] != 쪽번호]
    for 방 in 설정["방들"]:
        if 방.get("폴더") == 쪽번호:
            방["폴더"] = None
    쓰기(설정)
    return {"뺀것": 쪽번호}


def 폴더이름바꾸기(쪽번호: str, 새이름: str) -> dict:
    새이름 = (새이름 or "").strip()
    if not 새이름:
        raise ValueError("이름이 비었습니다.")
    설정 = 읽기()
    for 폴더 in 설정["폴더들"]:
        if 폴더["쪽번호"] == 쪽번호:
            폴더["이름"] = 새이름[:60]
            폴더["이름고정"] = True      # ChatGPT 프로젝트 이름이 바뀌어도 덮지 않는다
            쓰기(설정)
            return 폴더
    raise ValueError("그런 폴더가 없습니다.")


# ── ChatGPT 프로젝트 = 묶음 ────────────────────────────────────
# ChatGPT 프로젝트 하나를 판의 묶음(폴더) 하나로 본다. 그 프로젝트의 대화는
# 저절로 그 묶음 아래 방이 되고, 일할 폴더도 묶음에서 한 번만 정한다.
# 주소 /g/g-p-<번호>/c/<대화> 의 g-p-<번호> 가 프로젝트 번호다.

_프로젝트꼴 = re.compile(r"^g-p-[0-9a-f]{16,64}$")


def 프로젝트번호다듬기(번호) -> str:
    번호 = str(번호 or "").strip()
    return 번호 if _프로젝트꼴.match(번호) else ""


def _묶음찾기(설정: dict, 프로젝트: str) -> dict | None:
    return next((f for f in 설정["폴더들"] if f.get("프로젝트") == 프로젝트), None)


def _방을묶음에(설정: dict, 방: dict, 프로젝트: str, 프로젝트이름: str) -> None:
    """방을 프로젝트 묶음에 넣는다. 묶음이 없으면 만든다. 설정만 고치고 쓰지는 않는다.

    사람이 판에서 끌어 옮긴 방(폴더고정)은 건드리지 않는다. 예전엔 대화를 열 때마다
    프로젝트 묶음으로 다시 넣어, 끌어 놓은 자리가 창을 닫고 켜면 되돌아갔다.
    """
    if 방.get("폴더고정"):
        return
    묶음 = _묶음찾기(설정, 프로젝트)
    if 묶음 is None:
        # 예전에 사람이 고른 폴더에 들어 있던 방이면, 그 폴더를 이 프로젝트 묶음으로 삼는다.
        # (새 묶음을 만들면 사람이 골라 둔 일할 폴더가 사라진 것처럼 보인다)
        옛것 = next((f for f in 설정["폴더들"]
                    if f["쪽번호"] == 방.get("폴더") and not f.get("프로젝트")), None)
        if 옛것 is not None:
            묶음 = 옛것
            묶음["프로젝트"] = 프로젝트
        else:
            묶음 = {
                "쪽번호": uuid.uuid4().hex[:8],
                "이름": (프로젝트이름 or "").strip()[:60] or "이름 없는 프로젝트",
                "밭": None,                 # 판에서 한 번 고른다
                "프로젝트": 프로젝트,
                "만든때": _지금(),
            }
            설정["폴더들"].append(묶음)
    새이름 = (프로젝트이름 or "").strip()[:60]
    if 새이름 and not 묶음.get("이름고정") and 묶음.get("이름") != 새이름:
        묶음["이름"] = 새이름
    방["폴더"] = 묶음["쪽번호"]
    방["밭"] = 묶음.get("밭")


# ── 압축 요약 ──────────────────────────────────────────────────
# Claude·Codex 처럼 긴 대화를 틀을 갖춘 요약 한 장으로 줄인다. 새 대화가 넘김 파일을 읽고
# 【압축】…【압축끝】 로 쓰면 확장이 여기 적는다. 다음 넘김은 '이 요약 + 그 뒤 기록' 만 넘긴다.

def 압축적기(쪽번호: str, 글: str) -> dict:
    글 = (글 or "").strip()
    if not 글:
        raise ValueError("압축 요약이 비었습니다.")
    if len(글) > 40000:
        raise ValueError("압축 요약이 너무 깁니다(4만 자 넘음).")
    설정 = 읽기()
    방 = next((r for r in 설정["방들"] if r["쪽번호"] == 쪽번호), None)
    if 방 is None:
        raise ValueError("그런 방이 없습니다.")
    안전파일.쓰기(방자료칸(쪽번호) / "압축.md", 글 + "\n", newline="\n")
    방["압축기준"] = len(대화읽기(쪽번호, 최대=0))      # 이 뒤의 기록만 다음 넘김에 넣는다
    방["압축때"] = _지금()
    쓰기(설정)
    대화추가(쪽번호, 압축표종류, "")        # 기록 안에 '여기까지 요약했다' 는 표를 남긴다
    return {"압축기준": 방["압축기준"], "글자수": len(글)}


def 압축읽기(쪽번호: str) -> tuple[str, int]:
    설정 = 읽기()
    방 = next((r for r in 설정["방들"] if r["쪽번호"] == 쪽번호), None) or {}
    파일 = 방자료칸(쪽번호) / "압축.md"
    글 = 안전파일.글읽기(파일) if 파일.exists() else ""
    return 글, int(방.get("압축기준") or 0)


def 압축뒤기록(쪽번호: str) -> tuple[list, int]:
    """압축 요약을 쓴 뒤에 쌓인 기록과, 그 앞에 있어 뺀 건수.

    '압축기준' 은 요약을 쓸 때의 기록 수(자리 번호)다. 기록은 꽉 차면 앞에서부터
    잘리므로 자리 번호는 금방 어긋난다 — 500건이 찬 방은 기준이 500 이라 그 뒤가
    늘 0건이었다(넘김 파일에 최근 대화가 하나도 안 실림).
    그래서 기록 안에 남긴 표를 찾고, 표가 없는 옛 방은 요약을 쓴 때로 고른다.
    """
    대화 = 대화읽기(쪽번호, 최대=0)
    설정 = 읽기()
    방 = next((r for r in 설정["방들"] if r["쪽번호"] == 쪽번호), None) or {}
    때 = 방.get("압축때") or ""
    표 = max((번 for 번, 항 in enumerate(대화) if 항.get("종류") == 압축표종류), default=-1)
    if 표 >= 0:
        시작 = 표 + 1
    elif 때:
        # 때는 분까지만 적힌다. 같은 분의 것은 넣는다(빠뜨리는 것보다 겹치는 게 낫다).
        시작 = next((번 for 번, 항 in enumerate(대화) if (항.get("때") or "") >= 때), len(대화))
    else:
        시작 = min(int(방.get("압축기준") or 0), len(대화))
    return 대화[시작:], 시작


def 프로젝트이름맞추기(프로젝트: str, 이름: str) -> dict | None:
    """ChatGPT 에서 본 프로젝트 이름으로 판의 묶음 이름을 맞춘다(사람이 판에서 고친 이름은 둔다)."""
    프로젝트 = 프로젝트번호다듬기(프로젝트)
    이름 = (이름 or "").strip()[:60]
    if not 프로젝트 or not 이름:
        return None
    설정 = 읽기()
    묶음 = _묶음찾기(설정, 프로젝트)
    if 묶음 is None or 묶음.get("이름고정") or 묶음.get("이름") == 이름:
        return 묶음
    묶음["이름"] = 이름
    쓰기(설정)
    return 묶음


def 묶음밭정하기(쪽번호: str, 밭: str) -> dict:
    """프로젝트 묶음의 일할 폴더를 정한다. 그 묶음의 방 모두가 이 폴더를 쓴다."""
    대상 = _정규화(밭)
    if not 대상.is_dir():
        raise ValueError(f"폴더가 아닙니다: {대상}")
    뿌리 = _정규화(Path(sandbox.설정["루트"]))
    try:
        대상.relative_to(뿌리)
    except ValueError:
        raise ValueError(f"{뿌리} 안쪽만 됩니다. 고른 자리: {대상}")

    설정 = 읽기()
    묶음 = next((f for f in 설정["폴더들"] if f["쪽번호"] == 쪽번호), None)
    if 묶음 is None:
        raise ValueError("그런 묶음이 없습니다.")
    묶음["밭"] = str(대상)
    for 방 in 설정["방들"]:
        if 방.get("폴더") == 쪽번호:
            방["밭"] = str(대상)
    쓰기(설정)
    return 묶음


def 프로젝트기억칸(쪽번호: str = "") -> Path | None:
    """이 방이 ChatGPT 프로젝트에 속하면 그 프로젝트의 방들이 같이 쓰는 칸."""
    설정 = 읽기()
    방번호 = 쪽번호 or (지금방() or {}).get("쪽번호")
    방 = next((r for r in 설정["방들"] if r["쪽번호"] == 방번호), None)
    if not 방 or not 방.get("폴더"):
        return None
    묶음 = next((f for f in 설정["폴더들"] if f["쪽번호"] == 방["폴더"]), None)
    if not 묶음 or not 묶음.get("프로젝트"):
        return None
    칸 = 방뿌리 / "_프로젝트" / 묶음["쪽번호"]
    칸.mkdir(parents=True, exist_ok=True)
    return 칸


# ── 대화방 ─────────────────────────────────────────────────────

def 방만들기(폴더쪽번호: str = "", 이름: str = "") -> dict:
    설정 = 읽기()

    밭 = None
    if 폴더쪽번호:
        찾음 = next((f for f in 설정["폴더들"] if f["쪽번호"] == 폴더쪽번호), None)
        if 찾음 is None:
            raise ValueError("그런 폴더가 없습니다.")
        밭 = 찾음["밭"]

    방 = {
        "쪽번호": uuid.uuid4().hex[:8],
        "이름": (이름 or "").strip()[:60] or "",   # 비워두면 에이전트가 짓는다
        "폴더": 폴더쪽번호 or None,
        "밭": 밭,
        "만든때": _지금(),
        "마지막": _지금(),
    }
    설정["방들"].append(방)
    설정["지금방"] = 방["쪽번호"]
    쓰기(설정)
    (방뿌리 / 방["쪽번호"]).mkdir(parents=True, exist_ok=True)
    return 방


def 일꾼방만들기(대장방: str, 이름: str, 역할: str, 밭: str | None = None) -> dict:
    """대장 방 아래 일꾼 방. 같은 묶음·같은 폴더를 쓰고, 프로젝트를 따라 옮기지 않는다.

    밭 을 주면(구현 일꾼의 worktree) 그 폴더만 고칠 수 있다.
    """
    설정 = 읽기()
    대장 = next((r for r in 설정["방들"] if r["쪽번호"] == 대장방), None)
    if 대장 is None:
        raise ValueError("그런 방이 없습니다.")
    방 = {
        "쪽번호": uuid.uuid4().hex[:8],
        "이름": ("일꾼 · " + (이름 or "").strip())[:60],
        "이름고정": True,
        "폴더": 대장.get("폴더"),
        "밭": 밭 or 대장.get("밭"),
        "폴더고정": True,
        "부모": 대장방,
        "역할": 역할,
        "대화": None,
        "만든때": _지금(),
        "마지막": _지금(),
    }
    설정["방들"].append(방)
    쓰기(설정)
    (방뿌리 / 방["쪽번호"]).mkdir(parents=True, exist_ok=True)
    return 방


def 방역할(쪽번호: str) -> str:
    """일꾼 방이면 그 역할, 아니면 ''."""
    설정 = 읽기()
    방 = next((r for r in 설정["방들"] if r["쪽번호"] == 쪽번호), None)
    return (방 or {}).get("역할") or ""


def 방빼기(쪽번호: str) -> dict:
    설정 = 읽기()
    설정["방들"] = [r for r in 설정["방들"] if r["쪽번호"] != 쪽번호]
    if 설정["지금방"] == 쪽번호:
        설정["지금방"] = None
    쓰기(설정)
    return {"뺀것": 쪽번호}


def 방폴더바꾸기(쪽번호: str, 폴더쪽번호: str) -> dict:
    """방을 다른 폴더 밑으로 옮긴다(끌어다 놓기). 폴더쪽번호가 비면 '폴더 없음' 으로."""
    설정 = 읽기()
    방 = next((r for r in 설정["방들"] if r["쪽번호"] == 쪽번호), None)
    if 방 is None:
        raise ValueError("그런 방이 없습니다.")

    if 폴더쪽번호:
        폴더 = next((f for f in 설정["폴더들"] if f["쪽번호"] == 폴더쪽번호), None)
        if 폴더 is None:
            raise ValueError("그런 폴더가 없습니다.")
        방["폴더"] = 폴더쪽번호
        방["밭"] = 폴더["밭"]
    else:
        방["폴더"] = None
        방["밭"] = None
    # 사람이 옮긴 자리다. ChatGPT 프로젝트를 따라 저절로 다시 옮기지 않는다.
    방["폴더고정"] = True

    쓰기(설정)
    return 방


def 방이름바꾸기(쪽번호: str, 새이름: str, 자동: bool = False) -> dict:
    """방 이름을 바꾼다.

    자동 = ChatGPT 대화 제목을 따라 탭이 바꾸는 것. 사람이 판에서 직접 바꾼 방은
    '이름고정' 이 붙어, 그 뒤로는 탭이 제목을 따라 덮지 않는다.
    """
    새이름 = (새이름 or "").strip()
    if not 새이름:
        raise ValueError("이름이 비었습니다.")
    설정 = 읽기()
    for 방 in 설정["방들"]:
        if 방["쪽번호"] == 쪽번호:
            if 자동 and 방.get("이름고정"):
                return 방
            # 새 대화로 넘긴 방은 새 대화 제목을 따라가지 않는다(판에서 방 이름이 바뀌면 헷갈린다)
            if 자동 and 방.get("대화들"):
                return 방
            방["이름"] = 새이름[:60]
            if not 자동:
                방["이름고정"] = True
            쓰기(설정)
            return 방
    raise ValueError("그런 방이 없습니다.")


def 방고르기(쪽번호: str) -> dict:
    설정 = 읽기()
    방 = next((r for r in 설정["방들"] if r["쪽번호"] == 쪽번호), None)
    if 방 is None:
        raise ValueError("그런 방이 없습니다.")
    방["마지막"] = _지금()
    설정["지금방"] = 쪽번호
    설정["허락"] = []          # 방이 바뀌면 허락은 초기화
    쓰기(설정)
    대기요청.clear()
    (방뿌리 / 쪽번호).mkdir(parents=True, exist_ok=True)
    return {**방, "대화": 대화읽기(쪽번호)}


def 지금방() -> dict | None:
    """이번 요청이 볼 방. 요청이 방을 찍어 보냈으면 그것, 아니면 마지막으로 고른 방."""
    설정 = 읽기()
    찍은것 = _고정된방()
    쪽번호 = 찍은것 or 설정["지금방"]
    if not 쪽번호:
        return None
    return next((r for r in 설정["방들"] if r["쪽번호"] == 쪽번호), None)


def 지금밭() -> Path | None:
    """지금 방이 고칠 수 있는 자리. 폴더를 안 정한 방은 None."""
    방 = 지금방()
    if not 방 or not 방.get("밭"):
        return None
    자리 = _정규화(방["밭"])
    return 자리 if 자리.exists() else None


def 방자료칸(쪽번호: str = "") -> Path:
    """이 방의 기억·차례가 남는 자리."""
    쪽번호 = 쪽번호 or (지금방() or {}).get("쪽번호") or "임시"
    칸 = 방뿌리 / 쪽번호
    칸.mkdir(parents=True, exist_ok=True)
    return 칸


# ── 방별 대화 ──────────────────────────────────────────────────
# 방에 들어가면 전에 하던 대화를 그대로 이어 볼 수 있게 남겨 둔다.
# 종류는 '나' (사용자가 보낸 것) 또는 'gpt' (모델의 바구니/일반 답).
# 화면에서는 '나' 쪽 소쿠리 원문은 숨기고 gpt 바구니만 번역해서 보여주지만,
# 저장 자체는 둘 다 그대로 한다 — 나중에 다시 볼 수도 있어야 하니까.

대화최대건수 = 500

# GPT 가 사람 눈에 보이는 말(사용자·gpt)을 안 하고 도구만 이어 부른 횟수. 방마다, 서버를 켠 뒤부터 센다.
# 길잡이가 '지금 무엇을 하는지 한마디 해 주세요' 하고 일러 줄 때 쓴다.
말없는도구 = {}

# GPT 답에 '아마' · '~것 같다' 같은 확실하지 않은 말이 있으면 방마다 적어 둔다. 길잡이가 다음 도구 결과에서
# '짐작으로 가지 말고 물어보라' 고 한 번 일러 준다. 이미 【물음】 으로 물었으면 적지 않는다.
불확실한말 = {}
_불확실꼴 = re.compile(r"아마|것 같|듯합니다|듯해요|추측|짐작|확실하지|잘 모르|모르겠|가정하고|추정")


def 불확실말찾기(글: str) -> str:
    """확실하지 않다는 뜻의 말이 있으면 그 말(앞뒤 조금 포함), 없으면 빈 글."""
    if not 글 or "【물음】" in 글:
        return ""
    m = _불확실꼴.search(글)
    if not m:
        return ""
    return 글[max(0, m.start() - 12): m.end() + 12].replace(chr(10), " ").strip()


def 말없는도구수(쪽번호: str = "") -> int:
    쪽번호 = 쪽번호 or (지금방() or {}).get("쪽번호") or ""
    return 말없는도구.get(쪽번호, 0)

# 같은 말이 또 들어왔는지 얼마나 뒤까지 살필지.
# 탭을 새로 고칠 때마다 화면에 떠 있던 답변이 다시 들어와서,
# 중간에 다른 말이 끼어 있어도 같은 글이 여러 번 쌓인다.
겹침살필개수 = 30


def _대화파일(쪽번호: str = "") -> Path:
    return 방자료칸(쪽번호) / "대화.json"


# 대화 기록(대화.json)을 잠시 못 읽을 때(G: 가 구글 드라이브라 올리는 동안 잠긴다) 예전엔 '빈 기록' 으로 보고,
# 그 위에 새 말 한 줄만 써서 기록 607건이 1건이 됐다(2026-10-04). 그래서
# ① 없는 것(처음 쓰는 방)과 못 읽는 것(잠김·깨짐)을 가르고 ② 못 읽으면 쓰지 않고 ③ 깨졌으면 백업에서 읽고
# ④ 쓰기 전에 10분마다 백업을 남긴다.
대화백업간격초 = 600
대화백업개수 = 48
대화백업최소건수 = 3
_대화잠김기다림 = 12          # 쓰기 쪽이 잠김을 기다리는 횟수(0.25초씩, 약 3초)


class 대화못읽음(OSError):
    """대화 기록이 있는데 지금은 못 읽는다. 빈 기록으로 보고 덮어쓰면 안 된다."""


def _대화백업폴더(쪽번호: str = "") -> Path:
    return 방자료칸(쪽번호) / "대화백업"


def _대화백업목록(쪽번호: str = "") -> list:
    try:
        return sorted(_대화백업폴더(쪽번호).glob("대화_*.json"))
    except OSError:
        return []


def _대화백업하기(쪽번호: str, 목록: list) -> None:
    """방금 온전하게 읽은 기록을, 마지막 백업이 오래됐을 때 한 부 남긴다. 안 돼도 본 저장은 막지 않는다."""
    if len(목록) < 대화백업최소건수:
        return
    try:
        백업들 = _대화백업목록(쪽번호)
        if 백업들 and time.time() - 백업들[-1].stat().st_mtime < 대화백업간격초:
            return
        폴더 = _대화백업폴더(쪽번호)
        폴더.mkdir(exist_ok=True)
        안전파일.json쓰기(폴더 / ("대화_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"), 목록)
        for 옛 in _대화백업목록(쪽번호)[:-대화백업개수]:
            옛.unlink(missing_ok=True)
    except OSError:
        pass


def _대화백업읽기(쪽번호: str) -> list | None:
    """가장 최근의 온전한 백업. 없으면 None."""
    for 백업 in reversed(_대화백업목록(쪽번호)):
        try:
            값 = json.loads(백업.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(값, list) and 값:
            return 값
    return None


def _대화읽어보기(쪽번호: str, 번수: int = 4) -> tuple:
    """(상태, 목록). 상태: 됨 | 없음 | 못읽음(잠김 같은 읽기 오류) | 깨짐(내용이 목록이 아님). 못읽음·깨짐이면 목록은 None."""
    파일 = _대화파일(쪽번호)
    상태 = "없음"
    for 번 in range(번수):
        if not 파일.exists():
            return "없음", []
        try:
            목록 = json.loads(파일.read_text(encoding="utf-8"))
        except OSError:
            상태 = "못읽음"
        except ValueError:
            상태 = "깨짐"
        else:
            if isinstance(목록, list):
                return "됨", 목록
            상태 = "깨짐"
        if 번 < 번수 - 1:
            time.sleep(0.25 if 번수 > 4 else 0.05 * (번 + 1))
    if 상태 == "깨짐":
        # 정말 깨졌다 — 다음 쓰기가 덮어쓰기 전에 깨진 것을 따로 남긴다(옛 기록이 증거가 된다)
        안전파일.깨진것남기기(파일)
    return 상태, None


def 대화읽기(쪽번호: str = "", 최대: int = 200, 엄격: bool = False) -> list:
    """대화 기록. 못 읽으면 보기용으로는 빈 목록(깨졌으면 백업)이지만, 고쳐 쓸 때는 엄격=True 로 불러 예외를 받는다."""
    상태, 목록 = _대화읽어보기(쪽번호)
    if 목록 is None:
        if 엄격:
            raise 대화못읽음(f"대화 기록을 읽을 수 없습니다({상태}). 빈 기록으로 덮어쓰지 않으려고 멈춥니다.")
        목록 = (_대화백업읽기(쪽번호) if 상태 == "깨짐" else None) or []
    return 목록[-최대:] if 최대 else 목록


# 사람과 GPT 가 주고받은 말. 도구 줄·소쿠리 원문('나')과 따로 센다.
# 한 번 일하면 도구 줄과 소쿠리가 수백 개 쌓여, 같이 세면 말이 밀려났다
# (발로란트 방: 500건 중 말 24건, 판에 보낸 마지막 200건 중 말 5건 — 옛 대화가 안 보였다).
말종류 = ("사용자", "gpt", "예약")
말최대건수 = 400
판도구최대 = 200
압축표종류 = "압축표"       # 압축 요약을 쓴 자리 표시. 판에는 안 보낸다.
판에안보낼종류 = ("나", 압축표종류)


def _대화줄이기(목록: list) -> list:
    """말은 말끼리, 나머지는 나머지끼리 최근 것만 남긴다. 순서는 그대로."""
    말 = [번 for 번, 항 in enumerate(목록) if 항.get("종류") in 말종류]
    딴 = [번 for 번, 항 in enumerate(목록) if 항.get("종류") not in 말종류]
    if len(말) <= 말최대건수 and len(딴) <= 대화최대건수:
        return 목록
    남길 = set(말[-말최대건수:]) | set(딴[-대화최대건수:])
    return [항 for 번, 항 in enumerate(목록) if 번 in 남길]


def 판대화읽기(쪽번호: str = "") -> list:
    """판에 보일 것 — 남아 있는 말 전부 + 최근 도구 줄. 소쿠리 원문('나')은 판이 안 쓴다."""
    목록 = 대화읽기(쪽번호, 최대=0)
    딴 = [번 for 번, 항 in enumerate(목록)
          if 항.get("종류") not in 말종류 and 항.get("종류") not in 판에안보낼종류]
    남길 = set(딴[-판도구최대:])
    return [항 for 번, 항 in enumerate(목록) if 항.get("종류") in 말종류 or 번 in 남길]


def 대화되돌리기(쪽번호: str, 남은지문들: list) -> dict:
    """대화창을 앞 시점으로 되돌렸을 때, 여기 기록도 같이 잘라낸다.

    ChatGPT 에서 내 말 옆 연필을 눌러 고치면 그 뒤 대화가 통째로 사라진다.
    그런데 여기 기록은 그대로 남아 있어서, 이미 없어진 일을 한 것처럼 보인다.

    화면에 살아남은 답변들의 지문을 받아, 뒤에서부터 훑으며
    '지문이 있는데 살아남은 축에 없는' 첫 답변을 찾아 거기서부터 잘라낸다.
    지문이 없는 옛 기록은 판단할 수 없으므로 건드리지 않는다.
    """
    목록 = 대화읽기(쪽번호, 최대=0, 엄격=True)
    남은 = set(남은지문들 or [])
    if not 남은:
        return {"잘랐나": False, "남은건수": len(목록)}

    # 뒤에서부터 훑어 '화면에 없어진 답변' 만 걷어낸다.
    # 앞에서부터 훑으면 위험하다 — 긴 대화에서 위쪽 메시지가 화면에서
    # 치워졌을 뿐인데 되돌린 걸로 보고 뒤를 통째로 날려버린다.
    자를자리 = len(목록)
    for 번 in range(len(목록) - 1, -1, -1):
        항목 = 목록[번]
        if 항목.get("종류") != "gpt":
            continue
        도장 = 항목.get("지문")
        if not 도장:
            break              # 판단할 수 없는 옛 기록 — 여기서 멈춘다
        if 도장 in 남은:
            break              # 아직 화면에 있다 — 여기까지는 살린다
        자를자리 = 번           # 없어졌다 — 여기서부터 잘라낸다

    if 자를자리 >= len(목록):
        return {"잘랐나": False, "남은건수": len(목록)}

    남길것 = 목록[:자를자리]
    안전쓰기(_대화파일(쪽번호), json.dumps(남길것, ensure_ascii=False, indent=2))

    # 잘려 나가는 첫 답변의 되새김 = 그 앞 차례가 막 끝난 시점이다.
    # 목표와 기억도 거기로 되돌려야 그만둔 일을 계속 붙들지 않는다.
    되돌림 = {"되돌림": False}
    try:
        되돌림 = 되새김되돌리기(쪽번호, 목록[자를자리].get("지문", ""))
    except OSError:
        pass

    return {"잘랐나": True, "지운건수": len(목록) - len(남길것),
            "남은건수": len(남길것), **되돌림}


def 대화추가(쪽번호: str, 종류: str, 글: str, 나물: str = "", 지문: str = "") -> dict:
    """대화 한 줄을 남긴다. 종류: '나' | 'gpt'"""
    파일 = _대화파일(쪽번호)
    상태, 목록 = _대화읽어보기(쪽번호, 번수=_대화잠김기다림)
    if 목록 is None:
        if 상태 == "못읽음":
            raise 대화못읽음("대화 기록을 읽을 수 없어(잠김) 새 말을 쓰지 않았습니다. 기존 기록은 그대로입니다.")
        목록 = _대화백업읽기(쪽번호) or []         # 깨진 파일은 증거로 남겼다. 백업이 있으면 거기서 이어 간다
    else:
        _대화백업하기(쪽번호, 목록)

    # 같은 말이 이어서 또 들어오면 버린다.
    # 탭을 새로 고치면 확장의 '마지막으로 남긴 글' 기억이 지워져서
    # 화면에 떠 있던 답변을 다시 남긴다 — 그래서 같은 글이 여러 번 쌓였다.
    # 지문이 있으면 그것으로 거른다(가장 정확하다).
    # 지문이 없는 말은 글 자체로 보되, 짧은 말은 진짜 두 번 할 수 있으니 길 때만 본다.
    if 종류 in ("gpt", "나", "사용자"):
        for 앞항목 in 목록[-겹침살필개수:]:
            if 앞항목.get("종류") != 종류:
                continue
            if 지문 and 앞항목.get("지문") == 지문:
                return 앞항목
            if not 지문 and len(글 or "") >= 40 and 앞항목.get("글") == 글:
                return 앞항목

    항목 = {
        "종류": 종류,
        "글": 글,
        "나물": 나물,
        "지문": 지문,        # 되돌렸을 때 어디까지 지울지 알아보는 표
        "때": _지금(),
    }
    # 이 순간의 차례·기억을 지문과 함께 챙겨 둔다(되돌릴 때 쓴다)
    if 종류 == "gpt" and 지문:
        try:
            되새김남기기(쪽번호, 지문)
        except OSError:
            pass

    목록.append(항목)
    목록 = _대화줄이기(목록)
    안전쓰기(파일, json.dumps(목록, ensure_ascii=False, indent=2))
    if 종류 in ("gpt", "사용자"):
        말없는도구[쪽번호] = 0
    if 종류 == "gpt":
        단서 = 불확실말찾기(글)
        if 단서:
            불확실한말[쪽번호] = 단서
    elif 종류 == "도구":
        말없는도구[쪽번호] = 말없는도구.get(쪽번호, 0) + 1
    return 항목


def 대화비우기(쪽번호: str = "") -> dict:
    파일 = _대화파일(쪽번호)
    if 파일.exists():
        파일.unlink()
    return {"비움": True}


def _대화의방(설정: dict, 대화아이디: str) -> dict | None:
    """이 대화가 붙은 방. 꽉 차서 넘겨준 옛 대화(대화들)도 같은 방으로 본다."""
    return next((r for r in 설정["방들"]
                 if r.get("대화") == 대화아이디 or 대화아이디 in (r.get("대화들") or [])), None)


def 방대화이어붙이기(쪽번호: str, 새대화: str) -> dict:
    """꽉 찬 대화를 새 ChatGPT 대화로 넘겼다. 같은 방이 새 대화를 이어 갖는다.

    판에서 방은 하나로 보이고(기록·할 일·기억 그대로), 옛 대화는 '대화들' 에 남는다.
    """
    새대화 = (새대화 or "").strip()
    if not 새대화:
        raise ValueError("새 대화 번호가 없습니다.")
    설정 = 읽기()
    방 = next((r for r in 설정["방들"] if r["쪽번호"] == 쪽번호), None)
    if 방 is None:
        raise ValueError("그런 방이 없습니다.")
    if 방.get("대화") == 새대화:
        return 방
    # 새 대화가 다른 방에 이미 붙어 있으면(열어 보는 사이 생긴 빈 방) 그 방에서 떼어 낸다
    for 다른 in 설정["방들"]:
        if 다른 is not 방 and 다른.get("대화") == 새대화:
            다른["대화"] = None
    옛것 = [d for d in (방.get("대화들") or []) if d != 새대화]
    if 방.get("대화"):
        옛것.append(방["대화"])
    if not 방.get("기본이름"):
        방["기본이름"] = 방.get("이름") or ""     # 판에서는 이 이름 그대로, 대화만 '… N번'
    방["대화들"] = 옛것
    방["대화"] = 새대화
    방["마지막"] = _지금()
    설정["지금방"] = 방["쪽번호"]
    쓰기(설정)
    return 방


def 대화방찾기(대화아이디: str, 프로젝트: str = "", 프로젝트이름: str = "") -> dict | None:
    """이 대화에 붙은 방이 있으면 돌려준다. 없으면 None — 만들지 않는다.

    ChatGPT 에서 대화를 열어 보기만 해도 방이 생기던 것을 막는다.
    (중고 그래픽카드 물어본 대화까지 일할 곳 목록에 떴다)
    """
    대화아이디 = (대화아이디 or "").strip()
    if not 대화아이디:
        return None
    설정 = 읽기()
    방 = _대화의방(설정, 대화아이디)
    프로젝트 = 프로젝트번호다듬기(프로젝트)
    if 방 is not None and 프로젝트:
        앞 = json.dumps(설정, ensure_ascii=False, sort_keys=True)
        _방을묶음에(설정, 방, 프로젝트, 프로젝트이름)
        if json.dumps(설정, ensure_ascii=False, sort_keys=True) != 앞:
            쓰기(설정)
    return 방


def 대화방잡기(대화아이디: str, 이름: str = "", 프로젝트: str = "", 프로젝트이름: str = "") -> dict:
    """ChatGPT 대화 하나에 방 하나를 붙인다. 없으면 만든다.

    대화창마다 제 방을 가지므로, 창을 여러 개 띄워 서로 다른 프로젝트를
    동시에 할 수 있다. 예전처럼 한 탭만 '붙이는' 짓을 할 필요가 없다.
    """
    대화아이디 = (대화아이디 or "").strip()
    if not 대화아이디:
        raise ValueError("대화 번호가 없습니다.")

    설정 = 읽기()
    방 = _대화의방(설정, 대화아이디)

    # 아직 어느 대화에도 안 붙은 '지금 방' 이 있으면 그것을 이 대화에 붙인다.
    # 판에서 폴더를 먼저 고르면(대화 번호가 생기기 전) 주인 없는 방이 생긴다.
    # 여기서 새 방을 또 만들면 사람이 고른 폴더가 사라진 것처럼 보인다.
    if 방 is None:
        지금 = next((r for r in 설정["방들"]
                    if r.get("쪽번호") == 설정.get("지금방") and not r.get("대화")), None)
        if 지금 is not None:
            방 = 지금
            방["대화"] = 대화아이디
            방["마지막"] = _지금()
            if 이름 and not (방.get("이름") or "").strip():
                방["이름"] = 이름.strip()[:60]

    if 방 is None:
        방 = {
            "쪽번호": uuid.uuid4().hex[:8],
            "이름": (이름 or "").strip()[:60],
            "폴더": None,
            "밭": None,
            "대화": 대화아이디,
            "만든때": _지금(),
            "마지막": _지금(),
        }
        설정["방들"].append(방)
    else:
        방["마지막"] = _지금()
        if 이름 and not (방.get("이름") or "").strip():
            방["이름"] = 이름.strip()[:60]

    프로젝트 = 프로젝트번호다듬기(프로젝트)
    if 프로젝트:
        _방을묶음에(설정, 방, 프로젝트, 프로젝트이름)

    설정["지금방"] = 방["쪽번호"]        # 창이 하나뿐일 때를 위한 대비책
    쓰기(설정)
    (방뿌리 / 방["쪽번호"]).mkdir(parents=True, exist_ok=True)
    return 방


def 이름필요한가() -> bool:
    방 = 지금방()
    return bool(방) and not (방.get("이름") or "").strip()


# ── 되새김 : 그 시점의 차례·기억을 남겨 둔다 ──────────────────
# 대화를 되돌리면 대화만 되돌아가고 목표와 기억은 그대로였다.
# 그러면 그만둔 일을 에이전트가 계속 붙들고 늘어진다.
# 그래서 gpt 가 말할 때마다 그 순간의 차례·기억을 지문과 함께 남겨 두고,
# 되돌릴 때 그 시점으로 되돌린다. 지우지 않고 파일로 남긴다.

되새김최대 = 60
챙길것 = ("차례.json", "기억.md")


def _되새김칸(쪽번호: str = "") -> Path:
    칸 = 방자료칸(쪽번호) / "되새김"
    칸.mkdir(parents=True, exist_ok=True)
    return 칸


def _지문이름(지문: str) -> str:
    """지문을 파일 이름으로 쓸 수 있게 다듬는다."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", 지문 or "")[:40] or "빈것"


def 되새김남기기(쪽번호: str, 지문: str) -> None:
    """지금 차례·기억을 이 지문 이름으로 챙겨 둔다."""
    if not 지문:
        return
    칸 = _되새김칸(쪽번호) / _지문이름(지문)
    if 칸.exists():
        return                     # 같은 자리는 한 번만
    칸.mkdir(parents=True, exist_ok=True)

    자료칸 = 방자료칸(쪽번호)
    for 이름 in 챙길것:
        원본 = 자료칸 / 이름
        안전파일.바이트쓰기(칸 / 이름, 원본.read_bytes() if 원본.exists() else b"")

    # 너무 쌓이면 오래된 것부터 접는다(지우지 않고 헌것 칸으로 옮긴다)
    것들 = sorted(_되새김칸(쪽번호).iterdir(), key=lambda p: p.stat().st_mtime)
    if len(것들) > 되새김최대:
        헌것 = _되새김칸(쪽번호) / "_헌것"
        헌것.mkdir(exist_ok=True)
        for 낡은것 in 것들[:len(것들) - 되새김최대]:
            if 낡은것.name == "_헌것":
                continue
            try:
                낡은것.rename(헌것 / 낡은것.name)
            except OSError:
                pass


def 되새김되돌리기(쪽번호: str, 지문: str) -> dict:
    """그 지문 때의 차례·기억으로 되돌린다. 지금 것은 버리지 않고 챙겨 둔다."""
    칸 = _되새김칸(쪽번호) / _지문이름(지문)
    if not 지문 or not 칸.exists():
        return {"되돌림": False}

    자료칸 = 방자료칸(쪽번호)
    되돌린것 = []
    때 = datetime.now().strftime("%Y%m%d-%H%M%S")
    물린칸 = _되새김칸(쪽번호) / "_물린것" / 때
    물린칸.mkdir(parents=True, exist_ok=True)

    for 이름 in 챙길것:
        지금것 = 자료칸 / 이름
        챙긴것 = 칸 / 이름
        if not 챙긴것.exists():
            continue
        if 지금것.exists():
            안전파일.바이트쓰기(물린칸 / 이름, 지금것.read_bytes())   # 지우지 않는다
        안전파일.바이트쓰기(지금것, 챙긴것.read_bytes())
        되돌린것.append(이름)

    # 기억은 프로젝트 쪽에도 같이 두므로 그쪽도 맞춰 준다.
    # 안 맞추면 되돌린 뒤에도 프로젝트에는 옛 기억이 남는다.
    if "기억.md" in 되돌린것:
        try:
            import tools_memory
            프로젝트파일 = tools_memory._프로젝트기억파일()
            if 프로젝트파일 is not None:
                프로젝트파일.parent.mkdir(parents=True, exist_ok=True)
                안전파일.바이트쓰기(프로젝트파일, (자료칸 / "기억.md").read_bytes())
        except (OSError, ImportError):
            pass

    return {"되돌림": True, "되돌린것": 되돌린것,
            "물린것": str(물린칸)}


# ── 다른 자리 쓰기 허락 ────────────────────────────────────────
# 방을 바꾸면 허락은 전부 지워진다.

대기요청 = {}


def 쓸수있는자리들() -> list:
    자리들 = []
    밭 = 지금밭()
    if 밭:
        자리들.append(밭)
    for 허락 in 읽기()["허락"]:
        자리들.append(_정규화(허락))
    return 자리들


def 쓸수있나(대상: Path) -> bool:
    자리들 = 쓸수있는자리들()
    if not 자리들:
        return False
    for 자리 in 자리들:
        try:
            대상.relative_to(자리)
            return True
        except ValueError:
            continue
    return False


def 요청쌓기(대상: Path) -> str:
    폴더 = str(대상.parent if 대상.suffix else 대상)
    if 폴더 not in 대기요청:
        대기요청[폴더] = {"밭": 폴더,
                        "때": datetime.now().strftime("%H:%M:%S"),
                        "몇번": 0}
    대기요청[폴더]["몇번"] += 1
    return 폴더


def 허락하기(밭: str) -> dict:
    대상 = _정규화(밭)
    뿌리 = _정규화(Path(sandbox.설정["루트"]))
    try:
        대상.relative_to(뿌리)
    except ValueError:
        raise ValueError(f"정해진 범위 밖입니다: {대상}")
    설정 = 읽기()
    if str(대상) not in 설정["허락"]:
        설정["허락"].append(str(대상))
    쓰기(설정)
    대기요청.pop(str(대상), None)
    return {"밭": str(대상), "허락": 설정["허락"]}


def 거절하기(밭: str) -> dict:
    대상 = str(_정규화(밭))
    대기요청.pop(대상, None)
    return {"밭": 대상}


# ── 화면에 뿌릴 모양 ───────────────────────────────────────────

def 나무(지금방번호: str | None = None) -> dict:
    """폴더 → 그 밑 방들. 폴더 없는 방은 따로 모은다."""
    설정 = 읽기()
    지금 = 지금방번호 or 설정["지금방"]

    가지들 = []
    잃은폴더 = set()
    for 폴더 in 설정["폴더들"]:
        # 디스크에서 사라진 폴더는 아예 보여주지 않는다.
        # 눌러도 아무것도 못 하는 자리를 목록에 두면 헷갈리기만 한다.
        # 적어둔 것은 지우지 않는다 — 폴더가 돌아오면 다시 나타난다.
        # 프로젝트 묶음은 폴더를 아직 안 골라도 보여 준다(판에서 고르게).
        if 폴더.get("밭") and not Path(폴더["밭"]).exists() and not 폴더.get("프로젝트"):
            잃은폴더.add(폴더["쪽번호"])
            continue

        속한방 = [_방보기(r, 지금) for r in 설정["방들"]
                 if r.get("폴더") == 폴더["쪽번호"]]
        속한방.sort(key=lambda r: r["마지막"], reverse=True)
        가지들.append({
            "쪽번호": 폴더["쪽번호"],
            "이름": 폴더["이름"],
            "밭": 폴더.get("밭"),
            "있음": bool(폴더.get("밭")) and Path(폴더["밭"]).exists(),
            "프로젝트": 폴더.get("프로젝트") or "",
            "방들": 속한방,
        })

    # 사라진 폴더에 딸려 있던 방은 잃어버리지 않게 '폴더 없음' 으로 모은다
    떠도는방 = [_방보기(r, 지금) for r in 설정["방들"]
              if not r.get("폴더") or r.get("폴더") in 잃은폴더]
    if 떠도는방:
        떠도는방.sort(key=lambda r: r["마지막"], reverse=True)
        가지들.append({
            "쪽번호": "",
            "이름": 없는폴더이름,
            "밭": None,
            "있음": True,
            "방들": 떠도는방,
        })

    방 = 지금방()
    return {
        "폴더들": 가지들,
        "지금방": 지금,
        "지금방이름": (방 or {}).get("이름"),
        "지금밭": str(지금밭()) if 지금밭() else None,
        "이름필요": 이름필요한가(),
        "허락": 설정["허락"],
        "대기": list(대기요청.values()),
        "대화": 판대화읽기(지금) if 지금 else [],
    }


def _방보기(방: dict, 지금: str) -> dict:
    return {
        "쪽번호": 방["쪽번호"],
        "이름": 방.get("이름") or "(이름 짓는 중…)",
        "밭": 방.get("밭"),
        "마지막": 방.get("마지막", ""),
        "지금": 방["쪽번호"] == 지금,
        # 판에서 방을 누르면 이 대화를 ChatGPT 탭에 연다(넘겼으면 가장 최근 대화)
        "대화": 방.get("대화") or "",
        "대화들": list(방.get("대화들") or []),
        "대화차례": len(방.get("대화들") or []) + 1,          # 판에 '… N번' 으로 보인다
        "부모": 방.get("부모") or "",                          # 일꾼 방이면 대장 방
        "역할": 방.get("역할") or "",
    }
