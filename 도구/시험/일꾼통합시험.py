# -*- coding: utf-8 -*-
"""일꾼 통합 시험 — 진짜 깃 저장소 · 진짜 HTTP 서버로 일꾼 3·4단계를 처음부터 끝까지 돌린다.

확장(대장 탭 · 일꾼 탭)이 서버에 보내는 요청을 그 순서 그대로 보낸다.
  대장 GPT 가 콩(구현) → 대장 탭 '열것' → 일꾼 탭 '일감' → 일꾼 GPT 가 상추로 고침(일꾼 방)
  → 일꾼 탭 '결과' → 가지에 맡김 → 대장 탭 '알릴것' → 대장 GPT 가 팥 합치기 → 본 폴더에 들어옴

사용자 자료는 안 건드린다. 임시 폴더에 제 저장소·제 방목록을 차린다.
돌리는 법:  python 도구▸시험▸일꾼통합시험.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(뿌리 / "서버"))

import rooms      # noqa: E402
import sandbox    # noqa: E402


def 깃(자리, *뒷말):
    끝 = subprocess.run(["git", "-c", "user.name=시험", "-c", "user.email=t@t", *뒷말], cwd=str(자리),
                       capture_output=True, text=True, encoding="utf-8")
    return 끝.returncode, (끝.stdout + 끝.stderr).strip()


class 일꾼통합(unittest.TestCase):

    def setUp(self):
        self.임시 = Path(tempfile.mkdtemp(prefix="일꾼통합-"))
        self.저장소 = self.임시 / "게임"
        (self.저장소 / "sim").mkdir(parents=True)
        (self.저장소 / "sim" / "보상.py").write_text("def 보상():\n    return 1\n", encoding="utf-8")
        깃(self.저장소, "init", "-q")
        깃(self.저장소, "add", "-A")
        깃(self.저장소, "commit", "-q", "-m", "처음")

        self.옛설정 = dict(sandbox.설정)
        self.옛목록 = rooms.목록파일
        self.옛방뿌리 = rooms.방뿌리
        sandbox.설정.update(루트=str(self.임시), 쓰기루트=str(self.임시), 기준폴더=str(self.임시))
        rooms.목록파일 = self.임시 / "방목록.json"
        rooms.방뿌리 = self.임시 / "방"
        rooms.방뿌리.mkdir()
        rooms.쓰기(rooms._기본값())
        폴더 = rooms.폴더더하기(str(self.저장소))
        self.대장 = rooms.방만들기(폴더["쪽번호"], "대장")

        import 서버
        self.서버 = ThreadingHTTPServer(("127.0.0.1", 0), 서버.핸들러)
        self.주소 = f"http://127.0.0.1:{self.서버.server_address[1]}"
        threading.Thread(target=self.서버.serve_forever, daemon=True).start()

    def tearDown(self):
        self.서버.shutdown()
        self.서버.server_close()
        rooms.방풀기()
        sandbox.설정.clear()
        sandbox.설정.update(self.옛설정)
        rooms.목록파일 = self.옛목록
        rooms.방뿌리 = self.옛방뿌리
        subprocess.run(["git", "worktree", "prune"], cwd=str(self.저장소), capture_output=True)
        shutil.rmtree(self.임시, ignore_errors=True)

    # 확장이 보내는 것 그대로
    def 보내(self, 길, 몸):
        요 = urllib.request.Request(self.주소 + 길, method="POST",
                                   data=json.dumps(몸, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(요, timeout=30) as 응:
            return json.loads(응.read().decode("utf-8"))

    def 나물(self, 방, 나물이름, **값):
        return self.보내("/tool", {"나물": 나물이름, "방번호": 방, **값})

    def 일꾼(self, 짓, **값):
        return self.보내("/workers", {"짓": 짓, **값})

    def 구현일꾼부르고_일시키기(self, 일꾼이름, 새글, **더):
        부름 = self.나물(self.대장["쪽번호"], "콩", 역할="구현", 이름=일꾼이름, 일="보상 함수를 고쳐라", **더)
        self.assertTrue(부름.get("됨"), 부름)
        열 = self.일꾼("열것", 방=self.대장["쪽번호"])["일꾼"]
        self.assertEqual(열["번호"], 부름["번호"])
        일감 = self.일꾼("일감", 번호=부름["번호"])
        self.assertIn("worktree", 일감["글"])
        # 일꾼 GPT 가 제 방에서 고친다
        고침 = self.나물(부름["방"], "상추", 밭="sim▸보상.py", 속=새글)
        self.assertTrue(고침.get("됨"), 고침)
        return 부름

    # ── 3단계 ──
    def test_구현_일꾼은_떼어놓은_폴더에서_고치고_합치면_본폴더에_들어온다(self):
        부름 = self.구현일꾼부르고_일시키기("보상 고치기", "def 보상():\n    return 2\n")
        본파일 = self.저장소 / "sim" / "보상.py"
        복사파일 = self.저장소 / ".일꾼" / 부름["번호"] / "sim" / "보상.py"
        self.assertIn("return 1", 본파일.read_text(encoding="utf-8"), "일꾼은 본 폴더를 안 건드린다")
        self.assertIn("return 2", 복사파일.read_text(encoding="utf-8"), "일꾼 복사 폴더에만 고쳤다")
        _, 상태 = 깃(self.저장소, "status", "--porcelain")
        self.assertNotIn(".일꾼", 상태, "복사 폴더는 본 저장소 상태에 안 보인다")

        # 일꾼이 【일꾼결과】 로 끝냄 → 제 가지에 맡김
        self.일꾼("결과", 번호=부름["번호"], 글="보상을 2로 바꿈")
        알 = self.일꾼("알릴것", 방=self.대장["쪽번호"])["일꾼"]
        self.assertIn("가지 일꾼/" + 부름["번호"], 알["결과"])
        self.assertIn("상태 합치기", 알["결과"])
        _, 가지기록 = 깃(self.저장소, "log", "--oneline", "일꾼/" + 부름["번호"])
        self.assertIn("보상 고치기", 가지기록)

        # 대장이 합친다
        합 = self.나물(self.대장["쪽번호"], "팥", 번호=부름["번호"], 상태="합치기")
        self.assertTrue(합.get("됨") and 합.get("합침"), 합)
        self.assertIn("return 2", 본파일.read_text(encoding="utf-8"), "합치면 본 폴더에 들어온다")
        self.assertFalse((self.저장소 / ".일꾼" / 부름["번호"]).exists(), "다 합치면 복사 폴더는 치운다")
        _, 가지들 = 깃(self.저장소, "branch")
        self.assertIn("일꾼/" + 부름["번호"], 가지들, "가지는 남긴다(작업이 안 사라지게)")

    def test_충돌이면_되돌리고_충돌파일을_알린다(self):
        부름 = self.구현일꾼부르고_일시키기("보상 고치기", "def 보상():\n    return 2\n")
        self.일꾼("결과", 번호=부름["번호"], 글="보상을 2로")
        # 그사이 대장이 본 폴더의 같은 줄을 다르게 고치고 맡김
        (self.저장소 / "sim" / "보상.py").write_text("def 보상():\n    return 3\n", encoding="utf-8")
        깃(self.저장소, "commit", "-qam", "대장이 3으로")
        합 = self.나물(self.대장["쪽번호"], "팥", 번호=부름["번호"], 상태="합치기")
        self.assertFalse(합.get("합침"), 합)
        self.assertIn("sim/보상.py", 합.get("충돌", []))
        self.assertIn("return 3", (self.저장소 / "sim" / "보상.py").read_text(encoding="utf-8"), "충돌이면 되돌려 대장 것 그대로")
        _, 상태 = 깃(self.저장소, "status", "--porcelain")
        self.assertEqual(상태, "", "merge 가 반쯤 남아 있지 않다")

    def test_일꾼방에서는_복사폴더_밖을_못고친다(self):
        부름 = self.구현일꾼부르고_일시키기("보상 고치기", "def 보상():\n    return 2\n")
        답 = self.나물(부름["방"], "상추", 밭=str(self.저장소 / "sim" / "딴것.py"), 속="x = 1\n")
        self.assertFalse(답.get("됨"), "일꾼은 본 폴더에 직접 못 쓴다")
        self.assertFalse((self.저장소 / "sim" / "딴것.py").exists())

    def test_버리기는_폴더만_치우고_가지는_남긴다(self):
        부름 = self.구현일꾼부르고_일시키기("보상 고치기", "def 보상():\n    return 9\n")
        self.일꾼("결과", 번호=부름["번호"], 글="9로")
        버림 = self.나물(self.대장["쪽번호"], "팥", 번호=부름["번호"], 상태="버리기")
        self.assertTrue(버림.get("됨"), 버림)
        self.assertFalse((self.저장소 / ".일꾼" / 부름["번호"]).exists())
        _, 가지들 = 깃(self.저장소, "branch")
        self.assertIn("일꾼/" + 부름["번호"], 가지들)
        self.assertIn("return 1", (self.저장소 / "sim" / "보상.py").read_text(encoding="utf-8"))

    # ── 4단계 ──
    def test_먼저_적은_일꾼이_끝나야_열리고_결과를_이어받는다(self):
        앞 = self.나물(self.대장["쪽번호"], "콩", 역할="분석", 이름="조사", 일="보상이 어디 쓰이나")
        뒤 = self.나물(self.대장["쪽번호"], "콩", 역할="검토", 이름="검토", 일="조사 결과 검토", 먼저=앞["번호"])
        self.assertTrue(뒤.get("됨"), 뒤)
        열 = self.일꾼("열것", 방=self.대장["쪽번호"])["일꾼"]
        self.assertEqual(열["번호"], 앞["번호"], "앞 일꾼부터")
        self.assertIsNone(self.일꾼("열것", 방=self.대장["쪽번호"])["일꾼"], "앞이 안 끝났으면 뒤는 안 연다")
        self.일꾼("일감", 번호=앞["번호"])
        self.일꾼("결과", 번호=앞["번호"], 글="보상은 sim/보상.py 1줄에서만 쓰임")
        열 = self.일꾼("열것", 방=self.대장["쪽번호"])["일꾼"]
        self.assertEqual(열["번호"], 뒤["번호"], "앞이 끝나면 뒤가 열린다")
        일감 = self.일꾼("일감", 번호=뒤["번호"])
        self.assertIn("1줄에서만 쓰임", 일감["글"], "뒤 일꾼은 앞 일꾼 결과를 받는다")

    def test_앞이_실패하면_뒤도_실패_실패만다시(self):
        앞 = self.나물(self.대장["쪽번호"], "콩", 역할="분석", 이름="조사", 일="조사")
        뒤 = self.나물(self.대장["쪽번호"], "콩", 역할="검토", 이름="검토", 일="검토", 먼저=앞["번호"])
        self.일꾼("열것", 방=self.대장["쪽번호"])
        self.일꾼("일감", 번호=앞["번호"])
        self.일꾼("결과", 번호=앞["번호"], 실패=True, 글="헛돎")
        self.일꾼("열것", 방=self.대장["쪽번호"])
        목록 = {w["번호"]: w["상태"] for w in self.나물(self.대장["쪽번호"], "팥")["일꾼들"]}
        self.assertEqual(목록[뒤["번호"]], "실패", "앞이 실패하면 뒤도 실패")
        다시 = self.나물(self.대장["쪽번호"], "팥", 상태="실패만다시")
        self.assertEqual(다시.get("개수"), 2, 다시)
        목록 = {w["번호"]: w["상태"] for w in self.나물(self.대장["쪽번호"], "팥")["일꾼들"]}
        self.assertEqual((목록[앞["번호"]], 목록[뒤["번호"]]), ("대기", "대기"))

    def test_열두명까지만_돌고_열셋째는_줄선다(self):
        번호들 = [self.나물(self.대장["쪽번호"], "콩", 역할="분석", 이름=f"조사{i}", 일="조사")["번호"] for i in range(13)]
        열린 = [self.일꾼("열것", 방=self.대장["쪽번호"])["일꾼"] for _ in range(13)]
        self.assertEqual(sum(1 for x in 열린 if x), 12, "동시에 열두 명만 연다")
        self.일꾼("일감", 번호=번호들[0])
        self.일꾼("결과", 번호=번호들[0], 글="끝")
        열셋째 = self.일꾼("열것", 방=self.대장["쪽번호"])["일꾼"]
        self.assertEqual(열셋째["번호"], 번호들[12], "하나 끝나면 줄 선 열셋째를 연다")


if __name__ == "__main__":
    unittest.main(verbosity=2)
