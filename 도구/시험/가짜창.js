// 가짜 ChatGPT 창 — 브라우저 없이 확장 코드를 돌려 보려고 만든 흉내판.
//
// 진짜 크롬 없이도 content.js 가 하는 일을 그대로 시켜 볼 수 있다.
//   · 답변이 생기고 지워지는 것
//   · 입력창에 글이 들어가고 전송 단추가 눌리는 것
//   · 스트리밍 중인 것
//   · 탭이 가려진 것
//
// 진짜 DOM 이 아니라 필요한 만큼만 흉내 낸다. 그래서 빠르고, 무엇이 왜 깨졌는지 보인다.

class 가짜요소 {
  constructor(속성 = {}) {
    // Object.assign 은 getter 를 '그때 한 번 읽은 값' 으로 복사해 버린다.
    // 그러면 innerText 가 처음 값에 얼어붙어, 글을 넣어도 안 들어간 것처럼 보인다.
    // 그래서 속성 설명을 그대로 옮겨 붙인다.
    for (const 이름 of Object.keys(속성)) {
      const 설명 = Object.getOwnPropertyDescriptor(속성, 이름);
      Object.defineProperty(this, 이름, 설명);
    }
    this.자식 = [];
    this.눌린수 = 0;
    this.보낸사건 = [];
  }
  click() { this.눌린수 += 1; if (this.누르면) this.누르면(); }
  focus() {}
  getAttribute(이름) { return this.속성 && this.속성[이름] !== undefined ? this.속성[이름] : null; }
  dispatchEvent(사건) {
    this.보낸사건.push(사건);
    if (this.붙임 && this.붙임[사건.type]) this.붙임[사건.type](사건);
    return true;
  }
  querySelectorAll() { return []; }
  querySelector() { return null; }
}

class 가짜창 {
  constructor() {
    this.답변들 = [];          // 문자열 목록
    this.스트리밍 = false;
    this.보낸것 = [];          // 실제로 전송된 글
    this.입력창글 = '';
    this.가려짐 = false;
    this.주소 = '/c/chat-1111';
    this.제목 = '시험 대화';

    const 창 = this;

    this.입력창요소 = new 가짜요소({
      tagName: 'DIV',
      isContentEditable: true,
      get innerText() { return 창.입력창글; },
      붙임: {
        paste: (사건) => { 창.입력창글 = 사건.clipboardData.getData('text/plain'); },
      },
    });

    this.전송단추 = new 가짜요소({
      disabled: false,
      속성: {},
      누르면: () => {
        if (!창.입력창글.trim()) return;      // 빈 칸이면 아무 일도 없다
        창.보낸것.push(창.입력창글);
        if (창.첨부들 && 창.첨부들.length) { 창.보낸첨부.push(...창.첨부들); 창.첨부들 = []; }
        // 느린 화면: 보내지긴 했는데 입력칸 글이 한참 남아 있다(긴 대화에서 실제로 그랬다)
        if (창.느림) {
          if (창.느림 === '내말뜸') 창.사람말붙이기(창.입력창글, 'u-' + 창.보낸것.length);
          if (창.느림 === '쓰기시작') 창.스트리밍 = true;
          return;
        }
        창.입력창글 = '';
      },
    });
  }

  // ── 메시지 편집 흉내 (2026-09-30 형님 Chrome 에서 본 그대로) ──
  // 연필을 누르면 [취소](type=button)·[보내기](type=submit, 글자 '보내기')가 생긴다.
  편집칸만들기() {
    this.편집중 = false;
    this.편집재전송수 = 0;
    return this;
  }
  편집단추() {
    const 창 = this;
    return [new 가짜요소({ getAttribute: (k) => (k === 'aria-label' ? '메시지 편집' : null),
                           누르면: () => { 창.편집중 = true; } })];
  }
  편집칸단추들() {
    const 창 = this;
    if (!this.편집중) return [];
    return [
      new 가짜요소({ innerText: '취소', getAttribute: (k) => (k === 'type' ? 'button' : null),
                     누르면: () => { 창.편집중 = false; } }),
      new 가짜요소({ innerText: '보내기', getAttribute: (k) => (k === 'type' ? 'submit' : null),
                     누르면: () => { 창.편집중 = false; 창.편집재전송수 += 1; } }),
    ];
  }

  // ── 추론 수준 흉내 (2026-09-29 형님 Chrome 에서 본 그대로) ──
  // 단추 글자 = 지금 수준, 열려 있는 동안엔 '추론 수준'. Enter 로 열고 ← → 로 옮기고 Esc 로 닫는다.
  추론칸만들기(처음 = 0) {
    const 창 = this;
    this.추론이름들 = ['Instant', 'Medium', 'High'];
    this.추론값 = 처음;
    this.추론열림 = false;
    this.추론연수 = 0;
    this.추론단추 = new 가짜요소({
      get innerText() { return 창.추론열림 ? '추론 수준' : 창.추론이름들[창.추론값]; },
      붙임: { keydown: (사건) => { if (사건.key === 'Enter') { 창.추론열림 = true; 창.추론연수 += 1; } } },
    });
    return this;
  }
  추론막대() {
    if (!this.추론열림) return [];
    const 창 = this;
    const 손잡이 = new 가짜요소({ getAttribute: (k) => ({ 'aria-valuenow': String(창.추론값), 'aria-valuemax': '2' })[k] || null });
    return [new 가짜요소({
      getAttribute: (k) => (k === 'aria-describedby' ? '추론설명' : null),
      querySelector: (고른것) => (고른것 === '[role="slider"]' ? 손잡이 : null),
      붙임: { keydown: (사건) => {
        if (사건.key === 'ArrowRight') 창.추론값 = Math.min(2, 창.추론값 + 1);
        if (사건.key === 'ArrowLeft') 창.추론값 = Math.max(0, 창.추론값 - 1);
        if (사건.key === 'Escape') 창.추론열림 = false;
      } },
    })];
  }
  추론설명() {
    return { textContent: this.추론이름들[this.추론값] + ', 3개 중 ' + (this.추론값 + 1) + '번째.' };
  }

