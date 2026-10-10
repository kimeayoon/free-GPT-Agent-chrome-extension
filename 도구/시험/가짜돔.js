// 가짜 DOM — 판(panel.js)을 브라우저 없이 그려 보려고 만든 흉내판.
//
// 진짜 브라우저만큼 할 필요는 없다. 판이 실제로 쓰는 것만 있으면 된다.
//   createElement / appendChild / textContent / className / classList
//   style / onclick / getElementById / hidden / title
//
// 그린 결과를 글로 뽑아 볼 수 있어서(글자뽑기), 무엇이 보이는지 시험에서 확인한다.

// 글자만 담는 쪽. 진짜 DOM 의 텍스트 노드에 해당한다.
// 상태줄처럼 '글자 + 요소 + 글자' 를 섞어 붙이는 곳에서 쓴다.
class 글쪽 {
  constructor(글) {
    this.tagName = '#text';
    this.자식들 = [];
    this.부모 = null;
    this._글 = String(글 == null ? '' : 글);
    this.className = '';
    this.id = '';
    this.style = {};
  }

  get textContent() { return this._글; }
  set textContent(값) { this._글 = String(값 == null ? '' : 값); }

  _칸들() { return []; }
  글자뽑기(깊이 = 0) { return '  '.repeat(깊이) + '"' + this._글 + '"'; }
}

class 요소 {
  constructor(태그) {
    this.tagName = (태그 || 'div').toUpperCase();
    this.자식들 = [];
    this.부모 = null;
    this._글 = '';
    this.className = '';
    this.id = '';
    this.title = '';
    this.hidden = false;
    this.style = {};
    this.onclick = null;
    this.ondblclick = null;
    this.onmousedown = null;
    this.draggable = false;
    this.눌린수 = 0;

    const 나 = this;
    this.classList = {
      add(이름) { if (!나._칸들().includes(이름)) 나.className = (나.className + ' ' + 이름).trim(); },
      remove(이름) { 나.className = 나._칸들().filter((x) => x !== 이름).join(' '); },
      toggle(이름, 켤까) {
        const 있나 = 나._칸들().includes(이름);
        const 켜자 = 켤까 === undefined ? !있나 : !!켤까;
        if (켜자) this.add(이름); else this.remove(이름);
      },
      contains(이름) { return 나._칸들().includes(이름); },
    };
  }

  _칸들() { return this.className.split(/\s+/).filter(Boolean); }

  get lastChild() { return this.자식들[this.자식들.length - 1] || null; }
  get firstChild() { return this.자식들[0] || null; }
  get children() { return this.자식들; }

  // 진짜 DOM 은 글과 자식이 같이 있을 수 있다.
  // (textContent 로 글을 넣은 뒤 자식을 붙여도 글이 안 사라진다)
  // 그래서 글도 자식 하나로 다룬다.
  get textContent() {
    return this._글 + this.자식들.map((c) => c.textContent).join('');
  }
  set textContent(값) {
    this._글 = String(값 == null ? '' : 값);
    this.자식들 = [];
  }

  appendChild(아이) { 아이.부모 = this; this.자식들.push(아이); return 아이; }
  append(...아이들) { for (const a of 아이들) this.appendChild(a); }
  setAttribute(이름, 값) { this[이름] = 값; }
  getAttribute(이름) { return this[이름] === undefined ? null : this[이름]; }
  addEventListener(갈래, 함수) { this['on' + 갈래] = 함수; }
  click() {
    this.눌린수 += 1;
    if (this.onclick) this.onclick({ stopPropagation() {}, preventDefault() {}, target: this });
  }
  getBoundingClientRect() { return { top: 0, left: 0, bottom: 0, right: 0, width: 100, height: 100 }; }
  focus() {}
  scrollIntoView() {}

  // 시험에서 화면을 글로 뽑아 볼 때 쓴다
  글자뽑기(깊이 = 0) {
    const 안 = '  '.repeat(깊이);
    const 내글 = this._글;
    let 줄 = 안 + (this.id ? '#' + this.id : this.tagName.toLowerCase());
    if (this.className) 줄 += '.' + this._칸들().join('.');
    if (this.hidden) 줄 += ' (숨김)';
    if (내글) 줄 += '  "' + 내글 + '"';
    const 아래 = this.자식들.map((c) => c.글자뽑기(깊이 + 1));
    return [줄, ...아래].join('\n');
  }

  모두찾기(조건) {
    const 모음 = [];
    const 훑기 = (것) => {
      if (조건(것)) 모음.push(것);
      for (const c of (것.자식들 || [])) 훑기(c);
    };
    훑기(this);
    return 모음;
  }
}

function 문서만들기(아이디들) {
  const 뿌리 = new 요소('body');
  const 표 = {};
  const 듣개들 = {};                 // 갈래 → 함수들 (시험이 쏘아 볼 수 있게)
  for (const 아이디 of 아이디들) {
    const 것 = new 요소('div');
    것.id = 아이디;
    표[아이디] = 것;
    뿌리.appendChild(것);
  }
  return {
    뿌리,
    표,
    듣개들,
    문서: {
      getElementById: (아이디) => 표[아이디] || null,
      createElement: (태그) => new 요소(태그),
      createTextNode: (글) => new 글쪽(글),
      addEventListener: (갈래, 함수) => { (듣개들[갈래] = 듣개들[갈래] || []).push(함수); },
      querySelector: () => null,
      querySelectorAll: () => [],
      body: 뿌리,
    },
  };
}

module.exports = { 요소, 글쪽, 문서만들기 };
