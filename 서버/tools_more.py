# -*- coding: utf-8 -*-
"""손이 모자라던 것들 — 갓 · 쑥 · 버섯.

  갓   : 옮기기 · 이름 바꾸기 · 베끼기
  쑥   : 파일 끝에 이어 붙이기
  버섯 : 글이 아닌 파일의 속내 보기 (그림 크기, 꾸러미 안 목록 …)

여태 이게 없어서 이름 하나 바꾸려고 상추로 통째로 쓰고 시금치로 치우는
먼 길을 돌아야 했다. 로그 한 줄 더하려고 파일 전체를 다시 쓰기도 했다.
"""

import shutil
import struct
import zipfile
from pathlib import Path

import sandbox
import tools_edit

# 글로 읽을 수 없는 파일에서 앞머리를 보고 무엇인지 알아내는 표
생김새 = [
    (b"\x89PNG\r\n\x1a\n", "PNG 그림"),
    (b"\xff\xd8\xff", "JPEG 그림"),
    (b"GIF8", "GIF 그림"),
    (b"%PDF", "PDF 문서"),
    (b"PK\x03\x04", "압축 꾸러미 (zip · whl · xlsx …)"),
    (b"\x1f\x8b", "gzip 압축"),
    (b"MZ", "윈도우 실행 파일"),
    (b"\x7fELF", "리눅스 실행 파일"),
    (b"PK\x05\x06", "빈 압축 꾸러미"),
    (b"\x80\x02", "파이썬 pickle (체크포인트일 수 있음)"),
]


# ── 갓 : 옮기기 · 이름 바꾸기 · 베끼기 ─────────────────────────

def move_file(path: str, dest: str, action: str = "옮기기", **_):
    """파일이나 칸을 옮기거나 이름을 바꾸거나 베낀다."""
    짓 = (action or "옮기기").strip()
    if 짓 not in ("옮기기", "베끼기"):
        raise ValueError("짓 은 '옮기기' 또는 '베끼기' 입니다.")

    원본 = sandbox.경로검증(path)
    if not 원본.exists():
        raise FileNotFoundError(f"그런 자리가 없습니다: {원본}")

    # 옮기면 원본이 사라지므로 원본 쪽도 쓰기 검사를 받는다
    if 짓 == "옮기기":
        sandbox.경로검증(path, 쓰기=True)
    대상 = sandbox.경로검증(dest, 쓰기=True)

    if 대상.exists():
        raise ValueError(
            f"그 자리에 이미 있습니다: {sandbox.표시경로(대상)}. "
            "덮어쓰지 않았습니다. 다른 이름을 고르거나 먼저 치우세요."
        )

    대상.parent.mkdir(parents=True, exist_ok=True)

    if 짓 == "베끼기":
        if 원본.is_dir():
            shutil.copytree(원본, 대상)
        else:
            shutil.copy2(원본, 대상)
    else:
        shutil.move(str(원본), str(대상))

    return {
        "path": sandbox.표시경로(원본),
        "간곳": sandbox.표시경로(대상),
        "action": 짓,
        "칸인가": 대상.is_dir(),
    }


# ── 쑥 : 이어 붙이기 ───────────────────────────────────────────

