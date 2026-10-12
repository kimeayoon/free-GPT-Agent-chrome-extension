# -*- coding: utf-8 -*-
"""릴리스에 올릴 두 파일을 만든다 — 서버 설치(cmd) 하나, 크롬 확장(zip) 하나.

서버 설치: 더블클릭하면 파이썬을 찾아(없으면 winget 으로 설치를 시도) 안에 든 설치 프로그램(설치.py)을 돌린다.
확장 zip : 풀어서 chrome://extensions 의 '압축해제된 확장 프로그램을 로드' 로 고른다. 설치 파일과 같은 폴더에 두면 설치가 알아서 풀어 준다.
버전은 서버/서버.py 의 버전 한 숫자를 쓴다(확장 manifest · protocol 과 다르면 멈춘다).
사용자(만든 사람)의 개인 자료는 넣지 않는다: 대화 기록(서버/방) · 설정.json · 권한 · 허용 사이트 · 로그 · 작업기록 · 백업.
코드와 확장과 지침 문서만 넣는다. 설정은 템플릿을 넣고 받는 사람 PC 에서 만든다.

  만들기:  python -X utf8 도구/배포/만들기.py
  결과:    도구/배포/결과/GPT-LocalAgent-Server-Setup-<버전>.cmd · GPT-LocalAgent-Extension-<버전>.zip
"""

import base64
import io
import json
import re
import sys
import zipfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent.parent
이칸 = Path(__file__).resolve().parent
결과칸 = 이칸 / "결과"
확장폴더이름 = "GPT-LocalAgent-Extension"      # zip 안의 맨 위 폴더(풀면 이 이름의 폴더 하나가 나온다)

서버제외 = {"__pycache__"}
# 서버 칸 안에서 코드가 아닌 것(사용자 자료)은 이름으로 막는다. 코드는 *.py 만 넣는다.
문서목록 = ("프로토콜.md", "에이전트_설명서.md", "도구_첫사용_안내.md")


def 지침뽑기() -> str:
    """프로토콜.md 의 울타리(```) 안쪽만 — ChatGPT 프로젝트 지침 칸에 그대로 붙인다."""
    줄들 = (뿌리 / "문서" / "프로토콜.md").read_text(encoding="utf-8").splitlines()
    울타리 = [i for i, 줄 in enumerate(줄들) if 줄.strip() == "```"]
    if len(울타리) != 2:
        raise SystemExit(f"프로토콜.md 의 울타리가 2개여야 합니다(지금 {len(울타리)}개).")
    글 = "\n".join(줄들[울타리[0] + 1:울타리[1]]).strip() + "\n"
    if len(글) > 8000:
        raise SystemExit(f"지침이 8000자를 넘습니다({len(글)}자). ChatGPT 가 못 받습니다.")
    return 글


def 설정템플릿() -> str:
    원 = json.loads((뿌리 / "서버" / "설정.json").read_text(encoding="utf-8"))
    원["루트"] = "{{HOME}}"
    원["쓰기루트"] = "{{HOME}}"
    원["기준폴더"] = "{{INSTALL}}/workspace"
    원["백업폴더"] = "{{INSTALL}}/_archive/백업"
    원["휴지통폴더"] = "{{INSTALL}}/_archive/휴지통"
    원["설치폴더"] = "{{INSTALL}}/설치된것"
    return json.dumps(원, ensure_ascii=False, indent=2) + "\n"


def 파일모으기() -> list:
    """(압축 안 이름, 읽을 자리). 코드만."""
    나온 = []
    for 파일 in sorted((뿌리 / "서버").glob("*.py")):
        나온.append((f"서버/{파일.name}", 파일))
    호스트 = 뿌리 / "서버" / "자동켜기" / "agent_host.py"
    if 호스트.exists():
        나온.append(("서버/자동켜기/agent_host.py", 호스트))
    for 이름 in 문서목록:
        나온.append((f"문서/{이름}", 뿌리 / "문서" / 이름))
    나온.append(("도구/자동켜기등록.py", 뿌리 / "도구" / "자동켜기등록.py"))
    나온.append(("도구/서버 켜기.bat", 뿌리 / "도구" / "서버 켜기.bat"))
    나온.append(("도구/설치.py", 이칸 / "설치.py"))
    나온.append(("_설치.py", 이칸 / "설치.py"))
    return 나온


def 확장모으기() -> list:
    return [(파일.name, 파일) for 파일 in sorted((뿌리 / "확장").iterdir()) if 파일.is_file()]


