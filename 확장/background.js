// 서비스 워커 — 콘텐츠 스크립트 대신 로컬 브리지 서버로 요청을 보낸다.
// (페이지 CSP 영향을 안 받으려고 fetch 를 여기서 한다.)

const 브리지 = 'http://127.0.0.1:8765';

async function 도구실행(요청) {
  const 응답 = await fetch(브리지 + '/tool', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(요청),
  });
  return await 응답.json();
}

async function 서버확인() {
  const 응답 = await fetch(브리지 + '/ping');
  return await 응답.json();
}

async function 등급바꾸기(등급, 모드) {
  const 응답 = await fetch(브리지 + '/mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(모드 !== undefined && 모드 !== null ? { 모드: 모드 } : { 등급: 등급 }),
  });
  return await 응답.json();
}

async function 대화남기기(몸통) {
  const 응답 = await fetch(브리지 + '/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(몸통),
  });
  return await 응답.json();
}

async function 계획보기(방) {
  const 응답 = await fetch(브리지 + '/plan' + (방 ? '?방=' + encodeURIComponent(방) : ''));
  return await 응답.json();
}

// 도구막대 아이콘을 누르면 사이드 패널이 열리게 한다.
// (이 설정을 켜면 chrome.action.onClicked 는 더 이상 불리지 않는다.)
if (chrome.sidePanel) {
  chrome.runtime.onInstalled.addListener(() => {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
      .catch((e) => console.warn('[로컬에이전트] 사이드 패널 설정 실패:', e));
  });
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
} else if (chrome.sidebarAction && chrome.action) {
  // Firefox에서는 도구막대 아이콘을 누르면 같은 panel.html을 연다.
  chrome.action.onClicked.addListener(() => chrome.sidebarAction.open());
}

// ── 심장 박동 ──
// 크롬은 안 보이는 탭의 타이머를 1분에 한 번까지 늦춘다.
// 그래서 ChatGPT 창을 다른 창으로 덮으면 일이 사실상 멈췄다.
// 서비스 워커는 그 제한을 안 받으므로, 여기서 박동을 보내 탭을 깨운다.
// 통로가 열려 있는 동안은 워커도 안 잠든다.
const 박동주기ms = 400;
const 뛰는탭들 = new Set();
let 박동타이머 = null;

function 박동시작() {
  if (박동타이머) return;
  박동타이머 = setInterval(() => {
    for (const 통로 of 뛰는탭들) {
      try {
        통로.postMessage({ 짓: '뛰어' });
      } catch (e) {
        뛰는탭들.delete(통로);
      }
    }
    if (!뛰는탭들.size) { clearInterval(박동타이머); 박동타이머 = null; }
  }, 박동주기ms);
}

chrome.runtime.onConnect.addListener((통로) => {
  if (통로.name !== '심장') return;
  뛰는탭들.add(통로);
  박동시작();
  통로.onDisconnect.addListener(() => 뛰는탭들.delete(통로));

  // 에이전트가 도는 탭을 크롬이 메모리 절약으로 버리면(탭 폐기) 에이전트가 통째로 멈춘다.
  // 오래 딴 탭에 가 있으면 일어나는 일이라, 박동을 받는 탭은 못 버리게 해 둔다(통로를 다시 열 때마다 확인).
  try {
    const 탭 = 통로.sender && 통로.sender.tab && 통로.sender.tab.id;
    if (탭 !== undefined && 탭 !== null) {
      Promise.resolve(chrome.tabs.update(탭, { autoDiscardable: false })).catch(() => {});
    }
  } catch (e) { /* 넘어간다 */ }
});

// 패널은 ChatGPT 탭에서만 뜬다. 다른 탭으로 가면 저절로 사라진다.
const 챗주소 = /^https:\/\/(chatgpt\.com|chat\.openai\.com)\//;

// ◆ 기본을 '안 보임' 으로 깔아 둔다.
// manifest 의 default_path 때문에 기본이 '보임' 이라, 우리가 손대지 못한 탭
// (확장을 새로고침하기 전부터 열려 있던 탭, 방금 만든 탭)은 그 기본을 그대로 써서
// 구글이든 어디든 패널이 떠 있었다.
async function 기본은안보이게() {
  if (!chrome.sidePanel) return;
  try {
    await chrome.sidePanel.setOptions({ enabled: false });
  } catch (e) {
    console.warn('[로컬에이전트] 기본값 설정 실패:', e);
  }
}

