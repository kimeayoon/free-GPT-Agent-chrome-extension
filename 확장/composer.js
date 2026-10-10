// 입력창에 텍스트를 넣고 전송 버튼을 누른다.
// ChatGPT 입력창은 ProseMirror(contenteditable)라서 value 대입이 안 먹는다.
// → paste 이벤트를 흉내내는 방식이 가장 잘 붙는다. 실패하면 execCommand 로 폴백.

// 대기는 setTimeout 하나에만 맡기지 않는다.
// 크롬은 안 보이는 탭의 타이머를 1초 단위로 늦추고, 5분 넘게 숨어 있으면 1분에 한 번만 돌린다.
// 그러면 "첨부가 붙을 때까지 기다리기"·"전송 단추가 켜질 때까지 기다리기" 같은 안쪽 대기가
// 한 번에 몇 분씩 걸려서, 딴 탭에 가 있으면 진행이 거의 안 됐다.
// 서비스 워커의 박동(400ms 마다 오는 메시지)은 안 늦춰지므로, 박동이 올 때도 '때가 됐나' 를 보고 깨운다.
// 눈에 보이는 탭에서는 타이머가 먼저 울려 예전과 똑같이 움직인다.
const 기다리는중 = new Set();

function 잠깐(ms) {
  return new Promise((풀기) => {
    const 항 = { 끝: Date.now() + ms, 타이머: null };
    항.깨우기 = () => {
      clearTimeout(항.타이머);
      기다리는중.delete(항);
      풀기();
    };
    기다리는중.add(항);
    항.타이머 = setTimeout(항.깨우기, ms);
  });
}

// 박동이 올 때마다 부른다 — 때가 된 대기를 깨운다
function 박동으로깨우기() {
  const 지금 = Date.now();
  for (const 항 of Array.from(기다리는중)) {
    if (항.끝 <= 지금) 항.깨우기();
  }
}

function 입력창비우기(el) {
  // 편집 불가능한 요소에 execCommand('delete') 를 쓰면 화면의 메시지가 지워진다.
  if (!편집가능한가(el)) {
    throw new Error('편집 불가능한 요소입니다. 입력창 셀렉터가 잘못 잡혔습니다.');
  }
  el.focus();
  const 선택 = window.getSelection();
  const 범위 = document.createRange();
  범위.selectNodeContents(el);
  선택.removeAllRanges();
  선택.addRange(범위);
  document.execCommand('delete', false, null);
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

// textContent 로 본다. innerText 는 읽을 때마다 화면 배치를 다시 계산해서,
// 입력칸 글이 길면 0.15초마다 읽는 것만으로도 페이지가 무거워진다.
function 입력칸글(el) {
  if (!el) return '';
  if (typeof el.textContent === 'string' && el.textContent) return el.textContent;
  return el.innerText || el.value || '';
}

function 들어갔나(el, 텍스트) {
  const 빈칸뺌 = (글) => String(글 || '').replace(/\s+/g, '');
  const 안에 = 빈칸뺌(입력칸글(el));
  const 넣을것 = 빈칸뺌(텍스트);
  return !!안에 && 안에 === 넣을것;
}

function 전송가능한가(버튼) {
  return !!버튼 && !정지단추인가(버튼) && !버튼.disabled
    && 버튼.getAttribute('aria-disabled') !== 'true'
    && 버튼.getAttribute('data-visually-disabled') === null;
}

function 편집기가입력받았나(버튼) {
  return !!버튼 && 버튼.getAttribute('aria-disabled') !== 'true'
    && 버튼.getAttribute('data-visually-disabled') === null;
}

async function 입력인정기다리기(최대대기ms = 700) {
  const 시작 = Date.now();
  while (Date.now() - 시작 < 최대대기ms) {
    if (편집기가입력받았나(찾기(셀렉터.전송버튼))) return true;
    await 잠깐(50);
  }
  return false;
}

async function 텍스트넣기(el, 텍스트) {
  el.focus();

  // textarea 인 경우 (구버전 UI)
  if (el.tagName === 'TEXTAREA') {
    const 세터 = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype, 'value'
    ).set;
    세터.call(el, 텍스트);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    return 들어갔나(el, 텍스트) && await 입력인정기다리기();
  }

  입력창비우기(el);

  // 1순위: paste 이벤트 (여러 줄 텍스트가 안 깨진다)
  try {
    const dt = new DataTransfer();
    dt.setData('text/plain', 텍스트);
    el.dispatchEvent(new ClipboardEvent('paste', {
      clipboardData: dt,
      bubbles: true,
      cancelable: true,
    }));
    el.dispatchEvent(new Event('input', { bubbles: true }));
  } catch (e) {
    /* 무시하고 폴백 */
  }

  // 화면에 글만 보이고 ChatGPT 내부 편집기는 빈 것으로 보는 경우가 있다.
  // 전송 단추까지 활성화돼야 정상 입력으로 인정한다.
  if (들어갔나(el, 텍스트) && await 입력인정기다리기()) return true;

  // 2순위: execCommand insertText
  입력창비우기(el);
  document.execCommand('insertText', false, 텍스트);
  el.dispatchEvent(new Event('input', { bubbles: true }));

  return 들어갔나(el, 텍스트) && await 입력인정기다리기(1200);
}

