// 배경 시험 — background.js 의 '서버 자동 켜기' 를 진짜 소스로 돌려 본다.
//
// 돌리는 법:  node 도구▸시험▸배경시험.js
//
// 보는 것
//   · 서버가 꺼져 있으면 자동 켜기를 부르고, 켜지면 원래 요청을 다시 보낸다
//   · 이미 켜져 있었는데 실패한 것이면 다시 안 보낸다 (같은 일을 두 번 하면 안 된다)
//   · 등록이 안 돼 있으면 무엇을 하라고 말해 준다
//   · 요청이 한꺼번에 몰려도 자동 켜기는 한 번만 부른다
//   · 켜기에 실패했으면 잠시 동안은 다시 안 두드린다

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const 확장칸 = path.join(__dirname, '..', '..', '확장');

let 통과 = 0;
let 실패 = 0;
const 실패목록 = [];

function 확인(이름, 조건, 덧붙임) {
  if (조건) { 통과 += 1; return; }
  실패 += 1;
  실패목록.push(이름 + (덧붙임 ? '  → ' + 덧붙임 : ''));
}

const 잠깐 = (ms) => new Promise((r) => setTimeout(r, ms));
const 빈듣개 = () => ({ addListener: () => {} });

// 설정
//   서버살음   : 처음에 서버가 켜져 있나
//   켜기답     : 자동 켜기가 돌려줄 답 (함수면 불릴 때마다 계산)
//   켜기틀림   : 크롬이 lastError 로 줄 말 (등록 안 됨 등)
//   켜기걸림ms : 자동 켜기가 답하기까지 걸리는 시간
function 판차리기(설정 = {}) {
  const 기록 = { fetch: [], 켜기부름: 0 };
  const 판 = { 서버살음: !!설정.서버살음, 기록 };
  let 받는이 = null;

  const 가짜fetch = async (주소, 옵션) => {
    기록.fetch.push({ 주소, 몸: 옵션 && 옵션.body });
    if (!판.서버살음) throw new TypeError('Failed to fetch');
    if (설정.켜진뒤에도실패) throw new TypeError('Failed to fetch');
    return { json: async () => ({ 됨: true, 온곳: 주소 }) };
  };

  const chrome = {
    runtime: {
      lastError: undefined,
      onMessage: { addListener: (f) => { 받는이 = f; } },
      onConnect: { addListener: (f) => { 판.통로받이 = f; } },
      onInstalled: 빈듣개(),
      onStartup: 빈듣개(),
      sendNativeMessage: (이름, 쪽지, 돌려줄것) => {
        기록.켜기부름 += 1;
        기록.켜기이름 = 이름;
        setTimeout(() => {
          if (설정.켜기틀림) {
            chrome.runtime.lastError = { message: 설정.켜기틀림 };
            돌려줄것(undefined);
            chrome.runtime.lastError = undefined;
            return;
          }
          const 답 = typeof 설정.켜기답 === 'function' ? 설정.켜기답(판) : 설정.켜기답;
          돌려줄것(답);
        }, 설정.켜기걸림ms || 5);
      },
    },
    sidePanel: {
      setPanelBehavior: () => Promise.resolve(),
      setOptions: () => Promise.resolve(),
      open: () => Promise.resolve(),
    },
    tabs: {
      query: () => Promise.resolve([]),
      get: () => Promise.resolve({}),
      create: async (값) => { 기록.연탭 = (기록.연탭 || []).concat(값); return { id: 77 }; },
      update: (id, 값) => {
        if (설정.탭고침터짐) throw new Error('탭이 없습니다');
        기록.탭고침 = (기록.탭고침 || []).concat({ id, 값 });
        return 설정.탭고침거절 ? Promise.reject(new Error('닫힌 탭')) : Promise.resolve({ id });
      },
      onUpdated: 빈듣개(), onCreated: 빈듣개(), onActivated: 빈듣개(), onRemoved: 빈듣개(),
    },
    storage: {
      local: {
        _것: {},
        get: async function (k) { return { [k]: this._것[k] }; },
        set: async function (값) { Object.assign(this._것, 값); },
        remove: async function (k) { delete this._것[k]; },
      },
    },
    commands: { onCommand: 빈듣개() },
  };

  const 상자 = {
    console: { log: () => {}, warn: () => {}, error: () => {} },
    setTimeout, clearTimeout, setInterval, clearInterval,
    Date, JSON, Math, Set, Map, Promise, Object, Array, String, Number, TypeError,
    fetch: 가짜fetch, chrome,
  };
  상자.globalThis = 상자;
  const 문맥 = vm.createContext(상자);
  vm.runInContext(fs.readFileSync(path.join(확장칸, 'background.js'), 'utf-8'), 문맥,
                  { filename: 'background.js' });

  판.묻기 = (쪽지, 보낸이 = {}) => new Promise((풀기) => {
    받는이(쪽지, 보낸이, 풀기);
  });
  return 판;
}

