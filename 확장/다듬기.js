// 화면 다듬기 — ChatGPT 화면에 날것으로 보이던 에이전트의 도구 호출(【바구니】 코드블록)과
// 결과(【소쿠리】 말풍선)를 Claude·ChatGPT 처럼 한 줄 카드로 접어 보여 준다.
//
//   도구 ▸ 내용 보기 · sim/evaluate_combat.py        ← GPT 가 보낸 바구니(코드블록) 자리
//   결과 ▸ 내용 보기 · sim/evaluate_combat.py        ← 내가 자동으로 보낸 소쿠리(말풍선) 자리
//
// 카드를 누르면 원문이 펼쳐지고, 펼친 카드의 윗줄을 누르면 다시 접힌다.
// 글을 지우거나 숨기지 않는다: 내용은 그대로 DOM 에 있고(높이만 0), 그래서 바구니 읽기·되돌림이
// 쓰는 innerText 에도 그대로 잡힌다. ChatGPT 가 UI 를 바꿔도 못 찾을 뿐 아무것도 망가지지 않는다.

const 다듬기스타일아이디 = 'gla-다듬기-스타일';
const 다듬기스타일 = `
[data-gla] { position: relative; }
[data-gla]::before {
  content: attr(data-gla-이름표);
  display: block; width: fit-content; max-width: 100%; box-sizing: border-box;
  padding: 6px 12px; font-size: 13px; line-height: 1.4;
  border: 1px solid rgba(128,128,128,.35); border-radius: 10px;
  background: rgba(128,128,128,.08); opacity: .8; cursor: pointer;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
[data-gla="소쿠리"]::before { margin-left: auto; }
[data-gla]:not([data-gla-열림]) {
  background: none !important; border: 0 !important; padding: 0 !important;
  min-height: 0 !important; box-shadow: none !important;
}
[data-gla]:not([data-gla-열림]) > * {
  max-height: 0 !important; overflow: hidden !important; opacity: 0 !important;
  margin: 0 !important; padding: 0 !important; border: 0 !important; pointer-events: none !important;
}
[data-gla][data-gla-열림]::before { margin-bottom: 6px; opacity: .6; }
`;

// 바구니 글에서 카드에 쓸 이름표를 뽑는다. 여러 개면 '… 외 N건'.
function 바구니이름표(글) {
  const 나물들 = [];
  const 정규식 = /^[ \t]*나물[ \t]+(\S+)/gm;
  let m;
  while ((m = 정규식.exec(글)) !== null) 나물들.push(m[1]);
  const 첫 = /^[ \t]*나물[ \t]+(\S+)[^\n]*\n([\s\S]*)/m.exec(글);
  let 대상 = '';
  if (첫) {
    const 줄 = /^[ \t]*(?:밭|불|향|일)[ \t]+(.+)$/m.exec(첫[2]);
    if (줄) 대상 = 줄[1].trim().replace(/[ \t]*▸[ \t]*/g, '/');
  }
  const 끝났나 = 글.indexOf(규약.요청끝) !== -1;
  let 이름표 = '도구 ▸ ';
  if (!나물들.length) {
    이름표 += 끝났나 ? '명령' : '명령 쓰는 중…';
    return 이름표;
  }
  이름표 += 사람말(나물들[0]);
  if (대상) 이름표 += ' · ' + (대상.length > 70 ? 대상.slice(0, 69) + '…' : 대상);
  if (나물들.length > 1) 이름표 += ' 외 ' + (나물들.length - 1) + '건';
  if (!끝났나) 이름표 += ' …';
  return 이름표;
}

