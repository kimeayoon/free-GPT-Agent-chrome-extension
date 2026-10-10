# -*- coding: utf-8 -*-
"""윈도우 창 조회 · 화면 잡기 · 키보드/마우스 보내기의 바닥 층(ctypes, 설치할 것 없음).

눈(오이)과 손(마늘)이 쓴다. 시험은 이 모듈의 함수를 가짜로 바꿔 끼운다 — 시험에서 진짜 입력이 나가면 안 된다.
윈도우 전용이다. 다른 운영체제에서는 쓰는 순간 ValueError 로 알린다.
"""

import ctypes
import sys
from ctypes import wintypes

_DPI맞춤 = False

# 마우스 단추 · 휠
_마우스플래그 = {
    ("왼", "누름"): 0x0002, ("왼", "뗌"): 0x0004,
    ("오른", "누름"): 0x0008, ("오른", "뗌"): 0x0010,
    ("가운데", "누름"): 0x0020, ("가운데", "뗌"): 0x0040,
}
_이동 = 0x0001
_휠 = 0x0800
_절대 = 0x8000
_가상화면 = 0x4000

# 이름으로 부르는 키 → 가상키 코드
키이름표 = {
    "enter": 0x0D, "엔터": 0x0D, "esc": 0x1B, "escape": 0x1B, "space": 0x20, "스페이스": 0x20,
    "tab": 0x09, "탭": 0x09, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "shift": 0x10, "ctrl": 0x11, "control": 0x11, "alt": 0x12, "win": 0x5B,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22, "insert": 0x2D,
}
for _i in range(1, 13):
    키이름표["f%d" % _i] = 0x6F + _i
for _c in "abcdefghijklmnopqrstuvwxyz":
    키이름표[_c] = ord(_c.upper())
for _d in "0123456789":
    키이름표[_d] = ord(_d)


def 키코드(이름: str) -> int:
    코드 = 키이름표.get(str(이름).strip().lower())
    if 코드 is None:
        raise ValueError(f"모르는 키 이름입니다: '{이름}'. 영문 한 글자 · 숫자 · enter esc space tab shift ctrl alt left up right down f1~f12 중에서 쓰세요.")
    return 코드


def _윈도우만():
    if sys.platform != "win32":
        raise ValueError("화면 보기·키보드 마우스는 윈도우에서만 됩니다.")


def _선명하게():
    """화면 좌표를 실제 픽셀로 쓰게 한다(배율 125% 같은 화면에서 어긋나지 않게)."""
    global _DPI맞춤
    if _DPI맞춤:
        return
    _DPI맞춤 = True
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def 가상화면() -> tuple:
    """(왼, 위, 가로, 세로) — 모니터가 여럿이면 전부를 아우르는 네모."""
    _윈도우만()
    _선명하게()
    u = ctypes.windll.user32
    return (u.GetSystemMetrics(76), u.GetSystemMetrics(77), u.GetSystemMetrics(78), u.GetSystemMetrics(79))


def _네모(창) -> tuple:
    r = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(창, ctypes.byref(r))
    try:       # 그림자를 뺀 진짜 테두리
        e = wintypes.RECT()
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(창, 9, ctypes.byref(e), ctypes.sizeof(e)) == 0:
            r = e
    except Exception:
        pass
    return (r.left, r.top, r.right, r.bottom)


def _제목(창) -> str:
    u = ctypes.windll.user32
    길이 = u.GetWindowTextLengthW(창)
    if 길이 <= 0:
        return ""
    글 = ctypes.create_unicode_buffer(길이 + 1)
    u.GetWindowTextW(창, 글, 길이 + 1)
    return 글.value


def 창들() -> list:
    """보이는 창 목록. [{핸들, 제목, 왼, 위, 오른, 아래, 앞}] — 제목이 없거나 접힌 창은 뺀다."""
    _윈도우만()
    _선명하게()
    u = ctypes.windll.user32
    앞창 = u.GetForegroundWindow()
    나온 = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _돌기(창, _):
        if not u.IsWindowVisible(창) or u.IsIconic(창):
            return True
        제목 = _제목(창)
        if not 제목.strip():
            return True
        왼, 위, 오른, 아래 = _네모(창)
        if 오른 - 왼 < 40 or 아래 - 위 < 30:
            return True
        나온.append({"핸들": int(창), "제목": 제목, "왼": 왼, "위": 위, "오른": 오른, "아래": 아래, "앞": int(창) == int(앞창 or 0)})
        return True

    u.EnumWindows(_돌기, 0)
    return 나온


