// 사이드 패널 UI.
// 여기는 확장 페이지라 ChatGPT DOM 에 직접 손댈 수 없다.
// 서버 일은 background 를 거치고, ChatGPT 페이지 일은 content 에게 부탁한다.

const 화면 = {
  나무: null,
  지금방: null,
  지금방이름: null,
  지금폴더이름: null,
  대화: [],
  거울대화: null,
  기록: [],
  진행: null,
  계획: null,
  지금등급: '전부',
  지금모드: '자동',
  대기허락: [],
  대기받아오기: [],
  허가중: [],
  켜짐: true,
  처리중: false,
  생성중: false,
  메시지: '',
  서버글: '',
  서버살음: null,        // null=아직 모름 · true=살아 있음 · false=꺼짐
};

// 같은 허용 단추를 두 번 누르거나, 첫 처리 중 화면을 다시 그려도
// 설치 요청은 한 번만 서버에 보낸다.
const 설치처리중 = new Set();
let 방읽는중 = false;
let 다음방읽기 = undefined;

const $ = (id) => document.getElementById(id);

// 오른쪽에 어떤 칸을 보일지 기억한다. 칸을 복제하지 않고 기존 칸을 그대로 숨기거나 보여 주므로 내용이 서로 어긋나지 않는다.
// 위에서부터 실행 현황 → 일할 곳 → 추가한 것(실행 기록) → 파일 순이다. 처음에는 실행 기록만 꺼져 있다.
// 실행 현황은 일이 있을 때만 뜨는 칸이다(일이 없으면 켜 있어도 안 보인다).
// 보이는 칸은 오른쪽 높이를 몫대로 나눠 꽉 채운다. 칸을 다 끄면 오른쪽 전체가 사라져 대화가 넓어진다.
const 보기설정 = { 현황: true, 일할곳: true, 기록: false, 파일: true };
const 보기이름 = { 현황: '실행 현황', 일할곳: '일할 곳', 기록: '추가한 것 (실행 기록)', 파일: '파일' };
const 보기설정판 = '2';          // 판 2: 처음에는 실행 기록만 꺼 둔다. 옛 판에서 저장한 칸 선택은 한 번 새 기본으로 돌린다

const 칸순서 = [
  { 이름: '현황', 칸: '현황칸', 가름대: '현황가름대' },
  { 이름: '일할곳', 칸: '나무칸', 가름대: '기록나무가름대' },
  { 이름: '기록', 칸: '기록칸', 가름대: '세로가름대' },
  { 이름: '파일', 칸: '파일칸', 가름대: null },
];

// ── 칸 크기: 처음 모습과 저장 ──
// 처음: 오른쪽 폭은 판 너비의 35%, 보이는 칸은 높이를 똑같이 나눈다(몫 1:1:1…).
// 사용자가 가름대를 끌면 그 크기를 '지금 켜 둔 칸의 조합' 마다 따로 저장한다 — 셋을 켰을 때 크기와
// 둘을 켰을 때 크기가 서로 안 섞인다. 크기는 px 가 아니라 비율이라 판 창 크기를 바꿔도 같은 모양으로 늘고 준다.
const 기본옆너비 = 0.35;
let 옆너비비 = 기본옆너비;       // 오른쪽 칸 너비 ÷ 판 너비
const 칸무게 = {};                // 이름 → 그 칸의 몫(보이는 칸끼리의 비율)
let 지금조합 = '';

function 조합열쇠() {
  return 칸순서.filter((항) => 보기설정[항.이름]).map((항) => 항.이름).join('+');
}

function 배치저장() {
  try {
    localStorage.setItem('칸배치:' + 조합열쇠(), JSON.stringify({ 너비: 옆너비비, 몫: 칸무게 }));
    localStorage.setItem('칸배치:마지막너비', String(옆너비비));
  } catch (e) { /* 화면만 바꾼다 */ }
}

// 지금 조합의 저장값을 올린다. 저장한 적 없으면 몫은 똑같이, 너비는 마지막으로 쓴 것(없으면 35%).
function 배치불러오기() {
  for (const 이름 of Object.keys(칸무게)) delete 칸무게[이름];
  옆너비비 = 기본옆너비;
  try {
    const 마지막 = parseFloat(localStorage.getItem('칸배치:마지막너비'));
    if (마지막 > 0 && 마지막 < 1) 옆너비비 = 마지막;
    const 저장 = JSON.parse(localStorage.getItem('칸배치:' + 조합열쇠()) || 'null');
    if (저장 && typeof 저장 === 'object') {
      if (저장.너비 > 0 && 저장.너비 < 1) 옆너비비 = 저장.너비;
      for (const 이름 of Object.keys(보기설정)) {
        if (저장.몫 && 저장.몫[이름] > 0) 칸무게[이름] = 저장.몫[이름];
      }
    }
  } catch (e) { /* 기본값을 쓴다 */ }
}

function 칸보이나(항) {
  const 칸 = $(항.칸);
  return !!칸 && !!보기설정[항.이름] && !칸.hidden;
}

function 보이는칸수() {
  return 칸순서.filter((항) => 보기설정[항.이름]).length;
}

// 저장된 몫이 없는 칸(방금 나타난 실행 현황 등)은 이미 있는 칸들의 평균 몫을 받는다
function 칸몫(이름, 보임) {
  const 알려진 = 보임.map((항) => 칸무게[항.이름]).filter((값) => 값 > 0);
  const 평균 = 알려진.length ? 알려진.reduce((a, b) => a + b, 0) / 알려진.length : 1;
  return 칸무게[이름] > 0 ? 칸무게[이름] : 평균;
}

function 옆너비적용() {
  const 위칸 = $('위칸');
  if (!위칸 || 위칸.classList.contains('칸없음')) return;
  위칸.style.width = 일할곳너비맞추기(옆너비비 * window.innerWidth) + 'px';
}

function 보기배치() {
  const 열쇠 = 조합열쇠();
  if (열쇠 !== 지금조합) { 지금조합 = 열쇠; 배치불러오기(); }
  for (const 항 of 칸순서) {
    const 칸 = $(항.칸);
    if (칸) 칸.classList.toggle('숨김', !보기설정[항.이름]);
  }
  const 보임 = 칸순서.filter(칸보이나);
  // 가름대는 '그 칸이 보이고, 그 뒤에도 보이는 칸이 있을 때' 만 — 보이는 칸 사이마다 하나씩만 남는다
  칸순서.forEach((항, 번) => {
    const 가름대 = 항.가름대 && $(항.가름대);
    if (!가름대) return;
    const 뒤에있나 = 보임.some((것) => 칸순서.indexOf(것) > 번);
    가름대.classList.toggle('숨김', !(칸보이나(항) && 뒤에있나));
  });
  // 높이: 보이는 칸이 몫대로 나눠 꽉 찬다(flex-grow = 몫, 기준 0). 켠 칸이 둘이든 하나든 오른쪽이 빈틈없다.
  for (const 항 of 보임) {
    const 칸 = $(항.칸);
    칸.style.flex = 칸몫(항.이름, 보임) + ' 1 0';
    칸.style.maxHeight = 'none';
  }
  // 보이는 칸이 하나도 없으면 오른쪽 전체를 치워 대화가 넓어지게 한다
  const 위칸 = $('위칸');
  const 좌우가름대 = $('가름대');
  if (위칸) 위칸.classList.toggle('칸없음', !보임.length);
  if (좌우가름대) 좌우가름대.classList.toggle('칸없음', !보임.length);
  옆너비적용();
  const 도구 = $('파일도구');
  if (도구) 도구.style.display = 보기설정.파일 ? 'flex' : 'none';
  const 토글 = $('위칸토글');
  if (토글) 토글.title = 보기설정.일할곳 ? '일할 곳 접기 · 펴기' : '오른쪽 칸 접기 · 펴기';
}

// 가름대를 끌 때: 위 칸과 그 아래 칸의 높이 합은 그대로 두고 둘의 몫만 바꾼다. 어느 쪽도 40px 밑으로는 안 간다.
function 가름대높이나누기(높이들, 번, 새윗높이) {
  const 합 = 높이들[번] + 높이들[번 + 1];
  const 윗 = Math.max(40, Math.min(새윗높이, 합 - 40));
  const 새 = 높이들.slice();
  새[번] = 윗;
  새[번 + 1] = 합 - 윗;
  return 새;
}

// 몫을 바꾸고 바로 화면에 맞춘다(저장은 끌기가 끝났을 때 배치저장)
function 칸몫정하기(몫들) {
  for (const 이름 of Object.keys(몫들)) 칸무게[이름] = 몫들[이름];
  보기배치();
}

function 보기설정불러오기() {
  try {
    if (localStorage.getItem('보기설정판') !== 보기설정판) {
      for (const 이름 of Object.keys(보기설정)) localStorage.setItem('보기칸:' + 이름, 보기설정[이름] ? '1' : '0');
      localStorage.setItem('보기설정판', 보기설정판);
    }
  } catch (e) { /* 기본값을 쓴다 */ }
  for (const 이름 of Object.keys(보기설정)) {
    try {
      const 값 = localStorage.getItem('보기칸:' + 이름);
      if (값 !== null) 보기설정[이름] = 값 === '1';
    } catch (e) { /* 기본값을 쓴다 */ }
  }
  보기배치();
}

function 보기전환(이름) {
  보기설정[이름] = !보기설정[이름];
  try { localStorage.setItem('보기칸:' + 이름, 보기설정[이름] ? '1' : '0'); }
  catch (e) { /* 화면만 바꾼다 */ }
  보기배치();
  본문그리기();
  if (이름 === '파일' && 보기설정.파일) 파일나무그리기();
}

// ── 통로 ───────────────────────────────────────────────────────

async function 서버에게(몸통) {
  try {
    return await chrome.runtime.sendMessage(몸통);
  } catch (e) {
    알림('⚠ 서버에 연결하지 못했습니다: ' + e.message);
    return null;
  }
}

// 이 패널이 들어 있는 브라우저 창의 번호. 모르면 null.
async function 내창번호() {
  try {
    const 창 = await chrome.windows.getCurrent();
    return 창 && 창.id !== undefined && 창.id !== null ? 창.id : null;
  } catch (e) { return null; }
}

// 이 패널이 상대할 탭은 '이 창에서 지금 보고 있는 ChatGPT 탭' 하나뿐이다.
// 예전에는 열려 있는 아무 ChatGPT 탭이나 잡아서, 딴 창에 말을 걸기도 했다.
async function 챗탭찾기() {
  const 조건 = {
    active: true,
    url: ['https://chatgpt.com/*', 'https://chat.openai.com/*'],
  };
  // 이 패널이 든 창의 탭을 먼저 본다. '마지막으로 포커스한 창' 만 보면 창이 둘일 때
  // 두 패널이 다 그 창의 탭을 따라가서 하나로 합쳐진다(2026-10-04 사용자 화면).
  const 창 = await 내창번호();
  if (창 !== null) {
    const 내것 = await chrome.tabs.query({ ...조건, windowId: 창 });
    if (내것.length) return 내것[0].id;
  }
  // 사이드 패널에서는 currentWindow가 패널 창으로 해석되는 브라우저가 있다.
  // 그 경우 방을 눌러도 ChatGPT 탭을 못 찾아 아무 일도 안 한다.
  let 탭들 = await chrome.tabs.query({ ...조건, lastFocusedWindow: true });
  if (!탭들.length) 탭들 = await chrome.tabs.query(조건);
  return 탭들.length ? 탭들[0].id : null;
}

// (예전에는 탭 하나만 '붙여서' 일하게 했다. 이제 대화마다 제 방이라 필요 없다.)
// 남겨 둔 까닭: 창이 여러 개일 때 어느 탭을 상대할지는 여전히 골라야 한다.


async function 탭에게(짓, 값) {
  const 탭 = await 챗탭찾기();
  if (탭 === null) {
    알림('⚠ ChatGPT 화면이 없습니다. chatgpt.com 을 먼저 열어 주세요.');
    return null;
  }
  try {
    return await chrome.tabs.sendMessage(탭, { 종류: '창→탭', 짓, 값 });
  } catch (e) {
    알림('⚠ ChatGPT 화면과 연결되지 않았습니다. 그 화면을 새로고침해 보세요.');
    return null;
  }
}

// 판은 이 창에서 지금 보고 있는 ChatGPT 탭의 소식만 듣는다.
// 예전엔 모든 ChatGPT 탭의 상태를 다 받아, 탭이 둘이면 두 상태가 0.35초마다
// 번갈아 그려져 상태줄이 깜박였다('대기 중' ↔ '멈춤 · 다시 시작했습니다').
let 보는탭 = null;

async function 보는탭갱신() {
  try { 보는탭 = await 챗탭찾기(); } catch (e) { /* 넘어간다 */ }
}

function 딴탭소식인가(보낸이) {
  const 탭 = 보낸이 && 보낸이.tab && 보낸이.tab.id;
  return 탭 !== undefined && 탭 !== null && 보는탭 !== null && 탭 !== 보는탭;
}

보는탭갱신();
setInterval(보는탭갱신, 1500);
try {
  if (chrome.tabs.onActivated) chrome.tabs.onActivated.addListener(보는탭갱신);
} catch (e) { /* 넘어간다 */ }

chrome.runtime.onMessage.addListener((메시지, 보낸이) => {
  if (!메시지 || 메시지.종류 !== '탭→창') return false;
  if ((메시지.짓 === '상태' || 메시지.짓 === '기록' || 메시지.짓 === '대화갱신' || 메시지.짓 === '대화거울')
      && 딴탭소식인가(보낸이)) return false;
  if (메시지.짓 === '상태') {
    탭상태받기(메시지.값);
    상태그리기();
    입력상태();
    줄선것내보내기();      // 일이 끝났으면 줄 세운 말을 내보낸다
  } else if (메시지.짓 === '기록') {
    화면.기록 = 메시지.값 || [];
    본문그리기();
  } else if (메시지.짓 === '대화거울') {
    // 받아만 둔다. 그리는 곳이 없는데 GPT가 쓰는 동안 1초마다 본문을 다시 그렸다.
    화면.거울대화 = Array.isArray(메시지.값) ? 메시지.값 : [];
  } else if (메시지.짓 === '대화갱신') {
    방새로고침(화면.지금방);
  } else if (메시지.짓 === '계획갱신') {
    계획새로고침();
  } else if (메시지.짓 === '허락갱신') {
    방새로고침();
    받아오기새로고침();
  }
  return false;
});

// ChatGPT 탭이 보내 온 상태를 받는다.
// 탭은 '이 대화의 방' 을 아직 모를 수 있다(새 대화 화면, 서버가 막 켜지는 중).
// 그때 온 빈 방으로 판을 덮으면 멀쩡한 일할 곳이 '없습니다' 로 바뀐다(실제로 그랬다).
// 그래서 빈 방은 무시하고, 탭이 다른 방을 알려 오면 서버에서 나무를 새로 받는다.
function 탭상태받기(값) {
  if (!값) return;
  const 받은것 = Object.assign({}, 값);
  const 탭방 = 받은것.지금방;
  delete 받은것.지금방;
  Object.assign(화면, 받은것);
  // 탭이 대화는 보고 있는데 그 대화에 방이 없다 — 서버에 남은 엉뚱한 방을 대신 보이지 않는다
  const 방없는대화 = !!(받은것.대화번호 && !탭방);
  if (방없는대화 !== !!화면.방없는대화) {
    화면.방없는대화 = 방없는대화;
    상태그리기();
    본문그리기();
  }
  진행그리기();
  if (탭방 && 탭방 !== 화면.지금방) {
    화면.지금방 = 탭방;
    방새로고침(탭방);
    계획새로고침();              // 할 일도 이 창의 방 것으로
  }
}

// ── 상태 ───────────────────────────────────────────────────────

function 알림(글) {
  화면.메시지 = 글;
  상태그리기();
}

function 상태그리기() {
  진행그리기();
  상태줄그리기();
  // 글자를 함께 둔다 — 기호만으로는 무슨 단추인지 몰랐다
  $('멈춤단추').textContent = 화면.켜짐 ? '⏸ 멈춤' : '▶ 이어서 하기';
  $('멈춤단추').classList.toggle('멈춤', !화면.켜짐);
  $('멈춤단추').title = 화면.켜짐
    ? '자동 진행을 멈춥니다. 하던 도구는 끝까지 합니다.'
    : '멈춘 자동 진행을 다시 시작합니다.';

  // 방은 골랐는데 이름만 아직 없는 경우가 있다.
  // 그때 '고르세요' 라고 하면 이미 골랐는데도 안 고른 줄 안다.
  $('방이름').textContent = 화면.방없는대화 ? '이 대화에는 아직 일할 방이 없습니다'
    : (화면.지금방이름 || (화면.지금방 ? '(이름 짓는 중…)' : '일할 곳을 고르세요'));
  const 폴더 = $('폴더이름');
  if (화면.지금폴더이름) {
    폴더.textContent = 화면.지금폴더이름;
    폴더.hidden = false;
  } else {
    폴더.hidden = true;
  }

  const 모드 = 지금모드();
  $('모드글').textContent = 모드;
  추론글그리기();
  $('모드알약').classList.toggle('수동', 모드 === '수동');
  $('모드알약').classList.toggle('전체권한', 모드 === '전체권한');
  $('모드알약').title = 모드설명[모드];

  심장그리기();
  해낸것그리기();
  보냄단추맞추기();

  $('끝글').textContent = (화면.처리중 || 화면.생성중) ? '일하는 중'
    : (화면.켜짐 ? '' : '멈춰 있음');
  수치줄맞추기();
}

// 셋 다 비면 줄 자체를 접는다
function 수치줄맞추기() {
  const 줄 = $('수치줄');
  if (!줄) return;
  const 심장글 = $('심장').textContent.trim();
  줄.hidden = !($('끝글').textContent || $('해낸것').textContent || (심장글 && 심장글 !== '·'));
}

// 지금 무엇을 하는지는 상태줄에 한 줄로만 보인다.
// GPT가 쓰는 글을 실시간으로 보이던 '진행 카드' 는 없앴다(대화는 ChatGPT 창에서 한다).
// 도구를 돌리는 중일 때만 '무엇을' 을 덧붙인다. 예: 도구 실행 중 · 내용 보기 sim/ppo.py
function 진행한줄() {
  const 진행 = 화면.진행;
  if (!진행 || 진행.단계 !== '도구 실행 중') return '';
  if (진행.방번호 && 화면.지금방 && 진행.방번호 !== 화면.지금방) return '';
  if (진행.대화번호 && 화면.대화번호 && 진행.대화번호 !== 화면.대화번호) return '';
  if (!화면.처리중) return '';                       // 끝난 실행의 늦은 상태
  const 무엇 = String(진행.글 || '').split(String.fromCharCode(10))[0].trim();
  if (!무엇) return '';
  // 상태줄 앞머리가 이미 '내용 보기 처리 중…' 이면 도구 이름은 빼고 대상만 덧붙인다
  const 조각 = 무엇.split(' · ');
  const 대상 = 조각.slice(1).join(' · ');
  const 보일 = (대상 && 화면.메시지 && 화면.메시지.indexOf(조각[0]) !== -1) ? 대상 : 무엇;
  return 보일.length > 60 ? 보일.slice(0, 60) + '…' : 보일;
}

// 진행 소식이 바뀌면 상태줄만 다시 그린다
function 진행그리기() {
  상태줄그리기();
}

// ── 서버가 살아 있나 ──────────────────────────────────────────
// 서버는 사람이 창을 닫으면 그냥 죽는다. 그때 판이 아무 말도 안 하면
// '단추를 눌러도 아무 일이 없다' 로만 보인다. 그래서 늘 확인하고 알린다.

// 서버는 판을 열면 스스로 켜진다(자동 켜기). 그래도 못 켰을 때만 이 말이 나온다.
const 서버켜는법 = '서버를 자동으로 켜지 못했습니다. 잠시 뒤 다시 시도합니다.';

function 서버꺼짐알리기(탈) {
  화면.서버살음 = false;
  화면.서버글 = '⚠ 서버 꺼짐';
  화면.서버꺼짐까닭 = 탈 || '';
  알림('⚠ ' + (탈 || ('서버가 꺼져 있습니다. ' + 서버켜는법)));
}

async function 서버살았나() {
  const 핑 = await 서버에게({ 종류: '서버확인' });
  const 살음 = !!(핑 && (핑.success || 핑.됨));
  const 바뀜 = 화면.서버살음 !== 살음;
  화면.서버살음 = 살음;

  if (!살음) {
    서버꺼짐알리기(핑 && 핑.탈);
    return false;
  }
  화면.서버글 = '서버 v' + (핑.version || '?')
              + ' · 도구 ' + ((핑.도구목록 || []).length) + '개';
  if (핑.등급) 화면.지금등급 = 핑.등급;
  if (핑.모드) 화면.지금모드 = 핑.모드;
  if (바뀜) { 알림('서버가 다시 연결되었습니다'); 방새로고침(); }
  상태그리기();
  return true;
}

// 상태줄 — 일하는 중이면 도는 표시를 앞에 붙인다.
function 상태줄그리기() {
  const 칸 = $('상태줄');
  칸.textContent = '';

  // 서버가 죽었으면 다른 무엇보다 이것부터 보여야 한다.
  if (화면.서버살음 === false) {
    const 경고 = document.createElement('span');
    경고.className = '서버꺼짐';
    경고.textContent = '⚠ ' + (화면.서버꺼짐까닭 || ('서버 꺼짐 — ' + 서버켜는법));
    경고.title = 경고.textContent;
    칸.appendChild(경고);
    return;
  }

  const 도나 = 화면.처리중 || 화면.생성중;
  if (도나) {
    const 돎 = document.createElement('span');
    돎.className = '돎';
    돎.textContent = '✳';
    칸.appendChild(돎);
  } else if (!화면.켜짐) {
    칸.appendChild(document.createTextNode('○ 멈춤 · '));
  } else {
    칸.appendChild(document.createTextNode('● '));
  }
  칸.appendChild(document.createTextNode(화면.메시지 || '대기 중'));
  const 한줄 = 진행한줄();
  if (한줄) 칸.appendChild(document.createTextNode(' · ' + 한줄));

  // 대답이 끝내 없으면 짧게 재촉하는 단추
  if (화면.대답없음 && !화면.결과대기) {
    const 단추 = document.createElement('button');
    단추.className = '알약 다시보내기';
    단추.textContent = '대답 다시 받기';
    단추.title = '앞 결과를 보고 이어서 하도록 ChatGPT에 짧게 알립니다.';
    단추.onclick = 대답다시받기누름;
    칸.appendChild(단추);
  }

  // 보내야 할 결과를 들고 있으면 사람이 바로 밀어 보낼 수 있게 단추를 붙인다.
  if (화면.결과대기) {
    const 단추 = document.createElement('button');
    단추.className = '알약 다시보내기';
    단추.textContent = '다시 보내기';
    단추.title = '결과를 입력칸에 다시 넣어 보냅니다. 도구는 다시 실행하지 않습니다.';
    단추.onclick = 결과다시보내기;
    칸.appendChild(단추);
  }
}

// 대화가 꽉 찼을 때. 같은 프로젝트에 새 대화를 열고 넘김 파일을 보낸다. 판에서는 같은 방이다.
async function 새대화로넘기기누름() {
  알림('새 대화로 넘길 파일을 만드는 중…');
  const 답 = await 탭에게('넘기기');
  if (답) 알림(답.됨 ? '새 대화를 열어 지금까지의 내용을 넘기고, 같은 방에서 이어 갑니다.' : ('⚠ ' + (답.탈 || '넘기지 못했습니다')));
}

async function 대답다시받기누름() {
  알림('이어서 해 달라고 보내는 중…');
  const 답 = await 탭에게('대답다시받기');
  if (답) 알림(답.됨 ? '이어서 하라고 보냈습니다. 답을 기다립니다' : ('⚠ ' + (답.탈 || '보내지 못했습니다')));
}

async function 마지막결과다시보내기누름() {
  알림('마지막 결과를 다시 보내는 중…');
  const 답 = await 탭에게('마지막결과다시보내기');
  if (답) 알림(답.됨 ? '마지막 결과를 다시 보냈습니다. 답을 기다립니다' : ('⚠ ' + (답.탈 || '보내지 못했습니다')));
}

let 결과재전송중 = false;
async function 결과다시보내기() {
  if (결과재전송중) return;
  결과재전송중 = true;
  알림('결과를 다시 보내는 중…');
  try {
    const 답 = await 탭에게('다시보내기');
    if (답) 알림(답.됨 ? '다시 보냈습니다. 답을 기다립니다' : ('⚠ ' + (답.탈 || '보내지 못했습니다')));
  } finally {
    결과재전송중 = false;
  }
}

// 이번 일을 얼마나 했는지. 횟수 상한을 없앤 자리를 이것이 대신한다.
// 사람이 이 숫자를 보고 '너무 오래 헤매는데' 싶으면 ⏸ 를 누른다.
function 해낸것그리기() {
  const 칸 = $('해낸것');
  const 도구수 = 화면.이번나물수 || 0;      // 탭이 '이번나물수' 로 보낸다(안쪽 이름은 그대로)
  const 시작 = 화면.시작한때 || 0;
  if (!도구수 && !시작) {
    칸.textContent = '';
    칸.className = '';
    수치줄맞추기();
    return;
  }
  const 초 = 시작 ? Math.floor((Date.now() - 시작) / 1000) : 0;
  const 때 = 초 < 60 ? 초 + '초' : Math.floor(초 / 60) + '분 ' + (초 % 60) + '초';
  칸.textContent = '경과 ' + 때 + ' · 도구 ' + 도구수 + '번 실행';
  칸.className = (화면.처리중 || 화면.생성중) ? '도는중' : '';
  칸.title = [
    '이번 일을 시작한 지 ' + 때 + ', 도구를 ' + 도구수 + '번 실행했습니다.',
    '횟수 제한은 없습니다. 너무 오래 걸린다 싶으면 [⏸ 멈춤] 으로 멈추세요.',
    (화면.헛돎횟수 ? '같은 실패가 ' + 화면.헛돎횟수 + '번 이어졌습니다.' : ''),
  ].filter(Boolean).join(String.fromCharCode(10));
  수치줄맞추기();
}

