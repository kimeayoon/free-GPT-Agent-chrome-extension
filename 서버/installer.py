# -*- coding: utf-8 -*-
"""설치 허락 — 무엇을 어디서 받아 어디에 놓는지 보여주고 승인을 받는다.

받아온 것은 결국 실행된다. 그래서 사람이 눈으로 보고 허락하기 전에는
한 줄도 내려받지 않는다.

흐름:
  1. 에이전트가 도토리로 설치를 요청한다 (무엇 / 어디서 / 어디에)
  2. 서버는 받지 않고 '기다림' 으로 쌓아 둔다
  3. 사용자가 창에서 무엇을 받는지 보고 [허용] 을 누른다
  4. 그때 실제로 받는다
  5. 에이전트가 도토리를 다시 부르면 결과를 받는다
"""

import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import sandbox

def 받을자리() -> Path:
    """받아온 것을 놓을 자리. 일터 안 .agent/받은것.

    일터 밖에 두면 프로젝트를 옮길 때 짝이 끊기고, 프로젝트끼리 같은 이름이
    섞인다. 그래서 부를 때마다 지금 일터를 보고 정한다.
    """
    return sandbox.받은것칸()

# 받아오는 데 쓸 수 있는 것만 허용한다. 나머지는 거부.
# 파이썬 꾸러미(pip·uv)는 '어디에' 가 상황에 따라 달라지므로 따로 만든다.
파이썬받기 = ("pip", "uv")
허용받기 = {
    "npm": ["npm", "install"],
    "git": ["git", "clone", "--depth", "1"],
}


def _파이썬꾸러미자리():
    """파이썬 꾸러미를 어디에 넣을지 정한다.

    지금 방 폴더에 일터(.venv)가 있으면 거기로, 없으면 컴퓨터 전체로 간다.
    전체로 가는 건 프로젝트끼리 섞이니 좋지 않다 — 그래서 그 사실을
    허락 물음에 그대로 적어 사람이 보고 판단하게 한다.
    """
    import tools_venv
    일터 = tools_venv.일터파이썬()
    if 일터:
        return str(일터), str(일터.parent.parent), True
    return sys.executable, "컴퓨터 전체 (일터 없음)", False


# 꾸러미 창고로 쓸 수 있는 주소.
# PyTorch 의 CUDA 판처럼 공식 PyPI 가 아닌 곳에서 받아야 하는 것이 있다.
# 아무 주소나 열어주면 받아오기 허락이 무의미해지므로, 여기 적힌 곳만 쓴다.
창고허용 = {
    "https://download.pytorch.org/whl/": "PyTorch 공식 창고",
    "https://pypi.org/simple": "파이썬 공식 창고",
    "https://pypi.nvidia.com": "NVIDIA 공식 창고",
}

# 도토리로 할 수 있는 것
짓목록 = {
    "깔기":   "받아서 깝니다",
    "지우기": "깔린 것을 지웁니다 (받지 않습니다)",
    "올리기": "이미 깔린 것을 최신으로 올립니다",
}


def 창고검사(창고: str) -> str:
    """쓸 수 있는 창고 주소인지 본다. 설명을 돌려준다."""
    창고 = (창고 or "").strip()
    if not 창고:
        return ""
    for 허용, 설명 in 창고허용.items():
        if 창고.startswith(허용):
            return 설명
    raise ValueError(
        "그 창고 주소는 쓸 수 없습니다. 쓸 수 있는 곳: "
        + ", ".join(창고허용)
    )


def _돌릴것만들기(어디서: str, 무엇: str, 창고: str = "", 짓: str = "깔기"):
    """(돌릴 명령, 어디에 설명, 일터인가) 를 돌려준다."""
    if 어디서 in 파이썬받기:
        파이썬, 어디에, 일터인가 = _파이썬꾸러미자리()
        머리 = [파이썬, "-m", "uv", "pip"] if 어디서 == "uv" else [파이썬, "-m", "pip"]

        if 짓 == "지우기":
            return 머리 + ["uninstall", "-y", 무엇], 어디에, 일터인가

        돌릴것 = 머리 + ["install"]
        if 짓 == "올리기":
            돌릴것 += ["--upgrade"]
        if 창고:
            돌릴것 += ["--index-url", 창고]
        return 돌릴것 + [무엇], 어디에, 일터인가

    자리 = 받을자리()
    돌릴것 = 허용받기[어디서] + [무엇]
    if 어디서 == "git":
        이름 = Path(무엇.rstrip("/")).name
        if 이름.endswith(".git"):
            이름 = 이름[:-4]
        돌릴것 = 돌릴것 + [str(자리 / 이름)]
    return 돌릴것, str(자리), False


