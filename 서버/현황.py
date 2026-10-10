# -*- coding: utf-8 -*-
"""현황판 — GPT 가 '무엇을 보여 줄지' 정하고, 서버가 직접 재서 판에 띄운다.

GPT 가 "파인튜닝 40% 진행 중이에요" 라고 말하는 것이 아니다.
GPT 는 당근으로 '이 로그의 진행률 · 이 폴더의 파일 · GPU' 처럼 볼 것을 걸어 두기만 하고,
숫자는 서버가 디스크·프로세스에서 읽는다. GPT 의 말이 틀려도 판의 숫자는 맞다.

  틀(항목 종류)        무엇을 재나
  ─────────────────────────────────────────────────────────────
  일     번호          뒤뜰 일 하나 — 상태·경과·남은 시간·진행률·숫자·끝 줄
  진행   밭 [/ 낱말 / 전체]   로그에서 '3/20' · '45%' · 'step 120' 을 읽어 막대로
  숫자   밭 / 낱말     로그의 'loss=0.31' 같은 값의 변해 가는 모양
  기록   밭 [/ 줄]     파일의 끝 몇 줄
  파일   밭            파일 하나 또는 폴더 — 크기·시각·늘고 있나 (체크포인트)
  값     밭 / 키       JSON 파일 속 값 하나
  기계   GPU|메모리|디스크

뒤뜰 일은 GPT 가 아무것도 안 해도 방마다 저절로 한 장씩 뜬다(자동 판).
읽기만 한다. 파일을 바꾸지 않는다. 멈추기만 예외다(사용자가 판에서 누를 때).
"""

import json
import math
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import rooms
import sandbox
import tools_bg
import 안전파일

판파일이름 = "현황판.json"

판최대 = 6                # 한 방에 GPT 가 걸어 둘 수 있는 판
항목최대 = 12             # 판 하나의 항목
자동판최대 = 8            # 한 번에 보이는 자동 판
방금끝남초 = 6 * 3600     # 끝난 일을 이만큼은 판에 둔다
읽는바이트 = 256 * 1024   # 로그는 끝에서 이만큼만 읽는다(870KB 짜리 기록에서도 가볍게)
점최대 = 40               # 그래프 한 줄의 점

항목종류 = ("일", "진행", "숫자", "기록", "파일", "값", "기계")
기계종류 = ("GPU", "메모리", "디스크")


def _지금초() -> float:
    return time.time()


# ── 글에서 항목 읽기 ───────────────────────────────────────────

def 항목읽기(글: str) -> list:
    """당근의 '항목' 글을 항목 목록으로 바꾼다. 한 줄에 하나.

    일 22feb94d
    진행 logs▸학습.log / 낱말 update / 전체 40
    숫자 logs▸학습.log / 낱말 loss
    파일 checkpoints
    기계 GPU
    """
    항목들 = []
    for 원줄 in str(글 or "").splitlines():
        줄 = 원줄.strip()
        if not 줄:
            continue
        조각 = [p.strip() for p in 줄.split(" / ")]
        머리 = 조각[0].split(None, 1)
        종류 = 머리[0]
        값 = 머리[1].strip() if len(머리) > 1 else ""
        if 종류 not in 항목종류:
            raise ValueError(f"모르는 항목 종류입니다: '{종류}' (일·진행·숫자·기록·파일·값·기계 중 하나) ← {줄[:60]}")
        선택 = {}
        for 옵션 in 조각[1:]:
            키값 = 옵션.split(None, 1)
            if len(키값) == 2:
                선택[키값[0]] = 키값[1].strip()
        항목 = {"종류": 종류, "값": 값}
        if 선택.get("이름"):
            항목["이름"] = 선택["이름"][:40]
        if 종류 == "일":
            if not re.fullmatch(r"[0-9a-f]{4,16}", 값):
                raise ValueError(f"'일' 은 두릅이 준 번호(영문·숫자)가 필요합니다: {줄[:60]}")
        elif 종류 == "기계":
            if 값.upper() not in 기계종류 and 값 not in 기계종류:
                raise ValueError(f"'기계' 는 GPU·메모리·디스크 중 하나입니다: {줄[:60]}")
            항목["값"] = 값.upper() if 값.upper() == "GPU" else 값
        else:
            if not 값:
                raise ValueError(f"'{종류}' 에는 밭(파일·폴더)이 필요합니다: {줄[:60]}")
            if 종류 in ("숫자",) and not 선택.get("낱말"):
                raise ValueError(f"'숫자' 에는 / 낱말 이 필요합니다. 예) 숫자 logs▸학습.log / 낱말 loss")
            if 종류 == "값" and not 선택.get("키"):
                raise ValueError(f"'값' 에는 / 키 가 필요합니다. 예) 값 결과.json / 키 승률")
        for 키 in ("낱말", "키"):
            if 선택.get(키):
                항목[키] = 선택[키][:60]
        for 키, 한도 in (("전체", 10 ** 9), ("줄", 40)):
            if 선택.get(키):
                try:
                    항목[키] = max(1, min(int(float(선택[키])), 한도))
                except ValueError:
                    raise ValueError(f"'{키}' 는 숫자여야 합니다: {줄[:60]}")
        항목들.append(항목)
    if not 항목들:
        raise ValueError("항목이 비었습니다. 한 줄에 하나씩 적으세요. 예) 일 22feb94d")
    if len(항목들) > 항목최대:
        raise ValueError(f"항목이 너무 많습니다(최대 {항목최대}).")
    return 항목들