// 정지 단추는 전송 단추 자리에 뜬다. 무엇으로 잡았든 정지 단추면 절대 안 누른다.
function 정지단추인가(버튼) {
  if (!버튼 || !버튼.getAttribute) return false;
  const 표 = String(버튼.getAttribute('data-testid') || '');
  const 이름 = String(버튼.getAttribute('aria-label') || '');
  return 표 === 'stop-button' || /중지|정지|stop/i.test(이름);
}

async function 전송버튼누르기(최대대기ms = 5000) {
  const 시작 = Date.now();
  while (Date.now() - 시작 < 최대대기ms) {
    const 버튼 = 찾기(셀렉터.전송버튼);
    if (전송가능한가(버튼)) {
      버튼.click();
      return true;
    }
    await 잠깐(100);
  }
  return false;
}

// 두 번 겹쳐 들어가는 것을 막는다.
// 넣고 보내는 사이에 또 넣으면, 하나는 보내지고 하나는 칸에 남는다.
let 넣는중 = false;
let 마지막실패지문 = '';
let 마지막실패때 = 0;
const 같은글중복방지ms = 12000;

// 첫 줄과 글자 수만 비교하면 서로 다른 결과를 같은 글로 오인한다.
// 긴 결과 전체를 저장하지 않고, 전체 글을 간단한 32비트 지문으로 줄인다.
function 전송지문만들기(텍스트) {
  const 글 = String(텍스트 || '');
  let 해시 = 2166136261;
  for (let i = 0; i < 글.length; i++) {
    해시 ^= 글.charCodeAt(i);
    해시 = Math.imul(해시, 16777619);
  }
  return 글.length + '|' + (해시 >>> 0);
}

// 텍스트를 입력창에 넣고 전송까지 한다. 성공 여부를 돌려준다.
async function 입력하고전송(텍스트, 강제 = false) {
  if (넣는중) {
    console.warn('[로컬에이전트] 이미 넣는 중이라 건너뜁니다.');
    return false;
  }

  const 입력창 = 입력창찾기();
  if (!입력창) {
    console.error('[로컬에이전트] 편집 가능한 입력창을 못 찾았습니다. selectors.js 를 확인하세요.');
    return false;
  }

  // 사람이 치던 글이 있으면 덮어쓰지 않는다. 우리 것(【소쿠리】)만 지운다.
  const 있던글 = (입력창.innerText || 입력창.value || '').trim();
  if (있던글 && 있던글.indexOf(규약.응답시작) === -1) {
    console.warn('[로컬에이전트] 사람이 쓰던 글이 있어 기다립니다.');
    return false;
  }

  const 전송지문 = 전송지문만들기(텍스트);
  if (!강제 && 전송지문 === 마지막실패지문 && Date.now() - 마지막실패때 < 같은글중복방지ms) {
    console.warn('[로컬에이전트] 같은 글의 전송이 방금 실패했으므로 자동 중복 전송을 막습니다.');
    return false;
  }

  넣는중 = true;
  try {
    const 보냄 = await _넣고보내기(입력창, 텍스트);
    if (!보냄) {
      // 버튼만 눌리고 글이 입력창에 남은 경우에만 잠근다.
      // 성공한 같은 글은 다음 독립 결과로 다시 보낼 수 있어야 한다.
      마지막실패지문 = 전송지문;
      마지막실패때 = Date.now();
    }
    return 보냄;
  } finally {
    넣는중 = false;
  }
}

// 단추를 눌렀다고 보내진 것이 아니다. 새로고침 직후엔 화면이 덜 준비돼 눌러도
// 안 가고 글만 입력칸에 남았다(실제로 그랬다). 입력칸에서 글이 사라져야 보낸 것이다.
const 보냄확인ms = 4000;

