# -*- coding: utf-8 -*-
"""뒤뜰에서 혼자 돌아가는 일꾼.

서버가 이 파일을 '떼어 놓은 프로세스'로 띄운다.
서버의 자식이 아니므로 서버를 껐다 켜도 하던 일은 계속 돌아간다.

하는 일은 단순하다.
  1. 칸에 있는 일.json 을 읽는다
  2. 명령을 돌리면서 나오는 글을 전부 기록.txt 에 적는다
  3. 끝나면 끝번호.txt 에 끝번호를 적는다  ← 서버는 이 파일로 '끝났구나' 를 안다

쓰는 법:  python 뒤뜰달리기.py <칸경로>
"""

import json
import subprocess
import sys
from pathlib import Path


def 달리기(칸: Path) -> int:
    일 = json.loads((칸 / "일.json").read_text(encoding="utf-8"))

    기록 = 칸 / "기록.txt"
    with open(기록, "ab", buffering=0) as 적을곳:
        try:
            끝 = subprocess.run(
                일["불"],
                shell=True,
                cwd=일["자리"],
                stdout=적을곳,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,   # 입력을 기다리다 멈추는 일이 없게
            )
            끝번호 = 끝.returncode
        except OSError as e:
            적을곳.write(f"\n[뒤뜰] 돌리지 못했습니다: {e}\n".encode("utf-8"))
            끝번호 = -1

    (칸 / "끝번호.txt").write_text(str(끝번호), encoding="utf-8")
    return 끝번호


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("칸 경로가 필요합니다.")
        raise SystemExit(2)
    raise SystemExit(달리기(Path(sys.argv[1])))
