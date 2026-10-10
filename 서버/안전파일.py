# -*- coding: utf-8 -*-
"""상태 파일을 안전하게 읽고 쓴다.

서버는 요청마다 실이 따로라, 한 실이 파일을 쓰는 도중(비운 뒤 채우기 전)에 다른 실이 읽으면
'읽기 실패 → 기본값(빈 것)' 이 돌아오고, 그 상태로 고쳐 쓰면 내용이 통째로 날아간다.
방 목록이 그렇게 사라진 적이 있다. 상태 파일은 전부 이 모듈로 읽고 쓴다.

  쓰기   : 임시 파일에 다 쓴 뒤 한 번에 바꿔 끼운다 → 읽는 쪽은 늘 온전한 파일을 보고, 쓰다 죽어도 원본이 남는다.
           (윈도우는 다른 실이 읽는 순간엔 바꿔 끼우지 못해 잠깐 뒤 다시 한다)
  읽기   : 실패하면 다시 읽는다. 끝내 안 되면 깨진 파일을 '이름.깨짐-시각' 으로 남기고 기본값을 돌려준다.
"""

import json
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

_자물쇠 = threading.RLock()


def 쓰기(경로, 글: str, newline: str | None = None) -> None:
    경로 = Path(경로)
    임시 = 경로.with_name(경로.name + ".임시")
    with _자물쇠:
        임시.write_text(글, encoding="utf-8", newline=newline)
        _바꿔끼우기(임시, 경로)


def 바이트쓰기(경로, 내용: bytes) -> None:
    경로 = Path(경로)
    임시 = 경로.with_name(경로.name + ".임시")
    with _자물쇠:
        임시.write_bytes(내용)
        _바꿔끼우기(임시, 경로)


def _바꿔끼우기(임시: Path, 경로: Path) -> None:
    for 번 in range(20):
        try:
            os.replace(임시, 경로)
            return
        except PermissionError:
            if 번 == 19:
                raise
            time.sleep(0.02 * (번 + 1))


def json쓰기(경로, 값) -> None:
    쓰기(경로, json.dumps(값, ensure_ascii=False, indent=2))


def 깨진것남기기(경로: Path) -> None:
    """깨진 파일을 증거로 남긴다. 같은 내용이 이미 남아 있으면 또 남기지 않는다(읽을 때마다 쌓이지 않게)."""
    try:
        내용 = 경로.read_bytes()
        for 옛 in 경로.parent.glob(경로.name + ".깨짐-*"):
            if 옛.stat().st_size == len(내용) and 옛.read_bytes() == 내용:
                return
        shutil.copy2(경로, 경로.with_name(경로.name + ".깨짐-" + datetime.now().strftime("%Y%m%d_%H%M%S")))
    except OSError:
        pass


def 글읽기(경로) -> str:
    """글 파일을 읽는다. 바꿔 끼우는 순간에 걸려 권한 오류가 나면 잠깐 뒤 다시 읽는다(끝내 안 되면 그 오류)."""
    경로 = Path(경로)
    for 번 in range(4):
        try:
            return 경로.read_text(encoding="utf-8")
        except PermissionError:
            if 번 == 3:
                raise
            time.sleep(0.05 * (번 + 1))
    return ""


def json읽기(경로, 기본=None, 종류=None):
    """온전한 값을 돌려준다. 파일이 없으면 기본값(처음 쓰는 것이니 빈 값이 맞다).
    읽기가 끝내 안 되거나 종류(dict/list)가 다르면 깨진 것을 남기고 기본값."""
    경로 = Path(경로)
    값 = None
    읽음 = False
    for 번 in range(4):
        if not 경로.exists():
            return 기본
        try:
            값 = json.loads(경로.read_text(encoding="utf-8"))
            읽음 = True
            break
        except (OSError, ValueError):
            time.sleep(0.05 * (번 + 1))
    if not 읽음 or (종류 is not None and not isinstance(값, 종류)):
        깨진것남기기(경로)
        return 기본
    return 값