// 창을 다른 창으로 덮으면 크롬이 시계를 늦춘다.
// 그때도 일꾼이 계속 도는지 여기서 바로 보인다.
//   '가장 오래 멈춤' 이 1초 안쪽이면 잘 도는 것이고,
//   덮었다 켰을 때 갑자기 몇십 초로 뛰면 멈췄던 것이다.
function 심장그리기() {
  const 칸 = $('심장');
  const 최대틈 = 화면.최대틈ms || 0;
  if (!화면.돈횟수) {
    칸.textContent = '';
    칸.className = '';
    칸.title = '아직 동작이 확인되지 않았습니다. ChatGPT 화면을 새로고침해 보세요.';
    수치줄맞추기();
    return;
  }

  const 초 = (최대틈 / 1000).toFixed(1);
  // 답 쓰는 속도(✎). 느려서 다음에 새 대화로 넘길 참이면 붉게.
  const 쉬운수 = (값) => (Number.isFinite(Number(값)) ? String(Math.round(Number(값))) : String(값));
  const 속도글 = 화면.속도 ? ' · GPT 쓰기 속도 ' + 쉬운수(화면.속도) + '자/초'
    + (화면.평소속도 ? ' (평소 ' + 쉬운수(화면.평소속도) + ')' : '') : '';
  칸.textContent = '화면 최대 멈춤 ' + 초 + '초' + 속도글;
  칸.className = 화면.느려서넘김 ? '나쁨' : (최대틈 <= 1500 ? '좋음' : (최대틈 <= 5000 ? '' : '나쁨'));
  칸.title = [
    'ChatGPT 화면에서 가장 오래 멈췄던 시간: ' + 초 + '초',
    '돈 횟수 ' + 화면.돈횟수 + ' · 박동 ' + (화면.박동수 || 0),
    '다른 창으로 덮었다가 다시 열어도 1초 안쪽이면 정상입니다.',
    '(⋮ → 다시 시작 을 누르면 다시 잽니다)',
  ].join(String.fromCharCode(10));
  수치줄맞추기();
}

// 창에 보이는 권한 모드는 셋이다. 서버가 저장하고, 도구마다 바로 할지 · 물을지 · 막을지는 서버의 승인 문이 정한다.
const 모드목록 = ['전체권한', '자동', '수동'];
const 모드설명 = {
  전체권한: 'GPT가 묻지 않고 모두 처리합니다. 위험한 명령·화면·입력은 그래도 막거나 묻습니다.',
  자동: '결정을 GPT가 처리합니다. 위험한 일만 사용자에게 묻습니다.',
  수동: '고치거나 실행하기 전에 늘 사용자에게 묻습니다.',
};

function 지금모드() {
  return 모드목록.includes(화면.지금모드) ? 화면.지금모드 : '자동';
}

// 예전에는 일하는 중이면 무조건 'GPT가 일하는 중…' 으로 덮었다. 그러면 탭이 보낸
// 자세한 말('결과를 들고 기다리는 중 — 무엇 때문에')이 가려져 왜 멈췄는지 알 수 없었다.
// 탭이 아무 말도 안 보냈을 때만 채운다.
function 입력상태() {
  if ((화면.처리중 || 화면.생성중) && !화면.메시지) 알림('GPT가 일하는 중…');
}

// ── 서버에서 받아오기 ──────────────────────────────────────────

async function 방새로고침(유지할방 = null) {
  const 목표 = 유지할방 || 화면.지금방 || null;
  if (방읽는중) {
    다음방읽기 = 목표;
    return;
  }
  방읽는중 = true;
  try {
    const 답 = await 서버에게({ 종류: '방나무', 방: 목표 || '' });
    if (!답 || !답.됨) return;
    const 현재방 = 목표 || 답.지금방 || null;
    const 방바뀜 = 현재방 !== 화면.지금방;
    화면.나무 = 답;
    화면.지금방 = 현재방;
    if (방바뀜) 계획새로고침();        // 할 일은 방마다 다르다
    if (방바뀜) 현황방바뀜();          // 현황도 방마다 다르다
    진행그리기();
    화면.지금방이름 = 목표
      ? ((답.폴더들 || []).flatMap((f) => f.방들 || [])
          .find((r) => r.쪽번호 === 목표) || {}).이름 || null
      : (답.지금방이름 || null);
    화면.대화 = 답.대화 || [];
    화면.대기허락 = 답.대기 || [];

    화면.지금폴더이름 = null;
    for (const 폴더 of (답.폴더들 || [])) {
      if ((폴더.방들 || []).some((r) => r.쪽번호 === 현재방)) {
        화면.지금폴더이름 = 폴더.이름;
      }
    }

    상태그리기();
    입력상태();
    물음그리기();
    나무그리기();
    파일나무그리기();
    본문그리기();
    await 예약새로고침();
  } finally {
    방읽는중 = false;
    const 다음 = 다음방읽기;
    다음방읽기 = undefined;
    if (다음 !== undefined) void 방새로고침(다음);
  }
}

// ── 예약 (배추) ───────────────────────────────────────────────
async function 예약새로고침() {
  if (!화면.지금방) { 화면.예약들 = []; return; }
  const 답 = await 서버에게({ 종류: '예약', 몸통: { 짓: '목록', 방: 화면.지금방 } });
  const 새것 = 답 && 답.됨 ? (답.예약들 || []) : [];
  const 바뀜 = JSON.stringify(새것) !== JSON.stringify(화면.예약들 || []);
  화면.예약들 = 새것;
  if (바뀜) 본문그리기();
}

function 예약그리기() {
  const 목록 = 화면.예약들 || [];
  if (!화면.지금방 || !목록.length) return;
  const 칸 = document.createElement('div');
  칸.className = '할일칸 예약칸';
  const 머리 = document.createElement('div');
  머리.className = '할일머리';
  const 이름 = document.createElement('span');
  이름.textContent = '⏰ 예약';
  const 몇 = document.createElement('span');
  몇.className = '몇';
  몇.textContent = 목록.length + '개';
  머리.append(이름, 몇);
  칸.appendChild(머리);

  for (const 예약 of 목록) {
    const 줄 = document.createElement('div');
    줄.className = '예약줄';
    const 글 = document.createElement('span');
    글.className = '글';
    글.textContent = (예약.조건 ? '조건 ' + 예약.조건 : 예약.간격 + '마다')
      + ' · ' + 예약.보낸수 + '/' + 예약.횟수 + ' · 다음 ' + (예약.다음 || '') + ' — ' + 예약.말;
    글.title = 예약.말;
    const 그만 = document.createElement('button');
    그만.className = '알약';
    그만.textContent = '그만';
    그만.title = '이 예약을 멈춥니다';
    그만.onclick = () => 예약그만(예약.번호);
    줄.append(글, 그만);
    칸.appendChild(줄);
  }
  $('본문').appendChild(칸);
}

async function 예약그만(번호) {
  const 답 = await 서버에게({ 종류: '예약', 몸통: { 짓: '그만', 방: 화면.지금방, 번호 } });
  알림(답 && 답.됨 ? '⏰ 예약을 멈췄습니다' : ('⚠ ' + ((답 && 답.탈) || '멈추지 못했습니다')));
  await 예약새로고침();
}

setInterval(() => { 예약새로고침(); }, 15000);

async function 계획새로고침() {
  const 답 = await 서버에게({ 종류: '계획보기', 방: 화면.지금방 || '' });
  if (!답 || !답.됨) return;
  화면.계획 = 답;
  if ($('목표창').style.display === 'flex' && !목표폼.열림.size) 목표그리기();
  목표알림그리기();
}

let 마지막물음열쇠글 = '';

async function 받아오기새로고침() {
  const 답 = await 서버에게({ 종류: '받아오기목록' });
  if (!답 || !답.됨) return;
  화면.대기받아오기 = 답.기다림 || [];
  화면.허가중 = 답.허가중 || [];
  // 카드는 바뀐 때만 다시 그린다(3초마다 지우고 그리면 누르는 순간 단추가 사라진다)
  const 열쇠글 = (화면.대기받아오기 || []).map((요청) => 요청.열쇠).join('|');
  if (열쇠글 !== 마지막물음열쇠글) { 마지막물음열쇠글 = 열쇠글; 물음그리기(); }
  허가중그리기();
}

// 눈·손 허가가 살아 있는 동안 늘 보이는 줄 — [그만] 으로 바로 거둘 수 있다.
function 허가중그리기() {
  const 칸 = $('허가중칸');
  if (!칸) return;
  칸.textContent = '';
  for (const 허가 of (화면.허가중 || [])) {
    const 줄 = document.createElement('div');
    줄.className = '허가중 ' + 허가.종류;
    const 뜻 = document.createElement('span');
    뜻.className = '뜻';
    뜻.textContent = (허가.종류 === '눈' ? '👁 화면 보기 허가 · ' : '🖱 키보드·마우스 허가 · ')
      + (허가.창 === '*' ? '화면 전체' : '창 ' + 허가.창) + ' · 남은 ' + 초글(허가.남은초) + ' · ' + 허가.쓴수 + '번 사용';
    뜻.title = 허가.왜 || '';
    const 그만 = document.createElement('button');
    그만.className = '작은';
    그만.textContent = '그만';
    그만.onclick = () => 허가그만(허가.번호);
    줄.append(뜻, 그만);
    칸.appendChild(줄);
  }
}

async function 허가그만(번호) {
  const 답 = await 서버에게({ 종류: '받아오기처리', 그만: 번호 === undefined || 번호 === null ? '' : String(번호) });
  if (답 && 답.됨) {
    화면.허가중 = 답.허가중 || [];
    화면.대기받아오기 = 답.기다림 || 화면.대기받아오기;
    허가중그리기();
    알림('허가를 거두었습니다.');
  } else {
    알림('⚠ 허가를 거두지 못했습니다. 서버가 켜져 있는지 보세요.');
  }
}

// ── 본문 (Chat / Log) ──────────────────────────────────────────

function 빈안내(글, 대상 = $('본문')) {
  const d = document.createElement('div');
  d.className = '빈안내';
  d.textContent = 글;
  대상.appendChild(d);
}

// 옛 기록(확장 3.78.0 까지)에는 ChatGPT 코드블록 머리의 이름표가 GPT 말로 남아 있다.
// 바구니만 있던 답이 '일반 텍스트' 한 줄로 적혔다. 기록은 두고 판에서만 그 줄을 가린다.
const 코드이름표줄 = /^[ \t]*일반 텍스트[ \t]*$/gm;

function 프로즈만(글) {
  const 블록들 = 요청블록추출(글);
  let 남은것 = 글;
  for (const b of 블록들) 남은것 = 남은것.split(b.원문).join('');
  return 남은것.replace(/```[a-zA-Z]*\s*```/g, '').replace(코드이름표줄, '').trim();
}

function 요청한줄값(요청) {
  for (const 키 of 요약키) {
    if (요청[키] && typeof 요청[키] === 'string') {
      return 요청[키].split('\n')[0].slice(0, 70);
    }
  }
  return '';
}


// ── 아주 작은 마크다운 그리개 ──────────────────────────────────
// 표·제목·굵게·코드·목록만 다룬다. 글자를 넣을 때 textContent 만 쓰므로
// 답변에 무엇이 들어 있든 그대로 글자로만 나온다(HTML 로 해석되지 않는다).

function 속줄넣기(칸, 글) {
  // **굵게** , `코드` , *기울임* 만 처리한다.
  const 조각정규식 = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)/g;
  let 자리 = 0;
  let m;
  while ((m = 조각정규식.exec(글)) !== null) {
    if (m.index > 자리) 칸.appendChild(document.createTextNode(글.slice(자리, m.index)));
    const 조각 = m[0];
    if (조각.startsWith('**')) {
      const b = document.createElement('strong');
      b.textContent = 조각.slice(2, -2);
      칸.appendChild(b);
    } else if (조각.startsWith('`')) {
      const c = document.createElement('code');
      c.className = '속코드';
      c.textContent = 조각.slice(1, -1);
      칸.appendChild(c);
    } else {
      const i = document.createElement('em');
      i.textContent = 조각.slice(1, -1);
      칸.appendChild(i);
    }
    자리 = m.index + 조각.length;
  }
  if (자리 < 글.length) 칸.appendChild(document.createTextNode(글.slice(자리)));
}

// 좁은 판에서 표가 넘칠 때 가로로만 밀리게 감싼다. (판 전체가 밀리면 안 된다)
function 표감기(표) {
  const 감개 = document.createElement('div');
  감개.className = '표감개';
  감개.appendChild(표);
  return 감개;
}

function 표만들기(줄들) {
  const 칸나누기 = (줄) => 줄.trim().replace(/^\||\|$/g, '').split('|').map((x) => x.trim());
  const 표 = document.createElement('table');
  표.className = '표';
  const 머리 = document.createElement('tr');
  for (const 칸 of 칸나누기(줄들[0])) {
    const th = document.createElement('th');
    속줄넣기(th, 칸);
    머리.appendChild(th);
  }
  표.appendChild(머리);
  for (const 줄 of 줄들.slice(2)) {
    const tr = document.createElement('tr');
    for (const 칸 of 칸나누기(줄)) {
      const td = document.createElement('td');
      속줄넣기(td, 칸);
      tr.appendChild(td);
    }
    표.appendChild(tr);
  }
  return 표;
}

// 탭으로 칸을 나눈 표.
// ChatGPT 화면의 표를 긁어오면 세로줄(|) 없이 탭만 남는다.
// 그대로 두면 글자가 줄줄이 붙어 읽을 수가 없다.
function 탭칸(줄) {
  return 줄.split('\t').map((x) => x.trim());
}

function 탭표인가(줄들, i) {
  if (!줄들[i] || 줄들[i].indexOf('\t') === -1) return 0;
  const 칸수 = 탭칸(줄들[i]).length;
  if (칸수 < 2) return 0;
  let 끝 = i;
  while (끝 + 1 < 줄들.length && 줄들[끝 + 1].indexOf('\t') !== -1) 끝 += 1;
  return 끝 - i + 1 >= 2 ? 끝 - i + 1 : 0;   // 최소 두 줄이어야 표로 본다
}

function 탭표만들기(줄들) {
  const 표 = document.createElement('table');
  표.className = '표';
  줄들.forEach((줄, 번) => {
    const tr = document.createElement('tr');
    for (const 칸 of 탭칸(줄)) {
      const 셀 = document.createElement(번 === 0 ? 'th' : 'td');
      속줄넣기(셀, 칸);
      tr.appendChild(셀);
    }
    표.appendChild(tr);
  });
  return 표;
}

function 마크다운그리기(글, 담을곳) {
  const 줄들 = String(글 || '').split('\n');
  let i = 0;
  let 문단 = [];

  const 문단내기 = () => {
    if (!문단.length) return;
    const p = document.createElement('div');
    p.className = '문단';
    속줄넣기(p, 문단.join('\n'));
    담을곳.appendChild(p);
    문단 = [];
  };

  while (i < 줄들.length) {
    const 줄 = 줄들[i];

    // 코드블록
    if (/^\s*```/.test(줄)) {
      문단내기();
      const 모음 = [];
      i += 1;
      while (i < 줄들.length && !/^\s*```/.test(줄들[i])) { 모음.push(줄들[i]); i += 1; }
      i += 1;
      const pre = document.createElement('pre');
      pre.className = '코드덩이';
      pre.textContent = 모음.join('\n');
      담을곳.appendChild(pre);
      continue;
    }

    // 표 (다음 줄이 |---| 모양이어야 한다)
    if (/^\s*\|.*\|\s*$/.test(줄) && i + 1 < 줄들.length &&
        /^\s*\|[\s:|-]+\|\s*$/.test(줄들[i + 1])) {
      문단내기();
      const 모음 = [];
      while (i < 줄들.length && /^\s*\|.*\|\s*$/.test(줄들[i])) { 모음.push(줄들[i]); i += 1; }
      담을곳.appendChild(표감기(표만들기(모음)));
      continue;
    }

    // 탭으로 나뉜 표
    const 탭줄수 = 탭표인가(줄들, i);
    if (탭줄수) {
      문단내기();
      담을곳.appendChild(표감기(탭표만들기(줄들.slice(i, i + 탭줄수))));
      i += 탭줄수;
      continue;
    }

    // 제목
    const 제목 = 줄.match(/^(#{1,4})\s+(.*)$/);
    if (제목) {
      문단내기();
      const h = document.createElement('div');
      h.className = '제목 제목' + 제목[1].length;
      속줄넣기(h, 제목[2]);
      담을곳.appendChild(h);
      i += 1;
      continue;
    }

    // 인용문 — 왼쪽에 세로 막대를 세운다
    if (/^\s*>\s?/.test(줄)) {
      문단내기();
      const 모음 = [];
      while (i < 줄들.length && /^\s*>\s?/.test(줄들[i])) {
        모음.push(줄들[i].replace(/^\s*>\s?/, ''));
        i += 1;
      }
      const 인용 = document.createElement('div');
      인용.className = '인용';
      속줄넣기(인용, 모음.join('\n'));
      담을곳.appendChild(인용);
      continue;
    }

    // 가로줄
    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(줄)) {
      문단내기();
      const hr = document.createElement('div');
      hr.className = '가로줄';
      담을곳.appendChild(hr);
      i += 1;
      continue;
    }

    // 목록
    if (/^\s*([-*+]|\d+\.)\s+/.test(줄)) {
      문단내기();
      while (i < 줄들.length && /^\s*([-*+]|\d+\.)\s+/.test(줄들[i])) {
        const 항 = document.createElement('div');
        항.className = '목록항';
        const 글자 = 줄들[i].replace(/^\s*([-*+]|\d+\.)\s+/, '');
        const 점 = document.createElement('span');
        점.className = '점';
        점.textContent = /^\s*\d+\./.test(줄들[i])
          ? 줄들[i].trim().split('.')[0] + '.'
          : '•';
        항.appendChild(점);
        const 몸 = document.createElement('span');
        속줄넣기(몸, 글자);
        항.appendChild(몸);
        담을곳.appendChild(항);
        i += 1;
      }
      continue;
    }

    // 빈 줄이면 문단을 끊는다
    if (!줄.trim()) { 문단내기(); i += 1; continue; }

    문단.push(줄);
    i += 1;
  }
  문단내기();
}

// 패널은 대화창이 아니다. 승인과 일할 곳 고르기, 그리고 무슨 일이
// 벌어지고 있는지 보는 곳이다. 대화는 ChatGPT 창에서 한다.
function 본문그리기() {
  const 본문 = $('본문');
  const 흐름 = $('흐름');        // 굴리는 칸 — 대화와 진행 카드를 같이 담는다
  const 옛자리 = 흐름.scrollTop;
  const 바닥이었나 = 바닥인가(흐름);
  본문.textContent = '';
  // 할 일이 끝났으면 기록그리기가 제자리에 끼워 그린다. 아니면 맨 아래.
  if (!기록그리기(본문, false)) 할일그리기();
  예약그리기();
  도구기록그리기();
  // 본문을 비우면 브라우저가 굴린 자리를 맨 위로 돌린다. 판은 3초마다 다시 그리므로
  // 제자리에 돌려놓지 않으면 위로 올려 앞 대화를 볼 수가 없었다(올리자마자 튕겼다).
  흐름.scrollTop = 바닥이었나 ? 흐름.scrollHeight : 옛자리;
  고르기그리기();
}

function 바닥인가(흐름) {
  return 흐름.scrollHeight - 흐름.scrollTop - 흐름.clientHeight < 60;
}

// ── 도구 한 줄 (클로드의 ⏺ 줄) ────────────────────────────────
// 한 줄만 보이고, 누르면 그 아래로 결과가 펴진다.
// 무엇이 펴져 있는지는 기억해 둔다. 새로 그려도 접히지 않게.

const 펴둔도구 = new Set();

function 때글(ms) {
  if (!ms) return '';
  return ms < 1000 ? ms + 'ms' : (ms / 1000).toFixed(1) + '초';
}

// 도구 호출은 됐어도(성공) 돌려본 명령이 끝번호 0 이 아니면(시험 실패 등) 나쁜 것으로 본다 — 안 그러면 실패한 시험이 정상처럼 보였다
function 도구나쁨(값) {
  return 값.성공 === false || /^끝번호 /.test(String(값.꼬리 || ''));
}

// ── 작업 묶음 ──────────────────────────────────────────────────
// GPT가 '짧은 말 → 도구' 를 되풀이하는 동안의 줄들(짧은 말 · 도구 · 거절된 소쿠리)을 클로드 화면처럼 한 줄 요약으로 접는다:
//   읽은 파일 5개, 찾은 글자 6번, 고친 파일 1개  [+9 −0] ›
// 누르면 그 안의 줄이 순서대로 펴지고, 줄을 누르면 결과·바뀐 줄이 펴진다.
// 길거나 표·목록이 든 말, 물음 카드, 사람 말, 예약 알림은 묶지 않고 그대로 보인다(중요한 글이 접혀 안 보이지 않게).
// 도구 뒤에 오는 마지막 짧은 말은 '답' 이라 묶음 밖에 그대로 보인다. 묶음은 늘 접힌 채 시작하고 눌러야 펴진다.
const 나물갈래 = {
  열무: '읽음', 버섯: '읽음', 취: '읽음',
  가지: '살핌', 토란: '살핌', 더덕: '살핌', 고사리: '살핌', 무: '살핌', 팥: '살핌',
  미나리: '찾음',
  상추: '만듦', 냉이: '만듦',
  부추: '고침', 쑥: '고침', 갓: '고침', 시금치: '고침', 미역: '고침',
  도라지: '실행', 두릅: '실행', 콩: '실행', 배추: '실행', 씨앗: '실행', 도토리: '실행', 열매: '실행',
  감자: '기록', 고구마: '기록', 우엉: '기록', 당근: '기록',
  칡: '깃',
  호박: '살핌', 오이: '살핌', 마늘: '실행',
};
const 줄라벨 = { 읽음: '읽음', 살핌: '살핌', 찾음: '찾음', 만듦: '생성됨', 고침: '수정됨', 실행: '실행', 기록: '기록', 깃: '깃', 기타: '도구' };
const 묶음말최대 = 240;
const 펴둔묶음 = new Map();      // 열쇠 → 사용자가 누른 상태(true 폄 · false 접음)
const 펴둔줄 = new Set();

// 도구 호출은 됐어도(성공) 돌려본 명령이 끝번호 0 이 아니면(시험 실패 등) 나쁜 것으로 본다 — 안 그러면 실패한 시험이 정상처럼 보였다
// (위에 있는 도구나쁨 을 쓴다)

function 짧은말인가(항목) {
  if (항목.종류 !== 'gpt') return false;
  const 글 = String(항목.글 || '').trim();
  if (!글 || 글.length > 묶음말최대) return false;
  if (글.indexOf(규약.물음시작) !== -1) return false;
  return 글.split('\n').length <= 3 && !/^\s*([-*•]|\d+[.)]|\||#)/m.test(글);
}

// 바구니를 못 읽어 도구는 안 돌고 소쿠리에만 '됨 거짓 / 탈 …' 이 남은 것 — 안 보이면 GPT가 왜 다시 쓰는지 모른다
function 거절소쿠리인가(목록, 번) {
  const 항목 = 목록[번];
  return 항목.종류 === '나' && /(^|\n)됨 거짓/.test(항목.글 || '') && !(번 > 0 && 목록[번 - 1].종류 === '도구');
}

function 줄값(항목) {
  try { return JSON.parse(항목.글) || {}; } catch (e) { return {}; }
}

// 기록을 { 항목 } 과 { 묶음 } 의 차례로 나눈다
function 묶음나누기(목록) {
  const 결과 = [];
  let 묶음 = null;
  let 대기말 = [];                  // 도구가 따라올지 아직 모르는 짧은 말
  const 말로내기 = () => { for (const 말 of 대기말) 결과.push({ 종류: '항목', 번: 말.번 }); 대기말 = []; };
  const 묶음에넣기 = (줄) => {
    if (!묶음) 묶음 = { 종류: '묶음', 줄들: [] };
    for (const 말 of 대기말) 묶음.줄들.push(말);
    대기말 = [];
    묶음.줄들.push(줄);
  };
  목록.forEach((항목, 번) => {
    if (항목.종류 === '요약') return;                    // 고친 파일 요약 카드는 묶음 요약이 대신한다
    if (항목.종류 === '나') {
      if (거절소쿠리인가(목록, 번)) 묶음에넣기({ 번, 종류: '거절', 항목 });
      return;                                              // 나머지 소쿠리 원문은 '도구' 줄이 대신한다
    }
    if (항목.종류 === '도구') { 묶음에넣기({ 번, 종류: '도구', 항목 }); return; }
    if (짧은말인가(항목)) { 대기말.push({ 번, 종류: '말', 항목 }); return; }
    if (묶음) { 결과.push(묶음); 묶음 = null; }            // 사람 말 · 예약 · 긴 말이 오면 묶음은 끝
    말로내기();
    결과.push({ 종류: '항목', 번 });
  });
  if (묶음) 결과.push(묶음);
  말로내기();
  return 결과;
}

function 묶음요약(줄들) {
  const 셈 = { 읽음: new Set(), 만듦: new Set(), 고침: new Set(), 찾음: 0, 살핌: 0, 실행: 0, 기록: 0, 깃: 0, 기타: 0 };
  let 더함 = 0;
  let 뺌 = 0;
  let 실패 = 0;
  for (const 줄 of 줄들) {
    if (줄.종류 === '거절') { 실패 += 1; continue; }
    if (줄.종류 !== '도구') continue;
    const 값 = 줄값(줄.항목);
    const 갈래 = 나물갈래[값.나물] || '기타';
    if (도구나쁨(값)) 실패 += 1;
    if (갈래 === '읽음' || 갈래 === '만듦' || 갈래 === '고침') 셈[갈래].add(String(값.대상 || 값.이름 || ''));
    else 셈[갈래] += 1;
    const 증감 = String(값.꼬리 || '').match(/^\+(\d+) -(\d+)$/);
    if (증감 && 값.성공 !== false) { 더함 += Number(증감[1]); 뺌 += Number(증감[2]); }
  }
  const 조각 = [];
  if (셈.읽음.size) 조각.push('읽은 파일 ' + 셈.읽음.size + '개');
  if (셈.찾음) 조각.push('찾은 글자 ' + 셈.찾음 + '번');
  if (셈.살핌) 조각.push('살펴본 것 ' + 셈.살핌 + '번');
  if (셈.만듦.size) 조각.push('만든 파일 ' + 셈.만듦.size + '개');
  if (셈.고침.size) 조각.push('고친 파일 ' + 셈.고침.size + '개');
  if (셈.실행) 조각.push('실행한 명령 ' + 셈.실행 + '개');
  if (셈.기록) 조각.push('차례·기억 ' + 셈.기록 + '번');
  if (셈.깃) 조각.push('깃 ' + 셈.깃 + '번');
  if (셈.기타) 조각.push('그 밖의 도구 ' + 셈.기타 + '개');
  return { 글: 조각.join(', ') || '작업', 더함, 뺌, 실패 };
}