  // ── 파일 첨부 흉내 ──
  // 파일칸 = true 로 켜면 ChatGPT 처럼 파일 칸이 생긴다. 첨부막힘 = true 면 붙여도 카드가 안 뜬다(횟수 제한).
  파일칸만들기() {
    const 창 = this;
    this.첨부들 = [];
    this.보낸첨부 = [];
    this.파일칸요소 = new 가짜요소({
      set files(목록) { this._files = 목록; },
      get files() { return this._files; },
      붙임: {
        change: () => {
          if (창.첨부막힘) return;
          for (const f of (this.파일칸요소._files || [])) 창.첨부들.push({ 이름: f.name, 글: f.글, 종류: f.type, 바이트: f.바이트들 });
        },
      },
    });
    return this;
  }
  첨부단추들() {
    const 창 = this;
    const 단추 = [];
    for (const 첨 of (this.첨부들 || [])) {
      단추.push(new 가짜요소({ getAttribute: (k) => (k === 'aria-label' ? 첨.이름 : null) }));
      단추.push(new 가짜요소({
        getAttribute: (k) => (k === 'aria-label' ? 첨.이름 + ' 제거' : null),
        누르면: () => { 창.첨부들 = 창.첨부들.filter((x) => x !== 첨); },
      }));
    }
    return 단추;
  }

  // ── 시험에서 쓰는 손잡이 ──
  // 조각: 진짜 화면처럼 태그가 있는 답을 흉내 낼 때 넘기는 노드 (없으면 글만 있는 답)
  답변붙이기(글, 메시지번호, 조각) {
    this.답변들.push(글);
    this.답변번호들 = this.답변번호들 || [];
    this.답변번호들[this.답변들.length - 1] = 메시지번호 || null;
    this.답변조각들 = this.답변조각들 || [];
    this.답변조각들[this.답변들.length - 1] = 조각 || null;
  }
  // 사람이 ChatGPT 에 직접 쓴 말
  사람말붙이기(글, 메시지번호) {
    this.사람말들 = this.사람말들 || [];
    this.사람말들.push({ 글, 메시지번호 });
  }
  // '긴 대화 가볍게' 가 옛 답을 덜어 낸 화면 — 앞에서부터 몇 개를 뺀다
  옛답덜기(뺄수) {
    this.답변들 = this.답변들.slice(뺄수);
    this.답변번호들 = (this.답변번호들 || []).slice(뺄수);
  }
  되돌리기(남길수) {
    this.답변들 = this.답변들.slice(0, 남길수);
    this.답변번호들 = (this.답변번호들 || []).slice(0, 남길수);
  }
  사람이치기(글) { this.입력창글 = 글; }

  // ── content.js 가 부르는 것들 ──
  셀렉터찾기(무엇) {
    if (무엇 === '어시스턴트') {
      // 진짜 화면에서는 코드블록이 <pre> 로 그려진다.
      // content.js 는 그 <pre> 안 글만 원문 그대로라고 믿으므로 흉내 내 준다.
      return this.답변들.map((글, 순번) => {
        const 메시지번호 = (this.답변번호들 || [])[순번] || null;
        const 프레들 = [];
        const 정규식 = new RegExp('```[a-zA-Z]*\\n([\\s\\S]*?)```', 'g');
        let m;
        while ((m = 정규식.exec(글)) !== null) {
          프레들.push(new 가짜요소({ innerText: m[1] }));
        }
        const 조각 = (this.답변조각들 || [])[순번] || null;
        return new 가짜요소({
          innerText: 글,
          childNodes: 조각 ? [조각] : undefined,
          querySelectorAll: (고른것) => (고른것 === 'pre' ? 프레들 : []),
          // 진짜 화면의 답에는 ChatGPT 메시지 번호(data-message-id)가 붙는다
          getAttribute: (이름) => (이름 === 'data-message-id' ? 메시지번호 : null),
        });
      });
    }
    if (무엇 === '사용자') {
      return (this.사람말들 || []).map((말) => new 가짜요소({
        innerText: 말.글,
        getAttribute: (이름) => (이름 === 'data-message-id' ? 말.메시지번호 : null),
      }));
    }
    if (무엇 === '메시지편집') return this.편집재전송수 !== undefined ? this.편집단추() : [];
    if (무엇 === '편집단추들') return this.편집재전송수 !== undefined ? this.편집칸단추들() : [];
    if (무엇 === '추론단추') return this.추론단추 ? [this.추론단추] : [];
    if (무엇 === '추론막대') return this.추론막대 ? this.추론막대() : [];
    if (무엇 === '한도안내') return (this.한도안내 || []).map((글) => new 가짜요소({ textContent: 글 }));
    if (무엇 === '파일칸') return this.파일칸요소 ? [this.파일칸요소] : [];
    if (무엇 === '첨부단추') return this.첨부단추들();
    if (무엇 === '입력창') return [this.입력창요소];
    if (무엇 === '전송') return [this.전송단추];
    if (무엇 === '정지') return this.스트리밍 ? [new 가짜요소({})] : [];
    return [];
  }
}

module.exports = { 가짜창, 가짜요소 };