// 이미 열려 있는 탭을 한 번 훑어 제자리를 잡아 준다.
async function 열린탭전부맞추기() {
  try {
    for (const 탭 of await chrome.tabs.query({})) {
      await 탭에맞추기(탭.id, 탭.url || 탭.pendingUrl);
    }
  } catch (e) { /* 넘어간다 */ }
}

async function 탭에맞추기(탭아이디, 주소) {
  if (!chrome.sidePanel) return;
  if (탭아이디 === undefined) return;
  const 챗인가 = 챗주소.test(주소 || '');
  try {
    await chrome.sidePanel.setOptions({
      tabId: 탭아이디,
      path: 'panel.html',
      enabled: 챗인가,
    });
  } catch (e) { /* 닫힌 탭이면 그냥 넘어간다 */ }
}

chrome.tabs.onUpdated.addListener((탭아이디, 바뀐것, 탭) => {
  if (바뀐것.url || 바뀐것.status === 'complete') 탭에맞추기(탭아이디, 탭.url);
});

// 새로 만든 탭은 주소가 아직 없을 수 있다. 일단 안 보이게 해 둔다.
chrome.tabs.onCreated.addListener((탭) => {
  탭에맞추기(탭.id, 탭.url || 탭.pendingUrl);
});

// 서비스 워커가 살아날 때마다 기본값을 다시 깔고 열린 탭을 훑는다.
// (서비스 워커는 자주 잠들었다 깨므로 한 번만 해서는 모자라다)
(async function 자리잡기() {
  await 기본은안보이게();
  await 열린탭전부맞추기();
})();

chrome.runtime.onStartup.addListener(async () => {
  await 기본은안보이게();
  await 열린탭전부맞추기();
});

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const 탭 = await chrome.tabs.get(tabId);
    탭에맞추기(tabId, 탭.url);
  } catch (e) { /* 넘어간다 */ }
});

// 확장을 새로 켰을 때 이미 열려 있던 탭들에도 한 번 맞춰 준다.
chrome.tabs.query({}).then((탭들) => {
  for (const 탭 of 탭들) 탭에맞추기(탭.id, 탭.url);
}).catch(() => {});

// 단축키로도 연다.
if (chrome.commands) chrome.commands.onCommand.addListener(async (이름) => {
  if (이름 !== '창토글') return;
  const [탭] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (탭 && 탭.windowId !== undefined) {
    try {
      if (chrome.sidePanel) await chrome.sidePanel.open({ windowId: 탭.windowId });
      else if (chrome.sidebarAction) await chrome.sidebarAction.open();
    } catch (e) {
      console.warn('[로컬에이전트] 사이드 패널을 못 열었습니다:', e);
    }
  }
});

async function 방나무(방번호 = '') {
  const 주소 = 방번호 ? 브리지 + '/rooms?방=' + encodeURIComponent(방번호) : 브리지 + '/rooms';
  const 응답 = await fetch(주소);
  return await 응답.json();
}

async function 보내기(길, 몸통) {
  const 응답 = await fetch(브리지 + 길, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(몸통 || {}),
  });
  return await 응답.json();
}

async function 허락처리(밭, 허용) {
  const 응답 = await fetch(브리지 + '/grant', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 밭: 밭, 허용: 허용 }),
  });
  return await 응답.json();
}

async function 받아오기목록() {
  const 응답 = await fetch(브리지 + '/installs');
  return await 응답.json();
}

async function 받아오기처리(열쇠, 허용, 그만) {
  // 그만 = 눈·손 허가를 거둔다(번호, 빈 글이면 전부)
  const 응답 = await fetch(브리지 + '/install', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(그만 !== undefined ? { 그만: 그만 } : { 열쇠: 열쇠, 허용: 허용 }),
  });
  return await 응답.json();
}

// ── 서버 자동 켜기 ─────────────────────────────────────────────
// 사람이 서버를 따로 켜지 않아도 되게 한다. 서버에 닿지 못하면
// Native Messaging 으로 서버/자동켜기/agent_host 를 불러 켜 달라고 하고,
// 켜지면 원래 하려던 요청을 한 번 더 보낸다.
//   등록은 한 번만: python 도구▸자동켜기등록.py