// ── 시험들 ────────────────────────────────────────────────────

async function 시험_꺼져있으면_켜고_다시_보낸다() {
  const 판 = 판차리기({
    서버살음: false,
    켜기답: (판) => { 판.서버살음 = true; return { 됨: true, 이미켜짐: false, 어떻게: 'breakaway' }; },
  });
  const 답 = await 판.묻기({ 종류: '폴더고르기' });

  확인('꺼져 있으면 자동 켜기를 부른다', 판.기록.켜기부름 === 1, '부른 수 ' + 판.기록.켜기부름);
  확인('  등록한 이름으로 부른다', 판.기록.켜기이름 === 'com.local_agent.server', 판.기록.켜기이름);
  확인('  켜지면 원래 요청을 다시 보낸다', 판.기록.fetch.length === 2,
       'fetch 수 ' + 판.기록.fetch.length);
  확인('  그 답을 그대로 돌려준다', 답 && 답.됨 === true && /pick-folder/.test(답.온곳),
       JSON.stringify(답));
}

async function 시험_켜져있었으면_다시_안_보낸다() {
  // 서버는 살아 있는데 요청이 실패한 경우. 요청이 서버에 닿았을 수도 있다.
  const 판 = 판차리기({
    서버살음: true,
    켜진뒤에도실패: true,
    켜기답: { 됨: true, 이미켜짐: true },
  });
  const 답 = await 판.묻기({ 종류: '도구실행', 요청: { 나물: '쑥', 밭: 'a.txt' } });

  확인('이미 켜져 있었으면 요청을 다시 안 보낸다 (두 번 붙이기 막기)',
       판.기록.fetch.length === 1, 'fetch 수 ' + 판.기록.fetch.length);
  확인('  실패라고 알린다', 답 && 답.됨 === false, JSON.stringify(답));
}

async function 시험_등록이_안되어_있으면_할일을_말한다() {
  const 판 = 판차리기({
    서버살음: false,
    켜기틀림: 'Specified native messaging host not found.',
  });
  const 답 = await 판.묻기({ 종류: '서버확인' });

  확인('등록 안 됨을 알아챈다', 답 && 답.자동켜기등록안됨 === true, JSON.stringify(답));
  확인('  무엇을 하라고 말해 준다', 답 && /자동켜기등록/.test(답.탈), 답 && 답.탈);
  확인('  판이 읽는 한국어 키가 있다', 답 && 답.됨 === false && 답.서버꺼짐 === true);
  확인('  옛 영어 키도 있다', 답 && 답.success === false && !!답.error);
}

async function 시험_몰려와도_한번만_켠다() {
  const 판 = 판차리기({
    서버살음: false,
    켜기걸림ms: 60,
    켜기답: (판) => { 판.서버살음 = true; return { 됨: true, 이미켜짐: false }; },
  });
  const 답들 = await Promise.all([
    판.묻기({ 종류: '서버확인' }),
    판.묻기({ 종류: '방나무' }),
    판.묻기({ 종류: '계획보기' }),
  ]);

  확인('요청 셋이 몰려도 자동 켜기는 한 번만 부른다', 판.기록.켜기부름 === 1,
       '부른 수 ' + 판.기록.켜기부름);
  확인('  셋 다 답을 받는다', 답들.every((d) => d && d.됨 === true), JSON.stringify(답들));
}

async function 시험_실패하면_잠시_쉰다() {
  const 판 = 판차리기({ 서버살음: false, 켜기답: { 됨: false, 탈: '안 떴습니다' } });
  await 판.묻기({ 종류: '서버확인' });
  await 판.묻기({ 종류: '서버확인' });
  await 판.묻기({ 종류: '서버확인' });

  확인('켜기에 실패하면 곧바로 또 두드리지 않는다 (판이 5초마다 물어도)',
       판.기록.켜기부름 === 1, '부른 수 ' + 판.기록.켜기부름);
}

