# -*- coding: utf-8 -*-
"""윈도우 폴더 선택창.

확장(브라우저)은 보안 때문에 폴더 선택창을 못 띄운다.
하지만 서버는 윈도우에서 그냥 도는 프로그램이라 띄울 수 있다.

창은 따로 띄운 프로세스에서 연다. 서버 안에서 직접 띄우면
여러 요청이 겹칠 때 얼어붙는다.
"""

import subprocess
import sys
from pathlib import Path

# 따로 돌릴 작은 프로그램. 고른 자리를 한 줄로 찍고 끝난다.
_고르기코드 = r"""
import sys
import tkinter as tk
from tkinter import filedialog

# 창을 띄우는 쪽은 서버인데 사람이 보고 있는 것은 브라우저다.
# 그냥 띄우면 브라우저 뒤에 깔려서 '아무 일도 안 일어난 것' 처럼 보인다.
# 그래서 ① 늘 맨 위 ② 그 창을 주인으로 삼아 고르기 창을 연다 ③ 윈도우에게
# 앞으로 내달라고 한 번 더 부탁한다.
뿌리 = tk.Tk()
뿌리.withdraw()
뿌리.attributes("-topmost", True)
뿌리.update()

try:
    import ctypes
    손잡이 = ctypes.windll.user32.GetForegroundWindow()
    ctypes.windll.user32.SetForegroundWindow(뿌리.winfo_id())
except Exception:
    pass   # 윈도우가 아니거나 막혀 있으면 그냥 넘어간다

고른것 = filedialog.askdirectory(
    parent=뿌리,
    title="일할 폴더를 고르세요 (새 폴더도 만들 수 있습니다)",
    initialdir=sys.argv[1] if len(sys.argv) > 1 else "/",
    mustexist=False,
)
뿌리.destroy()
sys.stdout.write(고른것 or "")
"""


def 폴더고르기(처음자리: str = "", 기다림초: int = 300) -> dict:
    """윈도우 폴더 선택창을 띄우고 고른 자리를 돌려준다."""
    임시 = Path(__file__).with_name("_폴더고르기.py")
    임시.write_text(_고르기코드, encoding="utf-8")

    try:
        끝 = subprocess.run(
            [sys.executable, str(임시), 처음자리 or ""],
            capture_output=True,
            timeout=기다림초,
            text=False,
        )
    except subprocess.TimeoutExpired:
        return {"고름": False, "이유": "너무 오래 기다려서 닫았습니다."}
    except OSError as e:
        return {"고름": False, "이유": f"창을 못 띄웠습니다: {e}"}

    if 끝.returncode != 0:
        탈 = (끝.stderr or b"").decode("utf-8", errors="replace").strip().splitlines()
        return {"고름": False, "이유": "폴더 선택창을 못 띄웠습니다: " + (탈[-1][:240] if 탈 else "GUI 사용 불가")}

    고른것 = (끝.stdout or b"").decode("utf-8", errors="replace").strip()
    if not 고른것:
        return {"고름": False, "이유": "고르지 않고 닫았습니다."}

    자리 = Path(고른것)
    if not 자리.exists():
        # 선택창에서 새로 만들기를 눌렀는데 실제로는 안 만들어진 경우
        try:
            자리.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return {"고름": False, "이유": f"그 자리를 만들 수 없습니다: {e}"}

    return {"고름": True, "밭": str(자리), "이름": 자리.name or str(자리)}