function 세부있나(값) {
  return !!((값.미리 && (값.미리.줄들 || []).length) || 값.차이 || 값.귀띔);
}

function 작업세부그리기(값) {
  const 칸 = document.createElement('div');
  칸.className = '줄세부';
  if (값.미리 && (값.미리.줄들 || []).length) {
    const 속 = document.createElement('div');
    속.className = '세부글' + (값.미리.갈래 === '탈' ? ' 탈' : '');
    속.textContent = 값.미리.줄들.slice(0, 12).join(String.fromCharCode(10)) + (값.미리.잘림 || 값.미리.줄들.length > 12 ? String.fromCharCode(10) + '… 더 있습니다' : '');
    칸.appendChild(속);
  }
  if (값.차이) {
    for (const 글 of (값.차이.줄들 || []).slice(0, 40)) {
      const d = document.createElement('div');
      const 첫 = 글.charAt(0);
      d.className = '차이줄' + (첫 === '+' ? ' 더함' : 첫 === '-' ? ' 뺌' : 첫 === '@' ? ' 자리' : '');
      d.textContent = 글;
      칸.appendChild(d);
    }
  }
  if (값.귀띔) {
    const 띔 = document.createElement('div');
    띔.className = '세부귀띔';
    띔.textContent = '↳ ' + 값.귀띔;
    칸.appendChild(띔);
  }
  return 칸;
}

function 작업줄그리기(줄, 묶음열쇠) {
  const 열쇠 = 묶음열쇠 + ':' + 줄.번;
  const 틀 = document.createElement('div');
  const 머리 = document.createElement('div');
  머리.className = '작업줄머리';
  const 라벨 = document.createElement('span');
  라벨.className = '줄라벨';
  const 대상 = document.createElement('span');
  대상.className = '줄대상';
  const 꼬리 = document.createElement('span');
  꼬리.className = '줄꼬리';
  let 값 = null;
  let 눌러펼칠수있나 = false;

  if (줄.종류 === '말') {
    틀.className = '작업줄 말';
    const 글 = String(줄.항목.글 || '').trim();
    라벨.textContent = '말';
    대상.textContent = 펴둔줄.has(열쇠) ? 글 : 글.replace(/\s+/g, ' ').slice(0, 100) + (글.length > 100 ? '…' : '');
    눌러펼칠수있나 = 글.length > 100;
    if (펴둔줄.has(열쇠)) 틀.className += ' 펴짐';
  } else if (줄.종류 === '거절') {
    틀.className = '작업줄 도구 나쁨';
    const 탈 = String(줄.항목.글 || '').match(/^탈\s+(.+)$/m);
    라벨.textContent = '실패';
    대상.textContent = 탈 ? 탈[1].slice(0, 100) : '요청을 읽지 못함';
  } else {
    값 = 줄값(줄.항목);
    const 갈래 = 나물갈래[값.나물] || '기타';
    틀.className = '작업줄 도구' + (도구나쁨(값) ? ' 나쁨' : '');
    라벨.textContent = 줄라벨[갈래];
    대상.textContent = (갈래 === '찾음' && 값.찾는말) ? 값.찾는말 : (값.대상 || 값.이름 || '?');
    if (갈래 === '찾음' && 값.대상 && 값.찾는말) 꼬리.textContent = 값.대상 + (값.꼬리 ? ' · ' + 값.꼬리 : '');
    else if (값.꼬리 && !/^\+\d+ -\d+$/.test(값.꼬리)) 꼬리.textContent = String(값.꼬리).slice(0, 70);
    눌러펼칠수있나 = 세부있나(값);
  }
  머리.append(라벨, 대상);
  const 증감 = 값 && String(값.꼬리 || '').match(/^\+(\d+) -(\d+)$/);
  if (증감 && 값.성공 !== false) {
    const 칸 = document.createElement('span');
    칸.className = '줄증감';
    const 더 = document.createElement('span');
    더.className = '더함';
    더.textContent = '+' + 증감[1];
    const 빼 = document.createElement('span');
    빼.className = '뺌';
    빼.textContent = '−' + 증감[2];
    칸.append(더, 빼);
    머리.appendChild(칸);
  }
  if (꼬리.textContent) 머리.appendChild(꼬리);
  if (눌러펼칠수있나) {
    const 화살 = document.createElement('span');
    화살.className = '줄화살';
    화살.textContent = 펴둔줄.has(열쇠) ? '⌄' : '›';
    머리.appendChild(화살);
    머리.onclick = () => {
      if (펴둔줄.has(열쇠)) 펴둔줄.delete(열쇠); else 펴둔줄.add(열쇠);
      본문그리기();
    };
  } else {
    머리.style.cursor = 'default';
  }
  틀.appendChild(머리);
  if (눌러펼칠수있나 && 값 && 펴둔줄.has(열쇠)) 틀.appendChild(작업세부그리기(값));
  return 틀;
}

function 작업묶음그리기(본문, 묶음) {
  const 줄들 = 묶음.줄들;
  const 열쇠 = (줄들[0].항목.때 || '') + '#' + 줄들[0].번;
  const 요 = 묶음요약(줄들);
  const 펴짐 = 펴둔묶음.has(열쇠) ? 펴둔묶음.get(열쇠) : false;     // 늘 접힌 채 시작 — 일하는 중에도 저절로 펴지지 않는다(사용자 요청 2026-10-04)
  const 틀 = document.createElement('div');
  틀.className = '작업묶음' + (펴짐 ? ' 펴짐' : '') + (요.실패 ? ' 실패있음' : '');

  const 머리 = document.createElement('div');
  머리.className = '작업머리';
  const 글 = document.createElement('span');
  글.className = '작업요약';
  글.textContent = 요.글;
  머리.appendChild(글);
  if (요.더함 || 요.뺌) {
    const 증감 = document.createElement('span');
    증감.className = '작업증감';
    const 더 = document.createElement('span');
    더.className = '더함';
    더.textContent = '+' + 요.더함;
    const 빼 = document.createElement('span');
    빼.className = '뺌';
    빼.textContent = '−' + 요.뺌;
    증감.append(더, 빼);
    머리.appendChild(증감);
  }
  if (요.실패) {
    const 실패 = document.createElement('span');
    실패.className = '작업실패';
    실패.textContent = '실패 ' + 요.실패;
    머리.appendChild(실패);
  }
  const 화살 = document.createElement('span');
  화살.className = '작업화살';
  화살.textContent = 펴짐 ? '⌄' : '›';
  머리.appendChild(화살);
  머리.onclick = () => { 펴둔묶음.set(열쇠, !펴짐); 본문그리기(); };
  틀.appendChild(머리);

  if (펴짐) {
    const 목록칸 = document.createElement('div');
    목록칸.className = '작업목록';
    for (const 줄 of 줄들) 목록칸.appendChild(작업줄그리기(줄, 열쇠));
    틀.appendChild(목록칸);
  }
  본문.appendChild(틀);
}

function 도구그리기(본문, 값, 열쇠) {
  const 묶음 = document.createElement('div');
  묶음.className = '도구묶음';

  const 줄 = document.createElement('div');
  줄.className = '도구줄' + (!도구나쁨(값) && 값.성공 ? '' : ' 나쁨');

  const 알 = document.createElement('span');
  알.className = '알';
  알.textContent = '●';

  const 이름 = document.createElement('span');
  이름.className = '이름';
  이름.textContent = 값.이름 || '?';

  const 대상 = document.createElement('span');
  대상.className = '대상';
  대상.textContent = 값.대상 || '';
  누르면열기(대상, 값.대상);

  줄.append(알, 이름, 대상);

  if (값.꼬리) {
    const 꼬리 = document.createElement('span');
    // '+12 -3' 은 두 조각으로 갈라 색을 따로 준다
    const 증감 = String(값.꼬리).match(/^\+(\d+) -(\d+)$/);
    if (증감 && 값.성공) {
      const 더 = document.createElement('span');
      더.className = '꼬리 더함';
      더.textContent = '+' + 증감[1];
      const 빼 = document.createElement('span');
      빼.className = '꼬리 뺌';
      빼.textContent = '-' + 증감[2];
      줄.append(더, 빼);
    } else {
      꼬리.className = '꼬리';
      꼬리.textContent = String(값.꼬리).slice(0, 60);
      줄.appendChild(꼬리);
    }
  }

  if (값.걸린ms) {
    const 때 = document.createElement('span');
    때.className = '때';
    때.textContent = 때글(값.걸린ms);
    줄.appendChild(때);
  }

  묶음.appendChild(줄);

  const 펴짐 = 펴둔도구.has(열쇠);
  const 볼것 = 값.미리 || (값.차이 ? { 갈래: '차이' } : null);

  if (볼것) {
    줄.title = 펴짐 ? '눌러서 접기' : '눌러서 결과 보기';
    줄.onclick = () => {
      if (펴둔도구.has(열쇠)) 펴둔도구.delete(열쇠);
      else 펴둔도구.add(열쇠);
      본문그리기();
    };
  } else {
    줄.style.cursor = 'default';
  }

  // 실패한 것은 접지 않는다. 왜 실패했는지가 가장 급한 정보다.
  const 펼칠까 = 펴짐 || !값.성공;

  if (값.미리 && (값.미리.줄들 || []).length) {
    const 결과 = document.createElement('div');
    결과.className = '결과' + (값.미리.갈래 === '탈' ? ' 탈' : '');

    const 갈고리 = document.createElement('span');
    갈고리.className = '갈고리';
    갈고리.textContent = '⎿';

    const 속 = document.createElement('div');
    속.className = '속' + (펼칠까 ? '' : ' 접힘');
    속.textContent = 펼칠까
      ? 값.미리.줄들.join(String.fromCharCode(10))
      : (값.미리.줄들[0] || '');

    결과.append(갈고리, 속);
    묶음.appendChild(결과);

    if (펼칠까 && 값.미리.잘림) {
      const 더 = document.createElement('div');
      더.className = '더보기';
      더.textContent = '… 더 있습니다 (앞 ' + 값.미리.줄들.length + '줄만)';
      묶음.appendChild(더);
    }
  }

  if (값.차이 && 펼칠까) {
    const 차이 = document.createElement('div');
    차이.className = '차이';
    for (const 줄글 of (값.차이.줄들 || [])) {
      const d = document.createElement('div');
      const 첫 = 줄글.charAt(0);
      d.className = '줄' + (첫 === '+' ? ' 더함' : 첫 === '-' ? ' 뺌'
                            : 첫 === '@' ? ' 자리' : '');
      d.textContent = 줄글;
      차이.appendChild(d);
    }
    묶음.appendChild(차이);
    if (값.차이.잘림) {
      const 더 = document.createElement('div');
      더.className = '더보기';
      더.textContent = '… 바뀐 줄이 더 있습니다';
      묶음.appendChild(더);
    }
  }

  if (값.귀띔) {
    const 띔 = document.createElement('div');
    띔.className = '귀띔';
    띔.textContent = '↳ ' + 값.귀띔;
    묶음.appendChild(띔);
  }

  본문.appendChild(묶음);
}

// ── 할 일 (클로드의 체크리스트) ───────────────────────────────
// 하는 중이면 대화 맨 아래에 붙인다. 다 끝났으면 계획을 마지막으로 고친 뒤
// 사람이 처음 다시 말한 자리 바로 앞에 남긴다. 그 뒤 대화는 할 일 아래로 쌓인다.

const 계획나물 = new Set(['감자', '고구마']);

function 할일자리(목록) {
  const 계획 = 화면.계획;
  if (!계획 || !계획.일 || !(계획.차례 || []).length) return -1;
  const 다끝남 = 계획.차례.every((단계) => 단계.상태 === '끝' || 단계.상태 === '건너뜀');
  if (!다끝남) return -1;
  let 마지막계획 = -1;
  목록.forEach((항목, 번) => {
    if (항목.종류 !== '도구') return;
    try { if (계획나물.has(JSON.parse(항목.글).나물)) 마지막계획 = 번; } catch (e) { /* 넘어간다 */ }
  });
  if (마지막계획 < 0) return -1;
  for (let 번 = 마지막계획 + 1; 번 < 목록.length; 번++) {
    if (목록[번].종류 === '사용자') return 번;
  }
  return -1;
}

const 펴둔쪽지 = new Set();

function 할일그리기() {
  const 계획 = 화면.계획;
  if (!계획 || !계획.일 || !(계획.차례 || []).length) return;

  const 칸 = document.createElement('div');
  칸.className = '할일칸';

  const 머리 = document.createElement('div');
  머리.className = '할일머리';
  const 이름 = document.createElement('span');
  이름.textContent = '할 일';
  const 몇 = document.createElement('span');
  몇.className = '몇';
  몇.textContent = 계획.진도 || '';
  const 고침 = document.createElement('span');
  고침.className = '할일고침';
  고침.textContent = '✎';
  고침.title = '목표 고치기 · 접기 · 새로 세우기';
  고침.onclick = 목표열기;
  머리.append(이름, 몇, 고침);
  칸.appendChild(머리);

  // 서버가 쓰는 상태는 다섯 가지다 — 기다림 · 하는중 · 끝 · 실패 · 건너뜀
  const 네모글 = { 끝: '☒', 하는중: '◉', 실패: '✗', 건너뜀: '–', 기다림: '☐' };

  for (const 단계 of 계획.차례) {
    const 줄 = document.createElement('div');
    const 끝 = 단계.상태 === '끝' || 단계.상태 === '건너뜀';
    const 지금 = 단계.상태 === '하는중';
    줄.className = '할일' + (끝 ? ' 끝' : 지금 ? ' 지금' : '');

    const 네모 = document.createElement('span');
    네모.className = '네모';
    네모.textContent = 네모글[단계.상태] || '☐';

    const 글 = document.createElement('span');
    글.className = '글';
    글.textContent = 단계.이름 || '';

    줄.append(네모, 글);
    칸.appendChild(줄);
    // 쪽지는 수천 자일 수 있다(실제 계획이 그랬다). 한 줄로 접어 두고 누르면 편다.
    if (단계.쪽) {
      const 열쇠 = (계획.일 || '') + '#' + 단계.이름;
      const 쪽 = document.createElement('div');
      쪽.className = '할일쪽지' + (펴둔쪽지.has(열쇠) ? ' 펴짐' : '');
      쪽.textContent = 단계.쪽;
      쪽.title = 펴둔쪽지.has(열쇠) ? '눌러서 접기' : '눌러서 다 보기';
      쪽.onclick = () => {
        if (펴둔쪽지.has(열쇠)) 펴둔쪽지.delete(열쇠); else 펴둔쪽지.add(열쇠);
        본문그리기();
      };
      칸.appendChild(쪽);
    }
  }

  $('본문').appendChild(칸);
}

// 할 일을 대화 사이에 끼워 그렸으면 true. 도구만=true면 오른쪽 실행 기록 칸에
// 도구·파일 요약만 그린다. 대화 본문과 실행 기록을 같은 칸에 넣지 않는다.
function 기록그리기(본문 = $('본문'), 도구만 = false) {
  const 목록 = 화면.대화 || [];
  if (화면.방없는대화) {
    빈안내('이 대화에는 아직 일할 방이 없습니다. 프로젝트 안의 대화는 열면 바로, 그 밖의 대화는 도구를 처음 쓸 때 만들어집니다.');
    return false;
  }
  if (!화면.지금방) {
    if (!도구만) 빈안내('오른쪽 [일할 곳] 의 ＋ 로 일할 폴더를 고르세요.', 본문);
    return false;
  }
  if (목록.length === 0) {
    빈안내(도구만 ? '아직 실행 기록이 없습니다.'
      : '아직 한 일이 없습니다. ChatGPT 창에서 시키면 여기에 쌓입니다.', 본문);
    return false;
  }
  if (도구만 && !목록.some((항목) => 항목.종류 === '도구' || 항목.종류 === '요약')) {
    빈안내('아직 실행 기록이 없습니다.', 본문);
    return false;
  }
  const 끼울자리 = 도구만 ? -1 : 할일자리(목록);

  // 오른쪽 실행 기록 칸: 도구 한 줄(● … ⎿ 결과)과 파일 요약을 그대로 쌓는다
  if (도구만) {
    목록.forEach((항목, 번) => {
      if (항목.종류 === '도구') {
        let 값 = {};
        try { 값 = JSON.parse(항목.글); } catch (e) { /* 넘어간다 */ }
        // 옛 기록에는 미리보기도 차이도 없다. 그래도 한 줄은 그대로 그려진다.
        도구그리기(본문, 값, (항목.때 || '') + '#' + 번);
      } else if (항목.종류 === '요약') {
        let 값 = {};
        try { 값 = JSON.parse(항목.글); } catch (e) { /* 넘어간다 */ }
        요약그리기(본문, 값.목록 || []);
      }
    });
    return false;
  }

  // 대화 본문:  사람 말 → 상자 · GPT 답 → 마크다운 그대로(표·제목·코드덩이까지) ·
  //             GPT가 도구를 부르며 하는 동안의 줄들 → 한 줄 요약 '작업 묶음' (누르면 펴짐)
  const 부분들 = 묶음나누기(목록);
  const 마지막 = 부분들[부분들.length - 1];
  for (const 부분 of 부분들) {
    if (부분.종류 === '묶음') { 작업묶음그리기(본문, 부분); continue; }
    const 번 = 부분.번;
    const 항목 = 목록[번];
    if (번 === 끼울자리) 할일그리기();

    if (항목.종류 === '사용자') {
      const 상자 = document.createElement('div');
      상자.className = '사람말';
      const 꺾 = document.createElement('span');
      꺾.className = '꺾';
      꺾.textContent = '>';
      const 글 = document.createElement('span');
      글.className = '글';
      글.textContent = 선택보기(항목.글);
      상자.append(꺾, 글);
      본문.appendChild(상자);
      continue;
    }

    if (항목.종류 === '예약') {
      const 줄 = document.createElement('div');
      줄.className = '예약알림';
      줄.textContent = 항목.글;
      본문.appendChild(줄);
      continue;
    }

    // GPT가 쓴 글
    const 프로즈 = 프로즈만(물음풀기(항목.글));
    if (!프로즈) continue;
    const 답 = document.createElement('div');
    답.className = '답';
    마크다운그리기(프로즈, 답);
    본문.appendChild(답);
  }
  return 끼울자리 >= 0;
}

function 도구기록그리기() {
  const 칸 = $('도구기록');
  if (!칸) return;
  칸.textContent = '';
  기록그리기(칸, true);
}

// 한 묶음에서 손댄 파일을 한 장으로. 클로드의 '변경 요약' 자리다.
function 요약그리기(본문, 목록) {
  if (!목록.length) return;
  const 카드 = document.createElement('div');
  카드.className = '요약카드';

  const 머리 = document.createElement('div');
  머리.className = '요약머리';
  머리.textContent = '파일 ' + 목록.length + '개 고쳤습니다';
  카드.appendChild(머리);

  for (const 것 of 목록) {
    const 줄 = document.createElement('div');
    줄.className = '요약줄';
    const 밭 = document.createElement('span');
    밭.className = '요약밭';
    밭.textContent = 것.밭 || '';
    누르면열기(밭, 것.밭);
    const 증감 = document.createElement('span');
    증감.className = '요약증감';
    const 더 = document.createElement('span');
    더.className = '더함';
    더.textContent = '+' + (것.더한줄 || 0);
    const 빼 = document.createElement('span');
    빼.className = '뺌';
    빼.textContent = '-' + (것.뺀줄 || 0);
    증감.append(더, 빼);
    줄.append(밭, 증감);
    카드.appendChild(줄);
  }
  본문.appendChild(카드);
}

// ── 목표 창 (보기 · 고치기 · 접기 · 새로 세우기 · 지난 목표) ───────────────
// 목표는 GPT도 고치고 사용자도 고친다. 판에서 고친 것은 GPT가 다음 도구 결과에서 알게 된다.
// 접거나 바꿔도 앞 목표는 '지난 목표' 로 남아 되살릴 수 있고, 구조를 바꾼 수정은 되돌릴 수 있다.

const 목표폼 = { 열림: new Set() };       // 열려 있는 입력(이름 고치기·새 목표·포기 …). 있으면 다시 그리지 않는다
const 상태순환 = { 기다림: '하는중', 하는중: '끝', 끝: '기다림', 실패: '기다림', 건너뜀: '기다림' };
const 단계표 = { 끝: '☑', 하는중: '▶', 실패: '✗', 건너뜀: '–', 기다림: '☐' };

async function 계획짓(짓, 인자 = {}) {
  const 답 = await 서버에게({ 종류: '계획짓', 몸통: { 방: 화면.지금방 || '', 짓, ...인자 } });
  if (답 && 답.됨) {
    화면.계획 = 답;
    목표폼.열림.clear();
    if ($('목표창').style.display === 'flex') 목표그리기();
    목표알림그리기();
    본문그리기();
    if (답.한일) 알림(답.한일);
  } else if (답) {
    알림('⚠ ' + (답.탈 || '하지 못했습니다'));
  }
  return 답;
}

function 목표열기() {
  목표폼.열림.clear();
  목표그리기();
  $('목표창').style.display = 'flex';
}

// 요소 안을 입력칸으로 바꾼다. Enter 저장 · Esc 취소 · 밖을 누르면 저장.
function 목표입력(요소, 지금값, 저장하기, 열쇠) {
  목표폼.열림.add(열쇠);
  const 칸 = 칸만들기('input', '목표입력');
  칸.value = 지금값 || '';
  요소.textContent = '';
  요소.appendChild(칸);
  칸.focus();
  let 끝남 = false;
  const 마치기 = (저장할까) => {
    if (끝남) return;
    끝남 = true;
    목표폼.열림.delete(열쇠);
    const 새 = 칸.value.trim();
    if (저장할까 && 새 && 새 !== (지금값 || '')) 저장하기(새);
    else 목표그리기();
  };
  칸.onkeydown = (e) => {
    e.stopPropagation();
    if (e.key === 'Enter') { e.preventDefault(); 마치기(true); }
    if (e.key === 'Escape') { e.preventDefault(); 마치기(false); }
  };
  칸.onblur = () => 마치기(true);
  칸.onclick = (e) => e.stopPropagation();
}

function 목표단추(글, 눌렀을때, 제목) {
  const 단추 = 칸만들기('button', '작은', 글);
  if (제목) 단추.title = 제목;
  단추.onclick = 눌렀을때;
  return 단추;
}

function 목표단계줄(단계, 번, 전체수) {
  const 틀 = 칸만들기('div', '목표단계');
  const 줄 = 칸만들기('div', '목표줄 ' + 단계.상태);
  const 네모 = 칸만들기('span', '네모', 단계표[단계.상태] || '☐');
  네모.title = '눌러서 상태 바꾸기 (☐ → ▶ → ☑)';
  네모.onclick = () => 계획짓('상태', { 몇: 번, 상태: 상태순환[단계.상태] || '기다림' });
  const 이름 = 칸만들기('span', '이름', 단계.이름);
  이름.title = '눌러서 이름 고치기';
  이름.onclick = () => 목표입력(이름, 단계.이름, (새) => 계획짓('고치기', { 몇: 번, 이름: 새 }), '단계' + 번);
  const 도구 = 칸만들기('span', '도구');
  const 위 = 칸만들기('span', '도구단추' + (번 === 1 ? ' 끔' : ''), '▲');
  위.title = '위로';
  위.onclick = () => 계획짓('옮기기', { 몇: 번, 새몇: 번 - 1 });
  const 아래 = 칸만들기('span', '도구단추' + (번 === 전체수 ? ' 끔' : ''), '▼');
  아래.title = '아래로';
  아래.onclick = () => 계획짓('옮기기', { 몇: 번, 새몇: 번 + 1 });
  const 빼기 = 칸만들기('span', '도구단추' + (전체수 === 1 ? ' 끔' : ''), '✕');
  빼기.title = '이 단계 빼기 (되돌리기로 살릴 수 있습니다)';
  빼기.onclick = () => 계획짓('빼기', { 몇: 번 });
  도구.append(위, 아래, 빼기);
  줄.append(네모, 이름, 도구);
  틀.appendChild(줄);
  if (단계.쪽) 틀.appendChild(칸만들기('div', '쪽지', 단계.쪽));
  return 틀;
}

// 새 목표 · 목표 포기 입력 칸 (목표 창 안에서 펼친다)
function 새목표폼(있음) {
  const 틀 = 칸만들기('div', '목표폼칸');
  const 일 = 칸만들기('input', '목표입력');
  일.placeholder = '목표 이름 (나중에 보고 알아볼 만큼)';
  const 차례 = 칸만들기('textarea', '목표입력');
  차례.rows = 5;
  차례.placeholder = '단계를 한 줄에 하나씩';
  틀.append(일, 차례);
  let 왜 = null;
  if (있음) {
    왜 = 칸만들기('input', '목표입력');
    왜.placeholder = '앞 목표를 바꾸는 까닭 (선택)';
    틀.appendChild(왜);
    const 계획 = 화면.계획 || {};
    틀.appendChild(칸만들기('div', '안내', "지금 목표 '" + (계획.일 || '') + "' (" + (계획.진도 || '') + ') 는 지난 목표로 보관됩니다.'));
  }
  const 줄 = 칸만들기('div', '줄');
  줄.append(
    목표단추('세우기', () => {
      const 일글 = (일.value || '').trim();
      const 차례글 = 차례.value || '';
      if (!일글 || !차례글.trim()) { 알림('⚠ 목표 이름과 단계를 적어 주세요'); return; }
      void 계획짓('세우기', { 일: 일글, 차례: 차례글, 왜: 왜 ? (왜.value || '').trim() : '' });
    }),
    목표단추('취소', () => { 목표폼.열림.delete('새목표'); 목표그리기(); }),
  );
  틀.appendChild(줄);
  return 틀;
}

