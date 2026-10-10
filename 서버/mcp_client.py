# -*- coding: utf-8 -*-
"""열매 — 바깥 도구(MCP 서버)에 붙어서 쓴다.

블렌더·유니티 같은 프로그램은 저마다 MCP 서버를 내놓는다.
그걸 띄워서 붙으면 그 프로그램의 기능을 그대로 쓸 수 있다.

나물을 기능 수만큼 늘리지 않는다. 창구는 '열매' 하나뿐이고,
어느 서버의 어느 기능인지는 인자로 고른다. 그래야 MCP 기능이
몇백 개가 되어도 지침이 커지지 않는다.

  나물 열매                      붙어 있는 서버 목록
  나물 열매 / 어디 blender        그 서버가 주는 기능 목록
  나물 열매 / 어디 blender / 무엇 create_cube / 값 {...}   실제로 부르기

■ 띄우는 것은 곧 남의 프로그램을 돌리는 일이다.
  그래서 새 서버를 붙일 때는 반드시 사용자 승인을 받는다(받아오기 카드와 같은 곳).

말은 JSON-RPC 2.0 을 줄 단위로 주고받는다(MCP 의 stdio 방식).
바깥 꾸러미를 쓰지 않는다 — 파이썬에 들어 있는 것만으로 된다.
"""

import json
import os
import queue
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path

import sandbox
import 안전파일

목록파일 = Path(__file__).with_name("mcp목록.json")

붙는참기 = 60      # 띄우고 인사하는 데 기다릴 시간
부르는참기 = 120   # 기능 하나 부르는 데 기다릴 시간
끄는참기 = 5       # 곱게 꺼지길 기다릴 시간

# 우리가 아는 규약 판. 최신 것을 먼저 건네고, 저쪽이 다른 걸 쓰면 맞춰 준다.
# (규약: 클라이언트는 자기가 아는 가장 최신 판을 보내야 한다)
아는판 = ["2025-03-26", "2024-11-05"]

# 이름에 이상한 글자가 섞이면 거부한다.
# 한글도 받는다 — 이름은 그냥 부르는 말이지 파일 이름이 아니다.
이름규칙 = __import__("re").compile(r"^[\w.\-]{1,40}$", __import__("re").UNICODE)

살아있는것 = {}    # 이름 → 붙은서버


