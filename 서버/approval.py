# -*- coding: utf-8 -*-
"""승인 문 — 권한 모드(전체권한 · 자동 · 수동)에 따라 도구 호출을 '바로 함 · 사용자에게 물음 · 막음' 으로 가른다.

  전체권한 : 묻지 않는다. (차단 명령 · 비밀 파일 · 설치 · 화면 · 입력 · 바깥 도구는 모드와 상관없이 따로 막거나 묻는다)
  자동     : 일할 폴더 안의 읽기 · 고치기 · 안전한 명령은 GPT 가 처리하고, 위험한 일만 묻는다
  수동     : 고치기 · 지우기 · 명령 · 일꾼 부르기 전에 늘 묻는다. 읽기와 기록은 그대로 한다

묻는 일은 판에 카드로 뜬다([이번만 허용] [이 방에서 항상 허용] [거부]). 허용하면 서버가 그 호출을 그대로 돌리고
결과를 GPT 에게 돌려준다. '항상 허용' 은 방마다(방 자료칸/허용규칙.json) 같은 종류만 기억한다.

일꾼 방과 웹사이트 호출은 카드를 볼 사람이 없으므로 '물을 일' 은 그냥 막는다.
"""

import itertools
import re
import shlex
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import permission
import rooms
import sandbox
import 안전파일

자동, 카드, 막음 = "자동", "카드", "막음"

읽기도구 = {"열무", "가지", "미나리", "버섯", "호박"}
기록도구 = {"감자", "고구마", "토란", "더덕", "우엉", "이름표", "숙주", "당근", "배추", "무", "고사리", "팥"}
자기문있는도구 = {"도토리", "열매", "오이", "마늘"}        # 이미 자기 승인 카드(설치 · 바깥 도구 · 화면 · 입력)가 있다
고치기도구 = {"부추", "상추", "쑥", "냉이"}
지우기옮기기 = {"시금치", "갓"}

한번에많이 = 10            # 폴더를 지우거나 옮길 때 파일이 이만큼을 넘으면 자동이어도 묻는다
두릅자동최대 = 3            # 자동 모드에서 한 방이 동시에 돌려도 되는 뒤뜰 일
두릅전체최대 = 6
카드줄최대 = 8
카드글최대 = 140

비밀이름패턴 = (".env", ".env.*", "credentials.json", "token.json", "*.key", "*.pem", "id_rsa*", "id_ed25519*", "*.ppk", "*.kdbx")

_잠금 = threading.RLock()
기다림: dict = {}            # 열쇠 → 요청(판에 카드로 뜬다)
_번호 = itertools.count(1)


# ── 글 다듬기 ─────────────────────────────────────────────────────

def _짧게(글, 최대=카드글최대) -> str:
    글 = str(글 if 글 is not None else "").replace("\r", "").replace("\n", " ⏎ ").strip()
    return 글 if len(글) <= 최대 else 글[:최대 - 1] + "…"


def _앞줄들(글, 줄수=3) -> list:
    줄들 = str(글 if 글 is not None else "").replace("\r", "").split("\n")
    나온 = [_짧게(줄) for 줄 in 줄들[:줄수]]
    if len(줄들) > 줄수:
        나온.append(f"… 외 {len(줄들) - 줄수}줄")
    return 나온


def _비밀이름인가(경로) -> bool:
    import fnmatch
    이름 = Path(str(경로)).name.lower()
    return any(fnmatch.fnmatch(이름, p.lower()) for p in 비밀이름패턴)


def _일할폴더():
    try:
        return rooms.지금밭()
    except Exception:
        return None


def _안인가(대상: Path, 폴더) -> bool:
    if 폴더 is None:
        return True            # 폴더를 안 정했으면 비교할 곳이 없다 — 막는 것은 sandbox 가 한다
    try:
        sandbox._정규화(대상).relative_to(sandbox._정규화(폴더))
        return True
    except ValueError:
        return False


def _파일수(경로: Path, 상한=한번에많이 + 1) -> int:
    if 경로.is_file():
        return 1
    수 = 0
    try:
        for 하나 in 경로.rglob("*"):
            if 하나.is_file():
                수 += 1
                if 수 >= 상한:
                    break
    except OSError:
        pass
    return 수