# ── 읽기 도우미 ────────────────────────────────────────────────

def _길(밭: str) -> Path:
    """샌드박스 읽기 규칙을 그대로 탄다(비밀 파일·범위 밖은 거부)."""
    return sandbox.경로검증(밭)


def _풀기(바이트: bytes) -> str:
    for 인코딩 in ("utf-8", "cp949"):
        try:
            return 바이트.decode(인코딩)
        except UnicodeDecodeError:
            continue
    return 바이트.decode("utf-8", errors="replace")


def _끝줄들(경로: Path, 줄수: int = 400) -> list:
    """파일 끝 부분의 줄들. 큰 파일도 끝에서 읽는 만큼만 읽는다."""
    try:
        크기 = 경로.stat().st_size
        with 경로.open("rb") as f:
            처음부터 = 크기 <= 읽는바이트
            if not 처음부터:
                f.seek(크기 - 읽는바이트)
            덩어리 = f.read()
    except OSError:
        return []
    줄들 = _풀기(덩어리).splitlines()
    if not 처음부터 and 줄들:
        줄들 = 줄들[1:]                 # 잘려서 시작한 첫 줄은 버린다
    # tqdm 같은 진행 막대는 \r 로 한 줄 안에서 덮어쓴다 — 마지막 조각만 본다
    줄들 = [줄.split("\r")[-1] if "\r" in 줄 else 줄 for 줄 in 줄들]
    return 줄들[-줄수:]


_몇나눗붙임 = re.compile(r"(?<![\w./:\\-])(\d{1,9})/(\d{1,9})(?![\w./:\\-])")
_몇나눗 = re.compile(r"(?<![\w./:\\-])(\d{1,9})\s*/\s*(\d{1,9})(?![\w./:\\-])")
_퍼센트 = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d+)?)\s*%")
_수치 = r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"
_이름수치 = re.compile(r"(?<![\w가-힣.])([A-Za-z_가-힣][\w가-힣.\-]{0,23})\s*[=:]\s*(" + _수치 + r")(?![\w.])")


def 진행찾기(줄들: list, 낱말: str = "", 전체: int = 0):
    """로그 끝에서 '지금 몇 번째/전체 몇' 을 찾는다. 못 찾으면 None.

    낱말을 주면 그 낱말 바로 뒤의 숫자만 본다(step 120 · update=5/40).
    안 주면 가장 최근 줄의 'a/b' 를, 없으면 가장 최근 '45%' 를 쓴다.
    """
    if 낱말:
        식 = re.compile(re.escape(낱말) + r"\W{0,3}(\d{1,9})(?:\s*/\s*(\d{1,9}))?", re.I)
        for 줄 in reversed(줄들):
            찾음 = list(식.finditer(줄))
            if not 찾음:
                continue
            m = 찾음[-1]
            지금 = int(m.group(1))
            분모 = int(m.group(2)) if m.group(2) else int(전체 or 0)
            return _진행모양(지금, 분모, 줄, 낱말)
        return None
    # 붙여 쓴 3/20 (진행 표시) 을 먼저 찾고, 없을 때만 '5 / 10 files' 같은 띄어 쓴 꼴을 본다
    for 식 in (_몇나눗붙임, _몇나눗):
        for 줄 in reversed(줄들):
            맞음 = [m for m in 식.finditer(줄)
                   if int(m.group(2)) >= 2 and int(m.group(1)) <= int(m.group(2))]
            if 맞음:
                m = 맞음[-1]
                앞 = 줄[:m.start()]
                이름 = re.search(r"([A-Za-z_가-힣]+)\W{0,3}$", 앞)
                return _진행모양(int(m.group(1)), int(m.group(2)), 줄, 이름.group(1) if 이름 else "")
    for 줄 in reversed(줄들):
        맞음 = list(_퍼센트.finditer(줄))
        if 맞음:
            값 = float(맞음[-1].group(1))
            if 0 <= 값 <= 100:
                return {"지금": None, "전체": None, "퍼센트": round(값, 1), "줄": 줄.strip()[:120], "이름": ""}
    return None


