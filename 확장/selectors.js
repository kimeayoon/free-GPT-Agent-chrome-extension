// ChatGPT DOM 셀렉터 모음.
// OpenAI 가 UI 를 바꾸면 여기만 고치면 된다. 각 항목은 위에서부터 순서대로 시도한다.

const 셀렉터 = {
  // 어시스턴트(=GPT) 답변 덩어리
  // 2026-09 ChatGPT 가 data-message-author-role 을 없앴다. 지금은 메시지 덩어리에
  // data-chatgpt-search-unit-key="<턴>:<번>:assistant|user" 가 붙는다(형님 Chrome 에서 확인).
  어시스턴트메시지: [
    '[data-chatgpt-search-unit-key$=":assistant"]',
    '[data-message-author-role="assistant"]',
    'div.agent-turn',
    'article[data-testid^="conversation-turn"]',
  ],

  // 사람이 쓴 말 덩어리
  사용자메시지: [
    '[data-chatgpt-search-unit-key$=":user"]',
    '[data-message-author-role="user"]',
  ],

  // ChatGPT 가 '대화가 너무 깁니다' 같은 한도 안내를 띄우는 자리(추정 — 처음 뜰 때 확인 필요).
  // GPT 답 글은 보지 않는다. GPT 가 '새 대화를 시작하세요' 라고 말해도 넘기면 안 된다.
  한도안내: [
    '[role="alert"]',
    '[data-testid*="error"]',
    '.text-token-text-error',
  ],

  // 화면 위 이동 경로의 프로젝트 링크. href 에 프로젝트 번호, 글자에 이름이 같이 있다.
  // (탭 제목 앞부분은 'ChatGPT' 일 때가 있어 못 믿는다 — 묶음 이름이 'ChatGPT' 가 됐다)
  프로젝트경로: ['nav[aria-label="이동 경로"] a[href$="/project"]', 'nav[aria-label="Breadcrumb"] a[href$="/project"]'],

  // 내 말의 '메시지 편집'(연필). 누르면 그 말 자리에 편집 칸과 [취소](type=button)·[보내기](type=submit,
  // 글자 '보내기')가 생긴다. 입력칸의 보내기 단추는 글자 없이 이름표만 '보내기' 라 글자로 가른다.
  // (2026-09-30 형님 Chrome 에서 열었다 취소해 확인)
  메시지편집: ['button[aria-label="메시지 편집"]', 'button[aria-label="Edit message"]'],
  편집단추들: ['main button'],

  // 추론 수준. 입력칸의 'ChatGPT 모델 선택' 단추(글자 = 지금 수준)를 Enter 로 열면
  // 메뉴 안에 '파워' 막대(role=slider, 0=Instant·1=Medium·2=High)가 있다. ← → 로 옮긴다.
  // (2026-09-29 형님 Chrome 에서 확인. 가짜 pointerdown 으로는 안 열리고 Enter 로 열린다)
  추론단추: ['form button[aria-label="ChatGPT 모델 선택"]', 'button[aria-label="ChatGPT 모델 선택"]'],
  추론막대: ['[data-reasoning-slider="true"]'],
  // 모델 고르기. 같은 메뉴 안에 'GPT-6' · 'GPT-5.6 Sol' 같은 줄(role=menuitemradio, 고른 것은 aria-checked=true)이 있다.
  // '간단히 보기' 에서는 가려져 있지만 .click() 은 먹고, 눌러도 메뉴는 열린 채다.
  // (2026-10-11 형님 Chrome 에서 GPT-6 ↔ GPT-5.6 Sol 을 바꿨다 되돌려 확인)
  모델줄: ['[role="menu"] [role="menuitemradio"]'],

  // 파일 첨부 칸. 그림만 받는 칸(accept="image/*")이 따로 있어서 아무 파일이나 받는 것을 고른다.
  파일넣기: [
    'input[type="file"]:not([accept])',
    'input[type="file"][accept=""]',
  ],

  // 입력칸 위에 붙은 첨부 카드의 단추. aria-label 이 파일 이름('결과.txt'),
  // 지우기 단추는 '결과.txt 제거' 다(2026-09-27 형님 Chrome 에서 확인).
  첨부단추: [
    'form button[aria-label]',
  ],

  // 입력창
  입력창: [
    '#prompt-textarea',
    'div[contenteditable="true"][id*="prompt"]',
    'form div[contenteditable="true"]',
    'textarea[data-testid="prompt-textarea"]',
    'form textarea',
  ],

  // 전송 버튼
  전송버튼: [
    'button[data-testid="send-button"]',
    'button[aria-label="프롬프트 보내기"]',
    'button[aria-label="Send prompt"]',
    'button[aria-label*="Send"]',
    'button[aria-label*="보내기"]',
    // 'form button[type="submit"]' 는 뺐다. 쓰는 중엔 같은 자리의 정지 단추까지 잡혀
    // 다시 보내려다 정지를 눌렀다('생각 중단됨').
  ],

  // 이게 화면에 있으면 = 아직 답변 생성 중
  정지버튼: [
    'button[data-testid="stop-button"]',
    'button[aria-label="스트리밍 중지"]',
    'button[aria-label*="Stop"]',
    'button[aria-label*="중지"]',
  ],

  // 왼쪽 목록에서 지금 보고 있는 대화 항목.
  // 주소의 /c/<번호> 와 같은 링크를 찾아 그 글자를 방 이름으로 쓴다.
  // 페이지 제목에는 프로젝트 이름이 섞여 들어와서 못 쓴다.
  대화목록링크: ['nav a[href*="/c/"]', 'a[href*="/c/"]'],

  // 코드블록. 여기 텍스트만 들여쓰기가 보존된다.
  // 예전엔 <pre>, 지금은 <div data-markdown-copy="code-block"> 안의 <code>(pre 없음).
  코드블록: ['pre', '[data-markdown-copy="code-block"] code'],

  // 마지막 답변의 '다시 시도' 단추. UI 가 바뀌면 여기만 고치면 된다.
  다시시도버튼: [
    'button[data-testid="regenerate-thread-button"]',
    'button[aria-label*="다시 시도"]',
    'button[aria-label*="Regenerate"]',
    'button[data-testid*="regenerate"]',
  ],

  // 스트리밍 중인 답변에 붙는 표시. 정지버튼을 못 찾을 때의 2차 방어선.
  // (이게 안 잡히면 생성 도중에 전송을 눌러 답변이 통째로 날아간다.)
  스트리밍표시: [
    '.result-streaming',
    // 2026-09-30 형님 Chrome 에서 확인: 쓰는 동안 입력칸 단추 이름이 '중지'(testid 없음), 끝나면 '보내기'.
    // 예전엔 이걸 느슨한 표시로만 봐서, 60초 넘게 쓰면 결과가 끼어들 수 있었다.
    'form button[aria-label="중지"]',
    '[data-is-streaming="true"]',
    '[data-streaming="true"]',
  ],
};

// 입력창은 반드시 '글을 넣을 수 있는 요소'여야 한다.
// 이 검증 없이 execCommand('delete') 를 때리면 엉뚱한 DOM 을 지워버린다.
function 편집가능한가(el) {
  if (!el) return false;
  if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') return true;
  return el.isContentEditable === true;
}

// 후보를 순서대로 보되, 편집 가능한 것만 입력창으로 인정한다.
function 입력창찾기() {
  for (const s of 셀렉터.입력창) {
    for (const el of document.querySelectorAll(s)) {
      if (편집가능한가(el)) return el;
    }
  }
  return null;
}

// 후보 셀렉터를 순서대로 시도해 첫 번째로 찾은 요소를 돌려준다.
function 찾기(후보들, 범위 = document) {
  for (const s of 후보들) {
    const el = 범위.querySelector(s);
    if (el) return el;
  }
  return null;
}

// 후보 셀렉터를 순서대로 시도해 결과가 있는 첫 목록을 돌려준다.
function 모두찾기(후보들, 범위 = document) {
  for (const s of 후보들) {
    const els = 범위.querySelectorAll(s);
    if (els.length) return Array.from(els);
  }
  return [];
}
