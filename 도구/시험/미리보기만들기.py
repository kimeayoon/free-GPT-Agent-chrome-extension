# -*- coding: utf-8 -*-
"""판 미리보기 — 크롬 확장 없이 판(panel)을 눈으로 보려고 한 장으로 합친다.

확장으로 띄우면 고칠 때마다 새로고침 → 사이드 패널 열기 를 해야 해서
그림을 다듬기가 아주 느리다. 그래서 panel.html·panel.js 를 그대로 읽어
가짜 서버를 물린 한 장짜리 html 을 만든다.

  돌리는 법:  python 도구▸시험▸미리보기만들기.py
  결과     :  <임시폴더>/판미리보기.html  (경로를 찍어 준다)

주의: 미리보기는 '보기' 전용이다. 진짜 동작은 확장에서 확인한다.
"""

import argparse
import tempfile
from pathlib import Path

여기 = Path(__file__).resolve().parent
확장칸 = 여기.parent.parent / "확장"

가짜서버 = r'''
<script>
// ── 가짜 크롬 ──────────────────────────────────────────────
// 판이 부르는 것만 흉내 낸다. 진짜 서버도 ChatGPT 탭도 없다.
const 가짜나무 = {
  됨: true,
  폴더들: [
    { 쪽번호: 'f1', 이름: 'siro-ai', 있음: true, 방들: [
      { 쪽번호: 'r1', 이름: '발로란트 AI', 지금: true, 마지막: '09-16 14:02' },
      { 쪽번호: 'r2', 이름: '화면 읽기 실험', 지금: false, 마지막: '09-15 21:40' },
    ] },
    { 쪽번호: 'f2', 이름: 'gpt 웹 코덱스로 만들기', 있음: true, 방들: [
      { 쪽번호: 'r3', 이름: '판 고치기', 지금: false, 마지막: '09-16 11:20' },
    ] },
  ],
  지금방: 'r1', 지금방이름: '발로란트 AI', 대기: [],
  대화: [
    { 종류: '사용자', 글: '발로란트 화면 읽는 것부터 만들어줘', 때: '2026-09-16 14:00' },
    { 종류: 'gpt', 글: [
        '화면 읽기부터 잡겠습니다.',
        '',
        '## 무엇을 쓸지',
        '',
        '| 것 | 고른 것 | 왜 |',
        '|---|---|---|',
        '| 화면 잡기 | **mss** | `dxcam` 보다 설치가 쉽습니다 |',
        '| 찾기 | **YOLOv8n** | 작고 빠릅니다 |',
        '| 붙이기 | `torch` | CUDA 를 씁니다 |',
        '',
        '먼저 지금 구조를 봅니다.',
      ].join('\n'), 때: '2026-09-16 14:00' },
    { 종류: '도구', 때: '2026-09-16 14:01', 글: JSON.stringify({
        이름: '구조 보기', 나물: '가지', 대상: 'G:/siro-ai', 성공: true,
        꼬리: '12개', 걸린ms: 34,
        미리: { 갈래: '나무', 줄들: ['siro-ai/', '  src/', '    core.py', '    보기.py', '  README.md'], 잘림: false } }) },
    { 종류: '도구', 때: '2026-09-16 14:01', 글: JSON.stringify({
        이름: '내용 보기', 나물: '열무', 대상: 'src/core.py', 성공: true,
        꼬리: '120줄', 걸린ms: 12,
        미리: { 갈래: '글', 줄들: ['import mss', 'import numpy as np', '', 'def 화면잡기():', '    return None'], 잘림: true } }) },
    { 종류: '도구', 때: '2026-09-16 14:02', 글: JSON.stringify({
        이름: '일부 고치기', 나물: '부추', 대상: 'src/core.py', 성공: true,
        꼬리: '+4 -1', 걸린ms: 8,
        귀띔: '바꾼 뒤에는 도라지로 한 번 돌려 보고 끝내세요.',
        차이: { 줄들: [
          '@@ -1,5 +1,8 @@',
          ' import mss',
          ' import numpy as np',
          '-def 화면잡기():',
          '+def 화면잡기(칸=None):',
          '+    """칸을 안 주면 주 화면 전체."""',
          '+    with mss.mss() as 잡개:',
          '+        return np.array(잡개.grab(칸 or 잡개.monitors[1]))',
        ], 잘림: false } }) },
    { 종류: '도구', 때: '2026-09-16 14:02', 글: JSON.stringify({
        이름: '돌려보기', 나물: '도라지', 대상: 'python -c "import src.core"', 성공: false,
        꼬리: 'ModuleNotFoundError: mss', 걸린ms: 420,
        미리: { 갈래: '탈', 줄들: ['ModuleNotFoundError: No module named \'mss\'', '먼저 도토리로 받아오기를 요청하세요.'], 잘림: false } }) },
    { 종류: '요약', 때: '2026-09-16 14:02', 글: JSON.stringify({
        목록: [{ 밭: 'G:/siro-ai/src/core.py', 더한줄: 4, 뺀줄: 1, 번: 1 }] }) },
  ],
};

const 가짜계획 = { 됨: true, 일: '발로란트를 스스로 하는 AI', 진도: '1/4', 차례: [
  { 이름: '화면 읽기', 상태: '끝' },
  { 이름: '적 찾기 (YOLO)', 상태: '하는중', 쪽: 'mss 받아오기 기다리는 중' },
  { 이름: '조준 붙이기', 상태: '기다림' },
  { 이름: '판단 붙이기', 상태: '기다림' },
] };

const 가짜파일 = {
  'G:/siro-ai': [
    { 이름: 'src', 밭: 'G:/siro-ai/src', 칸인가: true, 크기: 0 },
    { 이름: 'models', 밭: 'G:/siro-ai/models', 칸인가: true, 크기: 0 },
    { 이름: 'README.md', 밭: 'G:/siro-ai/README.md', 칸인가: false, 크기: 1240 },
    { 이름: 'requirements.txt', 밭: 'G:/siro-ai/requirements.txt', 칸인가: false, 크기: 180 },
    { 이름: 'shot.png', 밭: 'G:/siro-ai/shot.png', 칸인가: false, 크기: 402000 },
  ],
  'G:/siro-ai/src': [
    { 이름: 'core.py', 밭: 'G:/siro-ai/src/core.py', 칸인가: false, 크기: 3400 },
    { 이름: '보기.py', 밭: 'G:/siro-ai/src/보기.py', 칸인가: false, 크기: 900 },
  ],
  'G:/siro-ai/models': [
    { 이름: 'yolov8n.pt', 밭: 'G:/siro-ai/models/yolov8n.pt', 칸인가: false, 크기: 6200000 },
  ],
  '방': [
    { 이름: '기억.md', 밭: '방/기억.md', 칸인가: false, 크기: 1122 },
    { 이름: '차례.json', 밭: '방/차례.json', 칸인가: false, 크기: 480 },
  ],
};

window.chrome = {
  runtime: {
    onMessage: { addListener: () => {} },
    sendMessage: async (쪽지) => {
      if (쪽지.종류 === '서버확인') {
        return { success: true, version: '1.18.0', 도구목록: new Array(26), 등급: '전부' };
      }
      if (쪽지.종류 === '방나무') return 가짜나무;
      if (쪽지.종류 === '계획보기') return 가짜계획;
      if (쪽지.종류 === '받아오기목록') return { 됨: true, 기다림: [] };
      if (쪽지.종류 === '칸보기') {
        const 몸 = 쪽지.몸통 || {};
        const 열쇠 = 몸.어디 === '방' ? '방' : (몸.밭 || 'G:/siro-ai');
        return { 됨: true, 밭: 열쇠, 것들: 가짜파일[열쇠] || [] };
      }
      if (쪽지.종류 === '도구실행') {
        const 요 = 쪽지.요청 || {};
        if (요.나물 === '열무') {
          if (/\.md$/i.test(요.밭 || '')) {
            const 글 = [
              '# 대화 지침 v1.7', '', '## 붙여넣는 법', '',
              '아래 울타리 안쪽만 복사해서 ChatGPT 프로젝트 지침에 넣으세요. **이전 내용은 지우고 교체합니다.**',
              '', '## 나물 26개', '',
              '| 나물 | 하는 일 | 나물 | 하는 일 |', '|---|---|---|---|',
              '| 숙주 | 이어하기 | 시금치 | 치우기 |', '| 더덕 | 기억 보기 | 도라지 | 돌려보기 |',
              '| 열무 | 내용 보기 | 감자 | 차례 세우기 |',
            ].join('\n');
            return { 됨: true, 총줄: 11, 속: 글 };
          }
          if (/\.json$/i.test(요.밭 || '')) {
            return { 됨: true, 총줄: 6, 속: '{\n  "일": "발로란트 AI",\n  "차례": [\n    {"이름": "화면 읽기", "상태": "끝"}\n  ]\n}' };
          }
          return { 됨: true, 총줄: 2400,
                   속: 'import mss\nimport numpy as np\n\n\ndef 화면잡기(칸=None):\n    """칸을 안 주면 주 화면 전체."""\n    with mss.mss() as 잡개:\n        return np.array(잡개.grab(칸 or 잡개.monitors[1]))' };
        }
        if (요.나물 === '미역') {
          return { 됨: true, 건수: 2, 보관목록: [
            { 때: '20260916-140233-451', 크기: 3400, 줄수: 118 },
            { 때: '20260916-135901-002', 크기: 3200, 줄수: 110 },
          ] };
        }
        return { 됨: true };
      }
      return { 됨: true };
    },
  },
  tabs: {
    query: async () => [{ id: 1 }],
    sendMessage: async () => ({ 됨: true, 켜짐: true }),
  },
};
</script>
'''