function 포기폼() {
  const 계획 = 화면.계획 || {};
  const 틀 = 칸만들기('div', '목표폼칸');
  const 왜 = 칸만들기('input', '목표입력');
  왜.placeholder = '접는 까닭 (선택)';
  틀.appendChild(왜);
  틀.appendChild(칸만들기('div', '안내', "'" + (계획.일 || '') + "' (" + (계획.진도 || '') + ') 를 접습니다. 지난 목표로 보관되어 나중에 되살릴 수 있습니다.'));
  const 줄 = 칸만들기('div', '줄');
  줄.append(
    목표단추('접기', () => void 계획짓('포기', { 왜: (왜.value || '').trim() })),
    목표단추('취소', () => { 목표폼.열림.delete('포기'); 목표그리기(); }),
  );
  틀.appendChild(줄);
  return 틀;
}

function 지난목표줄(항목, 지금있음) {
  const 틀 = 칸만들기('div', '지난목표');
  틀.appendChild(칸만들기('div', '일', 항목.일 || '(이름 없음)'));
  틀.appendChild(칸만들기('div', '뜻', [항목.진도, 항목.까닭, 항목.끝낸때, 항목.누가 ? 항목.누가 + '가' : ''].filter(Boolean).join(' · ')));
  if (항목.이유) 틀.appendChild(칸만들기('div', '이유', 항목.이유));
  const 줄 = 칸만들기('div', '줄');
  줄.appendChild(목표단추('되살리기', () => void 계획짓('되살리기', { 번호: 항목.번호 }),
    지금있음 ? '지금 목표는 지난 목표로 보관되고, 이 목표가 지금 목표가 됩니다' : '이 목표를 지금 목표로 되살립니다'));
  틀.appendChild(줄);
  return 틀;
}

function 목표그리기() {
  const 몸 = $('목표몸');
  몸.textContent = '';
  const 계획 = 화면.계획 || {};
  const 단계들 = 계획.차례 || [];
  const 있음 = !!(계획.일 || 단계들.length);

  if (있음) {
    const 진도 = 칸만들기('div', '', 계획.진도 || '');
    진도.style.cssText = 'color:var(--흐린글);font-size:11.5px';
    몸.appendChild(진도);

    const 제목줄 = 칸만들기('div', '목표제목줄');
    const 제목 = 칸만들기('div', '', 계획.일 || '(이름 없음)');
    제목.id = '목표제목';
    제목.title = '눌러서 목표 이름 고치기';
    제목.onclick = () => 목표입력(제목, 계획.일, (새) => 계획짓('목표고치기', { 일: 새 }), '제목');
    제목줄.appendChild(제목);
    몸.appendChild(제목줄);

    단계들.forEach((단계, 칸번) => 몸.appendChild(목표단계줄(단계, 칸번 + 1, 단계들.length)));

    const 더하기 = 칸만들기('div', '목표더하기');
    const 입력 = 칸만들기('input', '목표입력');
    입력.placeholder = '＋ 단계 더하기 (Enter)';
    입력.onkeydown = (e) => {
      e.stopPropagation();
      if (e.key === 'Enter' && 입력.value.trim()) { e.preventDefault(); void 계획짓('더하기', { 이름: 입력.value.trim() }); }
    };
    입력.oninput = () => { if (입력.value) 목표폼.열림.add('더하기'); else 목표폼.열림.delete('더하기'); };
    더하기.appendChild(입력);
    몸.appendChild(더하기);
  } else {
    몸.appendChild(칸만들기('div', '빈안내', '세운 목표가 없습니다. 아래에서 새로 세우거나 지난 목표를 되살릴 수 있습니다.'));
  }

  const 되돌림수 = 계획.되돌림수 || 0;
  const 단추줄 = 칸만들기('div', '목표단추줄');
  단추줄.appendChild(목표단추('새 목표 세우기', () => { 목표폼.열림.add('새목표'); 목표폼.칸.textContent = ''; 목표폼.칸.appendChild(새목표폼(있음)); }));
  if (있음) 단추줄.appendChild(목표단추('목표 포기', () => { 목표폼.열림.add('포기'); 목표폼.칸.textContent = ''; 목표폼.칸.appendChild(포기폼()); }));
  const 되돌림 = 목표단추('되돌리기' + (되돌림수 ? ' (' + 되돌림수 + ')' : ''), () => void 계획짓('되돌리기'),
    (계획.최근고침 && 계획.최근고침.무엇) ? '마지막 수정: ' + 계획.최근고침.무엇 : '마지막 수정을 되돌립니다');
  되돌림.disabled = !되돌림수;
  단추줄.appendChild(되돌림);
  몸.appendChild(단추줄);

  목표폼.칸 = 칸만들기('div', '');
  몸.appendChild(목표폼.칸);
  // 입력이 열려 있던 채로 다시 그려졌으면(방을 바꾸는 등) 열린 것은 닫는다
  목표폼.열림.clear();

  const 지난 = 계획.지난목표 || [];
  if (지난.length) {
    몸.appendChild(칸만들기('div', '지난목표머리', '지난 목표 (' + 지난.length + ')'));
    for (const 항목 of 지난) 몸.appendChild(지난목표줄(항목, 있음));
  }
}

// GPT가 목표를 바꿨으면 입력칸 위에 한 줄로 알리고, 마음에 안 들면 바로 되돌릴 수 있게 한다
function 알림끈적있나(때) {
  try { return localStorage.getItem('목표알림끔:' + 때) === '1'; } catch (e) { return false; }
}

function 목표알림그리기() {
  const 칸 = $('목표알림');
  if (!칸) return;
  칸.textContent = '';
  const 계획 = 화면.계획 || {};
  const 고침 = 계획.최근고침;
  const 보일까 = !!(고침 && 고침.누가 === 'GPT' && !고침.되돌림 && (계획.되돌림수 || 0) > 0
    && (Date.now() / 1000 - 고침.때) < 600 && !알림끈적있나(고침.때));
  if (!보일까) { 칸.hidden = true; return; }
  칸.hidden = false;
  const 줄 = 칸만들기('div', '알림줄');
  줄.appendChild(칸만들기('span', '글', '✎ GPT가 목표를 바꿨습니다 — ' + 고침.무엇));
  줄.appendChild(목표단추('되돌리기', () => void 계획짓('되돌리기'), '바꾸기 전 모양으로 돌립니다'));
  const 닫기 = 칸만들기('span', '닫기', '✕');
  닫기.title = '알림 닫기';
  닫기.onclick = () => {
    try { localStorage.setItem('목표알림끔:' + 고침.때, '1'); } catch (e) { /* 이번 판에서만 */ }
    칸.hidden = true;
  };
  줄.appendChild(닫기);
  칸.appendChild(줄);
}

// ── 일할 곳 (폴더 / 방) — 늘 보이는 위칸에 그린다 ──────────────

// ── 파일 나무 ─────────────────────────────────────────────────
// 일하는 폴더와 이 방의 자료 칸을 탐색기처럼 펼쳐 본다.
// 한 겹씩만 물어본다 — 큰 폴더를 한꺼번에 훑으면 창이 멈춘다.

const 펼친것 = new Set();      // 펼쳐 둔 칸의 밭
let 거른글 = '';               // 거르개에 친 글자 (소문자)
let 고른파일 = '';             // 지금 열어 둔 파일의 밭
let 그린파일수 = 0;            // 이번에 그린 파일 줄 수 (걸린 게 없나 보려고)

function 크기글(바이트) {
  if (!바이트) return '';
  if (바이트 < 1024) return 바이트 + 'B';
  if (바이트 < 1024 * 1024) return (바이트 / 1024).toFixed(0) + 'K';
  return (바이트 / 1024 / 1024).toFixed(1) + 'M';
}

// 갈래마다 다른 딱지. 그림 문자 대신 글자 딱지를 쓴다 —
// 좁은 칸에서 줄 높이가 들쭉날쭉하지 않고, 색으로 갈래가 바로 보인다.
const 코드끝 = ['py', 'js', 'ts', 'tsx', 'jsx', 'json', 'html', 'css', 'c', 'cpp',
                'h', 'java', 'go', 'rs', 'rb', 'sh', 'bat', 'ps1', 'yml', 'yaml', 'toml'];
const 글월끝 = ['md', 'txt', 'log', 'csv'];
const 그림끝 = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'ico'];

function 딱지값(이름, 칸인가) {
  // 칸은 앞의 꺾쇠(▸▾)가 이미 칸이라는 뜻이다. 딱지까지 붙이면 ▸▸ 로 겹친다.
  if (칸인가) return { 글: '', 결: '' };
  const 끝 = (이름.split('.').pop() || '').toLowerCase();
  if (코드끝.includes(끝)) return { 글: '</>', 결: '코드' };
  if (글월끝.includes(끝)) return { 글: '✎', 결: '글월' };
  if (그림끝.includes(끝)) return { 글: '▨', 결: '그림' };
  return { 글: '·', 결: '' };
}

async function 칸속묻기(몸통) {
  const 답 = await 서버에게({ 종류: '칸보기', 몸통 });
  return (답 && 답.됨) ? 답 : null;
}

async function 칸그리기(담을곳, 몸통) {
  const 답 = await 칸속묻기(몸통);
  담을곳.textContent = '';
  if (!답) {
    const d = document.createElement('div');
    d.className = '나무빔';
    d.textContent = '볼 수 없습니다.';
    담을곳.appendChild(d);
    return null;
  }
  if (!(답.것들 || []).length) {
    const d = document.createElement('div');
    d.className = '나무빔';
    d.textContent = '(빈 칸)';
    담을곳.appendChild(d);
    return 답.밭;
  }

  for (const 것 of (답.것들 || [])) {
    // 거른 글자가 있으면 이름에 그 글자가 든 것만 보여준다.
    // 칸(폴더)은 속에 걸리는 것이 있을 수 있으니 늘 남긴다.
    if (거른글 && !것.칸인가 &&
        (것.이름 || '').toLowerCase().indexOf(거른글) === -1) continue;

    const 줄 = document.createElement('div');
    줄.className = '칸줄' + (것.칸인가 ? ' 칸' : '')
                 + (것.밭 === 고른파일 ? ' 고름' : '');
    줄.title = 것.밭;

    const 꺾쇠 = document.createElement('span');
    꺾쇠.className = '꺾쇠';
    꺾쇠.textContent = 것.칸인가 ? (펼친것.has(것.밭) ? '▾' : '▸') : '';
    const 딱지값것 = 딱지값(것.이름, 것.칸인가);
    const 딱지 = document.createElement('span');
    딱지.className = '딱지' + (딱지값것.결 ? ' ' + 딱지값것.결 : '');
    딱지.textContent = 딱지값것.글;
    const 글자 = document.createElement('span');
    글자.className = '글자';
    글자.textContent = 것.이름;
    const 크기 = document.createElement('span');
    크기.className = '크기';
    크기.textContent = 것.칸인가 ? '' : 크기글(것.크기);
    줄.append(꺾쇠, 딱지, 글자, 크기);
    담을곳.appendChild(줄);

    if (!것.칸인가) {
      그린파일수 += 1;
      // 파일은 눌러서 바로 속을 본다. 나무가 보여 주기만 하면 반쪽이다.
      줄.style.cursor = 'pointer';
      줄.title = 것.밭 + '  —  눌러서 보기';
      줄.onclick = (e) => { e.stopPropagation(); 파일열기(것.밭); };
      continue;
    }

    // 거른 글자가 있으면 칸은 저절로 펴서 속까지 보여준다
    if (거른글 && !펼친것.has(것.밭)) 펼친것.add(것.밭);

    const 속 = document.createElement('div');
    속.className = '속칸';
    담을곳.appendChild(속);

    const 펼치기 = async () => {
      if (펼친것.has(것.밭)) {
        펼친것.delete(것.밭);
        속.textContent = '';
        꺾쇠.textContent = '▸';
      } else {
        펼친것.add(것.밭);
        꺾쇠.textContent = '▾';
        await 칸그리기(속, { 밭: 것.밭 });
      }
    };
    줄.onclick = 펼치기;
    if (펼친것.has(것.밭)) await 칸그리기(속, { 밭: 것.밭 });
  }
  return 답.밭;
}

function 뿌리머리(글, 밭) {
  const 줄 = document.createElement('div');
  줄.className = '뿌리이름';
  const 이름 = document.createElement('span');
  이름.textContent = 글;
  const 밭글 = document.createElement('span');
  밭글.className = '밭글';
  밭글.textContent = 밭 || '';
  밭글.title = 밭 || '';
  줄.append(이름, 밭글);
  return 줄;
}

function 빈파일칸(굵은글, 잔글) {
  const 칸 = document.createElement('div');
  칸.className = '빈파일칸';
  const 딱지 = document.createElement('div');
  딱지.className = '큰딱지';
  딱지.textContent = '🗀';
  const 굵게 = document.createElement('div');
  굵게.className = '굵게';
  굵게.textContent = 굵은글;
  const 글 = document.createElement('div');
  글.className = '글';
  글.textContent = 잔글;
  칸.append(딱지, 굵게, 글);
  return 칸;
}

// 나무 그리기는 서버를 기다리는 동안 또 불릴 수 있다(파일을 연달아 열 때).
// 둘이 같은 칸에 번갈아 붙이면 '방 자료' 가 두 번 나온다(실제로 그랬다).
// 그래서 떼어 둔 칸에 다 그린 뒤, 가장 나중에 부른 것만 화면에 붙인다.
let 나무그림번호 = 0;

async function 파일나무그리기() {
  const 이번 = ++나무그림번호;
  const 칸 = $('파일나무');
  const 새칸 = document.createElement('div');
  let 센파일 = 0;

  if (!화면.지금방) {
    새칸.appendChild(빈파일칸(
      '일할 곳이 없습니다',
      '위 [일할 곳] 의 ＋ 로 폴더를 고르면 그 안이 여기 보입니다.'));
  } else {
    그린파일수 = 0;
    const 일머리 = 뿌리머리('', '');
    새칸.appendChild(일머리);
    const 일속 = document.createElement('div');
    새칸.appendChild(일속);
    const 일밭 = await 칸그리기(일속, { 어디: '일' });
    if (이번 !== 나무그림번호) return;          // 그사이 새로 불렸다 — 이건 버린다
    if (일밭) { 일머리.lastChild.textContent = 일밭; 일뿌리 = 일밭; }

    const 방머리 = 뿌리머리('방 자료', '');
    새칸.appendChild(방머리);
    const 방속 = document.createElement('div');
    새칸.appendChild(방속);
    const 방밭 = await 칸그리기(방속, { 어디: '방' });
    if (이번 !== 나무그림번호) return;
    if (방밭) { 방머리.lastChild.textContent = 방밭; 방뿌리 = 방밭; }
    센파일 = 그린파일수;

    // 걸러 놓고 하나도 안 걸리면 그렇다고 말해 준다.
    // (빈 화면만 보여 주면 고장인지 없는 건지 모른다)
    if (거른글 && 센파일 === 0) {
      새칸.appendChild(빈파일칸('걸린 파일이 없습니다', '"' + 거른글 + '" 가 든 이름이 없습니다.'));
    }
  }

  칸.textContent = '';
  칸.appendChild(새칸);
}

// ── 파일 거르개 ───────────────────────────────────────────────

let 거르개시계 = 0;

$('거르개').addEventListener('input', () => {
  const 글 = ($('거르개').value || '').trim().toLowerCase();
  $('거르개칸').classList.toggle('찼음', !!글);
  거른글 = 글;
  // 한 글자 칠 때마다 서버를 훑으면 느리다. 잠깐 쉬었다 그린다.
  clearTimeout(거르개시계);
  거르개시계 = setTimeout(() => 파일나무그리기(), 180);
});

$('거르개지우기').onclick = () => {
  $('거르개').value = '';
  $('거르개칸').classList.remove('찼음');
  거른글 = '';
  파일나무그리기();
};

$('파일새로고침').onclick = () => { 파일나무그리기(); };

// ── 오른쪽 칸 세로 가름대 ─────────────────────────────────────
// 보이는 두 칸 사이를 공통 방식으로 끌어 바꾼다. 가름대 바로 위 칸과 그 아래 보이는 칸이 높이를 나눠 갖는다.
function 세로가름대달기(가름대, 윗칸이름) {
  let 끄는중 = false;
  가름대.onmousedown = (e) => { 끄는중 = true; e.preventDefault(); };
  document.addEventListener('mousemove', (e) => {
    if (!끄는중) return;
    const 보임 = 칸순서.filter(칸보이나);
    const 번 = 보임.findIndex((항) => 항.이름 === 윗칸이름);
    if (번 < 0 || 번 + 1 >= 보임.length) return;
    const 높이들 = 보임.map((항) => $(항.칸).getBoundingClientRect().height);
    const 윗위 = $(보임[번].칸).getBoundingClientRect().top;
    const 새 = 가름대높이나누기(높이들, 번, e.clientY - 윗위);
    const 총 = 새.reduce((a, b) => a + b, 0) || 1;
    const 몫들 = {};
    보임.forEach((항, 순) => { 몫들[항.이름] = 새[순] / 총; });
    칸몫정하기(몫들);
  });
  document.addEventListener('mouseup', () => {
    if (!끄는중) return;
    끄는중 = false;
    배치저장();
  });
}

세로가름대달기($('현황가름대'), '현황');
세로가름대달기($('기록나무가름대'), '일할곳');
세로가름대달기($('세로가름대'), '기록');

function 나무그리기() {
  for (const 열쇠 of Object.keys(방줄들)) delete 방줄들[열쇠];
  const 대상 = $('나무');
  대상.textContent = '';
  const 나무 = 화면.나무;

  if (!나무 || !나무.폴더들 || 나무.폴더들.length === 0) {
    const d = document.createElement('div');
    d.className = '빈안내';
    d.textContent = '위의 ＋ 로 일할 폴더를 고르세요.';
    대상.appendChild(d);
    return;
  }

  for (const 폴더 of 나무.폴더들) {
    const 폴더줄 = document.createElement('div');
    폴더줄.className = '폴더';

    const 이름 = document.createElement('span');
    이름.className = '이름';
    이름.textContent = 폴더.이름;
    이름.title = 폴더.밭 || '';
    if (폴더.프로젝트) 이름.textContent = '◈ ' + 폴더.이름;   // ChatGPT 프로젝트 묶음
    // 없어진 폴더는 서버가 아예 안 보내므로 여기서 따로 표시할 일이 없다.
    이름.ondblclick = () => 폴더.쪽번호 && 이름고치기(이름, 폴더.이름,
      (새) => 폴더짓({ 짓: '이름', 쪽번호: 폴더.쪽번호, 이름: 새 }));
    폴더줄.appendChild(이름);

    // 프로젝트 묶음인데 일할 폴더를 아직 안 골랐으면 여기서 한 번 고른다
    if (폴더.프로젝트 && !폴더.있음) {
        const 고름 = document.createElement('button');
        고름.className = '알약';
        고름.textContent = 폴더.밭 ? '폴더 다시 고르기' : '폴더 고르기';
        고름.title = '이 ChatGPT 프로젝트의 대화들이 쓸 폴더를 고릅니다';
        고름.onclick = (e) => { e.stopPropagation(); 묶음폴더고르기(폴더.쪽번호); };
        폴더줄.appendChild(고름);
    }

    const 더하기 = document.createElement('span');
    더하기.className = '작은아이콘 늘보임';
    더하기.textContent = '＋';
    더하기.title = '이 폴더에서 새 대화';
    더하기.onclick = (e) => {
      e.stopPropagation();
      새대화열기(폴더.쪽번호 || '');
    };
    폴더줄.appendChild(더하기);

    if (폴더.쪽번호) {
      const 점 = document.createElement('span');
      점.className = '작은아이콘';
      점.textContent = '⋮';
      점.onclick = (e) => {
        e.stopPropagation();
        메뉴열기(점, [
          { 글: '이름 바꾸기', 동작: () => 이름고치기(이름, 폴더.이름,
              (새) => 폴더짓({ 짓: '이름', 쪽번호: 폴더.쪽번호, 이름: 새 })) },
          ...(폴더.프로젝트 ? [{ 글: '일할 폴더 바꾸기', 동작: () => 묶음폴더고르기(폴더.쪽번호) }] : []),
          { 글: '목록에서 빼기', 동작: () => 폴더짓({ 짓: '빼기', 쪽번호: 폴더.쪽번호 }) },
        ]);
      };
      폴더줄.appendChild(점);
    }

    폴더줄.ondragover = (e) => { e.preventDefault(); 폴더줄.classList.add('끌림'); };
    폴더줄.ondragleave = () => 폴더줄.classList.remove('끌림');
    폴더줄.ondrop = (e) => {
      e.preventDefault();
      폴더줄.classList.remove('끌림');
      const 옮길것 = e.dataTransfer.getData('text/plain');
      if (옮길것) 방짓({ 짓: '폴더이동', 쪽번호: 옮길것, 폴더: 폴더.쪽번호 || '' });
    };

    대상.appendChild(폴더줄);

    for (const 방 of 폴더.방들) {
      const 방줄 = document.createElement('div');
      방줄.className = '방' + (방.쪽번호 === 화면.지금방 ? ' 지금' : '');
      방줄.draggable = true;
      방줄.ondragstart = (e) => {
        e.dataTransfer.setData('text/plain', 방.쪽번호);
        e.dataTransfer.effectAllowed = 'move';
      };

      const 알 = document.createElement('span');
      알.className = '알';
      방줄.appendChild(알);

      const 방이름 = document.createElement('span');
      방이름.className = '이름';
      // 새 대화로 넘긴 방은 한 방 그대로 두고 지금 몇 번째 대화인지만 붙인다
      방이름.textContent = (방.부모 ? '↳ ' : '') + 방.이름 + ((방.대화차례 || 1) > 1 ? ' · ' + 방.대화차례 + '번' : '')
        + (방.역할 ? ' (' + 방.역할 + (방.일꾼상태 ? ' · ' + 방.일꾼상태 : '') + ')' : '');
      방이름.title = 방.마지막 ? '마지막 ' + 방.마지막 : '';
      방이름.ondblclick = (e) => {
        e.stopPropagation();
        이름고치기(방이름, 방.이름,
          (새) => 방짓({ 짓: '이름', 쪽번호: 방.쪽번호, 이름: 새 }));
      };
      방줄.appendChild(방이름);

      const 막대칸 = document.createElement('span');
      막대칸.className = '방현황';
      방줄.appendChild(막대칸);
      방줄들[방.쪽번호] = { 줄: 방줄, 알, 막대칸 };
      방막대맞추기(방.쪽번호);

      const 방점 = document.createElement('span');
      방점.className = '작은아이콘';
      방점.textContent = '⋮';
      방점.onclick = (e) => {
        e.stopPropagation();
        메뉴열기(방점, [
          { 글: '이름 바꾸기', 동작: () => 이름고치기(방이름, 방.이름,
              (새) => 방짓({ 짓: '이름', 쪽번호: 방.쪽번호, 이름: 새 })) },
          // 꽉 차서 넘겨준 옛 ChatGPT 대화들 — 최근 것부터
          ...(방.대화들 || []).slice().reverse().map((옛, 번) => ({
            글: '이전 대화 ' + ((방.대화들 || []).length - 번), 쪽: '열기',
            동작: () => 대화로가기({ ...방, 대화: 옛, 지금: false }),
          })),
          ...(방.부모 ? [
            { 글: '일꾼 멈추기', 동작: () => 일꾼짓('그만', 방.쪽번호) },
            { 글: '일꾼 다시', 쪽: '새 탭에서', 동작: () => 일꾼짓('다시', 방.쪽번호) },
            ...(방.역할 === '구현' && 방.일꾼상태 === '끝'
              ? [{ 글: '일꾼 합치기', 쪽: '본 폴더에 합치기', 동작: () => 일꾼짓('합치기', 방.쪽번호) }] : []),
          ] : []),
          { 글: '목록에서 빼기', 동작: () => 방짓({ 짓: '빼기', 쪽번호: 방.쪽번호 }) },
        ]);
      };
      방줄.appendChild(방점);

      방줄.onclick = () => 대화로가기(방);

      대상.appendChild(방줄);
    }
  }
}

function 이름고치기(줄, 지금이름, 저장하기) {
  const 칸 = document.createElement('input');
  칸.className = '이름고침';
  칸.value = 지금이름;
  줄.textContent = '';
  줄.appendChild(칸);
  칸.focus();
  칸.select();

  let 끝남 = false;
  const 마치기 = (저장할까) => {
    if (끝남) return;
    끝남 = true;
    const 새 = 칸.value.trim();
    if (저장할까 && 새 && 새 !== 지금이름) 저장하기(새);
    else 나무그리기();
  };
  칸.onkeydown = (e) => {
    e.stopPropagation();
    if (e.key === 'Enter') { e.preventDefault(); 마치기(true); }
    if (e.key === 'Escape') { e.preventDefault(); 마치기(false); }
  };
  칸.onblur = () => 마치기(true);
  칸.onclick = (e) => e.stopPropagation();
}

// ── 방을 누르면 그 대화로 ──────────────────────────────────────
// 방은 ChatGPT 대화 하나에 붙어 있다. 판에서 방을 누르면 서버의 '지금 방' 만
// 바꾸던 것을, 이 창의 ChatGPT 탭을 그 대화로 옮기게 했다(클로드에서 세션을
// 누르면 그 세션이 열리는 것과 같다). 탭이 옮겨 가면 탭이 제 방을 다시 잡는다.

const 챗주소뿌리 = 'https://chatgpt.com';

async function 탭옮기기(주소) {
  const 탭 = await 챗탭찾기();
  if (탭 === null) {
    알림('⚠ 이 창에 ChatGPT 화면이 없습니다.');
    return false;
  }
  try {
    await chrome.tabs.update(탭, { url: 주소 });
    return true;
  } catch (e) {
    알림('⚠ ChatGPT 화면을 옮기지 못했습니다: ' + e.message);
    return false;
  }
}