def _깔렸나(무엇: str) -> dict:
    """깐 뒤에 진짜 들어갔는지 확인한다. 판번호까지 본다.

    '됨' 이 참인데 실제로는 안 들어가 있는 경우가 있다(휠이 없거나
    다른 파이썬에 깔리거나). 그래서 끝나고 한 번 더 본다.
    """
    파이썬, _, _ = _파이썬꾸러미자리()
    이름만 = re.split(r"[=<>!\[]", 무엇)[0].strip()
    if not 이름만:
        return {"확인": "이름을 못 알아봤습니다"}
    try:
        끝 = subprocess.run(
            [파이썬, "-m", "pip", "show", 이름만],
            capture_output=True, timeout=120, text=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"확인": "확인하지 못했습니다"}

    글 = (끝.stdout or b"").decode("utf-8", errors="replace")
    if 끝.returncode != 0 or "Name:" not in 글:
        return {"확인": "안 보입니다", "깔림": False}

    판 = ""
    자리 = ""
    for 줄 in 글.splitlines():
        if 줄.startswith("Version:"):
            판 = 줄.split(":", 1)[1].strip()
        elif 줄.startswith("Location:"):
            자리 = 줄.split(":", 1)[1].strip()
    return {"확인": "보입니다", "깔림": True, "판번호": 판, "깔린자리": 자리}

어디서설명 = {
    "pip": "파이썬 공식 꾸러미 창고 (PyPI)",
    "npm": "노드 공식 꾸러미 창고 (npm)",
    "git": "깃 저장소 (주소를 직접 확인하세요)",
    "uv":  "파이썬 공식 꾸러미 창고 (uv 로)",
}

# 이름에 이상한 글자가 섞이면 거부한다(명령 끼워넣기 방지)
이름규칙 = re.compile(r"^[A-Za-z0-9._\-/@:+]+$")

기다림 = {}   # 열쇠 → 요청
끝난것 = {}   # 열쇠 → 결과


def _열쇠(어디서: str, 무엇: str) -> str:
    return f"{어디서}::{무엇}"


def 요청하기(무엇: str, 어디서: str = "pip", 왜: str = "",
            창고: str = "", 짓: str = "깔기") -> dict:
    """설치를 요청한다. 실제로 받지는 않는다."""
    어디서 = (어디서 or "pip").strip().lower()
    무엇 = (무엇 or "").strip()
    짓 = (짓 or "깔기").strip()
    창고 = (창고 or "").strip()

    if 짓 not in 짓목록:
        raise ValueError("짓 은 " + " · ".join(짓목록) + " 중 하나입니다.")
    if 짓 != "깔기" and 어디서 not in 파이썬받기:
        raise ValueError("지우기·올리기는 파이썬 꾸러미(pip·uv)만 됩니다.")
    창고설명 = 창고검사(창고)
    if 창고 and 짓 == "지우기":
        raise ValueError("지울 때는 창고가 필요 없습니다.")

    쓸수있는곳 = list(파이썬받기) + list(허용받기)
    if 어디서 not in 쓸수있는곳:
        raise ValueError(
            f"'{어디서}' 로는 못 받습니다. 쓸 수 있는 것: " + ", ".join(쓸수있는곳)
        )
    if not 무엇:
        raise ValueError('"무엇" 이 비었습니다.')
    if not 이름규칙.match(무엇):
        raise ValueError(
            "이름에 쓸 수 없는 글자가 있습니다. "
            "영문·숫자와 . _ - / @ : + 만 됩니다."
        )
    if 어디서 == "git" and not 무엇.startswith(("https://", "git@")):
        raise ValueError("깃은 https:// 또는 git@ 로 시작하는 주소만 됩니다.")

    열쇠 = _열쇠(어디서, f"{짓}:{무엇}:{창고}")

    if 열쇠 in 끝난것:
        return {"상태": "끝남", **끝난것[열쇠]}

    돌릴것, 어디에, 일터인가 = _돌릴것만들기(어디서, 무엇, 창고, 짓)

    기다림[열쇠] = {
        "열쇠": 열쇠,
        "무엇": 무엇,
        "어디서": 어디서,
        "어디서설명": (창고설명 + f" ({창고})") if 창고 else 어디서설명[어디서],
        "어디에": 어디에 if 짓 != "지우기" else f"{어디에} 에서 지웁니다",
        "일터인가": 일터인가,
        "짓": 짓,
        "창고": 창고,
        "왜": 왜 or "(이유를 안 적었습니다)",
        "돌릴것": " ".join(shlex.quote(x) for x in 돌릴것),
        "때": datetime.now().strftime("%H:%M:%S"),
    }

    안내꼬리 = ""
    if 어디서 in 파이썬받기 and not 일터인가:
        안내꼬리 = (
            " 지금은 일터(.venv)가 없어서 컴퓨터 전체에 깔립니다. "
            "프로젝트끼리 섞이지 않게 하려면 먼저 씨앗으로 일터를 만드세요."
        )

    return {
        "상태": "기다림",
        "무엇": 무엇,
        "짓": 짓,
        "어디서": (창고설명 + f" ({창고})") if 창고 else 어디서설명[어디서],
        "어디에": 어디에,
        "일터인가": 일터인가,
        "안내": (
            "아직 아무것도 받지 않았습니다. "
            "사용자에게 이렇게 말하고 답변을 끝내세요 — "
            f"'{무엇} 을(를) 받아야 합니다. 창에 뜬 물음에서 무엇을 받는지 "
            "확인하고 [허용] 을 눌러 주세요.' "
            "허락이 떨어지면 도토리를 다시 불러 결과를 받으세요." + 안내꼬리
        ),
    }