// 내가 자동으로 보낸 소쿠리(결과)·재촉에서 이름표를 뽑는다.
function 소쿠리이름표(글) {
  if (글.indexOf('【에이전트 자동 요청】') !== -1 && 글.indexOf(규약.응답시작) === -1) return '자동 ▸ 결과를 보고 이어서 하라고 재촉';
  const 첨부 = /첨부 파일[ \t]+(\S+)/.exec(글);
  const 나물 = /^[ \t]*나물[ \t]+(\S+)/m.exec(글);
  const 밭 = /^[ \t]*(?:밭|불|향|일)[ \t]+(.+)$/m.exec(글);
  const 실패 = /^[ \t]*됨[ \t]+거짓/m.test(글);
  let 이름표 = '결과 ▸ ';
  if (나물) {
    이름표 += 사람말(나물[1]);
    if (밭) {
      const 대상 = 밭[1].trim();
      이름표 += ' · ' + (대상.length > 70 ? 대상.slice(0, 69) + '…' : 대상);
    }
  } else if (첨부) {
    이름표 += '첨부 파일 ' + 첨부[1];
  } else {
    이름표 += '도구 결과';
  }
  if (실패) 이름표 += ' · 실패';
  return 이름표;
}

function _사용자말인가(el) {
  try {
    return 셀렉터.사용자메시지.some((s) => el.closest(s));
  } catch (e) {
    return false;
  }
}

function _표시(el, 종류, 이름표) {
  if (el.getAttribute('data-gla') !== 종류) el.setAttribute('data-gla', 종류);
  if (el.getAttribute('data-gla-이름표') !== 이름표) el.setAttribute('data-gla-이름표', 이름표);
}

function _스타일넣기(문서) {
  if (문서.getElementById(다듬기스타일아이디)) return;
  const 태그 = 문서.createElement('style');
  태그.id = 다듬기스타일아이디;
  태그.textContent = 다듬기스타일;
  (문서.head || 문서.documentElement).appendChild(태그);
}

let _눌림달았나 = false;
function _눌림달기(문서) {
  if (_눌림달았나) return;
  _눌림달았나 = true;
  // 접힌 카드는 아무 데나 누르면 열린다. 열린 카드는 윗줄(카드 자신이 눌린 것)을 누를 때만 접는다
  // (원문을 드래그하거나 복사 단추를 누를 때 접히지 않게).
  문서.addEventListener('click', (사건) => {
    const 카드 = 사건.target && 사건.target.closest ? 사건.target.closest('[data-gla]') : null;
    if (!카드) return;
    if (!카드.hasAttribute('data-gla-열림')) {
      카드.setAttribute('data-gla-열림', '1');
    } else if (사건.target === 카드) {
      카드.removeAttribute('data-gla-열림');
    }
  }, true);
}

const _본것 = new WeakMap();

// 화면의 바구니·소쿠리를 찾아 카드로 표시한다. 여러 번 불러도 같은 결과(이미 한 것은 건너뜀).
function 화면다듬기(문서) {
  문서 = 문서 || document;
  _스타일넣기(문서);
  _눌림달기(문서);

  // ① 바구니 — GPT 답 안의 코드블록
  const 블록들 = 문서.querySelectorAll('[data-markdown-copy="code-block"], pre');
  for (const el of Array.from(블록들)) {
    const 위 = el.parentElement && el.parentElement.closest ? el.parentElement.closest('[data-gla="바구니"]') : null;
    if (위) continue;                                   // 이미 카드 안쪽(바깥 상자가 카드)
    const 글 = el.textContent || '';
    const 앞 = _본것.get(el);
    if (앞 === 글.length) continue;
    _본것.set(el, 글.length);
    if (글.indexOf(규약.요청시작) === -1 || _사용자말인가(el)) continue;
    _표시(el, '바구니', 바구니이름표(글));
  }

  // ② 소쿠리·재촉 — 내가 자동으로 보낸 말풍선
  const 말들 = 문서.querySelectorAll(셀렉터.사용자메시지.join(', '));
  for (const el of Array.from(말들)) {
    const 글 = el.textContent || '';
    const 앞 = _본것.get(el);
    if (앞 === 글.length) continue;
    _본것.set(el, 글.length);
    const 소쿠리 = 글.indexOf(규약.응답시작) !== -1 && 글.indexOf('로컬 에이전트') !== -1;
    const 재촉 = 글.indexOf('【에이전트 자동 요청】') !== -1;
    if (!소쿠리 && !재촉) continue;
    _표시(el, '소쿠리', 소쿠리이름표(글));
  }
}
