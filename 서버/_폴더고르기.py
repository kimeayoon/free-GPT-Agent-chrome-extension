
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