async function 대화주소(대화) {
  const 기본 = 챗주소뿌리 + '/c/' + 대화;
  const 탭 = await 챗탭찾기();
  if (탭 === null || !chrome.tabs.get) return 기본;
  try {
    const 현재 = await chrome.tabs.get(탭);
    const 경로 = new URL(현재.url || '').pathname;
    // GPT·프로젝트 안의 대화는 앞의 경로를 버리면 일반 ChatGPT 대화가 된다.
    const 앞 = 경로.match(/^\/(g\/[^/]+|projects\/[^/]+)\/c\//);
    return 앞 ? 챗주소뿌리 + '/' + 앞[1] + '/c/' + 대화 : 기본;
  } catch (e) {
    return 기본;
  }
}

async function 대화로가기(방) {
  if (!방) return;
  if (방.대화) {
    if (방.지금) return;
    if (await 탭옮기기(await 대화주소(방.대화))) 알림('대화를 엽니다: ' + 방.이름);
    return;
  }
  // 아직 대화가 안 붙은 방 — 이 방을 지금 방으로 두고 새 대화를 연다.
  // 첫 말을 보내 대화 번호가 생기면 서버가 이 방을 그 대화에 붙인다.
  await 방짓({ 짓: '고르기', 쪽번호: 방.쪽번호 });
  if (await 탭옮기기(챗주소뿌리 + '/')) 알림('새 대화를 엽니다. 첫 말을 보내면 이 방에 붙습니다.');
}

// 폴더의 ＋ — 그 폴더에서 새 대화를 시작한다.
async function 새대화열기(폴더쪽번호) {
  await 방짓({ 짓: '만들기', 폴더: 폴더쪽번호 });
  if (await 탭옮기기(챗주소뿌리 + '/')) 알림('새 대화를 엽니다. 첫 말을 보내면 이 폴더에서 일합니다.');
}

async function 일꾼짓(짓, 일꾼방) {
  const 답 = await 서버에게({ 종류: '일꾼', 몸통: { 짓, 일꾼방 } });
  const 말 = { 그만: '멈춤', 다시: '다시 부름', 합치기: '합침' }[짓] || 짓;
  if (답 && 답.됨 && 짓 === '합치기' && 답.합침 === false) {
    알림('⚠ 합치는 중 충돌이 나서 되돌렸습니다: ' + ((답.충돌 || []).join(', ') || 답.안내 || ''));
  } else {
    알림(답 && 답.됨 ? '🔧 일꾼 ' + 말 : '⚠ ' + ((답 && 답.탈) || '실패했습니다'));
  }
  await 방새로고침();
}

async function 방짓(몸통) {
  const 답 = await 서버에게({ 종류: '방짓', 몸통 });
  if (!답 || !답.됨) { 알림('⚠ ' + ((답 && 답.탈) || '실패했습니다')); return; }
  await 방새로고침();
  await 계획새로고침();
  if (몸통.짓 === '고르기' || 몸통.짓 === '만들기') {
    본문그리기();
  }
  if (몸통.짓 === '만들기') 알림('새 일할 곳을 만들었습니다. ChatGPT에서 일을 시키세요.');
}

async function 폴더짓(몸통) {
  const 답 = await 서버에게({ 종류: '폴더짓', 몸통 });
  if (!답 || !답.됨) { 알림('⚠ ' + ((답 && 답.탈) || '실패했습니다')); return; }
  await 방새로고침();
}

// ChatGPT 프로젝트 묶음의 일할 폴더를 고른다. 그 프로젝트의 방 모두가 이 폴더를 쓴다.
async function 묶음폴더고르기(묶음) {
  if (!(await 서버살았나())) return;
  알림('폴더 선택창을 띄웠습니다. 이 프로젝트가 쓸 폴더를 고르세요…');
  const 답 = await 서버에게({ 종류: '폴더고르기', 묶음 });
  if (답 && 답.됨) {
    await 방새로고침();
    알림('프로젝트 폴더를 정했습니다: ' + (답.밭 || ''));
    return;
  }
  if (답 && 답.서버꺼짐) { 서버꺼짐알리기(답.탈); return; }
  if (답 && /폴더 선택창을 못 띄웠습니다/.test(답.탈 || '') && typeof window.prompt === 'function') {
    const 밭 = window.prompt('폴더 창을 열지 못했습니다. 이 프로젝트 폴더의 전체 경로를 적어 주세요.');
    if (밭 && 밭.trim()) {
      await 폴더짓({ 짓: '밭정하기', 쪽번호: 묶음, 밭: 밭.trim() });
      return;
    }
  }
  알림((답 && 답.탈) || '고르지 않았습니다');
}

async function 폴더더하기() {
  // 창을 띄우는 것은 서버다(브라우저는 폴더 창을 못 띄운다).
  // 그래서 서버가 꺼져 있으면 아무 일도 안 일어난다 — 그 말을 먼저 한다.
  if (!(await 서버살았나())) return;

  알림('폴더 선택창을 띄웠습니다. 화면에서 고르세요…');
  const 답 = await 서버에게({ 종류: '폴더고르기' });
  if (!답 || !답.됨) {
    if (답 && 답.서버꺼짐) { 서버꺼짐알리기(답.탈); return; }
    if (답 && /폴더 선택창을 못 띄웠습니다/.test(답.탈 || '') && typeof window.prompt === 'function') {
      const 밭 = window.prompt('폴더 창을 열지 못했습니다. 프로젝트 폴더의 전체 경로를 적어 주세요.');
      if (밭 && 밭.trim()) {
        const 직접 = await 서버에게({ 종류: '폴더짓', 몸통: { 짓: '더하기', 밭: 밭.trim() } });
        if (직접 && 직접.됨) {
          await 방새로고침();
          if (직접.쪽번호) await 일할폴더고르기(직접.쪽번호);
          return;
        }
        알림('⚠ ' + ((직접 && 직접.탈) || '폴더를 등록하지 못했습니다'));
        return;
      }
    }
    알림((답 && 답.탈) || '고르지 않았습니다');
    return;
  }
  await 방새로고침();
  // 새로 고른 폴더를 바로 이 대화의 일할 곳으로 삼는다.
  // 고르자마자 쓸 수 있어야지, 목록만 늘려 두면 한 번 더 눌러야 한다.
  if (답.쪽번호) await 일할폴더고르기(답.쪽번호);
  else 알림('폴더 더함: ' + 답.이름);
}

// ── 물음(쓰기 허락 / 받아오기) ─────────────────────────────────

function 물음그리기() {
  const 물음칸 = $('물음칸');
  물음칸.textContent = '';

  for (const 요청 of (화면.대기받아오기 || [])) {
    if (요청.갈래 === '승인') {
      // 권한 모드가 묻는 일 — 무엇을 하려는지 그대로 보여 주고, 이번만 · 항상 · 거부 를 고르게 한다
      const 틀 = document.createElement('div');
      틀.className = '물음 승인' + (요청.위험 ? ' 위험' : '');
      틀.appendChild(글줄((요청.위험 ? '⚠ ' : '') + (요청.제목 || '이 일을 해도 될까요?'), true));
      for (const 줄 of (요청.줄들 || [])) 틀.appendChild(글줄(줄));
      const 줄 = document.createElement('div');
      줄.className = '줄';
      const 단추들 = [['이번만 허용', true, false, '작은']];
      if (요청.분류 && !요청.위험) 단추들.push(['이 방에서 항상 허용', true, true, '작은']);
      단추들.push(['거부', false, false, '작은 거부']);
      for (const [글, 허용, 항상, 클래스] of 단추들) {
        const b = document.createElement('button');
        b.className = 클래스;
        b.textContent = 글;
        b.onclick = () => 받아오기누름(요청.열쇠, 허용, 항상);
        줄.appendChild(b);
      }
      틀.appendChild(줄);
      물음칸.appendChild(틀);
      continue;
    }
    if (요청.갈래 === '눈' || 요청.갈래 === '손') {
      // 화면 보기 · 키보드 마우스 — 창 하나 + 정해진 시간만 허락한다
      const 틀 = document.createElement('div');
      틀.className = '물음 ' + 요청.갈래;
      틀.appendChild(글줄(요청.갈래 === '눈' ? '👁 화면을 보려 합니다' : '🖱 키보드와 마우스를 움직이려 합니다', true));
      틀.appendChild(글줄('어디   ' + 요청.무엇));
      틀.appendChild(글줄('시간   ' + 요청.분 + '분 동안'));
      틀.appendChild(글줄('왜     ' + 요청.왜));
      const 경고 = document.createElement('div');
      경고.className = '경고';
      경고.textContent = 요청.갈래 === '눈'
        ? '찍은 그림은 ChatGPT에 올라갑니다. 다른 창이나 개인 정보가 겹쳐 보이지 않는지 확인하세요.' + (요청.창 === '*' ? ' 화면 전체라 열린 모든 창이 찍힙니다.' : '')
        : '허용하면 그동안 이 창에 키·마우스 입력이 갑니다. 위의 [그만] 으로 언제든 거둘 수 있습니다.' + (요청.창 === '*' ? ' 화면 전체라 어느 창에든 입력이 갈 수 있습니다.' : '');
      틀.appendChild(경고);
      틀.appendChild(단추줄(
        () => 받아오기누름(요청.열쇠, true),
        () => 받아오기누름(요청.열쇠, false)
      ));
      물음칸.appendChild(틀);
      continue;
    }
    const 틀 = document.createElement('div');
    틀.className = '물음 받기';
    틀.appendChild(글줄('⬇ 인터넷에서 받아 설치하려 합니다', true));
    틀.appendChild(글줄('무엇   ' + 요청.무엇));
    틀.appendChild(글줄('어디서 ' + 요청.어디서설명));
    틀.appendChild(글줄('어디에 ' + 요청.어디에));
    틀.appendChild(글줄('왜     ' + 요청.왜));
    const 코드 = document.createElement('code');
    코드.textContent = 요청.돌릴것;
    틀.appendChild(코드);
    틀.appendChild(단추줄(
      () => 받아오기누름(요청.열쇠, true),
      () => 받아오기누름(요청.열쇠, false)
    ));
    물음칸.appendChild(틀);
  }

  for (const 요청 of (화면.대기허락 || [])) {
    const 틀 = document.createElement('div');
    틀.className = '물음 쓰기';
    틀.appendChild(글줄('⚠ 이 폴더를 고쳐도 될까요?', true));
    틀.appendChild(글줄(요청.밭));
    틀.appendChild(단추줄(
      () => 허락누름(요청.밭, true),
      () => 허락누름(요청.밭, false)
    ));
    물음칸.appendChild(틀);
  }

  // 모르는 웹사이트(또는 낯선 확장)가 에이전트에 들어오려 한다 — 허용해야만 들어온다
  for (const 사이트 of ((화면.사이트 && 화면.사이트.대기) || [])) {
    const 틀 = document.createElement('div');
    틀.className = '물음 사이트';
    틀.appendChild(글줄(사이트.종류 === '확장' ? '🧩 낯선 확장이 에이전트를 쓰려 합니다' : '🌐 웹사이트가 에이전트를 쓰려 합니다', true));
    const 주소 = document.createElement('span');
    주소.className = '주소';
    주소.textContent = 사이트.출처;
    틀.appendChild(주소);
    틀.appendChild(글줄('시도 ' + 사이트.횟수 + '번 · ' + (사이트.몇초전 < 5 ? '방금' : 초글(사이트.몇초전) + ' 전')));
    const 경고 = document.createElement('div');
    경고.className = '경고';
    경고.textContent = '허용하면 이 곳이 일할 폴더의 파일을 읽을 수 있습니다. [전부 허용] 은 파일 고치기도 허락합니다. 단, 사용자 승인이 필요한 일은'
      + '웹사이트에서 할 수 없습니다. 내가 연 곳이 아니면 거부하세요.';
    틀.appendChild(경고);
    const 줄 = document.createElement('div');
    줄.className = '줄';
    const 단추 = (글, 짓, 등급, 갈래) => {
      const b = document.createElement('button');
      b.className = '작은' + (갈래 ? ' ' + 갈래 : '');
      b.textContent = 글;
      b.onclick = () => 사이트짓(짓, 사이트.출처, 등급);
      return b;
    };
    줄.append(단추('읽기만 허용', '허용', '보기'), 단추('전부 허용', '허용', '전부'), 단추('거부', '거부', '', '거부'));
    틀.appendChild(줄);
    물음칸.appendChild(틀);
  }
}

// ── 웹사이트 허용 (서버가 승인을 기다리는 곳 · 허용한 곳 · 거부한 곳) ──────────────
async function 사이트새로고침() {
  let 답 = null;
  try {
    답 = await chrome.runtime.sendMessage({ 종류: '사이트', 몸통: { 짓: '목록' } });
  } catch (e) { return; }                 // 폴링은 조용히 한다
  if (!답 || !답.됨) return;
  const 앞 = JSON.stringify(화면.사이트 || {});
  화면.사이트 = 답;
  if (JSON.stringify(답) === 앞) return;
  물음그리기();
  if ($('설정창').style.display === 'flex') 설정그리기();
  if ((답.대기 || []).length && !(JSON.parse(앞).대기 || []).length) {
    알림('🌐 웹사이트가 에이전트를 쓰려 합니다 — 위 카드에서 허용할지 정하세요');
    배지달기('?', '#d6a64b');
  }
}

async function 사이트짓(짓, 출처, 등급) {
  const 답 = await 서버에게({ 종류: '사이트', 몸통: { 짓, 출처, 등급 } });
  if (답 && 답.됨) {
    화면.사이트 = 답;
    물음그리기();
    if ($('설정창').style.display === 'flex') 설정그리기();
    알림(짓 === '허용' ? (출처 + ' 을(를) ' + (등급 === '전부' ? '전부' : '읽기만') + ' 허용했습니다')
      : 짓 === '거부' ? (출처 + ' 을(를) 거부했습니다') : (출처 + ' 을(를) 목록에서 뺐습니다'));
  } else if (답) {
    알림('⚠ ' + (답.탈 || '하지 못했습니다'));
  }
}

function 설정그리기() {
  const 몸 = $('설정몸');
  if (!몸) return;
  몸.textContent = '';
  const 사 = 화면.사이트 || { 대기: [], 허용: [], 거부: [], 확장: [] };
  const 머리 = (글) => 몸.appendChild(칸만들기('div', '설정머리', 글));
  const 줄 = (출처, 단추들) => {
    const 틀 = 칸만들기('div', '설정줄');
    틀.appendChild(칸만들기('span', '출처', 출처));
    for (const 단추 of 단추들) 틀.appendChild(단추);
    몸.appendChild(틀);
  };
  const 작은 = (글, 동작, 제목) => {
    const b = 칸만들기('button', '작은', 글);
    if (제목) b.title = 제목;
    b.onclick = 동작;
    return b;
  };

  머리('허용한 웹사이트 (' + (사.허용 || []).length + ')');
  if (!(사.허용 || []).length) 몸.appendChild(칸만들기('div', '설정안내', '아직 없습니다. 모르는 웹사이트가 들어오려 하면 위쪽에 허용 카드가 뜹니다.'));
  for (const 항 of 사.허용 || []) {
    const 바꿀등급 = 항.등급 === '전부' ? '보기' : '전부';
    줄(항.출처, [
      작은(항.등급 === '전부' ? '전부' : '읽기만', () => 사이트짓('허용', 항.출처, 바꿀등급),
        '눌러서 ' + (바꿀등급 === '전부' ? '전부' : '읽기만') + ' 으로 바꿉니다'),
      작은('빼기', () => 사이트짓('지움', 항.출처), '목록에서 뺍니다(다시 오면 처음처럼 물어봅니다)'),
    ]);
  }
  if ((사.거부 || []).length) {
    머리('거부한 곳 (' + 사.거부.length + ')');
    for (const 출처 of 사.거부) 줄(출처, [작은('풀기', () => 사이트짓('지움', 출처), '거부를 풉니다(다시 오면 처음처럼 물어봅니다)')]);
  }
  머리('믿는 확장 (' + (사.확장 || []).length + ')');
  for (const 출처 of 사.확장 || []) 줄(출처, []);
  몸.appendChild(칸만들기('div', '설정안내', '확장은 처음 연결된 것을 믿습니다. 웹사이트는 도구 호출과 서버 확인만 할 수 있고, 방·폴더·권한 모드·허락은 바꿀 수 없습니다.'));
}

function 설정열기() {
  void 사이트새로고침().then(설정그리기);
  설정그리기();
  $('설정창').style.display = 'flex';
}

function 글줄(글, 굵게) {
  const d = document.createElement('div');
  d.textContent = 글;
  if (굵게) d.style.fontWeight = '700';
  d.style.wordBreak = 'break-all';
  return d;
}

function 단추줄(허용동작, 거부동작) {
  const 줄 = document.createElement('div');
  줄.className = '줄';
  const 허용 = document.createElement('button');
  허용.className = '작은';
  허용.textContent = '허용';
  허용.onclick = 허용동작;
  const 거부 = document.createElement('button');
  거부.className = '작은';
  거부.textContent = '거부';
  거부.onclick = 거부동작;
  줄.append(허용, 거부);
  return 줄;
}

async function 허락누름(밭, 허용) {
  await 서버에게({ 종류: '허락처리', 밭, 허용 });
  알림(허용 ? '허용했습니다: ' + 밭 : '거부했습니다: ' + 밭);
  await 방새로고침();
}

// 권한 모드가 물었던 일의 허용 · 거부. 서버가 허용된 호출을 돌려 결과를 주면, 멈춰 있던 GPT 쪽 묶음을 잇는다.
async function 승인누름(열쇠, 허용, 항상) {
  if (설치처리중.has(열쇠)) return false;
  설치처리중.add(열쇠);
  화면.대기받아오기 = (화면.대기받아오기 || []).filter((요청) => 요청.열쇠 !== 열쇠);
  물음그리기();
  알림(허용 ? '허락했습니다. 실행하는 중…' : '허락하지 않기로 했습니다');
  try {
    const 답 = await 서버에게({ 종류: '받아오기처리', 열쇠, 허용, 항상: !!항상 });
    if (답 && Array.isArray(답.기다림)) 화면.대기받아오기 = 답.기다림;
    마지막물음열쇠글 = (화면.대기받아오기 || []).map((요청) => 요청.열쇠).join('|');
    물음그리기();
    if (!답 || !답.됨) {
      알림('⚠ ' + ((답 && 답.탈) || '승인 결과를 받지 못했습니다.'));
      return false;
    }
    const 전달 = await 탭에게('승인결과', { 열쇠, 허용: !!답.허용, 나물: 답.나물, 결과: 답.결과 });
    알림(!전달 || !전달.됨
      ? '⚠ 결과를 GPT에 전달하지 못했습니다. ChatGPT 화면을 새로고침해 주세요.'
      : (답.허용 ? '실행했습니다 — 결과를 GPT에게 보냈습니다' : '거부했다고 GPT에게 알렸습니다'));
    return true;
  } finally {
    설치처리중.delete(열쇠);
  }
}

async function 받아오기누름(열쇠, 허용, 항상) {
  if (String(열쇠).indexOf('승인::') === 0) return 승인누름(열쇠, 허용, 항상);
  if (설치처리중.has(열쇠)) return false;
  설치처리중.add(열쇠);
  // 서버 응답을 기다리는 동안에도 카드를 숨겨 두 번 누르지 못하게 한다.
  화면.대기받아오기 = (화면.대기받아오기 || []).filter((요청) => 요청.열쇠 !== 열쇠);
  물음그리기();
  const 눈손 = 열쇠.indexOf('허가::') === 0;
  알림(눈손 ? (허용 ? '허락하는 중…' : '허락하지 않기로 했습니다') : (허용 ? '받아오는 중… (오래 걸릴 수 있습니다)' : '받지 않기로 했습니다'));
  try {
    const 답 = await 서버에게({ 종류: '받아오기처리', 열쇠, 허용 });
    if (답 && Array.isArray(답.기다림)) 화면.대기받아오기 = 답.기다림;
    if (답 && Array.isArray(답.허가중)) 화면.허가중 = 답.허가중;
    마지막물음열쇠글 = (화면.대기받아오기 || []).map((요청) => 요청.열쇠).join('|');
    물음그리기();
    허가중그리기();
    if (눈손 && 답) {
      // 눈·손은 허락이든 거절이든 GPT가 기다리고 있다 — 결과를 알려야 다음으로 간다(거절도).
      const 전달 = await 탭에게('설치결과', 답);
      알림(!전달 || !전달.됨
        ? '⚠ 결과를 GPT에 전달하지 못했습니다. ChatGPT 화면을 새로고침해 주세요.'
        : (허용 ? '허락했습니다: ' + (답.무엇 || '') + ' — GPT에게 알렸습니다' : '허락하지 않았습니다 — GPT에게 알렸습니다'));
      return !!답;
    }
    if (허용 && 답) {
      // 설치가 끝났는지 실패했는지를 GPT에게 자동으로 알려야 다음 단계가 이어진다.
      const 전달 = await 탭에게('설치결과', 답);
      if (!전달 || !전달.됨) {
        알림('⚠ 설치 결과를 GPT에 전달하지 못했습니다. ChatGPT 화면을 새로고침해 주세요.');
      } else {
        알림(답.끝번호 === 0
          ? '받았습니다. 설치 결과를 GPT에 전달했습니다: ' + (답.무엇 || '')
          : '⚠ 설치는 끝났지만 실패 결과를 GPT에 전달했습니다: ' + String(답.나온것 || '').slice(0, 90));
      }
    } else if (!답) {
      알림('⚠ 설치 요청 처리 결과를 받지 못했습니다.');
    }
    return !!답;
  } finally {
    설치처리중.delete(열쇠);
  }
}

// ── 메뉴 ───────────────────────────────────────────────────────

function 메뉴열기(기준, 항목들) {
  const 메뉴 = $('메뉴');
  메뉴.textContent = '';
  for (const 항목 of 항목들) {
    if (항목 === null) {
      const 선 = document.createElement('div');
      선.className = '선';
      메뉴.appendChild(선);
      continue;
    }
    const 줄 = document.createElement('div');
    줄.className = '줄';
    줄.textContent = (항목.켬 !== undefined ? (항목.켬 ? '☑ ' : '☐ ') : '') + 항목.글;
    if (항목.쪽) {
      const 쪽 = document.createElement('span');
      쪽.className = '쪽';
      쪽.textContent = 항목.쪽;
      줄.appendChild(쪽);
    }
    줄.onclick = (e) => { e.stopPropagation(); 항목.동작(); 메뉴닫기(); };
    메뉴.appendChild(줄);
  }
  메뉴.style.display = 'block';
  const 네모 = 기준.getBoundingClientRect();
  const 폭 = 메뉴.offsetWidth;
  const 높이 = 메뉴.offsetHeight;
  메뉴.style.left = Math.max(6, Math.min(네모.left, window.innerWidth - 폭 - 6)) + 'px';
  const 아래 = 네모.bottom + 4;
  메뉴.style.top = (아래 + 높이 > window.innerHeight - 6
    ? Math.max(6, 네모.top - 높이 - 4)
    : 아래) + 'px';
  setTimeout(() => document.addEventListener('click', 메뉴닫기, { once: true }), 0);
}

function 메뉴닫기() { $('메뉴').style.display = 'none'; }

// ── 시작 ───────────────────────────────────────────────────────

// ▣ : 오른쪽 '일할 곳' 칸을 접었다 폈다. 늘 보이는 것이 기본이다.
function 위칸보이기(펼까) {   // 오른쪽 '일할 곳' 칸을 접었다 폈다
  const 위칸 = $('위칸'), 가름대 = $('가름대');
  const 펼침 = 펼까 === undefined ? 위칸.classList.contains('접힘') : !!펼까;
  위칸.classList.toggle('접힘', !펼침);
  가름대.classList.toggle('접힘', !펼침);
  $('위칸토글').classList.toggle('켬', 펼침);
  try { localStorage.setItem('위칸펼침', 펼침 ? '1' : '0'); } catch (e) { /* 넘어간다 */ }
  if (펼침) 파일나무그리기();
}

// 오른쪽 칸을 아무리 넓혀도 대화 본문은 최소 260px(창이 그보다 좁으면 가능한 만큼)
// 남긴다. 예전 저장값도 여기로 통과시켜 대화가 통째로 밀려나지 않게 한다.
function 일할곳너비맞추기(너비) {
  const 최소일할곳너비 = 150;
  const 최소본문너비 = 260;
  const 최대일할곳너비 = Math.max(최소일할곳너비, window.innerWidth - 최소본문너비);
  return Math.max(최소일할곳너비,
    Math.min(parseInt(너비, 10) || 최소일할곳너비, 최대일할곳너비));
}

// 가름대를 끌어 일할 곳 너비를 바꾼다. 바꾼 너비는 기억한다.
(function 가름대달기() {
  const 가름대 = $('가름대');
  let 끄는중 = false;
  가름대.onmousedown = (e) => { 끄는중 = true; e.preventDefault(); };
  document.addEventListener('mousemove', (e) => {
    if (!끄는중) return;
    // 오른쪽에 붙어 있으므로, 창 오른쪽 끝에서 마우스까지가 너비다. 비율로 기억해 창 크기가 바뀌어도 같은 모양을 지킨다.
    옆너비비 = 일할곳너비맞추기(window.innerWidth - e.clientX) / window.innerWidth;
    옆너비적용();
  });
  document.addEventListener('mouseup', () => {
    if (!끄는중) return;
    끄는중 = false;
    배치저장();
  });
  // 판 창 자체를 넓히거나 좁혀도 대화와 옆 칸의 비율은 그대로
  if (typeof window.addEventListener === 'function') window.addEventListener('resize', 옆너비적용);
})();

$('위칸토글').onclick = () => 위칸보이기();

// '일할 곳' 의 ＋ 는 새 폴더를 더하는 단추다. 바로 윈도우 창을 연다.
// (예전에는 메뉴를 한 번 더 띄웠다. 고를 것이 '폴더 열기…' 하나뿐일 때가 많아
//  누르는 수만 늘었다.)
$('폴더고르기단추').onclick = (e) => { e.stopPropagation(); 폴더더하기(); };

$('제목').onclick = () => 위칸보이기(true);

let 멈춤처리중 = false;
$('멈춤단추').onclick = async () => {
  if (멈춤처리중) return;
  멈춤처리중 = true;
  const 단추 = $('멈춤단추');
  if (단추) 단추.disabled = true;
  try {
    const 답 = await Promise.race([
      탭에게('멈춤토글'),
      new Promise((풀기) => setTimeout(() => 풀기(null), 5000)),
    ]);
    if (답) { 화면.켜짐 = 답.켜짐; 상태그리기(); }
    else 알림('⚠ 다시 시작 요청에 응답이 없습니다. ChatGPT 화면을 새로고침해 보세요.');
  } finally {
    멈춤처리중 = false;
    if (단추) 단추.disabled = false;
  }
};

// ── 추론 수준 (ChatGPT 입력칸의 Instant·Medium·High) ─────────────────
// 칸 이름과 수는 탭이 ChatGPT 메뉴에서 읽어 온 것을 쓴다. 기본은 가장 높은 칸.
const 기본추론단계들 = ['Instant', 'Medium', 'High'];
// 화면에는 우리말로 보인다(ChatGPT에 보내는 값은 영어 그대로).
const 추론우리말 = { Instant: '빠름', Medium: '보통', High: '깊게' };
function 추론이름(영어) { return 추론우리말[영어] || 영어; }

function 추론단계들() {
  const 받은것 = (화면.추론단계들 || []).filter(Boolean);
  return (화면.추론단계들 && 화면.추론단계들.length && 받은것.length === 화면.추론단계들.length)
    ? 화면.추론단계들 : 기본추론단계들;
}

function 추론목표번호() {
  const 단계 = 추론단계들();
  const 목표 = 화면.추론목표;
  return typeof 목표 === 'number' ? Math.min(목표, 단계.length - 1) : 단계.length - 1;
}

function 추론글그리기() {
  const 단계 = 추론단계들();
  $('추론글').textContent = '추론 ' + 추론이름(화면.추론 || 단계[추론목표번호()]);
}

function 추론창열기() {
  const 메뉴 = $('메뉴');
  const 단계 = 추론단계들();
  메뉴.textContent = '';
  const 틀 = document.createElement('div');
  틀.className = '추론틀';
  틀.onclick = (e) => e.stopPropagation();

  const 머리 = document.createElement('div');
  머리.className = '추론머리';
  const 흐림 = document.createElement('span');
  흐림.className = '흐림';
  흐림.textContent = '추론';
  const 이름 = document.createElement('span');
  이름.textContent = 추론이름(단계[추론목표번호()]);
  머리.append(흐림, 이름);

  const 끝 = document.createElement('div');
  끝.className = '추론끝';
  const 왼 = document.createElement('span');
  왼.textContent = '더 빠르게';
  const 오 = document.createElement('span');
  오.textContent = '더 스마트하게';
  끝.append(왼, 오);

  const 막대 = document.createElement('input');
  막대.type = 'range';
  막대.className = '추론막대';
  막대.min = '0';
  막대.max = String(단계.length - 1);
  막대.step = '1';
  막대.value = String(추론목표번호());
  막대.oninput = () => { 이름.textContent = 추론이름(단계[Number(막대.value)]); };
  막대.onchange = () => 추론바꾸기(Number(막대.value));

  const 칸이름 = document.createElement('div');
  칸이름.className = '추론칸이름';
  for (const 글 of 단계) {
    const 칸 = document.createElement('span');
    칸.textContent = 추론이름(글);
    칸이름.appendChild(칸);
  }

  틀.append(머리, 끝, 막대, 칸이름);
  메뉴.appendChild(틀);
  메뉴.style.display = 'block';
  const 네모 = $('추론알약').getBoundingClientRect();
  메뉴.style.left = Math.max(6, Math.min(네모.left, window.innerWidth - 메뉴.offsetWidth - 6)) + 'px';
  메뉴.style.top = Math.max(6, 네모.top - 메뉴.offsetHeight - 4) + 'px';
}

async function 추론바꾸기(번) {
  화면.추론목표 = 번;
  try { localStorage.setItem('추론목표', String(번)); } catch (e) { /* 넘어간다 */ }
  알림('추론 수준을 ' + 추론단계들()[번] + ' 으로 바꾸는 중…');
  const 답 = await 탭에게('추론바꾸기', 번);
  if (답) {
    if (답.추론) 화면.추론 = 답.추론;
    if (답.추론단계들 && 답.추론단계들.length) 화면.추론단계들 = 답.추론단계들;
    알림(답.됨 ? '추론 수준: ' + (답.추론 || 추론단계들()[번]) : '⚠ ChatGPT 추론 수준을 못 바꿨습니다(쓰는 중이면 끝난 뒤 다시).');
  }
  추론글그리기();
}

$('추론알약').onclick = (e) => {
  e.stopPropagation();
  if ($('메뉴').style.display === 'block') { 메뉴닫기(); return; }
  추론창열기();
};

$('모드알약').onclick = (e) => {
  e.stopPropagation();
  메뉴열기($('모드알약'), 모드목록.map((모드) => ({
    글: 모드,
    쪽: 모드설명[모드],
    켬: 지금모드() === 모드,
    동작: async () => {
      const 답 = await 서버에게({ 종류: '등급바꾸기', 모드 });
      if (답 && 답.됨) { 화면.지금모드 = 답.모드; 화면.지금등급 = 답.등급; 상태그리기(); 알림('권한 모드를 ' + 모드 + '(으)로 바꿨습니다'); }
    },
  })));
};

// ＋ 는 '이 대화를 어느 폴더에서 할지' 를 고르는 목록이다.
// 최근에 쓴 폴더가 먼저 나오고, 맨 아래로 새 폴더를 열 수 있다.
$('더하기').onclick = (e) => {
  e.stopPropagation();
  const 폴더들 = (화면.나무 && 화면.나무.폴더들) || [];

  // 고를 것이 없으면 메뉴를 띄우지 않고 바로 윈도우 창을 연다.
  // 한 줄짜리 메뉴는 누르는 수만 하나 더 늘릴 뿐이다.
  if (!폴더들.length) { 폴더더하기(); return; }

  const 지금폴더 = 폴더들.find((f) => (f.방들 || []).some((r) => r.지금));

  const 항목들 = 폴더들.map((폴더) => ({
    글: 폴더.이름,
    쪽: '',
    켬: !!(지금폴더 && 지금폴더.쪽번호 === 폴더.쪽번호),
    동작: () => 일할폴더고르기(폴더.쪽번호),
  }));
  if (항목들.length) 항목들.push(null);
  항목들.push({ 글: '폴더 열기…', 쪽: '윈도우 창에서 고르기', 동작: 폴더더하기 });
  메뉴열기($('더하기'), 항목들);
};

// 고른 폴더를 이 대화(창)의 일할 곳으로 삼는다.
// 대화방을 따로 만들 필요가 없다 — 이 창에 붙은 방을 찾아 그 폴더로 옮긴다.
// 아직 방이 없으면 탭에게 물어 만들게 한 뒤 옮긴다.
async function 일할폴더고르기(폴더쪽번호) {
  let 방 = 화면.지금방;
  if (!방) {
    const 답 = await 탭에게('방잡기');     // 이 대화에 방을 붙여 달라
    방 = (답 && 답.방) || null;
    if (방) 화면.지금방 = 방;
  }

  if (방) {
    await 방짓({ 짓: '폴더이동', 쪽번호: 방, 폴더: 폴더쪽번호 });
  } else {
    await 방짓({ 짓: '만들기', 폴더: 폴더쪽번호 });
  }
  const 폴더 = ((화면.나무 && 화면.나무.폴더들) || [])
    .find((f) => f.쪽번호 === 폴더쪽번호);
  알림('일할 곳: ' + ((폴더 && 폴더.이름) || '바꿈'));
}

// ── 시키는 칸 ─────────────────────────────────────────────────
// ── 실행 현황 (서버가 직접 잰 값) ──────────────────────────────
// GPT가 "40% 진행 중이에요" 라고 말하는 것이 아니다. 서버가 디스크·프로세스를 읽어 잰 값이다.
// GPT는 당근으로 '무엇을 볼지' 만 정하고, 뒤뜰(두릅) 일은 아무것도 안 해도 저절로 한 장 뜬다.

const 현황 = {
  판들: [], 더있음: 0, 요약: {},
  읽는중: false, 바퀴: 0,
  펴짐: new Map(),       // 판 번호 → 사용자가 펴거나 접은 것
  알린것: new Set(),     // 끝남·실패를 이미 알린 일(저장소를 못 쓸 때의 대신)
};
const 방줄들 = {};       // 방 번호 → { 줄, 알, 막대칸 } — 방 목록을 다시 그리지 않고 막대만 바꾸려고

function 초글(초) {
  if (초 === null || 초 === undefined) return '?';
  초 = Math.max(0, Math.floor(초));
  if (초 < 60) return 초 + '초';
  if (초 < 3600) return Math.floor(초 / 60) + '분 ' + (초 % 60) + '초';
  return Math.floor(초 / 3600) + '시간 ' + Math.floor((초 % 3600) / 60) + '분';
}

function 크기글(바이트) {
  const 수 = Number(바이트) || 0;
  if (수 < 1024) return 수 + 'B';
  if (수 < 1048576) return (수 / 1024).toFixed(1) + 'KB';
  if (수 < 1073741824) return (수 / 1048576).toFixed(1) + 'MB';
  return (수 / 1073741824).toFixed(2) + 'GB';
}

function 수글(값) {
  const 수 = Number(값);
  if (!Number.isFinite(수)) return String(값);
  const 절 = Math.abs(수);
  if (절 !== 0 && (절 >= 100000 || 절 < 0.001)) return 수.toExponential(2);
  return String(Math.round(수 * 1000) / 1000);
}

// ▁▂▃▄▅▆▇█ — 값이 변해 가는 모양을 글자 한 줄로
function 그래프글(점들) {
  const 칸 = '▁▂▃▄▅▆▇█';
  const 값 = (점들 || []).filter((v) => Number.isFinite(Number(v))).map(Number);
  if (값.length < 2) return '';
  const 작 = Math.min(...값);
  const 큰 = Math.max(...값);
  if (큰 === 작) return 칸[3].repeat(Math.min(값.length, 30));
  // 좁은 칸에서 두 줄로 꺾이지 않게 14칸 안쪽으로 줄인다
  const 칸수 = 14;
  const 줄 = 값.length > 칸수 ? Array.from({ length: 칸수 }, (_, 번) => 값[Math.min(값.length - 1, Math.round(번 * (값.length - 1) / (칸수 - 1)))]) : 값;
  return 줄.map((v) => 칸[Math.min(7, Math.floor((v - 작) / (큰 - 작) * 8))]).join('');
}

function 추이글(추이) {
  return 추이 === '오름' ? '▲' : 추이 === '내림' ? '▼' : '–';
}

async function 현황새로고침() {
  if (현황.읽는중 || !화면.지금방) return;
  현황.읽는중 = true;
  try {
    // 폴링은 조용히 한다(서버가 꺼졌다는 알림은 서버살았나가 맡는다)
    let 답 = null;
    try {
      답 = await chrome.runtime.sendMessage({ 종류: '현황', 몸통: { 방: 화면.지금방 } });
    } catch (e) { return; }
    if (!답 || !답.됨) return;
    현황.판들 = 답.판들 || [];
    현황.더있음 = 답.더있음 || 0;
    현황.요약 = 답.요약 || {};
    현황알림살피기();
    현황그리기();
    방막대모두맞추기();
  } finally {
    현황.읽는중 = false;
  }
}

// 도는 일이 있으면 2초마다, 없으면 6초마다 본다
function 현황돌기() {
  현황.바퀴 += 1;
  const 돈다 = 현황.판들.some((판) => 판.상태 === '달리는중') || Object.keys(현황.요약).length > 0;
  if (!돈다 && 현황.바퀴 % 3 !== 0) return;
  void 현황새로고침();
}

function 현황방바뀜() {
  현황.판들 = [];
  현황.더있음 = 0;
  현황그리기();
  void 현황새로고침();
}

async function 현황짓(짓, 번호) {
  const 답 = await 서버에게({ 종류: '현황', 몸통: { 방: 화면.지금방, 짓, 번호 } });
  if (답 && 답.됨) {
    현황.판들 = 답.판들 || [];
    현황.더있음 = 답.더있음 || 0;
    현황.요약 = 답.요약 || {};
    현황그리기();
    방막대모두맞추기();
  } else if (답) {
    알림('⚠ ' + (답.탈 || '하지 못했습니다'));
  }
  return 답;
}

function 현황멈춤누름(판, 항목) {
  const 묻는말 = '"' + (항목.이름 || 판.이름) + '" 을(를) 멈춥니다. 하던 학습은 여기서 끊깁니다. 멈출까요?';
  if (typeof confirm === 'function' && !confirm(묻는말)) return;
  void 현황짓('멈춤', 항목.값).then((답) => { if (답 && 답.됨) 알림('멈췄습니다: ' + (항목.이름 || 판.이름)); });
}

// 도는 중이던 일이 끝났거나 실패했거나 끊겼으면 한 번만 알린다
// (판을 닫았다 열어도, 새로고침해도 같은 알림이 또 울리지 않게 저장소에 적어 둔다)
function 알린적있나(열쇠) {
  if (현황.알린것.has(열쇠)) return true;
  try { return localStorage.getItem(열쇠) === '1'; } catch (e) { return false; }
}

function 알림적기(열쇠) {
  현황.알린것.add(열쇠);
  try { localStorage.setItem(열쇠, '1'); } catch (e) { /* 저장소를 못 쓰면 이번 판에서만 */ }
}

function 현황알림살피기() {
  for (const 판 of 현황.판들) {
    for (const 항목 of 판.항목들 || []) {
      if (항목.종류 !== '일' || !항목.있음 || 항목.상태 === '달리는중') continue;
      if (항목.끝난지초 === null || 항목.끝난지초 === undefined || 항목.끝난지초 > 600) continue;
      const 열쇠 = '현황알림:' + 항목.값 + ':' + 항목.상태 + ':' + 항목.끝번호;
      if (알린적있나(열쇠)) continue;
      알림적기(열쇠);
      끝남알리기(항목);
    }
  }
}

function 끝남알리기(항목) {
  const 잘됨 = 항목.상태 === '끝남' && 항목.끝번호 === 0;
  const 이름 = 항목.이름 || 항목.값;
  const 글 = 잘됨 ? '✓ ' + 이름 + ' 끝났습니다 (' + 초글(항목.경과초) + ')'
    : 항목.상태 === '끊김' ? '✗ ' + 이름 + ' 이(가) 중간에 끊겼습니다'
      : '✗ ' + 이름 + ' 이(가) 실패했습니다 (끝번호 ' + 항목.끝번호 + ')';
  알림(글);
  소리내기(잘됨);
  배지달기(잘됨 ? '✓' : '!', 잘됨 ? '#3fa66b' : '#d6584b');
}

function 소리내기(잘됨) {
  try {
    const 소리틀 = window.AudioContext || window.webkitAudioContext;
    if (!소리틀) return;
    const 맥락 = 현황.소리맥락 || (현황.소리맥락 = new 소리틀());
    if (맥락.state === 'suspended' && 맥락.resume) 맥락.resume();
    const 시작 = 맥락.currentTime;
    (잘됨 ? [660, 880] : [440, 330]).forEach((주파수, 번) => {
      const 때 = 시작 + 번 * 0.18;
      const 진동 = 맥락.createOscillator();
      const 크기 = 맥락.createGain();
      진동.frequency.value = 주파수;
      크기.gain.setValueAtTime(0.0001, 때);
      크기.gain.exponentialRampToValueAtTime(0.15, 때 + 0.02);
      크기.gain.exponentialRampToValueAtTime(0.0001, 때 + 0.16);
      진동.connect(크기);
      크기.connect(맥락.destination);
      진동.start(때);
      진동.stop(때 + 0.17);
    });
  } catch (e) { /* 소리가 안 나도 알림 글은 이미 떴다 */ }
}

// 판을 안 보고 있어도 확장 아이콘에 표시가 남는다 (새 권한이 필요 없다)
function 배지달기(글, 색) {
  try {
    chrome.action.setBadgeBackgroundColor({ color: 색 });
    chrome.action.setBadgeText({ text: 글 });
  } catch (e) { /* 넘어간다 */ }
}

function 배지지우기() {
  try { chrome.action.setBadgeText({ text: '' }); } catch (e) { /* 넘어간다 */ }
}
document.addEventListener('click', 배지지우기);

// ── 그리기 ──
function 칸만들기(태그, 갈래, 글) {
  const 요소 = document.createElement(태그);
  if (갈래) 요소.className = 갈래;
  if (글 !== undefined) 요소.textContent = 글;
  return 요소;
}

function 막대만들기(퍼센트) {
  const 틀 = 칸만들기('div', '현황막대' + (퍼센트 === null || 퍼센트 === undefined ? ' 모름' : ''));
  const 속 = document.createElement('i');
  if (퍼센트 !== null && 퍼센트 !== undefined) 속.style.width = Math.max(0, Math.min(100, 퍼센트)) + '%';
  틀.appendChild(속);
  return 틀;
}

// ── 실행 현황의 작은 네모 칸 ──
// 큰 틀(현황판 카드) 안에 작은 네모(이름·값·덧말·그래프) 여럿을 격자로 놓는다. 한 줄 글로 이어 쓰면 읽기 어려웠다.
// 로그의 영어 지표 이름은 쉬운 우리말로 보이고(마우스를 올리면 원래 이름), 모르는 이름은 그대로 둔다.
const 지표우리말 = {
  mean_return: '평균 보상', return: '보상 합계', mean_reward: '평균 보상', reward: '보상', ep_return: '한 판 보상',
  training_success: '학습 성공률', success: '성공률', success_rate: '성공률', win_rate: '승률', accuracy: '정확도',
  acc: '정확도', precision: '정밀도', recall: '찾아낸 비율', f1: '종합 점수', score: '점수',
  loss: '손실', train_loss: '학습 손실', val_loss: '검증 손실', policy_loss: '정책 손실', value_loss: '가치 손실',
  entropy: '다양성', kl: '정책 변화량', epoch: '회차', step: '단계', steps: '단계', update: '갱신 횟수',
  lr: '학습 속도', learning_rate: '학습 속도', fps: '초당 처리량', episode: '판 수', episodes: '판 수',
};
// 어느 쪽으로 가면 좋은지(그래서 ▲▼ 에 '좋아지는 중' 을 붙일 수 있다). 모르는 것은 방향만 말한다.
const 낮을수록좋은말 = ['loss', 'error', 'penalty', 'cost', '손실', '오차', '오류', '패널티'];
const 높을수록좋은말 = ['return', 'reward', 'success', 'accuracy', 'acc', 'win', 'score', 'precision', 'recall', 'f1',
  '보상', '성공', '정확', '승률', '점수'];

function 지표이름(영어) {
  const 글 = String(영어 || '').trim();
  return 지표우리말[글.toLowerCase()] || 글;
}

function 좋은방향(이름) {
  const 글 = String(이름 || '').toLowerCase();
  if (낮을수록좋은말.some((말) => 글.indexOf(말) !== -1)) return '낮음';
  if (높을수록좋은말.some((말) => 글.indexOf(말) !== -1)) return '높음';
  return '';
}

// 오름·내림이 좋은 일인지 나쁜 일인지 → [덧말, 갈래]
function 추이뜻(이름, 추이) {
  if (추이 !== '오름' && 추이 !== '내림') return ['그대로', ''];
  const 좋은 = 좋은방향(이름);
  if (!좋은) return [추이 === '오름' ? '올라가는 중' : '내려가는 중', ''];
  const 좋아짐 = (좋은 === '높음') === (추이 === '오름');
  return [좋아짐 ? '좋아지는 중' : '나빠지는 중', 좋아짐 ? '좋아짐' : '나빠짐'];
}

function 네모만들기(이름, 값, 덧말, 갈래, 그래프, 제목) {
  const 네모 = 칸만들기('div', '네모');
  if (제목) 네모.title = 제목;
  // 값이 길면(예: '4.00GB / 12.00GB', '약 3분 20초') 좁은 칸에서 꺾이므로 한 줄을 다 쓴다
  if (String(값).length > 6) 네모.style.gridColumn = '1 / -1';
  네모.appendChild(칸만들기('span', '네모이름', 이름));
  네모.appendChild(칸만들기('span', '네모값' + (갈래 ? ' ' + 갈래 : ''), 값));
  if (덧말) 네모.appendChild(칸만들기('span', '네모덧', 덧말));
  if (그래프) 네모.appendChild(칸만들기('span', '그래프', 그래프));
  return 네모;
}

function 숫자네모(숫) {
  const 한글 = 지표이름(숫.이름);
  const [뜻, 갈래] = 추이뜻(숫.이름, 숫.추이);
  return 네모만들기(한글, 수글(숫.최신) + ' ' + 추이글(숫.추이), 뜻, 갈래, 그래프글(숫.점들),
    한글 !== 숫.이름 ? '원래 이름: ' + 숫.이름 : '');
}

function 진행네모들(진행, 남은초, 남은출처) {
  const 네모들 = [];
  if (!진행) return 네모들;
  if (진행.퍼센트 !== null && 진행.퍼센트 !== undefined) 네모들.push(네모만들기('진행률', 진행.퍼센트 + '%'));
  if (진행.지금 !== null && 진행.지금 !== undefined && 진행.전체) 네모들.push(네모만들기('단계', 진행.지금 + '/' + 진행.전체));
  // 프로그램이 직접 찍은 남은 시간은 그대로, 내가 어림한 것은 '(추정)' 이라고 밝힌다
  if (남은초 !== null && 남은초 !== undefined) {
    네모들.push(네모만들기('남은 시간', '약 ' + 초글(남은초), 남은출처 === '프로그램' ? '' : '(추정)'));
  }
  return 네모들;
}

function 진행글(진행, 남은초, 남은출처) {
  if (!진행) return '';
  const 조각 = [];
  if (진행.퍼센트 !== null && 진행.퍼센트 !== undefined) 조각.push(진행.퍼센트 + '%');
  if (진행.지금 !== null && 진행.지금 !== undefined && 진행.전체) 조각.push(진행.지금 + '/' + 진행.전체);
  // 프로그램이 직접 찍은 남은 시간은 그대로, 내가 어림한 것은 '(추정)' 이라고 밝힌다
  if (남은초 !== null && 남은초 !== undefined) {
    조각.push('남은 약 ' + 초글(남은초) + (남은출처 === '프로그램' ? '' : ' (추정)'));
  }
  return 조각.join(' · ');
}

function 일상태글(항목) {
  if (!항목.있음) return 항목.탈 || '읽지 못함';
  const 조각 = [];
  if (항목.상태 === '달리는중') 조각.push('달리는 중');
  else if (항목.상태 === '끝남') 조각.push(항목.끝번호 === 0 ? '끝남 ✓' : (항목.끝번호 === -9 ? '멈춤' : '실패 (끝번호 ' + 항목.끝번호 + ')'));
  else 조각.push('끊김 (프로세스가 사라짐)');
  조각.push((항목.상태 === '달리는중' ? '경과 ' : '걸린 시간 ') + 초글(항목.경과초));
  return 조각.join(' · ');
}

// 항목 하나를 줄들로. 접힌 카드는 핵심 한두 줄만, 편 카드는 전부.
function 항목줄들(항목, 펴짐) {
  const 줄들 = [];
  const 이름 = 항목.이름 || 항목.값;
  const 없음 = (글) => 줄들.push(칸만들기('div', '줄항 없음', 이름 + ': ' + 글));
  if (!항목.있음) { 없음(항목.탈 || '읽지 못함'); return 줄들; }

  if (항목.종류 === '일') {
    // 끝난 일은 접어 두면 한 줄 상태만 — 100% 막대와 숫자를 계속 보여 줘도 쓸모가 없고
    // 판이 길어져 일할 곳 목록을 밀어낸다. 실패·끊김은 마지막 줄(까닭)만 보인다.
    if (!펴짐 && 항목.상태 !== '달리는중') {
      const 잘끝남 = 항목.상태 === '끝남' && 항목.끝번호 === 0;
      if (!잘끝남 && (항목.끝줄들 || []).length) {
        줄들.push(칸만들기('div', '옛줄', 항목.끝줄들[항목.끝줄들.length - 1]));
      }
      return 줄들;
    }
    if (항목.진행) {
      줄들.push(막대만들기(항목.진행.퍼센트));
      for (const 네모 of 진행네모들(항목.진행, 항목.남은초, 항목.남은출처)) 줄들.push(네모);
    } else if (항목.상태 === '달리는중') {
      줄들.push(막대만들기(null));
      줄들.push(칸만들기('div', '줄항 없음', '진행률 표시를 로그에서 못 찾았습니다'));
    }
    if (항목.상태 === '달리는중' && 항목.조용한초 !== null && 항목.조용한초 > 300) {
      줄들.push(칸만들기('div', '줄항 경고', '⚠ ' + 초글(항목.조용한초) + ' 동안 출력이 없습니다'));
    }
    for (const 숫 of (항목.숫자들 || []).slice(0, 펴짐 ? 6 : 2)) 줄들.push(숫자네모(숫));
    if (펴짐) {
      if (항목.불) 줄들.push(칸만들기('div', '줄항 없음', '명령: ' + 항목.불));
      if ((항목.끝줄들 || []).length) 줄들.push(칸만들기('div', '옛줄', 항목.끝줄들.join(String.fromCharCode(10))));
    }
    return 줄들;
  }

  if (항목.종류 === '진행') {
    줄들.push(막대만들기(항목.진행 ? 항목.진행.퍼센트 : null));
    if (!항목.진행) {
      줄들.push(칸만들기('div', '줄항 없음', 이름 + ': 진행 표시를 못 찾았습니다'));
    } else {
      줄들.push(칸만들기('div', '줄항 없음', 이름));
      for (const 네모 of 진행네모들(항목.진행, null)) 줄들.push(네모);
    }
    return 줄들;
  }
  if (항목.종류 === '숫자') {
    if (!항목.숫자) { 없음('아직 값이 없습니다'); return 줄들; }
    줄들.push(숫자네모({ ...항목.숫자, 이름 }));
    return 줄들;
  }
  if (항목.종류 === '파일') {
    const 최 = 항목.최근 || {};
    줄들.push(네모만들기(이름, '파일 ' + 항목.개수 + '개 · ' + 크기글(항목.합계크기),
      '최근 ' + 최.이름 + ' (' + 크기글(최.크기) + ', ' + 초글(최.몇초전) + ' 전)' + (항목.커지는중 ? ' ● 커지는 중' : '')));
    return 줄들;
  }
  if (항목.종류 === '값') {
    줄들.push(네모만들기(이름, 항목.값));
    return 줄들;
  }
  if (항목.종류 === '기록') {
    const 줄들끝 = (항목.줄들 || []);
    줄들.push(칸만들기('div', '옛줄', (펴짐 ? 줄들끝 : 줄들끝.slice(-1)).join(String.fromCharCode(10)) || '(비어 있음)'));
    return 줄들;
  }
  if (항목.종류 === '기계') {
    if (항목.값 === 'GPU') {
      줄들.push(막대만들기(항목.사용률));
      줄들.push(네모만들기('GPU 사용률', 항목.사용률 + '%'));
      줄들.push(네모만들기('GPU 메모리', 크기글(항목.메모리쓴 * 1048576) + ' / ' + 크기글(항목.메모리전체 * 1048576)));
      if (항목.온도 !== null && 항목.온도 !== undefined) 줄들.push(네모만들기('GPU 온도', 항목.온도 + '℃'));
    } else if (항목.값 === '메모리') {
      줄들.push(막대만들기(항목.사용률));
      줄들.push(네모만들기('메모리 사용률', 항목.사용률 + '%', '(' + 항목.쓴MB + ' / ' + 항목.전체MB + 'MB)'));
    } else {
      줄들.push(막대만들기(항목.사용률));
      줄들.push(네모만들기('디스크 여유', 항목.여유GB + 'GB', '전체 ' + 항목.전체GB + 'GB'));
    }
    return 줄들;
  }
  return 줄들;
}

function 판상태글(판) {
  const 일 = (판.항목들 || []).find((x) => x.종류 === '일' && x.있음);
  if (일) return 일상태글(일);
  return 판.상태 === '보는중' ? '지켜보는 중' : 판.상태;
}

function 현황판그리기(판) {
  const 펴짐 = 현황.펴짐.has(판.번호) ? 현황.펴짐.get(판.번호) : false;
  const 카드 = 칸만들기('div', '현황판 ' + 판.상태);
  const 머리 = 칸만들기('div', '판머리');
  머리.appendChild(칸만들기('span', '점'));
  머리.appendChild(칸만들기('span', '판이름', 판.이름));
  const 일 = (판.항목들 || []).find((x) => x.종류 === '일' && x.있음);
  if (일 && 일.상태 === '달리는중') {
    const 멈춤 = 칸만들기('span', '판단추 판멈춤', '■');
    멈춤.title = '이 일을 멈춥니다';
    멈춤.onclick = (e) => { e.stopPropagation(); 현황멈춤누름(판, 일); };
    머리.appendChild(멈춤);
  }
  const 닫기 = 칸만들기('span', '판단추', '✕');
  닫기.title = 판.자동 ? '이 카드 치우기 (일은 그대로 둡니다)' : '이 현황판 치우기';
  닫기.onclick = (e) => { e.stopPropagation(); void 현황짓(판.자동 ? '숨김' : '치움', 판.번호); };
  머리.appendChild(닫기);
  머리.onclick = () => { 현황.펴짐.set(판.번호, !펴짐); 현황그리기(); };
  머리.title = 펴짐 ? '눌러서 접기' : '눌러서 자세히 보기';
  카드.appendChild(머리);
  카드.appendChild(칸만들기('div', '상태글', 판상태글(판)));
  let 격자 = null;
  for (const 항목 of 판.항목들 || []) {
    // 접힌 카드는 일 하나의 핵심만. GPT가 건 여러 항목은 접어도 한 줄씩은 보인다
    for (const 줄 of 항목줄들(항목, 펴짐)) {
      if (줄.className && 줄.className.split(' ')[0] === '네모') {
        // 이웃한 네모는 한 격자에 담는다(칸마다 한 줄씩 늘어서면 길고 읽기 어렵다)
        if (!격자) { 격자 = 칸만들기('div', '네모틀'); 카드.appendChild(격자); }
        격자.appendChild(줄);
      } else {
        격자 = null;
        카드.appendChild(줄);
      }
    }
    격자 = null;
  }
  return 카드;
}

function 현황그리기() {
  const 칸 = $('현황칸');
  if (!칸) return;
  const 옛자리 = 칸.scrollTop;
  칸.textContent = '';
  if (!현황.판들.length) {
    칸.hidden = true;
    보기배치();
    return;
  }
  칸.hidden = false;
  보기배치();
  const 머리글 = 칸만들기('div', '머리글');
  const 이름 = 칸만들기('span', '이름', '실행 현황');
  이름.title = '숫자는 GPT가 아니라 서버가 직접 읽은 값입니다';
  머리글.appendChild(이름);
  칸.appendChild(머리글);
  for (const 판 of 현황.판들) 칸.appendChild(현황판그리기(판));
  if (현황.더있음) 칸.appendChild(칸만들기('div', '현황더', '… 오래된 일 ' + 현황.더있음 + '개는 접어 두었습니다'));
  칸.scrollTop = 옛자리;
}

// 방 목록 줄 옆의 작은 막대. 방 목록 전체를 다시 그리지 않고 막대만 바꾼다
// (다시 그리면 이름을 고치던 칸이나 끌던 줄이 날아간다).
function 방막대맞추기(번호) {
  const 칸 = 방줄들[번호];
  if (!칸) return;
  const 요 = 현황.요약[번호];
  칸.막대칸.textContent = '';
  칸.알.classList.toggle('돌아감', !!(요 && 요.달리는수));
  if (!요) { 칸.줄.title = ''; return; }
  if (요.달리는수) {
    const 막대 = 칸만들기('span', '방막대' + (요.퍼센트 === null || 요.퍼센트 === undefined ? ' 모름' : ''));
    const 속 = document.createElement('i');
    if (요.퍼센트 !== null && 요.퍼센트 !== undefined) 속.style.width = 요.퍼센트 + '%';
    막대.appendChild(속);
    막대.title = '도는 일 ' + 요.달리는수 + '개' + (요.퍼센트 !== null && 요.퍼센트 !== undefined ? ' · ' + 요.퍼센트 + '%' : '');
    칸.막대칸.appendChild(막대);
  }
  if (요.실패수) {
    const 실패 = 칸만들기('span', '방실패', '●');
    실패.title = '끊기거나 실패한 일 ' + 요.실패수 + '개';
    칸.막대칸.appendChild(실패);
  }
}

function 방막대모두맞추기() {
  for (const 번호 of Object.keys(방줄들)) 방막대맞추기(번호);
}

// ── 고르기 (클로드의 물음 카드) ────────────────────────────────
// GPT가 답 끝에 【물음】 … 【물음끝】 로 선택지를 내면 입력칸 위에 고르는 카드를 띄운다.
// 몇 개든 고를 수 있고 직접 적을 수도 있다. [보내기] 를 누르면 【선택】 으로 GPT에게 간다.
//
//   【물음】
//   무엇부터 할까요?
//   배경: 지금 상황과 왜 묻는지 두세 문장
//   - 보상 고치기 | 사격이 0회인 원인부터
//     하면: 무엇이 어떻게 바뀌는지
//     좋은 점: …
//     걱정: …
//     시간: 약 10분
//   - 재학습 | 지금 보상 그대로
//     하면: …
//   추천: 보상 고치기 — 이유 한두 문장
//   【물음끝】
//
// 이 카드만 읽어도 무슨 일이고 무엇을 고르면 어떻게 되는지 알 수 있게, 배경 · 선택지별 상세 · 추천을 카드에 그대로 보인다.
// 배경 · 상세 · 추천은 없어도 된다(옛 모양 그대로 읽힌다). 한 답에 【물음】 이 여러 개면 한 카드에 차례로 보인다.

// GPT가 코드블록으로 싸서 쓰기도 한다. 그 울타리(```)까지 한 덩어리로 본다.
function 물음식() {
  return new RegExp('(?:```[a-zA-Z]*\\s*)?' + 정규식이스케이프(규약.물음시작)
    + '([\\s\\S]*?)' + 정규식이스케이프(규약.물음끝) + '(?:\\s*```)?', 'g');
}

function 꾸밈뺌(글) {
  return String(글 || '').replace(/\*\*|`/g, '').replace(/^#+\s*/, '').trim();
}

function 고를것읽기(글) {
  const 자리 = 글.indexOf('|');
  return 자리 === -1 ? { 이름: 꾸밈뺌(글), 설명: '' }
    : { 이름: 꾸밈뺌(글.slice(0, 자리)), 설명: 꾸밈뺌(글.slice(자리 + 1)) };
}

// 선택지 아래에 붙는 상세 줄의 이름표 → 카드에 보일 이름
const 상세이름 = {
  '하면': '하면', '하면 어떻게 되나': '하면', '결과': '하면', '효과': '하면', '바뀌는 것': '하면', '하는 일': '하면',
  '좋은 점': '좋은 점', '장점': '좋은 점', '이점': '좋은 점',
  '걱정': '걱정', '걱정되는 점': '걱정', '단점': '걱정', '위험': '걱정', '주의': '걱정', '약점': '걱정',
  '시간': '시간', '걸리는 시간': '시간', '크기': '크기', '비용': '크기', '범위': '크기', '근거': '근거',
};
const 배경이름들 = ['배경', '상황', '지금 상황', '왜 묻나', '왜 묻는지', '묻는 까닭'];

// "이름: 값" 모양이면 {라벨, 값}, 아니면 null
function 이름표값읽기(글) {
  const m = 꾸밈뺌(글).match(/^([^:：|]{1,14}?)\s*[:：]\s*(.+)$/);
  return m ? { 라벨: m[1].trim(), 값: m[2].trim() } : null;
}

function 추천찾기(추천글, 고를것) {
  const 글 = 꾸밈뺌(추천글).replace(/^["'“‘]/, '');
  const 번 = 글.match(/^(\d+)\s*번?(?:\s*[-—–:|,.)]\s*|\s+|$)(.*)$/);
  if (번 && Number(번[1]) >= 1 && Number(번[1]) <= 고를것.length) {
    return { 번호: Number(번[1]) - 1, 이유: (번[2] || '').trim() };
  }
  let 맞은 = -1;
  고를것.forEach((것, i) => {
    if (글.startsWith(것.이름) && (맞은 < 0 || 것.이름.length > 고를것[맞은].이름.length)) 맞은 = i;
  });
  if (맞은 < 0) return { 번호: -1, 이유: 글 };
  const 이유 = 글.slice(고를것[맞은].이름.length).replace(/^["'”’]?\s*[-—–:|,.]*\s*/, '').trim();
  return { 번호: 맞은, 이유 };
}

// GPT가 닫는 표식(물음끝)을 빼먹고 끝낸 답도 카드로 읽는다(2026-10-04: 선택지·추천까지 멀쩡히 쓰고도 표식 하나가 없어 카드가 안 떴다).
// 안 닫힌 물음은 ① 다음 물음 열기 앞 ② 없으면 '사용자가 할 일' 줄 앞 ③ 없으면 글 끝 에서 닫는다.
function 물음닫기보정(글) {
  const 본 = String(글 || '');
  const 시작 = 규약.물음시작;
  const 끝 = 규약.물음끝;
  let 결과 = '';
  let 자리 = 0;
  for (;;) {
    const 열 = 본.indexOf(시작, 자리);
    if (열 === -1) { 결과 += 본.slice(자리); break; }
    const 닫 = 본.indexOf(끝, 열 + 시작.length);
    const 다음열 = 본.indexOf(시작, 열 + 시작.length);
    if (닫 !== -1 && (다음열 === -1 || 닫 < 다음열)) {         // 제대로 닫힘
      결과 += 본.slice(자리, 닫 + 끝.length);
      자리 = 닫 + 끝.length;
      continue;
    }
    let 자름 = 다음열 === -1 ? 본.length : 다음열;
    const 할일 = 본.slice(열, 자름).search(/\n[ \t]*사용자가 할 일/);
    if (할일 !== -1) 자름 = 열 + 할일;
    결과 += 본.slice(자리, 자름).replace(/\s+$/, '') + '\n' + 끝;
    자리 = 자름;
  }
  return 결과;
}

function 물음읽기(글) {
  const 물음들 = [];
  const 식 = 물음식();
  let m;
  while ((m = 식.exec(물음닫기보정(글))) !== null) {
    const 원줄들 = m[1].split('\n').filter((줄) => 줄.trim() && !/^\s*```/.test(줄));
    const 줄들 = 원줄들.map((줄) => 줄.trim());
    let 질문줄 = [];
    let 고를것 = [];
    let 배경 = [];
    let 추천글 = '';
    let 지금 = null;                 // 상세 줄이 붙을 선택지
    let 모드 = '질문';
    for (const 원줄 of 원줄들) {
      const 줄 = 원줄.trim();
      const 들여씀 = /^\s{2,}\S/.test(원줄);
      const 항 = 줄.match(/^(?:[-*•·]|\d+[.)])\s+(.+)$/);
      if (항) {
        // 불릿이어도 '하면: …' 같은 상세 줄이면 새 선택지가 아니라 앞 선택지의 상세다
        const 라 = 이름표값읽기(항[1]);
        if (라 && 지금 && 상세이름[라.라벨]) {
          지금.상세.push({ 라벨: 상세이름[라.라벨], 값: 라.값 });
          모드 = '상세';
          continue;
        }
        지금 = 고를것읽기(항[1]);
        지금.상세 = [];
        고를것.push(지금);
        모드 = '고르기';
        continue;
      }
      const 라 = 이름표값읽기(줄);
      if (라 && !고를것.length && 배경이름들.includes(라.라벨)) { 배경.push(라.값); 모드 = '배경'; continue; }
      if (라 && 라.라벨 === '추천') { 추천글 = 라.값; 모드 = '추천'; continue; }
      if (라 && 지금 && 상세이름[라.라벨]) {
        지금.상세.push({ 라벨: 상세이름[라.라벨], 값: 라.값 });
        모드 = '상세';
        continue;
      }
      // "배경:" · "추천:" 만 적고 값은 다음 줄부터 쓴 것 (GPT-5.6 이 이렇게 쓴다)
      const 머리만 = 꾸밈뺌(줄).match(/^([^:：|]{1,14}?)\s*[:：]$/);
      if (머리만 && !고를것.length && 질문줄.length && 배경이름들.includes(머리만[1].trim())) { 모드 = '배경'; continue; }
      if (머리만 && 머리만[1].trim() === '추천') { 모드 = '추천'; continue; }
      // 불릿 없이 "이름 | 설명" 으로 쓴 선택지. 질문(첫 줄)은 이미 나왔을 때만, 상세 줄("하면: 1 | 2")은 위에서 이미 걸러졌다.
      const 파이프 = 모드 !== '추천' && 질문줄.length ? 줄.match(/^([^:：|]{1,40}?)\s\|\s(.+)$/) : null;
      if (파이프) {
        지금 = 고를것읽기(줄);
        지금.상세 = [];
        고를것.push(지금);
        모드 = '고르기';
        continue;
      }
      if (!고를것.length) {
        if (모드 === '배경') 배경.push(꾸밈뺌(줄)); else 질문줄.push(꾸밈뺌(줄));
      } else if (모드 === '추천') {
        추천글 += ' ' + 꾸밈뺌(줄);
      } else if (들여씀 && 지금) {
        지금.상세.push({ 라벨: '', 값: 꾸밈뺌(줄) });
      }
    }
    // 목록 표시(-)가 화면에서 빠진 채 기록된 답: 첫 줄이 물음, 나머지가 고를 것
    if (!고를것.length && !배경.length && !추천글 && 줄들.length >= 3) {
      질문줄 = [꾸밈뺌(줄들[0])];
      고를것 = 줄들.slice(1).map(고를것읽기);
    }
    고를것 = 고를것.filter((것) => 것.이름);
    if (질문줄.length && 고를것.length >= 2) {
      const 물음 = { 질문: 질문줄.join(' '), 고를것 };
      if (배경.length) 물음.배경 = 배경.join(' ');
      if (추천글) {
        const 찾음 = 추천찾기(추천글, 고를것);
        if (찾음.번호 >= 0) 고를것[찾음.번호].추천 = true;
        물음.추천 = { 이름: 찾음.번호 >= 0 ? 고를것[찾음.번호].이름 : '', 이유: 찾음.이유 };
      }
      물음들.push(물음);
    }
  }
  return 물음들;
}