// ── 이미 보내졌나 ─────────────────────────────────────────────
// 대화가 길면 ChatGPT 가 느려서, 보내진 뒤에도 4초 넘게 입력칸에 글이 남아 있었다.
// 그걸 '안 갔다' 로 보고 다시 보내 소쿠리가 두 번 올라갔다.
// 그래서 입력칸만 보지 않고, 화면의 '내 말' 칸에 이번 글이 새로 올라왔는지도 본다.

function 내말표시() {
  try {
    const 목록 = 모두찾기(셀렉터.사용자메시지);
    const el = 목록.length ? 목록[목록.length - 1] : null;
    return {
      수: 목록.length,
      번호: el && el.getAttribute
        ? String(el.getAttribute('data-chatgpt-search-message-ids') || el.getAttribute('data-message-id') || '')
        : '',
      글: el ? String(el.textContent || el.innerText || '') : '',
    };
  } catch (e) {
    return { 수: 0, 번호: '', 글: '' };
  }
}

function 올라갔나(앞, 텍스트) {
  const 지금 = 내말표시();
  if (지금.수 === 앞.수 && 지금.번호 === 앞.번호) return false;   // 새 내 말이 없다
  if (!지금.수) return false;
  const 빈칸뺌 = (글) => String(글 || '').replace(/\s+/g, '');
  const 머리 = 빈칸뺌((텍스트 || '').slice(0, 60));
  return !머리 || 빈칸뺌(지금.글).indexOf(머리) !== -1;
}

async function 입력칸에서사라졌나(입력창, 텍스트, 기다림ms, 앞) {
  const 끝 = Date.now() + 기다림ms;
  while (Date.now() < 끝) {
    if (!들어갔나(입력창, 텍스트)) return true;
    if (앞 && 올라갔나(앞, 텍스트)) return true;
    await 잠깐(150);
  }
  return !들어갔나(입력창, 텍스트) || !!(앞 && 올라갔나(앞, 텍스트));
}

async function _넣고보내기(입력창, 텍스트) {
  const 앞 = 내말표시();          // 보내기 전의 마지막 내 말
  // 글이 이미 입력칸에 있으면 다시 붙이지 않는다. 긴 글을 지웠다 붙였다 하면
  // 그것만으로 페이지가 뻗는다. 없을 때만 넣는다.
  if (!들어갔나(입력창, 텍스트)) {
    const 넣기성공 = await 텍스트넣기(입력창, 텍스트);
    if (!넣기성공) {
      // 화면에만 붙고 ChatGPT가 입력으로 인정하지 않은 글은 지운다.
      // 결과 원문은 상태.보낼것대기에 남아 있어 다시 시도할 수 있다.
      try { 입력창비우기(입력창); } catch (e) { /* 넘어간다 */ }
      console.error('[로컬에이전트] 입력창에 텍스트를 넣지 못했습니다.');
      return false;
    }
  }

  await 잠깐(120);      // 넣은 글이 화면에 반영될 만큼 기다린다
  const 눌렀나 = await 전송버튼누르기();
  if (!눌렀나) {
    // 단추를 못 찾으면 엔터로. UI 가 바뀌어 셀렉터가 빗나가도 살아남게.
    엔터로보내기(입력창);
  }

  // 실제 사용자 메시지로 올라가거나 입력칸에서 사라져야 성공이다.
  // 버튼만 눌린 상태를 성공으로 치면 같은 글이 입력칸에 남은 채 다음 결과와
  // 합쳐지거나, 다음 검사에서 같은 글을 또 보내게 된다.
  if (await 입력칸에서사라졌나(입력창, 텍스트, 보냄확인ms, 앞)) {
    return true;
  }
  try { 입력창비우기(입력창); } catch (e) { /* 결과는 내부에 남는다 */ }
  console.warn('[로컬에이전트] 버튼은 눌렀지만 사용자 메시지로 확인되지 않았습니다. 자동 재전송하지 않습니다.');
  return false;
}

// ── 파일로 보내기 ──────────────────────────────────────────────
// 긴 결과를 입력칸에 붙이면 ChatGPT 가 뻗고, 자르면 GPT 가 못 본다.
// 그래서 결과를 .txt 파일로 첨부하고 입력칸엔 한 줄 안내만 쓴다.
// 돌려주는 값:
//   '보냄'     보냈다
//   '파일안됨' 첨부부터 안 됐다. 아무것도 안 보냈으니 글로 보내도 된다
//   '실패'     첨부는 됐는데 보내졌는지 모른다. 두 번 가지 않게 다시 보내지 않는다
let 첨부기다림ms = 8000;
let 파일보냄확인ms = 15000;          // (시험에서 줄인다)
const 올리기기다림ms = 30000;