async function 시험_살아있으면_켜기를_안_부른다() {
  const 판 = 판차리기({ 서버살음: true });
  await 판.묻기({ 종류: '서버확인' });
  await 판.묻기({ 종류: '방나무' });
  확인('서버가 살아 있으면 자동 켜기를 아예 안 부른다', 판.기록.켜기부름 === 0,
       '부른 수 ' + 판.기록.켜기부름);
}

async function 시험_일꾼탭을_열고_누구인지_알려준다() {
  const 판 = 판차리기({ 서버살음: true });
  const 답 = await 판.묻기({ 종류: '일꾼탭열기', 번호: 'w1', 주소: 'https://chatgpt.com/g/g-p-1/project' });
  확인('일꾼 탭은 대장 탭을 가리지 않게 뒤로 연다', 답 && 답.됨 && 판.기록.연탭 && 판.기록.연탭[0].active === false
       && 판.기록.연탭[0].url === 'https://chatgpt.com/g/g-p-1/project', JSON.stringify(판.기록.연탭));
  const 누구 = await 판.묻기({ 종류: '내일꾼' }, { tab: { id: 77 } });
  확인('  그 탭이 물으면 일꾼 번호를 알려 준다', 누구 && 누구.번호 === 'w1', JSON.stringify(누구));
  const 남 = await 판.묻기({ 종류: '내일꾼' }, { tab: { id: 12 } });
  확인('  다른 탭에는 빈 번호', 남 && 남.번호 === '', JSON.stringify(남));
}

async function 시험_권한이_선언돼_있다() {
  const 설명 = JSON.parse(fs.readFileSync(path.join(확장칸, 'manifest.json'), 'utf-8'));
  확인('manifest 에 nativeMessaging 권한이 있다',
       (설명.permissions || []).includes('nativeMessaging'), JSON.stringify(설명.permissions));
  // 완료 알림은 새 권한(notifications) 없이 한다 — 권한이 늘면 사용자가 확장을 다시 승인해야 한다
  확인('  알림 권한을 새로 요구하지 않는다(소리·글·아이콘 표시로 알린다)',
       !(설명.permissions || []).includes('notifications'), JSON.stringify(설명.permissions));
}

function 가짜통로(이름, 탭) {
  return { name: 이름, sender: 탭 === undefined ? {} : { tab: { id: 탭 } }, postMessage: () => {},
           onDisconnect: { addListener: () => {} } };
}

async function 시험_박동을_받는_탭은_크롬이_못_버리게_한다() {
  const 판 = 판차리기({ 서버살음: true });
  판.통로받이(가짜통로('심장', 42));
  await 잠깐(10);
  확인('박동 통로를 연 탭은 메모리 절약으로 버려지지 않게(autoDiscardable=false) 해 둔다',
       (판.기록.탭고침 || []).length === 1 && 판.기록.탭고침[0].id === 42 && 판.기록.탭고침[0].값.autoDiscardable === false,
       JSON.stringify(판.기록.탭고침));
  판.통로받이(가짜통로('다른통로', 43));
  판.통로받이(가짜통로('심장'));                       // 탭 번호가 없는 통로(확장 안쪽 페이지 등)
  await 잠깐(10);
  확인('  다른 이름의 통로나 탭 번호가 없는 통로는 건드리지 않는다', (판.기록.탭고침 || []).length === 1);
  const 거절 = 판차리기({ 서버살음: true, 탭고침거절: true });
  거절.통로받이(가짜통로('심장', 5));
  await 잠깐(10);
  확인('  닫힌 탭이라 크롬이 거절해도 조용히 넘어간다(박동은 계속 뛴다)', (거절.기록.탭고침 || []).length === 1);
  const 터짐 = 판차리기({ 서버살음: true, 탭고침터짐: true });
  let 던짐 = false;
  try { 터짐.통로받이(가짜통로('심장', 6)); } catch (e) { 던짐 = true; }
  확인('  탭 고치기가 던져도 통로 연결은 멀쩡하다', 던짐 === false);
}

async function 시험_사이트_허용은_서버_sites_길로_간다() {
  const 판 = 판차리기({ 서버살음: true });
  const 답 = await 판.묻기({ 종류: '사이트', 몸통: { 짓: '허용', 출처: 'https://my-tool.example', 등급: '보기' } });
  const 부름 = 판.기록.fetch.filter((f) => f.주소.indexOf('/sites') !== -1);
  확인('판이 정하는 웹사이트 허용은 서버의 /sites 길로 간다', 부름.length === 1 && 답 && 답.됨, JSON.stringify(판.기록.fetch));
  const 몸 = JSON.parse(부름[0].몸);
  확인('  짓·출처·등급이 그대로 간다', 몸.짓 === '허용' && 몸.출처 === 'https://my-tool.example' && 몸.등급 === '보기', 부름[0].몸);
}

