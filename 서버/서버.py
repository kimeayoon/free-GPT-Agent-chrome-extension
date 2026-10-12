# -*- coding: utf-8 -*-
"""로컬 브리지 서버 — Chrome 확장이 보낸 도구 요청을 실행하고 결과를 돌려준다.

실행: python 서버.py
주소: http://127.0.0.1:8765
"""

import json
import re
import sys
import traceback
from urllib.parse import parse_qs, urlsplit
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import aliases
import conversation_log
import installer
import 길잡이
import approval
import permission
import picker
import rooms
import sandbox
import gate
import tools_bg
import tools_eye
import tools_hand
import tools_git
import tools_mcp
import tools_more
import tools_web
import tools_edit
import tools_file
import tools_install
import tools_memory
import tools_plan
import tools_restore
import tools_resume
import tools_room
import tools_run
import tools_venv
import tools_timer
import 넘김
import 도구안내
import 설명서
import tools_worker
import 사이트
import 현황

버전 = "1.1.0"
이름키 = "나물"   # 요청에서 도구 이름을 담는 키 (확장의 protocol.js 와 맞춰야 함)

# 내부 이름으로 모은 뒤 공개 이름으로 갈아끼운다(aliases.py 참고).
_내부도구 = {
    **tools_file.등록된도구,
    **tools_edit.등록된도구,
    **tools_bg.등록된도구,
    **tools_more.등록된도구,
    **tools_mcp.등록된도구,
    **tools_git.등록된도구,
    **tools_web.등록된도구,
    **tools_run.등록된도구,
    **tools_plan.등록된도구,
    **tools_memory.등록된도구,
    **tools_restore.등록된도구,
    **tools_resume.등록된도구,
    **tools_install.등록된도구,
    **tools_room.등록된도구,
    **tools_venv.등록된도구,
    **tools_timer.등록된도구,
    **tools_worker.등록된도구,
    **tools_eye.등록된도구,
    **tools_hand.등록된도구,
    **현황.등록된도구,
}
등록된도구 = aliases.등록표만들기(_내부도구)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def 로그(*조각):
    시각 = datetime.now().strftime("%H:%M:%S")
    print(f"[{시각}]", *조각, flush=True)