# ── 방마다 '항상 허용' ─────────────────────────────────────────────

def _규칙파일(방번호: str) -> Path:
    return rooms.방자료칸(방번호) / "허용규칙.json"


def 규칙들(방번호: str) -> list:
    값 = 안전파일.json읽기(_규칙파일(방번호), [], list)
    return [str(x) for x in (값 or [])]


def 규칙있나(방번호: str, 분류: str) -> bool:
    return bool(분류) and 분류 in 규칙들(방번호)


def 규칙더하기(방번호: str, 분류: str) -> None:
    if not 분류:
        return
    with _잠금:
        목록 = 규칙들(방번호)
        if 분류 not in 목록:
            목록.append(분류)
            안전파일.json쓰기(_규칙파일(방번호), 목록)


def 규칙비우기(방번호: str) -> None:
    with _잠금:
        안전파일.json쓰기(_규칙파일(방번호), [])


# ── 명령이 안전한 꼴인가 ───────────────────────────────────────────

_이음표 = re.compile(r"\s*(?:&&|\|\||;|\|)\s*")
_안전읽기명령 = {
    "dir", "ls", "type", "cat", "more", "head", "tail", "echo", "where", "which", "findstr", "grep", "pwd", "cd",
    "nvidia-smi", "hostname", "whoami", "date", "tree", "wc", "sort", "uniq", "fc", "diff",
}
_안전깃 = {"status", "diff", "log", "branch", "show", "rev-parse", "ls-files", "blame", "describe", "remote", "config"}
_안전파이썬모듈 = {"unittest", "pytest", "py_compile", "compileall", "doctest", "timeit", "json.tool"}
_안전핍 = {"list", "show", "freeze", "check", "--version", "-V"}
_파이썬실행기 = re.compile(r"^(?:py(?:\.exe)?|python3?(?:\.\d+)?(?:\.exe)?)$", re.IGNORECASE)
_옵션값있음 = {"-X", "-W", "--check-hash-based-pycs"}
_옵션만 = {"-u", "-B", "-E", "-s", "-S", "-O", "-OO", "-I", "-q", "-v", "-b", "-d", "-x", "-R", "-P", "-3"}


_경로안봄 = {"echo", "hostname", "whoami", "date", "nvidia-smi", "pwd"}


def _경로가_안인가(토큰들: list, 자리, 폴더) -> bool:
    """읽는 명령이 가리키는 경로가 모두 일할 폴더 안인가(밖을 읽으면 열무처럼 물어야 한다)."""
    if 폴더 is None:
        return True
    기준 = 자리 if 자리 is not None else 폴더
    for t in 토큰들:
        t = t.strip('"').replace("▸", "/")
        if not t or t.startswith(("-", "/")) and len(t) <= 3:
            continue
        경로꼴 = ("\\" in t) or ("/" in t) or (":" in t) or (".." in t) or t.startswith("~")
        if not 경로꼴:
            continue
        if t.startswith("~"):
            return False
        후보 = Path(t) if Path(t).is_absolute() else Path(기준) / t
        if not _안인가(후보, 폴더):
            return False
    return True


def _토큰(명령: str) -> list:
    try:
        return shlex.split(명령, posix=False)
    except ValueError:
        return 명령.split()


