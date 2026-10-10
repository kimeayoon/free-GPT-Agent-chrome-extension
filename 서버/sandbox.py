# -*- coding: utf-8 -*-
"""샌드박스 경로 검증 — 루트 밖 접근과 민감 파일 접근을 막는다."""

import fnmatch
import json
import os
from pathlib import Path

설정경로 = Path(__file__).with_name("설정.json")


class 보안오류(Exception):
    """샌드박스 규칙 위반."""


def 설정읽기() -> dict:
    with open(설정경로, "r", encoding="utf-8") as f:
        값 = json.load(f)
    if os.name != "nt":
        # 기본은 이 프로젝트만. 등록할 때 --workspace로 고른 폴더 하나만 대신 허용한다.
        루트 = Path(os.environ.get("LOCAL_AGENT_WORKSPACE", 설정경로.parent.parent)).resolve()
        if not 루트.is_dir() or 루트 in (Path("/"), Path.home().resolve()):
            raise ValueError(f"작업 범위는 존재하는 프로젝트 폴더 하나여야 합니다: {루트}")
        값.update(루트=str(루트), 쓰기루트=str(루트), 기준폴더=str(루트),
                백업폴더=str(루트 / "_archive" / "백업"),
                휴지통폴더=str(루트 / "_archive" / "휴지통"))
    return 값


설정 = 설정읽기()


# 이름이 차단패턴에 걸려도 '쓰기' 는 허락하는 비밀 파일(키를 넣는 곳). 읽기는 계속 막는다 — 키가 ChatGPT 로 새지 않게.
# 비밀 키 · 비밀번호 보관 파일(*.pem · id_rsa* · *.ppk · *.kdbx)은 여기 없으므로 쓰기도 막힌다.
기본쓰기만허용 = (".env", ".env.*", "credentials.json", "token.json", "*.key")


def 쓰기만허용인가(이름: str) -> bool:
    패턴들 = 설정.get("쓰기만허용패턴", 기본쓰기만허용)
    return any(fnmatch.fnmatch(이름.lower(), str(p).lower()) for p in 패턴들)


def 비밀파일인가(대상: Path) -> bool:
    """읽기는 막고 쓰기만 되는 비밀 파일인가(이름으로 판단)."""
    이름 = 대상.name
    return any(fnmatch.fnmatch(이름.lower(), p.lower()) for p in 설정["차단패턴"]) and 쓰기만허용인가(이름)


def _정규화(p: Path) -> Path:
    """심볼릭 링크까지 풀어 실제 경로를 구한다(없는 파일도 처리)."""
    try:
        return Path(os.path.realpath(str(p)))
    except OSError:
        return p.absolute()


def 기준자리() -> Path:
    """상대 경로를 어디 기준으로 볼지.

    지금 고른 방의 폴더가 기준이다. 방을 안 골랐을 때만 설정의 기준폴더로 간다.
    이게 없으면 '밭 src▸core.py' 같은 상대 경로가 엉뚱하게 workspace 밑으로
    가서, 정작 일하는 폴더는 건드리지도 못한다.
    """
    try:
        import rooms
        밭 = rooms.지금밭()
        if 밭:
            return 밭
    except Exception:
        pass
    return Path(설정["기준폴더"])


# 에이전트가 남기는 것은 전부 일터 안 .agent 밑에 둔다.
# 백업·휴지통·받아온 것을 딴 데 두면 프로젝트를 옮길 때 짝이 끊기고,
# 프로젝트끼리 같은 이름 파일이 섞인다.
일터칸이름 = ".agent"


def 일터칸(이름: str, 설정키: str = "") -> Path:
    """일터 안의 .agent/<이름>. 일할 곳을 안 정했으면 설정에 적힌 자리로."""
    밭 = 기준자리()
    설정밭 = Path(설정["기준폴더"])
    if 밭 != 설정밭:
        return 밭 / 일터칸이름 / 이름
    if 설정키 and 설정.get(설정키):
        return Path(설정[설정키])
    return 설정밭 / 일터칸이름 / 이름


def 백업칸() -> Path:
    return 일터칸("백업", "백업폴더")


def 휴지통칸() -> Path:
    return 일터칸("휴지통", "휴지통폴더")


def 받은것칸() -> Path:
    return 일터칸("받은것", "설치폴더")


