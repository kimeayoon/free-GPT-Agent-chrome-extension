# -*- coding: utf-8 -*-
"""명령 실행 도구 — run_command.

승인 여부(전체권한·자동·수동)는 서버의 승인 문(approval.py)이 도구를 부르기 전에 정한다. 여기서는:
  - 차단 규칙에 걸리면 실행 자체를 거부
  - 받아오기(설치)로 보이면 도토리로 가라고 돌려보냄
  - 작업 디렉토리는 샌드박스 안으로 강제
  - 타임아웃 초과 시 강제 종료
"""

import re
import subprocess

import sandbox

타임아웃기본 = sandbox.설정["명령타임아웃초"]
타임아웃최대 = sandbox.설정.get("명령타임아웃최대초", 600)
출력최대 = sandbox.설정["명령출력최대문자"]

# 받아오기·설치로 보이는 것들.
# 막는 게 아니라 '도토리로 요청하라'고 돌려보낸다.
# 받아온 것은 결국 실행되므로, 무엇을 어디서 받는지 사람이 보고 허락해야 한다.
받아오기규칙 = [
    r"\bpip3?\b[^|&]*\binstall\b",
    r"\bnpm\b[^|&]*\b(install|add)\b",
    r"\bnpx\b",
    r"\byarn\b[^|&]*\badd\b",
    r"\bpnpm\b[^|&]*\badd\b",
    r"\bgit\s+clone\b",
    r"\buv\b[^|&]*\binstall\b",
    r"\b(winget|choco|scoop)\s+install\b",
    r"\bcurl\b[^|&]*\s-[oO]\b",
    r"\bwget\b",
    r"\b(iwr|invoke-webrequest)\b[^|&]*-outfile\b",
    r"\bStart-BitsTransfer\b",
    r"\bcertutil\b[^|&]*-urlcache\b",
]
받아오기검사 = [(원문, re.compile(원문, re.IGNORECASE)) for 원문 in 받아오기규칙]

차단규칙 = [
    (원문, re.compile(원문, re.IGNORECASE))
    for 원문 in sandbox.설정["명령차단정규식"]
]


def 명령검사(명령: str):
    """차단 규칙에 걸리면 보안오류를 던진다."""
    if not 명령 or not 명령.strip():
        raise ValueError("명령이 비었습니다.")

    for 원문, 규칙 in 차단규칙:
        if 규칙.search(명령):
            raise sandbox.보안오류(
                "허락되지 않은 문장입니다. 다른 방법을 찾으세요."
            )

    for 원문, 규칙 in 받아오기검사:
        if 규칙.search(명령):
            raise sandbox.보안오류(
                "도라지로는 받아올 수 없습니다. 도토리로 요청하세요. "
                "받아온 것은 결국 돌아가기 때문에, 무엇을 어디서 받는지 "
                "사람이 보고 허락해야 합니다. "
                "예) 나물 도토리 / 무엇 mcp / 어디서 pip / 왜 짧은 이유"
            )


def _자르기(문자열: str):
    if len(문자열) <= 출력최대:
        return 문자열, False
    절반 = 출력최대 // 2
    앞 = 문자열[:절반]
    뒤 = 문자열[-절반:]
    return f"{앞}\n\n... (가운데 {len(문자열) - 출력최대:,}자 생략) ...\n\n{뒤}", True


def run_command(command: str, cwd: str = ".", timeout: int | None = None, **_):
    """셸 명령을 실행하고 출력을 돌려준다."""
    명령검사(command)

    작업폴더 = sandbox.경로검증(cwd)
    if not 작업폴더.exists() or not 작업폴더.is_dir():
        raise NotADirectoryError(f"작업 폴더가 없습니다: {작업폴더}")

    제한 = min(int(timeout or 타임아웃기본), 타임아웃최대)

    # 일터가 있으면 일터를 켠 채로 돌린다.
    # 이게 없으면 'python' 이 컴퓨터 전체의 파이썬으로 잡혀서
    # 일터에 깐 꾸러미가 하나도 안 보인다.
    import tools_venv
    환경 = tools_venv.일터환경()

    try:
        결과 = subprocess.run(
            command,
            shell=True,
            cwd=str(작업폴더),
            capture_output=True,
            timeout=제한,
            text=False,
            env=환경,
            stdin=subprocess.DEVNULL,   # 입력을 기다리다 멈추지 않게
        )
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "cwd": sandbox.표시경로(작업폴더),
            "timed_out": True,
            "exit_code": None,
            "output": f"{제한}초를 넘겨 중단했습니다. "
                      f"더 기다려야 하면 '참기' 를 올리세요(최대 {타임아웃최대}초). "
                      f"입력을 기다리는 것은 아닌지도 확인하세요.",
        }

    def 디코딩(b: bytes) -> str:
        for 인코딩 in ("utf-8", "cp949"):
            try:
                return b.decode(인코딩)
            except UnicodeDecodeError:
                continue
        return b.decode("utf-8", errors="replace")

    표준출력 = 디코딩(결과.stdout or b"")
    표준에러 = 디코딩(결과.stderr or b"")
    합친출력 = 표준출력
    if 표준에러.strip():
        합친출력 += ("\n--- stderr ---\n" if 합친출력.strip() else "") + 표준에러

    잘린출력, 잘림 = _자르기(합친출력.strip())

    return {
        "command": command,
        "cwd": sandbox.표시경로(작업폴더),
        "일터": bool(환경),
        "exit_code": 결과.returncode,
        "ok": 결과.returncode == 0,
        "timed_out": False,
        "truncated": 잘림,
        "output": 잘린출력 or "(출력 없음)",
    }


등록된도구 = {
    "run_command": run_command,
}