def _파이썬꼴(토큰: list, 자리: Path, 폴더) -> tuple:
    """(안전한가, 분류글). 토큰[0] 이 파이썬 실행기일 때."""
    i = 1
    # py -3 / py -3.14
    while i < len(토큰) and re.fullmatch(r"-3(?:\.\d+)?|-\d\.\d+(?:-\d+)?", 토큰[i]):
        i += 1
    while i < len(토큰):
        t = 토큰[i]
        if t in _옵션값있음:
            i += 2
        elif t in _옵션만 or re.fullmatch(r"-X\S+", t):
            i += 1
        else:
            break
    if i >= len(토큰):
        return True, "python"            # 대화형 — 입력이 없어 곧 끝난다
    t = 토큰[i]
    if t == "-c":
        return False, ""
    if t in ("--version", "-V"):
        return True, "python --version"
    if t == "-m":
        if i + 1 >= len(토큰):
            return False, ""
        모듈 = 토큰[i + 1]
        if 모듈 == "pip":
            하위 = 토큰[i + 2] if i + 2 < len(토큰) else ""
            return (하위 in _안전핍), f"python -m pip {하위}"
        if 모듈 in _안전파이썬모듈:
            return True, f"python -m {모듈}"
        # 일할 폴더 안의 모듈(sim.train_combat 같은 것) — 그 폴더의 파일을 돌리는 것이다
        부분 = 모듈.split(".")
        기준 = 자리 if 자리 is not None else 폴더
        if 기준 is not None and all(re.fullmatch(r"[A-Za-z_]\w*", p) for p in 부분):
            후보 = [기준.joinpath(*부분).with_suffix(".py"), 기준.joinpath(*부분) / "__main__.py"]
            if any(p.is_file() and _안인가(p, 폴더) for p in 후보):
                return True, f"python -m {모듈}"
        return False, ""
    if t.startswith("-"):
        return False, ""
    # 스크립트 파일
    파일 = t.strip('"').replace("▸", "/")
    if not 파일.lower().endswith(".py"):
        return False, ""
    기준 = 자리 if 자리 is not None else 폴더
    if 기준 is None:
        return False, ""
    경로 = (기준 / 파일) if not Path(파일).is_absolute() else Path(파일)
    if 경로.is_file() and _안인가(경로, 폴더) and not _비밀이름인가(경로):
        return True, f"python {파일}"
    return False, ""


def 명령분류(명령: str, 자리: Path | None, 폴더) -> tuple:
    """(안전한 꼴인가, 분류글). 안전 = 읽기 명령 · 시험 · 일할 폴더 안 파이썬. 그 밖에는 묻는다."""
    글 = str(명령 or "").strip()
    if not 글:
        return False, ""
    if any(x in 글 for x in (">", "<", "`", "$(", "%(")):
        return False, ""                       # 파일로 쏟거나 끼워 넣기 — 안전하다고 안 본다
    조각들 = [c for c in _이음표.split(글) if c.strip()]
    분류들 = []
    for 조각 in 조각들:
        토큰 = _토큰(조각)
        if not 토큰:
            continue
        머리 = 토큰[0].strip('"').lower()
        if any(_비밀이름인가(t.strip('"')) for t in 토큰[1:]):
            return False, ""                   # .env 같은 것을 건드리는 명령은 안 넘긴다
        if _파이썬실행기.match(머리):
            됨, 분류 = _파이썬꼴(토큰, 자리, 폴더)
            if not 됨:
                return False, ""
            분류들.append(분류)
        elif 머리 in _안전읽기명령:
            if 머리 not in _경로안봄 and not _경로가_안인가(토큰[1:], 자리, 폴더):
                return False, ""
            분류들.append(머리)
        elif 머리 == "git" and len(토큰) > 1 and 토큰[1].lower() in _안전깃:
            if 토큰[1].lower() == "config" and not any(t in ("--get", "--list", "-l") for t in 토큰[2:]):
                return False, ""
            if 토큰[1].lower() == "remote" and len(토큰) > 2 and 토큰[2].lower() not in ("-v", "show", "get-url"):
                return False, ""
            if 토큰[1].lower() == "branch" and any(t in ("-d", "-D", "-m", "-M", "--delete") for t in 토큰[2:]):
                return False, ""
            분류들.append("git " + 토큰[1].lower())
        elif 머리 in ("pytest", "py.test"):
            분류들.append("pytest")
        elif 머리 == "pip" and len(토큰) > 1 and 토큰[1].lower() in _안전핍:
            분류들.append("pip " + 토큰[1].lower())
        else:
            return False, ""
    if not 분류들:
        return False, ""
    return True, " + ".join(dict.fromkeys(분류들))[:80]


def _명령규칙키(명령: str) -> str:
    """'항상 허용' 으로 기억할 말: 실행기를 python 으로 통일한 앞 세 낱말."""
    토큰 = _토큰(str(명령 or "").strip())
    if not 토큰:
        return ""
    if _파이썬실행기.match(토큰[0].strip('"')):
        토큰 = ["python"] + [t for t in 토큰[1:] if not re.fullmatch(r"-3(?:\.\d+)?", t)]
    return "명령:" + " ".join(t.strip('"') for t in 토큰[:3]).lower()[:80]