class 붙은서버:
    """띄워 둔 MCP 서버 하나."""

    def __init__(self, 이름: str, 명령: list, 자리: str):
        self.이름 = 이름
        self.명령 = 명령
        self.자리 = 자리
        self.프로세스 = None
        self.받은것 = queue.Queue()
        self.도구들 = []
        self.정보 = {}
        self.판 = ""
        self.투덜댄것 = []          # 저쪽이 stderr 로 흘린 말 (탈 났을 때 단서)
        self._자물쇠 = threading.Lock()

    # ── 띄우고 인사하기 ───────────────────────────────────────

    def 띄우기(self):
        try:
            self.프로세스 = subprocess.Popen(
                self.명령,
                cwd=self.자리 or None,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,   # 저쪽이 흘리는 말을 버리지 않는다
                close_fds=True,
            )
        except FileNotFoundError:
            raise ValueError(f"'{self.명령[0]}' 을(를) 찾을 수 없습니다. 깔려 있나요?")
        except OSError as e:
            raise ValueError(f"띄우지 못했습니다: {e}")

        threading.Thread(target=self._읽는일, daemon=True).start()
        threading.Thread(target=self._투덜대는것듣기, daemon=True).start()

        self._인사하기()
        self.보내기({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.도구읽기()
        return self

    def _인사하기(self):
        """판을 맞춰 가며 인사한다.

        규약: 저쪽이 다른 판을 쓰면 자기 판을 돌려준다. 우리가 아는 판이면
        그대로 따라가고, 모르는 판이면 끊는다.
        """
        탈 = None
        for 내판 in 아는판:
            try:
                인사 = self.주고받기("initialize", {
                    "protocolVersion": 내판,
                    "capabilities": {},
                    "clientInfo": {"name": "로컬에이전트", "version": "1.0"},
                }, 붙는참기)
            except ValueError as e:
                탈 = e
                if "Unsupported protocol version" not in str(e):
                    raise
                continue          # 저쪽이 이 판을 모른다 — 다음 판으로

            self.정보 = 인사.get("serverInfo", {})
            저쪽판 = 인사.get("protocolVersion", 내판)
            if 저쪽판 not in 아는판:
                self.끄기()
                raise ValueError(
                    f"우리가 모르는 규약 판입니다: {저쪽판} "
                    f"(우리가 아는 것: {', '.join(아는판)})"
                )
            self.판 = 저쪽판
            return

        raise ValueError(f"판을 맞추지 못했습니다: {탈}")

    def _투덜대는것듣기(self):
        """저쪽이 stderr 로 흘리는 말을 조금만 담아 둔다.

        규약이 로그 용도로 허락한 자리다. 버리면 안 떴을 때 까닭을 알 길이 없다.
        """
        for 줄 in self.프로세스.stderr:
            글 = 줄.decode("utf-8", errors="replace").rstrip()
            if 글:
                self.투덜댄것.append(글)
                del self.투덜댄것[:-40]     # 마지막 40줄만 둔다

    def _읽는일(self):
        """서버가 뱉는 줄을 계속 받아 큐에 쌓는다."""
        for 줄 in self.프로세스.stdout:
            줄 = 줄.strip()
            if not 줄:
                continue
            try:
                self.받은것.put(json.loads(줄.decode("utf-8", errors="replace")))
            except ValueError:
                continue          # JSON 이 아닌 줄은 버린다
        self.받은것.put(None)      # 끝났다는 표시

    # ── 말 주고받기 ───────────────────────────────────────────

    def 보내기(self, 몸통: dict):
        if not self.살았나():
            raise ValueError(f"'{self.이름}' 서버가 꺼져 있습니다.")
        글 = (json.dumps(몸통, ensure_ascii=False) + "\n").encode("utf-8")
        self.프로세스.stdin.write(글)
        self.프로세스.stdin.flush()

    def 주고받기(self, 방법: str, 값: dict, 참기: int) -> dict:
        """물어보고 답이 올 때까지 기다린다."""
        번호 = uuid.uuid4().hex[:12]
        with self._자물쇠:
            self.보내기({"jsonrpc": "2.0", "id": 번호, "method": 방법, "params": 값})

            남은 = 참기
            while 남은 > 0:
                try:
                    답 = self.받은것.get(timeout=1)
                except queue.Empty:
                    남은 -= 1
                    continue
                if 답 is None:
                    꼬리 = ("\n저쪽이 남긴 말: " + " / ".join(self.투덜댄것[-5:])
                           if self.투덜댄것 else "")
                    raise ValueError(f"'{self.이름}' 서버가 도중에 꺼졌습니다.{꼬리}")
                if 답.get("id") != 번호:
                    continue       # 다른 것에 대한 답이나 알림 — 흘려보낸다
                if "error" in 답:
                    탈 = 답["error"]
                    raise ValueError(
                        f"{방법} 실패: {탈.get('message', '')} "
                        f"({탈.get('code', '')})"
                    )
                return 답.get("result", {})

        # 규약: 기다리다 지치면 그만두라고 알려 주고 기다림을 접는다.
        # 안 그러면 저쪽은 계속 일하고 있다.
        try:
            self.보내기({"jsonrpc": "2.0", "method": "notifications/cancelled",
                        "params": {"requestId": 번호, "reason": "기다리다 그만둠"}})
        except Exception:
            pass
        raise ValueError(f"{참기}초를 기다려도 답이 없습니다.")

    # ── 쓰기 ─────────────────────────────────────────────────

    def 살았나(self) -> bool:
        return bool(self.프로세스) and self.프로세스.poll() is None

    def 도구읽기(self):
        결과 = self.주고받기("tools/list", {}, 붙는참기)
        self.도구들 = 결과.get("tools", [])
        return self.도구들

    def 부르기(self, 이름: str, 인자: dict):
        return self.주고받기("tools/call", {"name": 이름, "arguments": 인자 or {}},
                            부르는참기)

    def 끄기(self):
        """규약이 정한 순서대로 곱게 끈다.

        ① 들어가는 입을 닫고  ② 스스로 나가길 기다리고
        ③ 안 나가면 그만하라 하고  ④ 그래도 안 나가면 끊는다.
        바로 죽이면 저쪽이 저장하던 것을 잃을 수 있다.
        """
        것 = self.프로세스
        if not 것 or 것.poll() is not None:
            return

        try:
            것.stdin.close()
        except OSError:
            pass

        try:
            것.wait(timeout=끄는참기)
            return
        except subprocess.TimeoutExpired:
            pass

        try:
            것.terminate()
            것.wait(timeout=끄는참기)
        except (OSError, subprocess.TimeoutExpired):
            try:
                것.kill()
            except OSError:
                pass


# ── 적어 둔 목록 ──────────────────────────────────────────────

def 목록읽기() -> dict:
    return 안전파일.json읽기(목록파일, {"서버들": []}, dict)


def 목록쓰기(값: dict):
    안전파일.json쓰기(목록파일, 값)


def 적힌것(이름: str) -> dict | None:
    for 것 in 목록읽기()["서버들"]:
        if 것["이름"] == 이름:
            return 것
    return None


def 적어두기(이름: str, 명령: list, 자리: str):
    값 = 목록읽기()
    값["서버들"] = [s for s in 값["서버들"] if s["이름"] != 이름]
    값["서버들"].append({
        "이름": 이름,
        "명령": 명령,
        "자리": 자리,
        "때": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    목록쓰기(값)


def 지우기(이름: str):
    값 = 목록읽기()
    남은 = [s for s in 값["서버들"] if s["이름"] != 이름]
    if len(남은) == len(값["서버들"]):
        raise ValueError(f"적혀 있지 않습니다: {이름}")
    값["서버들"] = 남은
    목록쓰기(값)
    서버 = 살아있는것.pop(이름, None)
    if 서버:
        서버.끄기()


# ── 붙이기 ────────────────────────────────────────────────────

def 명령쪼개기(불: str) -> list:
    """'python -m blender_mcp' 같은 글을 조각으로 나눈다."""
    import shlex
    조각 = shlex.split(불, posix=(os.name != "nt"))
    if not 조각:
        raise ValueError("띄울 명령이 비었습니다.")
    return [c.strip('"') for c in 조각]


def 붙이기(이름: str, 명령: list, 자리: str = "") -> dict:
    """실제로 띄워서 붙는다. 승인이 끝난 뒤에만 불린다."""
    옛것 = 살아있는것.pop(이름, None)
    if 옛것:
        옛것.끄기()

    서버 = 붙은서버(이름, 명령, 자리).띄우기()
    살아있는것[이름] = 서버
    적어두기(이름, 명령, 자리)
    return {
        "이름": 이름,
        "상태": "붙음",
        "판": 서버.판,
        "서버정보": 서버.정보,
        "기능수": len(서버.도구들),
        "기능들": [t.get("name") for t in 서버.도구들][:60],
    }


def 챙기기(이름: str) -> 붙은서버:
    """살아 있으면 그대로, 아니면 적어둔 대로 다시 띄운다.

    서버를 껐다 켜면 살아있는것이 비므로 여기서 알아서 되살린다.
    """
    서버 = 살아있는것.get(이름)
    if 서버 and 서버.살았나():
        return 서버

    적힘 = 적힌것(이름)
    if 적힘 is None:
        raise ValueError(
            f"'{이름}' 은(는) 아직 붙여 둔 적이 없습니다. "
            "먼저 열매로 심기를 요청하세요. "
            "예) 나물 열매 / 짓 심기 / 어디 blender / 불 python -m blender_mcp"
        )
    붙이기(이름, 적힘["명령"], 적힘.get("자리", ""))
    return 살아있는것[이름]      # 붙이기는 사람이 읽을 답을 주므로 여기선 알맹이를 돌려준다


def 상태들() -> list:
    것들 = []
    for 적힘 in 목록읽기()["서버들"]:
        서버 = 살아있는것.get(적힘["이름"])
        것들.append({
            "이름": 적힘["이름"],
            "불": " ".join(적힘["명령"]),
            "자리": 적힘.get("자리", ""),
            "상태": "붙음" if (서버 and 서버.살았나()) else "꺼짐",
            "기능수": len(서버.도구들) if 서버 else 0,
        })
    return 것들


def 이름검사(이름: str) -> str:
    이름 = (이름 or "").strip()
    if not 이름:
        raise ValueError('"어디" 가 비었습니다. 서버 이름을 적으세요.')
    if not 이름규칙.match(이름):
        raise ValueError("서버 이름은 영문·숫자와 . _ - 만 됩니다(40자 이내).")
    return 이름