# ── 진짜 서버에 붙는 미리보기 (읽기만) ─────────────────────────
# 사용자 PC 에서 도는 진짜 서버의 진짜 자료로 판을 그린다.
# 무엇이든 바꾸는 요청(방 고르기·대화 남기기·폴더 고르기·고치는 나물)은 여기서 막는다.
# (한 번 확인하려고 /room-of-chat 을 보냈다가 사용자 방의 주인을 바꿔 버린 적이 있다)
진짜서버 = r'''
<script>
const 브리지 = 'http://127.0.0.1:8765';
const 읽는나물 = ['열무', '가지', '미나리', '버섯', '토란', '더덕'];

async function 가져(길) {
  return (await fetch(브리지 + 길)).json();
}
async function 보내(길, 몸) {
  return (await fetch(브리지 + 길, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(몸 || {}) })).json();
}

window.chrome = {
  runtime: {
    onMessage: { addListener: () => {} },
    sendMessage: async (쪽지) => {
      // 파이썬이 떠 온 진짜 자료에서 찾는다(파일 주소 페이지는 127.0.0.1 에 못 닿는다)
      const 떠 = 떠온자료;
      try {
        switch (쪽지.종류) {
          case '서버확인': return 떠.핑;
          case '방나무': return 떠.나무;
          case '계획보기': return 떠.계획;
          case '받아오기목록': return 떠.받아오기;
          case '칸보기': {
            const 몸 = 쪽지.몸통 || {};
            const 열쇠 = 몸.밭 || (몸.어디 === '방' ? '@방' : '@일');
            return 떠.칸[열쇠] || { 됨: false, 탈: '미리보기에 안 떠 온 칸: ' + 열쇠 };
          }
          case '도구실행': {
            const 요 = 쪽지.요청 || {};
            if (!읽는나물.includes(요.나물)) {
              return { 됨: false, 탈: '미리보기는 읽기만 합니다: ' + 요.나물 };
            }
            return 떠.파일[요.밭] || { 됨: false, 탈: '미리보기에 안 떠 온 파일: ' + 요.밭 };
          }
          default:
            console.warn('[미리보기] 막음:', 쪽지.종류);
            return { 됨: false, 탈: '미리보기는 읽기만 합니다: ' + 쪽지.종류 };
        }
      } catch (e) {
        return { 됨: false, 탈: '진짜 서버에 못 닿음: ' + e.message, 서버꺼짐: true };
      }
    },
  },
  tabs: {
    query: async () => [{ id: 1 }],
    sendMessage: async () => ({ 됨: false }),
  },
};
</script>
'''