# ── 판정 ─────────────────────────────────────────────────────────

def _카드(제목: str, 줄들: list, 분류: str, 위험=False) -> tuple:
    return 카드, {"제목": _짧게(제목, 80), "줄들": [_짧게(x) for x in 줄들][:카드줄최대], "분류": 분류, "위험": bool(위험)}


def _경로글(경로) -> str:
    try:
        return sandbox.표시경로(Path(sandbox._정규화(Path(str(경로)))))
    except Exception:
        return str(경로)


def _대상경로(인자: dict, 키="path") -> Path | None:
    값 = 인자.get(키)
    if not 값 or not str(값).strip():
        return None
    try:
        return sandbox.경로검증(str(값), 쓰기=False)
    except Exception:
        return None


def 판정(도구명: str, 인자: dict, 방번호: str = "", 모드: str | None = None, 웹출처: bool = False) -> tuple:
    """(자동 | 카드 | 막음, 요약). 막음이면 요약['탈'], 카드이면 요약['제목'·'줄들'·'분류'·'위험']."""
    모드 = 모드 or permission.모드읽기()
    결과 = _판정(도구명, 인자, 방번호, 모드)
    if 결과[0] != 카드:
        return 결과
    # 카드를 볼 사람이 없는 곳은 물을 수 없다
    역할 = rooms.방역할(방번호) if 방번호 else ""
    if 웹출처:
        return 막음, {"탈": "웹사이트가 부른 도구는 사용자 승인이 필요한 일을 할 수 없습니다. 판에서 직접 하세요."}
    if 역할:
        return 막음, {"탈": f"'{모드}' 모드에서는 일꾼({역할})이 이 일을 할 수 없습니다. 사용자 승인이 필요한 일입니다. "
                           "대장 대화에서 하거나, 사용자가 모드를 바꾸면 됩니다."}
    if 규칙있나(방번호, 결과[1].get("분류", "")):
        return 자동, {}
    return 결과