// 대화 본문에는 물음을 표식 없이 보통 글(굵은 물음 + 목록)로 보인다
function 물음풀기(글) {
  return 물음닫기보정(글).replace(물음식(), (통, 속) => {
    const 물음 = 물음읽기(규약.물음시작 + 속 + 규약.물음끝)[0];
    if (!물음) return 속;
    const 상세줄 = (것) => (것.상세 || []).map((상) => (상.라벨 ? 상.라벨 + ': ' : '') + 상.값).join(' ｜ ');
    return '\n\n**' + 물음.질문 + '**\n\n'
      + (물음.배경 ? '> ' + 물음.배경 + '\n\n' : '')
      + 물음.고를것.map((것) => '- ' + 것.이름 + (것.추천 ? ' ★추천' : '') + (것.설명 ? ' — ' + 것.설명 : '')
        + (상세줄(것) ? ' ｜ ' + 상세줄(것) : '')).join('\n') + '\n\n'
      + (물음.추천 ? '★ 추천: ' + (물음.추천.이름 ? 물음.추천.이름 + (물음.추천.이유 ? ' — ' : '') : '') + 물음.추천.이유 + '\n\n' : '');
  });
}

// 내가 고른 답(【선택】)은 표식을 떼고 보인다
function 선택보기(글) {
  const 말 = String(글 || '');
  if (말.indexOf(규약.선택시작) !== 0) return 말;
  return 말.split('\n').slice(1).filter((줄) => 줄.trim() && 줄.trim() !== 규약.선택끝).join('\n');
}