def append_file(path: str, content: str, **_):
    """파일 끝에 글을 이어 붙인다. 없으면 새로 만든다."""
    대상 = sandbox.경로검증(path, 쓰기=True)
    글 = content if content is not None else ""

    있던크기 = 대상.stat().st_size if 대상.exists() else 0
    if 있던크기 + len(글.encode("utf-8")) > sandbox.설정["쓰기최대바이트"]:
        raise ValueError(
            f"파일이 너무 커집니다(최대 {sandbox.설정['쓰기최대바이트']:,} 바이트)."
        )

    대상.parent.mkdir(parents=True, exist_ok=True)

    # 앞 글이 줄바꿈으로 안 끝났으면 한 줄 띄우고 붙인다
    앞에줄바꿈 = ""
    if 있던크기:
        try:
            with open(대상, "rb") as f:
                f.seek(-1, 2)
                if f.read(1) not in (b"\n", b"\r"):
                    앞에줄바꿈 = "\n"
        except OSError:
            pass

    with open(대상, "a", encoding="utf-8", newline="") as f:
        f.write(앞에줄바꿈 + 글)

    새크기 = 대상.stat().st_size
    결과 = {
        "path": sandbox.표시경로(대상),
        "action": "이어붙임",
        "bytes": 새크기,
        "더한줄": len(글.splitlines()),
        "늘어난크기": 새크기 - 있던크기,
    }
    if sandbox.비밀파일인가(대상):
        결과["안내"] = "비밀 파일입니다. 덧붙이기만 되고 읽을 수 없습니다. 값이 맞는지는 사용자가 직접 확인하게 하세요."
    return 결과


# ── 버섯 : 글 아닌 파일 들여다보기 ─────────────────────────────

def _png크기(머리: bytes):
    if len(머리) >= 24 and 머리.startswith(b"\x89PNG"):
        너비, 높이 = struct.unpack(">II", 머리[16:24])
        return f"{너비}×{높이}"
    return ""


def _gif크기(머리: bytes):
    if len(머리) >= 10 and 머리.startswith(b"GIF8"):
        너비, 높이 = struct.unpack("<HH", 머리[6:10])
        return f"{너비}×{높이}"
    return ""


def file_info(path: str, max_results: int = 20, **_):
    """파일이 무엇인지, 얼마나 큰지, 속에 무엇이 들었는지 본다."""
    대상 = sandbox.경로검증(path)
    if not 대상.exists():
        raise FileNotFoundError(f"그런 자리가 없습니다: {대상}")

    if 대상.is_dir():
        # 개수만 주면 GPT 가 폴더 이름을 모르고 '이름 목록이 생략됐다' 며 멈췄다(2026-10-04). 가지와 같은 거름(탐색 제외 폴더)으로 이름도 준다
        것들 = sorted(대상.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        보일것 = [p for p in 것들 if not (p.is_dir() and sandbox.제외폴더인가(p.name))]
        한도 = max(1, min(int(max_results or 20), 200))
        return {
            "path": sandbox.표시경로(대상),
            "무엇": "칸(폴더)",
            "entries": len(것들),
            "속개수": len(보일것),
            "속목록": [p.name + ("/" if p.is_dir() else "") for p in 보일것[:한도]],
        }

    크기 = 대상.stat().st_size
    with open(대상, "rb") as f:
        머리 = f.read(32)

    무엇 = "알 수 없음"
    for 앞머리, 이름 in 생김새:
        if 머리.startswith(앞머리):
            무엇 = 이름
            break
    else:
        try:
            머리.decode("utf-8")
            무엇 = "글 파일 — 열무로 그냥 읽으세요"
        except UnicodeDecodeError:
            pass

    답 = {
        "path": sandbox.표시경로(대상),
        "무엇": 무엇,
        "bytes": 크기,
        "앞머리": 머리[:16].hex(" "),
    }

    그림크기 = _png크기(머리) or _gif크기(머리)
    if 그림크기:
        답["그림크기"] = 그림크기

    # 압축 꾸러미면 안에 무엇이 들었는지 몇 개만 보여준다
    if 머리.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(대상) as z:
                이름들 = z.namelist()
            답["속개수"] = len(이름들)
            답["속목록"] = 이름들[:max(1, min(int(max_results or 20), 200))]
        except (OSError, zipfile.BadZipFile):
            답["속목록"] = ["(열지 못했습니다)"]

    답["안내"] = "글이 아닌 파일은 내용을 그대로 보여줄 수 없습니다. 크기와 생김새만 봅니다."
    return 답


등록된도구 = {
    "move_file": move_file,
    "append_file": append_file,
    "file_info": file_info,
}