def _판정(도구명: str, 인자: dict, 방번호: str, 모드: str) -> tuple:
    if 도구명 in 자기문있는도구 or 도구명 in 기록도구:
        return 자동, {}
    폴더 = _일할폴더()
    전체 = 모드 == "전체권한"
    수동 = 모드 == "수동"

    if 도구명 in 읽기도구:
        if 전체:
            return 자동, {}
        대상 = None
        for 조각 in str(인자.get("path") or "").split(","):
            if not 조각.strip():
                continue
            try:
                대상 = sandbox.경로검증(조각.strip())
            except Exception:
                대상 = None
            if 대상 is not None and not _안인가(대상, 폴더):
                부모 = 대상.parent if 대상.suffix or 대상.is_file() else 대상
                return _카드("일할 폴더 밖을 읽으려 합니다", ["읽을 곳  " + _경로글(대상),
                                                          "일할 폴더  " + (_경로글(폴더) if 폴더 else "(정하지 않음)")],
                         "읽기:" + str(sandbox._정규화(부모)).lower())
        return 자동, {}

    if 도구명 == "취":
        if 전체 or not 수동:
            return 자동, {}
        호스트 = (urlsplit(str(인자.get("url") or "")).hostname or "").lower()
        return _카드("웹 글을 읽으려 합니다", ["주소  " + _짧게(인자.get("url"))], "웹:" + 호스트)

    if 도구명 in 고치기도구:
        if not 수동:
            return 자동, {}
        대상 = _대상경로(인자)
        이름 = _경로글(대상) if 대상 else _짧게(인자.get("path"))
        # 읽기가 막힌 이름(.env 등)은 경로 검증이 실패해 대상이 None 이다 — 이름으로 직접 본다
        비밀 = _비밀이름인가(인자.get("path") or "")
        if 도구명 == "부추":
            줄들 = ["파일  " + 이름]
            줄들 += ["비밀 파일 — 내용은 표시하지 않습니다"] if 비밀 else \
                ["바꿀 글  " + x for x in _앞줄들(인자.get("old"), 2)] + ["새 글  " + x for x in _앞줄들(인자.get("new"), 2)]
            return _카드("파일 일부를 고치려 합니다", 줄들, "고치기")
        if 도구명 == "상추":
            있음 = bool(대상 and 대상.exists())
            줄들 = ["파일  " + 이름, ("이미 있는 파일을 덮어씁니다(원본은 백업됩니다)" if 있음 else "새 파일을 만듭니다")]
            줄들 += ["비밀 파일 — 내용은 표시하지 않습니다"] if 비밀 else ["내용  " + x for x in _앞줄들(인자.get("content"), 4)]
            return _카드("파일을 쓰려 합니다", 줄들, "고치기")
        if 도구명 == "쑥":
            줄들 = ["파일  " + 이름] + (["비밀 파일 — 내용은 표시하지 않습니다"] if 비밀 else
                                          ["덧붙일 글  " + x for x in _앞줄들(인자.get("content"), 3)])
            return _카드("파일 끝에 글을 덧붙이려 합니다", 줄들, "고치기")
        return _카드("폴더를 만들려 합니다", ["폴더  " + 이름], "고치기")

    if 도구명 in 지우기옮기기:
        대상 = _대상경로(인자)
        이름 = _경로글(대상) if 대상 else _짧게(인자.get("path"))
        많음 = bool(대상 and 대상.exists() and _파일수(대상) > 한번에많이)
        if not 수동 and not 많음:
            return 자동, {}
        if 도구명 == "시금치":
            줄들 = ["지울 것  " + 이름, "실제로 지우지 않고 휴지통 폴더로 옮깁니다"]
            if 많음:
                줄들.append(f"파일이 {한번에많이}개를 넘습니다")
            return _카드("지우려 합니다", 줄들, "삭제옮기기", 위험=많음)
        줄들 = ["대상  " + 이름, "새 자리  " + _짧게(인자.get("dest")), "하는 일  " + _짧게(인자.get("action") or "옮기기")]
        if 많음:
            줄들.append(f"파일이 {한번에많이}개를 넘습니다")
        return _카드("옮기거나 베끼려 합니다", 줄들, "삭제옮기기", 위험=많음)

    if 도구명 == "미역":
        if not 수동:
            return 자동, {}
        return _카드("보관해 둔 것으로 되돌리려 합니다", ["파일  " + _짧게(인자.get("path")), "때  " + _짧게(인자.get("when") or "(가장 최근)")], "되돌리기")

    if 도구명 == "씨앗":
        if not 수동:
            return 자동, {}
        return _카드("일터(.venv)를 만들려 합니다", ["버전  " + _짧게(인자.get("version") or "(기본)")], "일터")

    if 도구명 in ("도라지", "두릅"):
        명령 = str(인자.get("command") or "")
        자리 = None
        try:
            자리 = sandbox.경로검증(str(인자.get("cwd") or "."))
        except Exception:
            자리 = None
        if 도구명 == "두릅" and not 수동:
            돌고 = _돌고있는일수(방번호)
            한도 = 두릅전체최대 if 전체 else 두릅자동최대
            if 돌고 >= 한도:
                return _카드("오래 걸리는 일이 이미 많이 돌고 있습니다",
                           [f"지금 {돌고}개 돌고 있습니다(한도 {한도}개)", "명령  " + _짧게(명령)], _명령규칙키(명령), 위험=True)
        if 전체:
            return 자동, {}
        안전, _분류 = 명령분류(명령, 자리, 폴더)
        if 안전 and not 수동 and (자리 is None or _안인가(자리, 폴더)):
            return 자동, {}
        줄들 = ["명령  " + _짧게(명령, 200), "자리  " + (_경로글(자리) if 자리 else _짧게(인자.get("cwd") or "."))]
        if 도구명 == "두릅":
            줄들.append("오래 걸리는 일로 풀어 둡니다(서버를 껐다 켜도 계속 돕니다)")
        return _카드("명령을 실행하려 합니다" if 도구명 == "도라지" else "오래 걸리는 일을 시작하려 합니다", 줄들, _명령규칙키(명령))

    if 도구명 == "칡":
        짓 = str(인자.get("action") or "상태").strip()
        if 짓 in ("상태", "차이", "담긴차이", "기록", "가지") or not 수동:
            return 자동, {}
        return _카드("깃에 기록하려 합니다", ["하는 일  " + 짓, "메모  " + _짧게(인자.get("note"))], "깃담기")

    if 도구명 == "콩":
        if not 수동:
            return 자동, {}
        return _카드("일꾼을 부르려 합니다", ["역할  " + _짧게(인자.get("role")), "이름  " + _짧게(인자.get("name")),
                                         "맡길 일  " + _짧게(인자.get("task"), 200)], "일꾼")

    return 자동, {}