// 아직 답하지 않은 물음 — 마지막 말이 GPT 것이고 그 안에 물음이 있을 때만
function 열린물음() {
  if (!화면.지금방 || 화면.방없는대화) return null;
  const 목록 = 화면.대화 || [];
  for (let 번 = 목록.length - 1; 번 >= 0; 번--) {
    const 항목 = 목록[번];
    // 내가 이미 말했거나, 그 답 뒤에 도구가 돌았으면(GPT가 묻고도 계속 일했다) 지난 물음이다
    if (항목.종류 === '사용자' || 항목.종류 === '도구') return null;
    if (항목.종류 !== 'gpt') continue;
    const 물음들 = 물음읽기(항목.글);
    if (!물음들.length) return null;
    return { 열쇠: 화면.지금방 + '|' + (항목.지문 || '') + '|' + (항목.때 || '') + '|' + 항목.글.length, 물음들 };
  }
  return null;
}

const 고르기 = {
  그린열쇠: '',        // 지금 카드가 그리고 있는 물음
  물음들: [],
  고른: [],            // 물음마다 고른 것의 번호 Set
  기타: [],            // 물음마다 직접 적은 글
  닫은: new Set(),     // 답했거나 ✕ 로 닫은 물음
};

// 판은 3초마다 다시 그린다. 물음이 그대로면 카드를 건드리지 않는다
// (다시 만들면 고른 것과 적던 글, 글자 치던 자리가 날아간다).
function 고르기그리기() {
  const 칸 = $('고르기칸');
  if (!칸) return;
  const 열린 = 열린물음();
  const 열쇠 = 열린 && !고르기.닫은.has(열린.열쇠) ? 열린.열쇠 : '';
  if (열쇠 === 고르기.그린열쇠) return;
  고르기.그린열쇠 = 열쇠;
  고르기.물음들 = 열쇠 ? 열린.물음들 : [];
  고르기.고른 = 고르기.물음들.map(() => new Set());
  고르기.기타 = 고르기.물음들.map(() => '');
  // 카드가 생기면 대화 칸이 그만큼 줄어든다. 맨 아래를 보고 있었으면 맨 아래를 지킨다
  // (안 그러면 방금 온 물음 글이 카드 높이만큼 가려진다).
  const 흐름 = $('흐름');
  const 바닥이었나 = 바닥인가(흐름);
  고르기카드그리기();
  if (바닥이었나) 흐름.scrollTop = 흐름.scrollHeight;
}

// 배경 · 선택지 상세 · 추천이 하나도 없는 짧은 물음. 카드만 읽어서는 고르기 어려울 수 있다.
function 얇은물음(물음) {
  return !물음.배경 && !물음.추천 && 물음.고를것.every((것) => !(것.상세 || []).length);
}

const 자세히요청글 = '방금 물음 카드를 그 카드만 읽어도 알 수 있게 다시 써 주세요. 배경(지금 상황과 왜 묻는지), '
  + '선택지마다 하면·좋은 점·걱정·시간, 끝에 추천과 이유를 넣고, 어려운 말은 풀어 주세요.';

function 고른수() {
  return 고르기.고른.reduce((합, 모음) => 합 + 모음.size, 0)
    + 고르기.기타.filter((글) => 글.trim()).length;
}

function 고르기카드그리기() {
  const 칸 = $('고르기칸');
  칸.textContent = '';
  if (!고르기.물음들.length) return;

  const 카드 = document.createElement('div');
  카드.className = '고르기';

  const 머리 = document.createElement('div');
  머리.className = '머리';
  const 이름 = document.createElement('span');
  이름.textContent = 'ChatGPT가 묻습니다 · 몇 개든 고를 수 있습니다';
  const 벌림 = document.createElement('span');
  벌림.className = '벌림';
  const 닫기 = document.createElement('span');
  닫기.className = '닫기';
  닫기.textContent = '✕';
  닫기.title = '닫기 (ChatGPT 창에서 직접 답할 때)';
  닫기.onclick = () => { 고르기.닫은.add(고르기.그린열쇠); 고르기그리기(); };
  머리.append(이름, 벌림, 닫기);
  카드.appendChild(머리);

  const 단추 = document.createElement('button');
  const 몇 = document.createElement('span');
  const 아래맞추기 = () => {
    const 수 = 고른수();
    단추.disabled = 수 === 0;
    몇.textContent = 수 ? 수 + '개 선택' : '고르거나 직접 적으세요';
  };

  고르기.물음들.forEach((물음, 물음번) => {
    const 질문 = document.createElement('div');
    질문.className = '질문';
    질문.textContent = 물음.질문;
    카드.appendChild(질문);
    if (물음.배경) {
      const 배경 = document.createElement('div');
      배경.className = '배경';
      배경.textContent = 물음.배경;
      카드.appendChild(배경);
    }
    if (물음.추천) {
      const 추천 = document.createElement('div');
      추천.className = '추천';
      추천.textContent = '★ ChatGPT 추천: ' + (물음.추천.이름 || '') + (물음.추천.이름 && 물음.추천.이유 ? ' — ' : '') + (물음.추천.이유 || '');
      카드.appendChild(추천);
    }

    물음.고를것.forEach((것, 번) => {
      const 줄 = document.createElement('div');
      const 네모 = document.createElement('span');
      네모.className = '네모';
      const 맞추기 = () => {
        const 고름 = 고르기.고른[물음번].has(번);
        줄.className = '고를것' + (고름 ? ' 고름' : '');
        네모.textContent = 고름 ? '☑' : '☐';
      };
      const 속 = document.createElement('div');
      속.className = '속';
      const 이름칸 = document.createElement('div');
      이름칸.className = '이름';
      이름칸.textContent = 것.이름;
      if (것.추천) {
        const 별 = document.createElement('span');
        별.className = '추천표';
        별.textContent = ' ★추천';
        이름칸.appendChild(별);
      }
      속.appendChild(이름칸);
      if (것.설명) {
        const 설명 = document.createElement('div');
        설명.className = '설명';
        설명.textContent = 것.설명;
        속.appendChild(설명);
      }
      for (const 상 of (것.상세 || [])) {
        const 상세 = document.createElement('div');
        상세.className = '상세 ' + ({ '좋은 점': '좋음', '걱정': '걱정' }[상.라벨] || '');
        if (상.라벨) {
          const 라벨 = document.createElement('span');
          라벨.className = '라벨';
          라벨.textContent = 상.라벨;
          상세.appendChild(라벨);
        }
        상세.appendChild(document.createTextNode(상.값));
        속.appendChild(상세);
      }
      줄.append(네모, 속);
      // 누를 때 카드를 다시 만들지 않고 그 줄만 바꾼다(적던 글이 안 날아간다)
      줄.onclick = () => {
        const 모음 = 고르기.고른[물음번];
        if (모음.has(번)) 모음.delete(번); else 모음.add(번);
        맞추기();
        아래맞추기();
      };
      맞추기();
      카드.appendChild(줄);
    });

    const 기타 = document.createElement('input');
    기타.className = '기타';
    기타.type = 'text';
    기타.placeholder = '직접 적기 (다른 답이나 덧붙일 말)';
    기타.value = 고르기.기타[물음번];
    기타.addEventListener('input', () => { 고르기.기타[물음번] = 기타.value || ''; 아래맞추기(); });
    기타.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); 고르기보내기(); }
    });
    카드.appendChild(기타);
  });

  const 줄 = document.createElement('div');
  줄.className = '줄';
  몇.className = '몇';
  단추.className = '작은';
  단추.textContent = '보내기';
  단추.onclick = 고르기보내기;
  if (고르기.물음들.some(얇은물음)) {
    const 자세히 = document.createElement('button');
    자세히.className = '작은 자세히';
    자세히.textContent = '더 자세히 설명해 줘';
    자세히.title = '이 카드는 설명이 짧습니다. ChatGPT가 배경 · 선택지별 상세 · 추천을 넣어 다시 씁니다.';
    자세히.onclick = 자세히요청;
    줄.append(자세히);
  }
  줄.append(몇, 단추);
  카드.appendChild(줄);
  아래맞추기();

  칸.appendChild(카드);
}

function 선택글() {
  const 여럿 = 고르기.물음들.length > 1;
  const 줄들 = [규약.선택시작 + ' 사용자가 판에서 직접 고른 답입니다'];
  고르기.물음들.forEach((물음, 번) => {
    const 이름들 = 물음.고를것.filter((것, i) => 고르기.고른[번].has(i)).map((것) => 것.이름);
    const 적은것 = 고르기.기타[번].trim();
    줄들.push('물음' + (여럿 ? ' ' + (번 + 1) : '') + ' ' + 물음.질문);
    줄들.push('고름 ' + (이름들.length ? 이름들.join(' / ') : (적은것 ? '(목록에서는 고르지 않음)' : '(답하지 않음)')));
    if (적은것) 줄들.push('덧붙임 ' + 적은것);
  });
  줄들.push(규약.선택끝);
  return 줄들.join('\n');
}