def _진행모양(지금: int, 전체: int, 줄: str, 이름: str) -> dict:
    퍼센트 = round(min(지금 * 100.0 / 전체, 100.0), 1) if 전체 > 0 else None
    return {"지금": 지금, "전체": 전체 or None, "퍼센트": 퍼센트,
            "줄": 줄.strip()[:120], "이름": 이름}


_로그남은 = re.compile(r"(?<![\w가-힣])eta[_ ]?(?:sec(?:onds?)?|s)\s*[=:]\s*(\d+(?:\.\d+)?)", re.I)


def 로그남은초(줄들: list):
    """프로그램이 직접 찍어 준 남은 시간(eta_seconds=46.1)을 읽는다. 없으면 None.

    내가 경과·퍼센트로 어림하는 것보다 프로그램이 아는 값이 정확하다.
    """
    for 줄 in reversed(줄들):
        찾음 = list(_로그남은.finditer(줄))
        if 찾음:
            return int(float(찾음[-1].group(1)))
    return None


def _점줄이기(값들: list, 최대: int = 점최대) -> list:
    if len(값들) <= 최대:
        return 값들
    간격 = len(값들) / 최대
    return [값들[min(int(i * 간격), len(값들) - 1)] for i in range(최대 - 1)] + [값들[-1]]


def 숫자찾기(줄들: list, 낱말: str):
    """로그에서 '낱말=숫자' 를 모아 변해 가는 모양을 돌려준다. 없으면 None."""
    식 = re.compile(r"(?<![\w가-힣.])" + re.escape(낱말) + r"\s*[=:]?\s*(" + _수치 + r")(?![\w.])", re.I)
    값들 = []
    for 줄 in 줄들:
        for m in 식.finditer(줄):
            try:
                값 = float(m.group(1))
            except ValueError:
                continue
            if math.isfinite(값):
                값들.append(값)
    return _숫자모양(낱말, 값들)