const 자동켜기이름 = 'com.local_agent.server';
const 깨움실패쉼ms = 15000;       // 실패했으면 이만큼은 다시 안 두드린다
let 깨우는중 = null;              // 여러 요청이 동시에 와도 한 번만 켠다
let 마지막깨움실패 = { 때: 0, 답: null };

function 서버깨우기() {
  if (깨우는중) return 깨우는중;
  if (마지막깨움실패.답 && Date.now() - 마지막깨움실패.때 < 깨움실패쉼ms) {
    return Promise.resolve(마지막깨움실패.답);
  }

  깨우는중 = new Promise((풀기) => {
    try {
      chrome.runtime.sendNativeMessage(자동켜기이름, { 짓: '켜기' }, (답) => {
        const 틀림 = chrome.runtime.lastError;
        if (틀림) {
          const 글 = 틀림.message || '';
          // 크롬이 주는 말: 'Specified native messaging host not found.'
          //                 'Access to the specified native messaging host is forbidden.'
          풀기({ 됨: false, 등록안됨: /not found|forbidden/i.test(글), 탈: 글 });
          return;
        }
        풀기(답 || { 됨: false, 탈: '자동 켜기가 답을 안 했습니다.' });
      });
    } catch (e) {
      풀기({ 됨: false, 탈: e.message });
    }
  }).then((결과) => {
    깨우는중 = null;
    마지막깨움실패 = 결과.됨 ? { 때: 0, 답: null } : { 때: Date.now(), 답: 결과 };
    return 결과;
  });
  return 깨우는중;
}

function 켜기실패말(깸, 원래탈) {
  if (깸 && 깸.등록안됨) {
    return '서버가 꺼져 있고, 자동 켜기가 등록돼 있지 않습니다. '
         + '프로젝트 폴더에서 Windows는 python 도구/자동켜기등록.py, '
         + 'Linux는 python3 도구/자동켜기등록_리눅스.py 를 실행하세요.';
  }
  return '서버를 켜지 못했습니다: ' + ((깸 && 깸.탈) || 원래탈 || '알 수 없음');
}