// 설명이 짧은 카드: 고르지 않고 ChatGPT에게 다시 자세히 쓰라고 한다
async function 자세히요청() {
  if (고르기보내는중 || !고르기.그린열쇠) return;
  고르기보내는중 = true;
  try {
    const 열쇠 = 고르기.그린열쇠;
    if (일하는중()) {
      줄선말.push(자세히요청글);
      줄선것그리기();
      알림('줄 세웠습니다 (' + 줄선말.length + '개). 일이 끝나면 보냅니다.');
    } else if (!(await 진짜보내기(자세히요청글))) {
      return;
    }
    고르기.닫은.add(열쇠);
    고르기그리기();
  } finally {
    고르기보내는중 = false;
  }
}

let 고르기보내는중 = false;
async function 고르기보내기() {
  if (고르기보내는중 || !고르기.그린열쇠 || 고른수() === 0) return;
  고르기보내는중 = true;
  try {
    const 글 = 선택글();
    const 열쇠 = 고르기.그린열쇠;
    if (일하는중()) {
      줄선말.push(글);
      줄선것그리기();
      알림('줄 세웠습니다 (' + 줄선말.length + '개). 일이 끝나면 보냅니다.');
    } else if (!(await 진짜보내기(글))) {
      return;                       // 못 보냈으면 카드를 그대로 둔다
    }
    고르기.닫은.add(열쇠);
    고르기그리기();
  } finally {
    고르기보내는중 = false;
  }
}

// 판에서 바로 시킨다. 일하는 중이면 끼어들지 않고 줄을 세운다.
// (클로드도 일하는 중에 Enter 를 치면 끼어들지 않고 줄을 세운다.)

const 줄선말 = [];

function 일하는중() {
  return !!(화면.처리중 || 화면.생성중);
}

function 보냄단추맞추기() {
  const 글 = ($('시킴글').value || '').trim();
  const 단추 = $('보냄단추');
  단추.classList.toggle('쓸수있음', !!글);
  단추.textContent = 글 && 일하는중() ? '＋' : '↑';
  단추.title = 글 && 일하는중() ? '줄 세우기 (일 끝나면 보냄)' : '보내기';
}

function 줄선것그리기() {
  const 칸 = $('줄선것');
  칸.textContent = '';
  줄선말.forEach((말, 번) => {
    const 줄 = document.createElement('div');
    줄.className = '줄';
    const 빼기 = document.createElement('span');
    빼기.className = '빼기';
    빼기.textContent = '✕';
    빼기.title = '빼기';
    빼기.onclick = () => { 줄선말.splice(번, 1); 줄선것그리기(); };
    const 글 = document.createElement('span');
    글.className = '글';
    글.textContent = '⏳ ' + 말;
    줄.append(빼기, 글);
    칸.appendChild(줄);
  });
}

async function 진짜보내기(글) {
  const 답 = await 탭에게('보내기', 글);
  if (답 && 답.됨) {
    // 내 말은 ChatGPT 탭이 화면에서 읽어 남긴다. 여기서도 남기면 두 번 보인다.
    await 방새로고침();
    알림('보냈습니다. 답을 기다립니다…');
    return true;
  }
  알림('⚠ 보내지 못했습니다. ChatGPT 화면을 확인하세요.');
  return false;
}

async function 시킴보내기() {
  const 글 = ($('시킴글').value || '').trim();
  if (!글) return;
  $('시킴글').value = '';
  $('시킴글').style.height = 'auto';

  if (일하는중()) {
    줄선말.push(글);
    줄선것그리기();
    알림('줄 세웠습니다 (' + 줄선말.length + '개). 일이 끝나면 보냅니다.');
  } else {
    await 진짜보내기(글);
  }
  보냄단추맞추기();
}

// 일이 끝나면 줄 세운 말을 하나씩 내보낸다.
let 내보내는중 = false;
async function 줄선것내보내기() {
  if (내보내는중 || !줄선말.length || 일하는중() || !화면.켜짐) return;
  내보내는중 = true;
  try {
    const 글 = 줄선말.shift();
    줄선것그리기();
    await 진짜보내기(글);
  } finally {
    내보내는중 = false;
  }
}

$('시킴글').addEventListener('input', () => {
  const 칸 = $('시킴글');
  칸.style.height = 'auto';
  칸.style.height = Math.min(140, 칸.scrollHeight) + 'px';
  보냄단추맞추기();
});

$('시킴글').addEventListener('keydown', (e) => {
  // Enter 는 보내기, Shift+Enter 는 줄바꿈. 클로드와 같다.
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    시킴보내기();
  }
});

$('보냄단추').onclick = 시킴보내기;

// ── 파일 보기 (클로드의 파일 창) ──────────────────────────────
// 화면에 뜬 파일 이름을 누르면 오른쪽 파일 칸에 탭으로 열린다.
// (도구 줄 · 변경 요약 · 파일 나무 — 셋 다 이 하나로 이어진다)
//
//   [☰] [core.py ✕] [프로토콜.md ✕]           [⟳ ⋮ ⤢ ✕]
//   나무 │ 문서 › 프로토콜.md                     [</>]
//        │ (md 는 그려서, 나머지는 줄 번호와 함께)

const 한번에줄 = 2000;               // 한 번에 읽어 오는 줄 수. 넘으면 '더 불러오기'
const 그려볼끝 = ['md', 'markdown'];  // 그려서 보여줄 수 있는 것
const 열린탭 = [];                    // [{밭, 이름, 줄들, 총줄, 틀림, 원본, 읽는중}]
let 지금탭밭 = '';
let 일뿌리 = '';                      // 일할 폴더 자리. 빵부스러기를 짧게 쓰는 데 쓴다
let 방뿌리 = '';                      // 이 방의 자료 칸 자리

const 역빗금 = String.fromCharCode(92);
const 줄끝 = String.fromCharCode(10);

function 빗금으로(밭) {
  return String(밭 || '').split(역빗금).join('/');
}

function 파일이름(밭) {
  const 조각 = 빗금으로(밭).split('/').filter(Boolean);
  return 조각[조각.length - 1] || String(밭 || '');
}

function 끝말(밭) {
  const 이름 = 파일이름(밭);
  const 점 = 이름.lastIndexOf('.');
  return 점 === -1 ? '' : 이름.slice(점 + 1).toLowerCase();
}

function 탭찾기(밭) {
  return 열린탭.find((탭) => 탭.밭 === 밭) || null;
}

function 새탭(밭) {
  return { 밭, 이름: 파일이름(밭), 줄들: [], 총줄: 0, 틀림: '', 원본: false, 읽는중: false };
}

function 탭들기억() {
  try {
    localStorage.setItem('열린탭', JSON.stringify(열린탭.map((탭) => 탭.밭)));
    localStorage.setItem('지금탭', 지금탭밭);
  } catch (e) { /* 넘어간다 */ }
}

// 파일 열기 — 이미 열려 있으면 그 탭으로 옮기기만 한다.
async function 파일열기(밭) {
  if (!밭) return;
  let 탭 = 탭찾기(밭);
  if (!탭) {
    탭 = 새탭(밭);
    열린탭.push(탭);
  }
  지금탭밭 = 밭;
  고른파일 = 밭;
  윗칸펴기(밭);
  보기넓히기();
  탭들기억();
  보기그리기();
  파일나무그리기();
  if (!탭.줄들.length && !탭.틀림 && !탭.읽는중) await 탭읽기(탭, 1);
}

// 연 파일이 접힌 칸 속에 있으면 나무에서 안 보인다. 윗칸들을 펴서 드러낸다.
// 나무의 칸 자리는 서버가 준 그대로(윈도우면 역빗금)라, 일할 곳의 꼴에 맞춰 만든다.
function 윗칸펴기(밭) {
  if (!일뿌리) return;
  const 뿌리 = 빗금으로(일뿌리).replace(/\/$/, '');
  const 줄 = 빗금으로(밭);
  if (줄.toLowerCase().indexOf(뿌리.toLowerCase() + '/') !== 0) return;
  const 가름 = String(일뿌리).indexOf(역빗금) !== -1 ? 역빗금 : '/';
  const 조각 = 줄.slice(뿌리.length + 1).split('/').filter(Boolean);
  let 자리 = String(일뿌리).replace(/[\\/]$/, '');
  for (const 것 of 조각.slice(0, -1)) {
    자리 = 자리 + 가름 + 것;
    펼친것.add(자리);
  }
}

// 좁은 칸에서는 나무와 내용을 나란히 둘 수 없다. 처음 열 때 한 번 넓혀 준다.
function 보기넓히기() {
  const 위칸 = $('위칸');
  const 지금너비 = parseInt(위칸.style.width, 10) || 165;
  const 바람 = Math.min(560, Math.floor((window.innerWidth || 800) * 0.62));
  if (지금너비 < 바람) 위칸.style.width = 일할곳너비맞추기(바람) + 'px';
  위칸보이기(true);
}

async function 탭읽기(탭, 첫줄) {
  탭.읽는중 = true;
  if (탭.밭 === 지금탭밭) 보기그리기();
  const 답 = await 서버에게({
    종류: '도구실행',
    요청: { 나물: '열무', 밭: 탭.밭, 첫줄, 끝줄: 첫줄 + 한번에줄 - 1 },
    방번호: 화면.지금방 || '',
  });
  탭.읽는중 = false;

  if (!답 || 답.됨 === false) {
    탭.틀림 = '읽지 못했습니다: ' + ((답 && 답.탈) || '알 수 없음');
  } else {
    const 총줄 = 답.총줄 || 0;
    const 새줄 = 총줄 === 0 ? [] : String(답.속 || '').split(줄끝);
    탭.줄들 = 첫줄 === 1 ? 새줄 : 탭.줄들.concat(새줄);
    탭.총줄 = 총줄;
    탭.틀림 = '';
  }
  if (탭.밭 === 지금탭밭) 보기그리기();
}

async function 탭다시읽기(밭) {
  const 탭 = 탭찾기(밭);
  if (!탭) return;
  탭.줄들 = [];
  탭.틀림 = '';
  await 탭읽기(탭, 1);
}

function 탭닫기(밭) {
  const 자리 = 열린탭.findIndex((탭) => 탭.밭 === 밭);
  if (자리 === -1) return;
  열린탭.splice(자리, 1);
  if (지금탭밭 === 밭) {
    const 옆 = 열린탭[Math.min(자리, 열린탭.length - 1)];
    지금탭밭 = 옆 ? 옆.밭 : '';
    고른파일 = 지금탭밭;
    if (옆 && !옆.줄들.length && !옆.틀림 && !옆.읽는중) 탭읽기(옆, 1);
  }
  if (!열린탭.length) $('틀').classList.remove('보기크게');
  탭들기억();
  보기그리기();
  파일나무그리기();
}

// 일할 폴더 안이면 그 뒤만, 밖이면 전체를 › 로 잇는다.
function 빵부스러기그리기(밭) {
  const 칸 = $('빵부스러기');
  칸.textContent = '';
  let 줄 = 빗금으로(밭);
  let 머리 = '';
  // 일할 곳 안이면 그 뒤만, 방 자료 안이면 '방 자료 › …' 로 줄인다
  for (const [뿌리밭, 이름] of [[일뿌리, ''], [방뿌리, '방 자료']]) {
    const 뿌리 = 빗금으로(뿌리밭).replace(/\/$/, '');
    if (뿌리 && 줄.toLowerCase().indexOf(뿌리.toLowerCase() + '/') === 0) {
      줄 = 줄.slice(뿌리.length + 1);
      머리 = 이름;
      break;
    }
  }
  const 조각 = (머리 ? [머리] : []).concat(줄.split('/').filter(Boolean));
  조각.forEach((것, 번) => {
    if (번) 칸.appendChild(document.createTextNode(' › '));
    const 글 = document.createElement('span');
    if (번 === 조각.length - 1) 글.className = '끝';
    글.textContent = 것;
    칸.appendChild(글);
  });
  칸.title = 밭;
}

function 탭줄그리기() {
  const 탭줄 = $('탭줄');
  탭줄.textContent = '';
  if (!열린탭.length) {
    const 이름 = document.createElement('span');
    이름.className = '이름';
    이름.id = '파일칸이름';
    이름.textContent = '파일';
    탭줄.appendChild(이름);
    return;
  }
  for (const 하나 of 열린탭) {
    const 탭칸 = document.createElement('div');
    탭칸.className = '탭' + (하나.밭 === 지금탭밭 ? ' 지금' : '');
    탭칸.title = 하나.밭;
    const 이름 = document.createElement('span');
    이름.className = '이름';
    이름.textContent = 하나.이름;
    const 닫기 = document.createElement('span');
    닫기.className = '닫기';
    닫기.textContent = '✕';
    닫기.title = '닫기';
    닫기.onclick = (e) => { e.stopPropagation(); 탭닫기(하나.밭); };
    탭칸.append(이름, 닫기);
    탭칸.onclick = () => 파일열기(하나.밭);
    탭줄.appendChild(탭칸);
  }
}

function 보기그리기() {
  const 탭 = 탭찾기(지금탭밭);
  $('파일칸').classList.toggle('보는중', !!탭);
  탭줄그리기();

  const 속 = $('보기속');
  속.textContent = '';
  if (!탭) return;

  빵부스러기그리기(탭.밭);
  const 그릴수있나 = 그려볼끝.includes(끝말(탭.밭));
  $('원본토글').hidden = !그릴수있나;
  $('원본토글').classList.toggle('켬', 탭.원본);

  if (탭.틀림) {
    const 틀림 = document.createElement('div');
    틀림.className = '보기틀림';
    틀림.textContent = 탭.틀림;
    속.appendChild(틀림);
    return;
  }
  if (탭.읽는중 && !탭.줄들.length) {
    const 기다림 = document.createElement('div');
    기다림.className = '빈안내';
    기다림.textContent = '읽는 중…';
    속.appendChild(기다림);
    return;
  }
  if (!탭.줄들.length) {
    const 빈 = document.createElement('div');
    빈.className = '빈안내';
    빈.textContent = '(빈 파일)';
    속.appendChild(빈);
    return;
  }

  if (그릴수있나 && !탭.원본) {
    const 답 = document.createElement('div');
    답.className = '답';
    마크다운그리기(탭.줄들.join(줄끝), 답);
    속.appendChild(답);
  } else {
    const 원본 = document.createElement('div');
    원본.className = '원본';
    탭.줄들.forEach((줄글, 번) => {
      const 번칸 = document.createElement('span');
      번칸.className = '번';
      번칸.textContent = String(번 + 1);
      const 줄칸 = document.createElement('span');
      줄칸.className = '줄';
      줄칸.textContent = 줄글 || ' ';
      원본.append(번칸, 줄칸);
    });
    속.appendChild(원본);
  }

  if (탭.총줄 > 탭.줄들.length) {
    const 끝 = document.createElement('div');
    끝.className = '보기끝';
    const 글 = document.createElement('span');
    글.textContent = 탭.줄들.length + ' / ' + 탭.총줄 + '줄';
    const 더 = document.createElement('button');
    더.className = '알약';
    더.textContent = 탭.읽는중 ? '읽는 중…' : '더 불러오기';
    더.onclick = () => { if (!탭.읽는중) 탭읽기(탭, 탭.줄들.length + 1); };
    끝.append(글, 더);
    속.appendChild(끝);
  }
}

$('원본토글').onclick = () => {
  const 탭 = 탭찾기(지금탭밭);
  if (!탭) return;
  탭.원본 = !탭.원본;
  보기그리기();
};

$('보기닫기').onclick = () => {
  열린탭.splice(0, 열린탭.length);
  지금탭밭 = '';
  고른파일 = '';
  $('틀').classList.remove('보기크게');
  탭들기억();
  보기그리기();
  파일나무그리기();
};

$('보기크게').onclick = () => {
  $('틀').classList.toggle('보기크게');
};

$('나무쪽토글').onclick = () => {
  const 칸 = $('파일칸');
  칸.classList.toggle('나무접힘');
  try { localStorage.setItem('나무접힘', 칸.classList.contains('나무접힘') ? '1' : '0'); }
  catch (e) { /* 넘어간다 */ }
};

// 열린 파일 메뉴는 따로 ⋮ 를 두지 않고 판 ⋮ 에 넣는다(⋮ 가 두 개라 헷갈렸다).
// '다시 읽기' 는 ⟳ 단추가 있으니 뺀다.
function 파일메뉴항목() {
  const 탭 = 탭찾기(지금탭밭);
  if (!탭) return [];
  return [
    { 글: '파일 되돌리기…', 쪽: 탭.이름 || '', 동작: () => 되돌림목록보기(탭.밭) },
    { 글: '이 파일 탭 닫기', 동작: () => 탭닫기(탭.밭) },
    null,
  ];
}

// 나무 너비 — 끌어서 바꾸고 기억한다
(function 보기가름대달기() {
  const 가름대 = $('보기가름대');
  let 끄는중 = false;
  가름대.onmousedown = (e) => { 끄는중 = true; e.preventDefault(); };
  document.addEventListener('mousemove', (e) => {
    if (!끄는중) return;
    const 왼 = $('보기몸').getBoundingClientRect().left;
    const 너비 = Math.max(90, Math.min(e.clientX - 왼, 420));
    $('나무쪽').style.width = 너비 + 'px';
  });
  document.addEventListener('mouseup', () => {
    if (!끄는중) return;
    끄는중 = false;
    try { localStorage.setItem('나무쪽너비', $('나무쪽').style.width); } catch (e) { /* 넘어간다 */ }
  });
})();

// 판을 다시 열었을 때 열어 두었던 탭을 되살린다(내용은 볼 때 읽는다)
function 탭되살리기() {
  try {
    const 밭들 = JSON.parse(localStorage.getItem('열린탭') || '[]');
    for (const 밭 of 밭들) {
      if (typeof 밭 === 'string' && !탭찾기(밭)) 열린탭.push(새탭(밭));
    }
    const 지금 = localStorage.getItem('지금탭') || '';
    if (탭찾기(지금)) { 지금탭밭 = 지금; 고른파일 = 지금; }
    const 너비 = localStorage.getItem('나무쪽너비');
    if (너비) $('나무쪽').style.width = 너비;
    if (localStorage.getItem('나무접힘') === '1') $('파일칸').classList.add('나무접힘');
  } catch (e) { /* 넘어간다 */ }
  보기그리기();
  const 탭 = 탭찾기(지금탭밭);
  if (탭) 탭읽기(탭, 1);
}

// ── 되돌리기 ──────────────────────────────────────────────────
// 고치기 전에 서버가 원본을 보관해 둔다. 그 목록을 꺼내 고르게 한다.
// (보여 주기만 하고 못 되돌리면 보관해 둔 뜻이 없다)

async function 되돌림목록보기(밭) {
  const 답 = await 서버에게({
    종류: '도구실행', 요청: { 나물: '미역', 밭 }, 방번호: 화면.지금방 || '' });

  if (!답 || 답.됨 === false) {
    알림('되돌릴 것이 없습니다: ' + ((답 && 답.탈) || '알 수 없음'));
    return;
  }

  const 보관들 = 답.보관목록 || [];
  if (!보관들.length) { 알림('보관된 것이 없습니다.'); return; }

  메뉴열기($('메뉴단추'), 보관들.slice(0, 12).map((것) => ({
    글: 때보기좋게(것.때),
    쪽: (것.줄수 || '?') + '줄',
    동작: async () => {
      const 돌림 = await 서버에게({
        종류: '도구실행',
        요청: { 나물: '미역', 밭, 때: 것.때 },
        방번호: 화면.지금방 || '',
      });
      if (돌림 && 돌림.됨 !== false) {
        알림('되돌렸습니다: ' + 때보기좋게(것.때));
        await 탭다시읽기(밭);
        파일나무그리기();
      } else {
        알림('⚠ 되돌리지 못했습니다: ' + ((돌림 && 돌림.탈) || '알 수 없음'));
      }
    },
  })));
}

// 20260916-142233-451 → 09-16 14:22:33
function 때보기좋게(때) {
  const s = String(때 || '');
  const m = s.match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})/);
  if (!m) return s;
  return m[2] + '-' + m[3] + ' ' + m[4] + ':' + m[5] + ':' + m[6];
}

// 밭처럼 생겼으면(빗금이나 역빗금이 있으면) 누를 수 있게 만든다.
function 밭처럼생겼나(글) {
  const s = String(글 || '');
  if (!s || s.length > 200) return false;
  return s.indexOf('/') !== -1 || s.indexOf(String.fromCharCode(92)) !== -1;
}

function 누르면열기(요소, 밭) {
  if (!밭처럼생겼나(밭)) return;
  요소.style.cursor = 'pointer';
  요소.title = '눌러서 이 파일 보기';
  요소.onclick = (e) => { e.stopPropagation(); 파일열기(밭); };
}


$('메뉴단추').onclick = (e) => {
  e.stopPropagation();
  if ($('메뉴').style.display === 'block') { 메뉴닫기(); return; }
  const 목표있음 = !!(화면.계획 && 화면.계획.일);
  const 항목들 = [
    { 글: '표시할 칸', 쪽: 보이는칸수() + '개', 동작: () => {} },
    { 글: 보기이름.현황, 켬: 보기설정.현황, 동작: () => 보기전환('현황') },
    { 글: 보기이름.일할곳, 켬: 보기설정.일할곳, 동작: () => 보기전환('일할곳') },
    { 글: 보기이름.기록, 켬: 보기설정.기록, 동작: () => 보기전환('기록') },
    { 글: 보기이름.파일, 켬: 보기설정.파일, 동작: () => 보기전환('파일') },
    null,
    ...파일메뉴항목(),
  ];
  항목들.push({ 글: '목표', 쪽: 목표있음 ? (화면.계획.진도 || '') : '세우기', 동작: 목표열기 });
  if (화면.지금방 && !화면.방없는대화) 항목들.push({ 글: '새 대화로 넘기기', 쪽: '대화가 꽉 찼을 때', 동작: 새대화로넘기기누름 });
  항목들.push(
    { 글: '결과 다시 보내기', 쪽: '보내기가 막혔을 때', 동작: 결과다시보내기 },
    { 글: '대답 다시 받기', 쪽: '답이 오지 않을 때', 동작: 대답다시받기누름 },
    { 글: '마지막 결과 다시 보내기', 쪽: '이미 보낸 결과를 한 번 더', 동작: 마지막결과다시보내기누름 },
    { 글: '대답 다시 시도', 쪽: 'ChatGPT의 다시 시도를 누릅니다', 동작: async () => {
      const 답 = await 탭에게('다시시도');
      알림(답 && 답.됨 ? '다시 시도 중…' : ((답 && 답.탈) || '하지 못했습니다'));
    } },
    null,
    { 글: '설정', 쪽: ((화면.사이트 && 화면.사이트.허용) || []).length + '곳 허용', 동작: 설정열기 },
    { 글: '다시 시작', 쪽: '꼬였을 때', 동작: async () => { await 탭에게('리셋'); 알림('다시 시작했습니다'); } },
    { 글: '문제 살펴보기', 동작: async () => { await 탭에게('진단'); 알림('개발자 도구(F12)의 콘솔에 기록했습니다'); } }
  );
  메뉴열기($('메뉴단추'), 항목들);
};

$('목표닫기').onclick = () => { $('목표창').style.display = 'none'; };
$('설정닫기').onclick = () => { $('설정창').style.display = 'none'; };
$('목표창').onclick = (e) => { if (e.target === $('목표창')) $('목표창').style.display = 'none'; };
$('설정창').onclick = (e) => { if (e.target === $('설정창')) $('설정창').style.display = 'none'; };

// 경과 시간은 스스로 흐른다. 상태가 안 와도 초는 가야 한다.
setInterval(() => { if (화면.시작한때) 해낸것그리기(); }, 1000);

// 서버는 창을 닫으면 그냥 죽는다. 다시 켰을 때도 알아채야 하므로 계속 본다.
setInterval(() => { 서버살았나(); }, 5000);

// 탭→창 알림은 페이지가 잠깐 바쁘거나 패널이 다시 그려질 때 놓칠 수 있다.
// 현재 보고 있는 탭의 방을 짧게 다시 읽어 대화가 오래된 채 남지 않게 한다.
let 동기화중 = false;
async function 대화동기화() {
  if (동기화중) return;
  동기화중 = true;
  try {
    const 상태 = await 탭에게('상태요청');
    if (상태 && 상태.값) {
      탭상태받기(상태.값);
      await 방새로고침(상태.값.지금방 || 화면.지금방);
      상태그리기();
      입력상태();
    }
  } finally {
    동기화중 = false;
  }
}
setInterval(대화동기화, 3000);
setInterval(현황돌기, 2000);
setInterval(사이트새로고침, 3000);
setInterval(받아오기새로고침, 3000);
// ChatGPT 탭만 열어 둔 상태에서는 일하지 않는다. 이 판이 열린 동안만 허용한다.
setInterval(() => { if (보는탭 !== null) void 탭에게('패널심장'); }, 2000);

(async function 시작() {
  // 서버가 꺼져 있으면 이 첫 확인에서 background 가 스스로 켠다(2~3초).
  알림('서버 확인 중…');
  if (await 서버살았나()) 알림('준비됨');

  try {
    보기설정불러오기();
    if (localStorage.getItem('위칸펼침') === '0') 위칸보이기(false);
    else $('위칸토글').classList.add('켬');
  } catch (e) { /* 넘어간다 */ }

  await 방새로고침();
  await 계획새로고침();
  await 받아오기새로고침();
  await 현황새로고침();
  await 사이트새로고침();
  본문그리기();
  탭되살리기();

  // 이 창에서 보고 있는 ChatGPT 탭이 붙어 있는지 물어본다.
  await 탭에게('패널시작');
  const 상태 = await 탭에게('상태요청');
  if (상태 && 상태.값) {
    탭상태받기(상태.값);
    상태그리기();
    입력상태();
    본문그리기();
  }

})();