def _돌고있는일수(방번호: str) -> int:
    try:
        import tools_bg
        return sum(1 for 일 in tools_bg._목록() if 일.get("상태") == "달리는중")
    except Exception:
        return 0


# ── 기다림(카드) ───────────────────────────────────────────────────

def 요청하기(도구명: str, 인자: dict, 방번호: str, 요약: dict, 모드: str = "") -> dict:
    """사용자에게 물을 카드를 남긴다. 아무것도 돌리지 않는다. GPT 에게 돌려줄 결과를 만든다."""
    with _잠금:
        # 같은 일을 GPT 가 또 보냈으면 카드를 또 만들지 않는다
        for 열쇠, 이미 in 기다림.items():
            if 이미["나물"] == 도구명 and 이미["인자"] == 인자 and 이미["방번호"] == 방번호:
                return _기다림답(이미)
        열쇠 = f"승인::{next(_번호)}-{int(time.time() * 1000) % 100000}"
        요청 = {
            "열쇠": 열쇠, "갈래": "승인", "나물": 도구명, "인자": dict(인자), "방번호": 방번호,
            "제목": 요약.get("제목", ""), "줄들": list(요약.get("줄들", [])), "분류": 요약.get("분류", ""),
            "위험": bool(요약.get("위험")), "모드": 모드, "때": time.strftime("%H:%M:%S"),
        }
        기다림[열쇠] = 요청
    return _기다림답(요청)


def _기다림답(요청: dict) -> dict:
    return {
        "상태": "기다림", "갈래": "승인", "열쇠": 요청["열쇠"], "일": 요청["제목"],
        "안내": ("아직 실행하지 않았습니다. 사용자의 승인을 기다리는 중입니다. 사용자에게 \"창에 뜬 물음에서 [허용] 을 눌러 주세요\" "
                 "라고 말하고 답변을 끝내세요. 허락하면 실행한 결과가 알림으로 옵니다. 거부하면 그 말이 옵니다. 같은 요청을 다시 보내지 마세요."),
    }


def 기다림목록(방번호: str | None = None) -> list:
    """판에 보일 카드(인자 원문은 빼고)."""
    with _잠금:
        나온 = []
        for 요청 in 기다림.values():
            if 방번호 is not None and 방번호 and 요청["방번호"] != 방번호:
                continue
            나온.append({k: v for k, v in 요청.items() if k != "인자"})
        return 나온


def 허락하기(열쇠: str, 항상: bool = False) -> dict:
    """기다림을 꺼내 돌려준다(돌리는 것은 부른 쪽). 항상 이면 같은 분류를 이 방에서 다시 안 묻는다."""
    with _잠금:
        요청 = 기다림.pop(열쇠, None)
    if 요청 is None:
        raise ValueError("그런 요청이 없습니다(이미 처리했을 수 있습니다).")
    if 항상 and 요청.get("분류") and not 요청.get("위험"):
        규칙더하기(요청["방번호"], 요청["분류"])
    return {"열쇠": 열쇠, "갈래": "승인", "나물": 요청["나물"], "인자": 요청["인자"], "방번호": 요청["방번호"],
            "제목": 요청["제목"], "분류": 요청["분류"]}


def 거절하기(열쇠: str) -> dict:
    with _잠금:
        요청 = 기다림.pop(열쇠, None)
    return {"열쇠": 열쇠, "갈래": "승인", "나물": (요청 or {}).get("나물", ""), "제목": (요청 or {}).get("제목", ""),
            "됨": False, "나온것": "사용자가 허락하지 않았습니다. 같은 일을 다시 요청하지 말고, 무엇이 걱정인지 물어보세요."}


def 모두비우기() -> None:
    with _잠금:
        기다림.clear()