def 앞창() -> dict | None:
    _윈도우만()
    _선명하게()
    u = ctypes.windll.user32
    창 = u.GetForegroundWindow()
    if not 창:
        return None
    왼, 위, 오른, 아래 = _네모(창)
    return {"핸들": int(창), "제목": _제목(창), "왼": 왼, "위": 위, "오른": 오른, "아래": 아래, "앞": True}


def 앞으로(핸들: int) -> bool:
    """그 창을 앞으로 가져온다(윈도우가 막으면 안 될 수 있다)."""
    _윈도우만()
    try:
        return bool(ctypes.windll.user32.SetForegroundWindow(int(핸들)))
    except Exception:
        return False


def 잡기(네모: tuple):
    """화면의 (왼, 위, 오른, 아래) 를 그림(Pillow Image)으로 잡는다."""
    _윈도우만()
    _선명하게()
    from PIL import ImageGrab
    return ImageGrab.grab(bbox=tuple(int(v) for v in 네모), all_screens=True)


# ── 입력 보내기 (SendInput) ─────────────────────────────────────
class _마우스(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("data", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class _키(ctypes.Structure):
    _fields_ = [("vk", wintypes.WORD), ("scan", wintypes.WORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class _합침(ctypes.Union):
    _fields_ = [("mi", _마우스), ("ki", _키)]


class _입력(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _합침)]


def _보내기(항목):
    n = ctypes.windll.user32.SendInput(1, ctypes.byref(항목), ctypes.sizeof(_입력))
    if n != 1:
        raise ValueError("입력을 보내지 못했습니다(윈도우가 막았을 수 있습니다. 관리자 권한 창에는 보낼 수 없습니다).")


def 마우스이동(x: int, y: int) -> None:
    _윈도우만()
    왼, 위, 가로, 세로 = 가상화면()
    # 절대 좌표는 0~65535 로 접어서 보낸다(모니터 여럿이면 가상 화면 전체 기준)
    nx = int((x - 왼) * 65535 / max(1, 가로 - 1))
    ny = int((y - 위) * 65535 / max(1, 세로 - 1))
    i = _입력(type=0)
    i.mi = _마우스(nx, ny, 0, _이동 | _절대 | _가상화면, 0, 0)
    _보내기(i)


def 마우스단추(단추: str, 동작: str) -> None:
    _윈도우만()
    플래그 = _마우스플래그.get((단추, 동작))
    if 플래그 is None:
        raise ValueError(f"마우스 단추는 왼·오른·가운데, 동작은 누름·뗌 입니다(받은 값: {단추}/{동작}).")
    i = _입력(type=0)
    i.mi = _마우스(0, 0, 0, 플래그, 0, 0)
    _보내기(i)


def 휠(양: int) -> None:
    _윈도우만()
    i = _입력(type=0)
    i.mi = _마우스(0, 0, int(양) * 120 & 0xFFFFFFFF, _휠, 0, 0)
    _보내기(i)


def 키(코드: int, 동작: str) -> None:
    _윈도우만()
    i = _입력(type=1)
    i.ki = _키(int(코드), 0, 0 if 동작 == "누름" else 0x0002, 0, 0)
    _보내기(i)


def 글자(글: str) -> None:
    """글자를 그대로 친다(한글 포함, 키 배열과 상관없이)."""
    _윈도우만()
    조각 = 글.encode("utf-16-le")
    for k in range(0, len(조각), 2):       # 이모지처럼 두 칸을 쓰는 글자도 UTF-16 로 나눠 보낸다
        단위 = int.from_bytes(조각[k:k + 2], "little")
        for 동작 in (0x0004, 0x0004 | 0x0002):
            i = _입력(type=1)
            i.ki = _키(0, 단위, 동작, 0, 0)
            _보내기(i)
