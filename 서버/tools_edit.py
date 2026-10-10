# -*- coding: utf-8 -*-
"""쓰기 도구 — write_file / replace_text / delete_file / create_dir.

'전부 자동' 모드라 승인 버튼이 없다. 대신 모든 파괴적 작업 전에
원본을 _archive/백업/ 으로 복사해 둔다. 삭제는 실제 삭제 대신 휴지통 이동.
"""

import difflib
import shutil
from datetime import datetime
from pathlib import Path

import sandbox
from tools_file import _텍스트읽기

쓰기최대 = sandbox.설정["쓰기최대바이트"]


def _줄증감(앞글: str, 뒷글: str) -> tuple[int, int]:
    """진짜 차이를 내서 더한 줄·뺀 줄 수를 센다."""
    차이 = difflib.unified_diff(앞글.splitlines(), 뒷글.splitlines(), lineterm="", n=0)
    더함 = 뺌 = 0
    for 줄 in 차이:
        if 줄.startswith("+") and not 줄.startswith("+++"):
            더함 += 1
        elif 줄.startswith("-") and not 줄.startswith("---"):
            뺌 += 1
    return 더함, 뺌


차이최대줄 = 40
차이최대글자 = 200


def _차이(앞글: str, 뒷글: str) -> dict:
    """화면에 색으로 보여줄 바뀐 줄.

    이 값은 '_' 로 시작하는 키에 담아 돌려준다. 확장이 결과를 GPT 에게
    글로 되돌릴 때 '_' 로 시작하는 키는 건너뛰므로, 대화창 글자 수를
    늘리지 않고 판에서만 쓸 수 있다.
    """
    줄들: list[str] = []
    잘림 = False
    for 줄 in difflib.unified_diff(앞글.splitlines(), 뒷글.splitlines(),
                                   lineterm="", n=2):
        if 줄.startswith("---") or 줄.startswith("+++"):
            continue
        if len(줄들) >= 차이최대줄:
            잘림 = True
            break
        줄들.append(줄[:차이최대글자])
    return {"줄들": 줄들, "잘림": 잘림}


def _백업(대상: Path) -> str | None:
    """원본을 백업 폴더로 복사하고 백업 경로를 돌려준다. 파일이 없으면 None."""
    if not 대상.exists() or not 대상.is_file():
        return None

    # 밀리초까지 넣는다. 초 단위로만 하면 같은 초에 두 번 보관할 때
    # 앞의 것이 덮어써져 원본이 날아간다(실제로 한 번 날아갔다).
    도장 = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    상대 = sandbox.보관속경로(대상)
    백업경로 = sandbox.백업칸() / 도장 / 상대
    백업경로.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(대상, 백업경로)
    return str(백업경로)


def write_file(path: str, content: str, **_):
    """파일을 통째로 쓴다. 기존 파일이 있으면 먼저 백업한다."""
    if content is None:
        raise ValueError('"속" 이 없습니다.')
    바이트수 = len(content.encode("utf-8"))
    if 바이트수 > 쓰기최대:
        raise ValueError(f"내용이 너무 큽니다({바이트수:,} > {쓰기최대:,}).")

    대상 = sandbox.경로검증(path, 쓰기=True)
    기존 = 대상.exists()
    비밀 = sandbox.비밀파일인가(대상)
    if 비밀 and 기존:
        raise ValueError(
            f"{대상.name} 은 이미 있는 비밀 파일이라 통째로 덮어쓰지 않습니다(들어 있는 키가 사라질 수 있습니다). "
            "새 키 줄은 쑥으로 덧붙이고, 있는 값을 고치는 것은 사용자가 직접 하게 하세요.")
    옛글 = ""
    if 기존:
        try:
            옛글 = _텍스트읽기(대상)
        except ValueError:
            옛글 = ""      # 바이너리였다면 증감은 셀 수 없다
    백업 = _백업(대상)

    대상.parent.mkdir(parents=True, exist_ok=True)
    대상.write_text(content, encoding="utf-8", newline="\n")

    더함, 뺌 = _줄증감(옛글, content)
    결과 = {
        "path": sandbox.표시경로(대상),
        "action": "덮어씀" if 기존 else "새로 만듦",
        "bytes": 바이트수,
        "lines": len(content.splitlines()),
        "더한줄": 더함,
        "뺀줄": 뺌,
        "backup": 백업,
        "_차이": _차이(옛글, content),
    }
    if 비밀:
        # 비밀 파일은 바뀐 줄을 판 · 기록에 남기지 않는다(키가 로그에 복사되지 않게)
        결과["_차이"] = {"줄들": [], "잘림": False}
        결과["안내"] = "비밀 파일입니다. 쓰기만 되고 읽을 수 없습니다. 값은 사용자가 직접 채워 넣게 하세요."
    return 결과