def 버전읽기() -> str:
    """서버 · 확장 manifest · 확장 protocol 의 버전이 같은지 보고 그 숫자를 돌려준다."""
    서버 = re.search(r'^버전 = "([\d.]+)"', (뿌리 / "서버" / "서버.py").read_text(encoding="utf-8"), re.M).group(1)
    확장 = json.loads((뿌리 / "확장" / "manifest.json").read_text(encoding="utf-8"))["version"]
    규약 = re.search(r"const 빌드 = '([\d.]+)'", (뿌리 / "확장" / "protocol.js").read_text(encoding="utf-8")).group(1)
    if not (서버 == 확장 == 규약):
        raise SystemExit(f"버전이 서로 다릅니다 — 서버 {서버} · manifest {확장} · protocol {규약}. 한 숫자로 맞추세요.")
    if not re.fullmatch(r"\d+\.\d+\.\d+", 서버):
        raise SystemExit(f"버전은 세 자리(주.부.수)여야 합니다: {서버}")
    return 서버


def 개인자료검사(이름들: list, 글들: dict) -> list:
    """들어가면 안 되는 것이 섞였는지 본다. 문제 목록을 돌려준다."""
    문제 = []
    막을이름 = ("방/", "방목록", "설정.json", "권한.json", "허용사이트", "실행로그", "에러로그", "서버출력", "켜기일지", "뒤뜰/", ".env", "대화")
    for 이름 in 이름들:
        if any(막 in 이름 for 막 in 막을이름):
            문제.append(f"들어가면 안 되는 이름: {이름}")
    for 이름, 글 in 글들.items():
        for 낱말 in 개인글만들기():
            if 낱말 in 글:
                문제.append(f"{이름} 에 '{낱말}' 가 들어 있음")
    return 문제


def 개인글만들기() -> list:
    """이 PC 의 사용자 이름과 이 프로젝트 · 사용자 폴더 경로. 이 글이 파일에 들어 있으면 개인 자료가 섞인 것이다.
    (이름을 코드에 박아 두지 않는다 — 박으면 이 파일 자체가 개인 자료가 된다.)"""
    import os
    글 = {str(뿌리), str(뿌리).replace(chr(92), "/"), str(Path.home()), str(Path.home()).replace(chr(92), "/")}
    for 이름 in (os.environ.get("USERNAME"), os.environ.get("USER"), Path.home().name):
        if 이름 and len(이름) >= 4:
            글.add(이름)
    return sorted(g for g in 글 if g)


def main():
    결과칸.mkdir(parents=True, exist_ok=True)
    버전 = 버전읽기()
    결과파일 = 결과칸 / f"GPT-LocalAgent-Server-Setup-{버전}.cmd"
    확장파일 = 결과칸 / f"GPT-LocalAgent-Extension-{버전}.zip"
    확장목록 = 확장모으기()
    목록 = 파일모으기()
    지침 = 지침뽑기()
    템플릿 = 설정템플릿()

    이름들 = [이름 for 이름, _ in 목록] + ["설정_템플릿.json", "지침_붙여넣기.txt"] + [f"확장/{이름}" for 이름, _ in 확장목록]
    글들 = {}
    for 이름, 자리 in 목록 + [(f"확장/{이름}", 자리) for 이름, 자리 in 확장목록]:
        if 자리.suffix in (".py", ".js", ".json", ".html", ".md", ".bat"):
            글들[이름] = 자리.read_text(encoding="utf-8", errors="replace")
    글들["설정_템플릿.json"] = 템플릿
    문제 = 개인자료검사(이름들, {k: v for k, v in 글들.items() if k not in ("문서/프로토콜.md", "문서/에이전트_설명서.md", "문서/도구_첫사용_안내.md", "도구/자동켜기등록.py")})
    if 문제:
        print("✗ 개인 자료가 섞일 수 있어 만들지 않습니다:")
        for 줄 in 문제:
            print("  -", 줄)
        raise SystemExit(1)

    메모리 = io.BytesIO()
    with zipfile.ZipFile(메모리, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as 압축:
        for 이름, 자리 in 목록:
            압축.write(자리, 이름)
        압축.writestr("설정_템플릿.json", 템플릿)
        압축.writestr("지침_붙여넣기.txt", 지침)
    b64 = base64.b64encode(메모리.getvalue()).decode("ascii")
    줄들 = [b64[i:i + 76] for i in range(0, len(b64), 76)]

    머리 = (이칸 / "부트머리.cmd").read_text(encoding="utf-8").replace("\r\n", "\n")
    본문 = 머리.rstrip("\n") + "\n#PAYLOAD\n" + "\n".join(줄들) + "\n"
    결과파일.write_bytes(본문.replace("\n", "\r\n").encode("utf-8"))

    with zipfile.ZipFile(확장파일, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as 압축:
        for 이름, 자리 in 확장목록:
            압축.write(자리, f"{확장폴더이름}/{이름}")

    print(f"✓ {결과파일}")
    print(f"  서버 설치: 파일 {len(목록)}개 · 한 파일 {결과파일.stat().st_size // 1024}KB · 지침 {len(지침)}자")
    print(f"✓ {확장파일}")
    print(f"  확장: 파일 {len(확장목록)}개 · {확장파일.stat().st_size // 1024}KB · 버전 {버전}")


if __name__ == "__main__":
    sys.exit(main())
