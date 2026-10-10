# -*- coding: utf-8 -*-
"""1차 도구 모음 — 읽기 전용(read_file / list_files / search_files)."""

import os
from pathlib import Path

import sandbox

읽기최대 = sandbox.설정["읽기최대바이트"]


def _텍스트읽기(경로: Path) -> str:
    """UTF-8 우선, 실패하면 cp949로 재시도."""
    바이트 = 경로.read_bytes()
    if len(바이트) > 읽기최대:
        raise ValueError(
            f"파일이 너무 큽니다({len(바이트):,}바이트 > {읽기최대:,}). "
            f"'첫줄'/'끝줄' 로 나눠 보세요."
        )
    for 인코딩 in ("utf-8", "cp949"):
        try:
            return 바이트.decode(인코딩)
        except UnicodeDecodeError:
            continue
    raise ValueError("텍스트 파일이 아닙니다(바이너리로 보임).")


def read_file(path: str, start_line: int | None = None, end_line: int | None = None, **_):
    """파일 내용을 읽는다. 줄 범위를 주면 그 부분만 읽는다(1부터 시작, end 포함)."""
    대상 = sandbox.경로검증(path)
    if not 대상.exists():
        raise FileNotFoundError(f"파일이 없습니다: {대상}")
    if 대상.is_dir():
        raise IsADirectoryError(f"칸입니다. 가지를 쓰세요: {대상}")

    본문 = _텍스트읽기(대상)
    줄들 = 본문.splitlines()
    전체줄수 = len(줄들)

    시작 = max(1, start_line) if start_line else 1
    끝 = min(전체줄수, end_line) if end_line else 전체줄수
    잘림 = (시작 != 1) or (끝 != 전체줄수)
    조각 = 줄들[시작 - 1 : 끝]

    return {
        "path": sandbox.표시경로(대상),
        "total_lines": 전체줄수,
        "start_line": 시작,
        "end_line": 끝,
        "truncated": 잘림,
        "content": "\n".join(조각),
    }


def list_files(path: str = ".", depth: int = 2, max_entries: int = 400, **_):
    """폴더 구조를 트리 문자열로 돌려준다."""
    뿌리 = sandbox.경로검증(path)
    if not 뿌리.exists():
        raise FileNotFoundError(f"폴더가 없습니다: {뿌리}")
    if not 뿌리.is_dir():
        raise NotADirectoryError(f"폴더가 아닙니다: {뿌리}")

    줄들: list[str] = [sandbox.표시경로(뿌리) + "/"]
    개수 = 0
    잘림 = False

    def 훑기(현재: Path, 현재깊이: int, 들여쓰기: str):
        nonlocal 개수, 잘림
        if 현재깊이 > depth or 잘림:
            return
        try:
            항목들 = sorted(
                현재.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except PermissionError:
            줄들.append(들여쓰기 + "└─ (접근 거부)")
            return

        for i, 항목 in enumerate(항목들):
            if 개수 >= max_entries:
                잘림 = True
                return
            if 항목.is_dir() and sandbox.제외폴더인가(항목.name):
                continue
            마지막 = i == len(항목들) - 1
            가지 = "└─ " if 마지막 else "├─ "
            if 항목.is_dir():
                줄들.append(들여쓰기 + 가지 + 항목.name + "/")
                개수 += 1
                훑기(항목, 현재깊이 + 1, 들여쓰기 + ("   " if 마지막 else "│  "))
            else:
                try:
                    크기 = 항목.stat().st_size
                except OSError:
                    크기 = -1
                줄들.append(f"{들여쓰기}{가지}{항목.name}  ({크기:,}B)")
                개수 += 1

    훑기(뿌리, 1, "")
    return {
        "path": sandbox.표시경로(뿌리),
        "entries": 개수,
        "truncated": 잘림,
        "tree": "\n".join(줄들),
    }


def search_files(query: str, path: str = ".", max_results: int = 40,
                 extensions: list | None = None, **_):
    """폴더 안 텍스트 파일에서 문자열을 찾는다(대소문자 무시)."""
    뿌리 = sandbox.경로검증(path)
    찾을말 = query.lower()
    확장자 = {e.lower() if e.startswith(".") else "." + e.lower()
              for e in (extensions or [])}
    결과 = []
    잘림 = False

    for 폴더, 하위폴더들, 파일들 in os.walk(뿌리):
        하위폴더들[:] = [d for d in 하위폴더들 if not sandbox.제외폴더인가(d)]
        for 파일명 in 파일들:
            if 확장자 and Path(파일명).suffix.lower() not in 확장자:
                continue
            전체 = Path(폴더) / 파일명
            try:
                sandbox.경로검증(str(전체))
                if 전체.stat().st_size > 읽기최대:
                    continue
                본문 = _텍스트읽기(전체)
            except Exception:
                continue
            for 번호, 줄 in enumerate(본문.splitlines(), 1):
                if 찾을말 in 줄.lower():
                    if len(결과) >= max_results:
                        잘림 = True
                        break
                    결과.append({
                        "path": sandbox.표시경로(전체),
                        "line": 번호,
                        "text": 줄.strip()[:200],
                    })
            if 잘림:
                break
        if 잘림:
            break

    return {"query": query, "count": len(결과), "truncated": 잘림, "matches": 결과}


등록된도구 = {
    "read_file": read_file,
    "list_files": list_files,
    "search_files": search_files,
}