class 핸들러(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # 기본 접속 로그는 시끄러워서 끈다
    def log_message(self, *args):
        pass

    def _응답(self, 코드: int, 몸통: dict):
        데이터 = json.dumps(몸통, ensure_ascii=False).encode("utf-8")
        self.send_response(코드)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(데이터)))
        self._CORS헤더()
        self.end_headers()
        self.wfile.write(데이터)

    def _CORS헤더(self):
        # 받기로 한 곳(확장 · 사용자가 허용한 웹사이트)과, 승인을 기다리는 곳(까닭을 읽게)에만 허락 머리를 붙인다.
        # 예전엔 보낸 곳을 가리지 않고 그대로 돌려줘서 아무 웹사이트나 읽고 쓸 수 있었다.
        오리진 = getattr(self, "_허용출처", None)
        if 오리진:
            self.send_header("Access-Control-Allow-Origin", 오리진)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            if self.headers.get("Access-Control-Request-Private-Network") == "true":
                self.send_header("Access-Control-Allow-Private-Network", "true")

    # 같은 곳이 연달아 두드려도 로그가 도배되지 않게 1분에 한 번만 적는다
    _막음로그때 = {}

    def _막기(self, 코드: int, 글: str, 대기: bool = False, 출처: str = ""):
        """요청을 막고 까닭을 알린다. 안 읽은 몸통을 비워야 같은 연결의 다음 요청이 안 깨진다."""
        try:
            길이 = int(self.headers.get("Content-Length") or 0)
            if 길이:
                self.rfile.read(min(길이, 10_000_000))
        except (ValueError, OSError):
            pass
        데이터 = json.dumps({"됨": False, "탈": 글, "승인대기": bool(대기), "출처": 출처},
                         ensure_ascii=False).encode("utf-8")
        self.send_response(코드)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(데이터)))
        self.send_header("Connection", "close")
        self._CORS헤더()
        self.end_headers()
        self.wfile.write(데이터)
        self.close_connection = True
        열쇠 = (self.headers.get("Origin") or "(출처 없음)", 글)
        지금 = datetime.now().timestamp()
        if 지금 - 핸들러._막음로그때.get(열쇠, 0) > 60:
            핸들러._막음로그때[열쇠] = 지금
            로그(f"막음 ← {self.command} {self.path} 출처 {열쇠[0]} : {글}")

    def _출처검사(self, 길: str) -> bool:
        """이 요청을 받을지 정한다. 막으면 여기서 답까지 보내고 False 를 돌려준다.

        규칙은 서버/사이트.py 머리글을 보라. 요약:
          출처 없음 → 받음 · 확장 → 받음 · 웹사이트 → 사용자가 허용한 곳만(그것도 /tool 과 /ping 만)
        """
        self._허용출처 = None
        self._웹출처 = False
        self._출처등급 = "전부"
        호스트 = (self.headers.get("Host") or "").strip().lower()
        if 호스트 and 호스트 not in 사이트.허용호스트(self.server.server_address[1]):
            self._막기(403, "허용되지 않은 Host 이름입니다(127.0.0.1 · localhost 만 받습니다).")
            return False

        오리진 = self.headers.get("Origin")
        판 = 사이트.판정(오리진)
        if 판["종류"] == "없음":
            return True
        if 판["종류"] == "확장" and 판["허용"]:
            self._허용출처 = 오리진
            return True
        if 판["종류"] == "모름":
            self._막기(403, 판["이유"])
            return False

        # 웹사이트(또는 처음 보는 확장)
        self._웹출처 = True
        self._출처등급 = 판["등급"] or "보기"
        if 판["허용"] or 판["대기"]:
            self._허용출처 = 오리진          # 막더라도 그 곳이 까닭(승인 대기)을 읽을 수 있게
        if self.command == "OPTIONS":
            if 판["허용"] or 판["대기"]:
                return True                  # 사전 확인은 통과시키고 실제 요청에서 막는다
            self._막기(403, 판["이유"])
            return False
        if not 판["허용"]:
            self._막기(403, 판["이유"], 대기=판["대기"], 출처=판["출처"])
            return False
        if 길 not in ("/ping", "/tool"):
            self._막기(403, "웹사이트는 /tool 과 /ping 만 쓸 수 있습니다. 방·폴더·등급·허락은 확장만 바꿉니다.")
            return False
        return True

    def do_OPTIONS(self):
        if not self._출처검사(self._길()):
            return
        self.send_response(204)
        self._CORS헤더()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _사이트처리(self, 몸통):
        """웹사이트 허용 목록. 짓: 목록(기본) · 허용(등급) · 거부 · 지움. 확장만 부를 수 있다."""
        짓 = 몸통.get("짓") or "목록"
        출처 = 몸통.get("출처") or ""
        if 짓 == "허용":
            사이트.허용하기(출처, 몸통.get("등급") or "보기")
            로그(f"웹사이트 허용 → {출처} ({몸통.get('등급') or '보기'})")
        elif 짓 == "거부":
            사이트.거부하기(출처)
            로그(f"웹사이트 거부 → {출처}")
        elif 짓 == "지움":
            사이트.지우기(출처)
            로그(f"웹사이트 목록에서 뺌 → {출처}")
        elif 짓 != "목록":
            self._응답(200, {"됨": False, "탈": f"모르는 짓입니다: {짓}"})
            return
        self._응답(200, {"됨": True, **사이트.요약()})

    def _등급바꾸기(self):
        길이 = int(self.headers.get("Content-Length") or 0)
        원문 = self.rfile.read(길이).decode("utf-8", errors="replace")
        _등급바꾸기_본체(self, 원문)

    def _대화남기기(self):
        길이 = int(self.headers.get("Content-Length") or 0)
        원문 = self.rfile.read(길이).decode("utf-8", errors="replace")
        try:
            몸통 = json.loads(원문)
        except json.JSONDecodeError as e:
            self._응답(200, {"됨": False, "탈": f"형식이 깨졌습니다: {e}"})
            return
        결과 = conversation_log.남기기(
            몸통.get("답변원문", ""), 몸통.get("보낸글", ""), 몸통.get("처리요약")
        )
        conversation_log.목차갱신()
        self._응답(200, {"됨": 결과["남김"], **결과})

    @staticmethod
    def _처음안내(답, 도구명, 이름키):
        """대화마다 처음 한 번: 설명서(규칙)와, 드문 도구의 쓰는 법(사용법)을 결과에 얹는다."""
        return 설명서.첫읽기얹기(도구안내.첫사용얹기(답, 도구명, 이름키), 도구명, 이름키)

    def _몸통받아(self, 처리):
        길이 = int(self.headers.get("Content-Length") or 0)
        원문 = self.rfile.read(길이).decode("utf-8", errors="replace")
        try:
            몸통 = json.loads(원문 or "{}")
            if 몸통.get("방번호"):
                rooms.방고정(몸통["방번호"])
        except json.JSONDecodeError as e:
            self._응답(200, {"됨": False, "탈": f"형식이 깨졌습니다: {e}"})
            return
        try:
            처리(몸통)
        except (ValueError, OSError) as e:
            self._응답(200, {"됨": False, "탈": str(e)})

    def _일꾼(self, 몸통):
        """일꾼 장부. 짓: 열것 · 일감 · 상태 · 결과 · 알릴것 · 알림함 · 목록"""
        self._응답(200, {"됨": True, **tools_worker.처리(몸통.get("짓", ""), 몸통)})

    def _계획짓(self, 몸통):
        """판에서 사용자가 목표를 직접 고친다. GPT 도구와 같은 길(tools_plan.적용)을 타되 누가=사용자.

        짓: 세우기 · 포기 · 목표고치기 · 고치기 · 더하기 · 빼기 · 옮기기 · 상태 · 되살리기 · 되돌리기
        """
        방 = (몸통.get("방") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", 방):
            self._응답(200, {"됨": False, "탈": "방이 없습니다."})
            return
        rooms.방고정(방)
        차례 = 몸통.get("차례")
        if isinstance(차례, str):
            차례 = [줄 for 줄 in 차례.splitlines()]
        결과 = tools_plan.적용(
            몸통.get("짓") or "", "사용자", step=몸통.get("몇"), status=몸통.get("상태") or "",
            note=몸통.get("쪽"), name=몸통.get("이름") or "", task=몸통.get("일") or "",
            steps=차례, to_step=몸통.get("새몇"), why=몸통.get("왜") or "", job=몸통.get("번호") or "")
        로그(f"판에서 목표 고침 → {몸통.get('짓')}: {결과.get('한일') or ''}")
        self._응답(200, {"됨": True, **aliases.결과포장(tools_plan.plan_get(전체=True)),
                       **tools_plan.판정보(), "한일": 결과.get("한일", "")})

    def _현황판(self, 몸통):
        """실행 현황. 짓: 목록(기본) · 멈춤 · 숨김 · 치움.

        숫자는 GPT 말이 아니라 여기서 디스크·프로세스를 읽어 잰 것이다.
        """
        방 = (몸통.get("방") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", 방):
            self._응답(200, {"됨": False, "탈": "방이 없습니다."})
            return
        짓 = 몸통.get("짓") or "목록"
        rooms.방고정(방)               # 상대 경로(logs▸학습.log)는 이 방의 폴더 기준
        결과 = {}
        if 짓 == "멈춤":
            결과 = 현황.일멈추기(방, (몸통.get("번호") or "").strip())
            로그(f"현황판에서 일 멈춤 → {몸통.get('번호')}")
        elif 짓 == "숨김":
            현황.판숨기기(방, (몸통.get("번호") or "").strip())
        elif 짓 == "치움":
            현황.판치우기(방, (몸통.get("번호") or "").strip())
        elif 짓 != "목록":
            self._응답(200, {"됨": False, "탈": f"모르는 짓입니다: {짓}"})
            return
        self._응답(200, {"됨": True, **현황.측정(방), "요약": 현황.요약들(), "한일": 결과})

    def _압축(self, 몸통):
        """새 대화가 쓴 압축 요약(【압축】…【압축끝】)을 방에 적는다."""
        방 = (몸통.get("방") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", 방):
            self._응답(200, {"됨": False, "탈": "방이 없습니다."})
            return
        결과 = rooms.압축적기(방, 몸통.get("글", ""))
        로그(f"압축 요약 적음 → {방} ({결과['글자수']:,}자)")
        self._응답(200, {"됨": True, **결과})

    def _프로젝트이름(self, 몸통):
        """ChatGPT 에서 본 프로젝트 이름을 판의 묶음 이름에 맞춘다."""
        묶음 = rooms.프로젝트이름맞추기(몸통.get("프로젝트", ""), 몸통.get("이름", ""))
        self._응답(200, {"됨": True, "이름": (묶음 or {}).get("이름")})

    def _넘김(self, 몸통):
        """꽉 찬 대화를 새 대화로 넘길 자료(넘김 파일 글)를 만든다."""
        방 = (몸통.get("방") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", 방):
            self._응답(200, {"됨": False, "탈": "방이 없습니다."})
            return
        글 = 넘김.넘김글(방)
        로그(f"넘김 파일 만듦 → {방} ({len(글):,}자)")
        self._응답(200, {"됨": True, "글": 글})

    # 확장이 예약을 살핀다. 짓: 때된것 | 보냄 | 목록 | 그만
    def _예약처리(self, 몸통):
        방 = (몸통.get("방") or "").strip()
        # 방 번호는 폴더 이름이 된다. 엉뚱한 자리(../ 같은)에 파일을 못 만들게 모양을 본다.
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", 방):
            self._응답(200, {"됨": False, "탈": "방이 없습니다."})
            return
        짓 = 몸통.get("짓")
        if 짓 == "때된것":
            self._응답(200, {"됨": True, "예약": tools_timer.때된것(방)})
        elif 짓 == "보냄":
            self._응답(200, {"됨": True, "예약": tools_timer.보냄(방, 몸통.get("번호") or "")})
        elif 짓 == "목록":
            self._응답(200, {"됨": True, "예약들": tools_timer.목록(방)})
        elif 짓 == "그만":
            self._응답(200, {"됨": True, "예약": tools_timer.그만(방, 몸통.get("번호") or "")})
        elif 짓 == "지금상태":
            self._응답(200, {"됨": True, "글": tools_timer.지금상태글(방)})
        else:
            self._응답(200, {"됨": False, "탈": f"모르는 짓입니다: {짓}"})

    def _폴더고르기(self, 몸통):
        로그("폴더 선택창 띄우는 중…")
        결과 = picker.폴더고르기(몸통.get("처음자리", ""))
        if not 결과["고름"]:
            self._응답(200, {"됨": False, "탈": 결과["이유"]})
            return
        # 프로젝트 묶음의 일할 폴더를 고르는 것이면 새 폴더를 더하지 않고 그 묶음에 정한다
        if 몸통.get("묶음"):
            폴더 = rooms.묶음밭정하기(몸통["묶음"], 결과["밭"])
            로그(f"프로젝트 폴더 정함 → {폴더['이름']}  ({폴더['밭']})")
            self._응답(200, {"됨": True, **폴더, **rooms.나무()})
            return
        폴더 = rooms.폴더더하기(결과["밭"])
        로그(f"폴더 더함 → {폴더['이름']}  ({폴더['밭']})")
        self._응답(200, {"됨": True, **폴더, **rooms.나무()})

    def _폴더처리(self, 몸통):
        짓 = 몸통.get("짓", "")
        if 짓 == "더하기":
            폴더 = rooms.폴더더하기(몸통.get("밭", ""))
            self._응답(200, {"됨": True, "쪽번호": 폴더["쪽번호"], **rooms.나무()})
            return
        if 짓 == "밭정하기":
            rooms.묶음밭정하기(몸통.get("쪽번호", ""), 몸통.get("밭", ""))
        elif 짓 == "빼기":
            rooms.폴더빼기(몸통.get("쪽번호", ""))
        elif 짓 == "이름":
            rooms.폴더이름바꾸기(몸통.get("쪽번호", ""), 몸통.get("이름", ""))
        else:
            raise ValueError("'짓' 은 빼기 또는 이름 이어야 합니다.")
        self._응답(200, {"됨": True, **rooms.나무()})

    def _방처리(self, 몸통):
        짓 = 몸통.get("짓", "")
        if 짓 == "만들기":
            방 = rooms.방만들기(몸통.get("폴더", ""), 몸통.get("이름", ""))
            로그(f"방 만듦 → {방['쪽번호']}  ({방.get('밭') or '폴더 없음'})")
        elif 짓 == "고르기":
            방 = rooms.방고르기(몸통.get("쪽번호", ""))
            로그(f"방 바뀜 → {방.get('이름') or '(이름 없음)'}")
        elif 짓 == "이름":
            rooms.방이름바꾸기(몸통.get("쪽번호", ""), 몸통.get("이름", ""),
                             자동=bool(몸통.get("자동")))
        elif 짓 == "빼기":
            rooms.방빼기(몸통.get("쪽번호", ""))
        elif 짓 == "폴더이동":
            방 = rooms.방폴더바꾸기(몸통.get("쪽번호", ""), 몸통.get("폴더", ""))
            로그(f"방 옮김 → {방.get('이름')}  ({방.get('밭') or '폴더 없음'})")
        else:
            raise ValueError("'짓' 은 만들기·고르기·이름·빼기·폴더이동 중 하나여야 합니다.")
        self._응답(200, {"됨": True, **rooms.나무()})

    def _허락처리(self, 몸통):
        밭 = 몸통.get("밭", "")
        if 몸통.get("허용"):
            결과 = rooms.허락하기(밭)
            로그(f"쓰기 허락 → {밭}")
        else:
            결과 = rooms.거절하기(밭)
            로그(f"쓰기 거절 → {밭}")
        self._응답(200, {"됨": True, **결과, **rooms.나무()})

    def _대화방(self, 몸통):
        """ChatGPT 대화 하나에 방 하나를 붙여 준다.

        창을 여러 개 띄워도 서로 다른 프로젝트를 동시에 할 수 있게,
        대화 번호마다 제 방을 갖는다.
        """
        try:
            # 꽉 찬 대화를 넘겨받은 새 대화 — 옛 방을 그대로 이어 갖는다
            if 몸통.get("이어받을방"):
                방 = rooms.방대화이어붙이기(몸통["이어받을방"], 몸통.get("대화", ""))
                설명서.새대화로이어붙임(방["쪽번호"], 몸통.get("대화", ""))
                로그(f"대화 넘겨받음 → {방['쪽번호']} ({방.get('이름') or '이름 없음'})")
                self._응답(200, {"됨": True, "방": 방, **rooms.나무()})
                return
            # 만들기=false 면 있는 방만 찾는다(대화를 열어 본 것만으로 방을 안 만든다).
            # 옛 확장은 이 값을 안 보내므로 기본은 만든다.
            if 몸통.get("만들기", True) is False:
                방 = rooms.대화방찾기(몸통.get("대화", ""), 몸통.get("프로젝트", ""),
                                  몸통.get("프로젝트이름", ""))
                self._응답(200, {"됨": True, "방": 방, **rooms.나무()})
                return
            방 = rooms.대화방잡기(몸통.get("대화", ""), 몸통.get("이름", ""),
                                  몸통.get("프로젝트", ""), 몸통.get("프로젝트이름", ""))
            로그(f"대화방 → {방['쪽번호']} ({방.get('이름') or '이름 없음'})")
            self._응답(200, {"됨": True, "방": 방, **rooms.나무()})
        except Exception as e:
            self._응답(200, {"됨": False, "탈": str(e)})

    def _칸보기(self, 몸통):
        """창에 파일 나무를 그리려고 칸 하나의 속을 알려준다.

        도구(가지)와 달리 한 겹만 본다. 창에서 펼칠 때마다 다시 묻는 편이
        한꺼번에 깊이 훑는 것보다 빠르고, 큰 폴더에서도 안 멈춘다.
        """
        밭 = (몸통.get("밭") or "").strip()
        어디 = (몸통.get("어디") or "").strip()

        try:
            if not 밭:
                if 어디 == "방":
                    자리 = rooms.방자료칸()
                else:
                    자리 = rooms.지금밭()
                    if 자리 is None:
                        self._응답(200, {"됨": False, "탈": "일할 곳을 먼저 고르세요."})
                        return
            else:
                자리 = sandbox.경로검증(밭)

            if not 자리.is_dir():
                self._응답(200, {"됨": False, "탈": "칸이 아닙니다."})
                return

            것들 = []
            for 하나 in sorted(자리.iterdir(),
                             key=lambda x: (not x.is_dir(), x.name.lower())):
                if 하나.is_dir() and sandbox.제외폴더인가(하나.name):
                    continue
                try:
                    크기 = 하나.stat().st_size if hasattr(하나, "stat") else 0
                except OSError:
                    크기 = 0
                것들.append({
                    "이름": 하나.name,
                    "밭": str(하나),
                    "칸인가": 하나.is_dir(),
                    "크기": 0 if 하나.is_dir() else 크기,
                })
                if len(것들) >= 500:
                    break

            self._응답(200, {"됨": True, "밭": str(자리), "것들": 것들})
        except Exception as e:
            self._응답(200, {"됨": False, "탈": str(e)})

    def _대화처리(self, 몸통):
        쪽번호 = 몸통.get("쪽번호", "")
        종류 = 몸통.get("종류", "")

        # 대화창을 앞 시점으로 되돌린 경우
        if 종류 == "되돌리기":
            if not 쪽번호:
                self._응답(200, {"됨": False, "탈": "'쪽번호' 가 없습니다."})
                return
            결과 = rooms.대화되돌리기(쪽번호, 몸통.get("남은지문들") or [])
            if 결과.get("잘랐나"):
                로그(f"되돌림 ← {결과['지운건수']}건 지움")
            self._응답(200, {"됨": True, **결과})
            return

        if 종류 not in ("나", "gpt", "사용자", "도구", "요약"):
            self._응답(200, {
                "됨": False,
                "탈": "'종류' 는 나·gpt·사용자·도구·요약 중 하나여야 합니다.",
            })
            return
        if not 쪽번호:
            self._응답(200, {"됨": False, "탈": "'쪽번호' 가 없습니다."})
            return
        rooms.대화추가(쪽번호, 종류, 몸통.get("글", ""),
                      몸통.get("나물", ""), 몸통.get("지문", ""))
        self._응답(200, {"됨": True})

    def _승인처리(self, 몸통):
        """권한 모드가 묻는 카드(승인::…)의 허용 · 거부. 허용하면 그 호출을 지금 돌려 결과를 답에 싣는다."""
        열쇠 = 몸통.get("열쇠", "")
        try:
            if 몸통.get("허용"):
                요 = approval.허락하기(열쇠, bool(몸통.get("항상")))
                로그(f"승인 허락 → {요['나물']}" + (" (항상)" if 몸통.get("항상") else ""))
                결과 = self._실행하기(요["나물"], 요["인자"], 요["방번호"])
                답 = {"됨": True, "갈래": "승인", "열쇠": 열쇠, "허용": True, "나물": 요["나물"], "일": 요["제목"], "결과": 결과}
            else:
                거 = approval.거절하기(열쇠)
                로그(f"승인 거절 → {거['나물']}")
                답 = {"됨": True, "갈래": "승인", "열쇠": 열쇠, "허용": False, "나물": 거["나물"], "일": 거["제목"],
                      "결과": {"됨": False, 이름키: 거["나물"], "탈": 거["나온것"]}}
        except ValueError as e:
            답 = {"됨": False, "갈래": "승인", "열쇠": 열쇠, "탈": str(e)}
        self._응답(200, {**답, "기다림": installer.목록(), "허가중": gate.허가중목록()})

    def _받아오기처리(self, 몸통):
        열쇠 = 몸통.get("열쇠", "")
        if str(열쇠).startswith("승인::"):
            self._승인처리(몸통)
            return
        if 몸통.get("그만") is not None:
            # 판의 [그만] — 살아 있는 눈·손 허가를 거둔다(번호가 없으면 전부)
            번호 = 몸통.get("그만")
            로그(f"눈·손 허가 거둠 → {번호 if 번호 != '' else '전부'}")
            self._응답(200, {"됨": True, "거둠": gate.그만(None if 번호 in ("", "전부") else 번호),
                           "기다림": installer.목록(), "허가중": gate.허가중목록()})
            return
        if 몸통.get("허용"):
            로그(f"받아오기 허락 → {열쇠}")
            결과 = installer.허락하기(열쇠)
            로그(f"받아오기 {'성공' if 결과.get('됨') else '실패'} ← {열쇠}")
        else:
            결과 = installer.거절하기(열쇠)
            로그(f"받아오기 거절 → {열쇠}")
        self._응답(200, {"됨": True, **결과, "기다림": installer.목록(), "허가중": gate.허가중목록()})

    def do_GET(self):
        rooms.방풀기()
        길 = self._길()
        if not self._출처검사(길):
            return
        if 길 == "/installs":
            self._응답(200, {"됨": True, "기다림": installer.목록(), "허가중": gate.허가중목록()})
            return
        if 길 == "/rooms":
            try:
                방번호 = (parse_qs(urlsplit(self.path).query).get("방") or [""])[0]
                # 창을 둘 띄워 서로 다른 프로젝트를 할 때, 방 이름·폴더도 그 창의 방 기준이어야 한다
                if 방번호:
                    rooms.방고정(방번호)
                나무 = rooms.나무(방번호 or None)
                # 일꾼 방에 일꾼 상태를 붙인다(판에 '일하는중' 등으로 보인다)
                상태표 = tools_worker.방상태표()
                for 폴더 in 나무.get("폴더들", []):
                    for 방 in 폴더.get("방들", []):
                        if 방.get("부모"):
                            방["일꾼상태"] = 상태표.get(방["쪽번호"], "")
                self._응답(200, {"됨": True, **나무})
            except Exception as e:
                self._응답(200, {"됨": False, "탈": str(e)})
            return
        if 길 == "/plan":
            try:
                # 할 일도 그 창의 방 것. 예전엔 서버가 마지막으로 쓴 방의 할 일을 줬다
                방번호 = (parse_qs(urlsplit(self.path).query).get("방") or [""])[0]
                if 방번호:
                    rooms.방고정(방번호)
                self._응답(200, {"됨": True, **aliases.결과포장(tools_plan.plan_get(전체=True)),
                               **tools_plan.판정보()})
            except Exception as e:
                self._응답(200, {"됨": False, "탈": str(e)})
            return
        if 길 == "/ping" and self._웹출처:
            # 허용한 웹사이트에는 살아 있다는 것과 버전만 알린다(방 이름·폴더 이름이 새지 않게)
            self._응답(200, {"success": True, "version": 버전})
            return
        if 길 == "/ping":
            self._응답(200, {
                "success": True,
                "version": 버전,
                "루트": sandbox.설정["루트"],
                "기준폴더": sandbox.설정["기준폴더"],
                "도구목록": sorted(등록된도구),
                "등급": permission.등급읽기(),
                "등급목록": list(permission.등급목록),
                "모드": permission.모드읽기(),
                "모드목록": list(permission.모드목록),
                "지금쓸수있는것": permission.지금쓸수있는것(),
                "방": rooms.나무(),
            })
        else:
            self._응답(404, {"됨": False, "탈": "없는 길입니다."})

    def _길(self) -> str:
        """물음표 뒤와 끝 빗금을 뗀 주소. 길은 이것과 '똑같을' 때만 맞다고 본다.

        예전에는 startswith 로 앞글자만 맞췄다. 그래서 /room 이 /room-of-chat 을
        먼저 가로채, '이 대화의 방 잡기' 가 한 번도 실행되지 않았다.
        (창마다 따로 방을 갖는 기능 전체가 그 때문에 안 돌았다)
        """
        return self.path.split("?", 1)[0].rstrip("/") or "/"

    def _실행하기(self, 도구명, 인자, 방번호) -> dict:
        """도구 하나를 돌려 JSON 답을 만든다. /tool 과 승인 뒤 실행이 같이 쓴다(권한 판정은 여기서 안 한다)."""
        try:
            rooms.방고정(방번호)
            결과 = 등록된도구[도구명](**인자)
            답 = {"됨": True, 이름키: 도구명, **aliases.결과포장(결과)}
            # GPT 가 조건 예약이 기다리던 것을 스스로 확인했으면 그 예약은 닫는다(뒤늦은 알림 막기)
            try:
                if tools_timer.확인한조건닫기(방번호 or (rooms.지금방() or {}).get("쪽번호", ""), 도구명, 인자):
                    답["귀띔"] = "기다리던 조건 예약은 이미 확인했으므로 닫았습니다."
            except Exception as e:
                로그(f"예약 닫기 실패(넘어감): {e}")

            # 막지 않는다. 다음에 하면 좋을 것을 한 줄로 얹어 준다.
            try:
                말 = 길잡이.귀띔(도구명, 결과)
                if 말:
                    답["귀띔"] = 말
            except Exception as e:
                로그(f"귀띔 실패(넘어감): {e}")

            return self._처음안내(답, 도구명, 이름키)
            로그(f"성공 ← {도구명}")
        except TypeError as e:
            return self._처음안내({"됨": False, 이름키: 도구명,
                            "탈": "넣은 값이 맞지 않습니다. 이름과 개수를 확인하세요."}, 도구명, 이름키)
            로그(f"인자오류 ← {도구명}: {e}")
        except (sandbox.보안오류, ValueError, OSError) as e:
            # 예상된 거부/실패다. traceback 까지 찍으면 로그만 지저분해진다.
            # 예외 클래스 이름은 밖으로 내보내지 않는다(영어가 새어나간다).
            return self._처음안내({"됨": False, 이름키: 도구명, "탈": str(e)}, 도구명, 이름키)
            로그(f"거부 ← {도구명}: {e}")
        except Exception as e:
            return {"됨": False, 이름키: 도구명, "탈": str(e) or "알 수 없는 문제"}
            로그(f"실패 ← {도구명}: {type(e).__name__}: {e}")
            traceback.print_exc()
        finally:
            rooms.방풀기()

    def do_POST(self):
        rooms.방풀기()
        길 = self._길()
        if not self._출처검사(길):
            return

        몸통길 = {
            "/pick-folder":  self._폴더고르기,
            "/folder":       self._폴더처리,
            "/room":         self._방처리,
            "/room-of-chat": self._대화방,
            "/grant":        self._허락처리,
            "/install":      self._받아오기처리,
            "/dir":          self._칸보기,
            "/chat":         self._대화처리,
            "/reminders":    self._예약처리,
            "/handoff":      self._넘김,
            "/project-name": self._프로젝트이름,
            "/compact":      self._압축,
            "/workers":      self._일꾼,
            "/board":        self._현황판,
            "/plan":         self._계획짓,
            "/sites":        self._사이트처리,
        }
        if 길 in 몸통길:
            self._몸통받아(몸통길[길])
            return
        if 길 == "/mode":
            self._등급바꾸기()
            return
        if 길 == "/log":
            self._대화남기기()
            return
        if 길 != "/tool":
            self._응답(404, {"됨": False, "탈": f"없는 길입니다: {길}"})
            return

        길이 = int(self.headers.get("Content-Length") or 0)
        원문 = self.rfile.read(길이).decode("utf-8", errors="replace")

        try:
            요청 = json.loads(원문)
        except json.JSONDecodeError as e:
            로그("JSON 파싱 실패:", e)
            self._응답(200, {"됨": False, "탈": f"형식이 깨졌습니다: {e}"})
            return

        도구명 = 요청.get(이름키)
        # 어느 방에서 부르는지 같이 온다. 이 요청 동안만 그 방을 본다.
        방번호 = 요청.get("방번호") or ""
        바깥인자 = {k: v for k, v in 요청.items()
                  if k not in (이름키, "방번호")}
        인자 = aliases.인자풀기(바깥인자)
        로그(f"요청 → {도구명} {인자}" + (f"  (웹사이트 {self.headers.get('Origin')}, {self._출처등급})" if self._웹출처 else ""))

        # 웹사이트가 부른 것이면 그 사이트에 허락한 등급까지만. '읽기만' 이면 보기 등급 도구만 쓴다.
        if self._웹출처 and self._출처등급 != "전부" and permission.나물등급.get(도구명) != "보기":
            self._응답(200, {
                "됨": False,
                이름키: 도구명,
                "탈": "이 웹사이트는 '읽기만' 허용돼 있습니다. 읽는 도구만 쓸 수 있습니다. "
                      "더 필요하면 사용자가 에이전트 판의 Settings 에서 '전부 허용' 으로 바꿔야 합니다.",
            })
            로그(f"사이트등급차단 ← {도구명} (출처 {self.headers.get('Origin')})")
            return

        # 일꾼 방이면 역할 등급까지만(분석·검토 = 읽기만)
        허용, 막힌이유 = permission.쓸수있나(도구명, rooms.방역할(방번호) if 방번호 else "")
        if not 허용:
            self._응답(200, {
                "됨": False,
                이름키: 도구명,
                "탈": 막힌이유,
                "쓸수있는것": permission.지금쓸수있는것(),
            })
            로그(f"등급차단 ← {도구명} (지금 {permission.등급읽기()}" + (f", 일꾼 역할 {rooms.방역할(방번호)}" if 방번호 and rooms.방역할(방번호) else "") + ")")
            return

        if 도구명 not in 등록된도구:
            self._응답(200, {
                "됨": False,
                이름키: 도구명,
                "탈": f"모르는 이름입니다: {도구명}",
                "쓸수있는것": sorted(등록된도구),
            })
            return

        # 승인 문 — 권한 모드(전체권한 · 자동 · 수동)에 따라 바로 함 · 사용자에게 물음 · 막음
        try:
            rooms.방고정(방번호)
            모드 = permission.모드읽기()
            판정, 요약 = approval.판정(도구명, 인자, 방번호, 모드, bool(self._웹출처))
        except Exception as e:
            # 판정이 터지면 열어 주지 않는다(수동에서 승인 없이 지나가면 안 된다)
            rooms.방풀기()
            로그(f"승인 판정 실패 ← {도구명}: {type(e).__name__}: {e}")
            self._응답(200, {"됨": False, 이름키: 도구명, "탈": "승인 여부를 판단하지 못해 실행하지 않았습니다. 잠시 뒤 다시 하세요."})
            return
        if 판정 == approval.막음:
            rooms.방풀기()
            self._응답(200, {"됨": False, 이름키: 도구명, "탈": 요약.get("탈", "막혀 있습니다.")})
            로그(f"승인막음 ← {도구명} (모드 {모드})")
            return
        if 판정 == approval.카드:
            대기 = approval.요청하기(도구명, 인자, 방번호, 요약, 모드)
            rooms.방풀기()
            self._응답(200, {"됨": True, 이름키: 도구명, **대기})
            로그(f"승인대기 ← {도구명} (모드 {모드}) {요약.get('제목', '')}")
            return

        self._응답(200, self._실행하기(도구명, 인자, 방번호))


def _등급바꾸기_본체(핸들러, 원문):
    try:
        요청 = json.loads(원문)
        if 요청.get("모드") is not None:
            # 판의 메뉴: 전체권한 · 자동 · 수동. 도구를 막는 등급은 '전부' 로 풀고 승인 문이 정한다.
            새모드 = permission.모드쓰기(요청.get("모드"))
            로그(f"권한 모드 바뀜 → {새모드}")
            핸들러._응답(200, {"됨": True, "모드": 새모드, "등급": permission.등급읽기(),
                             "모드목록": list(permission.모드목록)})
            return
        새등급 = permission.등급쓰기(요청.get("등급"))
    except ValueError as e:
        핸들러._응답(200, {"됨": False, "탈": str(e)})
        return
    except json.JSONDecodeError as e:
        핸들러._응답(200, {"됨": False, "탈": f"형식이 깨졌습니다: {e}"})
        return

    로그(f"등급 바뀜 → {새등급}")
    핸들러._응답(200, {
        "됨": True,
        "등급": 새등급,
        "설명": permission.설명[새등급],
        "지금쓸수있는것": permission.지금쓸수있는것(),
    })


def 실행():
    포트 = sandbox.설정["포트"]
    서버 = ThreadingHTTPServer(("127.0.0.1", 포트), 핸들러)
    로그(f"브리지 서버 시작 v{버전}  →  http://127.0.0.1:{포트}")
    로그(f"샌드박스 루트 : {sandbox.설정['루트']}")
    로그(f"기준 폴더     : {sandbox.설정['기준폴더']}")
    로그(f"도구          : {', '.join(sorted(등록된도구))}")
    로그(f"권한 등급     : {permission.등급읽기()}  ({permission.설명[permission.등급읽기()]})")
    로그(f"권한 모드     : {permission.모드읽기()}")
    _밭 = rooms.지금밭()
    로그(f"지금 방       : {(rooms.지금방() or {}).get('이름') or '(없음)'}")
    로그(f"고칠 수 있는 곳: {_밭 or '(없음 — 쓰기 전부 막힘)'}")
    로그(f"받아올 자리   : {installer.받을자리()}")
    로그(f"대화기록       : {conversation_log.기록뿌리}")
    로그("종료하려면 Ctrl+C")
    try:
        서버.serve_forever()
    except KeyboardInterrupt:
        로그("종료합니다.")
        서버.shutdown()


if __name__ == "__main__":
    실행()