def 진짜자료담기() -> dict:
    """사용자 PC 의 진짜 서버에서 읽기만 해서 한 벌 떠 온다.

    미리보기 창(파일 주소로 연 페이지)은 127.0.0.1 에 못 닿는다. 그래서 파이썬이
    대신 읽어 와 html 에 박아 넣는다. 바꾸는 요청은 하나도 안 보낸다.
    """
    import json
    import urllib.request

    브리지 = "http://127.0.0.1:8765"

    def 가져(길):
        return json.loads(urllib.request.urlopen(브리지 + 길, timeout=5).read().decode("utf-8"))

    def 보내(길, 몸):
        요 = urllib.request.Request(브리지 + 길, method="POST",
                                   data=json.dumps(몸, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(요, timeout=10).read().decode("utf-8"))

    자료 = {"핑": 가져("/ping"), "나무": 가져("/rooms"), "계획": 가져("/plan"),
            "받아오기": 가져("/installs"), "칸": {}, "파일": {}}

    def 칸담기(열쇠, 몸, 깊이):
        답 = 보내("/dir", 몸)
        자료["칸"][열쇠] = 답
        for 것 in (답.get("것들") or [])[:60]:
            if 것.get("칸인가") and 깊이 < 2:
                칸담기(것["밭"], {"밭": 것["밭"]}, 깊이 + 1)
            elif not 것.get("칸인가") and (것.get("크기") or 0) < 200_000:
                자료["파일"][것["밭"]] = 보내("/tool", {"나물": "열무", "밭": 것["밭"],
                                                       "첫줄": 1, "끝줄": 2000})

    칸담기("@일", {"어디": "일"}, 0)
    칸담기("@방", {"어디": "방"}, 0)
    return 자료


def 만들기(자리: Path, 진짜: bool = False) -> Path:
    html = (확장칸 / "panel.html").read_text(encoding="utf-8")

    합친것 = []
    for 이름 in ("protocol.js", "parser.js", "i18n.js", "panel.js"):
        글 = (확장칸 / 이름).read_text(encoding="utf-8")
        합친것.append(f"<script>\n// ── {이름} ──\n{글}\n</script>")

    # 따로 불러오던 것을 통째로 넣는다(파일 주소로 열어도 되게)
    html = html.replace('<script src="protocol.js"></script>', "")
    html = html.replace('<script src="parser.js"></script>', "")
    html = html.replace('<script src="i18n.js"></script>', "")
    html = html.replace('<script src="panel.js"></script>', "")
    끼울것 = 가짜서버
    if 진짜:
        import json
        끼울것 = ("<script>const 떠온자료 = "
                  + json.dumps(진짜자료담기(), ensure_ascii=False).replace("</", "<\\/")
                  + ";</script>\n" + 진짜서버)
    html = html.replace("</body>", 끼울것 + "\n".join(합친것) + "\n</body>")

    자리.write_text(html, encoding="utf-8")
    return 자리


if __name__ == "__main__":
    받개 = argparse.ArgumentParser()
    받개.add_argument("--자리", default="")
    받개.add_argument("--진짜", action="store_true", help="사용자 PC 의 진짜 서버에 읽기만 붙는다")
    인자 = 받개.parse_args()

    낼곳 = (Path(인자.자리) if 인자.자리
            else Path(tempfile.gettempdir()) / "판미리보기.html")
    print(만들기(낼곳, 인자.진짜))
