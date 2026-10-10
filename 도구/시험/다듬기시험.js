// 화면 다듬기 시험 — 바구니·소쿠리 이름표와, 화면에서 카드로 표시되는 것을 확인한다.
// (진짜 크롬 화면에서 글자가 그대로 읽히는지는 미리보기 도구로 따로 본다)
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const 확장칸 = path.join(__dirname, '..', '..', '확장');
let 통과 = 0;
let 실패 = 0;
const 실패목록 = [];
function 확인(이름, 참, 덧붙임) {
  if (참) { 통과 += 1; return; }
  실패 += 1;
  실패목록.push(이름 + (덧붙임 !== undefined ? '  → ' + 덧붙임 : ''));
}

// ── 아주 작은 가짜 DOM : 속성·자식·closest·querySelectorAll 만 흉내 낸다 ──
class 요소 {
  constructor(태그, 속성 = {}, 글 = '') {
    this.tagName = 태그.toUpperCase();
    this.속성 = { ...속성 };
    this.자식 = [];
    this.부모 = null;
    this._글 = 글;
    this.눌림듣개 = [];
  }
  add(자식) { 자식.부모 = this; this.자식.push(자식); return 자식; }
  get parentElement() { return this.부모; }
  get id() { return this.속성.id; }
  set id(v) { this.속성.id = v; }
  get textContent() { return this._글 + this.자식.map((c) => c.textContent).join(''); }
  set textContent(v) { this._글 = v; this.자식 = []; }
  getAttribute(n) { return n in this.속성 ? this.속성[n] : null; }
  setAttribute(n, v) { this.속성[n] = String(v); }
  hasAttribute(n) { return n in this.속성; }
  removeAttribute(n) { delete this.속성[n]; }
  _맞나(선택) {
    for (const 하나 of 선택.split(',').map((s) => s.trim())) {
      let m;
      if ((m = /^\[([\w-가-힣]+)="([^"]*)"\]$/.exec(하나))) { if (this.속성[m[1]] === m[2]) return true; continue; }
      if ((m = /^\[([\w-가-힣]+)\$="([^"]*)"\]$/.exec(하나))) { if ((this.속성[m[1]] || '').endsWith(m[2])) return true; continue; }
      if ((m = /^\[([\w-가-힣]+)\]$/.exec(하나))) { if (m[1] in this.속성) return true; continue; }
      if (/^[a-z]+$/i.test(하나)) { if (this.tagName === 하나.toUpperCase()) return true; continue; }
    }
    return false;
  }
  closest(선택) { for (let e = this; e; e = e.부모) if (e._맞나(선택)) return e; return null; }
  _모두(출력) { for (const c of this.자식) { 출력.push(c); c._모두(출력); } return 출력; }
  querySelectorAll(선택) { return this._모두([]).filter((e) => e._맞나(선택)); }
  appendChild(c) { return this.add(c); }
}
class 문서모양 extends 요소 {
  constructor() {
    super('html');
    this.head = this.add(new 요소('head'));
    this.body = this.add(new 요소('body'));
    this.documentElement = this;
    this.눌림듣개들 = [];
  }
  createElement(태그) { return new 요소(태그); }
  getElementById(id) { return this._모두([]).find((e) => e.속성.id === id) || null; }
  addEventListener(종류, f) { if (종류 === 'click') this.눌림듣개들.push(f); }
  누르기(대상) { const 사건 = { target: 대상 }; this.눌림듣개들.forEach((f) => f(사건)); }
}

function 불러오기() {
  const 상자 = { console };
  const 문맥 = vm.createContext(상자);
  for (const 이름 of ['protocol.js', 'selectors.js', '다듬기.js']) {
    vm.runInContext(fs.readFileSync(path.join(확장칸, 이름), 'utf-8'), 문맥, { filename: 이름 });
  }
  return (식) => vm.runInContext(식, 문맥);
}

const 바구니글 = '【바구니】\n나물 열무\n밭 sim▸evaluate_combat.py\n첫줄 1\n끝줄 90\n【바구니끝】';
const 소쿠리글 = '【소쿠리】\n발신 로컬 에이전트 · 자동 도구 결과 (사용자 행동 아님)\n됨 참\n나물 열무\n밭 sim/evaluate_combat.py\n총줄 100\n【소쿠리끝】';

function 이름표시험() {
  const 돌려 = 불러오기();
  const 이름표 = (식) => 돌려(식);
  globalThis.__글 = null;
  const 부르기 = (함수, 글) => {
    const 상자 = 돌려(`(g => g)`)(null);
    return 돌려(`${함수}(${JSON.stringify(글)})`);
  };
  확인('바구니는 쉬운 우리말 뜻으로 보인다', 부르기('바구니이름표', 바구니글) === '도구 ▸ 내용 보기 · sim/evaluate_combat.py', 부르기('바구니이름표', 바구니글));
  확인('  쓰는 중(끝 표시가 아직 없음)이면 … 이 붙는다', 부르기('바구니이름표', 바구니글.replace('【바구니끝】', '')).endsWith(' …'));
  확인('  나물 줄이 아직 안 나왔으면 "명령 쓰는 중…"', 부르기('바구니이름표', '【바구니】') === '도구 ▸ 명령 쓰는 중…', 부르기('바구니이름표', '【바구니】'));
  확인('  한 코드블록에 여러 개면 "외 N건"', 부르기('바구니이름표', 바구니글 + '\n【바구니】\n나물 가지\n밭 sim\n【바구니끝】').indexOf('외 1건') !== -1);
  확인('  모르는 나물은 이름 그대로', 부르기('바구니이름표', '【바구니】\n나물 무화과\n밭 x\n【바구니끝】').indexOf('무화과') !== -1);
  확인('  불(명령)이나 향(찾을 말)도 대상으로 쓴다', 부르기('바구니이름표', '【바구니】\n나물 도라지\n불 python x.py\n【바구니끝】').indexOf('python x.py') !== -1);
  확인('  아주 긴 대상은 잘라서 …', 부르기('바구니이름표', '【바구니】\n나물 열무\n밭 ' + 'a'.repeat(200) + '\n【바구니끝】').length < 120);
  확인('소쿠리는 결과 ▸ 뜻 · 대상', 부르기('소쿠리이름표', 소쿠리글) === '결과 ▸ 내용 보기 · sim/evaluate_combat.py', 부르기('소쿠리이름표', 소쿠리글));
  확인('  실패한 결과는 · 실패', 부르기('소쿠리이름표', 소쿠리글.replace('됨 참', '됨 거짓')).endsWith('· 실패'));
  확인('  첨부 파일로 간 결과는 파일 이름을 보인다', 부르기('소쿠리이름표', '【소쿠리】\n발신 로컬 에이전트 · 자동 도구 결과\n결과 전체는 첨부 파일 결과_1002.txt 에 있습니다.\n【소쿠리끝】') === '결과 ▸ 첨부 파일 결과_1002.txt', 부르기('소쿠리이름표', '【소쿠리】\n발신 로컬 에이전트\n결과 전체는 첨부 파일 결과_1002.txt 에 있습니다.'));
  확인('  자동 재촉도 알아보기 쉽게', 부르기('소쿠리이름표', '【에이전트 자동 요청】\n앞에 보낸 결과').indexOf('재촉') !== -1);
}

function 화면시험() {
  const 돌려 = 불러오기();
  const 문서 = new 문서모양();
  // ① GPT 답: 설명 글 + 바구니 코드블록
  const 답 = 문서.body.add(new 요소('div', { 'data-chatgpt-search-unit-key': '1:2:assistant' }));
  const 일반 = 답.add(new 요소('p', {}, '먼저 파일을 읽어 볼게요.'));
  const 코드칸 = 답.add(new 요소('div', { 'data-markdown-copy': 'code-block' }));
  코드칸.add(new 요소('div', {}, '일반 텍스트'));            // 머리(언어 이름표)
  const 코드 = 코드칸.add(new 요소('code', {}, 바구니글));
  const 평범한코드칸 = 답.add(new 요소('div', { 'data-markdown-copy': 'code-block' }));
  평범한코드칸.add(new 요소('code', {}, 'print("hello")'));
  // ② 내 말: 소쿠리
  const 내말 = 문서.body.add(new 요소('div', { 'data-chatgpt-search-unit-key': '1:3:user' }, 소쿠리글));
  const 사람말 = 문서.body.add(new 요소('div', { 'data-chatgpt-search-unit-key': '2:1:user' }, '그냥 내가 쓴 말이야'));
  // ③ 내 말 안에 바구니 모양이 우연히 있어도(코드블록이어도) 접지 않는다
  const 사람코드칸 = 사람말.add(new 요소('div', { 'data-markdown-copy': 'code-block' }));
  사람코드칸.add(new 요소('code', {}, 바구니글));

  돌려('화면다듬기')(문서);
  확인('스타일이 한 번 들어간다', 문서.getElementById('gla-다듬기-스타일') !== null);
  확인('바구니 코드블록이 카드가 된다', 코드칸.getAttribute('data-gla') === '바구니' && 코드칸.getAttribute('data-gla-이름표') === '도구 ▸ 내용 보기 · sim/evaluate_combat.py', 코드칸.getAttribute('data-gla-이름표'));
  확인('  설명 글은 건드리지 않는다', 일반.getAttribute('data-gla') === null);
  확인('  바구니가 아닌 코드블록은 그대로', 평범한코드칸.getAttribute('data-gla') === null);
  확인('내가 자동으로 보낸 소쿠리가 카드가 된다', 내말.getAttribute('data-gla') === '소쿠리' && 내말.getAttribute('data-gla-이름표').startsWith('결과 ▸ 내용 보기'));
  확인('  사람이 쓴 평범한 말은 그대로', 사람말.getAttribute('data-gla') === null);
  확인('  사람이 쓴 말 속 바구니 모양 코드블록도 접지 않는다', 사람코드칸.getAttribute('data-gla') === null);

  // 사람이 【소쿠리】 글자를 따와서 말해도(우리 에이전트의 머리말이 없으면) 접지 않는다
  const 따온말 = 문서.body.add(new 요소('div', { 'data-chatgpt-search-unit-key': '3:1:user' }, '이런 【소쿠리】 말이 뭐야?'));
  // 카드가 된 코드블록 안쪽의 pre 는 따로 카드로 만들지 않는다(바깥 상자가 카드)
  const 겹상자 = 문서.body.add(new 요소('div', { 'data-markdown-copy': 'code-block' }));
  const 겹pre = 겹상자.add(new 요소('pre', {}, 바구니글));
  돌려('화면다듬기')(문서);
  확인('  사람이 따온 【소쿠리】 글자는 접지 않는다', 따온말.getAttribute('data-gla') === null);
  확인('  카드가 된 상자 안쪽의 pre 는 따로 카드가 되지 않는다', 겹상자.getAttribute('data-gla') === '바구니' && 겹pre.getAttribute('data-gla') === null);

  // 글은 지우지 않는다(바구니 읽기가 쓰는 글이 그대로 있다)
  확인('원문은 그대로 남아 있다', 코드칸.textContent.indexOf('나물 열무') !== -1 && 내말.textContent.indexOf('나물 열무') !== -1);

  // 여러 번 불러도 같다
  const 앞 = JSON.stringify(코드칸.속성);
  돌려('화면다듬기')(문서);
  돌려('화면다듬기')(문서);
  확인('여러 번 불러도 결과가 같고 스타일이 둘이 되지 않는다', JSON.stringify(코드칸.속성) === 앞 && 문서.head.자식.filter((e) => e.속성.id === 'gla-다듬기-스타일').length === 1);

  // 쓰는 중에 이름표가 바뀐다 (스트리밍)
  코드.textContent = 바구니글.replace('【바구니끝】', '');
  돌려('화면다듬기')(문서);
  확인('쓰는 중이던 바구니가 끝나면 이름표가 바뀐다', 코드칸.getAttribute('data-gla-이름표').endsWith(' …'));
  코드.textContent = 바구니글;
  돌려('화면다듬기')(문서);
  확인('  끝나면 … 이 사라진다', !코드칸.getAttribute('data-gla-이름표').endsWith(' …'));

  // 누르기: 접힘 → 열림, 열린 뒤엔 윗줄(카드 자신)을 눌러야 접힘
  문서.누르기(코드);
  확인('접힌 카드는 안쪽을 눌러도 열린다', 코드칸.hasAttribute('data-gla-열림'));
  문서.누르기(코드);
  확인('  열린 카드의 안쪽(원문)을 눌러도 접히지 않는다', 코드칸.hasAttribute('data-gla-열림'));
  문서.누르기(코드칸);
  확인('  열린 카드의 윗줄(카드 자신)을 누르면 접힌다', !코드칸.hasAttribute('data-gla-열림'));
  문서.누르기(일반);
  확인('카드가 아닌 곳을 눌러도 아무 일 없다', !일반.hasAttribute('data-gla-열림'));

  // 바구니·소쿠리 둘 다 없는 화면에서는 아무것도 안 한다
  const 빈문서 = new 문서모양();
  빈문서.body.add(new 요소('div', { 'data-chatgpt-search-unit-key': '1:1:assistant' }, '안녕'));
  let 터짐 = null;
  try { 돌려('화면다듬기')(빈문서); } catch (e) { 터짐 = e.message; }
  확인('바구니가 없는 화면에서도 터지지 않는다', 터짐 === null, 터짐);
  확인('  아무 표시도 안 붙는다', 빈문서.querySelectorAll('[data-gla]').length === 0);
}

function 연결시험() {
  const 매니페스트 = JSON.parse(fs.readFileSync(path.join(확장칸, 'manifest.json'), 'utf-8'));
  const 파일들 = 매니페스트.content_scripts[0].js;
  확인('manifest 에 다듬기.js 가 content.js 앞에 들어 있다(규약·셀렉터 뒤)',
       파일들.indexOf('다듬기.js') !== -1 && 파일들.indexOf('다듬기.js') < 파일들.indexOf('content.js')
       && 파일들.indexOf('다듬기.js') > 파일들.indexOf('selectors.js') && 파일들.indexOf('다듬기.js') > 파일들.indexOf('protocol.js'), 파일들.join(','));
  const 본체 = fs.readFileSync(path.join(확장칸, 'content.js'), 'utf-8');
  const 검사몸 = 본체.slice(본체.indexOf('async function 검사()'), 본체.indexOf('async function 검사()') + 600);
  확인('content.js 의 검사가 화면다듬기를 부른다(실패해도 검사는 이어 간다)', /try \{[^}]*화면다듬기\(\)[^}]*\} catch/.test(검사몸), 검사몸.slice(0, 300));
}

이름표시험();
화면시험();
연결시험();

if (실패목록.length) {
  console.log('실패한 것:');
  for (const 줄 of 실패목록) console.log('  ✗ ' + 줄);
}
console.log(`통과 ${통과} / 실패 ${실패}`);
process.exit(실패 ? 1 : 0);