def replace_text(path: str, old: str, new: str, count: int | None = None, **_):
    """파일 안의 정확히 일치하는 문자열을 바꾼다.

    old 가 몇 번 나오는지 먼저 세고, 예상과 다르면 아무것도 안 바꾸고 실패시킨다.
    (count 를 주면 그 횟수만큼 나와야 하고, 안 주면 정확히 1번이어야 한다.)
    """
    if not old:
        raise ValueError('"앞" 이 비었습니다. 통째로 쓰려면 상추를 쓰세요.')
    if old == new:
        raise ValueError('"앞" 과 "뒤" 가 같습니다.')

    대상 = sandbox.경로검증(path, 쓰기=True)
    if sandbox.비밀파일인가(대상):
        # 바꾸려면 '앞' 이 몇 군데 있는지 알려 줘야 해서, 되풀이하면 내용을 알아낼 수 있다 — 막는다
        raise ValueError(f"{대상.name} 은 비밀 파일이라 일부만 바꿀 수 없습니다. "
                         "새 키 줄은 쑥으로 덧붙이고, 있는 값을 고치는 것은 사용자가 직접 하게 하세요.")
    if not 대상.exists():
        raise FileNotFoundError(f"파일이 없습니다: {대상}")

    본문 = _텍스트읽기(대상)
    실제횟수 = 본문.count(old)
    기대횟수 = count if count is not None else 1

    if 실제횟수 == 0:
        raise ValueError(
            "'앞' 을 찾지 못했습니다. 공백과 들여쓰기까지 똑같아야 합니다. "
            "열무로 실제 내용을 다시 보고 오세요."
        )
    if 실제횟수 != 기대횟수:
        raise ValueError(
            f"'앞' 이 {실제횟수}군데 나옵니다(하나만 있어야 합니다). "
            f"위아래 줄을 더 붙여 하나만 걸리게 하거나 \"번\": {실제횟수} 를 넣으세요."
        )

    백업 = _백업(대상)
    바뀐본문 = 본문.replace(old, new)
    대상.write_text(바뀐본문, encoding="utf-8", newline="\n")

    # 바뀐 줄 번호를 알려주면 GPT 가 확인하기 쉽다
    바뀐줄 = []
    앞줄들, 뒷줄들 = 본문.splitlines(), 바뀐본문.splitlines()
    for i in range(min(len(앞줄들), len(뒷줄들))):
        if 앞줄들[i] != 뒷줄들[i]:
            바뀐줄.append(i + 1)
            if len(바뀐줄) >= 20:
                break

    더함, 뺌 = _줄증감(본문, 바뀐본문)
    return {
        "path": sandbox.표시경로(대상),
        "replaced": 실제횟수,
        "changed_lines": 바뀐줄,
        "total_lines": len(뒷줄들),
        "더한줄": 더함,
        "뺀줄": 뺌,
        "backup": 백업,
        "_차이": _차이(본문, 바뀐본문),
    }


def delete_file(path: str, **_):
    """실제로 지우지 않고 휴지통 폴더로 옮긴다."""
    대상 = sandbox.경로검증(path, 쓰기=True)
    if not 대상.exists():
        raise FileNotFoundError(f"파일이 없습니다: {대상}")
    if 대상.is_dir():
        raise IsADirectoryError("칸은 안 됩니다. 하나씩만 됩니다.")

    도장 = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    상대 = sandbox.보관속경로(대상)
    옮길곳 = sandbox.휴지통칸() / 도장 / 상대
    옮길곳.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(대상), str(옮길곳))

    return {
        "path": sandbox.표시경로(대상),
        "action": "휴지통으로 이동(실제 삭제 아님)",
        "trash": str(옮길곳),
    }


def create_dir(path: str, **_):
    """폴더를 만든다."""
    대상 = sandbox.경로검증(path, 쓰기=True)
    이미있음 = 대상.exists()
    대상.mkdir(parents=True, exist_ok=True)
    return {
        "path": sandbox.표시경로(대상),
        "action": "이미 있음" if 이미있음 else "만듦",
    }


등록된도구 = {
    "write_file": write_file,
    "replace_text": replace_text,
    "delete_file": delete_file,
    "create_dir": create_dir,
}