async function 처리(메시지, 보낸이) {
  if (메시지.종류 === '도구실행') {
    // 어느 방에서 부르는지 같이 보낸다. 창마다 제 방이 따로다.
    return await 도구실행({ ...메시지.요청, 방번호: 메시지.방번호 || '' });
  } else if (메시지.종류 === '서버확인') {
    return await 서버확인();
  } else if (메시지.종류 === '등급바꾸기') {
    return await 등급바꾸기(메시지.등급, 메시지.모드);
  } else if (메시지.종류 === '대화남기기') {
    return await 대화남기기(메시지.몸통);
  } else if (메시지.종류 === '계획보기') {
    return await 계획보기(메시지.방 || '');
  } else if (메시지.종류 === '방나무') {
    return await 방나무(메시지.방 || '');
  } else if (메시지.종류 === '폴더고르기') {
    return await 보내기('/pick-folder', { 처음자리: 메시지.처음자리 || '', 묶음: 메시지.묶음 || '' });
  } else if (메시지.종류 === '폴더짓') {
    return await 보내기('/folder', 메시지.몸통);
  } else if (메시지.종류 === '방짓') {
    return await 보내기('/room', 메시지.몸통);
  } else if (메시지.종류 === '칸보기') {
    return await 보내기('/dir', 메시지.몸통 || {});
  } else if (메시지.종류 === '대화방') {
    return await 보내기('/room-of-chat', 메시지.몸통 || {});
  } else if (메시지.종류 === '대화남기기2') {
    return await 보내기('/chat', 메시지.몸통);
  } else if (메시지.종류 === '일꾼') {
    return await 보내기('/workers', 메시지.몸통 || {});
  } else if (메시지.종류 === '사이트') {
    return await 보내기('/sites', 메시지.몸통 || {});
  } else if (메시지.종류 === '계획짓') {
    return await 보내기('/plan', 메시지.몸통 || {});
  } else if (메시지.종류 === '현황') {
    return await 보내기('/board', 메시지.몸통 || {});
  } else if (메시지.종류 === '일꾼탭열기') {
    // 대장 탭 옆에 뒤로 연다(대장 탭은 그대로 앞에). 탭 번호 ↔ 일꾼 번호를 적어 둔다.
    const 탭 = await chrome.tabs.create({ url: 메시지.주소, active: false });
    await chrome.storage.local.set({ ['일꾼탭:' + 탭.id]: 메시지.번호 });
    return { 됨: true, 탭: 탭.id };
  } else if (메시지.종류 === '일꾼탭닫기') {
    // 대장이 결과를 받았다 — 일꾼 탭을 닫아 탭이 쌓이지 않게(기록은 일꾼 방에 남는다)
    const 모두 = await chrome.storage.local.get(null);
    for (const 열쇠 of Object.keys(모두 || {})) {
      if (열쇠.indexOf('일꾼탭:') === 0 && 모두[열쇠] === 메시지.번호) {
        const 탭 = Number(열쇠.slice(4));
        try { await chrome.tabs.remove(탭); } catch (e) { /* 이미 닫힘 */ }
        await chrome.storage.local.remove(열쇠);
      }
    }
    return { 됨: true };
  } else if (메시지.종류 === '내일꾼') {
    // 일꾼 탭이 뜨면 '내가 일꾼이냐' 묻는다. 보낸 탭 번호로 찾는다.
    const 탭 = 보낸이 && 보낸이.tab && 보낸이.tab.id;
    if (탭 === undefined || 탭 === null) return { 됨: true, 번호: '' };
    const 받은것 = await chrome.storage.local.get('일꾼탭:' + 탭);
    return { 됨: true, 번호: (받은것 && 받은것['일꾼탭:' + 탭]) || '' };
  } else if (메시지.종류 === '압축') {
    return await 보내기('/compact', 메시지.몸통 || {});
  } else if (메시지.종류 === '프로젝트이름') {
    return await 보내기('/project-name', 메시지.몸통 || {});
  } else if (메시지.종류 === '넘김') {
    return await 보내기('/handoff', 메시지.몸통 || {});
  } else if (메시지.종류 === '예약') {
    return await 보내기('/reminders', 메시지.몸통 || {});
  } else if (메시지.종류 === '허락처리') {
    return await 허락처리(메시지.밭, 메시지.허용);
  } else if (메시지.종류 === '받아오기목록') {
    return await 받아오기목록();
  } else if (메시지.종류 === '받아오기처리') {
    return await 받아오기처리(메시지.열쇠, 메시지.허용, 메시지.그만);
  } else {
    return { success: false, error: '모르는 메시지 종류: ' + 메시지.종류 };
  }
}

// 일꾼 탭을 닫으면 짝 기록을 지운다
try {
  if (chrome.tabs.onRemoved) {
    chrome.tabs.onRemoved.addListener((탭) => {
      try { chrome.storage.local.remove('일꾼탭:' + 탭); } catch (e) { /* 넘어간다 */ }
    });
  }
} catch (e) { /* 넘어간다 */ }

chrome.runtime.onMessage.addListener((메시지, 보낸이, 응답보내기) => {
  (async () => {
    let 원래탈 = '';
    try {
      응답보내기(await 처리(메시지, 보낸이));
      return;
    } catch (e) {
      원래탈 = e.message;
    }

    // 서버에 닿지 못했다 → 켜 보고, '꺼져 있던 것을 새로 켰을 때만' 한 번 더 보낸다.
    // 이미 켜져 있었는데 실패한 것이면 요청이 서버에 닿았을 수도 있다.
    // 그때 다시 보내면 같은 일을 두 번 하게 된다(쑥으로 두 번 붙이기 같은).
    const 깸 = await 서버깨우기();
    if (깸.됨 && !깸.이미켜짐) {
      try {
        응답보내기(await 처리(메시지, 보낸이));
        return;
      } catch (e) {
        원래탈 = e.message;
      }
    }

    // 판은 한국어 키(됨·탈)로 보고, 옛 코드는 영어 키(success·error)로 본다. 둘 다 준다.
    // (하나만 줬더니 서버가 꺼졌는데 판이 '고르지 않았습니다' 라고 했다)
    const 탈 = 켜기실패말(깸, 원래탈);
    응답보내기({ success: false, error: 탈, 됨: false, 탈, 서버꺼짐: true,
                 자동켜기등록안됨: !!깸.등록안됨 });
  })();
  return true; // 비동기 응답을 쓰겠다는 표시
});