def _숫자모양(이름: str, 값들: list):
    if not 값들:
        return None
    최신 = 값들[-1]
    앞 = 값들[:max(1, len(값들) // 2)]
    뒤 = 값들[len(값들) // 2:] or 값들
    평앞, 평뒤 = sum(앞) / len(앞), sum(뒤) / len(뒤)
    틈 = max(abs(평앞), abs(평뒤), 1e-9)
    추이 = "비슷" if abs(평뒤 - 평앞) / 틈 < 0.03 else ("오름" if 평뒤 > 평앞 else "내림")
    return {"이름": 이름, "최신": 최신, "처음": 값들[0], "개수": len(값들),
            "추이": 추이, "점들": _점줄이기(값들)}


# 막대·남은 시간으로 이미 보이는 값(progress_percent · eta_seconds · elapsed_seconds)은 숫자 목록에서 뺀다
_메타이름 = re.compile(r"(percent|progress|elapsed|second|(^|[_\W])eta($|[_\W])|^time|_time)", re.I)
# 사람이 제일 궁금해하는 값 — 목록이 길면 이런 이름이 앞에 온다
_눈여겨볼이름 = ("return", "reward", "success", "win", "acc", "loss", "score", "f1", "ppl", "perplexity", "error", "mse")
숫자저절로최대 = 4


def 숫자저절로(줄들: list, 빼기: str = "") -> list:
    """낱말을 안 줘도 로그에 자주 나오는 'loss=0.3' 꼴을 골라 준다(최대 4개)."""
    모음 = {}
    순서 = {}
    for 번, 줄 in enumerate(줄들):
        for m in _이름수치.finditer(줄):
            이름 = m.group(1)
            if 이름.lower() == (빼기 or "").lower() or _메타이름.search(이름):
                continue
            try:
                값 = float(m.group(2))
            except ValueError:
                continue
            if not math.isfinite(값):
                continue
            모음.setdefault(이름, []).append(값)
            순서[이름] = 번
    후보 = []
    for 이름, 값들 in 모음.items():
        if len(값들) < 3:
            continue
        # 1, 2, 3… 처럼 세는 숫자(update=5)는 변해 가는 값이 아니라 번호다
        if all(float(v).is_integer() for v in 값들) and all(b - a == 1 for a, b in zip(값들, 값들[1:])):
            continue
        # 늘 같은 값(seed=42 · device=cuda 따위)도 보여 줄 게 없다
        if len(set(값들)) == 1:
            continue
        눈여겨 = next((i for i, 키 in enumerate(_눈여겨볼이름) if 키 in 이름.lower()), len(_눈여겨볼이름))
        후보.append((-눈여겨, len(값들), 순서[이름], 이름, 값들))
    후보.sort(reverse=True)
    return [_숫자모양(이름, 값들) for _, _, _, 이름, 값들 in 후보[:숫자저절로최대]]


# ── 항목 하나 재기 ─────────────────────────────────────────────

def _시각글(초: float) -> str:
    return datetime.fromtimestamp(초).strftime("%m-%d %H:%M:%S")


def _몇초전(초: float) -> int:
    return max(0, int(_지금초() - 초))


_앞측정: dict = {}          # 경로 → (크기, 잰 때). 파일이 커지는 중인지 보려는 것


def _파일항목(밭: str) -> dict:
    경로 = _길(밭) if "*" not in 밭 else None
    if 경로 is None:
        위 = _길(str(Path(밭).parent) if str(Path(밭).parent) not in ("", ".") else ".")
        찾은 = sorted(위.glob(Path(밭).name), key=lambda p: p.stat().st_mtime, reverse=True)
        대상 = [p for p in 찾은 if p.is_file()]
        열쇠 = str(위 / Path(밭).name)
    else:
        if not 경로.exists():
            return {"있음": False, "탈": "아직 없습니다"}
        if 경로.is_file():
            대상 = [경로]
        else:
            대상 = []
            for 뿌리, 폴더들, 파일들 in os.walk(경로):
                폴더들[:] = [d for d in 폴더들 if not sandbox.제외폴더인가(d)][:50]
                for 이름 in 파일들[:500]:
                    대상.append(Path(뿌리) / 이름)
                if len(대상) > 3000:
                    break
            대상.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        열쇠 = str(경로)
    if not 대상:
        return {"있음": False, "탈": "아직 없습니다"}
    최근 = 대상[0]
    try:
        상태 = 최근.stat()
    except OSError:
        return {"있음": False, "탈": "읽지 못했습니다"}
    합계 = 0
    for p in 대상[:3000]:
        try:
            합계 += p.stat().st_size
        except OSError:
            pass
    앞 = _앞측정.get(열쇠)
    지금크기 = 합계
    늘었나 = bool(앞 and 지금크기 != 앞[0])
    if not 앞 or 지금크기 != 앞[0]:
        _앞측정[열쇠] = (지금크기, _지금초())
    return {
        "있음": True, "개수": len(대상), "합계크기": 합계,
        "최근": {"이름": 최근.name, "크기": 상태.st_size, "때": _시각글(상태.st_mtime),
                "몇초전": _몇초전(상태.st_mtime)},
        "커지는중": 늘었나 or _몇초전(상태.st_mtime) < 10,
    }


def _값항목(밭: str, 키: str) -> dict:
    경로 = _길(밭)
    if not 경로.is_file():
        return {"있음": False, "탈": "아직 없습니다"}
    if 경로.stat().st_size > 2 * 1024 * 1024:
        return {"있음": False, "탈": "너무 큽니다(2MB 넘음)"}
    try:
        자료 = json.loads(_풀기(경로.read_bytes()))
    except ValueError:
        return {"있음": False, "탈": "JSON 이 아닙니다"}
    값 = 자료
    for 조각 in str(키).split("."):
        if isinstance(값, list) and 조각.lstrip("-").isdigit():
            번 = int(조각)
            값 = 값[번] if -len(값) <= 번 < len(값) else None
        elif isinstance(값, dict) and 조각 in 값:
            값 = 값[조각]
        else:
            return {"있음": False, "탈": f"'{키}' 를 못 찾았습니다"}
    글 = json.dumps(값, ensure_ascii=False) if not isinstance(값, str) else 값
    return {"있음": True, "값": 글[:200], "때": _시각글(경로.stat().st_mtime)}


_기계캐시: dict = {}


def _기계항목(무엇: str) -> dict:
    캐시 = _기계캐시.get(무엇)
    if 캐시 and _지금초() - 캐시[0] < 2:
        return 캐시[1]
    if 무엇 == "GPU":
        결과 = _GPU()
    elif 무엇 == "메모리":
        결과 = _메모리()
    else:
        결과 = _디스크()
    _기계캐시[무엇] = (_지금초(), 결과)
    return 결과


def _GPU() -> dict:
    프로그램 = shutil.which("nvidia-smi")
    if not 프로그램:
        return {"있음": False, "탈": "nvidia-smi 가 없습니다(NVIDIA GPU 아님)"}
    try:
        r = subprocess.run(
            [프로그램, "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4, encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        return {"있음": False, "탈": f"GPU 를 못 읽었습니다: {e}"}
    줄 = (r.stdout or "").strip().splitlines()
    if r.returncode != 0 or not 줄:
        return {"있음": False, "탈": "GPU 를 못 읽었습니다"}
    칸 = [c.strip() for c in 줄[0].split(",")]
    try:
        return {"있음": True, "이름": 칸[0], "사용률": int(float(칸[1])),
                "메모리쓴": int(float(칸[2])), "메모리전체": int(float(칸[3])),
                "온도": int(float(칸[4])) if len(칸) > 4 else None}
    except (ValueError, IndexError):
        return {"있음": False, "탈": "GPU 값을 읽지 못했습니다"}


def _메모리() -> dict:
    try:
        if os.name == "nt":
            import ctypes

            class _상태(ctypes.Structure):
                _fields_ = [("길이", ctypes.c_ulong), ("쓰는비율", ctypes.c_ulong),
                            ("전체", ctypes.c_ulonglong), ("남은", ctypes.c_ulonglong),
                            ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                            ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong),
                            ("e", ctypes.c_ulonglong)]
            s = _상태()
            s.길이 = ctypes.sizeof(s)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
            전체, 남은 = s.전체, s.남은
        else:
            정보 = {}
            for 줄 in Path("/proc/meminfo").read_text().splitlines():
                키, _, 나머지 = 줄.partition(":")
                정보[키] = int(나머지.split()[0]) * 1024
            전체, 남은 = 정보["MemTotal"], 정보.get("MemAvailable", 정보["MemFree"])
    except Exception as e:
        return {"있음": False, "탈": f"메모리를 못 읽었습니다: {e}"}
    쓴 = 전체 - 남은
    return {"있음": True, "사용률": int(쓴 * 100 / 전체) if 전체 else 0,
            "쓴MB": int(쓴 / 1048576), "전체MB": int(전체 / 1048576)}


def _디스크() -> dict:
    try:
        기준 = sandbox.기준자리()
        r = shutil.disk_usage(기준.anchor or str(기준))
    except OSError as e:
        return {"있음": False, "탈": f"디스크를 못 읽었습니다: {e}"}
    return {"있음": True, "자리": (sandbox.기준자리().anchor or ""), "여유GB": round(r.free / 1073741824, 1),
            "전체GB": round(r.total / 1073741824, 1),
            "사용률": int((r.total - r.free) * 100 / r.total) if r.total else 0}


def _경과(시작글: str, 끝초: float = 0) -> int:
    try:
        시작 = datetime.strptime(시작글, "%Y-%m-%d %H:%M:%S").timestamp()
    except (ValueError, TypeError):
        return 0
    return max(0, int((끝초 or _지금초()) - 시작))


def _끝난초(칸: Path) -> float:
    try:
        return (칸 / "끝번호.txt").stat().st_mtime
    except OSError:
        return 0


def _끝난지(칸: Path, 상태: str):
    """끝난 지(끊긴 지) 몇 초. 끝번호 파일이 있으면 그 시각, 끊김이면 기록이 마지막으로 바뀐 시각."""
    초 = _끝난초(칸)
    if not 초 and 상태 == "끊김":
        try:
            초 = (칸 / "기록.txt").stat().st_mtime
        except OSError:
            초 = 0
    return max(0, int(_지금초() - 초)) if 초 else None


def 일항목(번호: str, 이름: str = "") -> dict:
    """뒤뜰 일 하나를 재서 판 항목으로. 상태·경과·진행·숫자·끝 줄."""
    칸 = tools_bg._칸(번호)
    요약 = tools_bg._요약(번호)
    if not 요약:
        return {"종류": "일", "값": 번호, "이름": 이름 or 번호, "있음": False, "탈": "그런 일이 없습니다"}
    상태 = 요약["상태"]
    끝초 = _끝난초(칸) if 상태 != "달리는중" else 0
    경과 = _경과(요약.get("시작", ""), 끝초)
    줄들 = _끝줄들(칸 / "기록.txt")
    진행 = 진행찾기(줄들)
    남은, 남은출처 = None, ""
    if 상태 == "달리는중":
        남은 = 로그남은초(줄들)
        if 남은 is not None:
            남은출처 = "프로그램"
        elif 진행 and 진행.get("퍼센트") and 경과 >= 20 and 진행["퍼센트"] >= 1:
            남은 = int(경과 * (100 - 진행["퍼센트"]) / 진행["퍼센트"])
            남은출처 = "추정"
    if 상태 == "끝남" and 요약.get("끝번호") == 0 and 진행 and 진행.get("퍼센트") is not None:
        진행 = {**진행, "퍼센트": 100.0} if 진행["퍼센트"] >= 90 else 진행
    파일 = 칸 / "기록.txt"
    return {
        "종류": "일", "값": 번호, "이름": 이름 or 요약.get("이름") or 번호,
        "있음": True, "상태": 상태, "끝번호": 요약.get("끝번호"),
        "불": (요약.get("불") or "")[:120], "시작": 요약.get("시작", ""),
        "경과초": 경과, "남은초": 남은, "남은출처": 남은출처, "진행": 진행,
        # 끝났거나 끊긴 지 몇 초 — 판이 '방금 끝났다' 알림을 한 번만 울리려고 쓴다
        "끝난지초": None if 상태 == "달리는중" else _끝난지(칸, 상태),
        "숫자들": 숫자저절로(줄들, (진행 or {}).get("이름", "")),
        "끝줄들": [줄.strip()[:160] for 줄 in 줄들[-3:] if 줄.strip()],
        "기록크기": 파일.stat().st_size if 파일.exists() else 0,
        "조용한초": _몇초전(파일.stat().st_mtime) if 파일.exists() else None,
    }


def 항목재기(항목: dict) -> dict:
    """항목 하나를 재서 결과를 돌려준다. 못 읽으면 탈을 달아 돌려준다(전체를 막지 않는다)."""
    종류, 값 = 항목["종류"], 항목.get("값", "")
    이름 = 항목.get("이름", "")
    try:
        if 종류 == "일":
            return 일항목(값, 이름)
        if 종류 == "기계":
            return {"종류": 종류, "값": 값, "이름": 이름 or 값, **_기계항목(값)}
        if 종류 == "파일":
            return {"종류": 종류, "값": 값, "이름": 이름 or 값, **_파일항목(값)}
        if 종류 == "값":
            return {"종류": 종류, "값": 값, "이름": 이름 or 항목.get("키", 값), **_값항목(값, 항목["키"])}
        경로 = _길(값)
        if not 경로.is_file():
            return {"종류": 종류, "값": 값, "이름": 이름 or 값, "있음": False, "탈": "아직 없습니다"}
        줄들 = _끝줄들(경로)
        if 종류 == "진행":
            진행 = 진행찾기(줄들, 항목.get("낱말", ""), 항목.get("전체", 0))
            return {"종류": 종류, "값": 값, "이름": 이름 or 항목.get("낱말") or 값, "있음": True,
                    "진행": 진행, "조용한초": _몇초전(경로.stat().st_mtime)}
        if 종류 == "숫자":
            return {"종류": 종류, "값": 값, "이름": 이름 or 항목["낱말"], "있음": True,
                    "숫자": 숫자찾기(줄들, 항목["낱말"]), "조용한초": _몇초전(경로.stat().st_mtime)}
        if 종류 == "기록":
            n = int(항목.get("줄", 6))
            return {"종류": 종류, "값": 값, "이름": 이름 or 값, "있음": True,
                    "줄들": [줄.rstrip()[:200] for 줄 in 줄들[-n:]],
                    "조용한초": _몇초전(경로.stat().st_mtime)}
    except sandbox.보안오류 as e:
        return {"종류": 종류, "값": 값, "이름": 이름 or 값, "있음": False, "탈": str(e)[:120]}
    except Exception as e:      # 한 항목이 터져도 판 전체는 그대로
        return {"종류": 종류, "값": 값, "이름": 이름 or 값, "있음": False, "탈": f"못 읽었습니다: {e}"[:120]}
    return {"종류": 종류, "값": 값, "있음": False, "탈": "모르는 종류"}


# ── 판 저장 ────────────────────────────────────────────────────

def _판파일(방: str) -> Path:
    return rooms.방자료칸(방) / 판파일이름


def _판읽기(방: str) -> dict:
    자료 = 안전파일.json읽기(_판파일(방), {}, dict)
    자료.setdefault("판들", [])
    자료.setdefault("숨김", [])
    return 자료


def _판쓰기(방: str, 자료: dict) -> None:
    안전파일.json쓰기(_판파일(방), 자료)


def 판걸기(방: str, 이름: str, 항목글: str) -> dict:
    이름 = (이름 or "").strip()[:40]
    if not 이름:
        raise ValueError("판 이름이 필요합니다. 예) 이름 파인튜닝")
    항목들 = 항목읽기(항목글)
    자료 = _판읽기(방)
    새것 = {"번호": "p" + str(int(_지금초() * 1000))[-8:], "이름": 이름, "항목들": 항목들,
           "만든때": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    같은 = next((p for p in 자료["판들"] if p["이름"] == 이름), None)
    if 같은:
        새것["번호"] = 같은["번호"]
        자료["판들"] = [새것 if p["이름"] == 이름 else p for p in 자료["판들"]]
        바꿈 = True
    else:
        if len(자료["판들"]) >= 판최대:
            raise ValueError(f"판이 너무 많습니다(최대 {판최대}). 안 쓰는 것을 당근 짓 치우기 로 치우세요.")
        자료["판들"].append(새것)
        바꿈 = False
    _판쓰기(방, 자료)
    return {"이름": 이름, "번호": 새것["번호"], "항목수": len(항목들), "바꿈": 바꿈}


def 판치우기(방: str, 번호또는이름: str) -> dict:
    자료 = _판읽기(방)
    열쇠 = (번호또는이름 or "").strip()
    남음 = [p for p in 자료["판들"] if p["번호"] != 열쇠 and p["이름"] != 열쇠]
    if len(남음) == len(자료["판들"]):
        raise ValueError(f"그런 판이 없습니다: {열쇠}")
    자료["판들"] = 남음
    _판쓰기(방, 자료)
    return {"치움": 열쇠}


def 판숨기기(방: str, 번호: str) -> dict:
    """자동 판을 판에서 치운다(일 자체는 그대로 둔다)."""
    자료 = _판읽기(방)
    if 번호 not in 자료["숨김"]:
        자료["숨김"].append(번호)
        자료["숨김"] = 자료["숨김"][-200:]
        _판쓰기(방, 자료)
    return {"숨김": 번호}


def 일멈추기(방: str, 번호: str) -> dict:
    """사용자가 판에서 누른 멈춤. 이 방의 일만 멈춘다."""
    칸 = tools_bg._칸(번호)
    일 = tools_bg._일읽기(칸)
    if 일 is None:
        raise ValueError("그런 일이 없습니다.")
    if (일.get("방") or "") != 방:
        raise ValueError("이 방의 일이 아닙니다.")
    return tools_bg._그만두기(번호, 칸, 일)


# ── 판 재기 ────────────────────────────────────────────────────

def _뒤뜰일들(방: str = "") -> list:
    """(일.json, 칸) 목록. 방을 주면 그 방 것만. 옛것(끝난 지 오래)은 거른다."""
    결과 = []
    if not tools_bg.뒤뜰.exists():
        return 결과
    지금 = _지금초()
    for 칸 in tools_bg.뒤뜰.iterdir():
        if not 칸.is_dir():
            continue
        일 = tools_bg._일읽기(칸)
        if not 일:
            continue
        if 방 and (일.get("방") or "") != 방:
            continue
        결과.append((일, 칸))
    return 결과


def _살아있거나방금끝남(일: dict, 칸: Path) -> bool:
    """판에 둘 일인가. 달리는 중이거나, 끝난(끊긴) 지 얼마 안 된 것."""
    if tools_bg._끝번호(칸) is None:
        if tools_bg._상태(칸, 일) == "달리는중":
            return True
        # 끝번호도 없는데 프로세스도 없다(끊김). 기록이 마지막으로 바뀐 지 오래면 옛일이다.
        try:
            기준 = (칸 / "기록.txt").stat().st_mtime
        except OSError:
            기준 = 0
        if not 기준:
            try:
                기준 = datetime.strptime(일.get("시작", ""), "%Y-%m-%d %H:%M:%S").timestamp()
            except ValueError:
                return False
        return _지금초() - 기준 < 방금끝남초
    끝초 = _끝난초(칸)
    return bool(끝초) and _지금초() - 끝초 < 방금끝남초


def _판상태(항목들: list) -> str:
    일들 = [x for x in 항목들 if x.get("종류") == "일" and x.get("있음")]
    if not 일들:
        return "보는중"
    if any(x["상태"] == "달리는중" for x in 일들):
        return "달리는중"
    if any(x["상태"] == "끊김" or (x.get("끝번호") not in (0, None)) for x in 일들):
        return "실패"
    return "끝남"


def 측정(방: str) -> dict:
    """이 방의 현황판 전부 — GPT 가 건 판 + 뒤뜰 일마다 저절로 뜨는 판."""
    자료 = _판읽기(방)
    판들 = []
    덮인일 = set()
    for 판 in 자료["판들"]:
        항목들 = [항목재기(x) for x in 판["항목들"]]
        for x in 판["항목들"]:
            if x["종류"] == "일":
                덮인일.add(x["값"])
        판들.append({"번호": 판["번호"], "이름": 판["이름"], "자동": False,
                    "항목들": 항목들, "상태": _판상태(항목들), "만든때": 판.get("만든때", "")})

    자동 = []
    for 일, 칸 in _뒤뜰일들(방):
        번호 = 일.get("번호") or 칸.name
        if 번호 in 덮인일 or ("auto-" + 번호) in 자료["숨김"]:
            continue
        if not _살아있거나방금끝남(일, 칸):
            continue
        자동.append((일.get("시작", ""), 번호, 일))
    자동.sort(reverse=True)
    더있음 = max(0, len(자동) - 자동판최대)
    for _, 번호, 일 in 자동[:자동판최대]:
        항목 = 일항목(번호, 일.get("이름", ""))
        판들.append({"번호": "auto-" + 번호, "이름": 항목["이름"], "자동": True,
                    "항목들": [항목], "상태": _판상태([항목]), "만든때": 일.get("시작", "")})

    판들.sort(key=lambda p: p["상태"] != "달리는중")      # 도는 것이 위로(나머지는 그대로 순서)
    return {"판들": 판들, "더있음": 더있음, "때": _지금초()}


def 요약들() -> dict:
    """방마다 '달리는 일 몇 개 · 진행률' — 방 목록 줄 옆의 작은 막대용. 가볍게 센다."""
    방들 = {}
    for 일, 칸 in _뒤뜰일들():
        방 = 일.get("방") or ""
        if not 방:
            continue
        칸요약 = 방들.setdefault(방, {"달리는수": 0, "퍼센트": None, "끝남수": 0, "실패수": 0})
        상태 = tools_bg._상태(칸, 일)
        if 상태 == "달리는중":
            칸요약["달리는수"] += 1
            if 칸요약["퍼센트"] is None:
                진행 = 진행찾기(_끝줄들(칸 / "기록.txt", 120))
                if 진행 and 진행.get("퍼센트") is not None:
                    칸요약["퍼센트"] = 진행["퍼센트"]
        elif 상태 == "끊김" and _살아있거나방금끝남(일, 칸):
            칸요약["실패수"] += 1
    return {방: v for 방, v in 방들.items() if v["달리는수"] or v["실패수"]}


# ── 당근 (GPT 가 부르는 도구) ──────────────────────────────────

def board_set(action: str = "", name: str = "", items: str = "", **_):
    """현황판을 걸거나 치우거나 본다. GPT 는 '무엇을 볼지' 만 정한다 — 값은 서버가 잰다."""
    짓 = (action or "").strip() or "걸기"
    방 = (rooms.지금방() or {}).get("쪽번호", "")
    if not 방:
        raise ValueError("방이 없습니다. 사용자에게 창에서 일할 곳을 고르라고 말하세요.")
    if 짓 == "걸기":
        결과 = 판걸기(방, name, items)
        결과["안내"] = ("판에 떴습니다. 숫자는 서버가 직접 읽으니 말로 다시 보고하지 않아도 됩니다. "
                      "지금 값은 당근 짓 보기 로 볼 수 있습니다.")
        return 결과
    if 짓 == "치우기":
        return 판치우기(방, name)
    if 짓 == "보기":
        return {"요약": 글로보기(측정(방))}
    raise ValueError("'짓' 은 걸기·치우기·보기 중 하나입니다.")


def 글로보기(측정값: dict) -> str:
    """GPT 가 읽기 좋게 한 줄씩. 판의 숫자와 같은 값이다."""
    줄들 = []
    for 판 in 측정값["판들"]:
        줄들.append(f"■ {판['이름']} — {판['상태']}")
        for x in 판["항목들"]:
            줄들.append("  " + _항목한줄(x))
    return "\n".join(줄들) or "(걸린 판이 없습니다)"


def _초글(초) -> str:
    if 초 is None:
        return "?"
    초 = int(초)
    if 초 < 60:
        return f"{초}초"
    if 초 < 3600:
        return f"{초 // 60}분 {초 % 60}초"
    return f"{초 // 3600}시간 {(초 % 3600) // 60}분"


def _항목한줄(x: dict) -> str:
    이름 = x.get("이름", "")
    if not x.get("있음", True):
        return f"{이름}: {x.get('탈', '읽지 못함')}"
    종류 = x["종류"]
    if 종류 == "일":
        조각 = [f"{이름} {x['상태']}", f"경과 {_초글(x['경과초'])}"]
        진 = x.get("진행")
        if 진 and 진.get("퍼센트") is not None:
            조각.append(f"진행 {진['퍼센트']}%" + (f" ({진['지금']}/{진['전체']})" if 진.get("지금") is not None and 진.get("전체") else ""))
        if x.get("남은초") is not None:
            조각.append(f"남은 약 {_초글(x['남은초'])}")
        if x.get("끝번호") is not None:
            조각.append(f"끝번호 {x['끝번호']}")
        for 숫 in x.get("숫자들") or []:
            조각.append(f"{숫['이름']} {숫['최신']:g}({숫['추이']})")
        return " · ".join(조각)
    if 종류 == "진행":
        진 = x.get("진행")
        return f"{이름}: " + (f"{진['퍼센트']}%" if 진 and 진.get("퍼센트") is not None else "진행 표시를 못 찾음")
    if 종류 == "숫자":
        숫 = x.get("숫자")
        return f"{이름}: " + (f"{숫['최신']:g} ({숫['추이']}, {숫['개수']}번 봄)" if 숫 else "아직 없음")
    if 종류 == "파일":
        최 = x.get("최근") or {}
        return f"{이름}: {x.get('개수')}개, 최근 {최.get('이름')} ({최.get('크기')}바이트, {최.get('몇초전')}초 전)"
    if 종류 == "값":
        return f"{이름}: {x.get('값')}"
    if 종류 == "기록":
        return f"{이름}: " + " | ".join(x.get("줄들") or [])[-160:]
    if 종류 == "기계":
        if x.get("값") == "GPU":
            return f"GPU {x.get('사용률')}% · 메모리 {x.get('메모리쓴')}/{x.get('메모리전체')}MB · {x.get('온도')}℃"
        if x.get("값") == "메모리":
            return f"메모리 {x.get('사용률')}% ({x.get('쓴MB')}/{x.get('전체MB')}MB)"
        return f"디스크 여유 {x.get('여유GB')}GB / {x.get('전체GB')}GB"
    return 이름


등록된도구 = {
    "board_set": board_set,
}