def 바깥도구요청(이름: str, 명령: list, 자리: str = "", 왜: str = "") -> dict:
    """MCP 서버를 띄워 달라는 요청. 받아오기와 같은 카드로 승인을 받는다.

    띄우는 것은 남의 프로그램을 돌리는 일이다. 무엇을 돌리는지 사람이
    눈으로 보고 허락해야 하므로, 받아오기와 같은 줄에 세운다.
    """
    열쇠 = _열쇠("mcp", 이름)

    if 열쇠 in 끝난것:
        return {"상태": "끝남", **끝난것[열쇠]}

    기다림[열쇠] = {
        "열쇠": 열쇠,
        "갈래": "mcp",
        "무엇": 이름,
        "어디서": "mcp",
        "어디서설명": "바깥 도구(MCP) 를 띄웁니다",
        "어디에": 자리 or "(지금 일하는 곳)",
        "일터인가": False,
        "왜": 왜 or "(이유를 안 적었습니다)",
        "명령": 명령,
        "자리": 자리,
        "돌릴것": " ".join(shlex.quote(x) for x in 명령),
        "때": datetime.now().strftime("%H:%M:%S"),
    }

    return {
        "상태": "기다림",
        "무엇": 이름,
        "어디서": "바깥 도구(MCP)",
        "안내": (
            "아직 아무것도 띄우지 않았습니다. 사용자에게 이렇게 말하고 답변을 "
            f"끝내세요 — '{이름} 도구를 띄워야 합니다. 창에 뜬 물음에서 무엇을 "
            "돌리는지 확인하고 [허용] 을 눌러 주세요.' "
            "허락이 떨어지면 열매를 다시 불러 결과를 받으세요."
        ),
    }


def 목록() -> list:
    import gate           # 눈·손 허가 요청도 같은 카드 줄에 선다
    import approval       # 권한 모드가 묻는 카드도 같은 줄에 선다
    return list(기다림.values()) + gate.기다림목록() + approval.기다림목록()


def 거절하기(열쇠: str) -> dict:
    if 열쇠.startswith("허가::"):
        import gate
        return gate.거절하기(열쇠)
    요청 = 기다림.pop(열쇠, None)
    if 요청:
        끝난것[열쇠] = {
            "무엇": 요청["무엇"], "됨": False,
            "나온것": "사용자가 받지 않기로 했습니다.",
        }
    return {"열쇠": 열쇠}


def 허락하기(열쇠: str) -> dict:
    """이제 실제로 받는다."""
    if 열쇠.startswith("허가::"):
        import gate
        return gate.허락하기(열쇠)
    요청 = 기다림.pop(열쇠, None)
    if 요청 is None:
        raise ValueError("그런 요청이 없습니다(이미 처리했을 수 있습니다).")

    # MCP 는 받아오는 게 아니라 띄우는 것이라 길이 다르다
    if 요청.get("갈래") == "mcp":
        import mcp_client
        try:
            결과 = {"무엇": 요청["무엇"], "됨": True,
                    **mcp_client.붙이기(요청["무엇"], 요청["명령"],
                                       요청.get("자리", ""))}
        except Exception as e:
            결과 = {"무엇": 요청["무엇"], "됨": False,
                    "나온것": f"띄우지 못했습니다: {e}"}
        끝난것[열쇠] = 결과
        return {"열쇠": 열쇠, **결과}

    일하는자리_ = 받을자리()
    일하는자리_.mkdir(parents=True, exist_ok=True)
    돌릴것, 어디에, _ = _돌릴것만들기(
        요청["어디서"], 요청["무엇"], 요청.get("창고", ""), 요청.get("짓", "깔기")
    )
    일하는자리 = 일하는자리_

    try:
        끝 = subprocess.run(
            돌릴것,
            cwd=str(일하는자리),
            capture_output=True,
            timeout=900,
            text=False,
            shell=False,      # 셸을 거치지 않는다. 명령 끼워넣기를 막는다.
        )
        나온것 = (끝.stdout or b"") + b"\n" + (끝.stderr or b"")
        글 = 나온것.decode("utf-8", errors="replace").strip()[-4000:]
        결과 = {"무엇": 요청["무엇"], "됨": 끝.returncode == 0,
                "끝번호": 끝.returncode, "어디에": 어디에,
                "나온것": 글 or "(출력 없음)"}
        # 깔았다고 하고 실제로는 안 들어간 경우가 있다. 눈으로 한 번 더 본다.
        if 요청["어디서"] in 파이썬받기:
            결과.update(_깔렸나(요청["무엇"]))
    except subprocess.TimeoutExpired:
        결과 = {"무엇": 요청["무엇"], "됨": False,
                "끝번호": None, "나온것": "15분을 넘겨 중단했습니다."}
    except FileNotFoundError:
        결과 = {"무엇": 요청["무엇"], "됨": False, "끝번호": None,
                "나온것": f"'{돌릴것[0]}' 을(를) 찾을 수 없습니다. 설치돼 있나요?"}

    끝난것[열쇠] = 결과
    return {"열쇠": 열쇠, **결과}