function 그림바이트(자료) {
  const 이진 = atob(String(자료 || ''));
  const 칸 = new Uint8Array(이진.length);
  for (let i = 0; i < 이진.length; i++) 칸[i] = 이진.charCodeAt(i);
  return 칸;
}

function 첨부단추들() {
  try { return 모두찾기(셀렉터.첨부단추); } catch (e) { return []; }
}

function 첨부됐나(이름) {
  return 첨부단추들().some((b) => (b.getAttribute('aria-label') || '') === 이름);
}

function 첨부지우기(이름) {
  const 지우개 = 첨부단추들().find((b) => (b.getAttribute('aria-label') || '') === 이름 + ' 제거');
  if (지우개) 지우개.click();
}

// 그림들 = [{이름, 종류, 자료(base64)}] — 결과 글 파일과 함께 붙는 그림(호박·오이). 올리는 동안 전송 단추가 잠기므로 그 기다림에 맡긴다.
async function 파일로전송(글, 이름, 안내글, 그림들 = []) {
  if (넣는중) return '실패';
  const 입력창 = 입력창찾기();
  const 칸 = 찾기(셀렉터.파일넣기);
  if (!입력창 || !칸) return '파일안됨';

  const 있던글 = (입력창.innerText || 입력창.value || '').trim();
  if (있던글 && 있던글.indexOf(규약.응답시작) === -1) {
    console.warn('[로컬에이전트] 사람이 쓰던 글이 있어 기다립니다.');
    return '실패';
  }

  넣는중 = true;
  try {
    try {
      const dt = new DataTransfer();
      dt.items.add(new File([글], 이름, { type: 'text/plain' }));
      for (const 그림 of (그림들 || [])) {
        dt.items.add(new File([그림바이트(그림.자료)], 그림.이름, { type: 그림.종류 || 'image/png' }));
      }
      칸.files = dt.files;
      칸.dispatchEvent(new Event('change', { bubbles: true }));
    } catch (e) {
      return '파일안됨';
    }

    // 첨부 카드가 떠야 붙은 것이다. 안 뜨면(올리기 횟수 제한 등) 아무것도 안 보낸 것이다.
    let 끝 = Date.now() + 첨부기다림ms;
    while (!첨부됐나(이름) && Date.now() < 끝) await 잠깐(150);
    if (!첨부됐나(이름)) return '파일안됨';

    const 앞 = 내말표시();
    if (있던글) { try { 입력창비우기(입력창); } catch (e) { /* 넘어간다 */ } }
    if (!(await 텍스트넣기(입력창, 안내글))) {
      첨부지우기(이름);
      return '파일안됨';
    }

    // 올리는 동안 보내기 단추가 잠긴다. 풀릴 때까지 기다린다.
    끝 = Date.now() + 올리기기다림ms;
    while (!전송가능한가(찾기(셀렉터.전송버튼)) && Date.now() < 끝) await 잠깐(200);
    if (!전송가능한가(찾기(셀렉터.전송버튼))) {
      첨부지우기(이름);
      try { 입력창비우기(입력창); } catch (e) { /* 넘어간다 */ }
      return '파일안됨';
    }
    찾기(셀렉터.전송버튼).click();

    끝 = Date.now() + 파일보냄확인ms;     // 긴 대화에선 올리고 비우는 데 4초 넘게 걸렸다
    while (Date.now() < 끝) {
      if (올라갔나(앞, 안내글) || (!첨부됐나(이름) && !들어갔나(입력창, 안내글))) return '보냄';
      await 잠깐(150);
    }
    if (올라갔나(앞, 안내글) || (!첨부됐나(이름) && !들어갔나(입력창, 안내글))) return '보냄';
    console.warn('[로컬에이전트] 파일 결과를 눌렀지만 보내졌는지 확인하지 못했습니다. 자동으로 다시 보내지 않습니다.');
    return '실패';
  } finally {
    넣는중 = false;
  }
}

// 전송 단추가 안 잡힐 때의 대비책.
// 입력창이 비워졌으면 보내진 것으로 본다.
function 엔터로보내기(el) {
  el.focus();
  for (const 종류 of ['keydown', 'keypress', 'keyup']) {
    el.dispatchEvent(new KeyboardEvent(종류, {
      key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
      bubbles: true, cancelable: true,
    }));
  }
  return !(el.innerText || el.value || '').trim();
}