async function 시험_현황은_서버_board_길로_간다() {
  const 판 = 판차리기({ 서버살음: true });
  const 답 = await 판.묻기({ 종류: '현황', 몸통: { 방: 'r1', 짓: '목록' } });
  const 부름 = 판.기록.fetch.filter((f) => f.주소.indexOf('/board') !== -1);
  확인('판이 묻는 현황은 서버의 /board 길로 간다', 부름.length === 1 && 답 && 답.됨, JSON.stringify(판.기록.fetch));
  확인('  방 번호와 짓이 그대로 간다', 부름.length === 1 && JSON.parse(부름[0].몸).방 === 'r1' && JSON.parse(부름[0].몸).짓 === '목록', 부름[0] && 부름[0].몸);
}

async function 시험_허용과_그만은_서버_install_길로_간다() {
  const 판 = 판차리기({ 서버살음: true });
  await 판.묻기({ 종류: '받아오기처리', 열쇠: '허가::눈::VALORANT', 허용: true });
  await 판.묻기({ 종류: '받아오기처리', 그만: '3' });
  await 판.묻기({ 종류: '받아오기처리', 그만: '' });
  const 부름 = 판.기록.fetch.filter((f) => f.주소.indexOf('/install') !== -1).map((f) => JSON.parse(f.몸));
  확인('허용은 열쇠와 허용으로 간다', 부름.length === 3 && 부름[0].열쇠 === '허가::눈::VALORANT' && 부름[0].허용 === true, JSON.stringify(부름));
  확인('  눈·손 허가를 거두는 그만은 번호만 간다(열쇠·허용 없이)', 부름[1].그만 === '3' && 부름[1].열쇠 === undefined && 부름[1].허용 === undefined, JSON.stringify(부름[1]));
  확인('  번호가 빈 그만은 전부 거두라는 뜻으로 빈 글이 그대로 간다', 부름[2].그만 === '', JSON.stringify(부름[2]));
}

async function 시험_권한_모드는_서버_mode_길로_간다() {
  const 판 = 판차리기({ 서버살음: true });
  await 판.묻기({ 종류: '등급바꾸기', 모드: '수동' });
  await 판.묻기({ 종류: '등급바꾸기', 등급: '보기' });
  const 부름 = 판.기록.fetch.filter((f) => f.주소.indexOf('/mode') !== -1).map((f) => JSON.parse(f.몸));
  확인('모드를 고르면 서버 /mode 로 모드가 간다', 부름.length === 2 && 부름[0].모드 === '수동' && 부름[0].등급 === undefined, JSON.stringify(부름));
  확인('  옛 방식(등급)도 그대로 된다', 부름[1].등급 === '보기' && 부름[1].모드 === undefined, JSON.stringify(부름[1]));
}

// ── 돌리기 ────────────────────────────────────────────────────

(async function 다돌리기() {
  const 시험들 = [
    시험_꺼져있으면_켜고_다시_보낸다,
    시험_켜져있었으면_다시_안_보낸다,
    시험_등록이_안되어_있으면_할일을_말한다,
    시험_몰려와도_한번만_켠다,
    시험_실패하면_잠시_쉰다,
    시험_살아있으면_켜기를_안_부른다,
    시험_권한이_선언돼_있다,
    시험_일꾼탭을_열고_누구인지_알려준다,
    시험_현황은_서버_board_길로_간다,
    시험_사이트_허용은_서버_sites_길로_간다,
    시험_박동을_받는_탭은_크롬이_못_버리게_한다,
    시험_허용과_그만은_서버_install_길로_간다,
    시험_권한_모드는_서버_mode_길로_간다,
  ];
  for (const 하나 of 시험들) {
    try {
      await 하나();
    } catch (e) {
      실패 += 1;
      실패목록.push(하나.name + '  → 터짐: ' + e.message);
    }
  }
  console.log('');
  if (실패목록.length) {
    console.log('실패한 것:');
    for (const 줄 of 실패목록) console.log('  ✗ ' + 줄);
    console.log('');
  }
  console.log(`통과 ${통과} / 실패 ${실패}`);
  process.exit(실패 ? 1 : 0);
})();