def 경로검증(입력경로: str, 쓰기: bool = False) -> Path:
    """입력 경로를 절대 경로로 바꾸고 샌드박스 규칙을 확인한다.

    - 상대 경로는 지금 고른 방의 폴더 기준으로 해석(없으면 기준폴더)
    - 읽기는 '루트', 쓰기는 '쓰기루트' 하위여야 함
    - 파일명이 '차단패턴'에 걸리면 거부
    """
    if not 입력경로 or not str(입력경로).strip():
        raise 보안오류("경로가 비어 있습니다.")

    # 확장이 쓰는 자리 구분 기호(▸)도 받아준다
    다듬은것 = str(입력경로).strip().replace("▸", os.sep)
    원본 = Path(다듬은것.replace("\\", os.sep).replace("/", os.sep))

    if 원본.is_absolute():
        대상 = 원본
    else:
        대상 = 기준자리() / 원본

    대상 = _정규화(대상)

    # 읽기는 루트(G:) 어디든 된다. 쓰기는 고른 프로젝트 안쪽만 된다.
    루트 = _정규화(Path(설정["루트"]))
    try:
        대상.relative_to(루트)
    except ValueError:
        raise 보안오류(f"정해진 범위 밖입니다: {대상}")

    if 쓰기:
        import rooms   # 순환 참조를 피하려고 여기서 불러온다

        지금 = rooms.지금밭()
        if 지금 is None:
            raise 보안오류(
                "아직 일할 방이 없거나, 방에 폴더가 정해지지 않았습니다. "
                "사용자에게 창에서 폴더를 고르고 방을 만들라고 말하고 멈추세요."
            )

        if not rooms.쓸수있나(대상):
            폴더 = rooms.요청쌓기(대상)
            raise 보안오류(
                f"여기는 읽기만 됩니다: {폴더} / "
                f"지금 고쳐도 되는 곳은 '{지금.name}' 안쪽뿐입니다. "
                f"사용자에게 이렇게 말하고 멈추세요 — "
                f"'{폴더} 를 고쳐야 하는데 허락이 필요합니다. "
                f"창에 뜬 물음에서 허용을 눌러 주세요.'"
            )

    이름 = 대상.name
    for 패턴 in 설정["차단패턴"]:
        if fnmatch.fnmatch(이름.lower(), 패턴.lower()):
            if 쓰기만허용인가(이름):
                if 쓰기:
                    continue        # 비밀 파일은 쓰기만 된다 — 사용자가 키를 넣기 편하게
                raise 보안오류(f"비밀 파일입니다: {이름} — 쓰기만 되고 읽을 수 없습니다. 값은 사용자가 직접 채우게 하세요.")
            raise 보안오류(f"손댈 수 없는 이름입니다: {이름}")

    # 경로 중간에 .ssh 같은 민감 폴더가 끼어 있는 경우도 차단
    조각들 = {c.lower() for c in 대상.parts}
    for 위험폴더 in (".ssh", ".gnupg", ".aws", ".docker"):
        if 위험폴더 in 조각들:
            raise 보안오류("손댈 수 없는 자리입니다.")

    # 백업/휴지통 자체를 건드리는 건 막는다(되돌릴 길을 지켜야 함)
    if 쓰기:
        보호자리 = [백업칸(), 휴지통칸(),
                  Path(설정.get("백업폴더", "")), Path(설정.get("휴지통폴더", ""))]
        for 보호 in 보호자리:
            if not str(보호).strip():
                continue
            try:
                대상.relative_to(_정규화(보호))
                raise 보안오류("보관해 둔 자리는 손댈 수 없습니다.")
            except ValueError:
                pass

    return 대상


def 보관속경로(대상: Path) -> Path:
    """보관 자리 안에서 이 파일이 놓이는 상대 경로.

    일터 안 파일이면 일터 기준으로 짧게 (src/core.py).
    일터 밖 파일이면 드라이브 문자만 떼고 구조를 그대로 살린다.
    """
    try:
        return 대상.relative_to(_정규화(기준자리()))
    except ValueError:
        return Path(*대상.parts[1:]) if 대상.drive else Path(*대상.parts)


def 제외폴더인가(이름: str) -> bool:
    return 이름 in 설정["탐색제외폴더"]


def 표시경로(p: Path) -> str:
    """지금 일하는 폴더 기준 상대 경로로 보여준다(가능하면)."""
    for 기준 in (기준자리(), Path(설정["기준폴더"])):
        try:
            return str(p.relative_to(_정규화(기준))).replace(os.sep, "/")
        except ValueError:
            continue
    return str(p)
